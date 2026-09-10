import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.executor.temp_cleaner import clear_temp_files, get_demo_temp_dir, measure_temp_dir
from app.schemas.actions import ActionId, ApprovalDecision, ApprovalRequest, RecommendedAction
from app.schemas.session import CreateSessionRequest
from app.services.session_service import InvalidSessionStateError, SessionService


class ClearTempFilesExecutionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        os.environ["WINFIX_DEMO_TEMP_DIR"] = self.temp_dir_obj.name
        self.demo_root = get_demo_temp_dir()

    def tearDown(self) -> None:
        os.environ.pop("WINFIX_DEMO_TEMP_DIR", None)
        self.temp_dir_obj.cleanup()

    def test_cleanup_succeeds_inside_allowlisted_directory(self) -> None:
        # Populate demo directory with dummy files and subdirectories
        (self.demo_root / "junk1.tmp").write_text("Hello World 12345")
        sub_dir = self.demo_root / "nested"
        sub_dir.mkdir()
        (sub_dir / "junk2.tmp").write_text("More junk data")

        bytes_before, files_before = measure_temp_dir(self.demo_root)
        self.assertGreater(bytes_before, 0)
        self.assertEqual(files_before, 2)

        result = clear_temp_files()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.action_id, ActionId.CLEAR_TEMP_FILES)
        self.assertEqual(result.details["files_deleted"], 2)
        self.assertEqual(result.details["bytes_reclaimed"], bytes_before)
        self.assertEqual(result.details["file_count_after"], 0)
        self.assertEqual(result.details["bytes_after"], 0)

    def test_cleanup_cannot_escape_allowlisted_root(self) -> None:
        # Attempt to pass an arbitrary path parameter to executor
        service = SessionService()
        recommendation = RecommendedAction(
            action_id=ActionId.CLEAR_TEMP_FILES,
            reason="Clear temp",
            parameters={"target_path": "/etc"}
        )
        # Executor must reject unallowed parameter according to ActionValidator
        with self.assertRaises(Exception):
            service.executor.execute(recommendation, approved=True)

    def test_approval_required_before_execution(self) -> None:
        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC is slow")
        session = service.create(req)

        # Attempting execution on unapproved session must raise InvalidSessionStateError
        with self.assertRaises(InvalidSessionStateError):
            service.execute(session.session_id)

    async def test_verification_independently_measures_filesystem(self) -> None:
        # Create a file inside demo root
        test_file = self.demo_root / "to_be_cleaned.log"
        test_file.write_text("A" * 1024)

        service = SessionService()
        req = CreateSessionRequest(user_problem="My PC is slow")
        session = service.create(req)

        # Manually attach a diagnosis recommendation
        rec = RecommendedAction(action_id=ActionId.CLEAR_TEMP_FILES, reason="Cleanup temp junk")
        diagnosis = await service.agent.fallback.diagnose(session.user_problem, [])
        diagnosis.recommended_actions = [rec]
        session.diagnosis = diagnosis
        session.status = session.status.AWAITING_APPROVAL
        service._save(session)

        # Approve
        service.approve(session.session_id, ApprovalRequest(decisions=[ApprovalDecision(action_id=ActionId.CLEAR_TEMP_FILES, approved=True)]))

        # Execute
        executed_session = service.execute(session.session_id)
        self.assertEqual(len(executed_session.execution_results), 1)
        self.assertEqual(executed_session.execution_results[0].status, "success")

        # Verify
        verified_session = service.verify(session.session_id)
        self.assertEqual(len(verified_session.verification_results), 1)
        v_res = verified_session.verification_results[0]
        self.assertEqual(v_res.status.value, "verified")
        self.assertIn("Independent verification confirmed", v_res.summary)
        self.assertEqual(v_res.after["files"], 0)

    def test_locked_file_handling(self) -> None:
        if os.name != "nt":
            # Symlink / permission test on non-Windows
            locked_dir = self.demo_root / "unwritable"
            locked_dir.mkdir()
            (locked_dir / "normal.txt").write_text("data")
            os.chmod(locked_dir, 0o555)

            try:
                result = clear_temp_files()
                self.assertIn(result.status, {"partial_success", "success"})
            finally:
                os.chmod(locked_dir, 0o755)


if __name__ == "__main__":
    unittest.main()
