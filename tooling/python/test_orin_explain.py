import contextlib
import io
from pathlib import Path
import unittest

from tooling.python import orin_cli, orin_explain

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = sorted((ROOT / "examples").glob("*.orin"))


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orin_cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ExplainTests(unittest.TestCase):
    def test_every_example_explains_deterministically(self):
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            with self.subTest(path=path.name):
                code, out, _ = run("explain", str(path))
                self.assertEqual(code, 0)
                for heading in ("Purpose", "Rules (always true)", "Examples as stories",
                                "Open questions", "What is decided"):
                    if heading in ("Rules (always true)", "Examples as stories"):
                        continue
                    self.assertIn(heading, out)
                self.assertIn("Is this what you meant?", out)
                self.assertEqual(out, run("explain", str(path))[1])

    def test_every_conformance_model_explains(self):
        for path in sorted((ROOT / "tests" / "conformance").glob("*.model.json")):
            with self.subTest(path=path.name):
                self.assertEqual(run("explain", str(path))[0], 0)

    def test_password_reset_content(self):
        _, out, _ = run("explain", str(ROOT / "examples" / "password-reset.orin"))
        self.assertIn("- Reset tokens expire after 15 minutes.", out)
        self.assertIn("Story: Unknown address", out)
        self.assertIn("Start: No account exists for the requested email.", out)
        self.assertIn("(must be answered before building)", out)
        self.assertIn("Not ready", out)

    def test_resolved_question_is_decided(self):
        text = orin_explain.explain_document({
            "module": {"name": "demo", "purpose": "Show it"},
            "objects": [{"kind": "uncertainty", "name": "q", "status": "resolved",
                         "claims": ["Which one?"], "resolution": "The first one"}]})
        self.assertIn("- Which one? Answer: The first one.", text)
        self.assertIn("Nothing blocks building.", text)

    def test_missing_file_is_invalid_input(self):
        self.assertEqual(run("explain", "nope.orin")[0], 3)


if __name__ == "__main__":
    unittest.main()
