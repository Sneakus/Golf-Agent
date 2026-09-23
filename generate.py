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
import io
import json
import re
import sys
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

# Mechanical vocabulary the corpus language rules forbid in output.
# The golfer asked what went wrong, not for a physics lesson.
BANNED_JARGON = [
    "face-to-path", "face to path", "dynamic loft", "spin loft", "low point",
    "attack angle", "angle of attack", "club path", "smash factor",
    "gear effect", "d-plane", "launch angle", "spin axis", "kinematic",
]

ADVICE_SCHEMA = {
    "name": "give_advice",
    "description": "Return practical golf advice grounded in the retrieved corpus entries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "what_happened": {
                "type": "string",
                "description": ("Exactly one plain sentence naming the likely cause. Aim for "
                                "15 words. HARD LIMIT 20 WORDS."),
            },
            "entry_id": {
                "type": "string",
                "description": "The corpus entry ID this diagnosis comes from, e.g. F007.",
            },
            "setup_steps": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "step": {
                            "type": "string",
                            "description": ("A next-shot setup step. Aim for 10 words. "
                                            "HARD LIMIT 15 WORDS."),
                        },
                        "source_id": {
                            "type": "string",
                            "description": "The retrieved entry ID containing this step.",
                        },
                    },
                    "required": ["step", "source_id"],
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
            "if_it_keeps_happening": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": ("One plain line. Aim for 15 words. HARD LIMIT 20 WORDS. "
                                        "Follow required_action in the supplied lookup. When it is "
                                        "return_empty, this must be an empty string."),
                    },
                    "source_id": {
                        "type": ["string", "null"],
                        "description": ("When using a differential, exactly one retrieved confusable "
                                        "entry ID, never the primary ID. Otherwise the primary ID "
                                        "for compensation risk, or null when text is empty."),
                    },
                },
                "required": ["text"],
            },
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entry IDs used. Every claim must come from these.",
            },
        },
        "required": [
            "what_happened", "entry_id", "setup_steps", "swing_thought", "why",
            "if_it_keeps_happening", "citations",
        ],
    },
}

