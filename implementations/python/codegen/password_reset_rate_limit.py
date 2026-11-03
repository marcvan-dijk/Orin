"""Shared rate-limit cases executed by decision-resolved generated Python.

``run_case(policy_id, case)`` returns the three observable arrays.
``run_fixture(fixture_path=FIXTURE)`` checks every expected result and returns
``{policy_id: {case_id: observables}}``. Missing or invalid fixtures fail loudly.
"""

import json
from pathlib import Path

from implementations.python.codegen.generate import generate_source
from implementations.python.orin_agent_core import OrinDecisionAgent


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
FIXTURE = ROOT / "tests" / "conformance" / "password-reset.rate-limit.cases.json"
UNCERTAINTY = "account.password-reset/uncertainty/rate-limit"
POLICIES = (
    "five-per-15m-per-address-and-origin",
    "three-per-hour-per-address",
)
OBSERVABLES = ("responses", "resetMessages", "accountExistenceDisclosed")


def _object(value, keys, location):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{location} must be an object with keys {sorted(keys)}")


def _text(value, location):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{location} must be a nonempty string")


def _policy(policy_id):
    if policy_id not in POLICIES:
        raise ValueError(f"unsupported rate-limit policy: {policy_id!r}")


def _validate_case(case):
    _object(case, ("id", "given", "when", "then"), "case")
    _text(case["id"], "case.id")
    _object(case["given"], ("existingAddresses",), "case.given")
    addresses = case["given"]["existingAddresses"]
    if not isinstance(addresses, list) or any(not isinstance(item, str) or not item for item in addresses):
        raise ValueError("case.given.existingAddresses must be a list of nonempty strings")
    _object(case["when"], ("requests",), "case.when")
    requests = case["when"]["requests"]
    if not isinstance(requests, list) or not requests:
        raise ValueError("case.when.requests must be a nonempty list")
    for request in requests:
        _object(request, ("email", "origin", "at"), "request")
        _text(request["email"], "request.email")
        if not isinstance(request["origin"], str):
            raise ValueError("request.origin must be a string")
        if type(request["at"]) is not int:
            raise ValueError("request.at must be integer seconds")
    _object(case["then"], POLICIES, "case.then")
    for policy_id, expected in case["then"].items():
        _object(expected, OBSERVABLES, f"case.then.{policy_id}")
        for field, values in expected.items():
            value_type = bool if field == "accountExistenceDisclosed" else str
            if not isinstance(values, list) or len(values) != len(requests):
                raise ValueError(f"{policy_id}.{field} must have one value per request")
            if any(type(value) is not value_type for value in values):
                raise ValueError(f"{policy_id}.{field} has invalid value types")


def load_fixture(path=FIXTURE):
    """Load and validate the complete shared fixture; never skip missing data."""
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    _object(fixture, ("fixtureVersion", "uncertainty", "policies", "cases"), "fixture")
    if fixture["fixtureVersion"] != "0.1.0" or fixture["uncertainty"] != UNCERTAINTY:
        raise ValueError("unsupported rate-limit fixture version or uncertainty")
    policies = fixture["policies"]
    if not isinstance(policies, list):
        raise ValueError("fixture.policies must be a list")
    ids = []
    for policy in policies:
        _object(policy, ("id",), "policy")
        _policy(policy["id"])
        ids.append(policy["id"])
    if len(ids) != len(POLICIES) or set(ids) != set(POLICIES):
        raise ValueError("fixture must include each supported policy exactly once")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture.cases must be a nonempty list")
    case_ids = set()
    for case in cases:
        _validate_case(case)
        if case["id"] in case_ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        case_ids.add(case["id"])
    return fixture


def _generated(policy_id):
    _policy(policy_id)
    model = OrinDecisionAgent().apply_decision(MODEL, UNCERTAINTY, policy_id).model
    source = generate_source(model)
    namespace = {"__name__": "password_reset_rate_limit_generated"}
    exec(compile(source, "<password-reset-generated>", "exec"), namespace)
    return namespace


def replay_case(generated_module, case):
    """Replay a validated case using a generated module (or its exec namespace)."""
    _validate_case(case)
    namespace = generated_module if isinstance(generated_module, dict) else vars(generated_module)
    runtime = namespace["PasswordResetRuntime"](
        namespace["AccountStore"](set(case["given"]["existingAddresses"])),
        namespace["EmailProvider"](),
    )
    capabilities = {namespace["PERSON_CAPABILITY"], namespace["SEND_MESSAGE_CAPABILITY"]}
    results = [
        runtime.request_reset(
            request["email"], capabilities, now=request["at"], origin=request["origin"]
        )
        for request in case["when"]["requests"]
    ]
    return {
        "responses": [result.response for result in results],
        "resetMessages": [result.reset_message for result in results],
        "accountExistenceDisclosed": [result.account_existence_disclosed for result in results],
    }


def run_case(policy_id, case):
    """Run one policy/case with a fresh generated runtime, returning observables."""
    _policy(policy_id)
    _validate_case(case)
    return replay_case(_generated(policy_id), case)


def run_fixture(fixture_path=FIXTURE):
    """Verify all policy/case results, returning their complete observable arrays."""
    fixture = load_fixture(fixture_path)
    results = {}
    for policy in fixture["policies"]:
        policy_id = policy["id"]
        namespace = _generated(policy_id)
        results[policy_id] = {}
        for case in fixture["cases"]:
            actual = replay_case(namespace, case)
            expected = case["then"][policy_id]
            if actual != expected:
                raise AssertionError(
                    f"{policy_id}/{case['id']}: expected {expected!r}, got {actual!r}"
                )
            results[policy_id][case["id"]] = actual
    return results


if __name__ == "__main__":
    print(json.dumps(run_fixture(), sort_keys=True))
