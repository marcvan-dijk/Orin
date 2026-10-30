"""Consistency checks between rules and examples (stdlib only).

ORIN-E047: two rules say opposite things under the same condition.
ORIN-E048: an example expects something that a rule it belongs to forbids.

A statement is split into: condition, subject text, polarity, and an optional
assigned value ("order.state = paid"). The checks are text based and
deliberately simple: they only report clear conflicts.
"""

from __future__ import annotations

import re
from typing import Any

CONDITION_RE = re.compile(r"^(?:when|if)\s+(.+?)(?:,\s*|\s+then\s+)(.+)$", re.IGNORECASE)
NEGATION_PREFIXES = ("never ", "not ", "no ")
NEGATION_INFIXES = (
    (re.compile(r"\b(must|shall|should|can|may|will) not\b"), r"\1"),
    (re.compile(r"\b(does|do|did) not\b"), ""),
    (re.compile(r"\b(is|are) not\b"), r"\1"),
    (re.compile(r"\bcannot\b"), "can"),
)
ASSIGNMENT_RE = re.compile(r"^(.+?)\s*=\s*(.+)$")


def _clean(text: str) -> str:
    text = " ".join(text.strip().split()).lower()
    return re.sub(r"[.,;:!?]+$", "", text).strip()


def parse_statement(text: str, negated: bool = False) -> dict[str, Any] | None:
    """Return {condition, subject, negated, value} or None for empty text."""
    cleaned = _clean(text)
    condition = ""
    match = CONDITION_RE.match(cleaned)
    if match:
        condition, cleaned = _clean(match.group(1)), _clean(match.group(2))
    for prefix in NEGATION_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned, negated = _clean(cleaned[len(prefix):]), not negated
            break
    else:
        for pattern, replacement in NEGATION_INFIXES:
            if pattern.search(cleaned):
                cleaned, negated = _clean(pattern.sub(replacement, cleaned)), not negated
                break
    if not cleaned:
        return None
    value = None
    assignment = ASSIGNMENT_RE.match(cleaned)
    if assignment:
        cleaned, value = _clean(assignment.group(1)), _clean(assignment.group(2))
    return {"condition": condition, "subject": cleaned, "negated": negated, "value": value}


def _claim_statements(values: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in values if isinstance(values, list) else []:
        if isinstance(item, str):
            statement = parse_statement(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            statement = parse_statement(item["text"], item.get("negated") is True)
        else:
            statement = None
        if statement:
            result.append(statement)
    return result


def _conflict(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if first["condition"] != second["condition"] or first["subject"] != second["subject"]:
        return False
    if first["value"] is not None and second["value"] is not None:
        return (first["value"] == second["value"]) == (first["negated"] != second["negated"])
    if first["value"] != second["value"]:
        return False
    return first["negated"] != second["negated"]


def _describe(statement: dict[str, Any]) -> str:
    text = statement["subject"]
    if statement["value"] is not None:
        text += f" = {statement['value']}"
    if statement["negated"]:
        text = f"not {text}"
    if statement["condition"]:
        text = f"when {statement['condition']}: {text}"
    return text


def _example_statements(example: dict[str, Any]) -> list[dict[str, Any]]:
    statements = _claim_statements(example.get("expects"))
    # Parsed examples keep given/when/then as claims; only the last is the result.
    claims = example.get("claims")
    if isinstance(claims, list) and claims and not statements:
        statements = _claim_statements(claims[-1:])
    return statements


def consistency_diagnostics(objects: list[Any]) -> list[tuple[str, str, str | None]]:
    """Return (code, message, object id) tuples in a stable order."""
    rules = [o for o in objects if isinstance(o, dict) and o.get("kind") == "rule" and isinstance(o.get("id"), str)]
    examples = [o for o in objects if isinstance(o, dict) and o.get("kind") == "example"]
    parsed = {rule["id"]: _claim_statements(rule.get("claims")) for rule in rules}
    found: list[tuple[str, str, str | None]] = []

    ordered = sorted(parsed)
    for index, first_id in enumerate(ordered):
        for second_id in ordered[index + 1:]:
            reported: set[str] = set()
            for first in parsed[first_id]:
                for second in parsed[second_id]:
                    if _conflict(first, second) and _describe(first) not in reported:
                        reported.add(_describe(first))
                        found.append((
                            "ORIN-E047",
                            f"rules conflict: {first_id} says '{_describe(first)}' "
                            f"but {second_id} says '{_describe(second)}'",
                            second_id,
                        ))

    for example in sorted(examples, key=lambda o: str(o.get("id"))):
        example_id = example.get("id")
        requires = example.get("requires") if isinstance(example.get("requires"), list) else []
        outcomes = _example_statements(example)
        for rule_id in ordered:
            rule = next(r for r in rules if r["id"] == rule_id)
            links = rule.get("evidenceLinks") if isinstance(rule.get("evidenceLinks"), list) else []
            if rule_id not in requires and example_id not in links:
                continue
            for claim in parsed[rule_id]:
                for outcome in outcomes:
                    if _conflict(claim, outcome):
                        found.append((
                            "ORIN-E048",
                            f"example contradicts rule: {example_id} expects '{_describe(outcome)}' "
                            f"but {rule_id} says '{_describe(claim)}'",
                            example_id if isinstance(example_id, str) else None,
                        ))
    return found
