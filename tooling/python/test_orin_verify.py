import io
import unittest
from pathlib import Path

from tooling.python import orin_cli, orin_verify

CONF = Path(__file__).resolve().parents[2] / "tests" / "conformance"
RATE = "rate-limit=five-per-15m-per-address-and-origin"


def _verify(*args):
    lines: list[str] = []
    code = orin_verify.verify(*args, out=lines.append)
    return code, "\n".join(lines)


class VerifyTests(unittest.TestCase):
    def test_expense_approval_passes_and_reports_skipped(self):
        code, text = _verify(str(CONF / "expense-approval.resolved.model.json"))
        self.assertEqual(code, 0, text)
        self.assertIn("PASS within-limit", text)
        self.assertIn("PASS decide-twice", text)
        self.assertIn("SKIP eligible-approver-appears: cannot run yet", text)
        self.assertIn("NOT verified", text)
        self.assertNotIn("FAIL", text)

    def test_password_reset_with_decision_passes(self):
        code, text = _verify(str(CONF / "password-reset.model.json"), [RATE])
        self.assertEqual(code, 0, text)
        self.assertIn("PASS expired-token", text)
        self.assertIn("PASS reused-token", text)
        self.assertIn("SKIP unresolved-rate-limit", text)
        self.assertIn("8 passed, 0 failed, 1 could not be run yet.", text)

    def test_blocked_model_is_not_verified(self):
        code, text = _verify(str(CONF / "password-reset.model.json"))
        self.assertEqual(code, 1)
        self.assertIn("code could not be generated", text)
        self.assertIn("rate-limit", text)

    def test_missing_file_is_invalid_input(self):
        self.assertEqual(orin_verify.verify("no-such-file.json"), 3)

    def test_cli_exit_codes(self):
        out = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(out):
            code = orin_cli.main(["verify", str(CONF / "expense-approval.resolved.model.json")])
        self.assertEqual(code, 0)
        self.assertIn("8 passed", out.getvalue())


if __name__ == "__main__":
    unittest.main()
