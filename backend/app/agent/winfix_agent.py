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
    collect_battery_diagnostics,
    diagnose_performance,
    diagnose_windows_update,
    investigate_crashes,
)
from app.schemas.actions import ActionId, RecommendedAction
from app.schemas.diagnosis import DiagnosisResult, Finding, ProbableCause
from app.schemas.evidence import Evidence, EvidenceCategory, Severity


class AgentHarness(Protocol):
    """Pi integration needs only to fulfill this boundary."""

    async def diagnose(self, problem: str, evidence: list[Evidence]) -> DiagnosisResult: ...


class GroqHarness:
    """Direct Groq API adapter using OpenAI-compatible chat completions."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("WINFIX_MODEL", "llama-3.3-70b-versatile")
        self.base_url = "https://api.groq.com/openai/v1"

    async def diagnose(self, problem: str, evidence: list[Evidence]) -> DiagnosisResult:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        result = DiagnosisResult.model_validate_json(content)
        return result.model_copy(update={"generated_by": f"groq:{self.model}"})


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

        battery_ev = next(
            (item for item in evidence if item.data.get("kind") == "BATTERY_DIAGNOSIS" or item.category == EvidenceCategory.BATTERY),
            None,
        )
        if battery_ev:
            b_data = battery_ev.data
            b_status = b_data.get("status", "unknown")
            b_present = b_data.get("battery_present", False)
            b_warnings = b_data.get("warnings", [])
            b_limitations = b_data.get("limitations", [])

            if not b_present:
                findings.append(
                    Finding(
                        title="No battery detected",
                        description=battery_ev.description,
                        evidence_ids=[battery_ev.id],
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="Battery diagnostic snapshot collected",
                        description=battery_ev.description,
                        evidence_ids=[battery_ev.id],
                    )
                )
                if b_status in ("critical", "warning"):
                    causes.append(
                        ProbableCause(
                            title=f"Battery Alert ({b_status.title()})",
                            explanation=f"Battery evidence: {'; '.join(b_warnings) if b_warnings else battery_ev.description}",
                            evidence_ids=[battery_ev.id],
                            confidence=0.85 if b_status == "critical" else 0.70,
                        )
                    )
                for w in b_warnings:
                    findings.append(
                        Finding(
                            title="Battery Observation",
                            description=w,
                            evidence_ids=[battery_ev.id],
                        )
                    )
                for lim in b_limitations:
                    findings.append(
                        Finding(
                            title="Battery Metric Limitation",
                            description=lim,
                            evidence_ids=[battery_ev.id],
                        )
                    )

        resource_hog = next((item for item in evidence if item.data.get("kind") == "RESOURCE_HOG_ANALYSIS"), None)
        if resource_hog:
            top_resource_consumers = resource_hog.data.get("top_resource_consumers", [])
            high_or_med = [app for app in top_resource_consumers if app.get("impact") in ("HIGH", "MEDIUM")]
            if high_or_med:
                top_app = high_or_med[0]
                causes.append(
                    ProbableCause(
                        title=f"High resource consumption by {top_app['name']}",
                        explanation=(
                            f"Application '{top_app['name']}' ({top_app['process_count']} process{'es' if top_app['process_count'] != 1 else ''}) "
                            f"is a strong observed contributor to system load, consuming {top_app['raw_cpu_percent']}% CPU "
                            f"and {top_app['memory_mb']} MB RAM (Impact Score: {top_app['impact_score']} [{top_app['impact']}])."
                        ),
                        evidence_ids=[resource_hog.id],
                        confidence=0.85 if top_app["impact"] == "HIGH" else 0.70,
                    )
                )
                findings.append(
                    Finding(
                        title="Observed resource consumer bottleneck",
                        description=(
                            f"Identified {top_app['name']} as a major resource consumer "
                            f"({top_app['raw_cpu_percent']}% CPU, {top_app['memory_mb']} MB RAM)."
                        ),
                        evidence_ids=[resource_hog.id],
                    )
                )

        memory = by_title.get("Memory utilization")
        if memory and memory.data.get("percent", 0) >= 85:
            causes.append(ProbableCause(title="High memory pressure", explanation="Available memory is low relative to installed memory.", evidence_ids=[memory.id], confidence=0.85))
            findings.append(Finding(title="Memory use is elevated", description=memory.description, evidence_ids=[memory.id]))

        disk = by_title.get("System drive capacity")
        if disk and disk.data.get("percent", 0) >= 90:
            causes.append(ProbableCause(title="Low system drive capacity", explanation="A nearly full system drive can slow updates and temporary-file workloads.", evidence_ids=[disk.id], confidence=0.8))
            recommendations.append(RecommendedAction(action_id=ActionId.CLEAR_TEMP_FILES, reason="Temporary storage can be reclaimed through an approved, bounded cleanup.", evidence_ids=[disk.id]))

        startup = by_title.get("Startup applications") or next((item for item in evidence if "startup" in item.title.lower()), None)
        if startup:
            entries = startup.data.get("entries", [])
            enabled_entries = [e for e in entries if e.get("enabled")]
            demo_active = [e for e in entries if e.get("is_demo") and e.get("enabled")]
            target_entry = demo_active[0] if demo_active else (enabled_entries[0] if enabled_entries else None)
            
            if target_entry:
                causes.append(ProbableCause(
                    title="Startup Overhead",
                    explanation=f"Application '{target_entry['name']}' starts automatically with Windows and contributes to background overhead.",
                    evidence_ids=[startup.id],
                    confidence=0.85 if demo_active else 0.75,
                ))
                recommendations.append(RecommendedAction(
                    action_id=ActionId.DISABLE_STARTUP_APP,
                    reason=f"Application '{target_entry['name']}' starts automatically with Windows and may contribute to sign-in delay and background resource load.",
                    evidence_ids=[startup.id],
                    parameters={"startup_entry_id": target_entry["id"]},
                ))
            elif startup.severity in (Severity.WARNING, Severity.CRITICAL) or startup.data.get("count", 0) >= 5:
                causes.append(ProbableCause(title="Startup applications load", explanation="Active startup entries increase sign-in and background system load.", evidence_ids=[startup.id], confidence=0.7))
                findings.append(Finding(title="Review startup load", description=startup.description, evidence_ids=[startup.id]))

        temp = by_title.get("Temporary file usage") or next((item for item in evidence if "temp" in item.title.lower()), None)
        if temp and (temp.data.get("bytes", 0) > 10 * 1024**2 or temp.severity in (Severity.WARNING, Severity.CRITICAL)):
            mb_size = temp.data.get("bytes", 0) / (1024**2)
            causes.append(ProbableCause(
                title="Temporary file accumulation",
                explanation=f"Temporary storage has accumulated {mb_size:.1f} MB of junk files.",
                evidence_ids=[temp.id],
                confidence=0.85,
            ))
            if not any(r.action_id == ActionId.CLEAR_TEMP_FILES for r in recommendations):
                recommendations.append(RecommendedAction(
                    action_id=ActionId.CLEAR_TEMP_FILES,
                    reason=f"Temporary storage can be reclaimed ({mb_size:.1f} MB) through an approved, bounded cleanup.",
                    evidence_ids=[temp.id],
                ))

        # Check for System Health, Core Services, Windows Update, or System File degradation
        problematic_evidence = [
            item for item in evidence
            if item.severity in (Severity.WARNING, Severity.CRITICAL) or item.category in (EvidenceCategory.SYSTEM_HEALTH, EvidenceCategory.CRASH)
        ]
        for issue in problematic_evidence:
            title_lower = issue.title.lower()
            if "update" in title_lower or "service" in title_lower or "component" in title_lower:
                causes.append(ProbableCause(
                    title=f"Core Service Issue: {issue.title}",
                    explanation=f"System evidence indicates a critical/warning issue in {issue.title}: {issue.description}",
                    evidence_ids=[issue.id],
                    confidence=0.85,
                ))
                if not any(r.action_id == ActionId.RUN_DISM_HEALTH_CHECK for r in recommendations):
                    recommendations.append(RecommendedAction(
                        action_id=ActionId.RUN_DISM_HEALTH_CHECK,
                        reason=f"Running a DISM health check can verify and service core Windows components ({issue.title}).",
                        evidence_ids=[issue.id],
                    ))
            elif "file" in title_lower or "integrity" in title_lower or "system" in title_lower or issue.category == EvidenceCategory.CRASH:
                causes.append(ProbableCause(
                    title=f"System Integrity Warning: {issue.title}",
                    explanation=f"System evidence reported an anomaly in {issue.title}: {issue.description}",
                    evidence_ids=[issue.id],
                    confidence=0.80,
                ))
                if not any(r.action_id == ActionId.RUN_SFC_SCAN for r in recommendations):
                    recommendations.append(RecommendedAction(
                        action_id=ActionId.RUN_SFC_SCAN,
                        reason=f"Running System File Checker (SFC) can verify and repair system files associated with {issue.title}.",
                        evidence_ids=[issue.id],
                    ))

        # Fallback safeguard: If non-battery warnings exist but no action was matched yet, provide standard safe remediation steps
        if not recommendations:
            non_battery_warnings = [e for e in evidence if e.severity in (Severity.WARNING, Severity.CRITICAL) and e.category != EvidenceCategory.BATTERY]
            if non_battery_warnings:
                target_ev = non_battery_warnings[0]
                recommendations.append(RecommendedAction(
                    action_id=ActionId.CLEAR_TEMP_FILES,
                    reason=f"Cleaning temporary files will free system resources and resolve background file junk ({target_ev.title}).",
                    evidence_ids=[target_ev.id],
                ))

        wu_services = by_title.get("Windows Update core services")
        if wu_services:
            if wu_services.data.get("overall_service_health") in ("problem_detected", "warning"):
                causes.append(ProbableCause(
                    title="Windows Update service issue",
                    explanation=f"{wu_services.description} Administrator privileges may be required for future service remediation. No system changes were made during diagnostics.",
                    evidence_ids=[wu_services.id],
                    confidence=0.85,
                ))
                findings.append(Finding(
                    title="Windows Update service status",
                    description=wu_services.description,
                    evidence_ids=[wu_services.id],
                ))
            else:
                findings.append(Finding(
                    title="Windows Update services healthy",
                    description=wu_services.description,
                    evidence_ids=[wu_services.id],
                ))

        wu_reboot = by_title.get("Windows Update pending reboot status")
        if wu_reboot and wu_reboot.data.get("pending_reboot") is True:
            causes.append(ProbableCause(
                title="Windows Update pending reboot required",
                explanation=wu_reboot.description,
                evidence_ids=[wu_reboot.id],
                confidence=0.8,
            ))
            findings.append(Finding(
                title="Pending system reboot detected",
                description=wu_reboot.description,
                evidence_ids=[wu_reboot.id],
            ))
        elif wu_reboot and wu_reboot.data.get("status") == "UNKNOWN":
            findings.append(Finding(
                title="Pending reboot status unknown",
                description=wu_reboot.description,
                evidence_ids=[wu_reboot.id],
            ))

        wu_cache = by_title.get("Windows Update download cache")
        if wu_cache:
            if wu_cache.data.get("cache_accessible") is False or wu_cache.data.get("error_message"):
                findings.append(Finding(
                    title="Windows Update cache inspection issue",
                    description=wu_cache.description,
                    evidence_ids=[wu_cache.id],
                ))
            else:
                findings.append(Finding(
                    title="Windows Update cache metadata collected",
                    description=wu_cache.description,
                    evidence_ids=[wu_cache.id],
                ))

        if not causes:
            causes.append(ProbableCause(title="No single bottleneck identified", explanation="The current snapshot does not establish a definitive root cause. Further observation may be needed.", evidence_ids=[item.id for item in evidence[:4]], confidence=0.45))
        if not findings:
            findings.append(Finding(title="Performance snapshot collected", description="CPU, memory, storage, processes, and startup data were collected without changing the system.", evidence_ids=[item.id for item in evidence]))

        return DiagnosisResult(
            summary="WinFix collected system evidence and generated recommended remediation steps for all identified issues.",
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
        if harness:
            self.harness = harness
        elif runtime == "groq":
            self.harness = GroqHarness()
        elif runtime == "direct_ollama":
            self.harness = OllamaQwenHarness()
        else:
            self.harness = PiAgentHarness()
        self.fallback = DeterministicHarness()

    async def investigate(self, user_problem: str, categories: list[str]) -> tuple[list[Evidence], DiagnosisResult]:
        requested = set(categories or ["performance"])
        problem_lower = user_problem.lower()
        if any(term in problem_lower for term in ["update", "wuauserv", "bits", "cryptsvc", "patch", "kb"]):
            requested.add("windows_update")
        battery_keywords = {"battery", "drain", "charge", "power source", "ac power", "plugged in", "battery life"}
        if any(kw in problem_lower for kw in battery_keywords):
            requested.add("battery")


        if isinstance(self.harness, PiAgentHarness) and requested == {"performance"}:
            try:
                return await self.harness.investigate_performance(user_problem)
            except (PiHarnessError, OSError, NotImplementedError):
                evidence = diagnose_performance()
                return evidence, await self.fallback.diagnose(user_problem, evidence)

        evidence = self._collect_evidence(requested)
        try:
            diagnosis = await self.harness.diagnose(user_problem, evidence)
        except (httpx.HTTPError, KeyError, TypeError, ValidationError, ValueError, AttributeError):
            diagnosis = await self.fallback.diagnose(user_problem, evidence)
        return evidence, diagnosis

    @staticmethod
    def _collect_evidence(requested: set[str]) -> list[Evidence]:
        evidence: list[Evidence] = []
        if "performance" in requested:
            evidence.extend(diagnose_performance())
        if "system_health" in requested:
            evidence.extend(check_system_health())
        if "windows_update" in requested:
            evidence.extend(diagnose_windows_update())
        if "crash" in requested:
            evidence.extend(investigate_crashes())
        if "optimization" in requested:
            evidence.extend(analyze_windows_optimization())
        if "privacy" in requested:
            evidence.extend(analyze_privacy())
        if "battery" in requested:
            evidence.append(collect_battery_diagnostics())
        return evidence

