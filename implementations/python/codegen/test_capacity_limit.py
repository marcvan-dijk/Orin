import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from implementations.python.codegen import generate
from implementations.python.orin_parser import OrinParser


SOURCE = """module: event-booking

parameter: capacity
  type: number
  unit: seats

rules:
  - An event never has more confirmed bookings than its capacity.
"""


class CapacityLimitCodegenTests(unittest.TestCase):
    def test_limit_claim_generates_a_runtime_check_using_the_named_parameter(self):
        document = OrinParser().parse_outline(SOURCE).document
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_path = root / "event-booking.json"
            model_path.write_text(json.dumps(document), encoding="utf-8")
            generated_path = generate.generate(model_path, root / "out")
            spec = importlib.util.spec_from_file_location("event_booking_generated", generated_path)
            generated = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generated)

            constraint = next(item for item in generated.IR["constraints"] if item["kind"] == "capacity-limit")
            self.assertEqual(generated.IR["parameters"], ["capacity"])
            self.assertEqual(generated.IR["unimplemented"], [])
            runtime = generated.Runtime(params={"capacity": 4})
            self.assertTrue(runtime.within_limit(constraint["id"], 4))
            self.assertFalse(runtime.within_limit(constraint["id"], 5))

            with self.assertRaises(generated.MissingParameter):
                generated.Runtime().within_limit(constraint["id"], 1)

    def test_limit_runtime_rejects_invalid_values(self):
        document = OrinParser().parse_outline(SOURCE).document
        from implementations.python.codegen import prose_driven

        ir = prose_driven.derive_ir(document)
        constraint_id = next(item["id"] for item in ir["constraints"] if item["kind"] == "capacity-limit")
        from implementations.python.codegen.prose_driven import TEMPLATE, render_ir

        source = TEMPLATE.replace("@@MODULE@@", json.dumps("event-booking/module")).replace("@@IR@@", render_ir(ir))
        namespace = {}
        exec(compile(source, "<generated>", "exec"), namespace)
        with self.assertRaises(ValueError):
            namespace["Runtime"](params={"capacity": -1}).within_limit(constraint_id, 0)
        with self.assertRaises(ValueError):
            namespace["Runtime"](params={"capacity": 4}).within_limit(constraint_id, -1)


if __name__ == "__main__":
    unittest.main()
