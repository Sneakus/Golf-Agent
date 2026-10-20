#!/usr/bin/env python3
"""
Export the knowledge base the range game reads.

The game knows the true cause of every shot from its physics, so it reads the
corpus entries directly instead of asking retrieval or a model to pick one.
This script copies those entries, word for word, into one JSON file. It makes
no network calls of any kind.

Usage:
    python export_knowledge_base.py
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness import parse_corpus
from generate import corpus_fingerprint, listed_fixes, structural_grip_change

CORPUS = "golf-fault-corpus-v3.md"
# N001 is not in the fault corpus. It sits with the out-of-scope entries.
NO_FAULT_FILE = "golf-out-of-scope-entries.md"
OUT = Path("exports") / "golf-knowledge-base.json"

ENTRY_IDS = (
    [f"F{i:03d}" for i in range(1, 19)]
    + [f"L{i:03d}" for i in range(1, 7)]
    + [f"D{i:03d}" for i in range(1, 6)]
    + ["N001"]
)

# Written for the tool rather than for golfers.
LEFT_OUT = {"How I'd describe it", "Evidence tier", "Compensation risk"}

DIFFERENTIAL_HEADING = "## Differential diagnosis: when the fix does not work"
ID_RE = re.compile(r"\b[FPDLSCRN]\d{3}\b")
FIELD_RE = re.compile(r"^\*\*([^*]+?):?\*\*:?[ \t]*", re.M)
SIGNAL_RE = re.compile(r"\s(?:Distinguishing signal|Signal):\s")
POINTER_RE = re.compile(r"^Same as ([FPDLSCR]\d{3})\.?$")

FEEL_WORDS = {
    "feel", "keep", "trust", "let", "accelerate", "stay", "rotate", "commit",
    "steepen", "shorten", "shallow", "enter",
}
SETUP_WORDS = {
    "check", "aim", "flex", "hold", "take", "grip", "expect", "tee", "club",
    "pick", "add", "do", "set", "with", "on", "address",
}

# Lines the leading-word rule would get wrong, or that need a stated reason.
KIND_OVERRIDES = {
    ("F005", 1): ("feel", "a path change for the swing, once alignment has been checked"),
    ("F009", 3): ("feel", "starts with the club it applies to, but the fix is a swing cue: sweep level through the ball"),
    ("F018", 0): ("structural", "a way to work on the miss over many shots, not a next-shot fix"),
    ("F018", 1): ("structural", "accepting one miss for a while is a lasting plan, not a next-shot fix"),
    ("D004", 1): ("structural", "noting conditions over many rounds is a lasting habit, not a next-shot fix"),
    ("L004", 1): ("setup", "setting the shoulders with the slope is done at address; the line also carries a swing cue, chase the club down the slope"),
}


def fields(entry_text):
    """Labelled blocks of an entry, in order, as (label, text exactly as written)."""
    marks = list(FIELD_RE.finditer(entry_text))
    out = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(entry_text)
        out.append((mark.group(1).strip(), entry_text[mark.end():end].strip()))
    return out


def list_lines(block):
    """Numbered or bulleted lines, with the marker removed."""
    items = []
    for line in block.splitlines():
        match = re.match(r"^\s*(?:\d+\.|-)\s+(.+)$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def split_cause(line):
    """A cause's text and its distinguishing signal, each exactly as written."""
    match = SIGNAL_RE.search(line)
    if not match:
        return {"text": line, "signal": None}
    return {"text": line[:match.start()], "signal": line[match.end():]}


def tag_fix(entry_id, index, text):
    if structural_grip_change(text):
        return {"kind": "structural",
                "kind_reason": "matches generate.py's structural grip rule: grip strength or how the hands sit on the grip"}
    pointer = POINTER_RE.match(text)
    if pointer:
        return {"kind": "pointer", "points_to": pointer.group(1),
                "kind_reason": f"not a fix on its own; use the fixes of {pointer.group(1)}"}
    if (entry_id, index) in KIND_OVERRIDES:
        kind, reason = KIND_OVERRIDES[(entry_id, index)]
        return {"kind": kind, "kind_reason": reason}
    first = re.match(r"[A-Za-z]+", text).group(0).lower()
    if first in FEEL_WORDS:
        return {"kind": "feel", "kind_reason": f"starts with '{first}', a cue for the swing itself"}
    if first in SETUP_WORDS:
        return {"kind": "setup",
                "kind_reason": f"starts with '{first}', done before the swing: aim, ball position, stance, "
                               "where the club is held, tee height, club choice or a check"}
    raise SystemExit(f"{entry_id} fix {index} has no kind rule: {text!r}. Add one before exporting.")


