"""JSON diagnostic entry point used by the optional VS Code extension."""

import json
import sys

from orin_parser import analyze


def main() -> int:
    diagnostics = analyze(sys.argv[1])
    print(json.dumps([{"code": item.code, "message": item.message} for item in diagnostics]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())