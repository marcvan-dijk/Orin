"""Inline decision data for outline `uncertainty:` sections.

Keys: why: (or why-it-matters:), affects:, option:. They let an author keep a
decision in the .ori file, with no .decisions.json sidecar.
"""

import re
from typing import Any

WHY_KEYS = ("why", "why-it-matters")
_KEY = re.compile(r"^([A-Za-z][\w-]*):\s*(.*)$")
_OPTION_FIELDS = ("label", "explanation", "effects", "impact")


def _slug(text: str, words: int = 6) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:words]) or "option"


def _items(first: str, rest: list[str]) -> list[str]:
    items = []
    for chunk in ([first] if first else []) + rest:
        for part in chunk.split(","):
            part = part.strip()
            part = part[2:].strip() if part.startswith("- ") else part
            if part:
                items.append(part)
    return items


def parse_inline_decision(body: list[tuple[int, str]], resolve: Any) -> dict[str, Any]:
    """Return decision fields found in an uncertainty body. `resolve` maps a name to an object id."""
    groups: list[tuple[str, str, list[str]]] = []
    for _, text in body:
        match = _KEY.match(text)
        known = match and (match.group(1) in WHY_KEYS or match.group(1) in ("affects", "option", "question", "blocking")
                           or (groups and groups[-1][0] == "option" and match.group(1) in _OPTION_FIELDS))
        if known:
            groups.append((match.group(1), match.group(2).strip(), []))
        elif groups:
            groups[-1][2].append(text)
    out: dict[str, Any] = {}
    options: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for key, first, rest in groups:
        if key in WHY_KEYS:
            out["why_it_matters"] = " ".join([first] + rest).strip()
        elif key == "affects":
            out["affected_objects"] = [resolve(t) for t in _items(first, rest)]
        elif key == "option":
            text = " ".join([first] + rest).strip()
            current = {"id": _slug(text), "label": text, "explanation": text}
            options.append(current)
        elif current is not None and key in _OPTION_FIELDS:
            if key in ("effects", "impact"):
                current[key] = _items(first, rest)
            else:
                current[key] = " ".join([first] + rest).strip()
    if options:
        out["options"] = options
    return out
