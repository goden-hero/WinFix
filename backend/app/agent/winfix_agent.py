from __future__ import annotations

import json
import os
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.pi_harness import PiAgentHarness, PiHarnessError
from app.diagnostics import (
    analyze_privacy,
    analyze_windows_optimization,
    check_system_health,
    diagnose_performance,
    investigate_crashes,
)
from app.schemas.actions import ActionId, RecommendedAction
from app.schemas.diagnosis import DiagnosisResult, Finding, ProbableCause
from app.schemas.evidence import Evidence


class AgentHarness(Protocol):
    """Pi integration needs only to fulfill this boundary."""

    async def diagnose(self, problem: str, evidence: list[Evidence]) -> DiagnosisResult: ...


class OllamaQwenHarness:
    """Small direct Ollama adapter until the Pi runtime adapter is installed."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("WINFIX_MODEL", "qwen3:8b")

    async def diagnose(self, problem: str, evidence: list[Evidence]) -> DiagnosisResult:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"user_problem": problem, "evidence": [item.model_dump(mode="json") for item in evidence]}
                    ),
                },
            ],
        }
        # A missing local Ollama daemon must not make the UI appear stuck.
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
        content = response.json()["message"]["content"]
        result = DiagnosisResult.model_validate_json(content)
        return result.model_copy(update={"generated_by": f"ollama:{self.model}"})


class DeterministicHarness:
    """Reliable local fallback and demo baseline when an LLM is unavailable."""

    async def diagnose(self, problem: str, evidence: list[Evidence]) -> DiagnosisResult:
        by_title = {item.title: item for item in evidence}
        causes: list[ProbableCause] = []
        findings: list[Finding] = []
        recommendations: list[RecommendedAction] = []

        memory = by_title.get("Memory utilization")
        if memory and memory.data.get("percent", 0) >= 85:
            causes.append(ProbableCause(title="High memory pressure", explanation="Available memory is low relative to installed memory.", evidence_ids=[memory.id], confidence=0.85))
            findings.append(Finding(title="Memory use is elevated", description=memory.description, evidence_ids=[memory.id]))
        disk = by_title.get("System drive capacity")
        if disk and disk.data.get("percent", 0) >= 90:
            causes.append(ProbableCause(title="Low system drive capacity", explanation="A nearly full system drive can slow updates and temporary-file workloads.", evidence_ids=[disk.id], confidence=0.8))
            recommendations.append(RecommendedAction(action_id=ActionId.CLEAR_TEMP_FILES, reason="Temporary storage can be reclaimed through an approved, bounded cleanup.", evidence_ids=[disk.id]))
        startup = by_title.get("Startup applications")
        if startup and startup.data.get("count", 0) >= 10:
            causes.append(ProbableCause(title="Many startup applications", explanation="A high startup-entry count can increase sign-in and background load.", evidence_ids=[startup.id], confidence=0.7))
            findings.append(Finding(title="Review startup load", description=startup.description, evidence_ids=[startup.id]))
        temp = by_title.get("Temporary file usage")
        if temp and temp.data.get("bytes", 0) > 2 * 1024**3 and not recommendations:
            recommendations.append(RecommendedAction(action_id=ActionId.CLEAR_TEMP_FILES, reason="Large temporary-file usage is a safe optimization candidate after approval.", evidence_ids=[temp.id]))

        if not causes:
            causes.append(ProbableCause(title="No single bottleneck identified", explanation="The current snapshot does not establish a definitive root cause. Further observation may be needed.", evidence_ids=[item.id for item in evidence[:4]], confidence=0.45))
        if not findings:
            findings.append(Finding(title="Performance snapshot collected", description="CPU, memory, storage, processes, and startup data were collected without changing the system.", evidence_ids=[item.id for item in evidence]))
        return DiagnosisResult(
            summary="WinFix collected a read-only performance snapshot and identified the most likely causes based on current system evidence.",
            probable_causes=causes,
            findings=findings,
            recommended_actions=recommendations,
            overall_confidence=max(cause.confidence for cause in causes),
            generated_by="deterministic_fallback",
        )


class WinFixAgent:
    """Single-agent orchestration. It selects high-level diagnostic tools only."""

    def __init__(self, harness: AgentHarness | None = None) -> None:
        runtime = os.getenv("WINFIX_AGENT_RUNTIME", "pi").lower()
        self.harness = harness or (OllamaQwenHarness() if runtime == "direct_ollama" else PiAgentHarness())
        self.fallback = DeterministicHarness()

    async def investigate(self, user_problem: str, categories: list[str]) -> tuple[list[Evidence], DiagnosisResult]:
        requested = set(categories or ["performance"])
        if isinstance(self.harness, PiAgentHarness) and requested == {"performance"}:
            try:
                return await self.harness.investigate_performance(user_problem)
            except (PiHarnessError, OSError):
                evidence = diagnose_performance()
                return evidence, await self.fallback.diagnose(user_problem, evidence)

        evidence = self._collect_evidence(requested)
        try:
            diagnosis = await self.harness.diagnose(user_problem, evidence)
        except (httpx.HTTPError, KeyError, TypeError, ValidationError, ValueError):
            diagnosis = await self.fallback.diagnose(user_problem, evidence)
        return evidence, diagnosis

    @staticmethod
    def _collect_evidence(requested: set[str]) -> list[Evidence]:
        evidence: list[Evidence] = []
        if "performance" in requested:
            evidence.extend(diagnose_performance())
        if "system_health" in requested:
            evidence.extend(check_system_health())
        if "crash" in requested:
            evidence.extend(investigate_crashes())
        if "optimization" in requested:
            evidence.extend(analyze_windows_optimization())
        if "privacy" in requested:
            evidence.extend(analyze_privacy())
        return evidence
