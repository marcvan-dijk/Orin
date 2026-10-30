import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementations.python.codegen import generate as gen  # noqa: E402
from implementations.python.orin_model import SemanticModel  # noqa: E402

M = "demo.shop"


def _doc(objects):
    return {"module": {"id": f"{M}/module", "name": M, "purpose": "demo"}, "objects": objects, "unresolved": []}


OBJECTS = [
    {"id": f"{M}/rule/order-size", "kind": "rule", "name": "order-size",
     "claims": ["The order total is at most 500.", "Orders are shipped in plain boxes."]},
    {"id": f"{M}/rule/has-name", "kind": "rule", "name": "has-name",
     "claims": ["The customer name must not be empty."]},
    *[{"id": f"{M}/state/{n}", "kind": "state", "name": n} for n in ("placed", "shipped", "delivered")],
    {"id": f"{M}/workflow/fulfil", "kind": "workflow", "name": "fulfil",
     "transitions": [{"from": f"{M}/state/placed", "to": f"{M}/state/shipped"},
                     {"from": f"{M}/state/shipped", "to": f"{M}/state/delivered"}]},
    {"id": f"{M}/workflow/refund", "kind": "workflow", "name": "refund", "steps": ["pay back"]},
    {"id": f"{M}/example/delivery", "kind": "example", "name": "delivery",
     "requires": [f"{M}/workflow/fulfil"], "expects": ["order.state = delivered"]},
    {"id": f"{M}/example/bad-state", "kind": "example", "name": "bad-state",
     "requires": [f"{M}/workflow/fulfil"], "expects": ["order.state = lost"]},
    {"id": f"{M}/example/prose", "kind": "example", "name": "prose", "expects": ["a mail is sent"]},
]


def _build(doc):
    tmp = tempfile.mkdtemp(dir=Path(__file__).parent)
    model_path = Path(tmp) / "m.json"
    model_path.write_text(json.dumps(doc), encoding="utf-8")
    target = gen.generate(model_path, Path(tmp) / "out")
    spec = importlib.util.spec_from_file_location("generic_generated_test", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tmp, target, module


class GenericGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.target, cls.mod = _build(_doc(OBJECTS))

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_uses_generic_fallback_and_writes_report(self):
        report = json.loads(self.target.with_suffix(".report.json").read_text())
        self.assertEqual(report["mode"], "generic")
        self.assertEqual(len(report["unimplementedRules"]), 1)

    def test_rule_guarantee_checked(self):
        self.assertTrue(self.mod.rule_has_name(customer_name="Ann"))
        with self.assertRaises(self.mod.RuleViolation):
            self.mod.rule_has_name(customer_name="")
        with self.assertRaises(self.mod.RuleViolation):
            self.mod.rule_order_size(order_total=900)

    def test_unexpressible_claim_raises_hook(self):
        with self.assertRaises(self.mod.NotImplementedRule):
            self.mod.rule_order_size(order_total=100)
        with self.assertRaises(self.mod.NotImplementedRule):
            self.mod.rule_has_name()

    def test_state_machine(self):
        machine = self.mod.workflow_fulfil()
        self.assertEqual(machine.state, "placed")
        machine.move("shipped")
        with self.assertRaises(self.mod.IllegalTransition):
            machine.move("placed")
        self.assertEqual(machine.move("delivered"), "delivered")
        with self.assertRaises(self.mod.NotImplementedRule):
            self.mod.workflow_refund()

    def test_examples_are_executable(self):
        self.assertTrue(self.mod.example_delivery())
        with self.assertRaises(AssertionError):
            self.mod.example_bad_state()
        with self.assertRaises(self.mod.NotImplementedRule):
            self.mod.example_prose()
        results = self.mod.run_examples()
        self.assertEqual(results["delivery"], "passed")
        self.assertTrue(results["bad-state"].startswith("failed"))
        self.assertTrue(results["prose"].startswith("not-implemented"))

    def test_deterministic_and_hostile_text_is_inert(self):
        evil = 'x"""\nimport os; os.system("echo hi")\n'
        objects = [dict(OBJECTS[0], claims=[evil])] + OBJECTS[2:6]
        tmp, target, mod = _build(_doc(objects))
        try:
            self.assertNotIn("os.system", target.read_text().split("_IR = ")[0])
            with self.assertRaises(mod.NotImplementedRule):
                mod.rule_order_size()
            self.assertEqual(gen.generate_source(SemanticModel(_doc(objects))),
                             gen.generate_source(SemanticModel(_doc(objects))))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empty_model_says_no_generator(self):
        with self.assertRaises(gen.GenerationError) as ctx:
            gen.generate_source(SemanticModel(_doc([])))
        self.assertIn("no generator for module", str(ctx.exception))
        self.assertIn(M, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
