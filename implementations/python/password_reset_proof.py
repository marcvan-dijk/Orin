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
        if case["when"]["action"] == "compile":
            continue
        actual = execute_case(model, case)
        expected = expected_case_result(case)
        for key, value in expected.items():
            if actual[key] != value:
                raise AssertionError(f"case {case['id']} mismatch for '{key}': {actual[key]} != {value}")
        results.append({"id": case["id"], "actual": actual})
    return results


def run_password_reset_proof() -> dict[str, Any]:
    blocked_model = SemanticModel.from_json_file(MODEL_FIXTURE)
    cases = load_cases(CASES_FIXTURE)
    policies = load_cases(POLICIES_FIXTURE)

    blocked_case = next(case for case in cases["cases"] if case["when"]["action"] == "compile")
    blocked_compile = execute_case(blocked_model, blocked_case)["compilation"]

    resolved_model = _resolve_rate_limit(blocked_model)
    resolved_status = resolved_model.compilation_status()
    if resolved_status != "eligible":
        raise AssertionError(f"resolved model should be eligible, got {resolved_status}")

    variant_outputs: list[dict[str, Any]] = []
    for variant in policies["variants"]:
        variant_doc = deepcopy(resolved_model.document)
        variant_doc["implementationPolicies"] = variant["implementationPolicies"]
        variant_model = SemanticModel(variant_doc)
        lowered = lower(variant_model)
        behavioral_results = _behavioral_case_results(variant_model, cases)
        variant_outputs.append({"id": variant["id"], "derived": lowered["artifact"], "behavior": behavioral_results})

    if variant_outputs[0]["derived"] == variant_outputs[1]["derived"]:
        raise AssertionError("derived artifacts should differ across policy variants")
    if variant_outputs[0]["behavior"] != variant_outputs[1]["behavior"]:
        raise AssertionError("observable behavior should remain equal across policy variants")

    return {
        "blockedCompilation": blocked_compile,
        "resolvedCompilation": resolved_status,
        "canonicalMeaningStableAcrossVariants": SemanticModel({
            **resolved_model.document,
            "implementationPolicies": policies["variants"][0]["implementationPolicies"],
        }).canonical() == SemanticModel({
            **resolved_model.document,
            "implementationPolicies": policies["variants"][1]["implementationPolicies"],
        }).canonical(),
        "variants": [
            {"id": item["id"], "derivedArtifact": item["derived"]} for item in variant_outputs
        ],
        "behaviorCases": [item["id"] for item in variant_outputs[0]["behavior"]],
    }


def main() -> int:
    print(json.dumps(run_password_reset_proof(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
