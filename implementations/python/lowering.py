"""Reference lowering choices driven by non-semantic implementation policies."""

from typing import Any

from orin_model import SemanticModel


def lower(model: SemanticModel) -> dict[str, Any]:
    module = model.document.get("module", {})
    policies = module.get("implementationPolicies", model.document.get("implementationPolicies", {}))
    return {
        "behavior": model.canonical(),
        "artifact": {
            "latency": policies.get("optimize-for") == "low-latency",
            "managedServices": policies.get("prefer") == "managed-services",
            "persistence": policies.get("require", "relational-persistence"),
            "deployment": policies.get("deploy-to", "portable-infrastructure"),
        },
    }