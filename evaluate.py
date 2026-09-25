#!/usr/bin/env python3
"""
Canonical evaluation for the golf fault corpus.

Supersedes eval_harness.py and hybrid_eval.py as the thing you run.
Those remain as libraries for parsing and embedding.

Reports the standard IR metric set with bootstrap confidence intervals,
plus latency and cost, and can gate CI on a minimum score.

Usage:
    python evaluate.py --corpus golf-fault-corpus-v3.md golf-out-of-scope-entries.md \
                       --evals golf-eval-sets-v2.md

    # in CI, fail the build if retrieval regresses
    python evaluate.py --corpus ... --evals ... --fail-under-recall5 0.90
"""

import argparse
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus, parse_evals, entry_text
from hybrid_eval import BM25, tokenize, rrf

# text-embedding-3-small list price per million tokens.
# Verify against current pricing before quoting this figure anywhere.
EMBED_COST_PER_MTOK = 0.02


# ----------------------------------------------------------------- metrics

def reciprocal_rank(ranked, relevant):
    for i, doc in enumerate(ranked, start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, relevant, k):
    """Binary relevance. One or more relevant entries per query."""
    dcg = sum(1.0 / math.log2(i + 1)
              for i, doc in enumerate(ranked[:k], start=1) if doc in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def per_query_metrics(ranked, relevant, k):
    return {
        "hit@1": float(ranked[0] in relevant),
        f"hit@{k}": float(any(d in relevant for d in ranked[:k])),
        f"recall@{k}": len(set(ranked[:k]) & relevant) / len(relevant),
        "precision@1": float(ranked[0] in relevant),
        "mrr": reciprocal_rank(ranked, relevant),
        f"ndcg@{k}": ndcg_at_k(ranked, relevant, k),
    }


def wilson_ci(successes, n, z=1.959963984540054):
    """95% Wilson interval for a proportion. Stays wide when every item passes."""
    if n <= 0:
        return (0.0, 0.0)
    phat = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (phat + z2 / (2 * n)) / denom
    margin = z * ((phat * (1 - phat) + z2 / (4 * n)) / n) ** 0.5 / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def proportion_ci(values):
    """Bootstrap, except an all-pass result uses the Wilson interval."""
    if values and all(value == 1.0 for value in values):
        return wilson_ci(len(values), len(values))
    return bootstrap_ci(values)


def bootstrap_ci(values, n=10000, alpha=0.05, seed=0):
    """95% percentile bootstrap CI for a mean. Standard in the IR literature."""
    if not values:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    means = arr[rng.integers(0, len(arr), size=(n, len(arr)))].mean(axis=1)
    return (float(np.percentile(means, 100 * alpha / 2)),
            float(np.percentile(means, 100 * (1 - alpha / 2))))


# ----------------------------------------------------------------- run

def retrieve(queries, entries, q_vecs, e_vecs, bm25, k, mode="hybrid", rrf_k=60):
    ids = [e["id"] for e in entries]
    dense = q_vecs @ e_vecs.T
    out = []
    for i, q in enumerate(queries):
        t0 = time.perf_counter()
        d_order = list(np.argsort(-dense[i]))
        b_order = list(np.argsort(-bm25.get_scores(tokenize(q["query"]))))
        if mode == "dense":
            order = d_order
        elif mode == "bm25":
            order = b_order
        else:
            order = rrf([d_order, b_order], k=rrf_k)
        latency_ms = (time.perf_counter() - t0) * 1000

        ranked = [ids[j] for j in order[:k]]
        out.append({**q, "ranked": ranked, "latency_ms": round(latency_ms, 3)})
    return out


def evaluate(retrieved, k):
    answerable = [r for r in retrieved if not r["expects_nothing"]]
    non_fault = [r for r in retrieved if r["expects_nothing"]]

    rows = []
    for r in answerable:
        relevant = set(r["expected"])
        declined = r["ranked"][0][0] in ("X", "N")
        m = per_query_metrics(r["ranked"], relevant, k)
        if declined:                      # a false decline scores zero throughout
            m = {key: 0.0 for key in m}
        rows.append({**r, **m, "declined": declined})

    # abstention scored separately: correct behaviour is an X or N entry on top
    abst = [{**r, "correct": r["ranked"][0][0] in ("X", "N")} for r in non_fault]

    return rows, abst


def report(rows, abst, k, mode, embed_tokens):
    metrics = ["hit@1", f"hit@{k}", f"recall@{k}", "mrr", f"ndcg@{k}"]

    print(f"\n{'='*72}")
    print(f"Retrieval: {mode}   |   {len(rows)} answerable, {len(abst)} non-fault")
    print(f"{'='*72}")
    print(f"{'Metric':<12} {'Score':>7}   {'95% CI':>16}   {'Interpretation'}")
    print("-" * 72)

    summary = {}
    for m in metrics:
        vals = [r[m] for r in rows]
        mean = sum(vals) / len(vals)
        lo, hi = proportion_ci(vals)
        summary[m] = {"score": round(mean, 3), "ci": [round(lo, 3), round(hi, 3)]}
        note = {
            "hit@1": "right entry ranked first",
            f"hit@{k}": "right entry in top " + str(k),
            f"recall@{k}": "share of relevant entries found",
            "mrr": "how high the first hit lands",
            f"ndcg@{k}": "rank-weighted quality",
        }[m]
        print(f"{m:<12} {mean:>7.3f}   [{lo:.3f}, {hi:.3f}]   {note}")

    if k > 5 and rows:
        vals = [0.0 if r["declined"] else float(any(
            doc in set(r["expected"]) for doc in r["ranked"][:5])) for r in rows]
        mean = sum(vals) / len(vals)
        lo, hi = proportion_ci(vals)
        summary["hit@5"] = {"score": round(mean, 3), "ci": [round(lo, 3), round(hi, 3)]}
        print(f"{'hit@5':<12} {mean:>7.3f}   [{lo:.3f}, {hi:.3f}]   right entry in top 5")

    correct = sum(a["correct"] for a in abst)
    print(f"{'abstention':<12} {correct/len(abst):>7.3f}   {'':>16}   "
          f"{correct}/{len(abst)} correctly declined")
    summary["abstention"] = {"score": round(correct / len(abst), 3),
                             "n": len(abst)}

    # subset breakdown
    subsets = {}
    for r in rows:
        subsets.setdefault(r["subset"], []).append(r)
    print(f"\n{'Subset':<8} {'n':>4} {'hit@1':>7} {'hit@'+str(k):>7} {'mrr':>7}")
    print("-" * 40)
    for s in sorted(subsets):
        rs = subsets[s]
        print(f"{s:<8} {len(rs):>4} "
              f"{sum(r['hit@1'] for r in rs)/len(rs):>7.2f} "
              f"{sum(r[f'hit@{k}'] for r in rs)/len(rs):>7.2f} "
              f"{sum(r['mrr'] for r in rs)/len(rs):>7.2f}")
        summary.setdefault("subsets", {})[s] = {
            "n": len(rs),
            "hit@1": round(sum(r["hit@1"] for r in rs) / len(rs), 3),
            f"hit@{k}": round(sum(r[f"hit@{k}"] for r in rs) / len(rs), 3),
        }

    lat = sorted(r["latency_ms"] for r in rows)
    p50 = lat[len(lat) // 2]
    p95 = lat[int(len(lat) * 0.95)]
    cost = embed_tokens / 1e6 * EMBED_COST_PER_MTOK
    print(f"\nRetrieval latency (fusion only, embeddings excluded): "
          f"p50 {p50:.2f} ms, p95 {p95:.2f} ms")
    print(f"Embedding cost this run: ~${cost:.4f} ({embed_tokens:,} tokens)")
    summary["latency_ms"] = {"p50": round(p50, 3), "p95": round(p95, 3)}
    summary["embed_cost_usd"] = round(cost, 5)

    false_declines = [r for r in rows if r["declined"]]
    if false_declines:
        print(f"\nFALSE DECLINES ({len(false_declines)}):")
        for r in false_declines:
            print(f"  [{r['subset']} #{r['n']}] {r['query'][:60]}")
    summary["false_declines"] = len(false_declines)

    print(f"\n--- MISSES ---")
    misses = [r for r in rows if not r[f"hit@{k}"]]
    for r in misses:
        print(f"[{r['subset']} #{r['n']}] {r['query'][:70]}")
        print(f"  expected {', '.join(r['expected'])} | got {', '.join(r['ranked'])}")
    for a in abst:
        if not a["correct"]:
            print(f"[{a['subset']} #{a['n']}] {a['query'][:70]}")
            print(f"  should have declined | got {', '.join(a['ranked'])}")

    print(f"\nNote on significance: {len(rows)} answerable queries. One query is worth "
          f"{100/len(rows):.1f} points, so differences smaller than the CI width are "
          f"not meaningful. Treat small gaps as directional.")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, nargs="+")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--mode", default="hybrid", choices=["dense", "bm25", "hybrid"])
    ap.add_argument("--strategy", default="alias_weighted")
    ap.add_argument("--rrf-k", type=int, default=60)
    ap.add_argument("--out", default="eval_summary.json")
    ap.add_argument("--label", default="", help="What changed, for the results log")
    ap.add_argument("--fail-under-recall5", type=float, default=None,
                    help="Exit non-zero if recall@k drops below this. For CI.")
    args = ap.parse_args()

    entries = parse_corpus(args.corpus)
    queries = parse_evals(args.evals)
    texts = [entry_text(e, args.strategy) for e in entries]

    from eval_harness import embed
    e_vecs = embed(texts)
    q_vecs = embed([q["query"] for q in queries])
    embed_tokens = sum(len(t) for t in texts + [q["query"] for q in queries]) // 4

    bm25 = BM25(texts)
    retrieved = retrieve(queries, entries, q_vecs, e_vecs, bm25,
                         k=args.k, mode=args.mode, rrf_k=args.rrf_k)
    rows, abst = evaluate(retrieved, args.k)
    summary = report(rows, abst, args.k, args.mode, embed_tokens)

    summary["meta"] = {
        "date": str(date.today()),
        "label": args.label,
        "mode": args.mode,
        "strategy": args.strategy,
        "k": args.k,
        "entries": len(entries),
        "queries": len(queries),
    }
    Path(args.out).write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written to {args.out}")

    if args.fail_under_recall5 is not None:
        got = summary[f"recall@{args.k}"]["score"]
        if got < args.fail_under_recall5:
            print(f"\nFAIL: recall@{args.k} {got:.3f} is below "
                  f"threshold {args.fail_under_recall5}")
            sys.exit(1)
        print(f"\nPASS: recall@{args.k} {got:.3f} meets threshold "
              f"{args.fail_under_recall5}")


if __name__ == "__main__":
    main()
