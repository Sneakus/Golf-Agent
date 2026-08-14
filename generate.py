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
    "description": "Return one short piece of golf advice grounded in the retrieved corpus entries.",
    "input_schema": {
        "type": "object",
        "properties": {
            "diagnosis": {
                "type": "string",
                "description": "The fault, named in plain words as a golfer would say it. Not the entry code.",
            },
            "entry_id": {
                "type": "string",
                "description": "The corpus entry ID this diagnosis comes from, e.g. F007.",
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
                "description": ("One short sentence on what caused it, under 25 words. "
                                "Plain words a golfer would use. Say 'the club hit the ground "
                                "before the ball' not 'the low point was behind the ball'. "
                                "Say 'you were swinging down too steeply' not 'the attack "
                                "angle was steep'. Never use coaching jargon."),
            },
            "uncertainty": {
                "type": "string",
                "description": ("If the retrieved entries include a plausible alternative "
                                "diagnosis, say so in one sentence under 30 words, and give "
                                "the test that separates them. Plain words. Empty string if "
                                "the diagnosis is clear."),
            },
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entry IDs used. Every claim must come from these.",
            },
        },
        "required": ["diagnosis", "entry_id", "swing_thought", "why", "uncertainty", "citations"],
    },
}

SYSTEM = """You are the advice layer of a golf shot-logging tool.

You will be given a golfer's description of a shot and the corpus entries retrieved for it.

Rules, in order of importance:

1. Use ONLY the retrieved entries. If they do not support an answer, say so rather than
   drawing on general golf knowledge. Never invent a cause or a fix.
2. ONE swing thought. Never two. The golfer is standing over a ball.
3. Describe the intended effect, not the body part. "Feel the club brush the grass after
   the ball" not "shift your weight forward and keep your chest down".
4. Plain words. Never use these terms, use the plain version instead:
     low point            -> where the club reaches the bottom of its arc
     attack angle         -> how steeply you are swinging down
     face-to-path         -> where the face points against where the club is travelling
     dynamic loft         -> how much loft the club had at impact
     spin loft, club path, smash factor, gear effect, d-plane -> avoid entirely
   The golfer asked what went wrong, not for a physics lesson.
5. If the retrieved entries suggest more than one plausible cause, say which alternative
   it might be. Stating uncertainty is better than false confidence.
6. Short. A sentence or two per field.

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

def generate(query, result, model=MODEL, problems=None, previous=None):
    import anthropic
    client = anthropic.Anthropic()

    context = "\n\n---\n\n".join(
        f"[{e['id']}] {e['name']}\n{e['text']}" for e in result["entries"]
    )
    user = (f"Golfer's description of the shot:\n{query}\n\n"
            f"Retrieved corpus entries:\n\n{context}")

    if problems:
        user += ("\n\nYour previous answer broke these rules:\n"
                 + "\n".join(f"  - {p}" for p in problems)
                 + f"\n\nPrevious answer: {json.dumps(previous)}"
                 + "\n\nFix only what is listed. Keep everything else.")

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

def validate(advice, result):
    """Programmatic guardrails. Anything here is a hard failure, not a style note."""
    problems = []

    words = advice["swing_thought"].split()
    if len(words) > 15:
        problems.append(f"swing_thought is {len(words)} words, limit is 15")

    # one thought only: a second imperative joined by 'and then', 'also', ';'
    if re.search(r"\b(and then|also|as well as|secondly)\b|;", advice["swing_thought"], re.I):
        problems.append("swing_thought looks like more than one instruction")

    blob = f"{advice['swing_thought']} {advice['why']} {advice['uncertainty']}".lower()
    for term in BANNED_JARGON:
        if term in blob:
            problems.append(f"mechanical jargon in output: '{term}'")

    retrieved = set(result["ids"])
    for cited in advice["citations"]:
        if cited not in retrieved:
            problems.append(f"cited {cited}, which was not retrieved")
    if advice["entry_id"] not in retrieved:
        problems.append(f"diagnosed from {advice['entry_id']}, which was not retrieved")
    if not advice["citations"]:
        problems.append("no citations")

    return problems


def answer(query, retriever, model=MODEL, k=5, retry=True, q_vec=None):
    result = retriever.search(query, k=k, q_vec=q_vec)
    refusal = decide_refusal(result)
    if refusal["refused"]:
        return {"query": query, "retrieved": result["ids"], **refusal,
                "top_dense_sim": round(result["top_dense_sim"], 3)}

    advice, usage = generate(query, result, model=model)
    problems = validate(advice, result)
    retried = False

    # One repair attempt. Cheaper than accepting a rule violation, and the
    # model fixes its own output reliably when told exactly what is wrong.
    if problems and retry:
        retried = True
        advice, usage2 = generate(query, result, model=model, problems=problems,
                                  previous=advice)
        problems = validate(advice, result)
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

def print_answer(a):
    print(f"\nQuery: {a['query']}")
    print(f"Retrieved: {', '.join(a['retrieved'])}  (top dense sim {a['top_dense_sim']})")
    if a["refused"]:
        print(f"\nDECLINED ({a['kind']})")
        print(f"  {a['message']}")
        return
    ad = a["advice"]
    print(f"\n  {ad['diagnosis']}  [{ad['entry_id']}]")
    print(f"  Try this: {ad['swing_thought']}")
    print(f"  Why: {ad['why']}")
    if ad["uncertainty"]:
        print(f"  Note: {ad['uncertainty']}")
    print(f"  Sources: {', '.join(ad['citations'])}")
    if a["validation_problems"]:
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
    args = ap.parse_args()

    retriever = Retriever(args.corpus)

    if args.query:
        print_answer(answer(args.query, retriever, model=args.model))
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
        a = answer(q["query"], retriever, model=args.model, q_vec=q_vecs[i - 1])
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
