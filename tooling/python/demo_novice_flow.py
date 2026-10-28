"""Scripted end-to-end demo: plain-English request -> ready, generated, verified code.

Run from the repository root:
python -m tooling.python.demo_novice_flow [--app password-reset|expense-approval]
Stdlib only. Writes only to a scratch directory inside the repo and removes it.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from implementations.python.orin_agent_core import OrinDecisionAgent  # noqa: E402

CONFORMANCE = ROOT / "tests" / "conformance"
APPS = {
    "password-reset": {
        "request": (
            "People forget their passwords. Let them reset it by email, but never reveal "
            "whether an account exists, and make reset links expire and work only once."
        ),
        "source": ROOT / "examples" / "password-reset.orin",
        "model": CONFORMANCE / "password-reset.model.json",
        "cases": CONFORMANCE / "password-reset.cases.json",
        "uncertainty": "account.password-reset/uncertainty/rate-limit",
        "choice": "five-per-15m-per-address-and-origin",
        "module": "password_reset_generated.py",
    },
    "expense-approval": {
        "request": (
            "Employees submit expenses and approvers decide them. Nobody may decide their "
            "own expense, and an approver can only approve amounts within their limit."
        ),
        "source": ROOT / "examples" / "expense-approval.orin",
        "model": CONFORMANCE / "expense-approval.model.json",
        "cases": CONFORMANCE / "expense-approval.resolved.cases.json",
        "uncertainty": "finance.expense-approval/uncertainty/no-eligible-approver",
        "choice": None,  # taken from the agent's data-driven options
        "module": "expense_approval_generated.py",
    },
}


def _replay_password_reset(mod, case) -> dict:
    given, action = case.get("given", {}), case["when"]["action"]
    store = mod.AccountStore({"person@example.com"} if given.get("accountExists") else set(),
                             given.get("accountStore", "available") == "available")
    provider = mod.EmailProvider(given.get("emailProvider", "available") == "available")
    rt = mod.PasswordResetRuntime(store, provider)
    caps = {mod.PERSON_CAPABILITY, mod.SEND_MESSAGE_CAPABILITY}
    email = "person@example.com"
    if action == "request-password-reset":
        r = rt.request_reset(email, caps)
        return r.outputs | {"recovery": r.recovery, "failures": r.failures}
    if action == "request-password-reset-twice":
        rs = [rt.request_reset(email, caps) for _ in range(2)]
        return {"tokensDistinct": rs[0].reset_token != rs[1].reset_token,
                "responses": [r.response for r in rs]}
    if action == "request-password-reset-concurrently":
        rs = rt.request_resets_concurrently(given["emails"], caps)
        return {"tokensDistinct": len({r.reset_token for r in rs}) == len(rs),
                "responses": [r.response for r in rs]}
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


def _replay_expense(mod, case) -> dict:
    given, when = case["given"], case["when"]
    rt = mod.ExpenseRuntime()
    rt.submit("e1", "sam", given["amount"])
    if when["action"] == "route":
        others = [(f"approver-limit-{limit}", limit) for limit in given["otherApproverLimits"]]
        routed = rt.eligible_approver("e1", [("sam", given["submitterLimit"]), *others])
        return {"expense": rt.expenses["e1"].state, "routedTo": routed}
    rt.expenses["e1"].state = given.get("expense", "submitted")
    approver = "sam" if given["approverIsSubmitter"] else "alex"
    result: dict = {}
    try:
        if when["action"] == "approve":
            rt.approve("e1", approver, given["approverLimit"])
        else:
            rt.reject("e1", approver, given["approverLimit"], when["reason"])
    except mod.Refused:
        result["approval" if when["action"] == "approve" else "rejection"] = "refused"
    expense = rt.expenses["e1"]
    result["expense"] = expense.state
    if expense.reason:
        result["reasonVisibleToSubmitter"] = expense.reason == when.get("reason")
    return result


REPLAYERS = {"password-reset": _replay_password_reset, "expense-approval": _replay_expense}


def _pick_option(prompt, preferred: str | None) -> str:
    if preferred:
        return preferred
    # Options that keep compilation blocked (e.g. "defer") are not real choices.
    for option in prompt.options:
        if getattr(option, "compilation", None) != "blocked":
            return option.id
    raise RuntimeError("no resolving option offered by the agent")


def run_demo(say=print, keep_dir: Path | None = None, app: str = "password-reset") -> dict:
    """Run every step; returns a dict of step results. Raises on step failure."""
    cfg = APPS[app]
    replay = REPLAYERS[app]
    scratch = Path(tempfile.mkdtemp(prefix="orin-demo-", dir=ROOT))
    results: dict = {"app": app}
    try:
        say("Step 1 - Your request:\n  " + cfg["request"])
        say(f"  An Orin description of this already exists: {cfg['source'].relative_to(ROOT)}.")

        agent = OrinDecisionAgent()
        before = agent.inspect(cfg["source"])
        results["blocked_before"] = bool(before.decisions)
        results["compilation_before"] = before.compilation
        if not before.decisions:
            raise RuntimeError("expected the example to be blocked on a decision")
        need = next((d for d in before.decisions
                     if d.prompt.uncertainty_id == cfg["uncertainty"]), before.decisions[0])
        say("Step 2 - Readiness check: NOT READY. A question must be answered first: "
            + need.prompt.question)

        # The .orin source carries no decision options, so the agent's options
        # come from the matching conformance model and its decisions sidecar.
        planned = agent.inspect(cfg["model"])
        prompt = next(d.prompt for d in planned.decisions
                      if d.prompt.uncertainty_id == cfg["uncertainty"])
        choice = _pick_option(prompt, cfg["choice"])
        applied = agent.apply_decision(cfg["model"], cfg["uncertainty"], choice)
        results["choice"] = choice
        model_path = scratch / f"{app}.decided.json"
        agent.write_model(model_path, applied.model)
        say(f"Step 3 - Decision applied. Substitution: {cfg['source'].name} carries no "
            f"decision options, so the decision was applied to the full semantic model "
            f"{cfg['model'].name} of the same example:\n  " + applied.option.label)

        after = agent.inspect(model_path)
        results["blocked_after"] = bool(after.decisions)
        results["compilation_after"] = after.compilation
        say(f"Step 4 - Re-check: {'still blocked' if after.decisions else 'READY'} "
            f"(compilation: {after.compilation}).")
        if after.decisions or after.compilation != "eligible":
            raise RuntimeError("model is not ready after the decision")

        outdir = scratch / "out"
        proc = subprocess.run(
            [sys.executable, "-m", "implementations.python.codegen.generate",
             str(model_path), str(outdir)],
            cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("code generation failed: " + proc.stderr.strip())
        target = outdir / cfg["module"]
        say(f"Step 5 - Generated a Python implementation ({target.name}, "
            f"{len(target.read_text(encoding='utf-8').splitlines())} lines).")

        spec = importlib.util.spec_from_file_location(
            f"demo_generated_{app.replace('-', '_')}", target)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        passed, failed = [], []
        for case in json.loads(cfg["cases"].read_text(encoding="utf-8"))["cases"]:
            if case["when"]["action"] == "compile":
                continue
            try:
                actual = replay(mod, case)
                ok = all(actual.get(k) == v for k, v in case["then"].items())
            except Exception:
                ok = False
            (passed if ok else failed).append(case["id"])
        results["passed"], results["failed"] = passed, failed
        say(f"Step 6 - Checked against the agreed examples: {len(passed)} passed, "
            f"{len(failed)} failed.")
        for case_id in failed:
            say(f"  FAILED: {case_id}")
        say("Summary: your request became a checked description, one open question "
            "was answered, and the generated code behaves as the examples say."
            if not failed else "Summary: generated code does not match all examples.")
        return results
    finally:
        if keep_dir is not None:
            shutil.copytree(scratch, keep_dir, dirs_exist_ok=True)
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Novice flow demo")
    parser.add_argument("--app", choices=sorted(APPS), default="password-reset")
    args = parser.parse_args(argv)
    try:
        results = run_demo(app=args.app)
    except Exception as error:
        print(f"Demo step failed: {error}", file=sys.stderr)
        return 1
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
