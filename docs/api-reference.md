# HTTP API reference

The local API listens at `http://127.0.0.1:8000` by default. Interactive OpenAPI
documentation is available at `/docs`; the machine-readable schema is available
at `/openapi.json`.

The API requires no key. It is intended for a trusted local machine only.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Report service version and deterministic mode |
| `POST` | `/api/v1/mission/start` | Create a seeded mission |
| `POST` | `/api/v1/mission/step` | Execute an allowed action or the recommended next action |
| `POST` | `/api/v1/mission/drift` | Inject a bounded synthetic drift event |
| `POST` | `/api/v1/mission/human-answer` | Answer the pending structured human question |
| `POST` | `/api/v1/mission/reset` | Create a fresh mission linked to an earlier mission |
| `GET` | `/api/v1/mission/{mission_id}` | Read the current snapshot |
| `GET` | `/api/v1/mission/{mission_id}/events` | Replay audit events as server-sent events |

## Start a mission

```bash
curl --fail-with-body \
  --request POST http://127.0.0.1:8000/api/v1/mission/start \
  --header "Content-Type: application/json" \
  --data '{
    "goal": "Increase fashion recommendation conversion without reducing diversity by more than 2%.",
    "budget": 30000,
    "max_diversity_loss": 0.02,
    "seed": 42
  }'
```

The response is an `EpisodeSnapshot`. Save `mission_id`, inspect
`allowed_actions`, and use one of those actions in the next request.

## Step a mission

```bash
curl --fail-with-body \
  --request POST http://127.0.0.1:8000/api/v1/mission/step \
  --header "Content-Type: application/json" \
  --data '{"mission_id":"MISSION_ID","requested_action":"experiment"}'
```

Omit `requested_action` to ask the deterministic coordinator for its recommended
next action. Actions that target one segment also require `segment_id`.

## Inject drift

```bash
curl --fail-with-body \
  --request POST http://127.0.0.1:8000/api/v1/mission/drift \
  --header "Content-Type: application/json" \
  --data '{"mission_id":"MISSION_ID","severity":0.55,"segment_id":"new_arrivals"}'
```

Drift injection changes only the seeded simulator. It does not modify an external
dataset or production system.

## Answer a human question

First execute `ask_human`, then inspect `pending_question`. Send the requested
structured value with a concise explanation:

```bash
curl --fail-with-body \
  --request POST http://127.0.0.1:8000/api/v1/mission/human-answer \
  --header "Content-Type: application/json" \
  --data '{
    "mission_id":"MISSION_ID",
    "answer":"Keep the intervention above the declared margin floor.",
    "margin_floor":0.08
  }'
```

Depending on the pending question, the structured field may be `margin_floor` or
`subsidy_cap`. Free text alone does not satisfy a structured gate.

## Reset and provenance

```bash
curl --fail-with-body \
  --request POST http://127.0.0.1:8000/api/v1/mission/reset \
  --header "Content-Type: application/json" \
  --data '{"mission_id":"MISSION_ID"}'
```

Reset returns a new `mission_id`. The earlier mission remains readable until the
process exits.

## Response contract

`EpisodeSnapshot` contains:

- mission state, step, goal, and budget use;
- evidence mode, fixture/dataset version, split, seed, estimator, assumptions, and fingerprints;
- four risk indices with level and evidence strings;
- experiment and policy metrics;
- segment estimates, intervals, statuses, and visual coordinates;
- recommended decision and eligible segments;
- allowed actions and an optional pending human question;
- the append-only in-memory transition trace available for the mission.

The Pydantic models in `backend/causalpilot/schemas.py` and generated OpenAPI
schema are authoritative.

## Errors

| Status | Meaning |
| --- | --- |
| `404` | The mission identifier does not exist in this process |
| `409` | The action violates state, budget, target, evidence, or human gates |
| `422` | The request does not match the strict schema |

Request models reject unknown fields. A rejected request does not grant an action.

## Event stream

`GET /api/v1/mission/{mission_id}/events` emits each stored audit entry as an
`audit` event, followed by an `end` event. The current implementation then closes
the connection. Poll the mission endpoint for later state or reconnect to replay
the complete in-memory audit.
