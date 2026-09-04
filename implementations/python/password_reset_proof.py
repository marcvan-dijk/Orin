"""End-to-end proof runner for Orin password-reset meaning derivation."""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from conformance_runner import execute_case, expected_case_result, load_cases
from lowering import lower
from orin_model import SemanticModel


ROOT = Path(__file__).parents[2]
MODEL_FIXTURE = ROOT / "tests" / "conformance" / "password-reset.model.json"
CASES_FIXTURE = ROOT / "tests" / "conformance" / "password-reset.cases.json"
POLICIES_FIXTURE = ROOT / "tests" / "conformance" / "password-reset.policies.json"


def _resolve_rate_limit(model: SemanticModel) -> SemanticModel:
    resolved = deepcopy(model.document)
    for obj in resolved.get("objects", []):
        if obj.get("kind") != "uncertainty":
            continue
        if obj.get("id") == "account.password-reset/uncertainty/rate-limit":
            obj["status"] = "resolved"
    return SemanticModel(resolved)


def _behavioral_case_results(model: SemanticModel, cases: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases["cases"]:
        action = case.get("when", {}).get("action")
        if action is None:
            raise AssertionError(f"case {case.get('id', '<unknown>')} missing when.action")
        if action == "compile":
            continue
        actual = execute_case(model, case)
        expected = expected_case_result(case)
        for key, value in expected.items():
            if actual[key] != value:
                raise AssertionError(f"case {case['id']} mismatch for '{key}': {actual[key]} != {value}")
        results.append({"id": case["id"], "actual": actual})
    return results


def run_derivation_proof() -> dict[str, Any]:
    blocked_model = SemanticModel.from_json_file(MODEL_FIXTURE)
    cases = load_cases(CASES_FIXTURE)
    policies = load_cases(POLICIES_FIXTURE)
    variants = policies.get("variants", [])
    if len(variants) < 2:
        raise AssertionError("proof requires at least two policy variants")

    blocked_compile_cases = [
        case
        for case in cases["cases"]
        if case.get("when", {}).get("action") == "compile" and case.get("then", {}).get("compilation") == "blocked"
    ]
    if not blocked_compile_cases:
        raise AssertionError("cases fixture must include a blocked compile case for unresolved ambiguity")
    blocked_case = blocked_compile_cases[0]
    blocked_compile = execute_case(blocked_model, blocked_case)["compilation"]

    resolved_model = _resolve_rate_limit(blocked_model)
    resolved_status = resolved_model.compilation_status()
    if resolved_status != "eligible":
        raise AssertionError(f"resolved model should be eligible, got {resolved_status}")

    variant_outputs: list[dict[str, Any]] = []
    for variant in variants:
        variant_doc = deepcopy(resolved_model.document)
        variant_doc.setdefault("module", {})["implementationPolicies"] = variant["implementationPolicies"]
        variant_model = SemanticModel(variant_doc)
        lowered = lower(variant_model)
        if "artifact" not in lowered:
            raise AssertionError(f"variant {variant['id']} lowering must include artifact output")
        behavioral_results = _behavioral_case_results(variant_model, cases)
        variant_outputs.append({
            "id": variant["id"],
            "derived": lowered["artifact"],
            "behavior": behavioral_results,
            "canonical": variant_model.canonical(),
        })

    if not variant_outputs:
        raise AssertionError("proof requires at least one derived variant output")
    if len({json.dumps(item["derived"], sort_keys=True) for item in variant_outputs}) < 2:
        raise AssertionError("derived artifacts should differ across policy variants")
    first_behavior = variant_outputs[0]["behavior"]
    if any(item["behavior"] != first_behavior for item in variant_outputs[1:]):
        raise AssertionError("observable behavior should remain equal across policy variants")
    canonical_stable = all(item["canonical"] == variant_outputs[0]["canonical"] for item in variant_outputs[1:])

    return {
        "blockedCompilation": blocked_compile,
        "resolvedCompilation": resolved_status,
        "canonicalMeaningStableAcrossVariants": canonical_stable,
        "variants": [
            {"id": item["id"], "derivedArtifact": item["derived"]} for item in variant_outputs
        ],
        "behaviorCases": [item["id"] for item in variant_outputs[0]["behavior"]],
    }


def main() -> int:
    print(json.dumps(run_derivation_proof(), indent=2))
    return 0


def run_password_reset_proof() -> dict[str, Any]:
    """Backward-compatible wrapper for existing tests/imports."""
    return run_derivation_proof()


if __name__ == "__main__":
    raise SystemExit(main())
