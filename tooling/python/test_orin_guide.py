import io
import json
from pathlib import Path
import tempfile
import unittest

from tooling.python import orin_cli
from tooling.python.orin_guide import run_guide

ROOT = Path(__file__).resolve().parents[2]
PW = str(ROOT / "examples" / "password-reset.orin")
LIB = str(ROOT / "examples" / "library-lending.orin")


class GuideTests(unittest.TestCase):
    def run_guide(self, file, answers=None, stdin="", out=None):
        buf = io.StringIO()
        code = run_guide(file, answers, out, io.StringIO(stdin), buf)
        return code, buf.getvalue()

    def test_piped_input_decides_and_reports_ready(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            out = str(Path(d) / "decided.json")
            code, text = self.run_guide(PW, stdin="9\n1\n", out=out)
            self.assertEqual(code, 0)
            self.assertIn("is not a choice", text)
            self.assertIn("Nothing is open now", text)
            self.assertTrue(json.loads(Path(out).read_text(encoding="utf-8")))

    def test_answers_flag_two_questions(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            code, text = self.run_guide(LIB, ["1", "2"], out=str(Path(d) / "x.json"))
            self.assertEqual(code, 0)
            self.assertIn("You decided 2 question(s)", text)

    def test_defer_keeps_open(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            code, text = self.run_guide(PW, ["3"], out=str(Path(d) / "x.json"))
            self.assertEqual(code, 2)
            self.assertIn("Still open", text)

    def test_quit_and_bad_answer_and_missing_file(self):
        code, text = self.run_guide(PW, stdin="q\n")
        self.assertEqual(code, 2)
        self.assertEqual(self.run_guide(PW, ["x"])[0], 3)
        self.assertEqual(self.run_guide("nope.orin")[0], 3)

    def test_cli_wiring(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            out = str(Path(d) / "x.json")
            self.assertEqual(orin_cli.main(["guide", PW, "--answers", "1", "--out", out]), 0)
            self.assertTrue(Path(out).is_file())


if __name__ == "__main__":
    unittest.main()
