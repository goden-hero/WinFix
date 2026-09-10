# WinFix Agent Architecture

## Goal

WinFix is a local-first Windows diagnostic assistant. The MVP is one agent that investigates a user-reported problem, produces evidence and a remediation plan, then stops for human approval.

## System flow

```text
React dashboard -> FastAPI -> SessionService -> WinFixAgent -> high-level diagnostics
                                              -> Evidence -> agent harness -> DiagnosisResult
DiagnosisResult -> user approval -> safety policy -> action registry -> controlled executor -> verification
```

The LLM is an untrusted planner. It can select only high-level read-only diagnostic tools and produce contract-validated recommendations. It cannot receive a shell, PowerShell, registry, file-delete, or executor tool.

## Backend ownership

| Module | Responsibility |
| --- | --- |
| `schemas/` | Versioned Pydantic wire contracts shared by routes, tools, and UI. |
| `diagnostics/` | Bounded, read-only evidence collection. |
| `agent/` | Single-agent orchestration and Ollama/Pi harness boundary. |
| `services/` | Session state machine and workflow coordination. |
| `safety/` | Deterministic risk and recommendation validation. |
| `executor/` | Action registry, controlled capability adapter, and verification hooks. |
| `storage/` | Local SQLite persistence. |

## First vertical slice

`POST /sessions/{id}/diagnose` with `performance` calls `diagnose_performance()`. It reads CPU, memory, disk, processes, supported startup Run keys, and temp usage through Python/Windows APIs, then passes standardized evidence to the configured Qwen/Ollama harness. If Ollama is unavailable or its JSON is invalid, the deterministic harness produces the same `DiagnosisResult` contract. The call never changes the machine.

## Agent integration

`PiAgentHarness` is the default agent runtime for performance diagnosis. It starts the isolated `pi_runtime/runner.mjs`, which uses `@earendil-works/pi-agent-core` and `@earendil-works/pi-ai` against Ollama's OpenAI-compatible endpoint. The runner exposes exactly one TypeBox-validated Pi tool, `diagnose_performance` with no parameters. It has no Pi coding-agent package and therefore no `bash`, `read`, `write`, or `edit` tools.

The Python bridge executes that tool through the existing backend diagnostic, sends normalized `Evidence` back to Pi, requires exactly one call, validates the final JSON as `DiagnosisResult`, and rejects unknown evidence links. `OllamaQwenHarness` remains available only as a legacy direct adapter. Pi is an orchestration layer, never a security boundary.

Run `cd backend/pi_runtime && npm test` to validate the Pi tool loop with Pi AI's scripted provider. For a live run, start Ollama, pull `qwen3:8b` (or `qwen3:4b`), and leave `WINFIX_AGENT_RUNTIME` unset or set it to `pi`.

## Windows implementation guidance

Diagnostic modules may use `psutil`, WMI/CIM, Event Log APIs, and narrowly scoped backend-owned PowerShell functions. Executor implementations must receive typed parameters from `ActionRegistry`, use fixed commands or native APIs, record before state, and expose a deterministic verifier. No module may accept a raw command string.

## Deliberate MVP omissions

No authentication, cloud deployment, multi-agent system, arbitrary shell access, kernel dump analysis, or generalized WinUtil/PowerShell bridge. Those exclusions preserve the demo's safety model and speed of iteration.
