# Password-reset MVP demo runbook (1 day, executable)

Run from repository root (`/home/runner/work/Orin/Orin`).

## Command sequence and expected outcomes

1. Python proof run:
   ```bash
   python implementations/python/password_reset_proof.py
   ```
   Expected: JSON with `blockedCompilation: "blocked"`, `resolvedCompilation: "eligible"`, `canonicalMeaningStableAcrossVariants: true`, two policy variants with different `derivedArtifact`, and password-reset `behaviorCases`.

2. Python proof check:
   ```bash
   python implementations/python/test_orin_model.py PasswordResetProofRunTests.test_password_reset_end_to_end_derivation_proof
   ```
   Expected: `Ran 1 test ... OK`.

3. TypeScript proof run:
   ```bash
   node --experimental-strip-types implementations/typescript/src/password_reset_proof.ts
   ```
   Expected: same proof-shape JSON and key values as step 1.

4. TypeScript proof checks:
   ```bash
   node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
   ```
   Expected: `# pass 3`, `# fail 0`.

## What this demo proves

- **End-to-end workflow:** model + cases + policy lowering + runtime checks (`password_reset_proof`).
- **Consequential ambiguity boundary:** unresolved rate-limit uncertainty blocks compile (`blockedCompilation`).
- **Explicit decision completion:** resolving that uncertainty moves compile status to `eligible`.
- **Durable meaning:** canonical meaning remains stable across policy variants.
- **Deterministic evidence:** behavior case IDs and assertions come from `tests/conformance/password-reset.cases.json`.
- **Cross-implementation equivalence:** Python and TypeScript runs assert the same proof invariants.

## Acceptance gate (pass/fail)

**PASS** only if all 4 commands exit `0` and all expected outcomes above are observed.  
**FAIL** if any command fails, proof fields differ, or variant behavior diverges.

## Stop rule (out of scope for this demo)

- Any shared-tasks fixture or runtime work.
- Any roadmap/spec expansion beyond password-reset proof execution.
- New dependencies, new runners, or host-language code outside existing proof/test paths.
- Refactors or cleanup unrelated to the four commands above.
