# WinFix Pi Runtime

This directory contains the isolated Node runtime for the Pi agent loop. It has no Pi coding-agent package and therefore no `bash`, `read`, `write`, or `edit` tools.

`runner.mjs` speaks newline-delimited JSON with the Python `PiAgentHarness`:

1. Python sends a `start` message containing the user problem.
2. Pi may request only `diagnose_performance`.
3. Python executes the backend-owned diagnostic and responds with structured evidence.
4. Pi returns a JSON `DiagnosisResult` as its final message.

The process is launched with a fixed executable and script path. The model cannot influence either command, tool name, tool arguments, or the Windows implementation.

Run `npm test` to validate Pi's two-turn tool loop using Pi AI's scripted provider. A live model test additionally requires a running Ollama daemon with `qwen3:8b` or `qwen3:4b` installed.
