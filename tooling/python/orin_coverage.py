"""`orin_cli coverage`: which rules are proved by examples, and what is left over."""
from __future__ import annotations

import json
import re

EXIT_OK, EXIT_PROBLEMS = 0, 1

_FAILURE_WORDS = re.compile(
    r"refus|fail|cannot|can't|reject|denied|unauthori|not-found|not found|"
    r"not allowed|error|blocked", re.I)


def _short(object_id: str) -> str:
    return object_id.rsplit("/", 1)[-1]


def _text(obj: dict) -> str:
    parts = [*(obj.get("claims") or []), *(obj.get("expects") or []), obj.get("name", "")]
    return " ".join(str(p) for p in parts)


def build_report(document: dict) -> dict:
    objects = [o for o in document.get("objects", []) if isinstance(o, dict) and "id" in o]
    by_kind: dict[str, list[dict]] = {}
    for obj in objects:
        by_kind.setdefault(obj.get("kind", ""), []).append(obj)
    rules, examples = by_kind.get("rule", []), by_kind.get("example", [])
    workflows = by_kind.get("workflow", [])
    rule_ids = {r["id"] for r in rules}
    example_ids = {e["id"] for e in examples}

    proofs: dict[str, set[str]] = {r["id"]: set() for r in rules}
    for rule in rules:
        proofs[rule["id"]].update(l for l in rule.get("evidenceLinks", []) if l in example_ids)
    for example in examples:
        for ref in example.get("requires", []):
            if ref in rule_ids:
                proofs[ref].add(example["id"])
    proving = {e for found in proofs.values() for e in found}

    failure_examples = [e for e in examples if _FAILURE_WORDS.search(_text(e))]
    failure_gaps = []
    for wf in workflows:
        if not wf.get("failureBehavior"):
            continue
        verb = _short(wf["id"]).split("-")[0].lower()
        linked = [e for e in failure_examples
                  if wf["id"] in e.get("requires", []) or verb in _text(e).lower()]
        if not linked:
            failure_gaps.append(wf["id"])

    def unused(kind: str) -> list[str]:
        result = []
        for obj in by_kind.get(kind, []):
            others = json.dumps([o for o in objects if o is not obj], sort_keys=True)
            if f'"{obj["id"]}"' not in others:
                result.append(obj["id"])
        return result

    return {
        "rules": [{"id": r["id"], "claim": (r.get("claims") or [""])[0],
                   "examples": sorted(proofs[r["id"]])} for r in rules],
        "unprovedRules": [r["id"] for r in rules if not proofs[r["id"]]],
        "orphanExamples": [e["id"] for e in examples if e["id"] not in proving],
        "workflowsWithoutFailureExample": failure_gaps,
        "unusedCapabilities": unused("capability"),
        "unusedStates": unused("state"),
    }


def format_report(report: dict) -> str:
    lines: list[str] = []
    proved = [r for r in report["rules"] if r["examples"]]
    lines.append(f"Rules proved by an example: {len(proved)} of {len(report['rules'])}")
    for rule in proved:
        names = ", ".join(_short(e) for e in rule["examples"])
        lines.append(f"  - {_short(rule['id'])}: {names}")

    def section(title: str, ids: list[str], hint: str) -> None:
        lines.append("")
        if ids:
            lines.append(f"{title} ({len(ids)}):")
            lines.extend(f"  - {_short(i)}" for i in ids)
            lines.append(f"  {hint}")
        else:
            lines.append(f"{title}: none")

    section("Rules with no example", report["unprovedRules"],
            "Add an example that shows each rule, then link it.")
    section("Examples that prove no rule", report["orphanExamples"],
            "Link each example to a rule, or add the rule it shows.")
    section("Workflows whose failure has no example", report["workflowsWithoutFailureExample"],
            "Add an example where the workflow fails.")
    section("Capabilities not used", report["unusedCapabilities"],
            "Use them in a workflow or rule, or remove them.")
    section("States not used", report["unusedStates"],
            "Use them in a workflow or rule, or remove them.")
    return "\n".join(lines)


def run(model, as_json: bool, strict: bool, out=print) -> int:
    report = build_report(model.document)
    out(json.dumps(report, indent=2) if as_json else format_report(report))
    return EXIT_PROBLEMS if strict and report["unprovedRules"] else EXIT_OK
