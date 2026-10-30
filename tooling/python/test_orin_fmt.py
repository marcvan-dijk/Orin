import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from implementations.python.orin_parser import OrinParser  # noqa: E402
from tooling.python import orin_cli, orin_fmt  # noqa: E402

FILES = sorted([*(ROOT / "examples").glob("*.orin"),
                *(ROOT / "examples" / "authoring").glob("*.orin")])


def _strip_lines(value):
    if isinstance(value, dict):
        return {k: _strip_lines(v) for k, v in value.items() if k != "source"}
    if isinstance(value, list):
        return [_strip_lines(v) for v in value]
    return value


def _doc(text, path):
    return _strip_lines(OrinParser().parse_outline(text, path).document)


class FormatterTests(unittest.TestCase):
    def test_examples_keep_meaning_and_are_idempotent(self):
        self.assertTrue(FILES)
        for path in FILES:
            with self.subTest(file=path.name):
                before = path.read_text(encoding="utf-8")
                after = orin_fmt.format_text(before)
                self.assertEqual(_doc(before, path), _doc(after, path))
                self.assertEqual(after, orin_fmt.format_text(after))

    def test_messy_input_is_cleaned(self):
        messy = ("\ufeffmodule: demo\r\n\r\n\r\npurpose:\r\n\t  Do a thing.   \r\n"
                 "rule: r1\r\n      claims:\r\n         - A.\r\n\r\n"
                 "example: e1\r\n  then:\r\n    X.\r\n  given:\r\n    Y.\r\n  when:\r\n    Z.\r\n\r\n\r\n")
        expected = ("module: demo\n\npurpose:\n  Do a thing.\n\nrule: r1\n  claims:\n    - A.\n\n"
                    "example: e1\n  given:\n    Y.\n  when:\n    Z.\n  then:\n    X.\n")
        self.assertEqual(orin_fmt.format_text(messy), expected)

    def test_comments_stay_with_their_line(self):
        out = orin_fmt.format_text("module: m\n// about r\nrule: r\n  // note\n  claims:\n    - A.\n")
        self.assertEqual(out, "module: m\n\n// about r\nrule: r\n  // note\n  claims:\n    - A.\n")

    def test_cli_check_and_write(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            path = Path(tmp) / "a.orin"
            path.write_text("module: m   \nrule: r\n   claims:\n      - A.\n", encoding="utf-8")
            self.assertEqual(orin_cli.main(["fmt", str(path), "--check"]), 1)
            self.assertEqual(orin_cli.main(["fmt", str(path), "--write"]), 0)
            self.assertEqual(orin_cli.main(["fmt", str(path), "--check"]), 0)
            self.assertEqual(path.read_text(encoding="utf-8"),
                             "module: m\n\nrule: r\n  claims:\n    - A.\n")
            self.assertEqual(orin_cli.main(["fmt", str(path) + ".missing"]), 3)


if __name__ == "__main__":
    unittest.main()
