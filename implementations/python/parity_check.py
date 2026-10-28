"""Compare Python and TypeScript implementations over shared conformance fixtures.

For every model referenced by a tests/conformance fixture (validation cases,
readiness extension cases, and *.cases.json), both implementations compute the
compilation status, diagnostics, and readiness report; outputs must be equal.
TypeScript is skipped with a notice when node is unavailable.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from orin_model import SemanticModel

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / "tests" / "conformance"
TS_MODEL = ROOT / "implementations" / "typescript" / "src" / "orin_model.ts"

TS_SCRIPT = """
import { readFileSync } from "node:fs";
const { SemanticModel } = await import(process.argv[1]);
const out = {};
for (const path of JSON.parse(process.argv[2])) {
  try {
    const model = new SemanticModel(JSON.parse(readFileSync(path, "utf-8")));
    out[path] = {
      compilation: model.compilationStatus(),
      diagnostics: model.diagnostics().map((d) => ({ code: d.code, objectId: d.objectId ?? null, message: d.message })),
      readiness: JSON.parse(JSON.stringify(model.readinessReport())),
    };
  } catch (error) {
    out[path] = { error: String(error) };
  }
}
console.log(JSON.stringify(out));
"""


def collect_targets(conformance: Path = CONFORMANCE) -> list[tuple[str, str]]:
    """Return (fixture-case label, model filename) pairs."""
    targets: list[tuple[str, str]] = []
    for path in sorted(conformance.glob("*.json")):
        name = path.name
        if not (name.endswith(".cases.json") or name.endswith("validation-cases.json")):
            continue
        fixture = json.loads(path.read_text(encoding="utf-8"))
        top_model = fixture.get("model")
        if top_model:
            targets.append((name, top_model))
        for case in fixture.get("cases", []):
            if case.get("model"):
                targets.append((f"{name}::{case.get('id', '?')}", case["model"]))
    return targets


def python_snapshot(model_path: Path) -> dict[str, Any]:
    try:
        model = SemanticModel.from_json_file(model_path)
        return {
            "compilation": model.compilation_status(),
            "diagnostics": [
                {"code": d.code, "objectId": d.object_id, "message": d.message} for d in model.diagnostics()
            ],
            "readiness": model.readiness_report().to_dict(),
        }
    except Exception as error:  # noqa: BLE001 - reported as a snapshot for comparison
        return {"error": str(error)}


def typescript_snapshots(model_paths: list[Path]) -> dict[str, dict[str, Any]]:
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            TS_SCRIPT,
            TS_MODEL.as_uri(),
            json.dumps([str(p) for p in model_paths]),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"typescript execution failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def compare(py: dict[str, Any], ts: dict[str, Any]) -> str | None:
    if "error" in py or "error" in ts:
        return None if ("error" in py and "error" in ts) else "one implementation errored"
    for key in ("compilation", "diagnostics", "readiness"):
        if py.get(key) != ts.get(key):
            return f"{key} differs"
    return None


def run(conformance: Path = CONFORMANCE, node: str | None = None) -> tuple[list[tuple[str, str, str]], int]:
    node = node if node is not None else shutil.which("node")
    targets = collect_targets(conformance)
    paths = {model: conformance / model for _, model in targets}
    py = {model: python_snapshot(path) for model, path in paths.items()}
    ts: dict[str, dict[str, Any]] | None = None
    notice = ""
    if node:
        try:
            ts = typescript_snapshots(list(paths.values()))
        except (RuntimeError, OSError, json.JSONDecodeError) as error:
            return [("(typescript)", "-", f"FAIL {error}")], 1
    else:
        notice = "node not found; TypeScript parity skipped"
    rows: list[tuple[str, str, str]] = []
    failures = 0
    for label, model in targets:
        if ts is None:
            rows.append((label, model, "SKIP"))
            continue
        problem = compare(py[model], ts.get(str(paths[model]), {"error": "missing"}))
        if problem:
            failures += 1
        rows.append((label, model, f"FAIL {problem}" if problem else "PASS"))
    if notice:
        rows.append(("NOTICE", notice, "SKIP"))
    return rows, failures


def main() -> int:
    rows, failures = run()
    width = max((len(r[0]) for r in rows), default=10)
    mwidth = max((len(r[1]) for r in rows), default=10)
    print(f"{'fixture/case'.ljust(width)}  {'model'.ljust(mwidth)}  parity")
    for label, model, status in rows:
        print(f"{label.ljust(width)}  {model.ljust(mwidth)}  {status}")
    passed = sum(1 for r in rows if r[2] == "PASS")
    print(f"\n{passed} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
