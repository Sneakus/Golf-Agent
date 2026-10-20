#!/usr/bin/env python3
"""
Runs the knowledge base export and checks it. No network calls.

Usage:
    python test_export_knowledge_base.py
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from export_knowledge_base import ENTRY_IDS, build, write

ROOT = Path(__file__).parent
KINDS = {"feel", "setup", "structural", "pointer"}


def test_export():
    with tempfile.TemporaryDirectory() as tmp:
        out = write(build(ROOT), Path(tmp) / "golf-knowledge-base.json")
        text = out.read_text(encoding="utf-8")
    payload = json.loads(text)
    corpus = "".join(
        (ROOT / item["file"]).read_text(encoding="utf-8") for item in payload["source"]["files"]
    )

    entries = {entry["id"]: entry for entry in payload["entries"]}
    assert list(entries) == ENTRY_IDS, "every listed entry is exported, in order"
    for entry_id, entry in entries.items():
        if entry_id == "N001":
            # A good shot has no fix by design. Its correct response says so.
            assert entry["fixes"] == []
            assert any(note["label"] == "Correct response" for note in entry["notes"])
            continue
        assert entry["fixes"], f"{entry_id} has no fix"
        assert entry["what_it_is"], f"{entry_id} has no what it is"
        for fix in entry["fixes"]:
            assert fix["kind"] in KINDS, f"{entry_id} fix has kind {fix['kind']}"

    copied = []
    for entry in payload["entries"]:
        copied.append(entry["what_it_is"])
        copied += [cause["text"] for cause in entry["causes"]]
        copied += [cause["signal"] for cause in entry["causes"] if cause["signal"]]
        copied += [fix["text"] for fix in entry["fixes"]]
        copied += [note["text"] for note in entry["notes"]]
        copied += [value for row in entry["differentials"] for value in row.values()]
    assert all(item in corpus for item in copied), "text is copied exactly"

    body = json.dumps(payload["entries"], ensure_ascii=False)
    for left_out in ("How I'd describe it", "Evidence tier", "Compensation risk"):
        assert left_out not in body, f"{left_out} leaked into the export"
    assert chr(0x2014) not in text and chr(0x2013) not in text
    assert payload["source"]["files"][0]["file"] == "golf-fault-corpus-v3.md"
    assert len(payload["source"]["files"][0]["sha256"]) == 64

    structural = [(e["id"], f["text"]) for e in payload["entries"]
                  for f in e["fixes"] if f["kind"] == "structural"]
    assert ("F004", "Weaken the grip slightly.") in structural


if __name__ == "__main__":
    test_export()
    print("Knowledge base export test passed.")
