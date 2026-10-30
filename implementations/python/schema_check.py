"""Tiny stdlib-only JSON Schema checker.

Supports only the keywords used by tests/conformance/model.schema.json:
$ref (local "#/..." only), $defs, type, enum, const, required, properties,
additionalProperties (true/false), items, minLength, minimum, oneOf, anyOf, not.
Other keywords (for example $schema, $id, title, description) are ignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve(root: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local $ref is supported: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _same(a: Any, b: Any) -> bool:
    # JSON equality that does not treat true as 1.
    return type(a) is type(b) and a == b


def _check(root, schema, value, path, errors) -> None:
    if "$ref" in schema:
        _check(root, _resolve(root, schema["$ref"]), value, path, errors)

    if "type" in schema:
        expected = schema["type"]
        names = expected if isinstance(expected, list) else [expected]
        if not any(_TYPES[n](value) for n in names):
            errors.append(f"{path}: expected type {expected}")
            return
    if "enum" in schema and not any(_same(value, e) for e in schema["enum"]):
        errors.append(f"{path}: value {value!r} is not one of {schema['enum']}")
    if "const" in schema and not _same(value, schema["const"]):
        errors.append(f"{path}: value must be {schema['const']!r}")
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: string is shorter than {schema['minLength']}")
    if _TYPES["number"](value) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: value is less than {schema['minimum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required property '{key}'")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                _check(root, props[key], item, f"{path}/{key}", errors)
            elif schema.get("additionalProperties", True) is False:
                errors.append(f"{path}: unknown property '{key}'")
            elif isinstance(schema.get("additionalProperties"), dict):
                _check(root, schema["additionalProperties"], item, f"{path}/{key}", errors)

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _check(root, schema["items"], item, f"{path}/{index}", errors)

    if "not" in schema and validate_sub(root, schema["not"], value):
        errors.append(f"{path}: value must not match the 'not' schema")
    if "anyOf" in schema and not any(validate_sub(root, s, value) for s in schema["anyOf"]):
        errors.append(f"{path}: value does not match any allowed shape")
    if "oneOf" in schema:
        count = sum(1 for s in schema["oneOf"] if validate_sub(root, s, value))
        if count != 1:
            errors.append(f"{path}: value matches {count} shapes, expected exactly 1")


def validate_sub(root: dict[str, Any], schema: dict[str, Any], value: Any) -> bool:
    errors: list[str] = []
    _check(root, schema, value, "", errors)
    return not errors


def validate(schema: dict[str, Any], value: Any) -> list[str]:
    """Return a list of error messages. An empty list means the value is valid."""
    errors: list[str] = []
    _check(schema, schema, value, "#", errors)
    return errors
