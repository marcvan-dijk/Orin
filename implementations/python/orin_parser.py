"""Minimal parser for the provisional Orin module syntax."""

import re
from pathlib import Path
from typing import Any

from orin_model import Diagnostic, SemanticModel


DECLARATION_KINDS = {
    "type": "value-type",
    "entity": "entity-type",
    "relation": "relation",
    "state": "state",
    "capability": "capability",
    "effect": "effect",
    "rule": "rule",
    "workflow": "workflow",
    "example": "example",
    "uncertainty": "uncertainty",
    "evidence": "evidence",
    "target": "target",
}


class OrinParser:
    def parse_file(self, path: str | Path) -> SemanticModel:
        return self.parse(Path(path).read_text(encoding="utf-8"))

    def parse(self, text: str) -> SemanticModel:
        lines = text.splitlines()
        module_match = next((re.match(r"^module\s+([\w.-]+)\s*\{", line.strip()) for line in lines), None)
        if module_match is None:
            raise ValueError("ORIN-P001: module declaration is required")
        module_name = module_match.group(1)
        module_id = f"{module_name}/module"
        module: dict[str, Any] = {
            "id": module_id,
            "kind": "module",
            "name": module_name,
            "status": "accepted",
            "source": {"line": module_match.string.count("\n", 0, module_match.start()) + 1},
        }
        objects: list[dict[str, Any]] = []
        active: dict[str, Any] | None = None
        ignored_depth = 0
        context_depth = 0
        policy_depth = 0
        depth = 0

        for line_number, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            if context_depth:
                if line == "}":
                    context_depth = 0
                    continue
                context_attribute = re.match(r"^(repository|risk)\s+(.+)$", line)
                if context_attribute:
                    key, value = context_attribute.groups()
                    module.setdefault("context", {})[key] = self._string_value(value, line_number)
                    continue
                raise ValueError(f"ORIN-P006: unsupported context attribute at line {line_number}: {line}")
            if policy_depth:
                if line == "}":
                    policy_depth = 0
                    continue
                policy_attribute = re.match(r'^(optimize-for|prefer|require|deploy-to)\s+"([^"]+)"$', line)
                if policy_attribute:
                    key, value = policy_attribute.groups()
                    module.setdefault("implementationPolicies", {})[key] = value
                    continue
                raise ValueError(f"ORIN-P007: unsupported implementation policy at line {line_number}: {line}")
            if ignored_depth:
                ignored_depth += line.count("{") - line.count("}")
                continue
            if line.startswith("module "):
                depth += line.count("{") - line.count("}")
                continue
            if active is not None:
                if line == "}":
                    objects.append(active)
                    active = None
                    depth -= 1
                    continue
                self._read_attribute(active, line)
                continue
            if line.startswith("purpose "):
                module["purpose"] = self._string_value(line, line_number)
                continue
            if line.startswith("import "):
                module.setdefault("imports", []).append(line[7:].strip())
                continue
            declaration = re.match(r"^(type|state|capability)\s+([\w.-]+)\s*$", line)
            if declaration:
                objects.append(self._new_object(module_name, DECLARATION_KINDS[declaration.group(1)], declaration.group(2), line_number))
                continue
            declaration = re.match(r"^(entity|relation|rule|workflow|example|uncertainty|target|effect)\s+([\w.-]+)\s*\{\s*$", line)
            if declaration:
                active = self._new_object(module_name, DECLARATION_KINDS[declaration.group(1)], declaration.group(2), line_number)
                depth += 1
                continue
            declaration = re.match(r"^evidence\s+(\w+)\s+(.+)$", line)
            if declaration:
                evidence = self._new_object(module_name, "evidence", declaration.group(1), line_number)
                evidence["status"] = "blocked" if declaration.group(1) == "blocked" else "accepted"
                evidence["statement"] = self._string_value(declaration.group(2), line_number)
                objects.append(evidence)
                continue
            if line.startswith("context ") and "{" in line:
                context_depth = line.count("{") - line.count("}")
                continue
            if line.startswith("policy implementation") and "{" in line:
                policy_depth = line.count("{") - line.count("}")
                continue
            if line.startswith(("scope ", "risk ")) and "{" in line:
                ignored_depth = line.count("{") - line.count("}")
                continue
            if line.startswith("role "):
                continue
            if line == "}":
                depth -= 1
                continue
            raise ValueError(f"ORIN-P002: unsupported syntax at line {line_number}: {line}")

        if active is not None:
            raise ValueError("ORIN-P003: unterminated declaration block")
        model = SemanticModel({"modelVersion": "0.1.0", "module": module, "objects": objects})
        self._resolve_type_references(model.document)
        return model

    @staticmethod
    def _resolve_type_references(document: dict[str, Any]) -> None:
        objects = document.get("objects", [])
        types: dict[str, str] = {}
        for obj in objects:
            if obj.get("kind") in {"value-type", "entity-type"}:
                types[obj["name"]] = obj["id"]
        for obj in objects:
            if obj.get("kind") != "workflow":
                continue
            for field in ("inputs", "outputs"):
                for value in obj.get(field, []):
                    if isinstance(value, dict) and value.get("type") in types:
                        value["type"] = types[value["type"]]

    @staticmethod
    def _new_object(module_name: str, kind: str, name: str, line_number: int) -> dict[str, Any]:
        return {
            "id": f"{module_name}/{kind}/{name}",
            "kind": kind,
            "name": name,
            "status": "accepted",
            "source": {"line": line_number},
        }

    @staticmethod
    def _string_value(text: str, line_number: int) -> str:
        match = re.search(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text)
        if match is None:
            raise ValueError(f"ORIN-P004: quoted string required at line {line_number}")
        return bytes(match.group(1), "utf-8").decode("unicode_escape")

    def _read_attribute(self, obj: dict[str, Any], line: str) -> None:
        if obj["kind"] == "entity-type" and line.startswith("field "):
            parts = line.split()
            if len(parts) not in {3, 4}:
                raise ValueError(f"ORIN-P008: entity field requires name and type: {line}")
            field = {"name": parts[1], "type": self._reference(obj, parts[2], "value-type")}
            if len(parts) == 4:
                if parts[3] != "identity":
                    raise ValueError(f"ORIN-P009: unsupported entity field modifier: {parts[3]}")
                field["identity"] = True
            obj.setdefault("fields", []).append(field)
            return
        if obj["kind"] == "relation":
            relation = re.match(r"^(from|to)\s+([\w.-]+)$", line)
            if relation:
                obj.setdefault("endpoints", []).append({"type": self._reference(obj, relation.group(2), "entity-type")})
                return
            if line.startswith("cardinality "):
                obj["cardinality"] = line[12:].strip()
                return
        transition = re.match(r"^transition\s+([\w.-]+)\s*->\s*([\w.-]+)$", line)
        if transition:
            obj.setdefault("transitions", []).append({
                "from": self._reference(obj, transition.group(1), "state"),
                "to": self._reference(obj, transition.group(2), "state"),
            })
            return
        typed_value = re.match(r"^(input|output)\s+([\w.-]+)\s+([\w.-]+)$", line)
        if typed_value:
            field, name, value_type = typed_value.groups()
            obj.setdefault(f"{field}s", []).append({"name": name, "type": self._reference(obj, value_type, None)})
            return
        attribute = re.match(r"^(purpose|guarantee|question|authority|outcome|recovery|given|when|then|impact|severity)\s+(.+)$", line)
        if not attribute:
            if line.startswith("budget "):
                return
            if line.startswith("requires "):
                obj.setdefault("requires", []).append(self._reference(obj, line[9:], "capability"))
                return
            if line.startswith("input "):
                obj.setdefault("inputs", []).append(line[6:].strip())
                return
            raise ValueError(f"ORIN-P005: unsupported declaration attribute: {line}")
        key, value = attribute.groups()
        if key in {"guarantee", "question", "outcome", "recovery", "given", "when", "then", "impact"}:
            obj.setdefault("claims", []).append(self._string_value(value, 0))
        elif key == "authority":
            obj[key] = value
        else:
            obj[key] = self._string_value(value, 0)
        if obj["kind"] == "uncertainty":
            obj["status"] = "unresolved"
            obj["consequential"] = True

    @staticmethod
    def _reference(obj: dict[str, Any], attribute_text: str, kind: str | None = "capability") -> str:
        module_name = obj["id"].rsplit("/", 2)[0]
        if attribute_text.strip().startswith(f"{module_name}/"):
            return attribute_text.strip()
        if kind is None:
            return attribute_text.strip()
        return f"{module_name}/{kind}/{attribute_text.strip()}"


def analyze(path: str | Path) -> list[Diagnostic]:
    try:
        return OrinParser().parse_file(path).diagnostics()
    except ValueError as error:
        return [Diagnostic("ORIN-P000", str(error))]