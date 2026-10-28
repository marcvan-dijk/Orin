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

### Data-driven decisions

Any model's blocking, consequential uncertainty can carry its own decision
data; password-reset and shared-tasks keep built-in fallbacks. Data is read
from the uncertainty object itself (`why_it_matters`, `affected_objects`,
`options`, optional `rule: {id, name}`) and from a sidecar file found by
convention next to the model: `<name>.decisions.json` (for
`expense-approval.model.json`, `expense-approval.decisions.json`). Inline data
wins over the sidecar, which wins over built-ins. Sidecar shape:

```json
{"decisions": {"<uncertainty-id>": {"why_it_matters": "...",
  "options": [{"id": "...", "label": "...", "impact": ["..."],
    "rule_claims": ["..."], "examples": [{"id": "...", "kind": "example"}]}]}}}
```

An option with `"compilation": "blocked"` (e.g. `defer`) keeps the decision
unresolved. A blocking uncertainty with no options is still reported as blocked
(exit `2`).

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
python -m tooling.python.orin_cli new my-app [--out dir]
python -m tooling.python.orin_cli generate model.json --decision decision.json --target python|typescript --out dir
```

- `check` validates a `.orin` or model `.json` and lists diagnostics with IDs.
- `readiness` says READY or BLOCKED and lists the required decisions.
- `inspect` / `decide` delegate to `implementations/python/orin_agent_core.py`.
- `examples` runs the matching `tests/conformance/<name>.cases.json`, if any.
- `new` writes a minimal valid `<name>.orin` (one rule, workflow, example, open uncertainty).
- `generate` shells out to `implementations/python/codegen` or `implementations/typescript/src/codegen/cli.ts` (typescript needs `node`; reports "not available" if missing). `--decision` takes an option id (as shown by `inspect`) or a `.json` file `{"option": "<id>"}` (a raw TS decision file also works), for both targets. If the model is blocked and no decision is given, the open decisions and option ids are printed and the exit code is `2`. The python target applies the option via `orin_agent_core`, writes `<model>.resolved.json` into `--out`, then generates. The typescript target translates the option to its decision JSON (password-reset options; expense-approval accepts `stay-submitted`).

Exit codes: `0` ok/ready, `1` problems or failing examples, `2` blocked
(decisions required), `3` invalid input or usage.

Test: `python -m unittest tooling.python.test_orin_cli`
