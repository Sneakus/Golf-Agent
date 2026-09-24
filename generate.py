#!/usr/bin/env python3
"""
Generation layer for the golf fault tool.

Retrieval finds entries. This turns them into one short piece of advice,
grounded in the retrieved text, obeying the corpus language rules, and
refusing rather than guessing when retrieval is weak.

Three things are enforced structurally rather than requested politely:
  1. Output shape, via a tool schema the model must fill.
  2. Refusal, decided in code before the model is called at all.
  3. Plain language, via a banned-jargon check on the generated text.

Setup:
    pip install anthropic openai numpy
    set ANTHROPIC_API_KEY=...
    set OPENAI_API_KEY=...

Usage:
    python generate.py --corpus golf-fault-corpus-v3.md golf-out-of-scope-entries.md \
                       --query "chunked my wedge, took a divot before the ball"

    python generate.py --corpus ... --evals golf-eval-sets-v2.md --eval-mode
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus, parse_evals, entry_text, embed
from hybrid_eval import BM25, tokenize, rrf

MODEL = "claude-sonnet-4-6"

# Confidence floor, derived by sweeping every value from 0.20 to 0.60 against
# the eval set (see tune_threshold.py).
#
# The sweep showed the X and N entries catch every out-of-scope query on their
# own, at every threshold, so this floor contributes nothing to abstention. Its
# only measured effect was refusing real questions: at 0.40 it wrongly declined
# three. The lowest genuine query scores 0.388, so 0.35 leaves headroom for
# phrasings the eval set does not contain.
#
# This is a backstop for queries that are in scope but too vague for any entry
# to match. It should almost never fire.
MIN_DENSE_SIM = 0.35
LOW_CONFIDENCE_MESSAGE = (
    "I am not confident enough to diagnose that one. Can you say a bit more "
    "about where it started and which way it curved?"
)

# Mechanical vocabulary the corpus language rules forbid in output.
# The golfer asked what went wrong, not for a physics lesson.
BANNED_JARGON = [
    "face-to-path", "face to path", "dynamic loft", "spin loft", "low point",
    "attack angle", "angle of attack", "club path", "smash factor",
    "gear effect", "d-plane", "launch angle", "spin axis", "kinematic",
]

def advice_schema(entry_ids):
    """Strict tool schema. Entry ID enums are the full corpus, on every request."""
    id_enum = sorted(entry_ids)
    return {
    "name": "give_advice",
    "description": "Return practical golf advice grounded in the retrieved corpus entries.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "what_happened": {
                "type": "string",
                "description": ("Exactly one plain sentence naming the likely cause. Aim for "
                                "15 words. HARD LIMIT 20 WORDS."),
            },
            "entry_id": {
                "type": "string",
                "enum": id_enum,
                "description": "The corpus entry ID this diagnosis comes from, e.g. F007.",
            },
            "setup_steps": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "entry_id": {
                            "type": "string",
                            "enum": id_enum,
                            "description": "The retrieved entry this fix comes from.",
                        },
                        "fix_index": {
                            "type": "integer",
                            "description": "Position of the line in that entry's Fixes or Adjustments list, starting at 0.",
                        },
                        "text": {
                            "type": "string",
                            "description": ("The setup step, worded closely to that line. "
                                            "HARD LIMIT 15 WORDS."),
                        },
                    },
                    "required": ["entry_id", "fix_index", "text"],
                },
            },
            "swing_thought": {
                "type": "string",
                "description": ("ONE thing to feel on the next shot. HARD LIMIT 15 WORDS, "
                                "count them before answering. Describe the feel or the "
                                "intended effect, never a body part to move. "
                                "Good: 'Brush the grass just after the ball.' "
                                "Bad: 'Shift your weight forward through impact.' "
                                "Shorter is better. Ten words is ideal."),
            },
            "why": {
                "type": "string",
                "description": ("Write exactly one plain sentence of at most 20 words. The "
                                "absolute validation limit is 30 words across one or two sentences. "
                                "Plain words a golfer would use. Say 'the club hit the ground "
                                "before the ball' not 'the low point was behind the ball'. "
                                "Say 'you were swinging down too steeply' not 'the attack "
                                "angle was steep'. Never use coaching jargon."),
            },
        },
        "required": ["what_happened", "entry_id", "setup_steps", "swing_thought", "why"],
    },
    }

SYSTEM = """You are the advice layer of a golf shot-logging tool.

