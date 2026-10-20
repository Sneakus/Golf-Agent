#!/usr/bin/env python3
"""
Export the range game's coaching library from a Set G generation run.

Reads a generation results file written by generate.py's eval mode on
golf-game-queries.md, and writes the answers the game will show. Makes no
network calls.

Only answers that passed validation and whose diagnosis matched the expected
entries are exported. Every other query is listed, with its reason, in the
excluded file.

Usage:
    python export_coach_library.py generation_results-2026-10-20-120000.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ENTRY_TAG_RE = re.compile(r"\s*\[[FPDLSCRXN]\d{3}\]")
ID_RE = re.compile(r"\b([FPDLSCR]\d{3})\b")
GROUP_RE = re.compile(r"^## (A\d): (.+)$")
STAMP_RE = re.compile(r"generation_results-(\d{4}-\d{2}-\d{2})-\d{6}\.json$")


def parse_game_queries(path):
    """Rows of the Set G file, with the shot name and club group the game uses."""
    queries = []
    group = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        heading = GROUP_RE.match(stripped)
        if heading:
            group = heading.group(2).strip()
            continue
        if stripped.startswith("#"):
            group = None
            continue
        if group is None or not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4 or not cells[0].isdigit():
            continue
        queries.append({
            "n": int(cells[0]),
            "query": cells[1],
            "shot": cells[2],
            "club_group": group,
            "expected": ID_RE.findall(cells[3]),
        })
    return queries


def clean(text):
    """Strip entry tags and replace em and en dashes."""
    text = ENTRY_TAG_RE.sub("", text or "")
    text = text.replace(" — ", ", ").replace(" – ", ", ")
    text = text.replace("—", "-").replace("–", "-")
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def run_date(results_path, override=None):
    if override:
        return override
    stamp = STAMP_RE.search(Path(results_path).name)
    if stamp:
        return stamp.group(1)
    return datetime.fromtimestamp(Path(results_path).stat().st_mtime).strftime("%Y-%m-%d")


def exclusion_reason(query, row):
    if row is None:
        return "no answer in the results file"
    if row.get("query") != query["query"]:
        return "results row has different query text, so it is not from this Set G file"
    if row.get("refused"):
        return f"refused ({row.get('kind', 'unknown')})"
    if row.get("clarified"):
        return "clarifying question instead of an answer"
    problems = row.get("validation_problems") or []
    if problems:
        return "failed validation: " + "; ".join(problems)
    advice = row.get("advice")
    if not advice:
        return "no advice in the results row"
    if advice.get("entry_id") not in query["expected"]:
        return (f"diagnosed {advice.get('entry_id')}, expected "
                f"{' or '.join(query['expected'])}")
    return None


def library_entry(query, row, date):
    advice = row["advice"]
    entry_id = advice["entry_id"]
    return {
        "shot": query["shot"],
        "club_group": query["club_group"],
        "query_n": query["n"],
        "what_happened": clean(advice["what_happened"]),
        "setup_steps": [clean(step["text"]) for step in advice.get("setup_steps") or []],
        "thought_label": "Key thought" if entry_id[:1] in ("S", "C") else "Swing thought",
        "thought": clean(advice["swing_thought"]),
        "why": clean(advice["why"]),
        "if_it_keeps_happening": clean(advice.get("if_it_keeps_happening", "")),
        "diagnosed_entry": entry_id,
        "expected_entries": query["expected"],
        "matched_expected": True,
        "run_date": date,
    }


def excluded_markdown(excluded, results_name, date, total):
    lines = [
        "# Coaching library: excluded answers",
        "",
        f"From `{results_name}`, run date {date}. "
        f"{total - len(excluded)} of {total} answers exported, {len(excluded)} left out.",
        "",
    ]
    if not excluded:
        lines.append("Nothing was left out.")
        return "\n".join(lines) + "\n"
    lines += ["| # | Shot | Club group | Reason |", "|---|---|---|---|"]
    for query, reason in excluded:
        reason = clean(reason).replace("|", "/")
        lines.append(f"| {query['n']} | {query['shot']} | {query['club_group']} | {reason} |")
    return "\n".join(lines) + "\n"


def export(results_path, queries_path, out_dir, date_override=None):
    queries = parse_game_queries(queries_path)
    if not queries:
        raise SystemExit(f"No Set G queries found in {queries_path}.")
    rows = json.loads(Path(results_path).read_text(encoding="utf-8"))
    by_n = {row.get("n"): row for row in rows if isinstance(row, dict)}
    if not any(by_n.get(q["n"], {}).get("query") == q["query"] for q in queries):
        raise SystemExit(f"{results_path} has no rows from {queries_path}. Is it a Set G run?")

    date = run_date(results_path, date_override)
    library, excluded = [], []
    for query in queries:
        row = by_n.get(query["n"])
        reason = exclusion_reason(query, row)
        if reason:
            excluded.append((query, reason))
        else:
            library.append(library_entry(query, row, date))

    payload = {
        "source": "Golf Agent answers for Set G (golf-game-queries.md)",
        "results_file": Path(results_path).name,
        "run_date": date,
        "count": len(library),
        "answers": library,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if "—" in text or "–" in text:
        raise SystemExit("An em or en dash survived cleaning. Nothing was written.")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "golf-coach-library.json").write_text(text, encoding="utf-8")
    (out_dir / "golf-coach-library-excluded.md").write_text(
        excluded_markdown(excluded, Path(results_path).name, date, len(queries)),
        encoding="utf-8",
    )
    print(f"Exported {len(library)} of {len(queries)} answers to {out_dir / 'golf-coach-library.json'}")
    print(f"Left out {len(excluded)}, listed in {out_dir / 'golf-coach-library-excluded.md'}")
    return payload, excluded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", help="generation results file from a Set G eval run")
    parser.add_argument("--queries", default="golf-game-queries.md")
    parser.add_argument("--out-dir", default="exports")
    parser.add_argument("--run-date", default=None, help="YYYY-MM-DD, if not in the file name")
    args = parser.parse_args()
    export(args.results, args.queries, args.out_dir, args.run_date)


if __name__ == "__main__":
    sys.exit(main())
