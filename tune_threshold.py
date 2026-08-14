#!/usr/bin/env python3
"""
Derive the refusal threshold from the eval data instead of guessing.

The threshold decides when the tool declines rather than diagnosing. Set it
too high and you refuse real questions; too low and you answer things you
should not. This sweeps every candidate value and reports the trade-off, so
the number is chosen from evidence rather than picked.

Usage:
    python tune_threshold.py --corpus golf-fault-corpus-v3.md golf-out-of-scope-entries.md \
                             --evals golf-eval-sets-v2.md
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus, parse_evals, entry_text, embed
from hybrid_eval import BM25, tokenize, rrf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, nargs="+")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    entries = parse_corpus(args.corpus)
    queries = parse_evals(args.evals)
    texts = [entry_text(e) for e in entries]
    ids = [e["id"] for e in entries]

    bm25 = BM25(texts)
    e_vecs = embed(texts)
    q_vecs = embed([q["query"] for q in queries])

    rows = []
    for i, q in enumerate(queries):
        dense = e_vecs @ q_vecs[i]
        d_order = list(np.argsort(-dense))
        b_order = list(np.argsort(-bm25.get_scores(tokenize(q["query"]))))
        order = rrf([d_order, b_order])
        top_id = ids[order[0]]
        rows.append({
            "n": q["n"], "subset": q["subset"], "query": q["query"],
            "top_id": top_id,
            "top_dense": float(dense[d_order[0]]),
            "should_refuse": q["expects_nothing"],
            # an entry-based refusal happens regardless of threshold
            "entry_refusal": top_id[0] in ("X", "N"),
        })

    # Only queries not already settled by an X or N entry depend on the threshold
    threshold_relevant = [r for r in rows if not r["entry_refusal"]]

    answerable = [r for r in threshold_relevant if not r["should_refuse"]]
    should_refuse = [r for r in threshold_relevant if r["should_refuse"]]

    print(f"\n{len(rows)} queries. {len(rows) - len(threshold_relevant)} settled by "
          f"X or N entry regardless of threshold.")
    print(f"{len(threshold_relevant)} depend on the similarity threshold: "
          f"{len(answerable)} answerable, {len(should_refuse)} should refuse.\n")

    if answerable:
        sims = sorted(r["top_dense"] for r in answerable)
        print(f"Answerable queries, top dense similarity:")
        print(f"  min {sims[0]:.3f}   p5 {np.percentile(sims,5):.3f}   "
              f"median {np.median(sims):.3f}   max {sims[-1]:.3f}")
        print(f"  five lowest: " + ", ".join(f"{s:.3f}" for s in sims[:5]))
    if should_refuse:
        sims2 = sorted((r["top_dense"] for r in should_refuse), reverse=True)
        print(f"\nShould-refuse queries not caught by an entry, top dense similarity:")
        print(f"  " + ", ".join(f"{s:.3f}" for s in sims2))

    print(f"\n{'Threshold':>10} {'False refusals':>15} {'Missed refusals':>16}")
    print("-" * 45)
    best = None
    for t in np.arange(0.20, 0.61, 0.01):
        false_ref = sum(1 for r in answerable if r["top_dense"] < t)
        missed = sum(1 for r in should_refuse if r["top_dense"] >= t)
        mark = ""
        if false_ref == 0 and (best is None or t > best):
            best = t
            mark = ""
        print(f"{t:>10.2f} {false_ref:>15} {missed:>16}{mark}")

    # highest threshold with no false refusals, then back off for headroom
    safe = max((t for t in np.arange(0.20, 0.61, 0.01)
                if not any(r["top_dense"] < t for r in answerable)), default=0.20)
    margin = round(safe - 0.03, 2)

    print(f"\nHighest threshold with zero false refusals: {safe:.2f}")
    print(f"Recommended, with 0.03 headroom for queries not in this eval set: {margin:.2f}")
    print("\nNote: the X and N entries do most of the abstention work. The threshold is a "
          "backstop for queries that are in scope but too vague to diagnose, so it should "
          "be set low enough to almost never fire on a real question.")


if __name__ == "__main__":
    main()
