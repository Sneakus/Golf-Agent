# n8n Pipelines

Two workflows. The first is the substantial one and does real work: it watches the corpus, re-runs the evaluation on change, and blocks the change if retrieval regresses. The second is small and feeds the tool itself.

Self-hosted n8n, since the Execute Command node is needed and cloud execution limits make polling workflows expensive.

---

# Workflow 1: Corpus change, evaluate, gate, notify

## What it does and why it is worth building

The corpus is the part of this system most likely to change and most likely to break retrieval silently. Adding an alias line to one entry can pull queries away from another. Without automation you would only find out by remembering to rerun the eval.

This workflow makes that impossible to forget: any corpus change triggers a full re-embed and re-evaluation, the result is compared against the last recorded score, and a regression is reported rather than merged.

It is also the honest answer to "what did you build on n8n": an ingestion and quality-gate pipeline, not a weather cron.

## Nodes

**1. Schedule Trigger**
- Interval: every 15 minutes
- Alternative: Webhook node receiving a GitHub push event, if the repo is remote. The schedule version works entirely locally and needs no public URL.

**2. Execute Command: hash the corpus**
```
python -c "import hashlib,glob,json,sys; h=hashlib.sha256(); [h.update(open(f,'rb').read()) for f in sorted(glob.glob('D:/golf-tool/*.md'))]; print(json.dumps({'hash':h.hexdigest()}))"
```
- Working directory: `D:/golf-tool`

**3. Code node: parse the hash**
```javascript
const out = JSON.parse($input.first().json.stdout);
return [{ json: { hash: out.hash } }];
```

**4. Read/Write Files from Disk: read last hash**
- Operation: Read
- File path: `D:/golf-tool/.n8n-state/last_hash.json`
- On error: continue, so the first run works with no state file

**5. IF: has the corpus changed**
- Condition: `{{ $json.hash }}` not equal to `{{ $('Read last hash').item.json.hash }}`
- False branch: end. Nothing to do.

**6. Execute Command: run the evaluation**
```
python evaluate.py --corpus golf-fault-corpus-v3.md golf-out-of-scope-entries.md --evals golf-eval-sets-v2.md --label "n8n auto-run" --fail-under-recall5 0.90
```
- Working directory: `D:/golf-tool`
- Always output data: on, so a non-zero exit still flows through rather than killing the run

**7. Read/Write Files from Disk: read the summary**
- Operation: Read
- File path: `D:/golf-tool/eval_summary.json`

**8. Code node: compare against the previous run**
```javascript
const now = JSON.parse($input.first().json.data.toString());
let prev = null;
try {
  prev = JSON.parse($('Read previous summary').item.json.data.toString());
} catch (e) { /* first run */ }

const delta = (metric) => {
  if (!prev) return null;
  return +(now[metric].score - prev[metric].score).toFixed(3);
};

const regressed = prev
  ? now['recall@5'].score < prev['recall@5'].score - 0.02
  : false;

return [{ json: {
  recall5: now['recall@5'].score,
  hit5: now['hit@5'].score,
  hit1: now['hit@1'].score,
  mrr: now.mrr.score,
  abstention: now.abstention.score,
  false_declines: now.false_declines,
  delta_recall5: delta('recall@5'),
  delta_hit1: delta('hit@1'),
  regressed,
  passed: now['recall@5'].score >= 0.90 && now.false_declines === 0,
}}];
```

**9. Switch: route on outcome**
- Output "regression": `{{ $json.regressed }}` is true
- Output "failed gate": `{{ $json.passed }}` is false
- Output "passed": fallback

**10a. Slack or Email on regression**
```
Corpus change caused a retrieval regression.

recall@5  {{ $json.recall5 }}  ({{ $json.delta_recall5 }})
hit@1     {{ $json.hit1 }}  ({{ $json.delta_hit1 }})
false declines  {{ $json.false_declines }}

The corpus has changed and retrieval got worse. Review before committing.
```

**10b. Notification on pass**
```
Corpus updated, eval passed.

recall@5 {{ $json.recall5 }}, hit@5 {{ $json.hit5 }}, hit@1 {{ $json.hit1 }}, MRR {{ $json.mrr }}
Abstention {{ $json.abstention }}, false declines {{ $json.false_declines }}
```

**11. Write the new hash**
- Only on the pass branch, so a failing corpus keeps triggering until fixed
- File path: `D:/golf-tool/.n8n-state/last_hash.json`

**12. Error Trigger workflow**
- Separate workflow, bound as the error handler
- Sends the failing node name and message, so a broken API key does not fail silently

## What to expect when building it

Things worth noting for the write-up, since "what did the platform make easy and what made it annoying" is the question you will be asked:

- Reading a file and getting usable JSON out takes three nodes rather than one line of Python. Binary data comes back as a buffer and needs a Code node to parse.
- Execute Command node returns stdout as a string, so any structured output needs parsing on the way back in. Printing JSON from the script rather than human-readable text makes this much easier, which is why `evaluate.py` writes a summary file.
- Persisting state between runs has no built-in mechanism. Writing a file is the simplest option; static workflow data is the alternative but is easy to lose.
- Error handling is genuinely good. The Error Trigger pattern catches everything without wrapping each node.
- The visual layout makes the branch logic obvious in a way the equivalent script does not.

---

# Workflow 2: Round conditions

Small, and feeds the tool rather than the development loop.

## Nodes

**1. Webhook**
- Method: POST
- Path: `round-start`
- Body: `{ "round_id": "...", "lat": 51.56, "lon": -0.14 }`

**2. HTTP Request: weather**
- URL: `https://api.open-meteo.com/v1/forecast`
- Query parameters:
  - `latitude` `{{ $json.body.lat }}`
  - `longitude` `{{ $json.body.lon }}`
  - `current` `temperature_2m,wind_speed_10m,wind_direction_10m,precipitation`
  - `wind_speed_unit` `mph`
- Open-Meteo needs no API key for non-commercial use

**3. Code node: shape the record**
```javascript
const w = $input.first().json.current;
return [{ json: {
  round_id: $('Webhook').item.json.body.round_id,
  captured_at: new Date().toISOString(),
  temperature_c: w.temperature_2m,
  wind_speed_mph: w.wind_speed_10m,
  wind_direction_deg: w.wind_direction_10m,
  precipitation_mm: w.precipitation,
  // C001 cold conditions applies below roughly 10C
  cold_flag: w.temperature_2m < 10,
  // C002 wind matters above roughly 10mph
  wind_flag: w.wind_speed_10m > 10,
}}];
```

**4. Write to the round record**
- Append to a rounds file, or a database node once storage exists

**5. Schedule Trigger: hourly refresh**
- Second trigger on the same workflow, re-fetching for any round started in the last five hours, since conditions drift over a round

## Note

The `cold_flag` and `wind_flag` are what let the corpus suppress false diagnoses. If C001 applies, a round of short approach shots should not generate five distance-control fault records. That logic lives in the tool, but the flags come from here.

---

# What this closes and what it does not

**Closes:** a scheduled multi-step workflow with conditional branching, file state, external command execution, HTTP integration, structured error handling, and a quality gate that blocks a change. That is a real automation with a job to do.

**Does not close:** production scale, multi-user, or anything running unattended for months. Say "I built an ingestion and quality-gate pipeline on self-hosted n8n" rather than implying production operations experience.

**Worth being honest about in interview:** this is a personal project pipeline. The interesting part is not the platform, it is that a corpus change automatically triggers a measured re-evaluation and gets blocked if retrieval regresses. The same thing runs in GitHub Actions, and building it twice is what lets you say which tool suited which job.
