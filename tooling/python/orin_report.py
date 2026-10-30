"""Machine-readable diagnostics for `orin_cli check --format`: text, json, sarif, github."""

from __future__ import annotations

import json
import re
from pathlib import Path

FORMATS = ("text", "json", "sarif", "github")

_HINTS = {
    "ORIN-E041": "Answer the open question: run orin_cli decide <file> --option <option-id>.",
}
_DEFAULT_HINT = "Fix the issue in the file, then run orin_cli check again."


def _locate(lines: list[str], object_id: str | None) -> tuple[int, int]:
    """Best-effort 1-based line and column from the last part of the object id."""
    if object_id:
        name = re.split(r"[/.]", object_id)[-1]
        pattern = re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])")
        for number, text in enumerate(lines, 1):
            found = pattern.search(text)
            if found:
                return number, found.start() + 1
    return 1, 1


def collect(file: str, diagnostics) -> list[dict]:
    try:
        lines = Path(file).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        lines = []
    items = []
    for d in diagnostics:
        line, column = _locate(lines, d.object_id)
        items.append({"code": d.code, "message": d.message, "file": file, "line": line,
                      "column": column, "severity": "error", "objectId": d.object_id,
                      "hint": _HINTS.get(d.code, _DEFAULT_HINT)})
    return items


def _github_escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def render(fmt: str, file: str, items: list[dict]) -> str:
    if fmt == "json":
        return json.dumps({"file": file, "diagnostics": items}, indent=2)
    if fmt == "github":
        return "\n".join(
            f"::{i['severity']} file={_github_escape(i['file'])},line={i['line']},col={i['column']},"
            f"title={i['code']}::{_github_escape(i['message'])}" for i in items)
    if fmt == "sarif":
        rules = sorted({i["code"] for i in items})
        results = [{
            "ruleId": i["code"], "level": i["severity"],
            "message": {"text": f"{i['message']} Hint: {i['hint']}"},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": i["file"]},
                "region": {"startLine": i["line"], "startColumn": i["column"]}}}],
        } for i in items]
        return json.dumps({
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{"tool": {"driver": {"name": "orin", "rules": [{"id": r} for r in rules]}},
                      "results": results}]}, indent=2)
    raise ValueError(f"unknown format: {fmt}")