def differential_rows(corpus_text):
    section = corpus_text.split(DIFFERENTIAL_HEADING, 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] == "Entry":
            continue
        rows.append({
            "entry": cells[0],
            "commonly_confused_with": cells[1],
            "what_separates_them": cells[2],
            "entry_ids": ID_RE.findall(cells[0]) + ID_RE.findall(cells[1]),
        })
    return rows


def export_entry(entry, differentials):
    what_it_is = None
    causes = []
    notes = []
    for label, text in fields(entry["text"]):
        if label in LEFT_OUT:
            continue
        if label == "What it is":
            what_it_is = text
        elif label == "Causes":
            causes = [split_cause(line) for line in list_lines(text)]
        elif label in ("Fixes", "Adjustments"):
            continue
        else:
            notes.append({"label": label, "text": text})
    fixes = [{"text": text, **tag_fix(entry["id"], i, text)}
             for i, text in enumerate(listed_fixes(entry))]
    return {
        "id": entry["id"],
        "name": entry["name"],
        "what_it_is": what_it_is,
        "causes": causes,
        "fixes": fixes,
        "notes": notes,
        "differentials": [
            {key: row[key] for key in ("entry", "commonly_confused_with", "what_separates_them")}
            for row in differentials if entry["id"] in row["entry_ids"]
        ],
    }


def build(root=Path("."), export_date=None):
    root = Path(root)
    corpus_path = root / CORPUS
    no_fault_path = root / NO_FAULT_FILE
    by_id = {entry["id"]: entry for entry in parse_corpus([corpus_path, no_fault_path])}
    missing = [entry_id for entry_id in ENTRY_IDS if entry_id not in by_id]
    if missing:
        raise SystemExit(f"Entries not found in the corpus: {', '.join(missing)}")
    differentials = differential_rows(corpus_path.read_text(encoding="utf-8"))
    return {
        "source": {
            "files": [
                {"file": CORPUS, "sha256": corpus_fingerprint(corpus_path)},
                {"file": NO_FAULT_FILE, "sha256": corpus_fingerprint(no_fault_path),
                 "entries": ["N001"]},
            ],
            "hash_note": "sha256 of the file text with line endings normalised to LF",
            "export_date": export_date or str(date.today()),
            "note": ("Text is copied exactly as written in the corpus. The How I'd describe it, "
                     "Evidence tier and Compensation risk lines are left out."),
        },
        "fix_kinds": {
            "feel": "a swing feel or cue",
            "setup": "something done before the swing, such as ball position, aim or tee height",
            "structural": "a lasting change such as grip strength, which is not a next-shot fix",
            "pointer": "a line that only points at another entry's fixes",
        },
        "entries": [export_entry(by_id[entry_id], differentials) for entry_id in ENTRY_IDS],
    }


def write(payload, out=OUT):
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if chr(0x2014) in text or chr(0x2013) in text:
        raise SystemExit("The export contains an em or en dash. Nothing was written.")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    args = parser.parse_args()
    payload = build(export_date=args.date)
    out = write(payload, args.out)
    entries = payload["entries"]
    print(f"Exported {len(entries)} entries to {out}")
    for entry in entries:
        kinds = {fix["kind"] for fix in entry["fixes"]}
        for fix in entry["fixes"]:
            if fix["kind"] == "structural":
                print(f"  structural  {entry['id']}: {fix['text']}  ({fix['kind_reason']})")
        if not kinds & {"feel", "setup"}:
            print(f"  no feel or setup fix: {entry['id']} {entry['name']}")


if __name__ == "__main__":
    main()
