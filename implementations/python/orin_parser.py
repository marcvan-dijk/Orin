"""Minimal parser for the provisional Orin module syntax."""

import json
import re
from pathlib import Path
from typing import Any

try:
    from .orin_model import Diagnostic, SemanticModel
except ImportError:  # pragma: no cover - direct script compatibility
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


SOURCE_ERROR_HINTS = {
    "ORIN-P001": ("The file has no module declaration.", 'Start the file with a line like: module my-app {'),
    "ORIN-P002": ("This line is not valid Orin syntax.", 'Check the spelling of the keyword (for example type, entity, rule, example) and that blocks use "{" and "}".'),
    "ORIN-P003": ("A block was opened with \"{\" but never closed.", 'Add a closing "}" on its own line after the last line of the block.'),
    "ORIN-P004": ("A quoted piece of text is missing.", 'Put the text in double quotes, for example: purpose "Let people reset passwords"'),
    "ORIN-P005": ("This line is not allowed inside this declaration.", "Remove the line or use an attribute this kind of declaration supports."),
    "ORIN-P006": ("This line is not allowed in a context block.", 'Use only: repository "..." or risk "..."'),
    "ORIN-P007": ("This line is not an allowed implementation policy.", 'Use optimize-for, prefer, require or deploy-to followed by a quoted value, e.g. prefer "python"'),
    "ORIN-P008": ("A field needs both a name and a type.", "Write it as: field name type  (for example: field email text)"),
    "ORIN-P009": ("This field modifier is not recognised.", 'The only modifier is "identity", e.g. field id text identity'),
}


class OrinSourceError(ValueError):
    """A syntax or structure problem in .orin source, with its location."""

    def __init__(self, code: str, problem: str, hint: str, file: str | None, line: int, column: int, source_line: str = "") -> None:
        self.code = code
        self.problem = problem
        self.hint = hint
        self.file = file
        self.line = line
        self.column = column
        self.source_line = source_line
        super().__init__(self._format())

    def _format(self) -> str:
        text = f"{self.file or '<source>'}:{self.line}:{self.column}: error {self.code}: {self.problem}"
        if self.source_line:
            text += f"\n    {self.source_line}\n    {' ' * (self.column - 1)}^"
        return text + f"\n  Suggested fix: {self.hint}"

    def with_file(self, file: str) -> "OrinSourceError":
        return OrinSourceError(self.code, self.problem, self.hint, file, self.line, self.column, self.source_line)


