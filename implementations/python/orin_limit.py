"""Recognize the outline form for numeric upper-bound claims."""

import re

_CAPACITY_LIMIT = re.compile(
    r"^\s*an event never has more (?P<measure>[a-z][a-z -]*?) than its "
    r"(?P<parameter>[a-z][a-z0-9-]*)\.?\s*$",
    re.IGNORECASE,
)


def parse_capacity_limit_claim(text: str) -> dict[str, str] | None:
    match = _CAPACITY_LIMIT.fullmatch(text)
    return {key: value.lower() for key, value in match.groupdict().items()} if match else None
