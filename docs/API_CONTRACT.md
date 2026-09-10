# WinFix Agent API Contract

Base path: `/api/v1`. JSON uses Pydantic v2 serialization. The OpenAPI document at `/docs` is the live machine-readable contract.

| Endpoint | Purpose |
| --- | --- |
| `POST /sessions` | Create a session with `user_problem`. |
| `GET /sessions/{session_id}` | Fetch the complete persisted session. |
| `POST /sessions/{session_id}/diagnose` | Collect requested diagnostic categories; defaults to `performance`. |
| `POST /sessions/{session_id}/approve` | Submit explicit `approved: true/false` decisions for recommended action IDs. |
| `POST /sessions/{session_id}/reject` | Mark supplied recommendations rejected. |
| `POST /sessions/{session_id}/execute` | Execute approved registry actions through the controlled executor. |
| `POST /sessions/{session_id}/verify` | Run action-specific verification after execution. |
| `GET /actions` | Read registry metadata for UI rendering. |

## Key payloads

Create a session:

```json
{"user_problem":"My PC is slow"}
```

Diagnose it:

```json
{"categories":["performance"]}
```

Approve a plan item:

```json
{"decisions":[{"action_id":"clear_temp_files","approved":true}]}
```

## Stable models

`Evidence` is the generic diagnostic display contract: `id`, `category`, `severity`, `title`, `description`, `source`, `timestamp`, and `data`.

`DiagnosisResult` keeps facts and inference separate: `probable_causes` links evidence IDs and confidence, while `recommended_actions` contains only an `action_id`, reason, evidence IDs, and typed parameters. It cannot contain commands.

`WinFixSession` is the UI's source of truth. It includes evidence, diagnosis, approvals, execution results, and verification results. Status transitions are: `created -> diagnosing -> diagnosed|awaiting_approval -> approved -> executing -> verifying -> completed`; a workflow can also enter `failed`.

Validation failures for workflow state or unsupported decisions return `409`; missing sessions return `404`; request shape errors return FastAPI's standard `422`.
