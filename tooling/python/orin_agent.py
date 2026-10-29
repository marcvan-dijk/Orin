"""CLI entry point for the offline Orin decision-support agent.

Run as: python -m tooling.python.orin_agent (from the repository root).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementations.python.orin_agent_core import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
