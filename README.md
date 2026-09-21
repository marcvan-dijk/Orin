# Orin

> **What if the most important representation of a software project was not its source code?**

Orin is an experiment in a different way of programming software.

The idea is simple:

> **Humans define what the software is supposed to do. AI helps make important decisions explicit. Orin preserves that meaning. AI can then choose how to implement it.**

The implementation may change.

The project should not lose its meaning.

---

## The problem

Software projects contain far more knowledge than their source code.

Important information is often spread across:

- conversations
- tickets
- documentation
- architecture diagrams
- source code
- tests
- AI conversations
- decisions people made months ago
- assumptions nobody recorded

As AI increasingly generates and modifies code, this problem may become more important.

An AI can generate thousands of lines of working code.

But later, someone still needs to answer:

- What is this software supposed to do?
- Why does it behave this way?
- Which decisions were deliberate?
- Which things were left open?
- What should happen when requirements change?
- Can the implementation be replaced without changing the project itself?

Today, the answer is often:

> "Somewhere in the code, documentation, tickets and chat history."

Orin explores whether a project can instead have a durable representation of its meaning.

---

## The idea

Traditional programming usually mixes two things together:

1. **What the software should do**
2. **How the software does it**

Orin explores a separation:

```text
WHAT THE PROJECT MEANS
        ↓
       ORIN
        ↓
AI CHOOSES HOW TO IMPLEMENT IT
        ↓
CODE / INFRASTRUCTURE / UI / SERVICES
```

The implementation is a realisation of the project.

The Orin definition represents the project itself.
It preserves durable meaning, not implementation scaffolding metadata.

---

## A simple example

Imagine asking for this:

> Let a person reset their password without revealing whether the account exists.

An Orin definition might contain:

```text
purpose:
  Reset passwords safely without revealing whether an account exists.

rules:
  - Do not reveal whether an email exists.
  - Reset links expire after 15 minutes.
  - Reset links can only be used once.
```

This describes important project behaviour without first deciding:

- which language is used
- which database is used
- which web framework is used
- how tokens are stored
- where the service runs

Those may be implementation decisions.

AI can choose them.

---

## But AI should not silently decide everything

Some missing information is harmless.

Other missing information changes what the software actually does.

For example:

> Should password reset requests be rate-limited?

That decision affects behaviour and security.

Orin should not silently let AI make that decision.

Instead, the intended interaction is:

```text
User describes software
        ↓
AI helps create the Orin project
        ↓
Important decision is missing
        ↓
AI explains the decision
        ↓
AI presents understandable options
        ↓
User chooses
        ↓
Decision is recorded in Orin
```

The important distinction is:

> **AI should be free to choose implementation details. AI should not silently invent important project meaning.**

---

## Orin's boundary

Orin is not a process system.

It is not Spec Kit. It is not OpenSpec. It is not BMAD. It is not a task planner, workflow engine, prompt framework, or AI collaboration harness.

Orin is the durable layer of meaning that survives implementation churn.

It preserves:
- rules
- guarantees
- observable behavior
- accepted decisions
- domain concepts
- constraints
- consequential ambiguities

It does not prescribe:
- plans
- tasks
- implementation steps
- workflow stages
- prompts
- agent coordination
- execution tracking
- timestamps
- provenance metadata
- temporary reasoning

The test for every new concept is simple:

> If the entire implementation, language, framework, architecture, and development process were replaced, would this still need to survive?

If yes, it may belong in Orin.
If no, it belongs in a workflow tool, planning system, or implementation layer outside Orin.

Orin does not ask, "How should this be built?"
It asks, "What must remain true about this software, no matter how it is built?"

---

## Start here

You do not need to understand the Python or TypeScript implementation to
understand the idea.

1. Read the current readable program:
   [`examples/password-reset.orin`](examples/password-reset.orin)
2. Follow the 5-minute walkthrough:
   [`docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md)
3. Map the proof to exact artifacts:
   [`tests/conformance/README.md`](tests/conformance/README.md)
4. Use [`docs/ORIN-0001-intent-spec.md`](docs/ORIN-0001-intent-spec.md) for
   the detailed conceptual specification.
5. Use [`docs/README.md`](docs/README.md) for the rest of the document map.

The current example is intentionally small.

The purpose is not to demonstrate a complete application.

The purpose is to demonstrate the core interaction:

> **Define what is known. Identify what important decision is missing. Do not silently guess.**

---

## What Orin is

Orin is an experiment in creating a durable, implementation-independent representation of a software project.

It aims to preserve things such as:

- purpose
- behaviour
- rules
- constraints
- workflows
- guarantees
- important decisions

It does not require a specific internal scaffolding shape (for example
capability/effect/value-type bookkeeping) as long as the same observable meaning
and guarantees are preserved.

---

## What Orin is not

Orin is **not** currently intended to be:

- a replacement syntax for Python or TypeScript
- a prompt wrapper around an AI coding assistant
- a low-code application builder
- a system where generated code becomes the only source of truth
- a replacement for Spec Kit, OpenSpec, or another SDD/process framework
- a project-management, task-planning, or workflow-engine system
- a compliance or audit-trail system for regulated delivery processes

The experiment is whether humans can increasingly focus on:

> **What must be true about the software?**

while AI increasingly handles:

> **How should this be implemented?**

---

## The current experiment

Orin is still early.

The current repository proves the idea with one narrow password-reset slice.

The goal is not yet to design a complete programming language or application platform.

The goal is to discover:

> **What is the smallest useful representation of a software project that can preserve its meaning independently from its implementation?**

Active execution tracking lives in
[`docs/ORIN-0003-language-improvement-plan.md`](docs/ORIN-0003-language-improvement-plan.md).
Longer-term or deferred material is listed in
[`docs/DEFERRED-EVALUATION-BACKLOG.md`](docs/DEFERRED-EVALUATION-BACKLOG.md).

---

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

Implementations and tooling are replaceable. The accepted project meaning is the thing Orin is trying to keep durable.

---

## Status

Orin is experimental. Breaking changes are expected while the project tests the
core idea.
