import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.winfix_agent import WinFixAgent, DeterministicHarness
from app.diagnostics.windows_update import (
    diagnose_windows_update,
    default_service_checker,
    default_registry_reader,
    default_directory_checker,
    FIXED_WINDOWS_UPDATE_SERVICES,
)
from app.schemas.evidence import EvidenceCategory, Severity
from app.schemas.session import CreateSessionRequest, DiagnoseRequest
from app.services.session_service import SessionService


class WindowsUpdateDiagnosticsTest(unittest.IsolatedAsyncioTestCase):

    # 1. Platform Tests
    def test_non_windows_platform_returns_safe_result(self) -> None:
        with patch("platform.system", return_value="Linux"):
            evidence = diagnose_windows_update()
            self.assertEqual(len(evidence), 3)

            svc_ev = evidence[0]
            self.assertEqual(svc_ev.category, EvidenceCategory.WINDOWS_UPDATE)
            self.assertEqual(svc_ev.data["overall_service_health"], "not_applicable")
            self.assertFalse(svc_ev.data["is_windows"])

            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.data["status"], "NOT_APPLICABLE")

            cache_ev = evidence[2]
            self.assertIn("not applicable", cache_ev.description)

    def test_default_service_checker_on_non_windows(self) -> None:
        with patch("platform.system", return_value="Linux"):
            res = default_service_checker("wuauserv")
            self.assertEqual(res["status"], "unavailable")
            self.assertFalse(res["is_running"])
            self.assertIn("non-Windows", res["error"])

    def test_default_registry_reader_on_non_windows(self) -> None:
        with patch("platform.system", return_value="Linux"):
            pending, reasons, err = default_registry_reader()
            self.assertIsNone(pending)
            self.assertEqual(reasons, [])
            self.assertIn("non-Windows", err)

    # 2. Service Status Tests
    def test_all_services_running_healthy(self) -> None:
        def mock_service_checker(svc_name: str):
            return {
                "name": svc_name,
                "display_name": f"{svc_name} Display",
                "status": "running",
                "startup_type": "automatic",
                "is_running": True,
                "error": None,
            }

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(service_checker=mock_service_checker)
            svc_ev = evidence[0]
            self.assertEqual(svc_ev.severity, Severity.INFO)
            self.assertEqual(svc_ev.data["overall_service_health"], "healthy")
            self.assertTrue(all(s["is_running"] for s in svc_ev.data["services"].values()))

    def test_wuauserv_stopped_critical_warning(self) -> None:
        def mock_service_checker(svc_name: str):
            if svc_name == "wuauserv":
                return {"name": "wuauserv", "display_name": "Windows Update Service", "status": "stopped", "startup_type": "disabled", "is_running": False, "error": None}
            return {"name": svc_name, "display_name": svc_name, "status": "running", "startup_type": "automatic", "is_running": True, "error": None}

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(service_checker=mock_service_checker)
            svc_ev = evidence[0]
            self.assertEqual(svc_ev.severity, Severity.CRITICAL)
            self.assertEqual(svc_ev.data["overall_service_health"], "problem_detected")
            self.assertIn("Windows Update Service (stopped)", svc_ev.description)

    def test_wuauserv_missing(self) -> None:
        def mock_service_checker(svc_name: str):
            if svc_name == "wuauserv":
                return {"name": "wuauserv", "display_name": "Windows Update Service", "status": "missing", "startup_type": "unknown", "is_running": False, "error": "Service not found"}
            return {"name": svc_name, "display_name": svc_name, "status": "running", "startup_type": "automatic", "is_running": True, "error": None}

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(service_checker=mock_service_checker)
            svc_ev = evidence[0]
            self.assertEqual(svc_ev.severity, Severity.CRITICAL)
            self.assertEqual(svc_ev.data["overall_service_health"], "problem_detected")

    def test_bits_or_cryptsvc_stopped(self) -> None:
        def mock_service_checker(svc_name: str):
            if svc_name == "BITS":
                return {"name": "BITS", "display_name": "Background Intelligent Transfer Service", "status": "stopped", "startup_type": "manual", "is_running": False, "error": None}
            return {"name": svc_name, "display_name": svc_name, "status": "running", "startup_type": "automatic", "is_running": True, "error": None}

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(service_checker=mock_service_checker)
            svc_ev = evidence[0]
            self.assertEqual(svc_ev.severity, Severity.WARNING)
            self.assertEqual(svc_ev.data["overall_service_health"], "warning")
            self.assertIn("Background Intelligent Transfer Service (stopped)", svc_ev.description)

    def test_service_checker_permission_error(self) -> None:
        def mock_service_checker(svc_name: str):
            return {"name": svc_name, "display_name": svc_name, "status": "unavailable", "startup_type": "unknown", "is_running": False, "error": "Access denied"}

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(service_checker=mock_service_checker)
            svc_ev = evidence[0]
            self.assertIn("unavailable", svc_ev.description)

    # 3. Reboot Tests
    def test_pending_reboot_cbs_indicator(self) -> None:
        def mock_registry_reader():
            return True, ["CBS RebootPending registry key exists"], None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(registry_reader=mock_registry_reader)
            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.severity, Severity.WARNING)
            self.assertTrue(reboot_ev.data["pending_reboot"])
            self.assertEqual(reboot_ev.data["status"], "REBOOT_PENDING")
            self.assertIn("CBS RebootPending", reboot_ev.description)

    def test_pending_reboot_wu_indicator(self) -> None:
        def mock_registry_reader():
            return True, ["WindowsUpdate RebootRequired registry key exists"], None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(registry_reader=mock_registry_reader)
            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.severity, Severity.WARNING)
            self.assertTrue(reboot_ev.data["pending_reboot"])
            self.assertEqual(reboot_ev.data["status"], "REBOOT_PENDING")
            self.assertIn("WindowsUpdate RebootRequired", reboot_ev.description)

    def test_pending_reboot_file_rename_indicator(self) -> None:
        def mock_registry_reader():
            return True, ["PendingFileRenameOperations registry value exists"], None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(registry_reader=mock_registry_reader)
            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.severity, Severity.WARNING)
            self.assertTrue(reboot_ev.data["pending_reboot"])
            self.assertEqual(reboot_ev.data["status"], "REBOOT_PENDING")
            self.assertIn("PendingFileRenameOperations", reboot_ev.description)

    def test_no_pending_reboot(self) -> None:
        def mock_registry_reader():
            return False, [], None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(registry_reader=mock_registry_reader)
            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.severity, Severity.INFO)
            self.assertFalse(reboot_ev.data["pending_reboot"])
            self.assertEqual(reboot_ev.data["status"], "NO_REBOOT_PENDING")

    def test_registry_access_denied_returns_unknown(self) -> None:
        def mock_registry_reader():
            return None, [], "Access denied reading HKLM registry"

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(registry_reader=mock_registry_reader)
            reboot_ev = evidence[1]
            self.assertEqual(reboot_ev.severity, Severity.WARNING)
            self.assertIsNone(reboot_ev.data["pending_reboot"])
            self.assertEqual(reboot_ev.data["status"], "UNKNOWN")
            self.assertIn("Access denied", reboot_ev.data["error_message"])

    # 4. Cache Tests
    def test_cache_directory_exists_and_accessible(self) -> None:
        def mock_directory_checker(target_path: Path):
            return True, True, 10485760, 15, None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(directory_checker=mock_directory_checker)
            cache_ev = evidence[2]
            self.assertEqual(cache_ev.severity, Severity.INFO)
            self.assertTrue(cache_ev.data["cache_exists"])
            self.assertTrue(cache_ev.data["cache_accessible"])
            self.assertEqual(cache_ev.data["cache_size_bytes"], 10485760)

    def test_cache_directory_missing(self) -> None:
        def mock_directory_checker(target_path: Path):
            return False, False, 0, 0, None

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(directory_checker=mock_directory_checker)
            cache_ev = evidence[2]
            self.assertEqual(cache_ev.severity, Severity.WARNING)
            self.assertFalse(cache_ev.data["cache_exists"])
            self.assertIn("does not exist", cache_ev.description)

    def test_cache_directory_inaccessible(self) -> None:
        def mock_directory_checker(target_path: Path):
            return True, False, 0, 0, "Permission denied opening directory"

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            evidence = diagnose_windows_update(directory_checker=mock_directory_checker)
            cache_ev = evidence[2]
            self.assertEqual(cache_ev.severity, Severity.WARNING)
            self.assertFalse(cache_ev.data["cache_accessible"])
            self.assertIn("Permission denied", cache_ev.data["error_message"])

    # 5. Safety Requirements Tests
    def test_read_only_guarantee_no_remediation_recommended(self) -> None:
        evidence = diagnose_windows_update(
            service_checker=lambda s: {"name": s, "display_name": s, "status": "stopped", "startup_type": "disabled", "is_running": False, "error": None},
            registry_reader=lambda: (True, ["CBS RebootPending"], None),
            directory_checker=lambda p: (True, True, 50000, 10, None),
        )
        harness = DeterministicHarness()
        import asyncio
        result = asyncio.run(harness.diagnose("Windows Update failed", evidence))
        # Ensure no remediation action is recommended for Windows Update in Stage 1
        wu_recs = [rec for rec in result.recommended_actions if "update" in rec.action_id.value]
        self.assertEqual(len(wu_recs), 0)

    # 6. Agent & Workflow Integration Tests
    async def test_session_service_diagnoses_windows_update(self) -> None:
        service = SessionService()
        req = CreateSessionRequest(user_problem="Windows Update fails with error")
        session = service.create(req)

        diagnosed = await service.diagnose(session.session_id, request=DiagnoseRequest(categories=["windows_update"]))
        self.assertIsNotNone(diagnosed.diagnosis)

        wu_ev = [ev for ev in diagnosed.evidence if ev.category == EvidenceCategory.WINDOWS_UPDATE]
        self.assertEqual(len(wu_ev), 3)

    async def test_agent_auto_detects_update_keywords(self) -> None:
        agent = WinFixAgent()
        evidence, diagnosis = await agent.investigate("Windows Update service wuauserv fails to download patches", categories=["performance"])
        wu_ev = [ev for ev in evidence if ev.category == EvidenceCategory.WINDOWS_UPDATE]
        self.assertGreater(len(wu_ev), 0)


if __name__ == "__main__":
    unittest.main()