SYSTEM = """You are the advice layer of a golf shot-logging tool.

You will be given a golfer's description of a shot and the corpus entries retrieved for it.

Rules, in order of importance:

1. Use ONLY the retrieved entries. If they do not support an answer, say so rather than
   drawing on general golf knowledge. Never invent a cause or a fix.
2. ONE swing thought. Never two. Setup steps happen before address, so they do not
   compete with the swing thought. The one-thought limit applies to the swing only.
3. Setup steps must come from a Fixes or Adjustments section in a retrieved entry. Include
   only something the golfer can do in the next 30 seconds without practice: aim, ball
   position, stance, gripping down the club, or club choice. A structural grip change is
   not a setup step. Only include grip position when the entry says to grip down, not when
   it says to grip nearer the end. Return none when no step fits. Never pad the list or
   repeat the swing thought as a setup step.
4. Describe the swing thought's intended effect, not the body part. "Feel the club brush the grass after
   the ball" not "shift your weight forward and keep your chest down".
5. Plain words. Never use these terms, use the plain version instead:
     low point            -> where the club reaches the bottom of its arc
     attack angle         -> how steeply you are swinging down
     face-to-path         -> where the face points against where the club is travelling
     dynamic loft         -> how much loft the club had at impact
     spin loft, club path, smash factor, gear effect, d-plane -> avoid entirely
   The golfer asked what went wrong, not for a physics lesson.
6. Build "If it keeps happening" from the supplied lookup for the selected primary entry.
   If a listed confusable entry was retrieved, name it and use the table's distinguishing
   test. If several were retrieved, choose exactly one. Set source_id to that confusable
   entry, never to the primary entry. Otherwise use the primary entry's compensation risk
   and its ID. When required_action is return_empty, return text as an empty string and
   source_id as null. Never substitute another fix or reminder. Never name an entry that
   was not retrieved.
7. Use commas or full stops instead of em dashes or en dashes. Plain hyphens are fine.
8. Respect every field's hard word limit. Keep the whole answer at 140 words or fewer,
   excluding sources. Aim below each limit so punctuation and contractions cannot put the
   answer over. What happened is exactly one sentence. Write Why as exactly one sentence
   of at most 20 words; the absolute validator allows no more than two sentences and 30 words.

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

    def search(self, query, k=5, q_vec=None):
        if q_vec is None:
            q_vec = embed([query])[0]
        dense = self.e_vecs @ q_vec
        d_order = list(np.argsort(-dense))
        b_order = list(np.argsort(-self.bm25.get_scores(tokenize(query))))
        order = rrf([d_order, b_order])
        top = [self.ids[j] for j in order[:k]]
        return {
            "ids": top,
            "entries": [self.by_id[i] for i in top],
            "top_dense_sim": float(dense[d_order[0]]),
            "dense_top_id": self.ids[d_order[0]],
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
            "message": "I am not confident enough to diagnose that one. Can you say a bit more "
                       "about where it started and which way it curved?",
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


def build_followup_lookup(result, differentials):
    """Give the model lookup data for every retrieved potential primary entry."""
    retrieved = set(result["ids"])
    rows = []
    for entry in result["entries"]:
        differential_rows = []
        retrieved_confusables = []
        for row in differentials.get(entry["id"], []):
            present = [
                item for item in row["confused_ids"] if item in retrieved
            ]
            retrieved_confusables.extend(present)
            differential_rows.append({
                "confused_ids": row["confused_ids"],
                "retrieved_confusable_ids": present,
                "distinguishing_test": row["test"],
            })
        risk = compensation_risk(entry)
        if retrieved_confusables:
            required_action = "use_retrieved_confusable"
        elif risk:
            required_action = "use_compensation_risk"
        else:
            required_action = "return_empty"
        rows.append({
            "primary_id": entry["id"],
            "required_action": required_action,
            "differentials": differential_rows,
            "compensation_risk": risk,
        })
    return rows


def eligible_setup_bullets(result):
    """Extract only corpus bullets that fit the next-shot setup categories."""
    eligible = []
    for entry in result["entries"]:
        section = re.search(
            r"\*\*(?:Fixes|Adjustments)\*\*\s*(.+?)(?=\n\n\*\*|\Z)",
            entry["text"],
            re.S,
        )
        if not section:
            continue
        for bullet in re.findall(r"^-\s+(.+)$", section.group(1), re.M):
            lowered = bullet.lower()
            is_setup = (
                re.search(
                    r"\b(aim|alignment|ball position|ball back|setup distance|"
                    r"landing spot|land it|safe miss|side of the fairway)\b",
                    lowered,
                )
                or "set up" in lowered
                or "set your shoulders" in lowered
                or "grip down" in lowered
                or re.search(
                    r"\b(club up|club down|take .* club|add a club|club selection|"
                    r"choose the club|pick .* club|more loft|less club)\b",
                    lowered,
                )
            )
            if is_setup:
                eligible.append({"source_id": entry["id"], "source_text": bullet})
    return eligible


def generate(query, result, differentials, model=MODEL, problems=None, previous=None):
    import anthropic
    client = anthropic.Anthropic()

    context = "\n\n---\n\n".join(
        f"[{e['id']}] {e['name']}\n{e['text']}" for e in result["entries"]
    )
    followup_lookup = build_followup_lookup(result, differentials)
    setup_lookup = eligible_setup_bullets(result)
    user = (f"Golfer's description of the shot:\n{query}\n\n"
            f"Retrieved corpus entries:\n\n{context}\n\n"
            "Eligible setup source bullets. Setup steps may use ONLY this list. "
            "Paraphrase briefly without changing the action. Return none if empty:\n"
            f"{json.dumps(setup_lookup, indent=2)}\n\n"
            "Read-only lookup for If it keeps happening:\n"
            f"{json.dumps(followup_lookup, indent=2)}")

    if problems:
        repair_hints = []
        if any("must be empty when no lookup source exists" in p for p in problems):
            repair_hints.append(
                'Set if_it_keeps_happening exactly to {"text": "", "source_id": null}.'
            )
        if any("retrieved confusable entry before compensation risk" in p for p in problems):
            repair_hints.append(
                "Set follow-up source_id to one retrieved_confusable_id for the selected primary."
            )
        if any("why is" in p or "why must be" in p for p in problems):
            repair_hints.append("Rewrite Why as one sentence of at most 20 words.")
        user += ("\n\nYour previous answer broke these rules:\n"
                 + "\n".join(f"  - {p}" for p in problems)
                 + f"\n\nPrevious answer: {json.dumps(previous)}"
                 + ("\n\nRequired repair:\n" + "\n".join(repair_hints)
                    if repair_hints else "")
                 + "\n\nFix every listed failure. Recount all affected fields before returning. "
                   "Keep everything else.")

    resp = client.messages.create(
        model=model,
        max_tokens=1000,
        system=SYSTEM,
        tools=[ADVICE_SCHEMA],
        tool_choice={"type": "tool", "name": "give_advice"},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input, resp.usage
    raise RuntimeError("Model did not return the tool call")


# ------------------------------------------------------------------ validation

def word_count(text):
    return len(re.findall(r"\b[\w']+(?:-[\w']+)*\b", text))


def all_text_fields(advice):
    fields = [
        ("what_happened", advice["what_happened"]),
        ("swing_thought", advice["swing_thought"]),
        ("why", advice["why"]),
        ("if_it_keeps_happening.text", advice["if_it_keeps_happening"]["text"]),
    ]
    fields.extend(
        (f"setup_steps[{i}].step", item["step"])
        for i, item in enumerate(advice["setup_steps"])
    )
    return fields


def validate(advice, result, differentials):
    """Programmatic guardrails. Anything here is a hard failure, not a style note."""
    problems = []

    limits = {
        "what_happened": 20,
        "swing_thought": 15,
        "why": 30,
        "if_it_keeps_happening.text": 20,
    }
    for field, text in all_text_fields(advice):
        limit = 15 if field.startswith("setup_steps[") else limits[field]
        count = word_count(text)
        if count > limit:
            problems.append(f"{field} is {count} words, limit is {limit}")

    # one thought only: a second imperative joined by 'and then', 'also', ';'
    if re.search(r"\b(and then|also|as well as|secondly)\b|;", advice["swing_thought"], re.I):
        problems.append("swing_thought looks like more than one instruction")

    for field, text in all_text_fields(advice):
        lowered = text.lower()
        for term in BANNED_JARGON:
            if term in lowered:
                problems.append(f"mechanical jargon in {field}: '{term}'")
        if "\u2014" in text or "\u2013" in text:
            problems.append(f"{field} contains an em dash or en dash")

    if len(re.findall(r"[.!?]+(?:\s|$)", advice["what_happened"])) != 1:
        problems.append("what_happened must be exactly one sentence")
    why_sentences = len(re.findall(r"[.!?]+(?:\s|$)", advice["why"]))
    if why_sentences < 1 or why_sentences > 2:
        problems.append("why must be one or two sentences")

    retrieved = set(result["ids"])
    for cited in advice["citations"]:
        if cited not in retrieved:
            problems.append(f"cited {cited}, which was not retrieved")
    if advice["entry_id"] not in retrieved:
        problems.append(f"diagnosed from {advice['entry_id']}, which was not retrieved")
    if not advice["citations"]:
        problems.append("no citations")

    if not isinstance(advice["setup_steps"], list) or len(advice["setup_steps"]) > 3:
        problems.append("setup_steps must contain 0 to 3 items")
    used_ids = {advice["entry_id"]}
    eligible_setup_sources = {
        item["source_id"] for item in eligible_setup_bullets(result)
    }
    overlap_stopwords = {
        "before", "closer", "through", "target", "toward", "towards",
    }
    swing_tokens = {
        token.lower()
        for token in re.findall(r"\b[a-zA-Z']+\b", advice["swing_thought"])
        if len(token) > 5 and token.lower() not in overlap_stopwords
    }
    for i, item in enumerate(advice["setup_steps"]):
        source_id = item["source_id"]
        if source_id not in retrieved:
            problems.append(
                f"setup_steps[{i}] sourced from {source_id}, which was not retrieved"
            )
        if source_id not in eligible_setup_sources:
            problems.append(
                f"setup_steps[{i}] source {source_id} has no eligible setup bullet"
            )
        used_ids.add(source_id)
        step_lower = item["step"].lower()
        if "grip" in step_lower and "grip down" not in step_lower:
            problems.append(
                f"setup_steps[{i}] changes the grip without gripping down"
            )
        step_tokens = {
            token.lower()
            for token in re.findall(r"\b[a-zA-Z']+\b", item["step"])
            if len(token) > 5 and token.lower() not in overlap_stopwords
        }
        overlap = swing_tokens & step_tokens
        if overlap:
            problems.append(
                f"setup_steps[{i}] repeats the swing thought: {', '.join(sorted(overlap))}"
            )

    followup = advice["if_it_keeps_happening"]
    followup_source = followup.get("source_id")
    if followup_source is not None and followup_source not in retrieved:
        problems.append(
            f"if_it_keeps_happening sourced from {followup_source}, which was not retrieved"
        )
    if followup["text"] and not followup_source:
        problems.append("if_it_keeps_happening has text but no source_id")
    if not followup["text"] and followup_source:
        problems.append("if_it_keeps_happening has a source_id but no text")
    if followup_source:
        used_ids.add(followup_source)

    primary_entry = next(
        entry for entry in result["entries"] if entry["id"] == advice["entry_id"]
    )
    expected_alternatives = {
        confused_id
        for row in differentials.get(advice["entry_id"], [])
        for confused_id in row["confused_ids"]
        if confused_id in retrieved
    }
    if expected_alternatives and followup_source not in expected_alternatives:
        problems.append(
            "if_it_keeps_happening must use a retrieved confusable entry before compensation risk"
        )
    elif not expected_alternatives and compensation_risk(primary_entry):
        if followup_source != advice["entry_id"]:
            problems.append(
                "if_it_keeps_happening must use the primary entry's compensation risk"
            )
    elif not expected_alternatives and not compensation_risk(primary_entry):
        if followup["text"] or followup_source:
            problems.append(
                "if_it_keeps_happening must be empty when no lookup source exists"
            )

    missing_citations = used_ids - set(advice["citations"])
    for source_id in sorted(missing_citations):
        problems.append(f"used {source_id} but did not cite it")

    total = sum(word_count(text) for _, text in all_text_fields(advice))
    if total > 140:
        problems.append(f"answer is {total} words, limit is 140")

    return problems


def answer(query, retriever, differentials, model=MODEL, k=5, retry=True, q_vec=None):
    result = retriever.search(query, k=k, q_vec=q_vec)
    refusal = decide_refusal(result)
    if refusal["refused"]:
        return {"query": query, "retrieved": result["ids"], **refusal,
                "top_dense_sim": round(result["top_dense_sim"], 3)}

    advice, usage = generate(query, result, differentials, model=model)
    problems = validate(advice, result, differentials)
    retried = False

    # One repair attempt. Cheaper than accepting a rule violation, and the
    # model fixes its own output reliably when told exactly what is wrong.
    if problems and retry:
        retried = True
        advice, usage2 = generate(
            query, result, differentials, model=model, problems=problems, previous=advice
        )
        problems = validate(advice, result, differentials)
        usage.input_tokens += usage2.input_tokens
        usage.output_tokens += usage2.output_tokens

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


# ------------------------------------------------------------------ cli

def print_answer(a, plain=False):
    if not plain:
        print(f"\nQuery: {a['query']}")
        print(f"Retrieved: {', '.join(a['retrieved'])}  (top dense sim {a['top_dense_sim']})")
    if a["refused"]:
        if plain:
            print(a["message"])
        else:
            print(f"\nDECLINED ({a['kind']})")
            print(f"  {a['message']}")
        return
    ad = a["advice"]
    prefix = "" if plain else "  "
    if not plain:
        print()
    print(f"{prefix}What happened: {ad['what_happened']}")
    print(f"{prefix}Before your next shot:")
    if ad["setup_steps"]:
        for item in ad["setup_steps"]:
            print(f"{prefix}- {item['step']} [{item['source_id']}]")
    else:
        print(f"{prefix}None.")
    print(f"{prefix}Swing thought: {ad['swing_thought']}")
    print(f"{prefix}Why: {ad['why']}")
    followup = ad["if_it_keeps_happening"]
    if followup["text"]:
        print(f"{prefix}If it keeps happening: {followup['text']} [{followup['source_id']}]")
    else:
        print(f"{prefix}If it keeps happening:")
    print(f"{prefix}Sources: {', '.join(ad['citations'])}")
    if a["validation_problems"] and not plain:
        print("\n  VALIDATION FAILURES:")
        for p in a["validation_problems"]:
            print(f"    - {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, nargs="+")
    ap.add_argument("--query")
    ap.add_argument("--evals")
    ap.add_argument("--eval-mode", action="store_true")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default="generation_results.json")
    ap.add_argument(
        "--plain",
        action="store_true",
        help="Print only the answer, without query or retrieval diagnostics.",
    )
    args = ap.parse_args()

    if args.query and args.plain:
        with contextlib.redirect_stderr(io.StringIO()):
            retriever = Retriever(args.corpus)
            differentials = parse_differentials(args.corpus)
            result = answer(args.query, retriever, differentials, model=args.model)
        print_answer(result, plain=True)
        return

    retriever = Retriever(args.corpus)
    differentials = parse_differentials(args.corpus)

    if args.query:
        print_answer(answer(args.query, retriever, differentials, model=args.model))
        return

    if not args.eval_mode or not args.evals:
        sys.exit("Give --query, or --evals with --eval-mode")

    queries = parse_evals(args.evals)
    if args.limit:
        queries = queries[: args.limit]

    print("Embedding all queries once...", file=sys.stderr)
    q_vecs = embed([q["query"] for q in queries])

    results = []
    for i, q in enumerate(queries, 1):
        a = answer(
            q["query"], retriever, differentials, model=args.model, q_vec=q_vecs[i - 1]
        )
        a["subset"] = q["subset"]
        a["n"] = q["n"]
        a["should_refuse"] = q["expects_nothing"]
        results.append(a)
        print(f"  {i}/{len(queries)}", file=sys.stderr)

    answered = [r for r in results if not r["refused"]]
    refused = [r for r in results if r["refused"]]
    should = [r for r in results if r["should_refuse"]]

    correct_refusals = sum(1 for r in should if r["refused"])
    wrong_refusals = sum(1 for r in refused if not r["should_refuse"])
    with_problems = [r for r in answered if r["validation_problems"]]

    print(f"\n{'='*60}")
    print(f"Answered: {len(answered)}   Refused: {len(refused)}")
    print(f"Correct refusals: {correct_refusals}/{len(should)}")
    print(f"False refusals: {wrong_refusals}")
    retried = sum(1 for r in answered if r.get("retried"))
    print(f"Repaired on retry: {retried}")
    print(f"Validation failures after retry: {len(with_problems)}/{len(answered)}")
    answer_word_counts = [
        sum(word_count(text) for _, text in all_text_fields(r["advice"]))
        for r in answered
    ]
    with_setup = sum(1 for r in answered if r["advice"]["setup_steps"])
    if answer_word_counts:
        print(f"Average answer words: {sum(answer_word_counts) / len(answer_word_counts):.1f}")
        print(f"Maximum answer words: {max(answer_word_counts)}")
    print(f"Answers with setup steps: {with_setup}/{len(answered)}")

    false_ref = [r for r in refused if not r["should_refuse"]]
    if false_ref:
        print(f"\nFALSE REFUSALS ({len(false_ref)}):")
        for r in false_ref:
            print(f"  [{r['subset']} #{r['n']}] {r['query'][:60]}")
            print(f"      kind={r['kind']} sim={r['top_dense_sim']} top={r['retrieved'][0]}")
    if with_problems:
        print("\nFailures:")
        for r in with_problems:
            print(f"  [{r['subset']} #{r['n']}] {', '.join(r['validation_problems'])}")
    tin = sum(r["tokens"]["in"] for r in answered)
    tout = sum(r["tokens"]["out"] for r in answered)
    print(f"\nTokens: {tin:,} in, {tout:,} out across {len(answered)} generations")

    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"Written to {args.out}")


if __name__ == "__main__":
    main()
