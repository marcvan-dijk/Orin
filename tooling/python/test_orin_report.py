import contextlib
import io
import json
import unittest
from pathlib import Path

from tooling.python import orin_cli, orin_report

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = str(ROOT / "examples" / "password-reset.orin")


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = orin_cli.main(list(argv))
    return code, out.getvalue()


class ReportTests(unittest.TestCase):
    def test_json_fields(self):
        code, out = run("check", EXAMPLE, "--format", "json")
        self.assertEqual(code, 1)
        item = json.loads(out)["diagnostics"][0]
        for key in ("code", "message", "file", "line", "column", "severity", "hint"):
            self.assertIn(key, item)
        self.assertEqual(item["code"], "ORIN-E041")
        self.assertGreater(item["line"], 1)

    def test_github(self):
        code, out = run("check", EXAMPLE, "--format", "github")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("::error file="))
        self.assertIn(",line=", out)

    def test_sarif(self):
        _, out = run("check", EXAMPLE, "--format", "sarif")
        data = json.loads(out)
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["runs"][0]["results"][0]["ruleId"], "ORIN-E041")

    def test_text_default_unchanged(self):
        _, out = run("check", EXAMPLE)
        self.assertIn("PROBLEMS:", out)

    def test_bad_format(self):
        code, _ = run("check", EXAMPLE, "--format", "xml")
        self.assertEqual(code, 3)

    def test_github_escapes_newlines(self):
        self.assertEqual(orin_report._github_escape("a\nb%"), "a%0Ab%25")


if __name__ == "__main__":
    unittest.main()