You will be given a golfer's description of a shot and the corpus entries retrieved for it.

Rules, in order of importance:

1. Use ONLY the retrieved entries. If they do not support an answer, say so rather than
   drawing on general golf knowledge. Never invent a cause or a fix.
2. ONE swing thought. Never two. Setup steps happen before address, so they do not
   compete with the swing thought. The one-thought limit applies to the swing only.
3. Each setup step points at one Fixes or Adjustments line. Set entry_id and fix_index
   to that line. Word text closely to that line so it can be traced back to it. Include
   only something the golfer can do in the next 30 seconds without practice: aim, ball
   position, stance, gripping down the club, or club choice. A structural grip change is
   not a setup step. Only include grip position when the entry says to grip down, not when
   it says to grip nearer the end. Skip lines that only point at another entry. Return none
   when no step fits. Never pad the list or repeat the swing thought as a setup step.
4. Describe the swing thought's intended effect, not the body part. "Feel the club brush the grass after
   the ball" not "shift your weight forward and keep your chest down".
5. Plain words. Never use these terms, use the plain version instead:
     low point            -> where the club reaches the bottom of its arc
     attack angle         -> how steeply you are swinging down
     face-to-path         -> where the face points against where the club is travelling
     dynamic loft         -> how much loft the club had at impact
     spin loft, club path, smash factor, gear effect, d-plane -> avoid entirely
   The golfer asked what went wrong, not for a physics lesson.
6. Do not write "If it keeps happening" or a sources list. Code adds both after you answer.
7. Use commas or full stops instead of em dashes or en dashes. Plain hyphens are fine.
8. Respect every field's hard word limit. Keep the whole answer at 140 words or fewer,
   excluding sources. Aim below each limit so punctuation and contractions cannot put the
   answer over. What happened is exactly one sentence. Write Why as exactly one sentence
   of at most 20 words; the absolute validator allows no more than two sentences and 30 words.
9. Only state causes the golfer's description supports. Do not infer start direction, ground
   contact, deceleration or any other detail the golfer did not mention.
10. Never stretch an entry to fit, and never state anything that contradicts the entry or
    the ball flight laws.
11. Setup steps must fit the golfer's miss and club. If a fix is scoped to certain clubs or
    situations, do not apply it outside them. Never recommend a step that would make the
    described miss worse, such as more club when the ball went too far.
12. "Why" must use the entry's own explanation. If the entry gives none, keep to what it
    states and do not add a mechanism.
13. For strategy (S) and conditions (C) entries, the headline can be a decision or target
    cue rather than a swing cue. It is still one thought, within the same word limit.

The entries list several causes deliberately. Pick the one the golfer's description
best matches, and use the entry's own distinguishing signals to choose."""


# ------------------------------------------------------------------ retrieval

class Retriever:
    def __init__(self, corpus_paths, strategy="alias_weighted"):
        self.entries = parse_corpus(corpus_paths)
        self.by_id = {e["id"]: e for e in self.entries}
        self.texts = [entry_text(e, strategy) for e in self.entries]
        self.bm25 = BM25(self.texts)
        self.e_vecs = embed(self.texts)
        self.ids = [e["id"] for e in self.entries]

    def search(self, query, k=7, q_vec=None, rrf_k=60, top1_guarantee=False):
        if q_vec is None:
            q_vec = embed([query])[0]
        dense = self.e_vecs @ q_vec
        d_order = list(np.argsort(-dense))
        b_scores = self.bm25.get_scores(tokenize(query))
        b_order = list(np.argsort(-b_scores))
        fused = {}
        for ranking in (d_order, b_order):
            for rank, idx in enumerate(ranking):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        order = sorted(fused, key=fused.get, reverse=True)
        chosen = order[:k]
        if top1_guarantee:
            for must in (b_order[0], d_order[0]):
                if must not in chosen:
                    chosen = chosen[:-1] + [must]
        top = [self.ids[j] for j in chosen]
        return {
            "ids": top,
            "entries": [self.by_id[i] for i in top],
            "top_dense_sim": float(dense[d_order[0]]),
            "dense_top_id": self.ids[d_order[0]],
            "bm25_top_id": self.ids[b_order[0]],
            "scores": {self.ids[j]: round(fused[j], 6) for j in chosen},
        }


# ------------------------------------------------------------------ refusal

WHERE_RE = re.compile(r"\*\*Where the answer is:\*\*\s*(.+)")


