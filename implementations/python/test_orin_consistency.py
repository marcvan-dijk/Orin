import json
from pathlib import Path
import unittest

from .orin_consistency import consistency_diagnostics
from .orin_model import SemanticModel

FIXTURE = Path(__file__).parents[2] / "tests" / "conformance" / "rule-consistency.fixtures.json"


class ConsistencyTests(unittest.TestCase):
    def test_fixture_cases(self):
        for case in json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(case=case["id"]):
                actual = [[code, object_id] for code, _, object_id in consistency_diagnostics(case["objects"])]
                self.assertEqual(actual, case["expect"])

    def test_wired_into_model_diagnostics(self):
        case = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]
        model = SemanticModel({"module": {"id": "m/module", "kind": "module", "name": "m", "status": "accepted"},
                               "objects": case["objects"]})
        self.assertIn("ORIN-E048", [d.code for d in model.diagnostics()])
        self.assertEqual(model.compilation_status(), "fail")


if __name__ == "__main__":
    unittest.main()
