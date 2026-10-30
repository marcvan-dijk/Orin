import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

from tooling.python import orin_cli, orin_export

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
HOSTILE = "<script>alert(1)</script> & \"q\" <img src=x onerror=y>"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orin_cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def hostile_model():
    return {"module": {"name": HOSTILE, "purpose": HOSTILE},
            "objects": [
                {"id": "m/value-type/t", "kind": "value-type", "name": HOSTILE, "claims": [HOSTILE]},
                {"id": "m/rule/r", "kind": "rule", "name": HOSTILE, "claims": [HOSTILE],
                 "evidenceLinks": ["m/example/e"]},
                {"id": "m/example/e", "kind": "example", "name": HOSTILE, "claims": [HOSTILE]},
                {"id": "m/uncertainty/d", "kind": "uncertainty", "name": HOSTILE, "status": "accepted",
                 "claims": [HOSTILE], "resolution": {"option": HOSTILE, "rationale": HOSTILE}},
                {"id": "m/uncertainty/q", "kind": "uncertainty", "name": HOSTILE, "status": "unresolved",
                 "claims": [HOSTILE], "why_it_matters": HOSTILE,
                 "options": [{"id": HOSTILE, "label": HOSTILE}]},
            ]}


class ExportTests(unittest.TestCase):
    def test_html_escapes_hostile_text_and_is_self_contained(self):
        html = orin_export.export(hostile_model(), "html")
        self.assertNotIn("<script", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;q&quot;", html)
        self.assertEqual(re.findall(r"<(?:link|script|img|iframe)\b", html), [])
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_md_has_all_sections(self):
        text = orin_export.export(hostile_model(), "md")
        for title in orin_export.SECTIONS:
            self.assertIn(f"## {title}", text)

    def test_rule_examples_decisions_and_questions(self):
        doc = json.loads(orin_export.export(hostile_model(), "json"))
        self.assertEqual(doc["rules"][0]["examples"][0]["steps"], [HOSTILE])
        self.assertEqual(doc["other_examples"], [])
        self.assertEqual(doc["decisions"][0]["rationale"], HOSTILE)
        self.assertEqual(doc["open_questions"][0]["options"][0]["label"], HOSTILE)
        self.assertEqual(doc["glossary"][0]["kind"], "value-type")

    def test_empty_model_works(self):
        for fmt in orin_export.FORMATS:
            self.assertTrue(orin_export.export({}, fmt))

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            orin_export.export({}, "pdf")


class ExportCliTests(unittest.TestCase):
    def test_every_example_every_format(self):
        for path in sorted(EXAMPLES.glob("*.orin")):
            for fmt in orin_export.FORMATS:
                code, out, err = run("export", str(path), "--format", fmt)
                self.assertEqual(code, 0, f"{path.name} {fmt}: {err}")
                self.assertTrue(out.strip())

    def test_password_reset_content(self):
        _, out, _ = run("export", str(EXAMPLES / "password-reset.orin"))
        self.assertIn("recover an account", out)
        self.assertIn("reset-token-expiry", out)
        self.assertIn("rate-limit", out)

    def test_out_file(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            target = Path(d) / "spec.html"
            code, _, _ = run("export", str(EXAMPLES / "password-reset.orin"),
                             "--format", "html", "--out", str(target))
            self.assertEqual(code, 0)
            self.assertTrue(target.read_text(encoding="utf-8").startswith("<!DOCTYPE html>"))

    def test_bad_format_is_invalid(self):
        code, _, _ = run("export", str(EXAMPLES / "password-reset.orin"), "--format", "pdf")
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
