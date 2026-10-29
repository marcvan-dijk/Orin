from pathlib import Path
import unittest

from tooling.python import demo_novice_flow

ROOT = Path(__file__).resolve().parents[2]


class NoviceFlowDemoTests(unittest.TestCase):
    def test_expense_approval_flow(self):
        before = set(ROOT.glob("orin-demo-*"))
        results = demo_novice_flow.run_demo(say=lambda _: None, app="expense-approval")
        self.assertTrue(results["blocked_before"])
        self.assertFalse(results["blocked_after"])
        self.assertEqual(results["failed"], [])
        self.assertGreaterEqual(len(results["passed"]), 7)
        self.assertNotEqual(results["choice"], "defer")
        self.assertEqual(set(ROOT.glob("orin-demo-*")), before)

    def test_flow_goes_blocked_to_ready_and_passes_cases(self):
        lines = []
        before = set(ROOT.glob("orin-demo-*"))
        results = demo_novice_flow.run_demo(say=lines.append)
        self.assertTrue(results["blocked_before"])
        self.assertFalse(results["blocked_after"])
        self.assertEqual(results["failed"], [])
        self.assertGreater(len(results["passed"]), 0)
        self.assertTrue(lines[-1].startswith("Summary: your request"))
        self.assertEqual(set(ROOT.glob("orin-demo-*")), before)


if __name__ == "__main__":
    unittest.main()
