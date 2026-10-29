import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
CASES = ROOT / "tests" / "conformance" / "password-reset.cases.json"
RATE_LIMIT = "account.password-reset/uncertainty/rate-limit"


from implementations.python.orin_agent_core import OrinDecisionAgent  # noqa: E402

EXPENSE_MODEL = ROOT / "tests" / "conformance" / "expense-approval.model.json"
EXPENSE_CASES = ROOT / "tests" / "conformance" / "expense-approval.cases.json"
NO_APPROVER = "finance.expense-approval/uncertainty/no-eligible-approver"


def _resolved(path, option="five-per-15m-per-address-and-origin"):
    result = OrinDecisionAgent().apply_decision(MODEL, RATE_LIMIT, option)
    OrinDecisionAgent.write_model(path, result.model)


def _resolved_expense(path):
    doc = json.loads(EXPENSE_MODEL.read_text(encoding="utf-8"))
    doc["unresolved"] = [item for item in doc["unresolved"] if item != NO_APPROVER]
    for obj in doc["objects"]:
        if obj["id"] == NO_APPROVER:
            obj["status"] = "accepted"
    path.write_text(json.dumps(doc), encoding="utf-8")


def _load(model_path, tmp, name):
    result = _cli(str(model_path), str(tmp / "out"))
    assert result.returncode == 0, result.stderr
    spec = importlib.util.spec_from_file_location(name, tmp / "out" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "implementations.python.codegen.generate", *args],
                          cwd=ROOT, capture_output=True, text=True)


def _run_case(mod, case):
    given, action = case.get("given", {}), case["when"]["action"]
    store = mod.AccountStore({"person@example.com"} if given.get("accountExists") else set(),
                             given.get("accountStore", "available") == "available")
    rt = mod.PasswordResetRuntime(store, mod.EmailProvider(given.get("emailProvider", "available") == "available"))
    caps = {mod.PERSON_CAPABILITY, mod.SEND_MESSAGE_CAPABILITY}
    email = "person@example.com"
    if action == "request-password-reset":
        r = rt.request_reset(email, caps)
        return r.outputs | {"recovery": r.recovery, "failures": r.failures}
    if action == "request-password-reset-twice":
        rs = [rt.request_reset(email, caps) for _ in range(2)]
        return {"tokensDistinct": rs[0].reset_token != rs[1].reset_token, "responses": [r.response for r in rs]}
    if action == "request-password-reset-concurrently":
        rs = rt.request_resets_concurrently(given["emails"], caps)
        return {"tokensDistinct": len({r.reset_token for r in rs}) == len(rs), "responses": [r.response for r in rs]}
    if action in ("redeem-expired-token", "redeem-token-twice"):
        token = rt.request_reset(email, caps).reset_token
        if action == "redeem-expired-token":
            when = mod.TOKEN_TTL_SECONDS
        else:
            rt.redeem_reset(token, 1)
            when = 2
        try:
            rt.redeem_reset(token, when)
        except mod.TokenRejected as error:
            return {"token": "rejected", "reason": str(error)}
    raise ValueError(action)


