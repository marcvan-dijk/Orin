"""Python reference implementation of the Orin semantic-model slice."""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


REFERENCE_FIELDS = {"affects", "constrainedBy", "demonstrates", "requires", "uses", "verifies"}
DECLARATION_KINDS = {
    "value-type", "entity-type", "relation", "state", "capability", "effect",
    "rule", "workflow", "example", "uncertainty", "target", "evidence",
}
READINESS_DRIVER_KINDS = {"workflow", "rule", "example"}
COMPLETENESS_SCHEMA_VERSION = "0.1.0"
READINESS_CATEGORY_ORDER = {
    "required-decision": 0,
    "optional-default": 1,
    "unresolved-assumption": 2,
    "implementation-preference": 3,
}
READINESS_REQUIRED_FIELDS: dict[str, tuple[dict[str, Any], ...]] = {
    "capability": (
        {
            "code": "ORIN-R001",
            "field": "owner",
            "message": "capability requires issuing authority/owner decision",
            "impactAreas": ("safety",),
        },
        {
            "code": "ORIN-R002",
            "field": "scope",
            "message": "capability requires scope decision",
            "impactAreas": ("safety", "privacy"),
        },
    ),
    "effect": (
        {
            "code": "ORIN-R010",
            "field": "failureModes",
            "message": "effect requires declared failure modes",
            "impactAreas": ("operability",),
        },
        {
            "code": "ORIN-R011",
            "field": "dataAccess",
            "message": "effect requires declared data access boundary",
            "impactAreas": ("privacy", "safety"),
        },
    ),
    "workflow": (
        {
            "code": "ORIN-R020",
            "field": "failureBehavior",
            "message": "workflow requires declared failure behavior",
            "impactAreas": ("operability", "safety"),
        },
        {
            "code": "ORIN-R021",
            "field": "recoveryBehavior",
            "message": "workflow requires declared recovery behavior",
            "impactAreas": ("operability",),
        },
    ),
}
READINESS_OPTIONAL_DEFAULTS: dict[str, tuple[dict[str, Any], ...]] = {
    "relation": (
        {
            "code": "ORIN-R101",
            "field": "deletionBehavior",
            "defaultValue": "retain",
            "message": "relation deletion behavior is unset; default retain is available",
            "impactAreas": ("operability",),
        },
    ),
    "effect": (
        {
            "code": "ORIN-R102",
            "field": "retryPolicy",
            "defaultValue": "none",
            "message": "effect retry policy is unset; default none is available",
            "impactAreas": ("cost", "operability"),
        },
    ),
}
IMPLEMENTATION_PREFERENCE_AREAS = {
    "optimize-for": ("cost", "operability"),
    "prefer": ("cost", "operability"),
    "require": ("operability",),
    "deploy-to": ("operability",),
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    object_id: str | None = None


@dataclass(frozen=True)
class ReadinessDiagnostic:
    code: str
    category: str
    message: str
    severity: str
    blocking: bool
    object_id: str | None = None
    path: str | None = None
    impact_areas: tuple[str, ...] = ()
    affected_object_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
            "blocking": self.blocking,
            "objectId": self.object_id,
            "path": self.path,
            "impactAreas": list(self.impact_areas),
            "affectedObjectPaths": list(self.affected_object_paths),
        }


