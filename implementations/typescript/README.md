## TypeScript reference implementation

This folder contains a host-language TypeScript reference slice for the
password-reset proof flow.

Current files mirror the Python proof path at a small scope:

- `src/orin_model.ts` — canonicalization and readiness diagnostics parity checks
- `src/lowering.ts` — implementation-policy based artifact derivation
- `src/password_reset.ts` — deterministic password-reset runtime
- `src/conformance_runner.ts` — language-neutral fixture execution
- `src/password_reset_proof.ts` — end-to-end derivation proof runner

This is optional host-language code. It does not change `.ori` semantics or
`tests/conformance/` fixtures.

Run focused proof-flow validation with:

```bash
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
```

Generated password-reset rate-limit conformance uses the same language-neutral
cases as Python, under both accepted policy choices:

```bash
node --test --experimental-strip-types implementations/typescript/src/codegen/password_reset_rate_limit.test.ts
```

Unlike the reference-runtime proof above, this executes generated code and
checks each request's confirmation, message delivery, and privacy observations.
`python implementations/python/parity_check.py` additionally compares both
generated backends against the shared expectations.
