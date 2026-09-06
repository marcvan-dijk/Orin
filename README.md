# Orin

> **What if humans programmed what software means, while AI handled more of how it is built?**

Orin is an experiment in a new way of programming software.

Instead of making source code the primary way humans define a program, Orin explores whether humans can define **what software should do**, while AI and implementations handle more of **how it is built**.

The goal is not to replace programming with prompts.

The goal is to create a durable, human-understandable definition of software that can remain stable even when its implementation changes.

---

## Why Orin exists

Software is becoming increasingly complex.

At the same time, AI is becoming increasingly capable of generating and modifying source code.

That creates a challenge:

```text
Human
  ↓
AI
  ↓
Thousands of lines of generated code
  ↓
Human tries to understand and maintain it
```

If AI can increasingly handle implementation, asking humans to understand every implementation detail may eventually become the wrong abstraction.

Orin explores a different model:

```text
Human
  ↓
Describe what the software should do
  ↓
AI helps clarify and refine it
  ↓
Orin captures the program's meaning
  ↓
Implementation is generated
```

The human-readable definition remains the primary representation of the software.

Generated source code becomes an implementation detail.

---

## The core idea

Traditional programming usually mixes together two things:

1. **What the software should do**
2. **How the software should do it**

For example, a developer might need to think about:

* data structures
* APIs
* databases
* frameworks
* functions
* classes
* control flow
* infrastructure

Those things are often necessary to implement software.

But they are not necessarily the best way for a human to describe what the software is supposed to mean.

Orin explores separating these concerns.

Instead of starting with implementation, a program should be able to express things such as:

> Users can reset their password.

> A reset link expires after 15 minutes.

> Never reveal whether an email address belongs to an account.

> A user must not be able to use an expired reset link.

These statements describe **behaviour, rules and constraints**.

Orin's job is to turn those definitions into something precise enough to execute and implement.

---

## What this means in practice

Imagine defining a password reset system.

The important behaviour might be:

```text
A user can request a password reset.

If the account exists, a reset link can be created.

The system must not reveal whether an account exists.

A reset link expires after 15 minutes.

An expired link cannot be used.

A successful reset invalidates the link.
```

The goal is for Orin to capture the meaning of these rules.

AI can help ask questions when something important is unclear.

For example:

> Should reset requests be rate-limited?

Rate limiting means slowing down or blocking repeated requests to reduce abuse.
That choice matters because it affects user experience and safety.
Orin should not silently guess.

The human makes the decision.

The resulting meaning becomes part of the program.

---

## The vision

The long-term idea behind Orin is:

```text
Human expresses what they want
            ↓
AI helps clarify ambiguity
            ↓
Important decisions are made explicit
            ↓
Orin captures the resulting program meaning
            ↓
The program has deterministic meaning
            ↓
AI / implementations build the software
```

The important part is that AI should not simply generate code and leave the human with the result.

The meaning of the program should remain available as something humans can understand, inspect and change.

Later, the implementation may change:

```text
                 Orin program
                      │
                      │
              defines meaning
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
    Implementation A       Implementation B
          ↓                       ↓
      Same program meaning and behaviour
```

The implementation is replaceable.

The program's meaning is not.

---

## Orin is not

Orin is **not**:

* A prompt wrapper around an AI coding assistant
* A tool for analysing existing codebases
* A replacement syntax for TypeScript, Python or another language
* A low-code UI builder
* A system where an AI's generated source code becomes the only source of truth

AI-generated code can be an implementation.

Orin explores whether the **program itself can exist at a higher level than that implementation**.

---

## Start here: the 5-minute beginner demo

You do **not** need to read Python or TypeScript first.

If you want to understand Orin as a novice, follow this path:

