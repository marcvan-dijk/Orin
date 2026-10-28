# Orin Python codegen

Stdlib-only generator that turns a **ready** password-reset Orin model into a
standalone Python module (`password_reset_generated.py`). Output is
deterministic; the token lifetime is derived from the model's
`reset-token-expiry` rule.

```text
python -m implementations.python.codegen.generate <model.json> <outdir>
```

Run from the repository root. The model must have compilation `eligible`:
`tests/conformance/password-reset.model.json` still lists the consequential
`rate-limit` uncertainty as unresolved, so it is refused (exit 1, message on
stderr) until a human resolves that decision (e.g. via `orin_agent_core.py`).

Tests: `python -m unittest implementations.python.codegen.test_codegen`
(generates from a rate-limit-resolved copy and replays
`password-reset.cases.json` against the generated module).
