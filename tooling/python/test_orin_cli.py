import contextlib
import io
from pathlib import Path
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
