## Python/TypeScript parity check

`parity_check.py` runs every model referenced by `tests/conformance/*.cases.json`,
`*validation-cases.json` and the readiness extension cases through the Python
implementation and, if `node` is available, the TypeScript implementation. It
compares compilation status, diagnostics (code, object id, message) and the
readiness report, prints a PASS/FAIL table, and exits non-zero on any mismatch.
Without `node` the TypeScript side is skipped with a notice.

```bash
python implementations/python/parity_check.py
python -m unittest implementations/python/test_parity_check.py
```
