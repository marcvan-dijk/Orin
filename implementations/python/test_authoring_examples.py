import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orin_parser import analyze

EXAMPLES = Path(__file__).resolve().parents[2] / "docs" / "authoring-examples"


class AuthoringExamplesTests(unittest.TestCase):
    def test_examples_exist(self):
        self.assertGreaterEqual(len(list(EXAMPLES.glob("*.orin"))), 5)

    def test_only_open_uncertainty_diagnostics(self):
        for path in sorted(EXAMPLES.glob("*.orin")):
            with self.subTest(example=path.name):
                text = path.read_text(encoding="utf-8")
                open_count = text.count("  uncertainty ")
                self.assertGreaterEqual(open_count, 1)
                codes = [d.code for d in analyze(path)]
                self.assertEqual(codes, ["ORIN-E041"] * open_count)


if __name__ == "__main__":
    unittest.main()
