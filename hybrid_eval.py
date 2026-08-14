#!/usr/bin/env python3
"""
Hybrid retrieval eval: BM25 keyword search fused with dense embeddings.

Dense embeddings handle paraphrase but wash out rare distinctive terms
("hosel", "cart path"). BM25 does the opposite. Fusing them should beat
either alone.

Usage:
    python hybrid_eval.py --corpus golf-fault-corpus-v3.md golf-out-of-scope-entries.md \
                          --evals golf-eval-sets-v2.md
"""

import argparse
import json
import re
import sys
from pathlib import Path

import math
from collections import Counter

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus, parse_evals, embed, entry_text, report


TOKEN_RE = re.compile(r"[a-z0-9']+")

def tokenize(text):
    """Lowercase word tokens, markdown stripped."""
    text = re.sub(r"\*\*|\||#|-\s", " ", text.lower())
    return TOKEN_RE.findall(text)


class BM25:
    """Minimal BM25 Okapi. Rare terms score high, which is exactly what
    dense embeddings wash out."""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in docs]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / self.N
        self.tf = [Counter(d) for d in self.docs]
        df = Counter()
        for d in self.docs:
            for w in set(d):
                df[w] += 1
        self.idf = {w: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                    for w, n in df.items()}

    def get_scores(self, query_tokens):
        out = []
        for i, tf in enumerate(self.tf):
            dl = len(self.docs[i])
            s = 0.0
            for w in query_tokens:
                f = tf.get(w)
                if not f:
                    continue
                s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / (
                     f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            out.append(s)
        return np.array(out)


def rrf(rankings, k=60):
    """
    Reciprocal rank fusion. Combines several ranked lists by scoring each
    item 1/(k + rank). Standard, parameter-light, and does not need the
    two systems' scores to be on the same scale.
    """
    scores = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def hybrid_score(queries, entries, q_vecs, e_vecs, bm25, k=5, rrf_k=60, mode="hybrid"):
    ids = [e["id"] for e in entries]
    dense_sims = q_vecs @ e_vecs.T

    results = []
    for i, q in enumerate(queries):
        dense_order = list(np.argsort(-dense_sims[i]))
        bm25_scores = bm25.get_scores(tokenize(q["query"]))
        bm25_order = list(np.argsort(-bm25_scores))

        if mode == "dense":
            order = dense_order
        elif mode == "bm25":
            order = bm25_order
        else:
            order = rrf([dense_order, bm25_order], k=rrf_k)

        ranked = [ids[j] for j in order[:k]]
        declined = ranked[0][0] in ("X", "N")

        if q["expects_nothing"]:
            hit1 = hit5 = declined
        else:
            hit1 = (not declined) and ranked[0] in q["expected"]
            hit5 = (not declined) and any(e in ranked for e in q["expected"])

        results.append({
            **q,
            "returned": ranked,
            "top_sim": round(float(dense_sims[i][dense_order[0]]), 3),
            "bm25_top": ids[bm25_order[0]],
            "hit1": bool(hit1),
            "hit5": bool(hit5),
            "declined": bool(declined),
        })
    return results


def summarise(name, results):
    subsets = {}
    for r in results:
        subsets.setdefault(r["subset"], []).append(r)
    answerable = [r for r in results if not r["expects_nothing"]]
    h1 = sum(r["hit1"] for r in answerable) / len(answerable)
    h5 = sum(r["hit5"] for r in answerable) / len(answerable)
    subs = {s: sum(r["hit5"] for r in rs) / len(rs) for s, rs in sorted(subsets.items())}
    return (name, h1, h5, subs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, nargs="+")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--rrf-k", type=int, default=60)
    ap.add_argument("--strategy", default="alias_weighted")
    ap.add_argument("--out", default="hybrid_results.json")
    args = ap.parse_args()

    entries = parse_corpus(args.corpus)
    queries = parse_evals(args.evals)
    print(f"{len(entries)} entries, {len(queries)} queries", file=sys.stderr)

    texts = [entry_text(e, args.strategy) for e in entries]
    bm25 = BM25(texts)

    print("Embedding...", file=sys.stderr)
    e_vecs = embed(texts)
    q_vecs = embed([q["query"] for q in queries])

    rows = []
    all_results = {}
    for mode in ("dense", "bm25", "hybrid"):
        res = hybrid_score(queries, entries, q_vecs, e_vecs, bm25,
                           k=args.k, rrf_k=args.rrf_k, mode=mode)
        all_results[mode] = res
        rows.append(summarise(mode, res))

    print("\n" + "=" * 70)
    print(f"{'Mode':<10} {'hit@1':>7} {'hit@5':>7}   {'A1':>5} {'A2':>5} {'A3':>5} {'A4':>5}")
    print("-" * 70)
    for name, h1, h5, subs in rows:
        print(f"{name:<10} {h1:>7.2f} {h5:>7.2f}   "
              f"{subs.get('A1',0):>5.2f} {subs.get('A2',0):>5.2f} "
              f"{subs.get('A3',0):>5.2f} {subs.get('A4',0):>5.2f}")
    print("=" * 70)
    print("Subset columns are hit@5. hit@1 and hit@5 are answerable queries only.")

    print("\n--- HYBRID MISSES ---")
    for r in all_results["hybrid"]:
        if not r["hit5"]:
            exp = ", ".join(r["expected"]) or "(nothing)"
            print(f"\n[{r['subset']} #{r['n']}] {r['query'][:75]}")
            print(f"  expected: {exp}")
            print(f"  returned: {', '.join(r['returned'])}")
            print(f"  bm25 top: {r['bm25_top']}")

    fixed = [r for r in all_results["hybrid"]
             if r["hit5"] and not next(x for x in all_results["dense"] if x["n"] == r["n"])["hit5"]]
    broken = [r for r in all_results["dense"]
              if r["hit5"] and not next(x for x in all_results["hybrid"] if x["n"] == r["n"])["hit5"]]
    print(f"\n--- WHAT HYBRID CHANGED ---")
    print(f"Fixed by hybrid ({len(fixed)}): " + ", ".join(f"#{r['n']}" for r in fixed) or "none")
    print(f"Broken by hybrid ({len(broken)}): " + (", ".join(f"#{r['n']}" for r in broken) or "none"))

    Path(args.out).write_text(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