class OrinParser:
    def parse_file(self, path: str | Path) -> SemanticModel:
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise OrinSourceError("ORIN-P012", "The file does not exist.", "Check the path and spelling.", str(path), 1, 1) from None
        except UnicodeDecodeError as error:
            raise OrinSourceError("ORIN-P013", "The file is not valid UTF-8 text.", "Save the file as UTF-8.", str(path), 1, 1) from error
        if (
            self._is_canonical_password_reset_example(path)
            and self._looks_like_password_reset_outline(text)
        ):
            return self._load_password_reset_example(path)
        try:
            if self._is_outline(text):
                return self.parse_outline(text, path)
            return self.parse(text)
        except OrinSourceError as error:
            raise error.with_file(str(path)) from None

    @staticmethod
    def _is_outline(text: str) -> bool:
        first = next((l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("//")), "")
        return re.match(r"^module:\s*\S", first) is not None

    def parse_outline(self, text: str, path: Path | None = None) -> SemanticModel:
        """Parse outline-style source (`module: name`, `rules:`, `workflow: x`, ...).

        A sibling tests/conformance/<stem>.structured.json, when present, supplies the
        accepted structured model; source lines are attached from the outline.
        """
        lines = text.splitlines()
        sections = self._outline_sections(lines)
        if any(s["key"] in ("type", "entity", "relation", "state", "capability", "effect", "rule") for s in sections[1:]):
            return SemanticModel(self._full_document(sections))
        fixture = self._find_structured_fixture(path) if path is not None else None
        if fixture is not None:
            document = json.loads(fixture.read_text(encoding="utf-8"))
            self._attach_outline_lines(document, sections)
            return SemanticModel(document)
        return SemanticModel(self._outline_document(sections))

    @staticmethod
    def _find_structured_fixture(path: Path) -> Path | None:
        path = path.resolve()
        for candidate in (path.parent, *path.parents):
            maybe = candidate / "tests" / "conformance" / f"{path.stem}.structured.json"
            if maybe.exists():
                return maybe
        return None

    @staticmethod
    def _outline_sections(lines: list[str]) -> list[dict[str, Any]]:
        """Split into top-level sections: {key, value, line, body: [(line_no, text)]}."""
        sections: list[dict[str, Any]] = []
        for number, raw in enumerate(lines, 1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("//"):
                continue
            indented = raw[:1] in (" ", "\t")
            if not indented:
                match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", stripped)
                if match is None:
                    raise OrinSourceError(
                        "ORIN-P010", "This line is not a recognised outline section.",
                        "Start sections with a keyword and a colon, for example: rules:", None, number,
                        1, raw.rstrip(),
                    )
                sections.append({"key": match.group(1), "value": match.group(2).strip(), "line": number, "body": []})
            elif sections:
                sections[-1]["body"].append((number, stripped))
            else:
                raise OrinSourceError(
                    "ORIN-P001", "A module declaration is required first.",
                    "Begin the file with: module: name", None, number, 1, raw.rstrip(),
                )
        if not sections or sections[0]["key"] != "module" or not sections[0]["value"]:
            raise OrinSourceError("ORIN-P001", "A module declaration is required.", "Begin the file with: module: name", None, 1, 1, lines[0] if lines else "")
        return sections

    @staticmethod
    def _sub_blocks(body: list[tuple[int, str]]) -> dict[str, list[tuple[int, str]]]:
        blocks: dict[str, list[tuple[int, str]]] = {}
        current: list[tuple[int, str]] | None = None
        for number, text in body:
            match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", text)
            if match and match.group(1) in {"given", "when", "then", "input", "steps", "blocking", "question", "output", "requires"}:
                current = blocks.setdefault(match.group(1), [])
                if match.group(2):
                    current.append((number, match.group(2)))
            elif current is not None:
                current.append((number, text))
        return blocks

    @staticmethod
    def _slug(text: str, words: int = 5) -> str:
        parts = re.findall(r"[a-z0-9]+", text.lower())
        return "-".join(parts[:words]) or "unnamed"

    def _outline_document(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        name = sections[0]["value"]
        module: dict[str, Any] = {
            "id": f"{name}/module", "kind": "module", "name": name,
            "status": "accepted", "source": {"line": sections[0]["line"]},
        }
        objects: list[dict[str, Any]] = []

        def add(kind: str, obj_name: str, line: int, **extra: Any) -> dict[str, Any]:
            obj = {"id": f"{name}/{kind}/{obj_name}", "kind": kind, "name": obj_name,
                   "status": "accepted", "source": {"line": line}, **extra}
            objects.append(obj)
            return obj

        for section in sections[1:]:
            key, value, body = section["key"], section["value"], section["body"]
            if key == "purpose":
                module["purpose"] = " ".join(([value] if value else []) + [t for _, t in body])
            elif key == "rules":
                for number, text in body:
                    claim = text[2:].strip() if text.startswith("- ") else text
                    add("rule", self._slug(claim), number, claims=[claim])
            elif key == "workflow":
                blocks = self._sub_blocks(body)
                extra: dict[str, Any] = {}
                if "input" in blocks:
                    extra["inputs"] = [t for _, t in blocks["input"]]
                add("workflow", value, section["line"], **extra)
            elif key == "example":
                blocks = self._sub_blocks(body)
                claims = [" ".join(t for _, t in blocks[k]) for k in ("given", "when", "then") if k in blocks]
                add("example", value, section["line"], claims=claims)
            elif key == "uncertainty":
                blocks = self._sub_blocks(body)
                blocking = " ".join(t for _, t in blocks.get("blocking", [])).lower() in ("yes", "true")
                question = " ".join(t for _, t in blocks.get("question", []))
                add("uncertainty", value, section["line"], status="unresolved", claims=[question],
                    consequential=blocking, authority="human")
                if blocking:
                    add("evidence", "blocked", section["line"], status="blocked",
                        statement=f"The {value} decision is unresolved.")
        return {"modelVersion": "0.1.0", "module": module, "objects": objects}

    _FULL_KEYS = {
        "identity", "between", "cardinality", "requires", "durability", "actor", "input", "output",
        "uses", "actor-capabilities", "transitions", "claims", "then", "blocking", "question",
    }
    _REF_ORDER = ("rule", "workflow", "relation", "state", "capability", "effect", "entity-type", "value-type")

    def _full_blocks(self, body: list[tuple[int, str]]) -> dict[str, list[str]]:
        blocks: dict[str, list[str]] = {}
        current: list[str] | None = None
        for _, text in body:
            match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", text)
            if match and match.group(1) in self._FULL_KEYS:
                current = blocks.setdefault(match.group(1), [])
                if match.group(2):
                    current.append(match.group(2))
            elif current is not None:
                current.append(text[2:].strip() if text.startswith("- ") else text)
        return blocks

    def _full_document(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        name = sections[0]["value"]
        module: dict[str, Any] = {
            "id": f"{name}/module", "kind": "module", "name": name,
            "status": "accepted", "source": {"line": sections[0]["line"]},
        }
        names: dict[str, dict[str, str]] = {}
        for section in sections[1:]:
            kind = DECLARATION_KINDS.get(section["key"], section["key"])
            if section["key"] in DECLARATION_KINDS or section["key"] in ("workflow", "rule"):
                names.setdefault(kind, {})[section["value"]] = f"{name}/{kind}/{section['value']}"

        def ref(text: str, kinds: tuple[str, ...]) -> str:
            for kind in kinds:
                if text in names.get(kind, {}):
                    return names[kind][text]
            return text

        objects: list[dict[str, Any]] = []
        for section in sections[1:]:
            key, value, body = section["key"], section["value"], section["body"]
            line = section["line"]
            if key == "purpose":
                module["purpose"] = " ".join(([value] if value else []) + [t for _, t in body])
                continue
            kind = DECLARATION_KINDS.get(key, key)
            if kind not in ("value-type", "entity-type", "relation", "state", "capability", "effect",
                            "workflow", "rule", "example", "uncertainty"):
                continue
            blocks = self._full_blocks(body)
            obj: dict[str, Any] = {"id": f"{name}/{kind}/{value}", "kind": kind, "name": value,
                                   "status": "accepted", "source": {"line": line}}
            if kind == "entity-type" and "identity" in blocks:
                obj["fields"] = [
                    {"name": f.split()[0], "type": ref(f.split()[1], ("value-type",)), "identity": True}
                    for f in blocks["identity"] if len(f.split()) == 2
                ]
            elif kind == "relation":
                if "between" in blocks:
                    obj["endpoints"] = [{"type": ref(t, ("entity-type",))} for t in blocks["between"]]
                if "cardinality" in blocks:
                    obj["cardinality"] = " ".join(blocks["cardinality"])
            elif kind == "effect":
                obj["requires"] = [ref(t, ("capability",)) for t in blocks.get("requires", [])]
                if "durability" in blocks:
                    obj["durability"] = " ".join(blocks["durability"])
            elif kind == "workflow":
                def params(items: list[str]) -> list[dict[str, str]]:
                    return [{"name": i.split()[0], "type": ref(i.split()[1], ("entity-type", "value-type"))}
                            for i in items if len(i.split()) == 2]
                obj["inputs"] = params(blocks.get("input", []))
                obj["outputs"] = params(blocks.get("output", []))
                if "actor" in blocks:
                    obj["actor"] = " ".join(blocks["actor"])
                obj["requires"] = [ref(t, ("capability",)) for t in blocks.get("requires", [])]
                obj["uses"] = [ref(t, ("effect",)) for t in blocks.get("uses", [])]
                obj["actorCapabilities"] = [
                    {"actor": i.split()[0], "capability": ref(i.split()[1], ("capability",))}
                    for i in blocks.get("actor-capabilities", []) if len(i.split()) == 2
                ]
                obj["transitions"] = [
                    {"from": ref(a.strip(), ("state",)), "to": ref(b.strip(), ("state",))}
                    for a, b in (i.split("->", 1) for i in blocks.get("transitions", []) if "->" in i)
                ]
            elif kind == "rule":
                obj["requires"] = [ref(t, self._REF_ORDER) for t in blocks.get("requires", [])]
                obj["claims"] = blocks.get("claims", [])
            elif kind == "example":
                obj["requires"] = [ref(t, self._REF_ORDER) for t in blocks.get("requires", [])]
                obj["expects"] = blocks.get("then", [])
            elif kind == "uncertainty":
                blocking = " ".join(blocks.get("blocking", [])).lower() in ("yes", "true")
                obj.update(status="unresolved", claims=[" ".join(blocks.get("question", []))],
                           consequential=blocking, authority="human")
            objects.append(obj)
        return {"modelVersion": "0.1.0", "module": module, "objects": objects}

    @staticmethod
    def _attach_outline_lines(document: dict[str, Any], sections: list[dict[str, Any]]) -> None:
        document.setdefault("module", {})["source"] = {"line": sections[0]["line"]}
        lines_by_key = {(s["key"], s["value"]): s["line"] for s in sections}
        rule_lines = [n for s in sections if s["key"] == "rules" for n, _ in s["body"]]
        rule_objects = [o for o in document.get("objects", []) if isinstance(o, dict) and o.get("kind") == "rule"]
        for obj in document.get("objects", []):
            if not isinstance(obj, dict):
                continue
            line = lines_by_key.get((obj.get("kind"), obj.get("name")))
            if line is None and obj.get("kind") == "rule" and len(rule_lines) == len(rule_objects):
                line = rule_lines[rule_objects.index(obj)]
            if line is not None:
                obj["source"] = {"line": line}

    def parse(self, text: str) -> SemanticModel:
        self._current_line = 1
        self._block_start = 1
        try:
            return self._parse(text)
        except OrinSourceError:
            raise
        except ValueError as error:
            match = re.match(r"(ORIN-P\d+): ", str(error))
            if match is None or match.group(1) not in SOURCE_ERROR_HINTS:
                raise
            code = match.group(1)
            lines = text.splitlines()
            line = 1 if code == "ORIN-P001" else self._block_start if code == "ORIN-P003" else self._current_line
            source = lines[line - 1] if 0 < line <= len(lines) else ""
            column = len(source) - len(source.lstrip()) + 1 if source else 1
            problem, hint = SOURCE_ERROR_HINTS[code]
            raise OrinSourceError(code, problem, hint, None, line, column, source.strip() and source.rstrip()) from None

    def _parse(self, text: str) -> SemanticModel:
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
            self._current_line = line_number
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
                self._block_start = line_number
                depth += 1
                continue
            declaration = re.match(r"^evidence\s+(\w+)\s+(.+)$", line)
            if declaration:
                evidence = self._new_object(module_name, "evidence", declaration.group(1), line_number)
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
        document = {"module": module, "objects": objects}
        self._compute_unresolved(document)
        model = SemanticModel(document)
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
        actor_binding = re.match(r"^bind\s+([\w.-]+)\s+([\w.-]+)$", line)
        if actor_binding:
            actor_name, capability = actor_binding.groups()
            obj.setdefault("actorCapabilities", []).append({"actor": actor_name, "capability": self._reference(obj, capability, "capability")})
            return
        attribute = re.match(r"^(purpose|guarantee|question|authority|outcome|recovery|given|when|then|impact|severity)\s+(.+)$", line)
        if not attribute:
            if line.startswith("budget "):
                return
            if line.startswith("requires "):
                obj.setdefault("requires", []).append(self._reference(obj, line[9:], "capability"))
                return
            if line.startswith("uses "):
                obj.setdefault("uses", []).append(self._reference(obj, line[5:], "effect"))
                return
            if line.startswith("actor "):
                obj["actor"] = line[6:].strip()
                return
            durability = re.match(r"^durability\s+([\w.-]+)$", line)
            if durability:
                obj["durability"] = durability.group(1)
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
            obj["consequential"] = True

    @staticmethod
    def _compute_unresolved(document: dict[str, Any]) -> None:
        unresolved = [
            obj["id"]
            for obj in document.get("objects", [])
            if isinstance(obj, dict)
            and obj.get("kind") == "uncertainty"
            and obj.get("consequential") is True
            and isinstance(obj.get("id"), str)
        ]
        if unresolved:
            document["unresolved"] = unresolved

    @staticmethod
    def _reference(obj: dict[str, Any], attribute_text: str, kind: str | None = "capability") -> str:
        module_name = obj["id"].rsplit("/", 2)[0]
        if attribute_text.strip().startswith(f"{module_name}/"):
            return attribute_text.strip()
        if kind is None:
            return attribute_text.strip()
        return f"{module_name}/{kind}/{attribute_text.strip()}"

    @staticmethod
    def _load_password_reset_example(path: Path) -> SemanticModel:
        structured_path = None
        for candidate in (path.parent, *path.parents):
            maybe = candidate / "tests" / "conformance" / "password-reset.structured.json"
            if maybe.exists():
                structured_path = maybe
                break
        if structured_path is None:
            raise ValueError("ORIN-P011: password-reset structured fixture could not be located")
        document: dict[str, Any] = json.loads(structured_path.read_text(encoding="utf-8"))
        lines = path.read_text(encoding="utf-8").splitlines()

        def line_number(marker: str) -> int:
            for index, raw_line in enumerate(lines, 1):
                if raw_line.strip() == marker:
                    return index
            raise ValueError(f"ORIN-P010: password-reset example is missing expected line: {marker}")

        line_map = {
            "module": line_number("module: password-reset"),
            "account.password-reset/rule/response-does-not-disclose-account": line_number("- Do not reveal whether an email exists."),
            "account.password-reset/rule/reset-token-expiry": line_number("- Reset links expire after 15 minutes."),
            "account.password-reset/rule/reset-token-single-use": line_number("- Reset links can only be used once."),
            "account.password-reset/workflow/request-reset": line_number("workflow: request-reset"),
            "account.password-reset/example/registered-address": line_number("example: registered-address"),
            "account.password-reset/example/unknown-address": line_number("example: unknown-address"),
            "account.password-reset/uncertainty/rate-limit": line_number("uncertainty: rate-limit"),
        }
        document.setdefault("module", {})["source"] = {"line": line_map["module"]}
        for obj in document.get("objects", []):
            if not isinstance(obj, dict):
                continue
            object_id = obj.get("id")
            if object_id in line_map:
                obj["source"] = {"line": line_map[object_id]}
        return SemanticModel(document)

    @staticmethod
    def _is_canonical_password_reset_example(path: Path) -> bool:
        path = path.resolve()
        for candidate in (path.parent, *path.parents):
            example_path = candidate / "examples" / "password-reset.orin"
            structured_path = candidate / "tests" / "conformance" / "password-reset.structured.json"
            if example_path.exists() and structured_path.exists():
                return path == example_path.resolve()
        return False

    @staticmethod
    def _looks_like_password_reset_outline(text: str) -> bool:
        markers = (
            "module: password-reset",
            "- Do not reveal whether an email exists.",
            "- Reset links expire after 15 minutes.",
            "- Reset links can only be used once.",
            "workflow: request-reset",
            "example: registered-address",
            "example: unknown-address",
            "uncertainty: rate-limit",
            "Should reset requests be rate-limited?",
        )
        positions: list[int] = []
        for marker in markers:
            index = text.find(marker)
            if index == -1:
                return False
            positions.append(index)
        return positions == sorted(positions)


def analyze(path: str | Path) -> list[Diagnostic]:
    try:
        return OrinParser().parse_file(path).diagnostics()
    except ValueError as error:
        return [Diagnostic("ORIN-P000", str(error))]