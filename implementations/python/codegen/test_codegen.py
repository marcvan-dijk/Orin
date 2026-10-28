import importlib.util
import json
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


def _resolved(path):
    doc = json.loads(MODEL.read_text(encoding="utf-8"))
    doc["unresolved"] = [item for item in doc["unresolved"] if item != RATE_LIMIT]
    path.write_text(json.dumps(doc), encoding="utf-8")


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
