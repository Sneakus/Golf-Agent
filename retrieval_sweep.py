#!/usr/bin/env python3
"""Offline retrieval sweep and miss-signal report. Embeddings only, no generation."""

import hashlib
import json
from pathlib import Path

import numpy as np

from eval_harness import parse_corpus, parse_evals, entry_text, embed
from hybrid_eval import BM25, tokenize


def rrf_scores(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return scores


def fuse(dense_order, bm25_order, rrf_k, passed, guarantee):
    scores = rrf_scores([dense_order, bm25_order], k=rrf_k)
    order = sorted(scores, key=scores.get, reverse=True)
    chosen = order[:passed]
    if guarantee:
        for must in (bm25_order[0], dense_order[0]):
            if must not in chosen:
                chosen = chosen[:-1] + [must]
    return chosen, scores, order


def hit_metrics(chosen, expected):
    relevant = set(expected)
    ranks = [i for i, idx in enumerate(chosen) if idx in relevant]
    hit1 = float(bool(chosen) and chosen[0] in relevant)
    hit_passed = float(bool(ranks))
    mrr = 0.0 if not ranks else 1.0 / (ranks[0] + 1)
    return hit1, hit_passed, mrr


def main():
    corpus = ["golf-fault-corpus-v3.md", "golf-out-of-scope-entries.md"]
    entries = parse_corpus(corpus)
    queries = parse_evals("golf-eval-sets-v2.md")
    texts = [entry_text(e) for e in entries]
    ids = [e["id"] for e in entries]
    e_vecs = embed(texts)
    q_vecs = embed([q["query"] for q in queries])
    bm25 = BM25(texts)
    dense = q_vecs @ e_vecs.T

    prepared = []
    for i, q in enumerate(queries):
        d_order = list(np.argsort(-dense[i]))
        b_order = list(np.argsort(-bm25.get_scores(tokenize(q["query"]))))
        prepared.append((q, d_order, b_order, float(dense[i][d_order[0]])))

    baseline_hits = {}
    print("\nSweep (live config is no guarantee, RRF k 60, pass 5)")
    print(f"{'guarantee':<10} {'k':>4} {'pass':>5} {'hit@1':>7} {'hit@pass':>9} "
          f"{'MRR':>7} {'q13':>5} {'q24':>5} lost")
    answerable_n = 0
    for guarantee in (False, True):
        for rrf_k in (10, 20, 60):
            for passed in (5, 7):
                hit1 = hitp = mrr = 0.0
                n = 0
                flags = {}
                hits = set()
                for q, d_order, b_order, _sim in prepared:
                    if q["expects_nothing"]:
                        continue
                    chosen, _scores, _order = fuse(d_order, b_order, rrf_k, passed, guarantee)
                    chosen_ids = [ids[j] for j in chosen]
                    h1, hp, m = hit_metrics(chosen_ids, q["expected"])
                    hit1 += h1
                    hitp += hp
                    mrr += m
                    n += 1
                    if hp:
                        hits.add(q["n"])
                    if q["n"] in (13, 24):
                        flags[q["n"]] = "yes" if hp else "no"
                if not guarantee and rrf_k == 60 and passed == 5:
                    baseline_hits = hits
                    answerable_n = n
                lost = sorted(baseline_hits - hits) if baseline_hits else []
                print(f"{str(guarantee):<10} {rrf_k:>4} {passed:>5} {hit1/n:>7.3f} "
                      f"{hitp/n:>9.3f} {mrr/n:>7.3f} {flags.get(13, ''):>5} "
                      f"{flags.get(24, ''):>5} {lost}")

    print(f"\nAnswerable queries: {answerable_n}")
    print("\nMiss signals")
    print(f"{'n':>4} {'disagree':<10} {'gap':>8} {'dense':>7} query")
    signals = []
    for q, d_order, b_order, sim in prepared:
        scores = rrf_scores([d_order, b_order], k=60)
        order = sorted(scores, key=scores.get, reverse=True)
        gap = scores[order[0]] - scores[order[1]]
        disagree = ids[b_order[0]] != ids[d_order[0]]
        signals.append({
            "n": q["n"], "disagree": disagree, "gap": gap, "dense": sim,
            "expects_nothing": q["expects_nothing"], "query": q["query"],
        })
        print(f"{q['n']:>4} {str(disagree):<10} {gap:>8.4f} {sim:>7.3f} {q['query'][:50]}")

    targets = {13, 24}
    answerable = [s for s in signals if not s["expects_nothing"]]
    print("\nSimple rules that catch both 13 and 24")
    candidates = []
    for gap_max in (0.005, 0.008, 0.01, 0.015, 0.02):
        for dense_max in (0.45, 0.50, 0.55, 0.60, 1.01):
            for need_disagree in (False, True):
                flagged = []
                for s in answerable:
                    if need_disagree and not s["disagree"]:
                        continue
                    if s["gap"] > gap_max or s["dense"] > dense_max:
                        continue
                    flagged.append(s["n"])
                if targets <= set(flagged):
                    others = [n for n in flagged if n not in targets]
                    candidates.append((len(others), gap_max, dense_max, need_disagree, others))
    if not candidates:
        print("No threshold on disagreement, fused gap and dense similarity catches both.")
    else:
        candidates.sort()
        others, gap_max, dense_max, need_disagree, other_ns = candidates[0]
        print(f"Smallest extra set: disagree={need_disagree}, gap<={gap_max}, "
              f"dense<={dense_max}: flags 13 and 24 plus {others} others {other_ns}")

    Path("retrieval_sweep.json").write_text(json.dumps({
        "signals": signals,
    }, indent=2))


if __name__ == "__main__":
    main()
