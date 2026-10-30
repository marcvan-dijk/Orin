"""Demo: change ONE decision, regenerate, and see exactly what changes.

Run from the repository root: python -m tooling.python.demo_decision_change
Stdlib only. Uses the public agent and codegen entry points; scratch files are
created inside the repo and removed.

Apps: password-reset (default), expense-approval, shared-tasks
(`--app NAME`). Shared conformance cases are replayed unchanged under every
option. Password-reset rate-limit observations come from shared conformance
cases. The option-specific expense and shared-tasks probes remain DEMO-ONLY,
labelled as such in the output, and are not part of tests/conformance/.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from implementations.python.orin_agent_core import OrinDecisionAgent  # noqa: E402
from implementations.python.codegen.password_reset_rate_limit import replay_case  # noqa: E402

MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
CASES = ROOT / "tests" / "conformance" / "password-reset.cases.json"
RATE_LIMIT_CASES = ROOT / "tests" / "conformance" / "password-reset.rate-limit.cases.json"
UNCERTAINTY = "account.password-reset/uncertainty/rate-limit"
OPTION_A = "five-per-15m-per-address-and-origin"
OPTION_B = "three-per-hour-per-address"
MODULE = "password_reset_generated.py"

MEANING = {
    OPTION_A: "Each email address may request at most 5 resets per 15 minutes from any one network "
              "origin. Another origin has its own allowance. Over the limit, the person still sees "
              "the standard confirmation but no message is sent.",
    OPTION_B: "Each email address may request at most 3 resets per hour, no matter where requests "
              "come from, so switching origin does not help. Over the limit, the person still sees "
              "the standard confirmation but no message is sent.",
}


def _generate(model_path: Path, outdir: Path) -> Path:
    proc = subprocess.run(
        [sys.executable, "-m", "implementations.python.codegen.generate", str(model_path), str(outdir)],
        cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("code generation failed: " + proc.stderr.strip())
    return outdir / MODULE


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _shipped_cases(mod) -> dict[str, str]:
    from tooling.python.demo_novice_flow import _replay_password_reset  # same replayer the novice demo uses
    outcome = {}
    for case in json.loads(CASES.read_text(encoding="utf-8"))["cases"]:
        if case["when"]["action"] == "compile":
            continue
        try:
            actual = _replay_password_reset(mod, case)
            outcome[case["id"]] = "pass" if all(actual.get(k) == v for k, v in case["then"].items()) else "fail"
        except Exception:
            outcome[case["id"]] = "fail"
    return outcome


def _blocks(source: str) -> list[str]:
    """Split generated source into blank-line-separated top-level chunks."""
    return [b for b in re.split(r"\n\s*\n", source) if b.strip()]


def run_demo(say=print) -> dict:
    scratch = Path(tempfile.mkdtemp(prefix="orin-decision-demo-", dir=ROOT))
    try:
        agent = OrinDecisionAgent()
        generated, models = {}, {}
        for label, option in (("A", OPTION_A), ("B", OPTION_B)):
            applied = agent.apply_decision(MODEL, UNCERTAINTY, option)
            path = scratch / f"{label}.model.json"
            agent.write_model(path, applied.model)
            check = agent.inspect(path)
            if check.decisions or check.compilation != "eligible":
                raise RuntimeError(f"option {label} did not make the model ready")
            models[label] = path
            generated[label] = _generate(path, scratch / label)

        src = {k: v.read_text(encoding="utf-8") for k, v in generated.items()}
        mods = {k: _load(v, f"decision_demo_{k}") for k, v in generated.items()}

        say(f"Decision A: {OPTION_A}\n  {MEANING[OPTION_A]}")
        say(f"Decision B: {OPTION_B}\n  {MEANING[OPTION_B]}\n")

        diff = list(difflib.unified_diff(
            src["A"].splitlines(), src["B"].splitlines(),
            "generated/A/" + MODULE, "generated/B/" + MODULE, n=0, lineterm=""))
        say("(1) Unified diff of generated code (A -> B, no context):")
        say("\n".join(diff) or "  (no change)")

        shipped = {k: _shipped_cases(m) for k, m in mods.items()}
        rate_fixture = json.loads(RATE_LIMIT_CASES.read_text(encoding="utf-8"))
        rate_results = {}
        for label, option in (("A", OPTION_A), ("B", OPTION_B)):
            rate_results[label] = {}
            for case in rate_fixture["cases"]:
                actual = replay_case(mods[label], case)
                expected = case["then"][option]
                if actual != expected:
                    raise AssertionError(f"shared rate-limit case {case['id']} failed under {option}: {actual} != {expected}")
                rate_results[label][case["id"]] = actual
        say("\n(2) Shared rate-limit conformance cases (all requests' resetMessages):")
        changed = []
        for case in rate_fixture["cases"]:
            case_id = case["id"]
            a, b = rate_results["A"][case_id]["resetMessages"], rate_results["B"][case_id]["resetMessages"]
            mark = "CHANGES" if a != b else "same"
            if a != b:
                changed.append(case_id)
            say(f"  {mark:7} {case_id}: A={a} B={b}")
        shipped_changed = [c for c in shipped["A"] if shipped["A"][c] != shipped["B"][c]]
        say(f"  shipped conformance cases: A {list(shipped['A'].values()).count('pass')}/{len(shipped['A'])} pass, "
            f"B {list(shipped['B'].values()).count('pass')}/{len(shipped['B'])} pass; "
            f"changed outcome: {shipped_changed or 'none'}")

        blocks_a, blocks_b = _blocks(src["A"]), _blocks(src["B"])
        digest = lambda bs: {hashlib.sha256(b.encode()).hexdigest() for b in bs}
        unchanged = [b for b in blocks_a if hashlib.sha256(b.encode()).hexdigest() in digest(blocks_b)]
        differing = [b for b in blocks_a if b not in unchanged]
        say("\n(3) In plain English: option A lets one origin retry often but short-term; option B is "
            "stricter overall (fewer requests, longer wait) and ignores where requests come from.")
        say(f"\n(4) Unchanged rules: {len(unchanged)} of {len(blocks_a)} generated code blocks are "
            f"byte-identical (token expiry, single use, no-disclosure, capabilities, response shape); "
            f"{len(differing)} block(s) differ (the constants header; only the three RATE_LIMIT_* lines changed).")
        for b in differing:
            say("  differing block begins: " + b.strip().splitlines()[0][:80])
        return {"diff_lines": len(diff), "changed_rate_limit_cases": changed, "shipped": shipped,
                "rate_limits": rate_results, "total_blocks": len(blocks_a), "unchanged_blocks": len(unchanged),
                "differing_blocks": differing, "diff": diff, "src": src}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _generate_any(model_path: Path, outdir: Path, pattern: str) -> Path:
    proc = subprocess.run(
        [sys.executable, "-m", "implementations.python.codegen.generate", str(model_path), str(outdir)],
        cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("code generation failed: " + proc.stderr.strip())
    return next(iter(sorted(outdir.glob(pattern))))


def _diff(src_a: str, src_b: str, name: str) -> list[str]:
    return list(difflib.unified_diff(src_a.splitlines(), src_b.splitlines(), f"{name}/first", f"{name}/second",
                                     n=0, lineterm=""))


EXPENSE_UNCERTAINTY = "finance.expense-approval/uncertainty/no-eligible-approver"
EXPENSE_MODEL = ROOT / "tests" / "conformance" / "expense-approval.model.json"
EXPENSE_RESOLVED = ROOT / "tests" / "conformance" / "expense-approval.resolved.model.json"
EXPENSE_CASES = ROOT / "tests" / "conformance" / "expense-approval.resolved.cases.json"
# DEMO-ONLY: the option examples in the decision prompt state these outcomes, but no shared case replays them.
EXPENSE_PROBE = {"id": "route-when-only-submitter-covers",
                 "expected": {"escalate-to-higher-authority": "escalated",
                              "reject-as-unapprovable": "rejected", "stay-submitted": "submitted"}}


def run_expense(say=print) -> dict:
    from tooling.python.demo_novice_flow import _replay_expense
    scratch = Path(tempfile.mkdtemp(prefix="orin-decision-demo-", dir=ROOT))
    try:
        agent = OrinDecisionAgent()
        models = {}
        for option in ("escalate-to-higher-authority", "reject-as-unapprovable"):
            path = scratch / f"{option}.model.json"
            agent.write_model(path, agent.apply_decision(EXPENSE_MODEL, EXPENSE_UNCERTAINTY, option).model)
            models[option] = path
        models["stay-submitted"] = EXPENSE_RESOLVED  # shipped fixture; not offered by the agent's prompt
        src, mods = {}, {}
        for option, path in models.items():
            gen = _generate_any(path, scratch / option, "expense_approval_generated.py")
            src[option] = gen.read_text(encoding="utf-8")
            mods[option] = _load(gen, "expense_demo_" + option.replace("-", "_"))
        base = "escalate-to-higher-authority"
        diffs = {o: _diff(src[base], src[o], "expense") for o in src if o != base}
        say("Decision: what happens when no approver other than the submitter covers the amount?")
        say("Options compared: " + ", ".join(src) + " (stay-submitted comes from the resolved fixture)")
        say(f"\n(1) Generated-code diff vs {base}: " + ", ".join(f"{o}: {len(d)} lines" for o, d in diffs.items()))
        cases = [c for c in json.loads(EXPENSE_CASES.read_text(encoding="utf-8"))["cases"]
                 if c["when"]["action"] != "compile"]
        shared = {}
        for option, mod in mods.items():
            shared[option] = {}
            for c in cases:
                try:
                    actual = _replay_expense(mod, c)
                    shared[option][c["id"]] = all(actual.get(k) == v for k, v in c["then"].items())
                except Exception:
                    shared[option][c["id"]] = False
        say("(2) Shared conformance cases (expense-approval.resolved.cases.json, replayed unchanged):")
        for option in mods:
            ok = sum(shared[option].values())
            say(f"  {option}: {ok}/{len(cases)} pass")
        probe = {}
        for option, mod in mods.items():
            rt = mod.ExpenseRuntime()
            rt.submit("e1", "sam", 3000)
            rt.eligible_approver("e1", [("sam", 5000), ("a", 100)])
            probe[option] = rt.expenses["e1"].state
        say("(3) DEMO-ONLY probe (derived from option text; no shared case): 3000 expense, only submitter covers it")
        for option in mods:
            want = EXPENSE_PROBE["expected"][option]
            say(f"  {option}: option says '{want}', generated code gives '{probe[option]}' -> "
                + ("matches" if want == probe[option] else "DOES NOT IMPLEMENT THE OPTION"))
        say("\n(4) Finding: the Python expense generator is a fixed template; the chosen option does not "
            "alter it, so switching options changes the model and accepted examples but 0 generated lines. "
            "Only stay-submitted matches the generated behaviour. The TypeScript generator "
            "(generate_expense_approval.ts) supports only noEligibleApprover: stay-submitted and refuses others.")
        return {"diffs": diffs, "shared": shared, "probe": probe, "src": src}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


SHARED_MODEL = ROOT / "tests" / "conformance" / "shared-tasks.minimal.model.json"
SHARED_CASES = ROOT / "tests" / "conformance" / "shared-tasks.minimal.cases.json"
SHARED_UNCERTAINTY = "shared-tasks.minimal/uncertainty/non-member-assignee-completion"
SHARED_OPTIONS = ("membership-required", "assignee-may-complete")
# DEMO-ONLY probe: the option examples exist in the model but no shared case replays them.
SHARED_PROBE = {"owner": "a", "members": [], "list": "l",
                "task": {"id": "t", "list": "l", "state": "open", "assignee": "z"}}


def _shared_runtime(mod, setup):
    rt = mod.Runtime()
    for person in [setup["owner"], *setup["members"]]:
        rt.relate("member-of", person, setup["list"])
    task = setup.get("task")
    if task:
        rt.add_entity(task["id"], "task", task["state"])
        rt.relate("contains", task["list"], task["id"])
        if task.get("assignee"):
            rt.relate("assigned-to", task["assignee"], task["id"])
    return rt


def _shared_outcome(mod, setup, actor, task):
    rt = _shared_runtime(mod, setup)
    try:
        r = rt.run("complete-task", actor, task)
        return {"ok": r.ok, "failure": r.failure, "taskState": rt.state_of(task) if task in rt.entities else None}
    except Exception as error:
        return {"raised": type(error).__name__}


def run_shared_tasks(say=print) -> dict:
    scratch = Path(tempfile.mkdtemp(prefix="orin-decision-demo-", dir=ROOT))
    try:
        agent = OrinDecisionAgent()
        src, mods, reports = {}, {}, {}
        for option in SHARED_OPTIONS:
            path = scratch / f"{option}.model.json"
            agent.write_model(path, agent.apply_decision(SHARED_MODEL, SHARED_UNCERTAINTY, option).model)
            gen = _generate_any(path, scratch / option, "*_generated.py")
            src[option] = gen.read_text(encoding="utf-8")
            mods[option] = _load(gen, "shared_demo_" + option.replace("-", "_"))
            reports[option] = json.loads(gen.with_suffix(".report.json").read_text(encoding="utf-8"))
        a, b = SHARED_OPTIONS
        diff = _diff(src[a], src[b], "shared-tasks")
        say(f"Decision A: {a}  (non-member assignee still fails with unauthorized)")
        say(f"Decision B: {b}  (assignee may complete even if no longer a member)")
        say("\n(1) Unified diff of model-driven generated code (A -> B, no context):")
        say("\n".join(diff) or "  (no change)")
        cases = json.loads(SHARED_CASES.read_text(encoding="utf-8"))["cases"]
        shared = {}
        for option, mod in mods.items():
            shared[option] = {}
            for c in cases:
                got = _shared_outcome(mod, c["setup"], c["action"]["actor"], c["action"]["task"])
                shared[option][c["id"]] = all(got.get(k) == v for k, v in c["then"].items()
                                              if k in ("ok", "failure", "taskState"))
        say("\n(2) Shared conformance cases (shared-tasks.minimal.cases.json, replayed unchanged):")
        for option in mods:
            say(f"  {option}: {sum(shared[option].values())}/{len(cases)} pass")
        probe = {o: _shared_outcome(m, SHARED_PROBE, "z", "t") for o, m in mods.items()}
        say("(3) DEMO-ONLY probe (no shared case): non-member assignee z completes task t")
        for option in mods:
            say(f"  {option}: {probe[option]}")
        hooks = {o: [r["id"] for r in reports[o]["unimplementedRules"] if r["scope"] == "workflow"] for o in mods}
        say(f"(4) Workflow-attached NotImplementedRule hooks: " + ", ".join(f"{o}={len(h)}" for o, h in hooks.items())
            + ". A hook raises until a human supplies an implementation, so under assignee-may-complete even the shared member-completes case "
            "fails until a human supplies the hook: the generator does not yet realise that option.")
        return {"diff": diff, "shared": shared, "probe": probe, "hooks": hooks, "src": src}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", choices=("password-reset", "expense-approval", "shared-tasks"),
                        default="password-reset")
    args = parser.parse_args(argv)
    try:
        {"password-reset": run_demo, "expense-approval": run_expense, "shared-tasks": run_shared_tasks}[args.app]()
    except Exception as error:
        print(f"Demo failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
