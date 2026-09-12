"""Read-only Resource Hog Detection diagnostic module.

Collects running process metrics via psutil using a single global 2-pass sampling cycle,
aggregates processes by normalized executable name, normalizes CPU usage against logical CPU cores,
calculates a deterministic Resource Impact Score, and classifies severity levels.
"""

from __future__ import annotations

import time
from typing import Any

import psutil

from app.schemas.evidence import Evidence, EvidenceCategory, Severity

KIND_RESOURCE_HOG_ANALYSIS = "RESOURCE_HOG_ANALYSIS"


def collect_process_metrics(sample_interval: float = 0.5) -> list[dict[str, Any]]:
    """Perform a global 2-pass CPU and memory sampling cycle across all accessible processes.
    
    Pass 1 initializes process CPU counters.
    Pass 2 reads delta CPU and memory usage after sample_interval seconds.
    """
    procs: list[tuple[psutil.Process, str]] = []

    # Pass 1: Baseline CPU counters
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name") or "unknown"
            proc.cpu_percent(interval=None)
            procs.append((proc, name))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sample_interval > 0:
        time.sleep(sample_interval)

    raw_metrics: list[dict[str, Any]] = []

    # Pass 2: Read CPU & memory deltas
    for proc, name in procs:
        try:
            raw_cpu = float(proc.cpu_percent(interval=None) or 0.0)
            mem_info = proc.memory_info()
            mem_bytes = int(mem_info.rss)
            mem_percent = float(proc.memory_percent() or 0.0)
            status = str(proc.status()) if hasattr(proc, "status") else "running"

            raw_metrics.append({
                "pid": proc.pid,
                "name": name,
                "raw_cpu_percent": round(raw_cpu, 1),
                "memory_bytes": mem_bytes,
                "memory_mb": round(mem_bytes / (1024 * 1024), 1),
                "memory_percent": round(mem_percent, 2),
                "status": status,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return raw_metrics


def aggregate_and_score_processes(
    raw_metrics: list[dict[str, Any]], logical_cores: int | None = None
) -> list[dict[str, Any]]:
    """Group processes by normalized executable name, compute normalized CPU %, impact score, and impact severity."""
    if logical_cores is None or logical_cores < 1:
        logical_cores = psutil.cpu_count() or 1

    grouped: dict[str, dict[str, Any]] = {}

    for item in raw_metrics:
        norm_name = (item["name"] or "unknown").strip()
        key = norm_name.lower()

        if key not in grouped:
            grouped[key] = {
                "name": norm_name,
                "process_count": 0,
                "pids": [],
                "raw_cpu_percent": 0.0,
                "memory_bytes": 0,
                "memory_mb": 0.0,
                "memory_percent": 0.0,
            }

        grouped[key]["process_count"] += 1
        grouped[key]["pids"].append(item["pid"])
        grouped[key]["raw_cpu_percent"] += item["raw_cpu_percent"]
        grouped[key]["memory_bytes"] += item["memory_bytes"]
        grouped[key]["memory_mb"] += item["memory_mb"]
        grouped[key]["memory_percent"] += item["memory_percent"]

    results: list[dict[str, Any]] = []

    for app_data in grouped.values():
        raw_cpu = round(app_data["raw_cpu_percent"], 1)
        mem_bytes = app_data["memory_bytes"]
        mem_mb = round(app_data["memory_mb"], 1)
        mem_percent = round(app_data["memory_percent"], 2)
        count = app_data["process_count"]

        # CPU Normalization: bounded by system core count
        normalized_cpu = round(min(100.0, raw_cpu / logical_cores), 1)

        # Resource Impact Score Formula
        impact_score = round(min(100.0, (normalized_cpu * 0.60) + (mem_percent * 0.40)), 1)

        # Impact Classification (evaluated on Normalized CPU % & Memory %)
        if impact_score >= 25.0 or normalized_cpu >= 30.0 or mem_percent >= 20.0:
            impact = "HIGH"
        elif impact_score >= 10.0 or normalized_cpu >= 15.0 or mem_percent >= 10.0:
            impact = "MEDIUM"
        else:
            impact = "LOW"

        results.append({
            "name": app_data["name"],
            "process_count": count,
            "pids": app_data["pids"][:5],  # Keep up to 5 representative PIDs
            "raw_cpu_percent": raw_cpu,
            "normalized_cpu_percent": normalized_cpu,
            "memory_bytes": mem_bytes,
            "memory_mb": mem_mb,
            "memory_percent": mem_percent,
            "impact_score": impact_score,
            "impact": impact,
        })

    return results


def detect_resource_hogs(sample_interval: float = 0.5) -> Evidence:
    """Collect process data, calculate resource hog scores, and return structured Evidence."""
    logical_cores = psutil.cpu_count() or 1
    system_cpu = psutil.cpu_percent(interval=None)
    system_mem = psutil.virtual_memory().percent

    raw_metrics = collect_process_metrics(sample_interval=sample_interval)
    app_summaries = aggregate_and_score_processes(raw_metrics, logical_cores=logical_cores)

    # Top-5 Bounded Lists
    top_cpu = sorted(app_summaries, key=lambda x: x["raw_cpu_percent"], reverse=True)[:5]
    top_memory = sorted(app_summaries, key=lambda x: x["memory_mb"], reverse=True)[:5]
    top_resource = sorted(app_summaries, key=lambda x: x["impact_score"], reverse=True)[:5]

    has_high_impact = any(item["impact"] == "HIGH" for item in top_resource)
    is_system_under_stress = system_cpu >= 85.0 or system_mem >= 85.0

    severity = Severity.WARNING if (has_high_impact or is_system_under_stress) else Severity.INFO

    if top_resource and top_resource[0]["impact"] in ("HIGH", "MEDIUM"):
        top_app = top_resource[0]
        desc = (
            f"Observed resource consumer {top_app['name']} ({top_app['process_count']} process"
            f"{'es' if top_app['process_count'] != 1 else ''}) with Raw CPU: {top_app['raw_cpu_percent']}%, "
            f"RAM: {top_app['memory_mb']} MB ({top_app['memory_percent']}%), Impact Score: {top_app['impact_score']} [{top_app['impact']}]."
        )
    else:
        desc = "No high-impact resource-hogging applications detected."

    data = {
        "kind": KIND_RESOURCE_HOG_ANALYSIS,
        "system_cpu_percent": round(system_cpu, 1),
        "system_memory_percent": round(system_mem, 1),
        "logical_cores": logical_cores,
        "top_cpu_consumers": top_cpu,
        "top_memory_consumers": top_memory,
        "top_resource_consumers": top_resource,
    }

    return Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=severity,
        title="Resource Hog Detection",
        description=desc,
        source="psutil.process_iter",
        data=data,
    )
