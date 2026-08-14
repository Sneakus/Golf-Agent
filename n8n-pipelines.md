# n8n Pipelines

Two workflows. The first is the substantial one and does real work: it watches the corpus, re-runs the evaluation on change, and blocks the change if retrieval regresses. The second is small and feeds the tool itself.

Self-hosted n8n, since the Execute Command node is needed and cloud execution limits make polling workflows expensive.

---

# Workflow 1: Corpus change, evaluate, gate, notify

## What it does and why it is worth building

The corpus is the part of this system most likely to change and most likely to break retrieval silently. Adding an alias line to one entry can pull queries away from another. Without automation you would only find out by remembering to rerun the eval.

This workflow makes that impossible to forget: any corpus change triggers a full re-embed and re-evaluation, the result is compared against the last recorded score, and a regression is reported rather than merged.

## Architecture note, and why it changed

The original plan used the Execute Command node to run the Python directly. That does not work: the n8n Docker image has no Python installed, which the container log states on startup.

Two options were available. Build a custom image with Python added, or run the Python as a local HTTP service and have n8n call it. The service won, for reasons worth being able to explain:

- n8n orchestrates rather than shells out, which is what it is actually good at
- HTTP Request nodes are a far more transferable skill than Execute Command
- The retrieval work stays in Python where it belongs
- No custom image to maintain, so anyone can run the workflow against any host

This is the same division the architecture already follows: n8n schedules, branches, notifies and handles errors; Python does the retrieval and evaluation.

## Prerequisite: start the service

```
pip install fastapi uvicorn
python eval_service.py
```

Runs on port 8000. From inside the n8n container, `localhost` means the container, so the host is reached at `host.docker.internal`.

Endpoints:

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | Service up |
| GET | `/corpus/hash` | Current hash and whether it changed since the last eval |
| POST | `/eval` | Runs the eval, returns metrics, deltas, and a pass or fail verdict |
| POST | `/diagnose` | Answers one golfer query |

## Nodes

**1. Schedule Trigger**
- Interval: every 15 minutes

**2. HTTP Request: check for a corpus change**
- Method: GET
- URL: `http://host.docker.internal:8000/corpus/hash`

**3. IF: has the corpus changed**
- Condition: `{{ $json.changed }}` is true
- False branch: end, nothing to do

**4. HTTP Request: run the eval**
- Method: POST
- URL: `http://host.docker.internal:8000/eval`
- Body, JSON:
```json
{
  "label": "n8n scheduled run",
  "threshold": 0.90
}
```
- Timeout: 600000 ms, since embedding the corpus takes a moment
- Response: JSON

**5. Switch: route on outcome**
- Output "regression": `{{ $json.regressed }}` is true
- Output "failed": `{{ $json.passed }}` is false
- Output "passed": fallback

**6a. Notification on regression**
```
Corpus change made retrieval worse.

recall@5  {{ $json.metrics["recall@5"] }}  ({{ $json.deltas["recall@5"] }})
hit@1     {{ $json.metrics["hit@1"] }}  ({{ $json.deltas["hit@1"] }})
MRR       {{ $json.metrics.mrr }}  ({{ $json.deltas.mrr }})

False declines: {{ $json.metrics.false_declines }}
Review before committing.
```

**6b. Notification on failed gate**
```
Eval failed the quality gate.

recall@5 {{ $json.metrics["recall@5"] }} against threshold 0.90
False declines: {{ $json.metrics.false_declines }}
```

**6c. Notification on pass**
```
Corpus updated, eval passed.

recall@5 {{ $json.metrics["recall@5"] }}  (CI {{ $json.confidence_intervals["recall@5"][0] }} to {{ $json.confidence_intervals["recall@5"][1] }})
hit@1 {{ $json.metrics["hit@1"] }}, MRR {{ $json.metrics.mrr }}
Abstention {{ $json.metrics.abstention }}, false declines {{ $json.metrics.false_declines }}

A1 {{ $json.subsets.A1["hit@5"] }}  A2 {{ $json.subsets.A2["hit@5"] }}  A3 {{ $json.subsets.A3["hit@5"] }}
```

Slack, Discord, email or a Telegram node all work. Pick whichever you would actually read.

**7. Error Trigger workflow**
- Separate workflow, bound as the error handler
- Sends the failing node and message, so a stopped service does not fail silently

## State handling

The service tracks the last successfully evaluated hash and the previous summary, so n8n does not need to persist anything between runs. Deliberate: n8n state handling is the fiddliest part of the platform, and keeping it in the service means the workflow is stateless and can be re-imported anywhere.

State is only written on a pass, so a failing corpus keeps triggering until it is fixed rather than being silently accepted.

## What to expect when building it

Notes for the write-up, since "what did the platform make easy and what made it annoying" is the question you will be asked. Check these against your own experience rather than repeating them:

- No Python in the container, which forced the architecture change above. Worth knowing before designing around Execute Command.
- `localhost` inside the container is the container. `host.docker.internal` is the host.
- HTTP Request plus JSON response is genuinely pleasant. The data is immediately usable in later nodes without parsing.
- Accessing nested JSON with a key containing an @ needs bracket syntax, `$json.metrics["recall@5"]` rather than dot notation.
- Error handling via the Error Trigger pattern is good, and catches everything without wrapping each node.
- The visual branch logic is clearer than the equivalent script.

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
