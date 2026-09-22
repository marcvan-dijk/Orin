# Orin agent vertical slice

This folder contains the first offline Orin authoring/decision-support agent.

## What it does

- inspects an Orin source or semantic JSON artifact
- reports blocking consequential decisions in human-readable form
- presents deterministic decision options for the current password-reset
  `rate-limit` question
- applies an explicit human choice and emits a revised semantic JSON artifact

## What it does not do

- it does **not** invent or silently resolve consequential decisions
- it does **not** orchestrate implementation work, tasks, or workflows
- it does **not** call remote models or require network access
- it does **not** extend Orin's durable meaning with workflow/provenance metadata

## Commands

From the repository root:

```bash
python tooling/python/orin_agent.py inspect examples/password-reset.orin
```

Expected result: human-readable blocked output listing the unresolved
`account.password-reset/uncertainty/rate-limit` decision and deterministic
options. Exit code `2` means blocked.

```bash
python tooling/python/orin_agent.py decide \
  tests/conformance/password-reset.model.json \
  --uncertainty account.password-reset/uncertainty/rate-limit \
  --option five-per-15m-per-address-and-origin \
  --write /tmp/password-reset.resolved.json
```

Expected result: writes a revised semantic artifact to
`/tmp/password-reset.resolved.json`, clears the unresolved blocker, and returns
exit code `4`.

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
