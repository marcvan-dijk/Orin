# Novice flow demo

A scripted, stdlib-only walk through the core Orin flow using password reset:

1. Plain-English request.
2. Existing `examples/password-reset.orin` is checked: **blocked** on the rate-limit question.
3. A decision is applied through `implementations/python/orin_agent_core.py` (read-only import).
4. Re-check: **ready**.
5. A Python implementation is generated with `implementations.python.codegen.generate`.
6. `tests/conformance/password-reset.cases.json` is replayed against it.

Each step prints a plain-English summary.

```text
python -m tooling.python.demo_novice_flow
python -m unittest tooling.python.test_demo_novice_flow
```

Run from the repository root. Output goes to a scratch directory inside the
repo that is removed afterwards. Exit code 1 means a step or case failed.
