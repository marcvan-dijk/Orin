"""Checks for `type:` constraints in outline sources.

A `type:` section may hold these lines:

    one of: low, medium, high     (a fixed list of values)
    number: 0 to 100              (also: at least N, at most N)
    optional                      (the value may be missing)

Rules and examples may then write `name = value` (or `name is value`).
The name is a type name, or a workflow input/output name of that type.
The value must fit the type.

Codes: ORIN-E052 bad type constraint, ORIN-E053 value is not in the
`one of` list, ORIN-E054 number is out of range or not a number,
ORIN-E055 a missing value is used for a type that is not `optional`.
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = r"-?\d+(?:\.\d+)?"
_MISSING = {"none", "empty", "missing", "absent", "null"}
_ASSIGN = re.compile(r"([A-Za-z][\w.-]*)\s*(?:=|\bis not\b|\bis\b|\bequals\b)\s*[\"']?([\w.-]+)")


def _parse_constraints(lines: list[str]) -> tuple[dict[str, Any], list[str]]:
    spec: dict[str, Any] = {}
    problems: list[str] = []
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        if text == "optional":
            spec["optional"] = True
            continue
        enum = re.match(r"^one of:\s*(.*)$", text)
        if enum:
            values = [v.strip() for v in enum.group(1).split(",") if v.strip()]
            if not values:
                problems.append("`one of:` needs at least one value")
            elif len(set(values)) != len(values):
                problems.append("`one of:` has a repeated value")
            elif "oneOf" in spec:
                problems.append("a type can have only one `one of:` line")
            else:
                spec["oneOf"] = values
            continue
        number = re.match(r"^number:\s*(.*)$", text)
        if number:
            body = number.group(1).strip()
            low = high = None
            span = re.match(rf"^({_NUMBER})\s+to\s+({_NUMBER})$", body)
            if span:
                low, high = float(span.group(1)), float(span.group(2))
            elif re.match(rf"^at least\s+{_NUMBER}$", body):
                low = float(body.split()[-1])
            elif re.match(rf"^at most\s+{_NUMBER}$", body):
                high = float(body.split()[-1])
            elif body == "":
                spec["number"] = True
                continue
            else:
                problems.append(f"bad number range: {body}")
                continue
            if low is not None and high is not None and low > high:
                problems.append(f"number range starts above its end: {body}")
                continue
            spec.update(number=True, min=low, max=high)
            continue
        problems.append(f"unknown type line: {text}")
    if "oneOf" in spec and spec.get("number"):
        problems.append("a type cannot be both `one of:` and `number:`")
    return spec, problems


def check_types(document: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    """Return (code, message, object_id) tuples."""
    objects = document.get("objects", [])
    if not isinstance(objects, list):
        return []
    results: list[tuple[str, str, str | None]] = []
    specs: dict[str, dict[str, Any]] = {}
    for obj in objects:
        if isinstance(obj, dict) and obj.get("kind") == "value-type" and obj.get("constraintLines"):
            spec, problems = _parse_constraints([str(l) for l in obj["constraintLines"]])
            for problem in problems:
                results.append(("ORIN-E052", f"type {obj.get('name')}: {problem}", obj.get("id")))
            specs[str(obj.get("name"))] = spec
            specs[str(obj.get("id"))] = spec
    if not specs:
        return results

    # Names that carry a constrained type: the type names and workflow inputs/outputs.
    names: dict[str, tuple[str, dict[str, Any]]] = {}
    for key, spec in specs.items():
        if "/" not in key:
            names[key] = (key, spec)
    for obj in objects:
        if isinstance(obj, dict) and obj.get("kind") == "workflow":
            for field in ("inputs", "outputs"):
                for item in obj.get(field) or []:
                    if isinstance(item, dict) and item.get("type") in specs:
                        spec = specs[item["type"]]
                        names[str(item.get("name"))] = (str(item["type"]).rsplit("/", 1)[-1], spec)

    for obj in objects:
        if not isinstance(obj, dict) or obj.get("kind") not in ("rule", "example"):
            continue
        texts = [t for f in ("claims", "expects") for t in (obj.get(f) or []) if isinstance(t, str)]
        for text in texts:
            for match in _ASSIGN.finditer(text):
                name = match.group(1).rstrip(".").split(".")[-1]
                value = match.group(2).rstrip(".")
                if name not in names:
                    continue
                type_name, spec = names[name]
                problem = _check_value(type_name, spec, value)
                if problem:
                    results.append((problem[0], problem[1], obj.get("id")))
    return results


def _check_value(type_name: str, spec: dict[str, Any], value: str) -> tuple[str, str] | None:
    if value.lower() in _MISSING:
        if spec.get("optional"):
            return None
        return ("ORIN-E055", f"type {type_name} is not optional, but a missing value is used")
    if "oneOf" in spec and value not in spec["oneOf"]:
        return ("ORIN-E053", f"{value} is not one of the values of type {type_name}: {', '.join(spec['oneOf'])}")
    if spec.get("number"):
        if not re.fullmatch(_NUMBER, value):
            return ("ORIN-E054", f"{value} is not a number, but type {type_name} is a number")
        number = float(value)
        if (spec.get("min") is not None and number < spec["min"]) or (
            spec.get("max") is not None and number > spec["max"]
        ):
            return ("ORIN-E054", f"{value} is outside the range of type {type_name}")
    return None
