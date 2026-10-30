import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import parity_check


class ParityCheckTests(unittest.TestCase):
    def test_collects_fixture_targets(self):
        targets = parity_check.collect_targets()
        self.assertTrue(any(name == "shared-tasks.validation-cases.json::shared-tasks/validation/minimal-model-is-eligible" for name, _ in targets))
        self.assertTrue(any(name == "shared-tasks.cases.json" for name, _ in targets))

    def test_compare_detects_difference(self):
        a = {"compilation": "fail", "diagnostics": [], "readiness": {}}
        self.assertIsNone(parity_check.compare(a, dict(a)))
        self.assertEqual(parity_check.compare(a, {**a, "compilation": "eligible"}), "compilation differs")

    def test_skips_typescript_without_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = Path(parity_check.CONFORMANCE / "shared-tasks.minimal.model.json")
            (root / "m.model.json").write_text(model.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "x.cases.json").write_text(json.dumps({"model": "m.model.json", "cases": []}), encoding="utf-8")
            rows, failures = parity_check.run(root, node="")
        self.assertEqual(failures, 0)
        self.assertEqual(rows[0][2], "SKIP")
        self.assertEqual(rows[-1][0], "NOTICE")

    def test_compare_parse_detects_readiness_and_decided_model(self):
        a = {"diagnostics": [], "document": {}, "compilation": "eligible", "readiness": {"a": 1}, "canonical": {}}
        self.assertIsNone(parity_check.compare_parse(a, dict(a)))
        self.assertEqual(parity_check.compare_parse(a, {**a, "readiness": {}}), "readiness differs")
        self.assertEqual(parity_check.compare_parse(a, {**a, "canonical": {"x": 1}}), "decided model differs")
        self.assertEqual(parity_check.compare_parse(a, {**a, "compilation": "fail"}), "compilation differs")

    def test_examples_parity(self):
        rows, failures = parity_check.run_examples()
        self.assertEqual(failures, 0, rows)

    def test_full_parity(self):
        rows, failures = parity_check.run()
        self.assertEqual(failures, 0, rows)


if __name__ == "__main__":
    unittest.main()
