# Orin agent vertical slice

This folder contains the first offline Orin authoring/decision-support agent.

## What it does

- inspects an Orin source or semantic JSON artifact
- reports blocking consequential decisions in human-readable form
- presents deterministic decision options for the current password-reset
  `rate-limit` question and the shared-tasks non-member assignee question
- applies an explicit human choice and emits a revised semantic JSON artifact

## What it does not do

- it does **not** invent or silently resolve consequential decisions
- it does **not** orchestrate implementation work, tasks, or workflows
- it does **not** call remote models or require network access
- it does **not** extend Orin's durable meaning with workflow/provenance metadata

## Commands

From the repository root:

```bash
python -m tooling.python.orin_agent inspect examples/password-reset.orin
```

Expected result: human-readable blocked output listing the unresolved
`account.password-reset/uncertainty/rate-limit` decision and deterministic
options. Exit code `2` means blocked.

```bash
python -m tooling.python.orin_agent decide \
  tests/conformance/password-reset.model.json \
  --uncertainty account.password-reset/uncertainty/rate-limit \
  --option five-per-15m-per-address-and-origin \
  --write /tmp/password-reset.resolved.json
```

Expected result: writes a revised semantic artifact to
`/tmp/password-reset.resolved.json`, clears the unresolved blocker, and returns
exit code `4`.

### Shared-tasks decision (ORIN-0006 Phase 2.1)

```bash
python -m tooling.python.orin_agent inspect tests/conformance/shared-tasks.minimal.model.json
python -m tooling.python.orin_agent decide \
  tests/conformance/shared-tasks.minimal.model.json \
  --uncertainty shared-tasks.minimal/uncertainty/non-member-assignee-completion \
  --option membership-required \
  --write shared-tasks.resolved.json
```

The agent surfaces the unresolved question of what happens when a non-member
assignee completes a task, lists each option with impact analysis, and on an
explicit choice adds a rule and example to the revised model, then
re-validates it (`eligible`; re-inspecting the output reports ready).
Options: `membership-required`, `assignee-may-complete` (`defer` stays blocked).

## Exit codes

- `0`: ready, no blocking consequential decisions remain
- `2`: blocked by unresolved consequential decisions
- `3`: invalid input or unknown/malformed decision
- `4`: explicit decision accepted and revised semantic artifact produced

## Current boundary

This first slice is intentionally narrow:

- semantic JSON artifacts are loaded through the existing structured frontend
- `.orin` source inspection currently supports the existing password-reset
  example path and reuses the repository's structured password-reset semantic
  artifact for deterministic offline analysis
- new uncertainty families can be added by registering new decision prompts and
  semantic patch handlers without rewriting the CLI

## Orin CLI (`orin_cli`)

One entry point for novices; stdlib only.

```bash
python -m tooling.python.orin_cli check tests/conformance/shared-tasks.model.json
python -m tooling.python.orin_cli readiness examples/password-reset.orin [--json]
python -m tooling.python.orin_cli inspect examples/password-reset.orin
python -m tooling.python.orin_cli decide <file> --uncertainty <id> --option <id>
python -m tooling.python.orin_cli examples tests/conformance/shared-tasks.model.json
```

- `check` validates a `.orin` or model `.json` and lists diagnostics with IDs.
- `readiness` says READY or BLOCKED and lists the required decisions.
- `inspect` / `decide` delegate to `implementations/python/orin_agent_core.py`.
- `examples` runs the matching `tests/conformance/<name>.cases.json`, if any.

Exit codes: `0` ok/ready, `1` problems or failing examples, `2` blocked
(decisions required), `3` invalid input or usage.

Test: `python -m unittest tooling.python.test_orin_cli`
