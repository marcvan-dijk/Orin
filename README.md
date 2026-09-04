# Orin

> **What if humans programmed what software means, while AI handled more of how it is built?**

Orin is an experiment in a new way of programming software.

Instead of making source code the primary way humans define a program, Orin explores whether humans can define **what software should do**, while AI and implementations handle more of **how it is built**.

The goal is not to replace programming with prompts.

The goal is to create a durable, human-understandable definition of software that can remain stable even when its implementation changes.

---

## Why?

Software is becoming increasingly complex.

At the same time, AI is becoming increasingly capable of generating and modifying source code.

This creates a problem:

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

Optional host-language derivation proof run (Python reference only):

```bash
python implementations/python/password_reset_proof.py
```

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

# The core idea

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

# The vision

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

# Orin is not

Orin is **not**:

* A prompt wrapper around an AI coding assistant
* A tool for analysing existing codebases
* A replacement syntax for TypeScript, Python or another language
* A low-code UI builder
* A system where an AI's generated source code becomes the only source of truth

AI-generated code can be an implementation.

Orin explores whether the **program itself can exist at a higher level than that implementation**.

---

# A simple example

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

> Should requesting a reset always return the same response, whether or not an account exists?

That decision changes observable behaviour.

Orin should not silently guess.

The human makes the decision.

The resulting meaning becomes part of the program.

---

# Authoring is not the same as meaning

One of Orin's central ideas is that **how a program is authored should not define what the program means**.

Eventually, the same program might be created through different frontends:

```text
Conversation with AI
        │
        │
.orin source
        │
        │
Structured input
        │
        ▼
┌───────────────────────┐
│                       │
│   Orin program model  │
│                       │
│   Canonical meaning   │
│                       │
└───────────┬───────────┘
            │
            ▼
     Implementations
```

This is important for the long-term vision.

A beginner should not necessarily need to learn a large programming language before defining useful software.

An experienced developer may want more direct control.

Both should ultimately be able to describe the same underlying program.

---

# Current status

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

My hypothesis is that humans will increasingly need a higher-level representation of software — one that allows them to define, understand and evolve what a program does without requiring the implementation itself to remain the primary source of understanding.

Orin is an attempt to explore that hypothesis.

---

# Project status

⚠️ **Experimental**

The language, semantic model and architecture are actively evolving.

The current focus is on proving the core idea rather than building a complete ecosystem.

Expect breaking changes and incomplete functionality.

---

# Repository structure

Orin keeps **execution implementations** and **authoring/analysis tooling**
separate:

- `implementations/` contains host-language backends that execute or generate
  artifacts from the same Orin semantic meaning.
- `tooling/` contains authoring, inspection, and analysis tools that operate on
  that same meaning.

This means multiple tools can help author and review one Orin program, while
multiple implementations can execute that same program meaning.

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
