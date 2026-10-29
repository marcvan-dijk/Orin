# Contributing to Orin

Run every command from the repository root.

## Scope rule

Orin holds **durable meaning**: rules, guarantees, domain concepts, accepted
decisions, constraints, observable behaviour, and unresolved ambiguities.

Orin does **not** hold plans, tasks, workflow, AI process, timestamps, or
provenance. Before adding syntax, a model field, or a document, ask: if the
whole implementation and process were replaced, would this still need to
survive? If not, it does not belong in Orin.

## Run the tests

Versions are listed once in the [README](README.md#try-it). They are only
needed for the tools and tests, not to read Orin or the fixtures. On Windows
PowerShell, run each command on one line.

```text
# Python implementation and tooling
python -m unittest discover -s implementations/python -t .
python -m unittest discover -s tooling/python -t .

# TypeScript implementation
node --test --experimental-strip-types implementations/typescript/src/*.test.ts implementations/typescript/src/codegen/*.test.ts

# Python and TypeScript must agree on the shared fixtures
python implementations/python/parity_check.py

# Password-reset proof
python implementations/python/password_reset_proof.py
python implementations/python/test_orin_model.py PasswordResetProofRunTests.test_password_reset_end_to_end_derivation_proof
node --experimental-strip-types implementations/typescript/src/password_reset_proof.ts
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts

# VS Code extension
(cd tooling/vscode-extension && npm ci && npm test)
```

CI runs the same commands: `.github/workflows/ci.yml`.

## Repository layout

- `docs/`, `examples/`, `tests/conformance/` are language-neutral.
- Host-language code goes under `implementations/<language>/` or `tooling/`.
- The language-neutral core (`orin/` if present, and `tests/conformance/`) must
  not import host-language code or hold package metadata or test runners.
- Keep each host folder's tests, dependencies, and setup notes inside that folder.
- Prefer the standard library. Do not make a runtime install a requirement for
  reading `.ori`/`.orin` programs or fixtures.

## Add a conformance fixture

1. Add JSON files to `tests/conformance/` named `<program>.model.json` (meaning)
   and `<program>.cases.json` (observable examples).
2. Keep them free of host-language details.
3. Describe the fixture in `tests/conformance/README.md`.
4. Make both implementations pass it. Check with
   `python implementations/python/parity_check.py`, and add it to that script's
   fixture list if it is not picked up.
5. Run the Python and TypeScript tests above.

## Add an example app

1. Write `examples/<name>.orin`. Use [`docs/ORIN-SYNTAX-GUIDE.md`](docs/ORIN-SYNTAX-GUIDE.md).
2. Check it: `python -m tooling.python.orin_cli check examples/<name>.orin`.
   Unresolved consequential decisions report "blocked" on purpose.
3. Add matching conformance fixtures (see above) if it should be proven.
4. Link it from [`docs/README.md`](docs/README.md).
