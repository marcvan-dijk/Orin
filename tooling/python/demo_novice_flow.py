"""Scripted end-to-end demo: plain-English request -> ready, generated, verified code.

Run from the repository root: python -m tooling.python.demo_novice_flow
Stdlib only. Writes only to a scratch directory inside the repo and removes it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from implementations.python.codegen.test_codegen import _run_case  # noqa: E402
from implementations.python.orin_agent_core import OrinDecisionAgent  # noqa: E402

REQUEST = (
    "People forget their passwords. Let them reset it by email, but never reveal "
    "whether an account exists, and make reset links expire and work only once."
)
SOURCE = ROOT / "examples" / "password-reset.orin"
FULL_MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
CASES = ROOT / "tests" / "conformance" / "password-reset.cases.json"
RATE_LIMIT = "account.password-reset/uncertainty/rate-limit"
CHOICE = "five-per-15m-per-address-and-origin"


def run_demo(say=print, keep_dir: Path | None = None) -> dict:
    """Run every step; returns a dict of step results. Raises on step failure."""
    scratch = Path(tempfile.mkdtemp(prefix="orin-demo-", dir=ROOT))
    results: dict = {}
    try:
        say("Step 1 - Your request:\n  " + REQUEST)
        say(f"  An Orin description of this already exists: {SOURCE.relative_to(ROOT)}.")

        agent = OrinDecisionAgent()
        before = agent.inspect(SOURCE)
        results["blocked_before"] = bool(before.decisions)
        results["compilation_before"] = before.compilation
        say("Step 2 - Readiness check: " + (
            "NOT READY. A question must be answered first: "
            + before.decisions[0].prompt.question if before.decisions else "ready."))
        if not before.decisions:
            raise RuntimeError("expected the example to be blocked on a decision")

        applied = agent.apply_decision(FULL_MODEL, RATE_LIMIT, CHOICE)
        model_path = scratch / "password-reset.decided.json"
        agent.write_model(model_path, applied.model)
        say("Step 3 - Decision applied to the full semantic model of the same example:\n  "
            + applied.option.label)

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
        target = outdir / "password_reset_generated.py"
        say(f"Step 5 - Generated a Python implementation ({target.name}, "
            f"{len(target.read_text(encoding='utf-8').splitlines())} lines).")

        spec = importlib.util.spec_from_file_location("demo_generated_pr", target)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        passed, failed = [], []
        for case in json.loads(CASES.read_text(encoding="utf-8"))["cases"]:
            if case["when"]["action"] == "compile":
                continue
            try:
                actual = _run_case(mod, case)
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
        if keep_dir is None:
            shutil.rmtree(scratch, ignore_errors=True)
        else:
            shutil.copytree(scratch, keep_dir, dirs_exist_ok=True)
            shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    try:
        results = run_demo()
    except Exception as error:
        print(f"Demo step failed: {error}", file=sys.stderr)
        return 1
    return 1 if results["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
