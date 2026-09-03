# Orin

Orin is an experiment in programming for an AI-native world.

Its core claim is simple: humans should define **program meaning** (intent, behavior, constraints, outcomes), and implementations should be generated and replaceable.

## What Orin is

- A human-readable representation of program meaning.
- A semantic model that frontends produce and backends consume.
- A way to keep behavior stable while implementation changes.
- A workflow that blocks unresolved consequential ambiguity.

## What Orin is not

- an AI code generator
- a prompt wrapper
- low-code/no-code UI
- a DSL that forces large new vocabulary
- a tool for analyzing existing codebases

## Core progression

Human expresses intent  
→ AI helps clarify intent  
→ Orin captures meaning  
→ Orin flags consequential ambiguity  
→ human decides  
→ meaning becomes deterministic  
→ compiler/AI derives implementation  
→ implementation can change without changing Orin meaning

## Beginner path (password-reset MVP)

Start here:

1. Read `examples/password-reset.orin`.
2. Inspect `tests/conformance/password-reset.model.json`.
3. Review `tests/conformance/password-reset.cases.json`.
4. Read `tests/conformance/README.md`.

Optional host-language execution proof (Python reference only):

```bash
cd implementations/python
python -m unittest test_orin_model
```

## Repository map

### Primary (user-facing)
- `examples/password-reset.orin`
- `tests/conformance/`
- `docs/MVP-PLAN.md`
- `docs/REFOCUS-ASSESSMENT.md`

### Internal and advanced
- Semantic/language specs: `docs/ORIN-0002-language-kernel.md`, `docs/ORIN-0004-semantic-model.md`
- Improvement backlog: `docs/ORIN-0003-language-improvement-plan.md`
- Shared-tasks expansion slice (advanced): `examples/shared-tasks.orin`
- VS Code extension (supporting): `implementations/typescript/vscode-extension/`
- Julius Skills integration notes (internal): `docs/SKILLS-INTEGRATION.md`

## Current MVP proof target

Orin MVP succeeds when password-reset meaning is:

- explicit,
- deterministic,
- blocked on unresolved consequential ambiguity,
- and evidenced as implementation-equivalent across targets.
