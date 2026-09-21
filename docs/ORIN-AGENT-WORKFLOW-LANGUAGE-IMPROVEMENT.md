# ORIN Agent Workflow: Language Improvement

## Decision

Use one active workflow for Orin language improvement, not multiple specialist workflows.

This repository is still in a narrow proof phase. The active tracker is `docs/ORIN-0003-language-improvement-plan.md`, and the current work should stay focused on the password-reset proof path and the durable semantic boundary.

This workflow exists to keep work disciplined without creating process overhead that expands scope before the language is proven.

## Purpose

Use this workflow for work that changes:

- Orin semantics or language meaning
- parser/analyzer behavior
- conformance fixtures
- Python or TypeScript reference behavior
- readiness, uncertainty, or diagnostic rules
- active execution docs that define the current proof path

## Core rule

Preserve durable meaning over implementation detail.

Host-language code may change, but Orin's core meaning must remain reviewable, implementation-independent, and testable.

Agents must not silently convert implementation detail into canonical project meaning.

## Required workflow

### 1. Start from the active tracker

Before making changes, read:

- `docs/ORIN-0003-language-improvement-plan.md`

Then:

- identify the exact current next step
- confirm the task belongs to the active proof path or a deferred future path
- do not broaden scope without updating the tracker

### 2. Classify the work

Classify the task as one of:

- semantic model change
- parser/analyzer change
- conformance fixture change
- Python implementation change
- TypeScript implementation change
- documentation-only change
- governance/process change

If the task spans multiple categories, keep it as one narrow increment and do not create a new workflow for each sub-area.

### 3. Protect the language boundary

Before changing code, confirm all of the following:

- `.orin` semantics remain distinct from host-language implementation details
- host implementations remain under `implementations/<language>/`
- conformance fixtures remain language-neutral under `tests/conformance/`
- implementation details do not become canonical meaning by default
- the current proof path stays centered on the password-reset MVP

### 4. Fixture-first changes when semantics change

When the language or semantic rules change, use this order:

1. update or add language-neutral conformance fixtures
2. define deterministic expected outcomes and diagnostics
3. update the affected reference implementations
4. validate the active proof path

This keeps behavior grounded in testable meaning rather than parser or runtime convenience.

### 5. Keep Python and TypeScript parity

Python and TypeScript implementations must remain behaviorally aligned for the active proof path.

If one implementation changes:

- verify whether the other must change in the same increment
- record any deliberate divergence in the tracker
- do not let parity drift silently

### 6. Stay on the narrow proof path

Use the current password-reset proof and existing conformance fixtures as the default validation path.

Do not reopen deferred work unless:

- the tracker explicitly says to do so
- the change is required to maintain the active proof
- the team intentionally approves a separate increment

### 7. Update the tracker after every increment

Every completed change should update:

- what changed
- which fixture or proof path was affected
- whether Python/TypeScript parity was preserved
- whether the change opened or closed a gap
- the exact next step

The tracker is the source of truth for project momentum.

## Required output of an agent run

Each task should produce:

- a small reviewable change set
- updated fixtures when semantics change
- implementation alignment or explicit divergence note
- proof validation for the active path
- a tracker update with the next step

## Do not do this yet

Do not create multiple workflow docs for:

- semantic model work
- parser work
- backend work
- evidence work
- web profile work
- AI proposal review
- documentation updates

unless the repository has already proven a second workflow boundary is necessary.

Until then, the default answer is: one workflow, narrow scope, tracker-first execution.

## Trigger rule

Apply this workflow whenever a task touches the Orin language, its semantics, its conformance model, or its active proof path.

Do not create new specialist workflows just because a sub-area is different.

## Success criteria

This workflow is successful if it keeps Orin work:

- meaning-focused
- implementation-independent at the semantic layer
- fixture-first when behavior changes
- parity-checked across Python and TypeScript
- easy to review and easy to explain
- intentionally not broad before the proof is mature

## Authority

This workflow complements:

- `docs/ORIN-0001-intent-spec.md`
- `docs/ORIN-0003-language-improvement-plan.md`
- `docs/SEMANTIC-BOUNDARY.md`
- `tests/conformance/README.md`

If there is a conflict, the active tracker and semantic-boundary guidance win.

## Summary

Use one disciplined workflow for Orin language improvement:

1. start from the active tracker
2. protect the semantic boundary
3. fix fixtures before implementation when semantics change
4. keep Python and TypeScript parity
5. validate the narrow proof path
6. update the tracker with the next step

That is the smallest governance structure that still keeps Orin durable, reviewable, and implementation-independent.
