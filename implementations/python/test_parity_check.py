import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch
from types import SimpleNamespace

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

    def test_rate_limit_parity_uses_both_generated_backends(self):
        rows, failures = parity_check.run_rate_limits()
        self.assertEqual(failures, 0, rows)
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(status == "PASS" for _, _, status in rows))
        self.assertEqual({policy for _, policy, _ in rows}, {
            "five-per-15m-per-address-and-origin", "three-per-hour-per-address",
        })

    def test_direct_script_checks_generated_runtime_parity(self):
        result = subprocess.run(
            [sys.executable, str(Path(parity_check.__file__))],
            capture_output=True, text=True, check=False, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("account.password-reset/rate-limit/", result.stdout)
        self.assertNotIn("FAIL", result.stdout)
        self.assertNotIn("SKIP", result.stdout)

    def test_rate_limit_parity_requires_node(self):
        rows, failures = parity_check.run_rate_limits(node="")
        self.assertEqual(failures, 1)
        self.assertEqual(rows[0][2], "FAIL")

    def test_rate_limit_parity_detects_missing_observation(self):
        from implementations.python.codegen.password_reset_rate_limit import run_fixture

        observations = run_fixture(parity_check.RATE_LIMIT_CASES)
        policy = next(iter(observations))
        observations[policy].pop(next(iter(observations[policy])))
        result = SimpleNamespace(returncode=0, stdout=json.dumps(observations), stderr="")
        with patch.object(parity_check.subprocess, "run", return_value=result):
            rows, failures = parity_check.run_rate_limits(node="node")
        self.assertEqual(failures, 1, rows)

    def test_rate_limit_parity_surfaces_backend_failure(self):
        result = SimpleNamespace(returncode=1, stdout="", stderr="generation refused")
        with patch.object(parity_check.subprocess, "run", return_value=result):
            rows, failures = parity_check.run_rate_limits(node="node")
        self.assertEqual(failures, 1)
        self.assertIn("generation refused", rows[0][2])

    def test_rate_limit_parity_rejects_equally_wrong_backends(self):
        from implementations.python.codegen.password_reset_rate_limit import run_fixture

        observations = run_fixture(parity_check.RATE_LIMIT_CASES)
        policy = next(iter(observations))
        case_id = next(iter(observations[policy]))
        observations[policy][case_id]["resetMessages"][0] = "incorrect"
        result = SimpleNamespace(returncode=0, stdout=json.dumps(observations), stderr="")
        with patch("implementations.python.codegen.password_reset_rate_limit.run_fixture", return_value=observations):
            with patch.object(parity_check.subprocess, "run", return_value=result):
                rows, failures = parity_check.run_rate_limits(node="node")
        self.assertEqual(failures, 1, rows)


if __name__ == "__main__":
    unittest.main()
