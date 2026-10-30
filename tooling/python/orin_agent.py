"""CLI entry point for the offline Orin decision-support agent.

Run as: python -m tooling.python.orin_agent (from the repository root).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import contextlib  # noqa: E402
import io  # noqa: E402

from implementations.python import orin_agent_core as core  # noqa: E402

_ALIASES = {"--decide": "--option", "--out": "--write"}
_STALE_HINT = "add an inline `options:` block to this uncertainty in the .orin file"
_NEW_HINT = "add `option: <id>` blocks to this uncertainty in the .orin file"


def _normalize(argv: list[str]) -> list[str]:
    """Accept the same decide flags as orin_cli: --option/--decide, --out/--write."""
    result = []
    for arg in argv:
        name, eq, value = arg.partition("=")
        result.append(_ALIASES[name] + eq + value if name in _ALIASES else arg)
    return result


def _resolve_uncertainty(argv: list[str]) -> list[str]:
    """Fill a missing --uncertainty from --option, and expand a short uncertainty name."""
    if "decide" not in argv[:1] or any(a in ("-h", "--help") for a in argv):
        return argv

    def value(flag):
        for i, a in enumerate(argv):
            if a == flag and i + 1 < len(argv):
                return argv[i + 1]
            if a.startswith(flag + "="):
                return a.partition("=")[2]
        return None

    path, option, given = (argv[1] if len(argv) > 1 else None), value("--option"), value("--uncertainty")
    if not path or given and "/" in given:
        return argv
    try:
        decisions = core.OrinDecisionAgent().inspect(path).decisions
    except Exception:
        return argv
    ids = [d.prompt.uncertainty_id for d in decisions]
    if given:
        found = [i for i in ids if i.rsplit("/", 1)[-1] == given]
    elif option:
        found = [d.prompt.uncertainty_id for d in decisions
                 if any(o.id == option for o in d.prompt.options)]
    else:
        return argv
    if len(found) != 1:
        return argv
    rest = []
    skip = False
    for a in argv:
        if skip:
            skip = False
        elif a == "--uncertainty":
            skip = True
        elif not a.startswith("--uncertainty="):
            rest.append(a)
    return rest + ["--uncertainty", found[0]]


def main(argv: list[str] | None = None) -> int:
    argv = _resolve_uncertainty(_normalize(list(sys.argv[1:] if argv is None else argv)))
    if argv[:1] == ["decide"] and not any(
            a == "--uncertainty" or a.startswith("--uncertainty=") or a in ("-h", "--help")
            for a in argv):
        print("invalid input: could not find the open decision. Use --option <id> with an "
              "option shown by inspect, or add --uncertainty <id>.", file=sys.stderr)
        return core.EXIT_INVALID
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = core.main(argv)
    finally:
        sys.stdout.write(buffer.getvalue().replace(_STALE_HINT, _NEW_HINT))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
