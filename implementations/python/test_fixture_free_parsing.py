"""Fixture-free parsing: the outline parser must reproduce the structured fixture from .orin text alone.

The fixture lookup is bypassed by calling OrinParser.parse_outline(text) without a path (a path
would let the parser walk up to tests/conformance/<stem>.structured.json). `source` line
metadata is ignored on both sides. Run `python -m implementations.python.test_fixture_free_parsing`
to print the gap report; tests for stems with no gaps are normal tests, others are expectedFailure.
"""
from __future__ import annotations

# Gap summary (initial run, parser before c1 changes):
#  * module.id/name use the bare file stem; fixture wants a namespaced module name
#    (account.password-reset, finance.expense-approval) -> object ids differ, so every object differs by id.
#  * password-reset module: context, implementationPolicies, imports not parsed; purpose text differs.
#  * rule ids: fixture uses short slugs (reset-token-expiry, no-self-decision, ...); outline derives
#    ids from the first words of the rule sentence.
#  * password-reset fixture-only objects: capability/person.request-password-reset,
#    capability/system.send-reset-message, state/{account-exists,reset-requested,reset-token-issued},
#    value-type/{email,reset-token}; the .orin text likely lacks these -> add lines to the .orin.
#  * Run `python -m implementations.python.test_fixture_free_parsing` for the full current list.

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


def parse_without_fixture(stem: str) -> dict[str, Any]:
    text = (ROOT / "examples" / f"{stem}.orin").read_text(encoding="utf-8")
    return _strip(OrinParser().parse_outline(text).document)


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

    @unittest.expectedFailure
    def test_password_reset_matches_fixture(self) -> None:
        self._check("password-reset")

    @unittest.expectedFailure
    def test_expense_approval_matches_fixture(self) -> None:
        self._check("expense-approval")


if __name__ == "__main__":
    print(gap_report())
