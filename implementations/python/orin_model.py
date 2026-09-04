"""Python reference implementation of the Orin semantic-model slice."""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REFERENCE_FIELDS = {"affects", "constrainedBy", "demonstrates", "requires", "uses", "verifies"}
DECLARATION_KINDS = {
    "value-type", "entity-type", "relation", "state", "capability", "effect",
    "rule", "workflow", "example", "uncertainty", "target", "evidence",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    object_id: str | None = None


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
        return diagnostics

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