def decide_refusal(result):
    """
    Decided in code, before the model is called. The model never gets the
    chance to talk itself into answering something it should decline.
    """
    top = result["ids"][0]
    if top.startswith("X"):
        msg = ("That is outside what this tool covers. It diagnoses shots you have hit, "
               "using your own logged data.")
        # Redirect using the entry's own guidance rather than a flat refusal
        entry = result["entries"][0] if result.get("entries") else None
        if entry:
            m = WHERE_RE.search(entry["text"])
            if m:
                where = m.group(1).strip().rstrip('.')
                where = where[0].lower() + where[1:] if where else where
                msg += f" For that, try {where}."
        return {
            "refused": True,
            "kind": "out_of_scope",
            "message": msg,
            "entry_id": top,
        }
    if top.startswith("N"):
        return {
            "refused": True,
            "kind": "no_fault",
            "message": "Nothing to fix there. Log it and move on.",
            "entry_id": top,
        }
    if result["top_dense_sim"] < MIN_DENSE_SIM:
        return {
            "refused": True,
            "kind": "low_confidence",
            "message": LOW_CONFIDENCE_MESSAGE,
            "entry_id": None,
        }
    return {"refused": False}


# ------------------------------------------------------------------ generation

DIFFERENTIAL_HEADING = "## Differential diagnosis: when the fix does not work"
NEXT_HEADING = "## Language rules for anything the tool says"


def parse_differentials(corpus_paths):
    """Parse the corpus notes table as a read-only generation lookup."""
    lookup = {}
    for path in corpus_paths:
        text = Path(path).read_text(encoding="utf-8")
        if DIFFERENTIAL_HEADING not in text:
            continue
        section = text.split(DIFFERENTIAL_HEADING, 1)[1]
        section = section.split(NEXT_HEADING, 1)[0]
        for line in section.splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 3 or cells[0] == "Entry":
                continue
            primary_ids = re.findall(r"\b[FPDLSCR]\d{3}\b", cells[0])
            confused_ids = re.findall(r"\b[FPDLSCR]\d{3}\b", cells[1])
            for primary_id in primary_ids:
                lookup.setdefault(primary_id, []).append({
                    "confused_ids": confused_ids,
                    "test": cells[2],
                })
    return lookup


def compensation_risk(entry):
    match = re.search(
        r"\*\*Compensation risk:\*\*\s*(.+?)(?=\n\n|\Z)",
        entry["text"],
        re.S,
    )
    return " ".join(match.group(1).split()) if match else ""




CACHE_DIR = Path(".golf-cache")
SNAPSHOT_PATH = Path("retrieval_snapshot.json")
INPUT_USD_PER_TOKEN = 3 / 1_000_000
OUTPUT_USD_PER_TOKEN = 15 / 1_000_000
POINTER_RE = re.compile(r"^\s*same as\b", re.I)
FIELD_LIMIT_RE = re.compile(
    r"^(what_happened|swing_thought|why|setup_steps\[\d+\]\.text) is \d+ words"
)
JARGON_RE = re.compile(
    r"^mechanical jargon in (what_happened|swing_thought|why|setup_steps\[\d+\]\.text):"
)


def live_enabled():
    return os.environ.get("GOLF_LIVE") == "1"


