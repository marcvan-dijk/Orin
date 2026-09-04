# Orin

Orin is an experiment in programming software by describing what it should do, rather than manually writing how it should be implemented. AI helps turn those descriptions into working software.

## Core idea

Instead of developers writing implementation code line-by-line, you write a clear description of what the software should do—its behavior, constraints, and outcomes. AI helps turn those descriptions into working implementations. The key difference: your description stays the primary representation. Generated source code becomes an implementation detail that can change without altering what the software actually does.

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
python -m unittest discover -s implementations/python -p "test_*.py"
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
