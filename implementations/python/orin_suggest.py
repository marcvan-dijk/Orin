"""Helpers that make Orin source errors easier to fix: 'did you mean' and valid-key lists."""

TOP_LEVEL_KEYWORDS = (
    "module", "purpose", "import", "type", "state", "capability", "entity", "relation", "rule",
    "workflow", "example", "uncertainty", "target", "effect", "evidence", "context",
    "policy implementation", "scope", "risk", "role",
)
DECLARATION_ATTRIBUTES = (
    "purpose", "guarantee", "question", "authority", "outcome", "recovery", "given", "when",
    "then", "impact", "severity", "requires", "uses", "actor", "durability", "input", "field", "budget",
)
CONTEXT_KEYS = ("repository", "risk")
POLICY_KEYS = ("optimize-for", "prefer", "require", "deploy-to")
FIELD_MODIFIERS = ("identity",)

VALID_KEYS = {
    "ORIN-P002": TOP_LEVEL_KEYWORDS,
    "ORIN-P005": DECLARATION_ATTRIBUTES,
    "ORIN-P006": CONTEXT_KEYS,
    "ORIN-P007": POLICY_KEYS,
    "ORIN-P009": FIELD_MODIFIERS,
}


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def suggest(word: str, options) -> str | None:
    """Return the closest option to word, or None when nothing is close."""
    word = word.lower()
    best, best_distance = None, None
    for option in options:
        distance = levenshtein(word, option)
        if best_distance is None or distance < best_distance:
            best, best_distance = option, distance
    if best is None or best_distance > max(1, min(len(word), len(best)) // 3 + 1):
        return None
    return best


def first_word(source_line: str, code: str) -> str:
    """The word most likely to be misspelled for this error code."""
    words = source_line.split()
    if code == "ORIN-P009":
        return words[-1] if words else ""
    return words[0] if words else ""


def extra_hint(code: str, source_line: str) -> str:
    """Extra help text: a 'did you mean' line and the list of valid keys, or ''."""
    options = VALID_KEYS.get(code)
    if not options:
        return ""
    parts = []
    close = suggest(first_word(source_line, code), options)
    if close:
        parts.append(f'Did you mean "{close}"?')
    parts.append("Valid here: " + ", ".join(options) + ".")
    return "\n  ".join(parts)