def cache_key(payload):
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def retrieval_config_hash(corpus_paths):
    parts = ["alias_weighted", "rrf=60", "k=7", "top1_guarantee=off"]
    for path in corpus_paths:
        parts.append(hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def strip_model_context(text):
    text = re.sub(r"\n\*\*Compensation risk:\*\*.*(?=\n\n|\Z)", "", text, flags=re.S)
    text = re.sub(r"\n\*\*Evidence tier:\*\*.*", "", text)
    return text.strip()


def listed_fixes(entry):
    match = re.search(
        r"\*\*(?:Fixes|Adjustments)\*\*\s*(.+?)(?=\n\n\*\*|\Z)",
        entry["text"],
        re.S,
    )
    if not match:
        return []
    return re.findall(r"^-\s+(.+)$", match.group(1), re.M)


def scrub_dashes(text):
    return text.replace("\u2014", "-").replace("\u2013", "-")


def scrub_advice(advice):
    advice["what_happened"] = scrub_dashes(advice.get("what_happened", ""))
    advice["swing_thought"] = scrub_dashes(advice.get("swing_thought", ""))
    advice["why"] = scrub_dashes(advice.get("why", ""))
    for step in advice.get("setup_steps") or []:
        if "text" in step:
            step["text"] = scrub_dashes(step["text"])
        elif "step" in step:
            step["text"] = scrub_dashes(step.pop("step"))
            step["entry_id"] = step.pop("source_id", step.get("entry_id"))
    return advice


def followup_text(entry_id, retrieved_ids, differentials):
    """Exact differential test. Rows apply in both directions. No compensation path."""
    rank = {entry: i for i, entry in enumerate(retrieved_ids)}
    best = None
    rows = []
    for primary, primary_rows in differentials.items():
        for row in primary_rows:
            rows.append((primary, row))
    for primary, row in rows:
        parties = [primary, *row["confused_ids"]]
        if entry_id not in parties:
            continue
        others = [item for item in parties if item != entry_id and item in rank]
        if not others:
            continue
        other = min(others, key=lambda item: rank[item])
        candidate = (rank[other], row["test"])
        if best is None or candidate[0] < best[0]:
            best = candidate
    return best[1] if best else ""


def apply_code_fields(advice, result, differentials):
    text = followup_text(advice["entry_id"], result["ids"], differentials)
    advice["if_it_keeps_happening"] = text
    used = [advice["entry_id"]]
    used.extend(step["entry_id"] for step in advice.get("setup_steps") or [])
    advice["sources"] = list(dict.fromkeys(used))
    return advice


def word_count(text):
    return len(re.findall(r"\b[\w']+(?:-[\w']+)*\b", text or ""))


def content_words(text):
    words = set()
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "for", "with", "your", "you", "it",
        "on", "in", "at", "from", "rather", "than", "not", "so", "as", "is", "be",
        "this", "that", "before", "through", "all", "into", "by", "if", "its", "are",
        "was", "were", "when", "then", "just", "only", "also", "off", "up", "down",
        "out", "over", "more", "less", "one", "keep", "feel", "check", "make", "take",
        "since", "because",
    }
    for word in re.findall(r"[a-z']+", (text or "").lower()):
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            word = word[:-1]
        if word in stop or len(word) < 4:
            continue
        words.add(word)
    return words


def model_fields(advice):
    fields = [
        ("what_happened", advice.get("what_happened", "")),
        ("swing_thought", advice.get("swing_thought", "")),
        ("why", advice.get("why", "")),
    ]
    for i, step in enumerate(advice.get("setup_steps") or []):
        fields.append((f"setup_steps[{i}].text", step.get("text", "")))
    return fields


def single_field_repair(problems):
    fields = []
    for problem in problems:
        limit = FIELD_LIMIT_RE.match(problem)
        jargon = JARGON_RE.match(problem)
        if limit:
            fields.append(limit.group(1))
        elif jargon:
            fields.append(jargon.group(1))
        else:
            return None
    if len(set(fields)) == 1:
        return fields[0]
    return None


def validate(advice, result):
    problems = []
    limits = {"what_happened": 20, "swing_thought": 15, "why": 30}
    for field, text in model_fields(advice):
        limit = 15 if field.startswith("setup_steps[") else limits[field]
        count = word_count(text)
        if count > limit:
            problems.append(f"{field} is {count} words, limit is {limit}")
    thought = advice.get("swing_thought", "")
    if re.search(r"\b(and then|also|as well as|secondly)\b|;", thought, re.I):
        problems.append("swing_thought looks like more than one instruction")
    for field, text in model_fields(advice):
        lowered = text.lower()
        for term in BANNED_JARGON:
            if term in lowered:
                problems.append(f"mechanical jargon in {field}: '{term}'")
        if "\u2014" in text or "\u2013" in text:
            problems.append(f"{field} contains an em dash or en dash")
    if len(re.findall(r"[.!?]+(?:\s|$)", advice.get("what_happened", ""))) != 1:
        problems.append("what_happened must be exactly one sentence")
    why_sentences = len(re.findall(r"[.!?]+(?:\s|$)", advice.get("why", "")))
    if why_sentences < 1 or why_sentences > 2:
        problems.append("why must be one or two sentences")
    retrieved = set(result["ids"])
    if advice.get("entry_id") not in retrieved:
        problems.append(f"diagnosed from {advice.get('entry_id')}, which was not retrieved")
    steps = advice.get("setup_steps") or []
    if not isinstance(steps, list) or len(steps) > 3:
        problems.append("setup_steps must contain 0 to 3 items")
    by_id = {entry["id"]: entry for entry in result["entries"]}
    for i, step in enumerate(steps):
        source_id = step.get("entry_id")
        if source_id not in retrieved:
            problems.append(f"setup_steps[{i}] sourced from {source_id}, which was not retrieved")
            continue
        fixes = listed_fixes(by_id[source_id])
        index = step.get("fix_index")
        if not isinstance(index, int) or not 0 <= index < len(fixes):
            problems.append(f"setup_steps[{i}] fix_index is not a line in {source_id}")
            continue
        line = fixes[index]
        if POINTER_RE.match(line):
            problems.append(f"setup_steps[{i}] points at a line that only refers elsewhere")
            continue
        if not (content_words(step.get("text", "")) & content_words(line)):
            problems.append(
                f"setup_steps[{i}] does not match fix line {index} of {source_id}"
            )
        if "grip" in step.get("text", "").lower() and "grip down" not in step.get("text", "").lower():
            problems.append(f"setup_steps[{i}] changes the grip without gripping down")
    total = sum(word_count(text) for _, text in model_fields(advice))
    total += word_count(advice.get("if_it_keeps_happening", ""))
    if total > 140:
        problems.append(f"answer is {total} words, limit is 140")
    return problems


