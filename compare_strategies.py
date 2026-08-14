#!/usr/bin/env python3
"""
Compare embedding strategies on the golf corpus.

Tests whether the "How I'd describe it" alias line is being diluted by the
rest of the entry text. Run this after the baseline.

Usage:
    python compare_strategies.py --corpus golf-fault-corpus-v3.md --evals golf-eval-sets-v2.md
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus, parse_evals, embed, score


ALIAS_RE = re.compile(r"\*\*How I'd describe it:\*\*\s*(.+)")
WHATIS_RE = re.compile(r"\*\*What it is:\*\*\s*(.+)")


def strategies(entries):
    """Return {name: [text per entry]} for each embedding strategy."""
    out = {}

    # 1. Whole entry (the baseline)
    out["whole_entry"] = [e["text"] for e in entries]

    # 2. Alias line only
    alias_only = []
    for e in entries:
        m = ALIAS_RE.search(e["text"])
        alias_only.append(f"{e['name']}. {m.group(1)}" if m else e["name"])
    out["alias_only"] = alias_only

    # 3. Name + alias + one-line definition
    summary = []
    for e in entries:
        a = ALIAS_RE.search(e["text"])
        w = WHATIS_RE.search(e["text"])
        parts = [e["name"]]
        if a:
            parts.append(a.group(1))
        if w:
            parts.append(w.group(1))
        summary.append(". ".join(parts))
    out["name_alias_def"] = summary

    # 4. Alias line repeated, then whole entry (weighting without losing detail)
    weighted = []
    for e in entries:
        m = ALIAS_RE.search(e["text"])
        alias = m.group(1) if m else ""
        weighted.append(f"{e['name']}. {alias} {alias} {alias}\n\n{e['text']}")
    out["alias_weighted"] = weighted

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--evals", required=True)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    entries = parse_corpus(args.corpus)
    queries = parse_evals(args.evals)
    answerable = [q for q in queries if not q["expects_nothing"]]
    print(f"{len(entries)} entries, {len(answerable)} answerable queries\n", file=sys.stderr)

    print("Embedding queries once...", file=sys.stderr)
    q_vecs = embed([q["query"] for q in answerable])

    variants = strategies(entries)
    rows = []
    for name, texts in variants.items():
        avg_len = sum(len(t) for t in texts) / len(texts)
        print(f"\nEmbedding corpus as '{name}' (avg {avg_len:.0f} chars)...", file=sys.stderr)
        e_vecs = embed(texts)
        res = score(answerable, entries, q_vecs, e_vecs, k=args.k)

        by_subset = {}
        for r in res:
            by_subset.setdefault(r["subset"], []).append(r)

        overall1 = sum(r["hit1"] for r in res) / len(res)
        overall5 = sum(r["hit5"] for r in res) / len(res)
        sub_scores = {s: sum(r["hit5"] for r in rs) / len(rs)
                      for s, rs in sorted(by_subset.items())}
        rows.append((name, avg_len, overall1, overall5, sub_scores))

    print("\n\n" + "=" * 78)
    print(f"{'Strategy':<18} {'chars':>7} {'hit@1':>7} {'hit@5':>7}   {'A1':>5} {'A2':>5} {'A3':>5}")
    print("-" * 78)
    for name, ln, h1, h5, subs in rows:
        a1 = subs.get("A1", 0)
        a2 = subs.get("A2", 0)
        a3 = subs.get("A3", 0)
        print(f"{name:<18} {ln:>7.0f} {h1:>7.2f} {h5:>7.2f}   {a1:>5.2f} {a2:>5.2f} {a3:>5.2f}")
    print("=" * 78)
    print("\nSubset columns are hit@5. A1 is your own voice and is the number that matters most.")


if __name__ == "__main__":
    main()
