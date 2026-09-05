# Orin Docs Guide (Start Here)

This folder now has one clear flow:

1. Read [`REFOCUS-ASSESSMENT.md`](./REFOCUS-ASSESSMENT.md) first (guiding constraint).
2. Track execution in [`ORIN-0003-language-improvement-plan.md`](./ORIN-0003-language-improvement-plan.md) (source of truth for done/next).
3. Use [`IMPLEMENTATION-ROADMAP.md`](./IMPLEMENTATION-ROADMAP.md) and [`MVP-PLAN.md`](./MVP-PLAN.md) for short strategic framing.

## What has been done (current snapshot)

- Repository was refocused to a strict password-reset MVP center.
- Shared-task semantic/runtime coverage was implemented as advanced follow-up coverage.
- Tooling and execution backends were separated (`tooling/` vs `implementations/<language>/`).
- TypeScript host-language reference slice was added under `implementations/typescript/src/`.

Authoritative completion log: see the `[done]` items in
[`ORIN-0003-language-improvement-plan.md`](./ORIN-0003-language-improvement-plan.md).

## Current execution status

- **Current project scope (password-reset MVP): complete**
- **Remaining tasks in current project scope: 0**
- **Open post-MVP backlog tasks: 1**

Authoritative status and task markers are maintained in
[`ORIN-0003-language-improvement-plan.md`](./ORIN-0003-language-improvement-plan.md).

## Document roles

- **Primary guidance:** `REFOCUS-ASSESSMENT.md`
- **Primary execution tracker:** `ORIN-0003-language-improvement-plan.md`
- **Supporting strategy docs:** `IMPLEMENTATION-ROADMAP.md`, `MVP-PLAN.md`
- **Background/reference specs:** `ORIN-0001`, `ORIN-0002`, `ORIN-0004`, `ORIN-0005`, gap/integration analyses
- **Post-MVP task queue marker:** `ORIN-0003` item tagged `[post-mvp-next]`
