import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from orin_parser import OrinParser, OrinSourceError

ROOT = Path(__file__).parents[2]
CONFORMANCE = ROOT / "tests" / "conformance"


class OutlineParserTests(unittest.TestCase):
    def test_expense_approval_matches_structured_fixture(self):
        model = OrinParser().parse_file(ROOT / "examples" / "expense-approval.orin")
        fixture = json.loads((CONFORMANCE / "expense-approval.structured.json").read_text(encoding="utf-8"))
        self.assertEqual(model.document["module"]["id"], fixture["module"]["id"])
        self.assertEqual({o["id"] for o in model.document["objects"]}, {o["id"] for o in fixture["objects"]})
        self.assertEqual(model.compilation_status(), "blocked")
        self.assertEqual(
            model.compute_readiness_gates()["blockingUnresolved"],
            ["finance.expense-approval/uncertainty/no-eligible-approver"],
        )
        self.assertTrue(all("source" in o for o in model.document["objects"] if o["kind"] != "evidence"))

    def test_generic_outline_without_fixture(self):
        text = (
            "module: demo\n\npurpose:\n  Do a thing.\n\nrules:\n  - Things are done once.\n\n"
            "workflow: do-it\n  input:\n    thing\n\n"
            "example: ok\n  given:\n    A thing.\n  when:\n    It is done.\n  then:\n    It is done once.\n\n"
            "uncertainty: later\n  blocking: yes\n  question:\n    When?\n"
        )
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "demo.orin"
            path.write_text(text, encoding="utf-8")
            model = OrinParser().parse_file(path)
        ids = {o["id"] for o in model.document["objects"]}
        self.assertIn("demo/workflow/do-it", ids)
        self.assertIn("demo/rule/things-are-done-once", ids)
        self.assertEqual(model.document["module"]["purpose"], "Do a thing.")
        self.assertEqual(model.compilation_status(), "blocked")

    def test_outline_diagnostic_has_line_and_column(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "bad.orin"
            path.write_text("module: demo\nwhat is this\n", encoding="utf-8")
            with self.assertRaises(OrinSourceError) as context:
                OrinParser().parse_file(path)
        self.assertEqual((context.exception.line, context.exception.column), (2, 1))


if __name__ == "__main__":
    unittest.main()
