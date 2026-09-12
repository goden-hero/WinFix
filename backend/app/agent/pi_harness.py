"""Bounded Python-to-Pi bridge for the performance-diagnosis agent loop."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from app.diagnostics.performance import diagnose_performance
from app.schemas.diagnosis import DiagnosisResult
from app.schemas.evidence import Evidence


class PiHarnessError(RuntimeError):
    """The Pi sidecar did not complete the constrained agent loop."""


class PiAgentHarness:
    """Runs Pi with one backend-owned diagnostic capability and no shell tools."""

    def __init__(self, node_binary: str | None = None, timeout_seconds: float | None = None) -> None:
        self.node_binary = node_binary or os.getenv("WINFIX_PI_NODE_BINARY", "node")
        self.timeout_seconds = timeout_seconds or float(os.getenv("WINFIX_PI_TIMEOUT_SECONDS", "90"))
        self.runner_path = Path(__file__).resolve().parents[2] / "pi_runtime" / "runner.mjs"

    async def investigate_performance(self, problem: str) -> tuple[list[Evidence], DiagnosisResult]:
        if not self.runner_path.is_file():
            raise PiHarnessError(f"Pi runtime is missing: {self.runner_path}")
        try:
            process = await asyncio.create_subprocess_exec(
                self.node_binary,
                str(self.runner_path),
                cwd=str(self.runner_path.parent),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except NotImplementedError as error:
            raise PiHarnessError("Asyncio event loop on Windows does not support subprocesses in this environment.") from error
        evidence: list[Evidence] = []
        try:
            await self._send(process, {"type": "start", "problem": problem})
            while True:
                message = await asyncio.wait_for(self._receive(process), timeout=self.timeout_seconds)
                kind = message.get("type")
                if kind == "tool_request":
                    await self._handle_tool_request(process, message, evidence)
                    continue
                if kind == "final":
                    if message.get("tool_calls") != 1:
                        raise PiHarnessError("Pi completed without the required single performance diagnostic call.")
                    diagnosis = self._parse_diagnosis(message.get("diagnosis_json"))
                    self._validate_evidence_links(diagnosis, evidence)
                    return evidence, diagnosis.model_copy(update={"generated_by": f"pi:ollama:{os.getenv('WINFIX_MODEL', 'qwen3:8b')}"})
                if kind == "error":
                    raise PiHarnessError(str(message.get("error", "Pi runtime failed.")))
                raise PiHarnessError(f"Pi emitted an unsupported protocol message: {kind!r}")
        except (asyncio.TimeoutError, json.JSONDecodeError) as error:
            raise PiHarnessError("Pi timed out or emitted invalid protocol JSON.") from error
        finally:
            if process.returncode is None:
                process.terminate()
            await process.wait()

    @staticmethod
    async def _send(process: asyncio.subprocess.Process, message: dict[str, Any]) -> None:
        if not process.stdin:
            raise PiHarnessError("Pi runtime stdin is unavailable.")
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

    @staticmethod
    async def _receive(process: asyncio.subprocess.Process) -> dict[str, Any]:
        if not process.stdout:
            raise PiHarnessError("Pi runtime stdout is unavailable.")
        line = await process.stdout.readline()
        if not line:
            raise PiHarnessError("Pi runtime exited before completing the agent loop.")
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise PiHarnessError("Pi protocol message must be a JSON object.")
        return payload

    async def _handle_tool_request(
        self, process: asyncio.subprocess.Process, message: dict[str, Any], evidence: list[Evidence]
    ) -> None:
        request_id = message.get("request_id")
        if message.get("name") != "diagnose_performance" or message.get("arguments") != {} or not isinstance(request_id, str):
            raise PiHarnessError("Pi requested a tool outside the WinFix performance allowlist.")
        if evidence:
            raise PiHarnessError("Pi attempted to repeat the performance diagnostic.")
        evidence.extend(diagnose_performance())
        await self._send(
            process,
            {"type": "tool_result", "request_id": request_id, "evidence": [item.model_dump(mode="json") for item in evidence]},
        )

    @staticmethod
    def _parse_diagnosis(raw: object) -> DiagnosisResult:
        if not isinstance(raw, str):
            raise PiHarnessError("Pi final diagnosis is missing.")
        candidate = raw.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return DiagnosisResult.model_validate_json(candidate)
        except ValueError as error:
            raise PiHarnessError("Pi final output does not match DiagnosisResult.") from error

    @staticmethod
    def _validate_evidence_links(diagnosis: DiagnosisResult, evidence: list[Evidence]) -> None:
        known_ids = {item.id for item in evidence}
        referenced_ids = {
            evidence_id
            for cause in diagnosis.probable_causes
            for evidence_id in cause.evidence_ids
        }
        referenced_ids.update(
            evidence_id
            for finding in diagnosis.findings
            for evidence_id in finding.evidence_ids
        )
        referenced_ids.update(
            evidence_id
            for action in diagnosis.recommended_actions
            for evidence_id in action.evidence_ids
        )
        unknown = referenced_ids - known_ids
        if unknown:
            raise PiHarnessError(f"Pi referenced unknown evidence IDs: {sorted(unknown)}")
