import unittest
import json

from tooling.python.demo_decision_change import RATE_LIMIT_CASES, OPTION_A, OPTION_B, run_demo, run_expense, run_shared_tasks


class DecisionChangeDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_demo(say=lambda *_: None)

    def test_diff_touches_only_rate_limit_constants(self):
        changed = [l for l in self.out["diff"] if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        self.assertEqual(len(changed), 6)
        self.assertTrue(all("RATE_LIMIT_" in l for l in changed))

    def test_expected_examples_change(self):
        cases = json.loads(RATE_LIMIT_CASES.read_text(encoding="utf-8"))["cases"]
        expected_changes = {case["id"] for case in cases if case["then"][OPTION_A] != case["then"][OPTION_B]}
        self.assertTrue(expected_changes)
        self.assertEqual(set(self.out["changed_rate_limit_cases"]), expected_changes)
        for label, option in (("A", OPTION_A), ("B", OPTION_B)):
            self.assertEqual(self.out["rate_limits"][label], {
                case["id"]: case["then"][option] for case in cases
            })

    def test_shipped_cases_pass_under_both_decisions(self):
        for label in "AB":
            self.assertTrue(all(v == "pass" for v in self.out["shipped"][label].values()))

    def test_unchanged_rules_byte_identical(self):
        self.assertEqual(self.out["total_blocks"] - self.out["unchanged_blocks"], 1)
        self.assertEqual(len(self.out["differing_blocks"]), 1)


class ExpenseDemoTests(unittest.TestCase):
    def test_generator_ignores_option_and_probe_exposes_it(self):
        out = run_expense(say=lambda *_: None)
        self.assertTrue(all(len(d) == 0 for d in out["diffs"].values()))
        for option in out["shared"]:
            self.assertTrue(all(out["shared"][option].values()))
        self.assertEqual(out["probe"], {o: "submitted" for o in out["probe"]})


class SharedTasksDemoTests(unittest.TestCase):
    def test_option_change_adds_hook_and_fails_a_shared_case(self):
        out = run_shared_tasks(say=lambda *_: None)
        self.assertTrue(out["diff"])
        self.assertTrue(all(out["shared"]["membership-required"].values()))
        self.assertFalse(all(out["shared"]["assignee-may-complete"].values()))
        self.assertEqual(len(out["hooks"]["membership-required"]), 0)
        self.assertEqual(len(out["hooks"]["assignee-may-complete"]), 1)


if __name__ == "__main__":
    unittest.main()
