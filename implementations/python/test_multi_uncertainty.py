import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from orin_parser import OrinParser

TEXT = (
    "module: demo\n\npurpose:\n  Do a thing.\n\nrules:\n"
    "  - Things are done once only here.\n  - Things are done once only there.\n\n"
    "uncertainty: first\n  blocking: yes\n  question:\n    One?\n\n"
    "uncertainty: second\n  blocking: yes\n  question:\n    Two?\n"
)


class MultiUncertaintyTests(unittest.TestCase):
    def test_two_blocking_uncertainties_parse(self):
        model = OrinParser().parse_outline(TEXT)
        ids = [o["id"] for o in model.document["objects"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("demo/uncertainty/first", ids)
        self.assertIn("demo/uncertainty/second", ids)
        self.assertEqual(model.compilation_status(), "blocked")

    def test_rules_with_same_slug_get_stable_distinct_ids(self):
        ids = [o["id"] for o in OrinParser().parse_outline(TEXT).document["objects"] if o["kind"] == "rule"]
        self.assertEqual(ids, ["demo/rule/things-are-done-once-only", "demo/rule/things-are-done-once-only-2"])


if __name__ == "__main__":
    unittest.main()