class CodegenTests(unittest.TestCase):
    def test_generated_module_passes_conformance_cases(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp = Path(tmp)
            _resolved(tmp / "model.json")
            result = _cli(str(tmp / "model.json"), str(tmp / "out"))
            self.assertEqual(result.returncode, 0, result.stderr)
            target = tmp / "out" / "password_reset_generated.py"
            spec = importlib.util.spec_from_file_location("generated_pr", target)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            ran = 0
            for case in json.loads(CASES.read_text(encoding="utf-8"))["cases"]:
                if case["when"]["action"] == "compile":
                    continue
                actual = _run_case(mod, case)
                for key, value in case["then"].items():
                    self.assertEqual(actual[key], value, f"{case['id']} {key}")
                ran += 1
            self.assertGreater(ran, 0)

    def _reset_runtime(self, option):
        tmp = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, tmp, True)
        _resolved(tmp / "model.json", option)
        mod = _load(tmp / "model.json", tmp, "password_reset_generated")
        rt = mod.PasswordResetRuntime(mod.AccountStore({"a@x"}), mod.EmailProvider())
        return mod, rt, {mod.PERSON_CAPABILITY, mod.SEND_MESSAGE_CAPABILITY}

    def test_rate_limit_five_per_15m_per_address_and_origin(self):
        mod, rt, caps = self._reset_runtime("five-per-15m-per-address-and-origin")
        self.assertEqual((mod.RATE_LIMIT_MAX_REQUESTS, mod.RATE_LIMIT_WINDOW_SECONDS), (5, 900))
        results = [rt.request_reset("a@x", caps, now=i, origin="o1") for i in range(6)]
        self.assertEqual([r.reset_message for r in results], ["sent"] * 5 + ["not-sent"])
        self.assertEqual(results[5].failures, ("rate-limit.exceeded",))
        self.assertEqual(results[5].response, results[0].response)
        self.assertEqual(len(rt.email_provider.sent_messages), 5)
        self.assertEqual(rt.request_reset("a@x", caps, now=10, origin="o2").reset_message, "sent")
        self.assertEqual(rt.request_reset("a@x", caps, now=900, origin="o1").reset_message, "sent")

    def test_rate_limit_three_per_hour_per_address(self):
        mod, rt, caps = self._reset_runtime("three-per-hour-per-address")
        self.assertEqual((mod.RATE_LIMIT_MAX_REQUESTS, mod.RATE_LIMIT_WINDOW_SECONDS), (3, 3600))
        results = [rt.request_reset("a@x", caps, now=i, origin=f"o{i}") for i in range(4)]
        self.assertEqual([r.reset_message for r in results], ["sent"] * 3 + ["not-sent"])
        self.assertEqual(rt.request_reset("a@x", caps, now=3600, origin="o9").reset_message, "sent")

    def test_rate_limit_does_not_disclose_account_existence(self):
        _, rt, caps = self._reset_runtime("three-per-hour-per-address")
        known = [rt.request_reset("a@x", caps, now=i) for i in range(5)][-1]
        unknown = [rt.request_reset("nobody@x", caps, now=i) for i in range(5)][-1]
        self.assertEqual(known.outputs, unknown.outputs)
        self.assertEqual(known.failures, unknown.failures)

    def test_expense_approval_passes_conformance_cases(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp = Path(tmp)
            _resolved_expense(tmp / "model.json")
            mod = _load(tmp / "model.json", tmp, "expense_approval_generated")
            cases = json.loads(EXPENSE_CASES.read_text(encoding="utf-8"))["cases"]
            ran = 0
            for case in cases:
                if case["when"]["action"] == "compile":
                    continue
                given = case["given"]
                rt = mod.ExpenseRuntime()
                rt.submit("e1", "sam", given["amount"])
                rt.expenses["e1"].state = given.get("expense", "submitted")
                approver = "sam" if given["approverIsSubmitter"] else "alex"
                action = case["when"]["action"]
                try:
                    if action == "approve":
                        rt.approve("e1", approver, given["approverLimit"])
                    else:
                        rt.reject("e1", approver, given["approverLimit"], case["when"]["reason"])
                    refused = False
                except mod.Refused:
                    refused = True
                then = case["then"]
                expense = rt.expenses["e1"]
                self.assertEqual(expense.state, then["expense"], case["id"])
                if "approval" in then or "rejection" in then:
                    self.assertTrue(refused, case["id"])
                else:
                    self.assertFalse(refused, case["id"])
                if then.get("reasonVisibleToSubmitter"):
                    self.assertEqual(expense.reason, case["when"]["reason"])
                ran += 1
            self.assertEqual(ran, 7)

    def test_expense_routing_and_reason_required(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp = Path(tmp)
            _resolved_expense(tmp / "model.json")
            mod = _load(tmp / "model.json", tmp, "expense_approval_generated")
            rt = mod.ExpenseRuntime()
            rt.submit("e1", "sam", 300)
            self.assertEqual(rt.eligible_approver("e1", [("sam", 9999), ("lee", 100), ("kim", 300)]), "kim")
            self.assertIsNone(rt.eligible_approver("e1", [("sam", 9999), ("lee", 100)]))
            with self.assertRaises(mod.Refused):
                rt.reject("e1", "kim", 300, " ")
            self.assertEqual(rt.expenses["e1"].state, "submitted")

    def test_expense_generation_deterministic_and_blocked_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp = Path(tmp)
            _resolved_expense(tmp / "model.json")
            _cli(str(tmp / "model.json"), str(tmp / "a"))
            _cli(str(tmp / "model.json"), str(tmp / "b"))
            self.assertEqual((tmp / "a" / "expense_approval_generated.py").read_bytes(),
                             (tmp / "b" / "expense_approval_generated.py").read_bytes())
            result = _cli(str(EXPENSE_MODEL), str(tmp / "c"))
            self.assertEqual(result.returncode, 1)
            self.assertIn("no-eligible-approver", result.stderr)
            self.assertFalse((tmp / "c").exists())

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp = Path(tmp)
            _resolved(tmp / "model.json")
            _cli(str(tmp / "model.json"), str(tmp / "a"))
            _cli(str(tmp / "model.json"), str(tmp / "b"))
            self.assertEqual((tmp / "a" / "password_reset_generated.py").read_bytes(),
                             (tmp / "b" / "password_reset_generated.py").read_bytes())

    def test_blocked_model_is_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            result = _cli(str(MODEL), str(Path(tmp) / "out"))
            self.assertEqual(result.returncode, 1)
            self.assertIn("not ready", result.stderr)
            self.assertIn("rate-limit", result.stderr)
            self.assertFalse((Path(tmp) / "out").exists())


if __name__ == "__main__":
    unittest.main()
