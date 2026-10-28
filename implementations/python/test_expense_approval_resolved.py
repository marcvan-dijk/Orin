import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance_runner import load_cases
from orin_model import SemanticModel

CONFORMANCE = Path(__file__).resolve().parents[2] / "tests" / "conformance"


def decide(case):
    given, action = case["given"], case["when"]["action"]
    if action == "compile":
        return {"compilation": model.compute_readiness_gates()["compilation"]}
    if action == "route":
        eligible = [limit for limit in given["otherApproverLimits"] if limit >= given["amount"]]
        return {"expense": "submitted", "routedTo": f"approver-limit-{min(eligible)}" if eligible else None}
    if action == "approve":
        if given.get("approverIsSubmitter") or given["approverLimit"] < given["amount"]:
            return {"approval": "refused", "expense": "submitted"}
        return {"expense": "approved"}
    if action == "reject":
        if given.get("approverIsSubmitter") or given.get("expense") == "approved":
            return {"rejection": "refused", "expense": given.get("expense", "submitted")}
        return {"expense": "rejected", "reasonVisibleToSubmitter": True}
    raise ValueError(action)


model = SemanticModel.from_json_file(CONFORMANCE / "expense-approval.resolved.model.json")


class ExpenseApprovalResolvedTest(unittest.TestCase):
    def test_model_is_eligible(self):
        self.assertEqual(model.diagnostics(), [])
        self.assertEqual(model.compute_readiness_gates()["compilation"], "eligible")

    def test_cases(self):
        cases = load_cases(CONFORMANCE / "expense-approval.resolved.cases.json")["cases"]
        for case in cases:
            with self.subTest(case["id"]):
                self.assertEqual(decide(case), case["then"])


if __name__ == "__main__":
    unittest.main()
