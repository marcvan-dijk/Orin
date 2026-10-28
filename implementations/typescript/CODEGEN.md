# TypeScript code generation (password-reset)

`src/codegen/generate_password_reset.ts` emits a standalone, dependency-free,
deterministic `.ts` module from the password-reset model, with the
`rate-limit` uncertainty resolved by an explicit decision
(`{ maxRequests, windowSeconds }`, per address).

The generator refuses (`GenerationRefused`) when the model, after applying the
decision, is not `eligible`, or when the decision is invalid. A blocked model
never produces output.

```bash
node --experimental-strip-types implementations/typescript/src/codegen/generate_password_reset.ts \
  tests/conformance/password-reset.model.json 5 3600 > password_reset.generated.ts
```

The generated module exports `PasswordReset` (constructed with `Ports`:
`accountExists`, `sendResetMessage`), `RATE_LIMIT`, and `TokenRejected`.
Rate-limited requests receive the same standard confirmation, with no token.

Test (runs generated code against `tests/conformance/password-reset.cases.json`):

```bash
node --test --experimental-strip-types implementations/typescript/src/codegen/
```

Optional host-language code; it does not change `.ori` semantics or fixtures.