def model_context(result):
    return "\n\n---\n\n".join(
        f"[{entry['id']}] {entry['name']}\n{strip_model_context(entry['text'])}"
        for entry in result["entries"]
    )


def request_payload(query, result, entry_ids, problems=None, previous=None, field=None):
    schema = advice_schema(entry_ids)
    if field:
        schema = {
            "name": "rewrite_field",
            "description": "Rewrite one field only.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
        user = (
            f"Rewrite only {field}. Previous text: {json.dumps(previous)}\n"
            f"Failures:\n" + "\n".join(f"- {problem}" for problem in problems) +
            "\nStay within its word limit and use none of the banned mechanical terms."
        )
        tool_name = "rewrite_field"
    else:
        user = f"Golfer's description of the shot:\n{query}\n\nRetrieved corpus entries:\n\n{model_context(result)}"
        if problems:
            user += ("\n\nYour previous answer broke these rules:\n"
                     + "\n".join(f"  - {problem}" for problem in problems)
                     + f"\n\nPrevious answer: {json.dumps(previous)}")
        tool_name = "give_advice"
    return {
        "model": MODEL,
        "max_tokens": 1000,
        "system": SYSTEM,
        "tools": [schema],
        "tool_choice": {"type": "tool", "name": tool_name},
        "messages": [{"role": "user", "content": user}],
        "extra_body": {"temperature": 0},
    }, tool_name


class Usage:
    def __init__(self, input_tokens=0, output_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def complete(payload, tool_name, live, stub, calls):
    key = cache_key({"payload": payload, "tool": tool_name})
    path = CACHE_DIR / f"{key}.json"
    if path.exists() and not stub:
        saved = json.loads(path.read_text(encoding="utf-8"))
        return saved["advice"], Usage(saved["usage"]["in"], saved["usage"]["out"]), False
    if stub:
        return stub(payload, tool_name), Usage(1, 1), False
    if not live:
        raise SystemExit(
            f"Replay cache miss for {key[:12]}. No Anthropic call was made. "
            "Set GOLF_LIVE=1 only when you intend to pay for a live run."
        )
    if calls["made"] >= calls["max"]:
        raise SystemExit(f"Call cap of {calls['max']} reached. No further Anthropic call was made.")
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(**payload)
    calls["made"] += 1
    advice = None
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            advice = block.input
    if advice is None:
        raise RuntimeError("Model did not return the tool call")
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps({
        "advice": advice,
        "usage": {"in": response.usage.input_tokens, "out": response.usage.output_tokens},
    }), encoding="utf-8")
    return advice, Usage(response.usage.input_tokens, response.usage.output_tokens), True


def splice_field(advice, field, text):
    match = re.fullmatch(r"setup_steps\[(\d+)\]\.text", field)
    if match:
        advice["setup_steps"][int(match.group(1))]["text"] = text
    else:
        advice[field] = text
    return advice


def answer(query, result, differentials, entry_ids, live=False, stub=None, calls=None):
    calls = calls if calls is not None else {"made": 0, "max": 25}
    if decide_refusal(result)["refused"]:
        refusal = decide_refusal(result)
        return {"query": query, "retrieved": result["ids"], **refusal,
                "top_dense_sim": round(result["top_dense_sim"], 3)}
    payload, tool_name = request_payload(query, result, entry_ids)
    advice, usage, _called = complete(payload, tool_name, live, stub, calls)
    advice = apply_code_fields(scrub_advice(advice), result, differentials)
    problems = validate(advice, result)
    retried = False
    if problems:
        retried = True
        field = single_field_repair(problems)
        if field:
            payload, tool_name = request_payload(
                query, result, entry_ids, problems=problems, previous=advice.get(field, advice), field=field
            )
            rewritten, usage2, _called = complete(payload, tool_name, live, stub, calls)
            advice = splice_field(advice, field, scrub_dashes(rewritten["text"]))
        else:
            payload, tool_name = request_payload(
                query, result, entry_ids, problems=problems, previous=advice
            )
            advice, usage2, _called = complete(payload, tool_name, live, stub, calls)
            advice = scrub_advice(advice)
        usage.input_tokens += usage2.input_tokens
        usage.output_tokens += usage2.output_tokens
        advice = apply_code_fields(advice, result, differentials)
        problems = validate(advice, result)
    return {
        "retried": retried,
        "query": query,
        "retrieved": result["ids"],
        "refused": False,
        "top_dense_sim": round(result["top_dense_sim"], 3),
        "advice": advice,
        "validation_problems": problems,
        "tokens": {"in": usage.input_tokens, "out": usage.output_tokens},
    }


def answer_accuracy_rows(results):
    rows = []
    for result in results:
        if result.get("refused"):
            continue
        expected = set(result["expected"])
        chosen = result["advice"]["entry_id"]
        rows.append({
            "subset": result["subset"], "n": result["n"], "query": result["query"],
            "expected": result["expected"], "chosen": chosen,
            "correct": float(chosen in expected),
        })
    return rows


def report_answer_accuracy(results):
    from evaluate import bootstrap_ci
    rows = answer_accuracy_rows(results)
    if not rows:
        return
    print("\nAnswer-level accuracy: diagnosed entry is one of the expected entries")
    print(f"{'Metric':<12} {'Score':>7}   {'95% CI':>16}   Correct")
    print("-" * 60)

    def emit(label, group):
        vals = [row["correct"] for row in group]
        mean = sum(vals) / len(vals)
        lo, hi = bootstrap_ci(vals)
        print(f"{label:<12} {mean:>7.3f}   [{lo:.3f}, {hi:.3f}]   {int(sum(vals))}/{len(vals)}")

    emit("overall", rows)
    for subset in ("A1", "A2", "A3"):
        group = [row for row in rows if row["subset"] == subset]
        if group:
            emit(subset, group)


def print_answer(answer_row, plain=False):
    if not plain:
        print(f"\nQuery: {answer_row['query']}")
        print(f"Retrieved: {', '.join(answer_row['retrieved'])}  (top dense sim {answer_row['top_dense_sim']})")
    if answer_row.get("refused"):
        print(answer_row["message"] if plain else f"\nDECLINED ({answer_row['kind']})\n  {answer_row['message']}")
        return
    advice = answer_row["advice"]
    prefix = "" if plain else "  "
    if not plain:
        print()
    print(f"{prefix}What happened: {advice['what_happened']}")
    if advice["setup_steps"]:
        print(f"{prefix}Before your next shot:")
        for step in advice["setup_steps"]:
            print(f"{prefix}- {step['text']} [{step['entry_id']}#{step['fix_index']}]")
    headline = "Key thought" if advice["entry_id"][:1] in ("S", "C") else "Swing thought"
    print(f"{prefix}{headline}: {advice['swing_thought']}")
    print(f"{prefix}Why: {advice['why']}")
    if advice.get("if_it_keeps_happening"):
        print(f"{prefix}If it keeps happening: {advice['if_it_keeps_happening']}")
    print(f"{prefix}Sources: {', '.join(advice['sources'])}")
    if answer_row["validation_problems"] and not plain:
        print("\n  VALIDATION FAILURES:")
        for problem in answer_row["validation_problems"]:
            print(f"    - {problem}")


def estimate_cost(saved_path, numbers, batch=False, passed=7, saved_passed=5):
    """Scale input tokens from the saved 5-entry runs to the live passed count."""
    saved = json.loads(Path(saved_path).read_text(encoding="utf-8"))
    rows = [row for row in saved if row.get("n") in numbers and row.get("tokens")]
    incoming = sum(row["tokens"]["in"] for row in rows) * passed / saved_passed
    outgoing = sum(row["tokens"]["out"] for row in rows)
    cost = incoming * INPUT_USD_PER_TOKEN + outgoing * OUTPUT_USD_PER_TOKEN
    if batch:
        cost *= 0.5
    return cost, int(incoming), outgoing, len(rows)


def write_snapshot(retriever, queries, corpus_paths):
    payload = {
        "config_hash": retrieval_config_hash(corpus_paths),
        "queries": [],
    }
    q_vecs = embed([query["query"] for query in queries])
    for query, q_vec in zip(queries, q_vecs):
        found = retriever.search(query["query"], q_vec=q_vec)
        payload["queries"].append({
            "n": query["n"],
            "query": query["query"],
            "ids": found["ids"],
            "scores": found["scores"],
            "top_dense_sim": found["top_dense_sim"],
        })
    SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {SNAPSHOT_PATH} ({payload['config_hash'][:12]})")


def load_snapshot(corpus_paths):
    if not SNAPSHOT_PATH.exists():
        raise SystemExit("No retrieval_snapshot.json. Run with --write-snapshot or --fresh-retrieval.")
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    expected = retrieval_config_hash(corpus_paths)
    if payload.get("config_hash") != expected:
        raise SystemExit("Snapshot configuration hash does not match. Refusing to use it.")
    return {row["n"]: row for row in payload["queries"]}


def result_from_snapshot(row, by_id):
    return {
        "ids": row["ids"],
        "entries": [by_id[entry_id] for entry_id in row["ids"]],
        "top_dense_sim": row["top_dense_sim"],
        "scores": row["scores"],
    }


def run_stub():
    entry = {
        "id": "F008",
        "name": "Thin",
        "text": (
            "**What it is:** Contact above the ball's middle.\n\n"
            "**Fixes**\n- Feel the clubhead brushing the ground after the ball.\n"
            "- Same as F009.\n\n**Evidence tier:** settled\n\n"
            "**Compensation risk:** This note must not reach the model.\n"
        ),
    }
    result = {
        "ids": ["F008"],
        "entries": [entry],
        "top_dense_sim": 0.5,
        "scores": {"F008": 0.01},
    }
    state = {"n": 0}

    def stub(_payload, tool_name):
        state["n"] += 1
        if tool_name == "rewrite_field":
            return {"text": "The club met the ball above its middle."}
        return {
            "what_happened": "The club caught the ball above its middle.",
            "entry_id": "F008",
            "setup_steps": [{
                "entry_id": "F008",
                "fix_index": 0,
                "text": "Feel the clubhead brushing the ground after the ball.",
            }],
            "swing_thought": "Brush the ground just after the ball.",
            "why": "The club met the ball too high \u2014 and this sentence keeps going with extra words about the strike, the loft, the hands, the ground and the follow through so the word limit forces one targeted repair.",
        }

    os.environ.pop("GOLF_LIVE", None)
    finished = answer("stub query", result, {}, ["F008"], live=False, stub=stub)
    assert not finished["validation_problems"], finished["validation_problems"]
    assert finished["retried"] is True
    assert "\u2014" not in finished["advice"]["why"]
    assert "Compensation risk" not in model_context(result)
    assert finished["advice"]["sources"] == ["F008"]
    print("Replay stub passed: repair, dash scrub, stripped context, code sources, no API call.")
    print_answer(finished, plain=True)


def submit_batch(requests, live, calls):
    """Message Batches API at half price. Not run unless --batch is passed."""
    if not live:
        raise SystemExit("Batch mode is a live Anthropic call. GOLF_LIVE is not set, so it was not submitted.")
    if calls["made"] + len(requests) > calls["max"]:
        raise SystemExit("Batch would exceed --max-calls. It was not submitted.")
    import anthropic
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    calls["made"] += len(requests)
    while batch.processing_status != "ended":
        time.sleep(2)
        batch = client.messages.batches.retrieve(batch.id)
    return list(client.messages.batches.results(batch.id))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True, nargs="+")
    parser.add_argument("--query")
    parser.add_argument("--evals")
    parser.add_argument("--eval-mode", action="store_true")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default="generation_results.json")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--max-calls", type=int, default=25)
    parser.add_argument("--confirm-cost", action="store_true")
    parser.add_argument("--fresh-retrieval", action="store_true")
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--subset", type=int, nargs="*")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--stub", action="store_true")
    parser.add_argument("--saved-results", default="generation_results.json")
    args = parser.parse_args()
    globals()["MODEL"] = args.model

    if args.stub:
        run_stub()
        return

    live = live_enabled()
    calls = {"made": 0, "max": args.max_calls}
    if args.write_snapshot or args.fresh_retrieval or args.query:
        retriever = Retriever(args.corpus)
        if args.write_snapshot:
            write_snapshot(retriever, parse_evals(args.evals), args.corpus)
            if not args.query and not args.eval_mode:
                return
    else:
        retriever = None

    entries = parse_corpus(args.corpus)
    by_id = {entry["id"]: entry for entry in entries}
    entry_ids = list(by_id)
    differentials = parse_differentials(args.corpus)

    def one(query, found):
        return answer(query, found, differentials, entry_ids, live=live, calls=calls)

    if args.query:
        found = retriever.search(args.query)
        print_answer(one(args.query, found), plain=args.plain)
        return

    if not args.eval_mode or not args.evals:
        raise SystemExit("Give --query, or --evals with --eval-mode")

    queries = parse_evals(args.evals)
    if args.subset:
        wanted = set(args.subset)
        queries = [query for query in queries if query["n"] in wanted]
    if args.limit:
        queries = queries[: args.limit]
    numbers = [query["n"] for query in queries]
    if live and Path(args.saved_results).exists():
        cost, incoming, outgoing, counted = estimate_cost(args.saved_results, set(numbers), batch=args.batch)
        print(f"Estimated cost: ${cost:.2f} from {counted} saved answers "
              f"({incoming:,} in, {outgoing:,} out)"
              + (" at batch half price" if args.batch else ""))
        if cost > 0.50 and not args.confirm_cost:
            raise SystemExit("Estimate is above $0.50. Re-run with --confirm-cost to proceed. No call was made.")

    if args.fresh_retrieval:
        found_by_n = {query["n"]: retriever.search(query["query"]) for query in queries}
    else:
        snapshot = load_snapshot(args.corpus)
        found_by_n = {query["n"]: result_from_snapshot(snapshot[query["n"]], by_id) for query in queries}

    if args.batch:
        requests = []
        pending = []
        for query in queries:
            found = found_by_n[query["n"]]
            refusal = decide_refusal(found)
            if refusal["refused"]:
                continue
            payload, _tool = request_payload(query["query"], found, entry_ids)
            requests.append({"custom_id": f"q{query['n']}", "params": payload})
            pending.append(query)
        first = submit_batch(requests, live, calls)
        repairs = []
        by_custom = {item.custom_id: item for item in first}
        for query in pending:
            item = by_custom[f"q{query['n']}"]
            if item.result.type != "succeeded":
                raise RuntimeError(f"Batch request q{query['n']} ended as {item.result.type}")
            message = item.result.message
            advice = None
            for block in message.content:
                if block.type == "tool_use":
                    advice = block.input
            found = found_by_n[query["n"]]
            advice = apply_code_fields(scrub_advice(advice), found, differentials)
            problems = validate(advice, found)
            if not problems:
                continue
            field = single_field_repair(problems)
            payload, _tool = request_payload(
                query["query"], found, entry_ids, problems=problems,
                previous=advice.get(field, advice) if field else advice,
                field=field,
            )
            repairs.append({"custom_id": f"repair{query['n']}", "params": payload})
        if repairs:
            submit_batch(repairs, live, calls)
        print(f"Anthropic requests counted against --max-calls: {calls['made']}")
        return

    results = []
    for query in queries:
        row = one(query["query"], found_by_n[query["n"]])
        row.update(subset=query["subset"], n=query["n"], expected=query["expected"],
                   should_refuse=query["expects_nothing"])
        results.append(row)
        print(f"  {query['n']}", file=sys.stderr)

    answered = [row for row in results if not row["refused"]]
    refused = [row for row in results if row["refused"]]
    should = [row for row in results if row["should_refuse"]]
    print(f"\nAnswered: {len(answered)}   Refused: {len(refused)}")
    print(f"Correct refusals: {sum(1 for row in should if row['refused'])}/{len(should)}")
    print(f"False refusals: {sum(1 for row in refused if not row['should_refuse'])}")
    print(f"Repaired on retry: {sum(1 for row in answered if row.get('retried'))}")
    failed = [row for row in answered if row["validation_problems"]]
    print(f"Validation failures after retry: {len(failed)}/{len(answered)}")
    report_answer_accuracy(results)
    Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Anthropic calls this run: {calls['made']}")


if __name__ == "__main__":
    main()
