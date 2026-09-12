"""Read-only performance diagnostics. No shell commands are accepted or run here."""

from __future__ import annotations

import os
import platform
from pathlib import Path

import psutil

from app.schemas.evidence import Evidence, EvidenceCategory, Severity


from app.diagnostics.startup import get_startup_apps
from app.executor.temp_cleaner import get_demo_temp_dir, measure_temp_dir


def _temp_usage_bytes() -> int:
    bytes_count, _ = measure_temp_dir(get_demo_temp_dir())
    return bytes_count


def diagnose_performance() -> list[Evidence]:
    """Collect bounded, structured performance evidence using psutil and Windows APIs."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getenv("SystemDrive", "/"))
    processes = []
    for process in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = process.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu_percent": float(info["cpu_percent"] or 0),
                    "memory_percent": round(float(info["memory_percent"] or 0), 2),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top_processes = sorted(processes, key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)[:8]
    startup_diag = get_startup_apps()
    startup_entries = startup_diag.get("entries", [])
    active_count = startup_diag.get("enabled_count", 0)

    temp_bytes = _temp_usage_bytes()
    evidence = [
        Evidence(
            category=EvidenceCategory.PERFORMANCE,
            severity=Severity.WARNING if cpu_percent >= 85 else Severity.INFO,
            title="CPU utilization",
            description=f"Current CPU utilization is {cpu_percent:.1f}%.",
            source="psutil.cpu_percent",
            data={"cpu_percent": cpu_percent, "logical_cores": psutil.cpu_count()},
        ),
        Evidence(
            category=EvidenceCategory.PERFORMANCE,
            severity=Severity.WARNING if memory.percent >= 85 else Severity.INFO,
            title="Memory utilization",
            description=f"Memory utilization is {memory.percent:.1f}%.",
            source="psutil.virtual_memory",
            data={"percent": memory.percent, "available_bytes": memory.available, "total_bytes": memory.total},
        ),
        Evidence(
            category=EvidenceCategory.PERFORMANCE,
            severity=Severity.WARNING if disk.percent >= 90 else Severity.INFO,
            title="System drive capacity",
            description=f"System drive utilization is {disk.percent:.1f}%.",
            source="psutil.disk_usage",
            data={"percent": disk.percent, "free_bytes": disk.free, "total_bytes": disk.total},
        ),
        Evidence(
            category=EvidenceCategory.PERFORMANCE,
            severity=Severity.INFO,
            title="Top running processes",
            description="Processes ranked by current CPU and memory consumption.",
            source="psutil.process_iter",
            data={"processes": top_processes},
        ),
        Evidence(
            category=EvidenceCategory.PERFORMANCE,
            severity=Severity.WARNING if active_count >= 10 or any(e.get("is_demo") for e in startup_entries) else Severity.INFO,
            title="Startup applications",
            description=f"Found {active_count} active startup application{'s' if active_count != 1 else ''} in HKCU Run.",
            source="Windows Registry HKCU Run" if platform.system() == "Windows" else "unavailable outside Windows",
            data={"count": len(startup_entries), "enabled_count": active_count, "entries": startup_entries, "diagnostic": startup_diag},
        ),
        Evidence(
            category=EvidenceCategory.OPTIMIZATION,
            severity=Severity.WARNING if temp_bytes > 50 * 1024**2 else Severity.INFO,
            title="Temporary file usage",
            description=f"Size of files in temporary storage ({temp_bytes / (1024**2):.1f} MB).",
            source="filesystem temp directory scan",
            data={"bytes": temp_bytes},
        ),
    ]
    return evidence
