# Orin

> **What if the durable source of a software project was its accepted meaning rather than its current implementation?**

Orin is an experiment in meaning-first software authoring for an AI-heavy world.
Humans define the project meaning that must not be lost or silently
reinterpreted. AI can then help surface missing consequential decisions and
choose how to implement the accepted result.

## Current scope

Orin's current core is intentionally narrow:

- the authoritative conceptual source is
  [`docs/ORIN-0001-intent-spec.md`](docs/ORIN-0001-intent-spec.md);
- the current proof path is the password-reset example and its deterministic
  conformance evidence;
- active execution tracking lives in
  [`docs/ORIN-0003-language-improvement-plan.md`](docs/ORIN-0003-language-improvement-plan.md);
- [`docs/ORIN-0004-semantic-model.md`](docs/ORIN-0004-semantic-model.md) is a
  deferred long-term semantic foundation, not current execution work;
- future expansion, historical strategy notes, and broader gap analyses are kept
  out of the primary path in
  [`docs/DEFERRED-EVALUATION-BACKLOG.md`](docs/DEFERRED-EVALUATION-BACKLOG.md).

Durable project meaning belongs in the authoritative spec and accepted Orin
artifacts. Broader strategy, future scope, and internal evaluation material are
retained separately for later review.

## Start here

1. Read the current conceptual source:
   [`docs/ORIN-0001-intent-spec.md`](docs/ORIN-0001-intent-spec.md)
2. Read the current readable program:
   [`examples/password-reset.orin`](examples/password-reset.orin)
3. Follow the 5-minute walkthrough:
   [`docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md)
4. Map the proof to exact artifacts:
   [`tests/conformance/README.md`](tests/conformance/README.md)
5. Use the docs index for navigation:
   [`docs/README.md`](docs/README.md)

## Repository structure

```text
docs/
    Specifications, execution notes, and deferred evaluation references

examples/
    Human-readable Orin programs

tests/
    Conformance fixtures and behavioral verification

implementations/
    Host-language reference implementations and execution backends

tooling/
    Authoring, inspection, and analysis tools
```

Implementations and tooling are replaceable. The accepted project meaning is the
thing Orin is trying to keep durable.

## Status

Orin is experimental. The current repository proves the core idea with one small
password-reset slice rather than a broad language or platform.
