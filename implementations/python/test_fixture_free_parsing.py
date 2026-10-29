"""Fixture-free parsing: the outline parser must reproduce the structured fixture from .orin text alone.

The fixture lookup is bypassed by calling OrinParser.parse_outline(text) without a path (a path
would let the parser walk up to tests/conformance/<stem>.structured.json). `source` line
metadata is ignored on both sides. Run `python -m implementations.python.test_fixture_free_parsing`
to print the gap report; tests for stems with no gaps are normal tests, others are expectedFailure.
"""
from __future__ import annotations

# Decision data authored inline on an uncertainty (why_it_matters, affected_objects, rule,
# options) is not part of the structured fixture; it is compared to <stem>.decisions.json instead.

import json
import unittest
from pathlib import Path
from typing import Any

from implementations.python.orin_parser import OrinParser

ROOT = Path(__file__).resolve().parents[2]
STEMS = ("password-reset", "expense-approval")


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k != "source"}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


DECISION_KEYS = ("why_it_matters", "affected_objects", "rule", "options")


def parse_without_fixture(stem: str, keep_decisions: bool = False) -> dict[str, Any]:
    text = (ROOT / "examples" / f"{stem}.orin").read_text(encoding="utf-8")
    document = _strip(OrinParser().parse_outline(text).document)
    if not keep_decisions:
        for obj in document["objects"]:
            if obj["kind"] == "uncertainty":
                for key in DECISION_KEYS:
                    obj.pop(key, None)
    return document


def load_fixture(stem: str) -> dict[str, Any]:
    path = ROOT / "tests" / "conformance" / f"{stem}.structured.json"
    return _strip(json.loads(path.read_text(encoding="utf-8")))


def _diff_values(path: str, expected: Any, actual: Any, out: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                out.append(f"{path}.{key}: missing (expected {expected[key]!r})")
            elif key not in expected:
                out.append(f"{path}.{key}: unexpected (got {actual[key]!r})")
            else:
                _diff_values(f"{path}.{key}", expected[key], actual[key], out)
    elif expected != actual:
        out.append(f"{path}: expected {expected!r}, got {actual!r}")


def diff_models(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Object-by-object differences; each line names the object id and field."""
    out: list[str] = []
    for key in sorted((set(expected) | set(actual)) - {"objects"}):
        _diff_values(key, expected.get(key), actual.get(key), out)
    exp = {o["id"]: o for o in expected.get("objects", [])}
    act = {o["id"]: o for o in actual.get("objects", [])}
    for oid in exp:
        if oid not in act:
            out.append(f"object {oid}: missing")
        else:
            _diff_values(f"object {oid}", exp[oid], act[oid], out)
    for oid in act:
        if oid not in exp:
            out.append(f"object {oid}: unexpected")
    return out


def gap_report() -> str:
    parts = []
    for stem in STEMS:
        try:
            gaps = diff_models(load_fixture(stem), parse_without_fixture(stem))
        except Exception as error:  # report parser failures as gaps too
            gaps = [f"parse failed: {type(error).__name__}: {error}"]
        parts.append(f"== {stem}: {len(gaps)} gap(s)\n" + "\n".join(f"  {g}" for g in gaps))
    return "\n".join(parts)


class FixtureFreeParsingTests(unittest.TestCase):
    def _check(self, stem: str) -> None:
        self.assertEqual([], diff_models(load_fixture(stem), parse_without_fixture(stem)))

    def test_password_reset_matches_fixture(self) -> None:
        self._check("password-reset")

    def test_expense_approval_matches_fixture(self) -> None:
        self._check("expense-approval")

    def test_expense_inline_decisions_match_sidecar(self) -> None:
        sidecar = json.loads((ROOT / "tests" / "conformance" / "expense-approval.decisions.json").read_text(encoding="utf-8"))
        document = parse_without_fixture("expense-approval", keep_decisions=True)
        for obj in document["objects"]:
            if obj["kind"] == "uncertainty":
                expected = sidecar["decisions"][obj["id"]]
                self.assertEqual(expected, {k: obj[k] for k in DECISION_KEYS})


if __name__ == "__main__":
    print(gap_report())
