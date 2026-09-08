# Password-reset MVP demo runbook (5-minute beginner path)

Run from repository root (`/home/runner/work/Orin/Orin`).

You do **not** need to read Python or TypeScript first.

This walkthrough is for a first-time viewer who wants to see why Orin matters:

- a human says what program they want,
- AI can turn that into readable Orin,
- Orin surfaces one consequential unresolved decision,
- and the proof shows stable behavior without making generated code the source of truth.

## Step 1: Read the human request

Start with this request:

> Let a person reset a password without revealing whether the account exists.

That is the novice-facing programming goal.

## Step 2: Read the Orin program

Open [`../examples/password-reset.orin`](../examples/password-reset.orin).

What to notice:

- `purpose` states the goal in plain language
- `rules` capture the required behavior and constraints
- `workflow` shows the intended operation
- `example` sections show observable outcomes
- `uncertainty: rate-limit` marks one important unresolved decision

This file is the readable program meaning. The beginner path is to inspect this file before any host-language implementation.

## Step 3: Notice the unresolved `rate-limit` decision

Open [`../tests/conformance/password-reset.model.json`](../tests/conformance/password-reset.model.json) and find:

- `account.password-reset/uncertainty/rate-limit`
- `unresolved: ["account.password-reset/uncertainty/rate-limit"]`
- no stored `compilation.status` field

This is the proof boundary: Orin does not silently guess when a consequential decision is still unresolved.
Readiness (`blocked`/`eligible`) is computed from unresolved consequential
uncertainties, not persisted as workflow metadata.

## Step 4: Run the proof commands and inspect the evidence

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

- The user can start from a plain goal instead of code.
- AI can help produce a readable Orin program the human can inspect.
- Orin keeps one consequential ambiguity visible instead of hiding it in generated code.
- The password-reset behavior is deterministic and testable.
- Different implementation strategies can vary without changing the required meaning.

## Acceptance gate (pass/fail)

**PASS** only if all 4 commands exit `0` and all expected outcomes above are observed.  
**FAIL** if any command fails, proof fields differ, or variant behavior diverges.

## Why Orin matters

Normal AI coding tends to give code first. Orin gives meaning first.

That means a novice user can still read the program, review important decisions, and keep the accepted behavior understandable even when implementations change.

## Stop rule (out of scope for this demo)

- Any shared-tasks fixture or runtime work.
- Any roadmap/spec expansion beyond password-reset proof execution.
- New dependencies, new runners, or host-language code outside existing proof/test paths.
- Refactors or cleanup unrelated to the four commands above.
