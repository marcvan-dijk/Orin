import subprocess
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
IMPLEMENTATIONS_PYTHON = ROOT / "implementations" / "python"
if str(IMPLEMENTATIONS_PYTHON) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATIONS_PYTHON))

from conformance_runner import execute_case, expected_case_result, load_cases
from implementations.python.orin_agent_core import (
    EXIT_ACCEPTED,
    EXIT_BLOCKED,
    EXIT_INVALID,
    RATE_LIMIT_RULE_ID,
    RATE_LIMIT_UNCERTAINTY_ID,
    DecisionRequiredError,
    OrinDecisionAgent,
    UnknownDecisionError,
)


MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
SOURCE = ROOT / "examples" / "password-reset.orin"
CASES = ROOT / "tests" / "conformance" / "password-reset.cases.json"
AGENT = ["-m", "tooling.python.orin_agent"]


class OrinDecisionAgentTests(unittest.TestCase):
    def test_blocked_inspection_explains_rate_limit_decision(self):
        inspection = OrinDecisionAgent().inspect(MODEL)

        self.assertEqual(inspection.status, "blocked")
        self.assertEqual(inspection.compilation, "blocked")
        self.assertEqual(len(inspection.decisions), 1)
        decision = inspection.decisions[0]
        self.assertEqual(decision.prompt.uncertainty_id, RATE_LIMIT_UNCERTAINTY_ID)
        self.assertIn("abuse boundary", decision.prompt.why_it_matters)
        self.assertEqual(
            [option.id for option in decision.prompt.options],
            [
                "five-per-15m-per-address-and-origin",
                "three-per-hour-per-address",
                "defer",
            ],
        )

    def test_source_inspection_supports_password_reset_example(self):
        inspection = OrinDecisionAgent().inspect(SOURCE)

        self.assertEqual(inspection.source_kind, "orin-source")
        self.assertEqual(inspection.compilation, "blocked")
        self.assertEqual(inspection.semantic_path, ROOT / "tests" / "conformance" / "password-reset.structured.json")

    def test_agent_refuses_to_apply_without_explicit_decision(self):
        with self.assertRaisesRegex(DecisionRequiredError, "explicit decision required"):
            OrinDecisionAgent().apply_decision(MODEL, RATE_LIMIT_UNCERTAINTY_ID, None)

    def test_unknown_decision_option_is_rejected(self):
        with self.assertRaisesRegex(UnknownDecisionError, "unknown decision option"):
            OrinDecisionAgent().apply_decision(
                MODEL,
                RATE_LIMIT_UNCERTAINTY_ID,
                "not-a-real-option",
            )

    def test_explicit_decision_produces_ready_semantic_model(self):
        result = OrinDecisionAgent().apply_decision(
            MODEL,
            RATE_LIMIT_UNCERTAINTY_ID,
            "five-per-15m-per-address-and-origin",
        )

        self.assertEqual(result.model.compilation_status(), "eligible")
        self.assertNotIn(RATE_LIMIT_UNCERTAINTY_ID, result.model.document.get("unresolved", []))
        rate_limit_rule = next(
            obj for obj in result.model.document["objects"]
            if obj.get("id") == RATE_LIMIT_RULE_ID
        )
        self.assertIn("5 attempts per 15 minutes", rate_limit_rule["claims"][0])

    def test_behavior_cases_stay_equal_after_rate_limit_decision(self):
        result = OrinDecisionAgent().apply_decision(
            MODEL,
            RATE_LIMIT_UNCERTAINTY_ID,
            "five-per-15m-per-address-and-origin",
        )

        for case in load_cases(CASES)["cases"]:
            if case.get("when", {}).get("action") == "compile":
                continue
            with self.subTest(case=case["id"]):
                actual = execute_case(result.model, case)
                for key, expected in expected_case_result(case).items():
                    self.assertEqual(actual[key], expected)


class OrinDecisionAgentCliTests(unittest.TestCase):
    def test_inspect_cli_reports_blocked_exit_code(self):
        completed = subprocess.run(
            [sys.executable, *AGENT, "inspect", str(SOURCE)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, EXIT_BLOCKED)
        self.assertIn("Blocked: 1 consequential decision", completed.stdout)
        self.assertIn("five-per-15m-per-address-and-origin", completed.stdout)

    def test_decide_cli_writes_revised_model_and_returns_acceptance_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "resolved.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    *AGENT,
                    "decide",
                    str(MODEL),
                    "--uncertainty",
                    RATE_LIMIT_UNCERTAINTY_ID,
                    "--option",
                    "five-per-15m-per-address-and-origin",
                    "--write",
                    str(output_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, EXIT_ACCEPTED)
            self.assertIn("Updated compilation: eligible", completed.stdout)
            self.assertTrue(output_path.exists())

    def test_decide_cli_rejects_unknown_decision(self):
        completed = subprocess.run(
            [
                sys.executable,
                *AGENT,
                "decide",
                str(MODEL),
                "--uncertainty",
                RATE_LIMIT_UNCERTAINTY_ID,
                "--option",
                "unknown-option",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, EXIT_INVALID)
        self.assertIn("unknown decision option", completed.stderr)


if __name__ == "__main__":
    unittest.main()
