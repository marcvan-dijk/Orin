"""Dependency-free Orin command line: check, readiness, inspect, decide, examples.

Exit codes: 0 ok/ready, 1 problems found (diagnostics or failing examples),
2 blocked (decisions required), 3 invalid input or usage.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
IMPL = ROOT / "implementations" / "python"
CONFORMANCE = ROOT / "tests" / "conformance"

EXIT_OK, EXIT_PROBLEMS, EXIT_BLOCKED, EXIT_INVALID = 0, 1, 2, 3

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(IMPL) not in sys.path:
    sys.path.insert(0, str(IMPL))

from implementations.python import orin_agent_core as core  # noqa: E402


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_INVALID)


def _load(path: str):
    return core.OrinDecisionAgent()._load_artifact(path).model


def cmd_check(args) -> int:
    model = _load(args.file)
    diagnostics = model.diagnostics()
    status = model.compilation_status()
    if not diagnostics:
        print(f"OK: {args.file} is valid (compilation: {status}).")
        return EXIT_OK
    print(f"PROBLEMS: {args.file} has {len(diagnostics)} issue(s) (compilation: {status}).")
    for d in diagnostics:
        where = f" [{d.object_id}]" if d.object_id else ""
        print(f"  {d.code}{where}: {d.message}")
    print("Fix the issues above, then run check again.")
    return EXIT_PROBLEMS


def cmd_readiness(args) -> int:
    report = _load(args.file).readiness_report()
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return EXIT_BLOCKED if report.status == "blocked" else EXIT_OK
    blocking = [d for d in report.diagnostics if d.blocking]
    others = [d for d in report.diagnostics if not d.blocking]
    if blocking or report.status == "blocked":
        print(f"BLOCKED: {args.file} needs {len(blocking)} decision(s) before it is ready.")
        print("Required decisions:")
        for d in blocking:
            where = f" [{d.object_id}]" if d.object_id else ""
            print(f"  - {d.code}{where}: {d.message}")
    else:
        print(f"READY: {args.file} has no blocking decisions.")
    if others:
        print("Notes (non-blocking):")
        for d in others:
            where = f" [{d.object_id}]" if d.object_id else ""
            print(f"  - {d.code}{where}: {d.message}")
    return EXIT_BLOCKED if (blocking or report.status == "blocked") else EXIT_OK


def _cases_for(path: Path) -> Path | None:
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


def _run_cases(cases_path: Path, model_path: Path):
    fixture = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = fixture.get("cases", [])
    first = cases[0] if cases else {}
    if "when" in first:
        from conformance_runner import execute_case
        from orin_model import SemanticModel

        model = SemanticModel.from_json_file(model_path)
        return [(c["id"], execute_case(model, c), c["then"]) for c in cases]
    from shared_tasks_conformance import run_fixture, run_minimal_fixture

    runner = run_minimal_fixture if "setup" in first else run_fixture
    return runner(cases_path)


def _matches(actual, expected) -> bool:
    return all(actual.get(k) == v for k, v in expected.items())


def cmd_examples(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"invalid input: file not found: {path}", file=sys.stderr)
        return EXIT_INVALID
    cases_path = _cases_for(path)
    if cases_path is None:
        print(f"No examples found for {path.name} (looked for <name>.cases.json in "
              f"{path.parent} and tests/conformance).")
        return EXIT_OK
    model_path = path
    if path.suffix == ".orin":
        sibling = cases_path.with_name(cases_path.name.replace(".cases.json", ".model.json"))
        if sibling.is_file():
            model_path = sibling
    try:
        results = _run_cases(cases_path, model_path)
    except (KeyError, ValueError, TypeError, OSError) as error:
        print(f"invalid input: could not run {cases_path.name}: {error}", file=sys.stderr)
        return EXIT_INVALID
    failed = 0
    print(f"Running examples from {cases_path.name}")
    for case_id, actual, expected in results:
        if _matches(actual, expected):
            print(f"  PASS {case_id}")
        else:
            failed += 1
            print(f"  FAIL {case_id}")
            print(f"       expected: {json.dumps(expected, sort_keys=True)}")
            print(f"       actual:   {json.dumps(actual, sort_keys=True, default=str)}")
    print(f"{len(results) - failed}/{len(results)} examples passed.")
    return EXIT_PROBLEMS if failed else EXIT_OK


_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

_SKELETON = """module {name} {{
  purpose "Describe what {name} is for and who it serves."

  rule first-guarantee {{
    guarantee "State one thing that must always be true about {name}."
  }}

  workflow main-flow {{
    input request
    outcome "The person receives a clear result for their request."
  }}

  example typical-use {{
    given "A person with a valid request."
    when "They submit the request."
    then "They see a clear result."
  }}

  uncertainty first-open-question {{
    question "What should happen in the most consequential case not yet decided?"
  }}
}}
"""


def cmd_new(args) -> int:
    if not _NAME_RE.match(args.name):
        print("invalid input: name must be lowercase words joined by hyphens, e.g. my-app",
              file=sys.stderr)
        return EXIT_INVALID
    target = Path(args.out or ".") / f"{args.name}.orin"
    if target.exists():
        print(f"invalid input: {target} already exists", file=sys.stderr)
        return EXIT_INVALID
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_SKELETON.format(name=args.name), encoding="utf-8", newline="\n")
    print(f"Created {target}. Edit it, then run: orin_cli check {target}")
    return EXIT_OK


def _unavailable(what: str) -> int:
    print(f"error: {what} is not available", file=sys.stderr)
    return EXIT_INVALID


def cmd_generate(args) -> int:
    model = Path(args.model)
    if not model.is_file():
        print(f"invalid input: model file not found: {model}", file=sys.stderr)
        return EXIT_INVALID
    if model.suffix != ".json":
        print("invalid input: generate needs a semantic model .json file", file=sys.stderr)
        return EXIT_INVALID
    decision = Path(args.decision) if args.decision else None
    if args.target == "python":
        module = IMPL / "codegen" / "generate.py"
        if not module.is_file():
            return _unavailable("python code generation")
        # The Python generator reads accepted decisions from the model itself.
        cmd = [sys.executable, "-m", "implementations.python.codegen.generate",
               str(model), args.out]
    else:
        cli = ROOT / "implementations" / "typescript" / "src" / "codegen" / "cli.ts"
        if not cli.is_file():
            return _unavailable("typescript code generation (cli.ts not found)")
        node = shutil.which("node")
        if node is None:
            return _unavailable("typescript code generation (node is not installed)")
        if decision is None or not decision.is_file():
            print("invalid input: typescript generation needs --decision <decision.json file>",
                  file=sys.stderr)
            return EXIT_INVALID
        cmd = [node, "--experimental-strip-types", str(cli), str(model), str(decision), args.out]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(
        [str(ROOT)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])))
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode == 0:
        return EXIT_OK
    return EXIT_PROBLEMS if result.returncode == 1 else EXIT_INVALID


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="orin_cli", description="Check and inspect Orin programs.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    sub.add_parser("check", help="validate a .orin or model.json").add_argument("file")
    ready = sub.add_parser("readiness", help="ready/blocked plus required decisions")
    ready.add_argument("file")
    ready.add_argument("--json", action="store_true", help="emit the readiness report as JSON")
    sub.add_parser("examples", help="run matching conformance cases").add_argument("file")
    new = sub.add_parser("new", help="scaffold a minimal valid .orin file")
    new.add_argument("name")
    new.add_argument("--out", help="directory to write into (default: current)")
    gen = sub.add_parser("generate", help="generate an implementation from a model and decision")
    gen.add_argument("model")
    gen.add_argument("--decision", help="decision id or decision .json file")
    gen.add_argument("--target", required=True, choices=["python", "typescript"])
    gen.add_argument("--out", required=True, help="output directory")
    for name, text in (("inspect", "inspect decisions (see orin_agent_core)"),
                       ("decide", "apply a human decision (see orin_agent_core)")):
        sub.add_parser(name, help=text, add_help=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("inspect", "decide"):
        try:
            return core.main(argv)
        except SystemExit as exit_:
            return exit_.code if isinstance(exit_.code, int) else EXIT_INVALID
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exit_:
        return exit_.code if isinstance(exit_.code, int) else EXIT_OK
    handler = {"check": cmd_check, "readiness": cmd_readiness, "examples": cmd_examples,
               "new": cmd_new, "generate": cmd_generate}[args.command]
    try:
        return handler(args)
    except core.AgentError as error:
        print(f"invalid input: {error}", file=sys.stderr)
        return EXIT_INVALID
    except (ValueError, OSError) as error:
        print(f"invalid input: {error}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
