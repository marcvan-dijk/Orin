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

`shared-tasks.validation-cases.json` adds advanced model-validation checks for actor-capability authorization and persistence durability contracts.

`password-reset.structured.json` is an internal/interchange structured frontend artifact used only to prove frontend-to-model equivalence against `examples/password-reset.orin`. It is not a primary beginner authoring format.

`shared-tasks.structured.json` provides the same equivalence proof for advanced coverage only.

Host-language runners must remain under `implementations/<language>/` and consume these fixtures unchanged.
