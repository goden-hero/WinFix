import asyncio
import os
import platform
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.diagnostics.startup import (
    DEMO_STARTUP_ENTRIES,
    get_startup_apps,
    is_demo_startup_entry,
    make_startup_entry_id,
    parse_startup_entry_id,
)
from app.executor.registry import ActionRegistry
from app.executor.startup_manager import disable_startup_app
from app.safety.validator import ActionValidationError, ActionValidator
from app.schemas.actions import ActionId, ApprovalDecision, ApprovalRequest, ExecutionResult, RecommendedAction
from app.schemas.session import CreateSessionRequest
from app.services.session_service import InvalidSessionStateError, SessionService


class DisableStartupAppTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.registry = ActionRegistry()
        self.validator = ActionValidator(self.registry)
        self.demo_entry_name = "WinFixDemoUpdater"
        self.demo_entry_id = make_startup_entry_id(self.demo_entry_name)
        self.demo_command = r"C:\Program Files\WinFixDemo\updater.exe"
        self.unrelated_name = "WinFixDemoAnalytics"
        self.unrelated_command = r"C:\Program Files\WinFixDemo\analytics.exe"

    def tearDown(self) -> None:
        # Clean up any test entries created in registry if on Windows
        if platform.system() == "Windows":
            try:
                import winreg

                run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
                    for name in [self.demo_entry_name, self.unrelated_name]:
                        try:
                            winreg.DeleteValue(key, name)
                        except OSError:
                            pass

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, disabled_path, 0, winreg.KEY_SET_VALUE) as key:
                    for name in [self.demo_entry_name, self.unrelated_name]:
                        try:
                            winreg.DeleteValue(key, name)
                        except OSError:
                            pass
            except Exception:
                pass

    # 1. Safety Tests
    def test_1_unknown_startup_entry_id_rejected(self) -> None:
        rec = RecommendedAction(
            action_id=ActionId.DISABLE_STARTUP_APP,
            reason="Disable startup",
            parameters={"startup_entry_id": "hkcu_run:NonExistentUnknownEntry12345"},
        )
        with self.assertRaises(ActionValidationError) as ctx:
            self.validator.validate_recommendation(rec)
        self.assertIn("not in the demo safe allowlist", str(ctx.exception))

    def test_2_malformed_startup_entry_id_rejected(self) -> None:
        invalid_ids = ["", "invalid_prefix", "hkcu_run:", "hklm_run:WinFixDemoUpdater"]
        for invalid_id in invalid_ids:
            rec = RecommendedAction(
                action_id=ActionId.DISABLE_STARTUP_APP,
                reason="Disable startup",
                parameters={"startup_entry_id": invalid_id},
            )
            with self.assertRaises(ActionValidationError):
                self.validator.validate_recommendation(rec)

    def test_3_non_hkcu_run_source_rejected(self) -> None:
        rec = RecommendedAction(
            action_id=ActionId.DISABLE_STARTUP_APP,
            reason="Disable startup",
            parameters={"startup_entry_id": "hklm_run:WinFixDemoUpdater"},
        )
        with self.assertRaises(ActionValidationError):
            self.validator.validate_recommendation(rec)

    def test_4_arbitrary_registry_paths_rejected(self) -> None:
        rec = RecommendedAction(
            action_id=ActionId.DISABLE_STARTUP_APP,
            reason="Disable startup",
            parameters={"startup_entry_id": "hkcu_run:WinFixDemoUpdater", "arbitrary_path": "HKLM\\System"},
        )
        with self.assertRaises(ActionValidationError):
            self.validator.validate_recommendation(rec)

    def test_5_execution_without_approval_rejected(self) -> None:
        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC startup is slow")
        session = session_service = service.create(req)

        with self.assertRaises(InvalidSessionStateError):
            service.execute(session.session_id)

    # 2. Diagnostic Tests
    def test_6_startup_diagnostic_returns_structured_entries(self) -> None:
        diag = get_startup_apps()
        self.assertIn("supported", diag)
        self.assertIn("entries", diag)
        self.assertIn("total_count", diag)
        self.assertIn("enabled_count", diag)
        self.assertIn("disabled_count", diag)

        if platform.system() == "Windows":
            self.assertTrue(diag["supported"])
        else:
            self.assertFalse(diag["supported"])

    def test_7_non_windows_platform_fails_gracefully(self) -> None:
        if platform.system() != "Windows":
            diag = get_startup_apps()
            self.assertFalse(diag["supported"])
            self.assertIn("not supported", diag["message"])

            res = disable_startup_app("hkcu_run:WinFixDemoUpdater")
            self.assertEqual(res.status, "failed")
            self.assertIn("only supported on Windows", res.message)

    # 3. Execution Tests (Windows-native)
    def test_8_approved_demo_entry_disabled(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only registry execution test")

        import winreg

        # Create demo entry in HKCU Run
        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        res = disable_startup_app(self.demo_entry_id)
        self.assertEqual(res.status, "success")
        self.assertEqual(res.details["name"], self.demo_entry_name)
        self.assertEqual(res.details["state_before"], "ENABLED")
        self.assertEqual(res.details["state_after"], "DISABLED")
        self.assertEqual(res.details["command"], self.demo_command)

    def test_9_original_command_value_preserved_in_backup(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only registry test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        disable_startup_app(self.demo_entry_id)

        # Verify entry was deleted from Run
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_READ) as key:
            with self.assertRaises(OSError):
                winreg.QueryValueEx(key, self.demo_entry_name)

        # Verify entry exists in RunDisabled with identical command
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, disabled_path, 0, winreg.KEY_READ) as key:
            cmd, _ = winreg.QueryValueEx(key, self.demo_entry_name)
            self.assertEqual(cmd, self.demo_command)

    def test_10_unrelated_startup_entries_remain_unchanged(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only registry test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)
            winreg.SetValueEx(key, self.unrelated_name, 0, winreg.REG_SZ, self.unrelated_command)

        disable_startup_app(self.demo_entry_id)

        # Verify unrelated entry remains in active Run key with untouched command
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_READ) as key:
            unrelated_cmd, _ = winreg.QueryValueEx(key, self.unrelated_name)
            self.assertEqual(unrelated_cmd, self.unrelated_command)

    # 4. Verification Tests
    async def test_11_12_verification_independently_reads_registry_and_verifies(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only verification test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)
            winreg.SetValueEx(key, self.unrelated_name, 0, winreg.REG_SZ, self.unrelated_command)

        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC is slow to start")
        session = service.create(req)

        rec = RecommendedAction(
            action_id=ActionId.DISABLE_STARTUP_APP,
            reason="Disable demo updater",
            parameters={"startup_entry_id": self.demo_entry_id},
        )
        diagnosis = await service.agent.fallback.diagnose(session.user_problem, [])
        diagnosis.recommended_actions = [rec]
        session.diagnosis = diagnosis
        session.status = session.status.AWAITING_APPROVAL
        service._save(session)

        # Approve
        service.approve(
            session.session_id,
            ApprovalRequest(decisions=[ApprovalDecision(action_id=ActionId.DISABLE_STARTUP_APP, approved=True)]),
        )

        # Execute
        executed_session = service.execute(session.session_id)
        self.assertEqual(len(executed_session.execution_results), 1)
        self.assertEqual(executed_session.execution_results[0].status, "success")

        # Verify independently
        verified_session = service.verify(session.session_id)
        self.assertEqual(len(verified_session.verification_results), 1)
        v_res = verified_session.verification_results[0]
        self.assertEqual(v_res.status.value, "verified")
        self.assertIn("Independent verification confirmed", v_res.summary)
        self.assertEqual(v_res.after["targeted_entry"], "DISABLED")

    def test_13_verification_reports_failed_if_entry_remains_enabled(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only verification test")

        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC is slow to start")
        session = service.create(req)

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        # Fake execution result claiming success without actual deletion
        fake_result = ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="success",
            message="Fake success",
            details={
                "name": self.demo_entry_name,
                "command": self.demo_command,
                "enabled_entries_before": 1,
                "total_entries_before": 1,
                "unrelated_entries_before": {},
            },
        )
        session.execution_results = [fake_result]
        session.status = session.status.VERIFYING
        service._save(session)

        # Independent verification must detect that entry is still in Run and report FAILED
        verified_session = service.verify(session.session_id)
        v_res = verified_session.verification_results[0]
        self.assertEqual(v_res.status.value, "failed")
        self.assertIn("Verification failed", v_res.summary)

    # 5. Collision & Rollback Tests
    def test_14_collision_in_rundisabled_different_command_rejected(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only collision test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, disabled_path) as disabled_key:
            winreg.SetValueEx(disabled_key, self.demo_entry_name, 0, winreg.REG_SZ, r"C:\different\path.exe")

        res = disable_startup_app(self.demo_entry_id)
        self.assertEqual(res.status, "failed")
        self.assertIn("Collision detected", res.message)

    def test_15_same_command_collision_allowed(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only collision test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, disabled_path) as disabled_key:
            winreg.SetValueEx(disabled_key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        res = disable_startup_app(self.demo_entry_id)
        self.assertEqual(res.status, "success")

    def test_16_deletion_failure_after_backup_triggers_rollback(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only rollback test")

        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.demo_entry_name, 0, winreg.REG_SZ, self.demo_command)

        # Mock DeleteValue to fail with OSError on deleting from Run
        original_delete_value = winreg.DeleteValue

        def mock_delete_value(key_handle, value_name):
            # If attempting to delete from Run, raise OSError
            if value_name == self.demo_entry_name:
                raise OSError("Access denied simulation")
            return original_delete_value(key_handle, value_name)

        with patch("winreg.DeleteValue", side_effect=mock_delete_value):
            res = disable_startup_app(self.demo_entry_id)

        self.assertEqual(res.status, "failed")
        self.assertIn("Rolled back", res.message)

    def test_17_verification_fails_if_command_changed_in_backup(self) -> None:
        if platform.system() != "Windows":
            self.skipTest("Windows-only verification test")

        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC is slow to start")
        session = service.create(req)

        fake_result = ExecutionResult(
            action_id=ActionId.DISABLE_STARTUP_APP,
            status="success",
            message="Fake success",
            details={
                "name": self.demo_entry_name,
                "command": r"C:\original\command.exe",  # Expected command
                "enabled_entries_before": 1,
                "total_entries_before": 1,
                "unrelated_entries_before": {},
            },
        )
        session.execution_results = [fake_result]
        session.status = session.status.VERIFYING
        service._save(session)

        # Put a different command in RunDisabled
        import winreg

        disabled_path = r"Software\Microsoft\Windows\CurrentVersion\RunDisabled"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, disabled_path) as disabled_key:
            winreg.SetValueEx(disabled_key, self.demo_entry_name, 0, winreg.REG_SZ, r"C:\different\command.exe")

        verified_session = service.verify(session.session_id)
        v_res = verified_session.verification_results[0]
        self.assertEqual(v_res.status.value, "failed")


if __name__ == "__main__":
    unittest.main()
