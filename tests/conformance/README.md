# Orin Conformance Fixtures

This directory contains language-neutral fixtures for proving Orin's core thesis:

- deterministic program meaning,
- explicit consequential-ambiguity gating,
- implementation-equivalence evidence.

These files are not tied to a parser, runtime, or implementation language.

## Required checks for a conforming implementation

1. Load `password-reset.model.json` as semantic meaning.
2. Report compile/readiness status as `blocked` while unresolved consequential `rate-limit` remains.
3. Execute `password-reset.cases.json` deterministically.
4. Preserve semantic identities and references.
5. Produce equivalent canonical meaning from alternative frontends.
6. Demonstrate policy/lowering variation without semantic behavior drift.

`password-reset.policies.json` provides lowering-policy variants. A conforming implementation may produce different artifact strategies, but must preserve the same canonical semantics and observable required behavior.

`authoring-choices.json` defines a language-neutral consequential question. Options are reviewable proposals; defer keeps behavior unresolved and compile blocked.

`shared-tasks.model.json` and `shared-tasks.cases.json` are an advanced/secondary slice and should not replace password-reset as the primary MVP proof path.

`shared-tasks.validation-cases.json` adds advanced model-validation checks for actor-capability authorization contracts (including missing and invalid actor bindings), persistence durability contracts, and deterministic multi-contradiction `ORIN-E046` diagnostic entries (`code`, `objectId`, `message`) ordering.

`shared-tasks.readiness-partial.model.json` is a language-neutral partial
application slice for deterministic completeness/readiness reporting. It is
used to prove stable readiness diagnostics for blocking required decisions,
optional defaults, unresolved assumptions, implementation preferences, and
affected-object paths without generating a full application artifact.

`readiness.schema.json` defines the shared readiness-schema version and category
set consumed by host implementations so completeness reporting stays aligned
across languages.

Current readiness fixture coverage includes required-decision contracts for
capability/effect/workflow plus the item-44 extension families (entity
lifecycle, effect input/output, rule evidence links, workflow
postconditions), optional defaults (relation/effect), unresolved assumptions,
and implementation-preference entries.

Item 44A extends `readiness.schema.json` with a required-decision extension
matrix and stable code allocation for:

- entity lifecycle contracts (`ORIN-R030`)
- effect input/output contracts (`ORIN-R031`, `ORIN-R032`)
- rule evidence-link contracts (`ORIN-R040`)
- workflow postcondition contracts (`ORIN-R050`)

Item 44B adds `shared-tasks.readiness-extension-cases.json` and associated
language-neutral model fixtures (`shared-tasks.readiness-extended.*.model.json`)
with deterministic readiness expectations for both complete and missing-contract
variants of each family.

`password-reset.structured.json` is an internal/interchange structured frontend artifact used only to prove frontend-to-model equivalence against `examples/password-reset.orin`. It is not a primary beginner authoring format.

`shared-tasks.structured.json` is retained as a future advanced structured artifact. The text authoring example is intentionally removed from the current MVP path.

Host-language runners must remain under `implementations/<language>/` and consume these fixtures unchanged.

The Python proof runner (`implementations/python/password_reset_proof.py`) uses these fixtures to show one end-to-end flow: unresolved ambiguity blocks readiness, resolving that ambiguity enables derivation of different implementation artifacts, and required observable behavior remains equivalent.

## Demo Evidence Checklist (password-reset MVP)

Language-neutral proof artifacts live in this folder; execution commands stay in
`implementations/<language>/`.

| MVP claim | Existing artifact(s) | Command(s) | Expected evidence |
| --- | --- | --- | --- |
| Unresolved consequential ambiguity blocks compilation. | `password-reset.model.json` (`account.password-reset/uncertainty/rate-limit`), `password-reset.cases.json` (`account.password-reset/case/unresolved-rate-limit`) | `python implementations/python/password_reset_proof.py` | JSON includes `"blockedCompilation": "blocked"`. |
| Resolving that ambiguity makes the same model eligible. | `implementations/python/password_reset_proof.py` (resolves only rate-limit uncertainty), `password-reset.model.json` | `python implementations/python/password_reset_proof.py` | JSON includes `"resolvedCompilation": "eligible"`. |
| Required observable behavior is deterministic for the MVP cases (privacy-preserving response, delivery/store failure recovery, duplicate/concurrent request handling, token expiry/reuse rejection). | `password-reset.cases.json`, `implementations/python/conformance_runner.py`, `implementations/typescript/src/conformance_runner.ts` | `node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts` | Test passes, including assertion that every non-compile case from `password-reset.cases.json` is executed and matched. |
| Lowering policy variants can change artifact strategy without changing canonical meaning or required behavior. | `password-reset.policies.json`, `implementations/python/password_reset_proof.py`, `implementations/typescript/src/password_reset_proof.ts` | `python implementations/python/password_reset_proof.py` | JSON includes `"canonicalMeaningStableAcrossVariants": true` and at least two distinct `variants[*].derivedArtifact` entries. |
