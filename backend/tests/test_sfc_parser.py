import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.executor.sfc_parser import SfcParsedStatus, parse_sfc_output


class SfcParserTest(unittest.TestCase):
    def test_no_integrity_violations(self) -> None:
        stdout = "Beginning system scan. This process will take some time.\nWindows Resource Protection did not find any integrity violations."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.NO_CORRUPTION_FOUND)
        self.assertFalse(res.corruption_found)
        self.assertFalse(res.repaired)
        self.assertIn("did not find any integrity violations", res.message)

    def test_corrupt_files_repaired(self) -> None:
        stdout = "Windows Resource Protection found corrupt files and successfully repaired them.\nDetails are included in the CBS.Log windir\\Logs\\CBS\\CBS.log."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.CORRUPTION_REPAIRED)
        self.assertTrue(res.corruption_found)
        self.assertTrue(res.repaired)
        self.assertIn("successfully repaired", res.message)

    def test_corrupt_files_not_repaired(self) -> None:
        stdout = "Windows Resource Protection found corrupt files but was unable to fix some of them.\nDetails are included in the CBS.Log."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.CORRUPTION_FOUND_NOT_REPAIRED)
        self.assertTrue(res.corruption_found)
        self.assertFalse(res.repaired)
        self.assertIn("unable to fix some of them", res.message)

    def test_operation_failed(self) -> None:
        stdout = "Windows Resource Protection could not perform the requested operation."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.EXECUTION_FAILED)
        self.assertIsNone(res.corruption_found)
        self.assertIsNone(res.repaired)

    def test_permission_denied(self) -> None:
        stdout = "You must be an administrator running a console session in order to use the sfc utility."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.PERMISSION_DENIED)
        self.assertIsNone(res.corruption_found)
        self.assertIsNone(res.repaired)

    def test_empty_output(self) -> None:
        res = parse_sfc_output("", "")
        self.assertEqual(res.status, SfcParsedStatus.UNKNOWN_RESULT)
        self.assertIn("empty", res.message)

    def test_ambiguous_output_with_nonzero_exit_code(self) -> None:
        stdout = "Unrecognized error occurred."
        res = parse_sfc_output(stdout, "", exit_code=1)
        self.assertEqual(res.status, SfcParsedStatus.EXECUTION_FAILED)
        self.assertIn("error code 1", res.message)

    def test_ambiguous_output_with_zero_exit_code(self) -> None:
        stdout = "Some arbitrary text without standard SFC phrases."
        res = parse_sfc_output(stdout, "", exit_code=0)
        self.assertEqual(res.status, SfcParsedStatus.UNKNOWN_RESULT)

    def test_case_insensitive_matching(self) -> None:
        stdout = "WINDOWS RESOURCE PROTECTION DID NOT FIND ANY INTEGRITY VIOLATIONS."
        res = parse_sfc_output(stdout, "")
        self.assertEqual(res.status, SfcParsedStatus.NO_CORRUPTION_FOUND)

    def test_stderr_parsing(self) -> None:
        stderr = "Access is denied. Administrator privileges required."
        res = parse_sfc_output("", stderr)
        self.assertEqual(res.status, SfcParsedStatus.PERMISSION_DENIED)


if __name__ == "__main__":
    unittest.main()