1. Start with the human request: "Let a person reset a password without revealing whether the account exists."
2. Open the readable Orin program: [`examples/password-reset.orin`](examples/password-reset.orin).
3. Notice the unresolved question about rate limiting.
4. Run the short walkthrough: [`docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md).

This is the core claim: AI can help write the Orin program, but the human can still read it, inspect it, and approve the important decisions before implementation takes over.

---

## Current status

Orin is currently an **early experimental project**.

The current work focuses on proving the central hypothesis with a small example.

The current proof is roughly:

```text
Program definition
        ↓
Semantic model
        ↓
Validation
        ↓
Deterministic meaning
        ↓
Executable behaviour
        ↓
Multiple implementations
        ↓
Equivalent observable behaviour
```

The password reset example is currently used as the primary proof.

The goal is not yet to build a complete general-purpose programming language.

The goal is to discover the smallest useful foundation needed to prove the idea.

## Password-reset MVP proof quickstart

Run from repository root (`/home/runner/work/Orin/Orin`).

### Beginner path

1. Read the human request in this README: password reset without revealing whether the account exists.
2. Open [`examples/password-reset.orin`](examples/password-reset.orin). This readable Orin file is the program meaning the human reviews.
3. Notice the unresolved question in that file and in [`tests/conformance/password-reset.model.json`](tests/conformance/password-reset.model.json).
4. Follow the short walkthrough in [`docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md).

Minimal proof check:

```bash
python implementations/python/password_reset_proof.py
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
```

Full demo gate command sequence:

```bash
python implementations/python/password_reset_proof.py
python implementations/python/test_orin_model.py PasswordResetProofRunTests.test_password_reset_end_to_end_derivation_proof
node --experimental-strip-types implementations/typescript/src/password_reset_proof.ts
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
```

How to inspect evidence quickly:

- Readable program meaning: `examples/password-reset.orin`.
- Claim-to-artifact checklist: `tests/conformance/README.md` (`Demo Evidence Checklist`).
- Full executable runbook and pass/fail gate: `docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`.
- Decision-completion protocol context: `docs/ORIN-0001-intent-spec.md`.
- Completion log and exact next step tracker: `docs/ORIN-0003-language-improvement-plan.md`.

---

# A readable Orin syntax

Orin currently uses a readable outline style for authoring.

See the full guide here:

[`docs/ORIN-SYNTAX-GUIDE.md`](docs/ORIN-SYNTAX-GUIDE.md)

Short version:

```text
module: password-reset

purpose:
  Reset passwords safely.

rules:
  - Do not reveal whether an email exists.
  - Reset links expire after 15 minutes.
  - Reset links can only be used once.

workflow: request-reset
  input:
    email
  steps:
    check account
    create token if allowed
    send reset message if allowed
    return same response
```

---

# Design principles

## Meaning before implementation

The program should primarily describe what software means, not how a particular technology implements it.

## AI assists; meaning remains explicit

AI can help interpret, refine and build a program.

Important decisions should ultimately become part of the program's defined meaning rather than remaining hidden inside a chat conversation.

## Ambiguity matters

Not every detail needs to be specified immediately.

But if an unresolved decision changes observable behaviour, it should be surfaced.

Orin should not silently invent important semantics.

## Internal complexity is acceptable

The implementation of Orin may require sophisticated semantic models, validation and execution machinery.

That does not mean those concepts should automatically become part of the primary user experience.

Complexity should exist where it provides value.

## The implementation is replaceable

A program's meaning should not depend on one generated codebase.

Different implementations should be able to represent the same accepted Orin program.

---

# An experiment

Orin does not claim to have solved the future of programming.

It is an experiment based on a question:

> **If AI increasingly writes the implementation, what should humans program?**

My hypothesis is that humans will increasingly need a higher-level representation of software — one that allows them to define, understand and evolve what a program does without requiring the implementation to be the only thing they can read.

Orin is an attempt to explore that hypothesis.

---

# Project status

⚠️ **Experimental**

The language, semantic model and architecture are actively evolving.

The current focus is on proving the core idea rather than building a complete ecosystem.

Expect breaking changes and incomplete functionality.

---

# Repository structure

Orin keeps **execution implementations** and **authoring/analysis tooling** separate:

- `implementations/` contains host-language backends that execute or generate artifacts from the same Orin semantic meaning.
- `tooling/` contains authoring, inspection, and analysis tools that operate on that same meaning.

This means multiple tools can help author and review one Orin program, while multiple implementations can execute that same program meaning.

---

# Contributing

Orin is still in an exploratory stage.

Feedback is particularly valuable around the central question:

> **What should a human-readable program look like when AI handles increasingly more of the implementation?**

Ideas, criticism and experiments are welcome.

---

## The short version

```text
Humans define what software should do.

AI helps make that definition precise.

Orin captures what the program means.

Implementations are generated from that meaning.

Humans continue to understand and evolve the software
through the program's meaning rather than its implementation.
```

**That's the experiment.**
