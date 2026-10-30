"""Guided session: walk a novice through each open question, one choice at a time.

Usage: python -m tooling.python.orin_cli guide FILE [--answers 1,2] [--out FILE.json]
Exit codes: 0 nothing open at the end, 2 questions still open, 3 invalid input.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TextIO

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementations.python import orin_agent_core as core  # noqa: E402

EXIT_OK, EXIT_BLOCKED, EXIT_INVALID = 0, 2, 3


def _show(need, number: int, total: int, out: TextIO) -> None:
    prompt = need.prompt
    print(f"\nQuestion {number} of {total}: {prompt.question}", file=out)
    if prompt.why_it_matters:
        print(f"Why it matters: {prompt.why_it_matters}", file=out)
    for index, option in enumerate(prompt.options, 1):
        print(f"  {index}. {option.label}", file=out)
        if option.explanation:
            print(f"     {option.explanation}", file=out)
        for effect in option.effects:
            print(f"     - {effect}", file=out)
        if option.compilation == "blocked":
            print("     - This choice keeps the question open.", file=out)


def _pick(prompt, answers, stdin: TextIO, out: TextIO):
    """Return the chosen option, None to stop, or raise ValueError for bad scripted input."""
    count = len(prompt.options)
    while True:
        if answers is not None:
            if not answers:
                return None
            raw = answers.pop(0)
        else:
            print(f"Type a number 1-{count} (or q to stop): ", end="", file=out, flush=True)
            line = stdin.readline()
            if not line:
                return None
            raw = line.strip()
        if raw.lower() in ("q", "quit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= count:
            return prompt.options[int(raw) - 1]
        if answers is not None:
            raise ValueError(f"answer '{raw}' is not a number from 1 to {count}")
        print(f"'{raw}' is not a choice. Please type a number from 1 to {count}.", file=out)


def run_guide(file: str, answers: list[str] | None = None, out_path: str | None = None,
              stdin: TextIO | None = None, out: TextIO | None = None) -> int:
    stdin = stdin or sys.stdin
    out = out or sys.stdout
    source = Path(file)
    if not source.is_file():
        print(f"invalid input: file not found: {source}", file=sys.stderr)
        return EXIT_INVALID
    target = Path(out_path) if out_path else source.with_name(f"{source.stem}.decided.json")
    agent = core.OrinDecisionAgent()
    current = source
    answers = list(answers) if answers is not None else None
    decided = 0
    skipped: set[str] = set()
    while True:
        open_needs = [n for n in agent.inspect(current).decisions
                      if n.prompt.uncertainty_id not in skipped]
        if not open_needs:
            break
        need = open_needs[0]
        total = decided + len(open_needs)
        _show(need, decided + 1, total, out)
        try:
            option = _pick(need.prompt, answers, stdin, out)
        except ValueError as error:
            print(f"invalid input: {error}", file=sys.stderr)
            return EXIT_INVALID
        if option is None:
            break
        if option.compilation == "blocked":
            skipped.add(need.prompt.uncertainty_id)
            print("\nOK, this question stays open. Nothing was saved for it.", file=out)
            continue
        result = agent.apply_decision(current, need.prompt.uncertainty_id, option.id)
        agent.write_model(target, result.model)
        current = target
        decided += 1
        print(f"\nSaved your choice '{option.label}' to {target}.", file=out)
    remaining = list(agent.inspect(current).decisions)
    if decided:
        print(f"\nYou decided {decided} question(s). Updated model: {target}", file=out)
    if remaining:
        print(f"Still open: {len(remaining)} question(s).", file=out)
        for need in remaining:
            print(f"  - {need.prompt.question}", file=out)
        print(f"Run again: python -m tooling.python.orin_cli guide {current}", file=out)
        return EXIT_BLOCKED
    print("Nothing is open now. Your program is ready.", file=out)
    print(f"Next: python -m tooling.python.orin_cli readiness {current}", file=out)
    return EXIT_OK
