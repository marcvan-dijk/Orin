# Orin + Julius Skills (Internal Supporting Notes)

## Positioning

This document is **internal**. Julius Skills are supporting tools for AI authoring and validation loops; they are not part of Orin language semantics and not part of the beginner path.
It is listed in [`DEFERRED-EVALUATION-BACKLOG.md`](./DEFERRED-EVALUATION-BACKLOG.md)
so it stays outside the current primary path.

## Keep

Keep only usage that materially improves the AI↔Orin loop:

- clearer, shorter reviewable proposals;
- stronger internal review gates for generated artifacts;
- session-quality checks for long authoring loops.

## Do not make user-facing requirements

- No required skill setup to understand `.orin` or conformance fixtures.
- No coupling between skills and semantic meaning.
- No implication that skill integration equals product completeness.

## Minimal integration boundary

- Any skill wiring stays under host-language implementation folders.
- Semantic model, `.orin` files, and `tests/conformance/` remain language-neutral.
- If skills are unavailable, Orin semantic behavior and conformance expectations remain unchanged.

## Refocused next step

Evaluate and keep only internal integrations that measurably improve proposal quality or validation fidelity for the password-reset MVP proof loop.
