from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from orin_parser import OrinParser
from orin_types_check import check_types

ROOT = Path(__file__).parents[2]

HEAD = (
    "module: demo.t\n\npurpose:\n  Test.\n\n"
    "type: priority\n  one of: low, medium, high\n\n"
    "type: tip\n  number: 0 to 100\n\n"
    "type: nick\n  one of: a, b\n  optional\n\n"
)


def codes(text):
    model = OrinParser().parse_outline(text)
    return sorted(d.code for d in model.diagnostics() if d.code in {"ORIN-E052", "ORIN-E053", "ORIN-E054", "ORIN-E055"})


def with_rule(claim):
    return HEAD + f"rule: r\n  claims:\n    - {claim}\n"


class TypesCheckTests(unittest.TestCase):
    def test_valid_values(self):
        self.assertEqual(codes(with_rule("priority = high and tip is 15.5 and nick = none")), [])

    def test_bad_enum_value(self):
        self.assertEqual(codes(with_rule("priority = urgent")), ["ORIN-E053"])

    def test_number_out_of_range_and_not_number(self):
        self.assertEqual(codes(with_rule("tip = 101")), ["ORIN-E054"])
        self.assertEqual(codes(with_rule("tip = lots")), ["ORIN-E054"])

    def test_missing_value_needs_optional(self):
        self.assertEqual(codes(with_rule("priority = none")), ["ORIN-E055"])

    def test_example_then_and_workflow_input_name(self):
        text = HEAD + "workflow: w\n  input:\n    level priority\n\nexample: e\n  requires:\n    w\n  then:\n    level = extreme\n"
        self.assertEqual(codes(text), ["ORIN-E053"])

    def test_bad_constraints(self):
        for line in ("one of:", "one of: a, a", "number: 5 to 1", "number: big", "colour: red"):
            text = f"module: demo.t\n\ntype: x\n  {line}\n"
            self.assertEqual(codes(text), ["ORIN-E052"], line)

    def test_unconstrained_types_ignored(self):
        self.assertEqual(check_types({"objects": []}), [])

    def test_shipped_examples_stay_valid(self):
        for name in ("password-reset", "expense-approval", "library-lending"):
            model = OrinParser().parse_file(ROOT / "examples" / f"{name}.orin")
            bad = [d for d in model.diagnostics() if d.code in {"ORIN-E052", "ORIN-E053", "ORIN-E054", "ORIN-E055"}]
            self.assertEqual(bad, [], name)


if __name__ == "__main__":
    unittest.main()
