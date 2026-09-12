"""Tests for read-only Resource Hog Detection diagnostic feature."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import psutil

from app.agent.winfix_agent import DeterministicHarness
from app.diagnostics.performance import diagnose_performance
from app.diagnostics.resource_hog import (
    KIND_RESOURCE_HOG_ANALYSIS,
    aggregate_and_score_processes,
    collect_process_metrics,
    detect_resource_hogs,
)
from app.schemas.evidence import Evidence, EvidenceCategory, Severity


def test_collect_process_metrics_real():
    """Verify collect_process_metrics runs a 2-pass sample on current OS processes without failing."""
    metrics = collect_process_metrics(sample_interval=0.1)
    assert isinstance(metrics, list)
    if metrics:
        item = metrics[0]
        assert "pid" in item
        assert "name" in item
        assert "raw_cpu_percent" in item
        assert "memory_bytes" in item
        assert "memory_mb" in item
        assert "memory_percent" in item


def test_aggregate_and_score_processes():
    """Test process grouping, multi-core CPU normalization, impact score formula, and severity classification."""
    raw_metrics = [
        {
            "pid": 101 + i,
            "name": "chrome.exe",
            "raw_cpu_percent": 10.0,
            "memory_bytes": 200 * 1024 * 1024,
            "memory_mb": 200.0,
            "memory_percent": 1.5,
            "status": "running",
        }
        for i in range(12)
    ]
    # Total raw CPU = 120%, Total memory = 2400 MB, Memory percent = 18.0%
    # On 4 logical cores: normalized CPU = min(100, 120 / 4) = 30.0%
    # Impact score = (30.0 * 0.6) + (18.0 * 0.4) = 18.0 + 7.2 = 25.2 -> HIGH
    aggregated = aggregate_and_score_processes(raw_metrics, logical_cores=4)

    assert len(aggregated) == 1
    app = aggregated[0]
    assert app["name"] == "chrome.exe"
    assert app["process_count"] == 12
    assert app["raw_cpu_percent"] == 120.0
    assert app["normalized_cpu_percent"] == 30.0
    assert app["memory_mb"] == 2400.0
    assert app["memory_percent"] == 18.0
    assert app["impact_score"] == 25.2
    assert app["impact"] == "HIGH"


def test_severity_thresholds():
    """Verify HIGH, MEDIUM, LOW impact classification rules."""
    raw_high = [{"pid": 1, "name": "heavy.exe", "raw_cpu_percent": 100.0, "memory_bytes": 1024**3, "memory_mb": 1024.0, "memory_percent": 25.0}]
    agg_high = aggregate_and_score_processes(raw_high, logical_cores=2)
    assert agg_high[0]["impact"] == "HIGH"

    raw_medium = [{"pid": 2, "name": "med.exe", "raw_cpu_percent": 40.0, "memory_bytes": 500 * 1024**2, "memory_mb": 500.0, "memory_percent": 12.0}]
    agg_medium = aggregate_and_score_processes(raw_medium, logical_cores=2)
    # Normalized CPU = 20.0%, Memory = 12.0% -> Score = (20*0.6) + (12*0.4) = 12.0 + 4.8 = 16.8 -> MEDIUM
    assert agg_medium[0]["impact"] == "MEDIUM"

    raw_low = [{"pid": 3, "name": "idle.exe", "raw_cpu_percent": 1.0, "memory_bytes": 50 * 1024**2, "memory_mb": 50.0, "memory_percent": 1.0}]
    agg_low = aggregate_and_score_processes(raw_low, logical_cores=4)
    assert agg_low[0]["impact"] == "LOW"


def test_detect_resource_hogs_evidence():
    """Verify detect_resource_hogs returns Evidence with stable kind identifier and Top-5 bounded lists."""
    evidence = detect_resource_hogs(sample_interval=0.1)
    assert isinstance(evidence, Evidence)
    assert evidence.category == EvidenceCategory.PERFORMANCE
    assert evidence.data.get("kind") == KIND_RESOURCE_HOG_ANALYSIS

    assert "top_cpu_consumers" in evidence.data
    assert "top_memory_consumers" in evidence.data
    assert "top_resource_consumers" in evidence.data

    assert len(evidence.data["top_cpu_consumers"]) <= 5
    assert len(evidence.data["top_memory_consumers"]) <= 5
    assert len(evidence.data["top_resource_consumers"]) <= 5


def test_diagnose_performance_includes_resource_hog():
    """Verify diagnose_performance includes the RESOURCE_HOG_ANALYSIS evidence."""
    evidences = diagnose_performance()
    kinds = [item.data.get("kind") for item in evidences if item.data]
    assert KIND_RESOURCE_HOG_ANALYSIS in kinds


@pytest.mark.asyncio
async def test_deterministic_harness_resource_hog_reasoning():
    """Verify DeterministicHarness uses stable kind identifier and non-overstating language for high resource consumers."""
    mock_evidence = Evidence(
        category=EvidenceCategory.PERFORMANCE,
        severity=Severity.WARNING,
        title="Resource Hog Detection",
        description="High resource usage observed.",
        source="psutil.process_iter",
        data={
            "kind": KIND_RESOURCE_HOG_ANALYSIS,
            "top_resource_consumers": [
                {
                    "name": "chrome.exe",
                    "process_count": 18,
                    "raw_cpu_percent": 85.0,
                    "normalized_cpu_percent": 21.25,
                    "memory_mb": 3200.0,
                    "memory_percent": 20.0,
                    "impact_score": 20.75,
                    "impact": "HIGH",
                }
            ],
        },
    )

    harness = DeterministicHarness()
    result = await harness.diagnose("My computer is slow", [mock_evidence])

    assert len(result.probable_causes) >= 1
    cause = result.probable_causes[0]
    assert "chrome.exe" in cause.title
    # Check for nuanced contributor phrasing (not "confirmed root cause")
    assert "strong observed contributor" in cause.explanation.lower()
    assert "chrome.exe" in cause.explanation


def test_access_denied_resilience():
    """Ensure processes throwing AccessDenied or NoSuchProcess are handled gracefully without breaking collection."""
    mock_proc_ok = MagicMock()
    mock_proc_ok.info = {"pid": 100, "name": "ok.exe"}
    mock_proc_ok.pid = 100
    mock_proc_ok.cpu_percent.side_effect = [0.0, 15.0]
    mock_proc_ok.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
    mock_proc_ok.memory_percent.return_value = 5.0
    mock_proc_ok.status.return_value = "running"

    mock_proc_denied = MagicMock()
    mock_proc_denied.info = {"pid": 4, "name": "System"}
    mock_proc_denied.cpu_percent.side_effect = psutil.AccessDenied(pid=4)

    with patch("psutil.process_iter", return_value=[mock_proc_ok, mock_proc_denied]):
        metrics = collect_process_metrics(sample_interval=0.01)
        assert len(metrics) == 1
        assert metrics[0]["name"] == "ok.exe"
