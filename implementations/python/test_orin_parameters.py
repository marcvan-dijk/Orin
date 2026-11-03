import unittest
from pathlib import Path

from implementations.python.orin_parser import OrinParser
from implementations.python.schema_check import load_schema, validate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = load_schema(ROOT / "tests" / "conformance" / "model.schema.json")

SOURCE = """module: event-booking

parameter: capacity
  type: number
  unit: seats

rules:
  - An event never has more confirmed bookings than its capacity.
"""


class ModuleParameterTests(unittest.TestCase):
    def test_summary_outline_preserves_typed_unit_parameter(self):
        model = OrinParser().parse_outline(SOURCE)
        self.assertEqual(model.document["module"]["parameters"], [
            {"name": "capacity", "type": "number", "unit": "seats"},
        ])
        self.assertEqual(model.diagnostics(), [])

    def test_event_booking_example_declares_capacity_without_parameter_errors(self):
        source = (ROOT / "examples" / "event-booking.orin").read_text(encoding="utf-8")
        model = OrinParser().parse_outline(source)
        self.assertEqual(model.document["module"]["parameters"], [
            {"name": "capacity", "type": "number", "unit": "seats"},
        ])
        self.assertNotIn("ORIN-E056", [diagnostic.code for diagnostic in model.diagnostics()])
        self.assertEqual(validate(SCHEMA, model.document), [])

    def test_declaration_outline_preserves_module_parameter(self):
        source = """module: event-booking

parameter: capacity
  type: number
  unit: seats

rule: bookings-fit
  claims:
    An event never has more confirmed bookings than its capacity.
"""
        model = OrinParser().parse_outline(source)
        self.assertEqual(model.document["module"]["parameters"][0]["unit"], "seats")
        self.assertEqual(model.diagnostics(), [])

    def test_limit_claim_requires_a_declared_parameter(self):
        source = SOURCE.replace(
            "parameter: capacity\n  type: number\n  unit: seats\n\n",
            "",
        )
        diagnostics = OrinParser().parse_outline(source).diagnostics()
        self.assertIn("ORIN-E056", [diagnostic.code for diagnostic in diagnostics])

    def test_parameter_requires_numeric_type_and_unit(self):
        for replacement in (
            "parameter: capacity\n  type: text\n  unit: seats",
            "parameter: capacity\n  type: number",
        ):
            source = SOURCE.replace("parameter: capacity\n  type: number\n  unit: seats", replacement)
            diagnostics = OrinParser().parse_outline(source).diagnostics()
            self.assertIn("ORIN-E056", [diagnostic.code for diagnostic in diagnostics])

    def test_duplicate_parameters_are_rejected(self):
        source = SOURCE.replace(
            "rules:",
            "parameter: capacity\n  type: number\n  unit: seats\n\nrules:",
        )
        diagnostics = OrinParser().parse_outline(source).diagnostics()
        self.assertIn("ORIN-E056", [diagnostic.code for diagnostic in diagnostics])


if __name__ == "__main__":
    unittest.main()
