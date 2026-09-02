# Orin

Orin is an experimental programming language for describing **what software
must do**. AI can help turn that description into a precise model, and a
compiler can later choose how to build it.

## Why Orin?

With ordinary programming, a developer often decides behavior and
implementation at the same time:

```text
Create a database table, call this API, retry three times, then return JSON.
```

Orin starts with the meaning instead:

```orin
goal "People can reset their password without revealing whether an account exists."

rule privacy:
   registered and unknown addresses receive the same response

workflow request-reset:
   when a person requests a reset
   then send a message only for a registered address
   always return the standard confirmation
```

The implementation details can be chosen later, as long as the generated
system preserves the goal and rule.

## AI-assisted authoring

People should not need to learn every Orin keyword before they can begin. A
developer can start with a sentence, and the AI can ask small, reviewable
questions:

```text
What should happen when email delivery is unavailable?

1. Return the standard confirmation and reveal nothing.
2. Show a delivery error.
3. Defer the decision.
```

The developer can choose, edit, reject, defer, or ask for an explanation. The
AI proposes changes; only an accepted choice changes the Orin model.

## Intent and implementation

The developer can also give lowering preferences without turning them into
application behavior:

```orin
policy implementation:
   optimize-for "low-latency"
   prefer "managed-services"
   deploy-to "existing-infrastructure"
```

Changing these preferences may change the generated database, services, or
deployment files. It must not change the rules, workflow results, permissions,
or other semantic behavior.

## Current state

Orin is a prototype, not yet a complete application generator. The repository
currently includes:

- a language-independent semantic model;
- a provisional `.orin` parser;
- deterministic password-reset runtime experiments;
- conformance fixtures;
- policy and guided-question examples;
- a Python reference implementation kept under `implementations/python/`.

The next major steps are a complete readiness checker, an executable
intermediate representation, progressive authoring tools, and one end-to-end
generated application.

## Project documents

- [Primary programming gap analysis](docs/ORIN-PRIMARY-PROGRAMMING-GAP-ANALYSIS.md)
- [Language kernel](docs/ORIN-0002-language-kernel.md)
- [Semantic model](docs/ORIN-0004-semantic-model.md)
- [Implementation plan](docs/ORIN-0003-language-improvement-plan.md)
- [Conformance fixtures](tests/conformance/README.md)

Orin's long-term goal is simple: define a new software system primarily in
terms of its purpose, behavior, constraints, and intent, then let suitable
implementations be generated from that meaning.