@dataclass(frozen=True)
class ReadinessReport:
    schema_version: str
    status: str
    validation_status: str
    diagnostics: tuple[ReadinessDiagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        category_counts = {
            "requiredDecisionCount": 0,
            "optionalDefaultCount": 0,
            "unresolvedAssumptionCount": 0,
            "implementationPreferenceCount": 0,
        }
        for diagnostic in self.diagnostics:
            if diagnostic.category == "required-decision":
                category_counts["requiredDecisionCount"] += 1
            elif diagnostic.category == "optional-default":
                category_counts["optionalDefaultCount"] += 1
            elif diagnostic.category == "unresolved-assumption":
                category_counts["unresolvedAssumptionCount"] += 1
            elif diagnostic.category == "implementation-preference":
                category_counts["implementationPreferenceCount"] += 1
        return {
            "schemaVersion": self.schema_version,
            "status": self.status,
            "validationStatus": self.validation_status,
            "summary": {
                "blockingCount": sum(1 for diagnostic in self.diagnostics if diagnostic.blocking),
                "nonBlockingCount": sum(1 for diagnostic in self.diagnostics if not diagnostic.blocking),
                **category_counts,
            },
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


class SemanticModel:
    """A semantic model loaded from the structured interchange format."""

    def __init__(self, document: dict[str, Any]):
        self.document = deepcopy(document)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "SemanticModel":
        with Path(path).open(encoding="utf-8") as model_file:
            document = json.load(model_file)
        if not isinstance(document, dict):
            raise ValueError("semantic model must be a JSON object")
        return cls(document)

    def canonical(self) -> dict[str, Any]:
        canonical = deepcopy(self.document)
        canonical.pop("implementationPolicies", None)
        module = canonical.get("module")
        if isinstance(module, dict):
            module.pop("implementationPolicies", None)
        self._remove_metadata(canonical)
        objects = canonical.get("objects", [])
        for obj in objects:
            for field in REFERENCE_FIELDS:
                if isinstance(obj.get(field), list):
                    obj[field] = sorted(obj[field])
        canonical["objects"] = sorted(objects, key=lambda obj: obj.get("id", ""))
        return canonical

    @staticmethod
    def _remove_metadata(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("source", None)
            value.pop("provenance", None)
            for child in value.values():
                SemanticModel._remove_metadata(child)
        elif isinstance(value, list):
            for child in value:
                SemanticModel._remove_metadata(child)

    def diagnostics(self) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        objects = self.document.get("objects", [])
        if not isinstance(objects, list):
            return [Diagnostic("ORIN-E001", "objects must be a list")]

        identifiers: set[str] = set()
        for obj in objects:
            if not isinstance(obj, dict):
                diagnostics.append(Diagnostic("ORIN-E002", "object must be an object"))
                continue
            object_id = obj.get("id")
            if not isinstance(object_id, str):
                diagnostics.append(Diagnostic("ORIN-E003", "object id must be a string"))
                continue
            if object_id in identifiers:
                diagnostics.append(Diagnostic("ORIN-E004", f"duplicate object identity: {object_id}", object_id))
            identifiers.add(object_id)

        module = self.document.get("module")
        if isinstance(module, dict) and isinstance(module.get("id"), str):
            module_id = module["id"]
            if module_id in identifiers:
                diagnostics.append(Diagnostic("ORIN-E005", f"duplicate module identity: {module_id}", module_id))
            identifiers.add(module_id)

        for obj in objects:
            if not isinstance(obj, dict):
                continue
            source_id = obj.get("id")
            for field in REFERENCE_FIELDS:
                references = obj.get(field, [])
                if not isinstance(references, list):
                    diagnostics.append(Diagnostic("ORIN-E006", f"{field} must be a list", source_id))
                    continue
                for target_id in references:
                    if target_id not in identifiers:
                        diagnostics.append(Diagnostic("ORIN-E007", f"unknown reference: {target_id}", source_id))

        kinds = {obj.get("id"): obj.get("kind") for obj in objects if isinstance(obj, dict)}
        objects_by_id = {obj.get("id"): obj for obj in objects if isinstance(obj, dict)}
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            source_id = obj.get("id")
            kind = obj.get("kind")
            if kind not in DECLARATION_KINDS:
                diagnostics.append(Diagnostic("ORIN-E008", f"unsupported declaration kind: {kind}", source_id))
            if kind == "entity-type":
                self._validate_entity(obj, kinds, diagnostics)
            elif kind == "relation":
                self._validate_relation(obj, kinds, diagnostics)
            elif kind == "effect":
                self._validate_effect(obj, kinds, diagnostics)
            elif kind == "rule":
                self._validate_rule(obj, diagnostics)
            elif kind == "workflow":
                self._validate_workflow(obj, kinds, objects_by_id, diagnostics)

        for obj in objects:
            if (
                isinstance(obj, dict)
                and obj.get("kind") == "uncertainty"
                and obj.get("consequential") is True
                and obj.get("status") == "unresolved"
            ):
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E041",
                        f"unresolved consequential uncertainty: {obj.get('name', obj.get('id'))}",
                        obj.get("id"),
                    )
                )
        readiness_references = self._collect_readiness_references(objects, kinds, objects_by_id)
        state_references = self._collect_readiness_state_references(objects)
        capability_readiness_enabled = self._capability_readiness_enabled(objects, kinds)
        relation_readiness_enabled = self._relation_readiness_enabled(objects, kinds)
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") != "effect":
                continue
            object_id = obj.get("id")
            if isinstance(object_id, str) and object_id not in readiness_references:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E042",
                        "effect declaration is not referenced by any workflow/rule/example",
                        object_id,
                    )
                )
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") != "capability":
                continue
            object_id = obj.get("id")
            if capability_readiness_enabled and isinstance(object_id, str) and object_id not in readiness_references:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E043",
                        "capability declaration is not referenced by any workflow/rule/example",
                        object_id,
                    )
                )
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") != "relation":
                continue
            object_id = obj.get("id")
            if relation_readiness_enabled and isinstance(object_id, str) and object_id not in readiness_references:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E045",
                        "relation declaration is not referenced by any workflow/rule/example",
                        object_id,
                    )
                )
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") != "state":
                continue
            object_id = obj.get("id")
            if state_references and isinstance(object_id, str) and object_id not in state_references:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E044",
                        "state declaration is not referenced by any workflow transition",
                        object_id,
                    )
                )
        return diagnostics

    def readiness_report(self) -> ReadinessReport:
        objects = self.document.get("objects", [])
        if not isinstance(objects, list):
            diagnostics = (
                ReadinessDiagnostic(
                    code="ORIN-R900",
                    category="required-decision",
                    message="semantic model structure is invalid; fix validation errors before readiness analysis",
                    severity="blocked",
                    blocking=True,
                    path="/objects",
                ),
            )
            return ReadinessReport(
                schema_version=COMPLETENESS_SCHEMA_VERSION,
                status="fail",
                validation_status="fail",
                diagnostics=diagnostics,
            )

        reverse_references = self._build_reverse_reference_graph(objects)
        readiness_diagnostics: list[ReadinessDiagnostic] = []
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            readiness_diagnostics.extend(
                self._collect_required_field_readiness(obj, reverse_references)
            )
            readiness_diagnostics.extend(
                self._collect_optional_default_readiness(obj, reverse_references)
            )
            if obj.get("kind") == "uncertainty" and obj.get("status") == "unresolved":
                readiness_diagnostics.append(
                    self._collect_uncertainty_readiness(obj, reverse_references)
                )

        readiness_diagnostics.extend(
            self._collect_implementation_preference_readiness()
        )
        ordered = tuple(sorted(
            readiness_diagnostics,
            key=lambda diagnostic: (
                READINESS_CATEGORY_ORDER.get(diagnostic.category, 99),
                diagnostic.code,
                diagnostic.path or "",
                diagnostic.object_id or "",
                diagnostic.message,
            ),
        ))
        validation_status = self.compilation_status()
        if validation_status == "fail":
            status = "fail"
        elif validation_status == "blocked" or any(diagnostic.blocking for diagnostic in ordered):
            status = "blocked"
        else:
            status = "eligible"
        return ReadinessReport(
            schema_version=COMPLETENESS_SCHEMA_VERSION,
            status=status,
            validation_status=validation_status,
            diagnostics=ordered,
        )

    @staticmethod
    def _collect_readiness_references(
        objects: list[Any],
        kinds: dict[str, str],
        objects_by_id: dict[str, dict[str, Any]],
    ) -> set[str]:
        references: set[str] = set()
        readiness_effects: set[str] = set()
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") not in READINESS_DRIVER_KINDS:
                continue
            for field in REFERENCE_FIELDS:
                values = obj.get(field, [])
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str):
                            references.add(value)
                            if kinds.get(value) == "effect":
                                readiness_effects.add(value)
            if obj.get("kind") == "workflow":
                transitions = obj.get("transitions", [])
                if isinstance(transitions, list):
                    for transition in transitions:
                        if not isinstance(transition, dict):
                            continue
                        from_state = transition.get("from")
                        to_state = transition.get("to")
                        if isinstance(from_state, str):
                            references.add(from_state)
                        if isinstance(to_state, str):
                            references.add(to_state)
                actor_capabilities = obj.get("actorCapabilities", [])
                if isinstance(actor_capabilities, list):
                    for binding in actor_capabilities:
                        if isinstance(binding, dict) and isinstance(binding.get("capability"), str):
                            references.add(binding["capability"])
        for effect_id in readiness_effects:
            effect = objects_by_id.get(effect_id, {})
            if isinstance(effect, dict):
                required_capabilities = effect.get("requires", [])
                if isinstance(required_capabilities, list):
                    for capability_id in required_capabilities:
                        if isinstance(capability_id, str):
                            references.add(capability_id)
        return references

    @staticmethod
    def _capability_readiness_enabled(objects: list[Any], kinds: dict[str, str]) -> bool:
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") not in READINESS_DRIVER_KINDS:
                continue
            if obj.get("kind") == "workflow" and "actorCapabilities" in obj:
                return True
            uses = obj.get("uses", [])
            if isinstance(uses, list) and any(isinstance(value, str) and kinds.get(value) == "effect" for value in uses):
                return True
        return False

    @staticmethod
    def _collect_readiness_state_references(objects: list[Any]) -> set[str]:
        references: set[str] = set()
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") != "workflow":
                continue
            transitions = obj.get("transitions", [])
            if not isinstance(transitions, list):
                continue
            for transition in transitions:
                if not isinstance(transition, dict):
                    continue
                from_state = transition.get("from")
                to_state = transition.get("to")
                if isinstance(from_state, str):
                    references.add(from_state)
                if isinstance(to_state, str):
                    references.add(to_state)
        return references

    @staticmethod
    def _relation_readiness_enabled(objects: list[Any], kinds: dict[str, str]) -> bool:
        for obj in objects:
            if not isinstance(obj, dict) or obj.get("kind") not in READINESS_DRIVER_KINDS:
                continue
            for field in REFERENCE_FIELDS:
                values = obj.get(field, [])
                if isinstance(values, list) and any(
                    isinstance(value, str) and kinds.get(value) == "relation"
                    for value in values
                ):
                    return True
        return False

    @staticmethod
    def _validate_entity(obj: dict[str, Any], kinds: dict[str, str], diagnostics: list[Diagnostic]) -> None:
        fields = obj.get("fields")
        if not isinstance(fields, list) or not fields:
            diagnostics.append(Diagnostic("ORIN-E020", "entity-type requires fields", obj.get("id")))
            return
        identities = [field for field in fields if isinstance(field, dict) and field.get("identity") is True]
        if len(identities) != 1:
            diagnostics.append(Diagnostic("ORIN-E021", "entity-type requires exactly one identity field", obj.get("id")))
        names: set[str] = set()
        for field in fields:
            if not isinstance(field, dict) or not isinstance(field.get("name"), str):
                diagnostics.append(Diagnostic("ORIN-E022", "entity field requires a name", obj.get("id")))
                continue
            if field["name"] in names:
                diagnostics.append(Diagnostic("ORIN-E023", f"duplicate entity field: {field['name']}", obj.get("id")))
            names.add(field["name"])
            field_type = field.get("type")
            if kinds.get(field_type) != "value-type":
                diagnostics.append(Diagnostic("ORIN-E024", f"entity field type must reference a value-type: {field_type}", obj.get("id")))

    @staticmethod
    def _validate_relation(obj: dict[str, Any], kinds: dict[str, str], diagnostics: list[Diagnostic]) -> None:
        endpoints = obj.get("endpoints")
        if not isinstance(endpoints, list) or len(endpoints) != 2:
            diagnostics.append(Diagnostic("ORIN-E025", "relation requires exactly two endpoints", obj.get("id")))
        else:
            for endpoint in endpoints:
                if kinds.get(endpoint.get("type")) != "entity-type":
                    diagnostics.append(Diagnostic("ORIN-E026", "relation endpoint must reference an entity-type", obj.get("id")))
        if obj.get("cardinality") not in {"one-to-one", "one-to-many", "many-to-one", "many-to-many"}:
            diagnostics.append(Diagnostic("ORIN-E027", f"invalid relation cardinality: {obj.get('cardinality')}", obj.get("id")))

    @staticmethod
    def _validate_effect(obj: dict[str, Any], kinds: dict[str, str], diagnostics: list[Diagnostic]) -> None:
        for capability in obj.get("requires", []):
            if kinds.get(capability) != "capability":
                diagnostics.append(Diagnostic("ORIN-E035", f"effect capability must reference a capability: {capability}", obj.get("id")))
        effect_name = obj.get("name", "")
        if isinstance(effect_name, str) and effect_name.startswith("persistent-entity-store."):
            durability = obj.get("durability")
            if durability is None:
                diagnostics.append(Diagnostic("ORIN-E039", "persistence effect requires durability contract", obj.get("id")))
            elif durability not in {"strong", "eventual"}:
                diagnostics.append(Diagnostic("ORIN-E040", f"invalid durability contract: {durability}", obj.get("id")))

    @staticmethod
    def _normalize_claim_text(text: str) -> str:
        normalized = " ".join(text.strip().split())
        normalized = re.sub(r"[.,;:!?]+$", "", normalized)
        return " ".join(normalized.strip().split())

    @staticmethod
    def _claim_signature(claim: Any) -> tuple[str, bool] | None:
        negated = False
        text: str | None = None
        if isinstance(claim, str):
            text = claim
        elif isinstance(claim, dict) and isinstance(claim.get("text"), str):
            text = claim["text"]
            negated = claim.get("negated") is True
        if text is None:
            return None
        normalized = SemanticModel._normalize_claim_text(text)
        lower = normalized.lower()
        if lower.startswith("not "):
            normalized = SemanticModel._normalize_claim_text(normalized[4:])
            negated = True
        if not normalized:
            return None
        return normalized.lower(), negated

    @staticmethod
    def _validate_rule(obj: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
        claims = obj.get("claims", [])
        if not isinstance(claims, list):
            return
        polarities_by_claim: dict[str, set[bool]] = {}
        for claim in claims:
            signature = SemanticModel._claim_signature(claim)
            if signature is None:
                continue
            claim_text, negated = signature
            polarities_by_claim.setdefault(claim_text, set()).add(negated)
        contradictory = sorted(
            claim_text for claim_text, polarities in polarities_by_claim.items() if len(polarities) > 1
        )
        for claim_text in contradictory:
            diagnostics.append(
                Diagnostic(
                    "ORIN-E046",
                    f"rule contains contradictory claims: {claim_text}",
                    obj.get("id"),
                )
            )

    @staticmethod
    def _validate_workflow(
        obj: dict[str, Any],
        kinds: dict[str, str],
        objects_by_id: dict[str, dict[str, Any]],
        diagnostics: list[Diagnostic],
    ) -> None:
        for field_name in ("inputs", "outputs"):
            values = obj.get(field_name)
            if values is None:
                continue
            if not isinstance(values, list):
                diagnostics.append(Diagnostic("ORIN-E028", f"workflow {field_name} must be a list", obj.get("id")))
                continue
            for value in values:
                if isinstance(value, str):
                    continue
                if not isinstance(value, dict) or not isinstance(value.get("name"), str):
                    diagnostics.append(Diagnostic("ORIN-E029", f"workflow {field_name} require named values", obj.get("id")))
                elif kinds.get(value.get("type")) not in {"value-type", "entity-type"}:
                    diagnostics.append(Diagnostic("ORIN-E030", f"workflow value type must reference a value/entity type: {value.get('type')}", obj.get("id")))
        transitions = obj.get("transitions", [])
        if not isinstance(transitions, list):
            diagnostics.append(Diagnostic("ORIN-E031", "workflow transitions must be a list", obj.get("id")))
        for transition in transitions:
            if not isinstance(transition, dict) or transition.get("from") == transition.get("to"):
                diagnostics.append(Diagnostic("ORIN-E032", "state transition requires distinct from and to states", obj.get("id")))
            elif not transition.get("from") or not transition.get("to"):
                diagnostics.append(Diagnostic("ORIN-E033", "state transition requires from and to", obj.get("id")))
            elif kinds.get(transition["from"]) != "state" or kinds.get(transition["to"]) != "state":
                diagnostics.append(Diagnostic("ORIN-E034", "state transition endpoints must reference states", obj.get("id")))
        for capability in obj.get("requires", []):
            if kinds.get(capability) != "capability":
                diagnostics.append(Diagnostic("ORIN-E035", f"workflow capability must reference a capability: {capability}", obj.get("id")))
        used_effects: list[str] = []
        for effect in obj.get("uses", []):
            if kinds.get(effect) != "effect":
                diagnostics.append(Diagnostic("ORIN-E036", f"workflow uses must reference an effect: {effect}", obj.get("id")))
            else:
                used_effects.append(effect)
        required_capabilities = set(obj.get("requires", []))
        for effect in used_effects:
            effect_obj = objects_by_id.get(effect, {})
            if isinstance(effect_obj, dict):
                for capability in effect_obj.get("requires", []):
                    required_capabilities.add(capability)
        actor = obj.get("actor")
        has_actor_capabilities = "actorCapabilities" in obj
        raw_bindings = obj.get("actorCapabilities", [])
        if not isinstance(raw_bindings, list):
            diagnostics.append(Diagnostic("ORIN-E038", "workflow actorCapabilities must be a list", obj.get("id")))
            bindings: list[Any] = []
        else:
            bindings = raw_bindings
        valid_bindings: list[dict[str, str]] = []
        for binding in bindings:
            if not isinstance(binding, dict):
                diagnostics.append(Diagnostic("ORIN-E038", "workflow actorCapabilities entries must be objects", obj.get("id")))
                continue
            actor_name = binding.get("actor")
            capability_name = binding.get("capability")
            if not isinstance(actor_name, str) or not isinstance(capability_name, str):
                diagnostics.append(Diagnostic("ORIN-E038", "workflow actorCapabilities entries require actor and capability strings", obj.get("id")))
                continue
            if kinds.get(capability_name) != "capability":
                diagnostics.append(Diagnostic("ORIN-E035", f"workflow actor capability must reference a capability: {capability_name}", obj.get("id")))
                continue
            valid_bindings.append({"actor": actor_name, "capability": capability_name})
        if actor is None:
            if has_actor_capabilities:
                diagnostics.append(Diagnostic("ORIN-E038", "workflow actorCapabilities require actor declaration", obj.get("id")))
        elif not isinstance(actor, str):
            diagnostics.append(Diagnostic("ORIN-E038", "workflow actor must be a string input name", obj.get("id")))
            if required_capabilities and not has_actor_capabilities:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E038",
                        "workflow actor requires actorCapabilities contract for required capabilities/effects",
                        obj.get("id"),
                    )
                )
        else:
            if required_capabilities and not has_actor_capabilities:
                diagnostics.append(
                    Diagnostic(
                        "ORIN-E038",
                        "workflow actor requires actorCapabilities contract for required capabilities/effects",
                        obj.get("id"),
                    )
                )
            inputs = obj.get("inputs", [])
            actor_inputs = [value for value in inputs if isinstance(value, dict) and value.get("name") == actor]
            actor_input_valid = True
            if not actor_inputs:
                diagnostics.append(Diagnostic("ORIN-E038", f"workflow actor must reference a declared input: {actor}", obj.get("id")))
                actor_input_valid = False
            elif kinds.get(actor_inputs[0].get("type")) != "entity-type":
                diagnostics.append(Diagnostic("ORIN-E038", f"workflow actor input must reference an entity-type: {actor}", obj.get("id")))
                actor_input_valid = False
            if actor_input_valid:
                actor_bindings: list[dict[str, str]] = []
                for binding in valid_bindings:
                    if binding["actor"] != actor:
                        diagnostics.append(
                            Diagnostic(
                                "ORIN-E038",
                                f"workflow actorCapabilities actor must match workflow actor: {binding['actor']}",
                                obj.get("id"),
                            )
                        )
                        continue
                    actor_bindings.append(binding)
                if has_actor_capabilities:
                    bound_capabilities = {
                        binding["capability"]
                        for binding in actor_bindings
                    }
                    missing = sorted(capability for capability in required_capabilities if capability not in bound_capabilities)
                    if missing:
                        diagnostics.append(
                            Diagnostic(
                                "ORIN-E037",
                                f"workflow actor is not bound to required capabilities: {', '.join(missing)}",
                                obj.get("id"),
                            )
                        )

    def compilation_status(self) -> str:
        diagnostics = self.diagnostics()
        if any(diagnostic.code == "ORIN-E041" for diagnostic in diagnostics):
            return "blocked"
        return "fail" if diagnostics else "eligible"

    @staticmethod
    def _has_declared_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return bool(value)
        return True

    @staticmethod
    def _escape_pointer_segment(segment: str) -> str:
        return segment.replace("~", "~0").replace("/", "~1")

    @classmethod
    def _object_path(cls, object_id: str, *segments: str) -> str:
        path = f"/objects/{cls._escape_pointer_segment(object_id)}"
        for segment in segments:
            path += f"/{cls._escape_pointer_segment(segment)}"
        return path

    @classmethod
    def _module_path(cls, *segments: str) -> str:
        path = "/module"
        for segment in segments:
            path += f"/{cls._escape_pointer_segment(segment)}"
        return path

    @staticmethod
    def _impact_areas(value: Any, fallback: tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(value, list):
            normalized = sorted(
                {
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip()
                }
            )
            if normalized:
                return tuple(normalized)
        return fallback

    @classmethod
    def _build_reverse_reference_graph(cls, objects: list[Any]) -> dict[str, set[str]]:
        reverse_references: dict[str, set[str]] = {}
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            source_id = obj.get("id")
            if not isinstance(source_id, str):
                continue
            for field in REFERENCE_FIELDS:
                values = obj.get(field, [])
                if isinstance(values, list):
                    for target_id in values:
                        if isinstance(target_id, str):
                            reverse_references.setdefault(target_id, set()).add(source_id)
            if obj.get("kind") == "workflow":
                transitions = obj.get("transitions", [])
                if isinstance(transitions, list):
                    for transition in transitions:
                        if not isinstance(transition, dict):
                            continue
                        for state_name in ("from", "to"):
                            state_id = transition.get(state_name)
                            if isinstance(state_id, str):
                                reverse_references.setdefault(state_id, set()).add(source_id)
                actor_capabilities = obj.get("actorCapabilities", [])
                if isinstance(actor_capabilities, list):
                    for binding in actor_capabilities:
                        capability_id = binding.get("capability") if isinstance(binding, dict) else None
                        if isinstance(capability_id, str):
                            reverse_references.setdefault(capability_id, set()).add(source_id)
        return reverse_references

    @classmethod
    def _collect_affected_object_paths(
        cls,
        seed_ids: set[str],
        reverse_references: dict[str, set[str]],
    ) -> tuple[str, ...]:
        ordered_paths: list[str] = []
        seen: set[str] = set()
        queue = sorted(seed_ids)
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            ordered_paths.append(cls._object_path(current))
            for dependent_id in sorted(reverse_references.get(current, set())):
                if dependent_id not in seen:
                    queue.append(dependent_id)
        return tuple(ordered_paths)

    @classmethod
    def _collect_required_field_readiness(
        cls,
        obj: dict[str, Any],
        reverse_references: dict[str, set[str]],
    ) -> list[ReadinessDiagnostic]:
        diagnostics: list[ReadinessDiagnostic] = []
        object_id = obj.get("id")
        kind = obj.get("kind")
        if not isinstance(object_id, str) or not isinstance(kind, str):
            return diagnostics
        for rule in READINESS_REQUIRED_FIELDS.get(kind, ()):
            if cls._has_declared_value(obj.get(rule["field"])):
                continue
            diagnostics.append(
                ReadinessDiagnostic(
                    code=rule["code"],
                    category="required-decision",
                    message=rule["message"],
                    severity="blocked",
                    blocking=True,
                    object_id=object_id,
                    path=cls._object_path(object_id, rule["field"]),
                    impact_areas=cls._impact_areas(obj.get("impactAreas"), rule["impactAreas"]),
                    affected_object_paths=cls._collect_affected_object_paths({object_id}, reverse_references),
                )
            )
        return diagnostics

    @classmethod
    def _collect_optional_default_readiness(
        cls,
        obj: dict[str, Any],
        reverse_references: dict[str, set[str]],
    ) -> list[ReadinessDiagnostic]:
        diagnostics: list[ReadinessDiagnostic] = []
        object_id = obj.get("id")
        kind = obj.get("kind")
        if not isinstance(object_id, str) or not isinstance(kind, str):
            return diagnostics
        for rule in READINESS_OPTIONAL_DEFAULTS.get(kind, ()):
            if cls._has_declared_value(obj.get(rule["field"])):
                continue
            diagnostics.append(
                ReadinessDiagnostic(
                    code=rule["code"],
                    category="optional-default",
                    message=f"{rule['message']} ({rule['field']}={rule['defaultValue']})",
                    severity="info",
                    blocking=False,
                    object_id=object_id,
                    path=cls._object_path(object_id, rule["field"]),
                    impact_areas=rule["impactAreas"],
                    affected_object_paths=cls._collect_affected_object_paths({object_id}, reverse_references),
                )
            )
        return diagnostics

    @classmethod
    def _collect_uncertainty_readiness(
        cls,
        obj: dict[str, Any],
        reverse_references: dict[str, set[str]],
    ) -> ReadinessDiagnostic:
        object_id = obj.get("id")
        if not isinstance(object_id, str):
            object_id = None
        impact_areas = cls._impact_areas(
            obj.get("impactAreas"),
            ("cost", "operability") if obj.get("consequential") is not True else ("cost", "operability", "privacy", "safety"),
        )
        affected_ids = set()
        for target_id in obj.get("affects", []):
            if isinstance(target_id, str):
                affected_ids.add(target_id)
        if object_id is not None:
            affected_ids.add(object_id)
        question = obj.get("question") or obj.get("name") or object_id or "unresolved assumption"
        blocking = obj.get("status") == "unresolved" and obj.get("consequential") is True
        severity = "blocked" if blocking else "warning"
        if obj.get("status") != "unresolved":
            severity = "info"
        return ReadinessDiagnostic(
            code="ORIN-R201",
            category="unresolved-assumption",
            message=f"uncertainty remains unresolved: {question}",
            severity=severity,
            blocking=blocking,
            object_id=object_id,
            path=cls._object_path(object_id) if object_id is not None else None,
            impact_areas=impact_areas,
            affected_object_paths=cls._collect_affected_object_paths(affected_ids, reverse_references),
        )

    def _collect_implementation_preference_readiness(self) -> list[ReadinessDiagnostic]:
        diagnostics: list[ReadinessDiagnostic] = []
        for key, value in sorted(self._get_module_implementation_policies().items()):
            diagnostics.append(
                ReadinessDiagnostic(
                    code="ORIN-R301",
                    category="implementation-preference",
                    message=f"implementation preference selected: {key}={value}",
                    severity="info",
                    blocking=False,
                    path=self._module_path("implementationPolicies", key),
                    impact_areas=IMPLEMENTATION_PREFERENCE_AREAS.get(key, ("operability",)),
                    affected_object_paths=("/module",),
                )
            )
        for key, value in sorted(self._get_root_implementation_policies().items()):
            diagnostics.append(
                ReadinessDiagnostic(
                    code="ORIN-R301",
                    category="implementation-preference",
                    message=f"implementation preference selected: {key}={value}",
                    severity="info",
                    blocking=False,
                    path=f"/implementationPolicies/{self._escape_pointer_segment(key)}",
                    impact_areas=IMPLEMENTATION_PREFERENCE_AREAS.get(key, ("operability",)),
                    affected_object_paths=("/implementationPolicies",),
                )
            )
        return diagnostics

    def _get_module_implementation_policies(self) -> dict[str, Any]:
        module = self.document.get("module")
        policies = module.get("implementationPolicies", {}) if isinstance(module, dict) else {}
        return dict(policies) if isinstance(policies, dict) else {}

    def _get_root_implementation_policies(self) -> dict[str, Any]:
        policies = self.document.get("implementationPolicies", {})
        return dict(policies) if isinstance(policies, dict) else {}