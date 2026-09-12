import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.executor.registry import ActionRegistry
from app.executor.sfc_parser import SfcParsedStatus
from app.executor.sfc_runner import SfcRunner
from app.executor.winutil_adapter import NativeWindowsAdapter
from app.safety.validator import ActionValidationError, ActionValidator
from app.schemas.actions import ActionId, RecommendedAction, RiskLevel


class SfcRunnerAndSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ActionRegistry()
        self.validator = ActionValidator(self.registry)
        self.dummy_sfc_path = Path(__file__).resolve()  # existing file to pass existence check

    # 1. Action Registration & Schema Tests
    def test_action_registered_with_correct_metadata(self) -> None:
        definition = self.registry.get(ActionId.RUN_SFC_SCAN)
        self.assertEqual(definition.action_id, ActionId.RUN_SFC_SCAN)
        self.assertEqual(definition.name, "Run System File Checker")
        self.assertEqual(definition.risk_level, RiskLevel.MEDIUM)
        self.assertTrue(definition.requires_approval)
        self.assertTrue(definition.enabled)
        self.assertEqual(definition.parameter_schema, {"type": "object", "properties": {}, "additionalProperties": False})

    # 2. Safety & Validation Tests
    def test_valid_empty_parameters_accepted(self) -> None:
        rec = RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="System repair scan", parameters={})
        # Should not raise exception
        self.validator.validate_recommendation(rec)

    def test_unexpected_parameters_rejected(self) -> None:
        unallowed_params = [
            {"command": "sfc.exe /scannow"},
            {"executable": "C:\\Windows\\System32\\cmd.exe"},
            {"args": ["/scannow"]},
            {"timeout": 100},
            {"shell": True},
            {"powershell": "Get-Process"},
            {"arbitrary_arg": "value"},
        ]
        for params in unallowed_params:
            rec = RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="Scan", parameters=params)
            with self.assertRaises(ActionValidationError) as ctx:
                self.validator.validate_recommendation(rec)
            self.assertIn("RUN_SFC_SCAN action does not accept parameters", str(ctx.exception))

    def test_non_dict_parameters_rejected(self) -> None:
        rec = RecommendedAction(action_id=ActionId.RUN_SFC_SCAN, reason="Scan", parameters={})
        rec.parameters = "invalid_string_param"  # type: ignore
        with self.assertRaises(ActionValidationError) as ctx:
            self.validator.validate_recommendation(rec)
        self.assertIn("parameters must be a dictionary", str(ctx.exception))

    # 3. Adapter & Execution Isolation Tests
    def test_non_windows_platform_returns_failed_status(self) -> None:
        with patch("platform.system", return_value="Linux"), patch("os.name", "posix"):
            runner = SfcRunner(
                process_runner=lambda exe, args, timeout: (0, "did not find any integrity violations", ""),
                admin_checker=lambda: True,
                sfc_path=self.dummy_sfc_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.details["reason"], "unsupported_platform")
            self.assertIn("only supported on Windows", result.message)

    def test_missing_executable_returns_failed_status(self) -> None:
        missing_path = Path(r"C:\NonExistentDirectory12345\sfc.exe")
        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=lambda exe, args, timeout: (0, "ok", ""),
                admin_checker=lambda: True,
                sfc_path=missing_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.details["reason"], "missing_executable")
            self.assertIn("not found", result.message)

    def test_unprivileged_admin_check_returns_permission_denied(self) -> None:
        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=lambda exe, args, timeout: (0, "ok", ""),
                admin_checker=lambda: False,
                sfc_path=self.dummy_sfc_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.details["parsed_status"], SfcParsedStatus.PERMISSION_DENIED.value)
            self.assertIn("Administrator privileges are required", result.message)

    def test_successful_scan_clean(self) -> None:
        def fake_runner(executable: str, args: list[str], timeout: float):
            # Assert caller cannot tamper with executable or args
            self.assertEqual(executable, str(self.dummy_sfc_path))
            self.assertEqual(args, ["/scannow"])
            return 0, "Windows Resource Protection did not find any integrity violations.", ""

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=fake_runner,
                admin_checker=lambda: True,
                sfc_path=self.dummy_sfc_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "success")
            self.assertEqual(result.details["parsed_status"], SfcParsedStatus.NO_CORRUPTION_FOUND.value)
            self.assertFalse(result.details["corruption_found"])
            self.assertFalse(result.details["repaired"])

    def test_successful_scan_repaired(self) -> None:
        def fake_runner(executable: str, args: list[str], timeout: float):
            return 0, "Windows Resource Protection found corrupt files and successfully repaired them.", ""

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=fake_runner,
                admin_checker=lambda: True,
                sfc_path=self.dummy_sfc_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "success")
            self.assertEqual(result.details["parsed_status"], SfcParsedStatus.CORRUPTION_REPAIRED.value)
            self.assertTrue(result.details["corruption_found"])
            self.assertTrue(result.details["repaired"])

    def test_scan_corrupt_files_unfixable(self) -> None:
        def fake_runner(executable: str, args: list[str], timeout: float):
            return 0, "Windows Resource Protection found corrupt files but was unable to fix some of them.", ""

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=fake_runner,
                admin_checker=lambda: True,
                sfc_path=self.dummy_sfc_path,
            )
            result = runner.execute()
            self.assertEqual(result.status, "partial_success")
            self.assertEqual(result.details["parsed_status"], SfcParsedStatus.CORRUPTION_FOUND_NOT_REPAIRED.value)
            self.assertTrue(result.details["corruption_found"])
            self.assertFalse(result.details["repaired"])

    def test_scan_timeout_handled(self) -> None:
        import subprocess

        def fake_timeout_runner(executable: str, args: list[str], timeout: float):
            raise subprocess.TimeoutExpired(cmd=[executable] + args, timeout=timeout)

        with patch("platform.system", return_value="Windows"), patch("os.name", "nt"):
            runner = SfcRunner(
                process_runner=fake_timeout_runner,
                admin_checker=lambda: True,
                sfc_path=self.dummy_sfc_path,
                timeout_seconds=5.0,
            )
            result = runner.execute()
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.details["parsed_status"], SfcParsedStatus.TIMEOUT.value)
            self.assertIn("timed out", result.message)

    def test_concurrent_execution_blocked(self) -> None:
        runner = SfcRunner(
            process_runner=lambda exe, args, timeout: (0, "ok", ""),
            admin_checker=lambda: True,
            sfc_path=self.dummy_sfc_path,
        )
        runner._lock.acquire()  # Simulate another thread running SFC
        try:
            result = runner.execute()
            self.assertEqual(result.status, "failed")
            self.assertIn("already in progress", result.message)
            self.assertEqual(result.details["reason"], "concurrent_execution_blocked")
        finally:
            runner._lock.release()

    def test_native_windows_adapter_dispatches_sfc(self) -> None:
        mock_sfc_runner = MagicMock()
        mock_sfc_runner.execute.return_value = "mock_sfc_result"
        adapter = NativeWindowsAdapter(sfc_runner=mock_sfc_runner)

        res = adapter.execute(ActionId.RUN_SFC_SCAN, {})
        self.assertEqual(res, "mock_sfc_result")
        mock_sfc_runner.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
