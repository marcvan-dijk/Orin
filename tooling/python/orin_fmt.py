"""Canonical formatter for outline-style .orin files (dependency-free).

Rules: LF line endings, no BOM, no trailing spaces, 2-space indentation per
nesting level, one blank line before each top-level section (none inside),
a single final newline, and a fixed key order inside example, uncertainty,
option and workflow-like blocks. The meaning of the file does not change.
"""

from __future__ import annotations

import re

INDENT = "  "
_KEY = re.compile(r"^([A-Za-z][\w-]*):")

_ORDER = {
    "example": ["given", "when", "then"],
    "uncertainty": ["blocking", "question", "why-it-matters", "affects", "rule", "option"],
    "option": ["label", "explanation", "effects", "impact", "rule-claims", "example",
              "compilation"],
    "workflow": ["input", "requires", "steps", "output", "failure", "recovery", "after",
                 "claims"],
}


def _key(text: str) -> str | None:
    match = _KEY.match(text)
    return match.group(1) if match else None


def _reorder(nodes: list[dict], parent_key: str | None) -> list[dict]:
    for node in nodes:
        node["children"] = _reorder(node["children"], _key(node["text"]))
    order = _ORDER.get(parent_key or "")
    keys = [_key(n["text"]) for n in nodes]
    if order and None not in keys and all(k in order for k in keys) \
            and len(set(keys)) == len(keys):
        nodes = sorted(nodes, key=lambda n: order.index(_key(n["text"])))
    return nodes


def _flatten(nodes: list[dict], out: list[dict]) -> None:
    for node in nodes:
        out.append(node)
        _flatten(node["children"], out)


def format_text(text: str) -> str:
    """Return the canonical form of outline-style source text."""
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    entries = []  # (indent width, stripped text, is_comment)
    for raw in text.split("\n"):
        stripped = raw.strip()
        if not stripped:
            continue
        width = len(raw.expandtabs(4)) - len(raw.expandtabs(4).lstrip())
        entries.append((width, stripped))

    # Comment lines take the depth of the next code line, so they stay with it.
    sections: list[list[tuple[int, str]]] = []
    pending: list[str] = []
    for width, stripped in entries:
        if stripped.startswith("//"):
            pending.append(stripped)
            continue
        if width == 0:
            sections.append([])
        if not sections:
            sections.append([])
        sections[-1].extend((width, c) for c in pending)
        pending = []
        sections[-1].append((width, stripped))
    trailing = pending

    blocks = []
    for section in sections:
        # Comments carry the width of their code line; rebuild depth from a stack.
        roots: list[dict] = []
        stack: list[dict] = []
        comments: list[str] = []
        for width, line in section:
            if line.startswith("//"):
                comments.append(line)
                continue
            node = {"indent": width, "text": line, "children": [], "comments": comments}
            comments = []
            while stack and stack[-1]["indent"] >= width:
                stack.pop()
            (stack[-1]["children"] if stack else roots).append(node)
            stack.append(node)
        roots = _reorder(roots, None)
        lines: list[str] = []

        def emit(nodes: list[dict], depth: int) -> None:
            for node in nodes:
                lines.extend(INDENT * depth + c for c in node["comments"])
                lines.append(INDENT * depth + node["text"])
                emit(node["children"], depth + 1)

        emit(roots, 0)
        blocks.append("\n".join(lines))
    if trailing:
        blocks.append("\n".join(trailing))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def main(file: str, check: bool = False, write: bool = False) -> int:
    """Format FILE. Exit 0 ok, 1 when --check finds changes, 3 on bad input."""
    import sys

    try:
        with open(file, encoding="utf-8", newline="") as handle:
            before = handle.read()
    except OSError as error:
        print(f"invalid input: {error}", file=sys.stderr)
        return 3
    after = format_text(before)
    if write:
        if after != before:
            with open(file, "w", encoding="utf-8", newline="") as handle:
                handle.write(after)
            print(f"Formatted {file}.")
        else:
            print(f"{file} is already formatted.")
        return 0
    if check:
        if after != before:
            print(f"{file} is not formatted. Run: python -m tooling.python.orin_cli fmt {file} --write")
            return 1
        print(f"{file} is formatted.")
        return 0
    sys.stdout.write(after)
    return 0
