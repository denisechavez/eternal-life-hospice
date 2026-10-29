#!/usr/bin/env python3
"""Network-free checks of the real contact-suite completion entry points."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import runpy
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


BASE = Path(__file__).resolve().parent
RUNNERS = ("test-website-phone-config.py", "test-website-phone.py",
           "test-footer-contact.py")


def application_stubs():
    """Only imports are stubbed; run_path executes each real __main__ block."""
    modules = {name: ModuleType(name) for name in
               ("form_antispam", "website_phone", "footer_contact", "fragments",
                "acknowledgments", "chat_api", "coverage_api", "form_intake",
                "devserver")}
    modules["devserver"].PrettyURLHandler = type("PrettyURLHandler", (), {})
    modules["website_phone"].MAIN_DISPLAY = "212.555.0199"
    modules["website_phone"].MAIN_TEL = "12125550199"
    modules["fragments"].FOOTER_HTML = ""
    return modules


def synthetic_result(tests_run, outcome):
    result = unittest.TestResult()
    result.testsRun = tests_run
    if outcome == "failure":
        result.failures.append(("synthetic test", "synthetic failure"))
    elif outcome == "error":
        result.errors.append(("synthetic test", "synthetic error"))
    elif outcome == "skip":
        result.skipped.append(("synthetic test", "synthetic skip"))
    return result


class ContactSuiteRunnerTests(unittest.TestCase):
    def test_completion_requires_successful_nonempty_unskipped_results(self):
        cases = (
            ("one passing test", 1, "success", True),
            ("multiple passing tests", 3, "success", True),
            ("assertion failure", 1, "failure", False),
            ("test error", 1, "error", False),
            ("only skipped test", 1, "skip", False),
            ("passing and skipped tests", 3, "skip", False),
            ("zero tests", 0, "success", False),
        )
        for filename in RUNNERS:
            for label, tests_run, outcome, passed in cases:
                with self.subTest(runner=filename, outcome=label):
                    result = synthetic_result(tests_run, outcome)
                    stdout, stderr = io.StringIO(), io.StringIO()
                    # No application imports, real suite execution or child
                    # processes: these checks cannot submit or rewrite a site.
                    with patch.dict("sys.modules", application_stubs()), \
                            patch("unittest.main", return_value=SimpleNamespace(result=result)) as main, \
                            patch("unittest.TestCase.run", side_effect=AssertionError("Real suite ran")), \
                            patch("subprocess.run", side_effect=AssertionError("Child process ran")), \
                            patch("socket.socket", side_effect=AssertionError("Network access")), \
                            redirect_stdout(stdout), redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exit_context:
                            runpy.run_path(str(BASE / filename), run_name="__main__")
                    main.assert_called_once_with(verbosity=2, exit=False)
                    sentinel = f"SENTINEL: {filename} OK"
                    if passed:
                        self.assertEqual(exit_context.exception.code, 0)
                        self.assertEqual(stdout.getvalue(), sentinel + "\n")
                    else:
                        self.assertIsInstance(exit_context.exception.code, int)
                        self.assertNotEqual(exit_context.exception.code, 0)
                        self.assertNotIn("SENTINEL:", stdout.getvalue() + stderr.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
