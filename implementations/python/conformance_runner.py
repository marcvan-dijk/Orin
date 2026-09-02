"""Execute language-neutral password-reset conformance cases."""

import json
from pathlib import Path
from typing import Any

from orin_model import SemanticModel
from password_reset import AccountStore, EmailProvider, PasswordResetRuntime, TokenRejected


def load_cases(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def execute_case(model: SemanticModel, case: dict[str, Any]) -> dict[str, Any]:
    given = case.get("given", {})
    action = case["when"]["action"]
    if action == "compile":
        return {"compilation": model.compilation_status()}

    store = AccountStore({"person@example.com"} if given.get("accountExists", False) else set(), given.get("accountStore", "available") == "available")
    email_provider = EmailProvider(given.get("emailProvider", "available") == "available")
    runtime = PasswordResetRuntime(store, email_provider)
    capabilities = {"person.request-password-reset", "system.send-reset-message"}

    if action == "request-password-reset":
        result = runtime.request_reset("person@example.com", capabilities)
        return result.outputs | {"recovery": result.recovery, "failures": result.failures}
    if action == "request-password-reset-twice":
        results = [runtime.request_reset("person@example.com", capabilities) for _ in range(2)]
        return {"tokensDistinct": results[0].reset_token != results[1].reset_token, "responses": [item.response for item in results]}
    if action == "request-password-reset-concurrently":
        results = runtime.request_resets_concurrently(given["emails"], capabilities)
        return {"tokensDistinct": len({item.reset_token for item in results}) == len(results), "responses": [item.response for item in results]}
    if action == "redeem-expired-token":
        result = runtime.request_reset("person@example.com", capabilities, now=0)
        try:
            runtime.redeem_reset(result.reset_token, 15 * 60)
        except TokenRejected as error:
            return {"token": "rejected", "reason": str(error)}
    if action == "redeem-token-twice":
        result = runtime.request_reset("person@example.com", capabilities)
        runtime.redeem_reset(result.reset_token, 1)
        try:
            runtime.redeem_reset(result.reset_token, 2)
        except TokenRejected as error:
            return {"token": "rejected", "reason": str(error)}
    raise ValueError(f"unsupported conformance action: {action}")


def expected_case_result(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["then"]
    return expected