#!/usr/bin/env python3
"""
Golf corpus retrieval eval harness.

Baseline version: embeddings only, no reranking, no metadata filtering.
Run this first to get your baseline row in the results log.

Setup:
    pip install openai numpy
    export OPENAI_API_KEY=sk-...

Usage:
    python eval_harness.py --corpus golf-fault-corpus-v3.md --evals golf-eval-sets-v2.md
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- parsing

ALIAS_LINE_RE = re.compile(r"\*\*How I'd describe it:\*\*\s*(.+)")
ENTRY_RE = re.compile(r"^## ([FPDLSCRXN]\d{3}) - (.+)$", re.M)

def parse_corpus(paths):
    """Split one or more corpus files into one chunk per entry."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    text = "\n\n".join(Path(p).read_text() for p in paths)
    matches = list(ENTRY_RE.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        start = m.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)
        body = text[start:end]
        # An entry ends at the next heading that is not part of it.
        # Guards against the final entry absorbing trailing notes sections.
        tail = re.search(r"\n#{1,2} (?![FPDLSCRXN]\d{3} )", body[len(m.group(0)):])
        if tail:
            body = body[: len(m.group(0)) + tail.start()]
        body = re.sub(r"\n---\s*$", "", body).strip()
        entries.append({
            "id": m.group(1),
            "name": m.group(2).strip(),
            "text": body,
        })
    return entries


# Eval rows look like:  | 14 | query text | L001, not F001 |
EVAL_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|?\s*$", re.M)
ID_RE = re.compile(r"\b([FPDLSCR]\d{3})\b")  # X entries are never an expected answer

def parse_evals(path):
    """Pull query rows out of the eval document, tagged by which subset they sit in."""
    text = Path(path).read_text()
    subset = None
    queries = []
    for line in text.splitlines():
        stripped = line.strip()
        # A top-level heading that is not Set A ends collection
        if stripped.startswith("# ") and "Set A" not in stripped:
            subset = None
            continue
        h = re.match(r"^## (A\d)[:\s]", stripped)
        if h:
            subset = h.group(1)
            continue
        # any other ## heading inside Set A ends the current subset
        if stripped.startswith("## "):
            subset = None
            continue
        if subset is None or not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if not cells[0].isdigit():
            continue  # header or separator row

        num = int(cells[0])
        query = cells[1]
        # Expected entry is the last cell for A1/A2/A4, third cell for A3
        expected_cell = cells[-1]
        expected = ID_RE.findall(expected_cell)

        # "L001, not F001" means only L001 counts as correct
        m_not = re.search(r"\bnot\b", expected_cell, re.I)
        if m_not:
            neg = ID_RE.findall(expected_cell[m_not.end():])
            expected = [e for e in expected if e not in neg]

        queries.append({
            "n": num,
            "subset": subset,
            "query": query,
            "expected": expected,
            "expects_nothing": subset == "A4" or not expected,
        })
    return queries


# ---------------------------------------------------------------- embedding

def entry_text(e, strategy="alias_weighted", repeats=3):
    """Build the string that gets embedded for a corpus entry."""
    if strategy == "whole_entry":
        return e["text"]
    m = ALIAS_LINE_RE.search(e["text"])
    alias = m.group(1).strip() if m else ""
    if strategy == "alias_only":
        return f"{e['name']}. {alias}"
    # alias_weighted: repeat the alias line, then the full entry
    return f"{e['name']}. " + (alias + " ") * repeats + "\n\n" + e["text"]


def embed(texts, model="text-embedding-3-small", batch=64):
    from openai import OpenAI
    client = OpenAI()
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        resp = client.embeddings.create(model=model, input=chunk)
        out.extend([d.embedding for d in resp.data])
        print(f"  embedded {min(i+batch, len(texts))}/{len(texts)}", file=sys.stderr)
    arr = np.array(out, dtype=np.float32)
    # normalise so dot product is cosine similarity
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr


# ---------------------------------------------------------------- scoring

