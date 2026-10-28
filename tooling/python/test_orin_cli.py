import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest

from tooling.python import orin_cli

CONF = Path(__file__).resolve().parents[2] / "tests" / "conformance"
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orin_cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class NewGenerateTests(unittest.TestCase):
    def test_new_scaffold_loads_and_is_blocked(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            code, out, _ = run("new", "my-app", "--out", d)
            self.assertEqual(code, 0)
            path = Path(d) / "my-app.orin"
            self.assertNotIn("TODO", path.read_text())
            self.assertIn("ORIN-E041", run("check", str(path))[1])
            self.assertEqual(run("readiness", str(path))[0], 2)
            self.assertEqual(run("new", "my-app", "--out", d)[0], 3)

    def test_new_rejects_bad_name(self):
        self.assertEqual(run("new", "Bad Name")[0], 3)

    def test_generate_missing_model(self):
        self.assertEqual(run("generate", "nope.json", "--target", "python", "--out", "x")[0], 3)

    def test_generate_typescript_needs_decision(self):
        code, _, err = run("generate", str(CONF / "shared-tasks.model.json"),
                           "--target", "typescript", "--out", "x")
        self.assertEqual(code, 3)
        self.assertTrue(err)

    def test_generate_python_delegates(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            code, out, err = run("generate", str(CONF / "shared-tasks.model.json"),
                                 "--target", "python", "--out", d)
            self.assertIn(code, (0, 1, 3))
            self.assertTrue(out or err)


PR = str(CONF / "password-reset.model.json")
EX = str(CONF / "expense-approval.model.json")
NODE = shutil.which("node")


class GenerateDecisionTests(unittest.TestCase):
    def _out(self):
        d = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(d.cleanup)
        return d.name

    def test_blocked_without_decision_lists_options(self):
        for target in ("python", "typescript"):
            code, out, _ = run("generate", PR, "--target", target, "--out", self._out())
            self.assertEqual(code, 2)
            self.assertIn("three-per-hour-per-address", out)

    def test_python_password_reset(self):
        d = self._out()
        code, out, err = run("generate", PR, "--decision", "three-per-hour-per-address",
                             "--target", "python", "--out", d)
        self.assertEqual(code, 0, err)
        self.assertTrue((Path(d) / "password_reset_generated.py").is_file())

    def test_python_decision_file(self):
        d = self._out()
        f = Path(d) / "dec.json"
        f.write_text('{"option": "five-per-15m-per-address-and-origin"}')
        self.assertEqual(run("generate", PR, "--decision", str(f), "--target", "python",
                             "--out", d)[0], 0)

    def test_python_expense_approval(self):
        d = self._out()
        code, _, err = run("generate", EX, "--decision", "reject-as-unapprovable",
                           "--target", "python", "--out", d)
        self.assertEqual(code, 0, err)
        self.assertTrue((Path(d) / "expense_approval_generated.py").is_file())

    def test_unknown_option(self):
        self.assertEqual(run("generate", PR, "--decision", "nope", "--target", "python",
                             "--out", self._out())[0], 3)

    @unittest.skipUnless(NODE, "node not installed")
    def test_typescript_password_reset_and_expense(self):
        d = self._out()
        code, _, err = run("generate", PR, "--decision", "three-per-hour-per-address",
                           "--target", "typescript", "--out", d)
        self.assertEqual(code, 0, err)
        self.assertTrue((Path(d) / "password_reset.generated.ts").is_file())
        self.assertFalse((Path(d) / ".orin-decision.json").exists())
        code, _, err = run("generate", EX, "--decision", "stay-submitted",
                           "--target", "typescript", "--out", d)
        self.assertEqual(code, 0, err)
        self.assertTrue((Path(d) / "expense_approval.generated.ts").is_file())


class OrinCliTests(unittest.TestCase):
    def test_check_valid(self):
        code, out, _ = run("check", str(CONF / "shared-tasks.model.json"))
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_check_invalid_prints_ids(self):
        code, out, _ = run("check", str(CONF / "shared-tasks.unauthorized-actor.model.json"))
        self.assertEqual(code, 1)
        self.assertIn("ORIN-E037", out)

    def test_readiness_blocked(self):
        code, out, _ = run("readiness", str(EXAMPLES / "password-reset.orin"))
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED", out)
        self.assertIn("rate-limit", out)

    def test_readiness_json(self):
        code, out, _ = run("readiness", "--json", str(EXAMPLES / "password-reset.orin"))
        self.assertEqual(code, 2)
        self.assertIn('"status"', out)

    def test_inspect_delegates(self):
        code, out, _ = run("inspect", str(EXAMPLES / "password-reset.orin"))
        self.assertEqual(code, 2)
        self.assertTrue(out)

    def test_decide_delegates_error(self):
        code, _, err = run("decide", str(EXAMPLES / "password-reset.orin"), "--uncertainty", "nope")
        self.assertEqual(code, 3)
        self.assertTrue(err)

    def test_examples_pass(self):
        for name in ("shared-tasks.model.json", "shared-tasks.minimal.model.json", "password-reset.model.json"):
            with self.subTest(name=name):
                code, out, _ = run("examples", str(CONF / name))
                self.assertEqual(code, 0, out)
                self.assertIn("PASS", out)

    def test_examples_none(self):
        code, out, _ = run("examples", str(CONF / "shared-tasks.orphaned-state.model.json"))
        self.assertEqual(code, 0)
        self.assertIn("No examples", out)

    def test_missing_file_and_usage(self):
        self.assertEqual(run("check", "nope.orin")[0], 3)
        self.assertEqual(run("examples", "nope.json")[0], 3)
        self.assertEqual(run("bogus")[0], 3)

    def test_bad_extension(self):
        with tempfile.TemporaryDirectory(dir=".") as d:
            p = Path(d) / "x.txt"
            p.write_text("hi")
            self.assertEqual(run("check", str(p))[0], 3)


if __name__ == "__main__":
    unittest.main()
