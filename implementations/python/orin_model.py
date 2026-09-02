"""Python reference implementation of the Orin semantic-model slice."""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


REFERENCE_FIELDS = {"affects", "constrainedBy", "demonstrates", "requires", "uses", "verifies"}


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

    def compilation_status(self) -> str:
        diagnostics = self.diagnostics()
        if any(diagnostic.code == "ORIN-E041" for diagnostic in diagnostics):
            return "blocked"
        return "fail" if diagnostics else "eligible"