def score(queries, entries, q_vecs, e_vecs, k=5, abstain_threshold=None):
    ids = [e["id"] for e in entries]
    sims = q_vecs @ e_vecs.T          # (n_queries, n_entries)
    order = np.argsort(-sims, axis=1)

    results = []
    for i, q in enumerate(queries):
        ranked = [ids[j] for j in order[i][:k]]
        top_sim = float(sims[i][order[i][0]])

        declined = ranked[0][0] in ("X", "N")
        if abstain_threshold is not None and top_sim < abstain_threshold:
            declined = True

        if q["expects_nothing"]:
            hit1 = hit5 = declined
        else:
            hit1 = (not declined) and ranked[0] in q["expected"]
            hit5 = (not declined) and any(e in ranked for e in q["expected"])

        results.append({
            **q,
            "returned": ranked,
            "top_sim": round(top_sim, 3),
            "hit1": bool(hit1),
            "hit5": bool(hit5),
            "declined": bool(declined),
        })
    return results


def report(results):
    subsets = {}
    for r in results:
        subsets.setdefault(r["subset"], []).append(r)

    print(f"\n{'Subset':<8} {'n':>4} {'hit@1':>8} {'hit@5':>8}")
    print("-" * 32)
    for s in sorted(subsets):
        rows = subsets[s]
        h1 = sum(r["hit1"] for r in rows) / len(rows)
        h5 = sum(r["hit5"] for r in rows) / len(rows)
        print(f"{s:<8} {len(rows):>4} {h1:>8.2f} {h5:>8.2f}")

    answerable = [r for r in results if not r["expects_nothing"]]
    if answerable:
        h1 = sum(r["hit1"] for r in answerable) / len(answerable)
        h5 = sum(r["hit5"] for r in answerable) / len(answerable)
        print("-" * 32)
        print(f"{'ALL':<8} {len(answerable):>4} {h1:>8.2f} {h5:>8.2f}   (answerable only)")

    false_declines = [r for r in results if r["declined"] and not r["expects_nothing"]]
    if false_declines:
        print(f"\n--- FALSE DECLINES ({len(false_declines)}): in-scope queries wrongly refused ---")
        for r in false_declines:
            print(f"  [{r['subset']} #{r['n']}] {r['query'][:60]} -> declined via {r['returned'][0]}")

    print("\n--- MISSES (read every one of these) ---")
    for r in results:
        if not r["hit5"]:
            exp = ", ".join(r["expected"]) or "(nothing)"
            print(f"\n[{r['subset']} #{r['n']}] {r['query'][:80]}")
            print(f"  expected: {exp}")
            print(f"  returned: {', '.join(r['returned'])}  (top sim {r['top_sim']})")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, nargs="+",
                    help="One or more corpus files")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--abstain-threshold", type=float, default=None,
                    help="Top similarity below this counts as declining. Try 0.3 to start.")
    ap.add_argument("--parse-only", action="store_true",
                    help="Check parsing without calling the API")
    ap.add_argument("--strategy", default="alias_weighted",
                    choices=["whole_entry", "alias_only", "alias_weighted"])
    ap.add_argument("--out", default="eval_results.json")
    args = ap.parse_args()

    entries = parse_corpus(args.corpus)
    queries = parse_evals(args.evals)
    print(f"Parsed {len(entries)} corpus entries, {len(queries)} eval queries", file=sys.stderr)

    by_subset = {}
    for q in queries:
        by_subset[q["subset"]] = by_subset.get(q["subset"], 0) + 1
    print(f"  subsets: {by_subset}", file=sys.stderr)

    unresolved = {e for q in queries for e in q["expected"]} - {e["id"] for e in entries}
    if unresolved:
        print(f"  WARNING: eval references entries not in corpus: {sorted(unresolved)}", file=sys.stderr)

    if args.parse_only:
        for e in entries[:3]:
            print(f"\n--- {e['id']} {e['name']} ({len(e['text'])} chars) ---")
            print(e["text"][:200] + "...")
        for q in queries[:5]:
            print(f"\n[{q['subset']} #{q['n']}] {q['query'][:70]} -> {q['expected']}")
        return

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Set OPENAI_API_KEY first.")

    print(f"Embedding corpus (strategy: {args.strategy})...", file=sys.stderr)
    e_vecs = embed([entry_text(e, args.strategy) for e in entries])
    print("Embedding queries...", file=sys.stderr)
    q_vecs = embed([q["query"] for q in queries])

    results = score(queries, entries, q_vecs, e_vecs,
                    k=args.k, abstain_threshold=args.abstain_threshold)
    report(results)

    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
