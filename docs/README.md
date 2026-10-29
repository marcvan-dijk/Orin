# Orin Docs Guide

Use this folder with one rule in mind: concept authority lives in
[`ORIN-0001-intent-spec.md`](./ORIN-0001-intent-spec.md), active execution
tracking lives in [`ORIN-0003-language-improvement-plan.md`](./ORIN-0003-language-improvement-plan.md),
and broader future material is kept out of the primary path.

New words: [`GLOSSARY.md`](./GLOSSARY.md) (10 simple terms).

Contributing: [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — test commands,
layout rules, and the scope rule.

## Authoritative now

- [`ORIN-0001-intent-spec.md`](./ORIN-0001-intent-spec.md) — canonical
  conceptual source for the current human/AI meaning boundary and
  decision-completion rule.
- [`../examples/password-reset.orin`](../examples/password-reset.orin) — current
  readable Orin program for the password-reset proof slice.
- [`../tests/conformance/README.md`](../tests/conformance/README.md) — exact map
  from current proof claims to existing evidence artifacts.
- [`SEMANTIC-BOUNDARY.md`](./SEMANTIC-BOUNDARY.md) — durable meaning vs.
  scaffolding/provenance boundary for the active password-reset proof.

## Execution now

- [`ONBOARDING.md`](./ONBOARDING.md) — 10-minute first-user walkthrough
  (demo video script: [`ONBOARDING-DEMO-SCRIPT.md`](./ONBOARDING-DEMO-SCRIPT.md)).
- [`PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](./PASSWORD-RESET-MVP-DEMO-RUNBOOK.md) —
  5-minute walkthrough for the current proof path.
- [`LANGUAGE-REFERENCE.md`](./LANGUAGE-REFERENCE.md) — language reference.
- [`AUTHORING-WITH-AI.md`](./AUTHORING-WITH-AI.md) — how to write Orin with an AI
  while keeping important decisions human-made.
- [`COLLABORATIVE-AUTHORING-PROTOTYPE.md`](./COLLABORATIVE-AUTHORING-PROTOTYPE.md) —
  prototype for several people authoring one program.
- [`../examples/expense-approval.orin`](../examples/expense-approval.orin) —
  supporting example (notes: [`EXAMPLE-EXPENSE-APPROVAL.md`](./EXAMPLE-EXPENSE-APPROVAL.md)).
- [`../tooling/python/orin_cli.py`](../tooling/python/orin_cli.py) — CLI:
  `check`, `readiness`, `examples`, `inspect`, `decide`.
- Code generators: [`../implementations/python/codegen/`](../implementations/python/codegen/README.md)
  and [`../implementations/typescript/src/codegen/`](../implementations/typescript/src/codegen/).
- [`../implementations/python/parity_check.py`](../implementations/python/parity_check.py) —
  checks Python and TypeScript agree on shared fixtures.
- [`../tooling/vscode-extension/`](../tooling/vscode-extension/README.md) — VS Code
  extension (supporting tooling).
- [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml) — CI.
- [`ORIN-SYNTAX-GUIDE.md`](./ORIN-SYNTAX-GUIDE.md) — concise help for reading
  the current outline syntax.
- [`../tooling/python/README.md`](../tooling/python/README.md) — offline Orin
  agent vertical slice for inspecting unresolved decisions and applying an
  explicit password-reset rate-limit choice.
- [`ORIN-0003-language-improvement-plan.md`](./ORIN-0003-language-improvement-plan.md) —
  active execution tracker and implementation log.
- [`ORIN-0006-next-evolution-roadmap.md`](./ORIN-0006-next-evolution-roadmap.md) —
  active post-MVP roadmap starting from the Track B audit outcome.

## Deferred later

- [`ORIN-0004-semantic-model.md`](./ORIN-0004-semantic-model.md) — deferred
  long-term foundational semantic specification, not current execution work.
- [`SHARED-TASKS-SEMANTIC-BOUNDARY-AUDIT.md`](./SHARED-TASKS-SEMANTIC-BOUNDARY-AUDIT.md) —
  docs-only deferred audit of retained shared-tasks fixtures/diagnostics; a
  reference artifact, not part of the current execution path.
- [`DEFERRED-EVALUATION-BACKLOG.md`](./DEFERRED-EVALUATION-BACKLOG.md) — parked
  future expansion, historical strategy, and gap-analysis material with source
  pointers.
