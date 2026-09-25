#!/usr/bin/env python3
"""
Local HTTP service exposing the eval pipeline, so n8n can orchestrate it
without needing Python inside the container.

n8n calls this with HTTP Request nodes. That keeps n8n doing what it is
good at, which is orchestration, and keeps the retrieval work in Python
where it belongs.

Setup:
    pip install fastapi uvicorn
    python eval_service.py

Then from n8n (which runs in Docker) call:
    http://host.docker.internal:8000/...

Endpoints:
    GET  /health          is the service up
    GET  /corpus/hash     current hash of the corpus files
    POST /eval            run the retrieval eval, returns the summary
    POST /diagnose        answer a single golfer query
"""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).parent
CORPUS = ["golf-fault-corpus-v3.md", "golf-out-of-scope-entries.md"]
EVALS = "golf-eval-sets-v2.md"
STATE = ROOT / ".service-state"
STATE.mkdir(exist_ok=True)

app = FastAPI(title="golf-tool eval service")

# Retriever is expensive to build (embeds the whole corpus), so build it once
# and rebuild only when the corpus changes.
_retriever = None
_retriever_hash = None


def corpus_hash():
    h = hashlib.sha256()
    for name in CORPUS:
        data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        h.update(data)
    return h.hexdigest()


def get_retriever():
    global _retriever, _retriever_hash
    current = corpus_hash()
    if _retriever is None or _retriever_hash != current:
        sys.path.insert(0, str(ROOT))
        from generate import Retriever
        _retriever = Retriever([str(ROOT / c) for c in CORPUS])
        _retriever_hash = current
    return _retriever


@app.get("/health")
def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/corpus/hash")
def get_hash():
    """
    Current corpus hash, and whether it has changed since the last eval.
    n8n polls this and only runs the eval when something has actually changed.
    """
    current = corpus_hash()
    last_file = STATE / "last_evaluated_hash.txt"
    last = last_file.read_text().strip() if last_file.exists() else None
    return {
        "hash": current,
        "last_evaluated": last,
        "changed": current != last,
    }


class EvalRequest(BaseModel):
    label: str = "n8n run"
    threshold: float = 0.90


@app.post("/eval")
def run_eval(req: EvalRequest):
    """
    Run the retrieval eval and return the summary, plus a comparison against
    the previous run and a pass or fail verdict.
    """
    cmd = [
        sys.executable, "evaluate.py",
        "--corpus", *CORPUS,
        "--evals", EVALS,
        "--label", req.label,
        "--fail-under-recall5", str(req.threshold),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)

    summary_path = ROOT / "eval_summary.json"
    if not summary_path.exists():
        raise HTTPException(500, f"Eval produced no summary. stderr: {proc.stderr[-800:]}")

    summary = json.loads(summary_path.read_text())

    prev_path = STATE / "previous_summary.json"
    previous = json.loads(prev_path.read_text()) if prev_path.exists() else None

    def delta(metric):
        if not previous:
            return None
        return round(summary[metric]["score"] - previous[metric]["score"], 3)

    passed = (
        summary["recall@5"]["score"] >= req.threshold
        and summary["false_declines"] == 0
    )
    regressed = bool(previous) and summary["recall@5"]["score"] < previous["recall@5"]["score"] - 0.02

    # Only record state on a pass, so a failing corpus keeps triggering
    if passed:
        prev_path.write_text(json.dumps(summary, indent=2))
        (STATE / "last_evaluated_hash.txt").write_text(corpus_hash())

    return {
        "passed": passed,
        "regressed": regressed,
        "exit_code": proc.returncode,
        "metrics": {
            "recall@5": summary["recall@5"]["score"],
            "hit@5": summary["hit@5"]["score"],
            "hit@1": summary["hit@1"]["score"],
            "mrr": summary["mrr"]["score"],
            "abstention": summary["abstention"]["score"],
            "false_declines": summary["false_declines"],
        },
        "deltas": {
            "recall@5": delta("recall@5"),
            "hit@1": delta("hit@1"),
            "mrr": delta("mrr"),
        },
        "confidence_intervals": {
            "recall@5": summary["recall@5"]["ci"],
            "hit@1": summary["hit@1"]["ci"],
        },
        "subsets": summary.get("subsets", {}),
        "meta": summary["meta"],
    }


class DiagnoseRequest(BaseModel):
    query: str


@app.post("/diagnose")
def diagnose(req: DiagnoseRequest):
    """Answer one query. Used for on-course logging later."""
    sys.path.insert(0, str(ROOT))
    from generate import answer
    return answer(req.query, get_retriever())


if __name__ == "__main__":
    import uvicorn
    print("Corpus:", ", ".join(CORPUS))
    print("From n8n in Docker, call http://host.docker.internal:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
