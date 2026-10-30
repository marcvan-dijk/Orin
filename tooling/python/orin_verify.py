"""Verification stage: generate Python code for a model and run its examples against it.

Usage: python -m tooling.python.orin_cli verify FILE [--decide UNCERTAINTY=OPTION]
Exit codes: 0 all runnable examples passed, 1 a failure or nothing could be run,
3 invalid input.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / "tests" / "conformance"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXIT_OK, EXIT_FAIL, EXIT_INVALID = 0, 1, 3
EMAIL = "person@example.com"


class Skip(Exception):
    """The example cannot be run against the generated code yet."""


def _find_cases(path: Path) -> Path | None:
    name = path.name
    for suffix in (".model.json", ".structured.json", ".json", ".orin"):
        if name.endswith(suffix):
            stem = name[: -len(suffix)]
            break
    else:
        return None
    for directory in (path.parent, CONFORMANCE):
        candidate = directory / f"{stem}.cases.json"
        if candidate.is_file():
            return candidate
    return None


def _run_password_reset(mod, case: dict) -> dict:
    given, action = case.get("given", {}), case["when"]["action"]
    store = mod.AccountStore({EMAIL} if given.get("accountExists") else set(),
                             given.get("accountStore", "available") == "available")
    runtime = mod.PasswordResetRuntime(
        store, mod.EmailProvider(given.get("emailProvider", "available") == "available"))
    caps = {mod.PERSON_CAPABILITY, mod.SEND_MESSAGE_CAPABILITY}
    if action == "request-password-reset":
        result = runtime.request_reset(EMAIL, caps)
        return {**result.outputs, "recovery": result.recovery, "failures": result.failures}
    if action == "request-password-reset-twice":
        results = [runtime.request_reset(EMAIL, caps) for _ in range(2)]
        return {"tokensDistinct": results[0].reset_token != results[1].reset_token,
                "responses": [r.response for r in results]}
    if action == "request-password-reset-concurrently":
        results = runtime.request_resets_concurrently(given["emails"], caps)
        return {"tokensDistinct": len({r.reset_token for r in results}) == len(results),
                "responses": [r.response for r in results]}
    if action in ("redeem-expired-token", "redeem-token-twice"):
        token = runtime.request_reset(EMAIL, caps).reset_token
        if action == "redeem-expired-token":
            when = mod.TOKEN_TTL_SECONDS
        else:
            runtime.redeem_reset(token, 1)
            when = 2
        try:
            runtime.redeem_reset(token, when)
        except mod.TokenRejected as error:
            return {"token": "rejected", "reason": str(error)}
        return {"token": "accepted"}
    raise Skip(f"no way to run the action '{action}' yet")


def _run_expense(mod, case: dict) -> dict:
    given, when = case.get("given", {}), case["when"]
    action = when["action"]
    if action not in ("approve", "reject"):
        raise Skip(f"no way to run the action '{action}' yet")
    runtime = mod.ExpenseRuntime()
    runtime.submit("e1", "sam", given["amount"])
    runtime.expenses["e1"].state = given.get("expense", "submitted")
    actor = "sam" if given["approverIsSubmitter"] else "alex"
    refused = False
    try:
        if action == "approve":
            runtime.approve("e1", actor, given["approverLimit"])
        else:
            runtime.reject("e1", actor, given["approverLimit"], when["reason"])
    except mod.Refused:
        refused = True
    expense = runtime.expenses["e1"]
    actual = {"expense": expense.state}
    if refused:
        actual["approval" if action == "approve" else "rejection"] = "refused"
    if action == "reject" and not refused:
        actual["reasonVisibleToSubmitter"] = expense.reason == when["reason"]
    return actual


_ADAPTERS = {
    "password_reset_generated.py": _run_password_reset,
    "expense_approval_generated.py": _run_expense,
}


def _generate(path: Path, outdir: Path, decisions: list[str]) -> Path:
    """Run the Python generator in its own process so it never mixes import styles with the CLI."""
    cmd = [sys.executable, "-m", "implementations.python.codegen.generate", str(path), str(outdir)]
    for decision in decisions:
        cmd += ["--decide", decision]
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise GenerationFailed(result.stderr.strip().removeprefix("error: ") or "unknown error")
    return Path(result.stdout.strip().splitlines()[-1])


class GenerationFailed(Exception):
    pass


def _load_module(target: Path):
    spec = importlib.util.spec_from_file_location(target.stem, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(file: str, decisions: list[str] | None = None, out=print) -> int:
    path = Path(file)
    if not path.is_file():
        print(f"invalid input: file not found: {path}", file=sys.stderr)
        return EXIT_INVALID
    cases_path = _find_cases(path)
    if cases_path is None:
        out(f"Cannot verify {path.name}: no examples file found "
            f"(looked for <name>.cases.json next to it and in tests/conformance).")
        return EXIT_FAIL
    try:
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    except (OSError, ValueError, KeyError) as error:
        print(f"invalid input: cannot read {cases_path.name}: {error}", file=sys.stderr)
        return EXIT_INVALID

    with tempfile.TemporaryDirectory(dir=ROOT, prefix=".orin-verify-") as tmp:
        try:
            target = _generate(path.resolve(), Path(tmp) / "out", list(decisions or []))
        except (GenerationFailed, OSError) as error:
            out(f"Cannot verify {path.name}: code could not be generated.")
            out(f"  Reason: {error}")
            out("  Fix: decide the open questions first, e.g. add --decide UNCERTAINTY=OPTION.")
            return EXIT_FAIL
        adapter = _ADAPTERS.get(target.name)
        module = _load_module(target) if adapter else None

        out(f"Generated {target.name}. Running examples from {cases_path.name}")
        passed = failed = skipped = 0
        for case in cases:
            label = case["id"].rsplit("/", 1)[-1]
            when = case.get("when", {})
            try:
                if when.get("action") == "compile":
                    raise Skip("this example checks the compile step, not the code")
                if adapter is None:
                    raise Skip(f"no example runner for {target.name} yet")
                actual = adapter(module, case)
            except Skip as reason:
                skipped += 1
                out(f"  SKIP {label}: cannot run yet - {reason}")
                continue
            except Exception as error:  # the generated code crashed: that is a failure
                failed += 1
                out(f"  FAIL {label}: the code raised {type(error).__name__}: {error}")
                continue
            wrong = {k: (v, actual.get(k)) for k, v in case["then"].items() if actual.get(k) != v}
            if wrong:
                failed += 1
                out(f"  FAIL {label}")
                for key, (want, got) in wrong.items():
                    out(f"       {key}: expected {json.dumps(want)}, got {json.dumps(got, default=str)}")
            else:
                passed += 1
                out(f"  PASS {label}")

    out(f"{passed} passed, {failed} failed, {skipped} could not be run yet.")
    if skipped:
        out("Examples that could not be run are NOT verified.")
    if failed:
        return EXIT_FAIL
    if not passed:
        out("Nothing was verified.")
        return EXIT_FAIL
    return EXIT_OK
