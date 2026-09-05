## TypeScript reference implementation

This folder contains a host-language TypeScript reference slice for the
password-reset proof flow.

Current files mirror the Python proof path at a small scope:

- `src/orin_model.ts` — canonicalization and unresolved-ambiguity readiness check
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
