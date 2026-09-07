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

# The idea

Traditional programming usually mixes two things together:

1. **What the software should do**
2. **How the software does it**

For example, implementing a feature may require choosing:

- a programming language
- a framework
- a database
- APIs
- classes
- functions
- infrastructure
- data structures
- deployment architecture

Those decisions may be necessary to build software.

But they are not necessarily the best way to describe what the software is.

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

---

# A simple example

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

This describes important project behaviour without requiring the user to first decide:

- whether the backend uses Python or TypeScript
- which database is used
- which web framework is used
- how tokens are stored
- where the service runs

Those may be implementation decisions.

AI can choose them.

---

# But AI should not silently decide everything

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

For example:

> **Password reset rate limiting has not been defined.**
>
> How should reset requests be limited?
>
> **A.** Limit by email address  
> **B.** Limit by network origin  
> **C.** Limit by both  
> **D.** Do not rate-limit

The user decides.

That decision becomes part of the project.

It should not disappear into:

- an AI conversation
- a developer's memory
- an implementation detail

---

# The central distinction

Orin needs to distinguish between four things.

## 1. Defined project meaning

Things the user has explicitly decided.

```text
Reset links expire after 15 minutes.
```

These are part of the project and must be preserved.

---

## 2. Implementation freedom

Things that do not materially change the accepted project meaning.

```text
Which database stores reset tokens?
```

AI may choose the most appropriate implementation.

The answer might change over time without changing what the project is.

---

## 3. Unknown but inconsequential details

Some things simply do not need to be decided yet.

Orin should not force users to specify everything.

The goal is abstraction, not replacing code with an enormous specification.

---

## 4. Unknown consequential decisions

Some missing decisions change observable behaviour or important guarantees.

These should be surfaced to the user.

```text
AI detects missing project decision
        ↓
Explains why it matters
        ↓
Presents options where possible
        ↓
User decides
        ↓
Decision becomes durable project meaning
```

This distinction is central to Orin.

> **AI should be free to choose implementation details. AI should not silently invent important project meaning.**

---

# A project should outlive its implementation

Imagine a project starts with:

```text
Orin project
        ↓
AI chooses implementation
        ↓
Python service + web frontend
```

Years later:

```text
Same Orin project
        ↓
Requirements change
        ↓
AI chooses a new implementation
        ↓
Different services + different technology
```

The implementation may change completely.

The project meaning should remain understandable.

```text
                  ORIN
                    │
                    │
             Project meaning
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
Implementation A  Implementation B  Future implementation
        │           │
        └───── must satisfy ─────┘
                    │
              Project meaning
```

The goal is not that every implementation looks the same.

The goal is that implementations remain accountable to what the project means.

---

# Orin and AI

Orin is not intended to compete with AI coding assistants.

AI is fundamental to the vision.

The intended relationship is:

```text
Human
  │
  │ describes what they want
  ▼
AI
  │
  │ helps clarify and identify
  │ important missing decisions
  ▼
ORIN
  │
  │ preserves accepted project meaning
  ▼
AI
  │
  │ chooses and creates an appropriate
  │ implementation
  ▼
WORKING SOFTWARE
```

AI may become increasingly capable of:

- generating code
- choosing architectures
- selecting technologies
- changing frameworks
- replacing implementations
- maintaining infrastructure

Orin explores what should remain stable while those things change.

---

# Start here

You do not need to understand the Python or TypeScript implementation to understand the idea.

Start with the password reset example:

1. Read the human request:

   > Let a person reset a password without revealing whether the account exists.

2. Open:

   [`examples/password-reset.orin`](examples/password-reset.orin)

3. Notice the behaviour and rules.

4. Notice the unresolved consequential decision.

5. Follow the walkthrough:

   [`docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](docs/PASSWORD-RESET-MVP-DEMO-RUNBOOK.md)

The current example is intentionally small.

The purpose is not to demonstrate a complete application.

The purpose is to demonstrate the core interaction:

> **Define what is known. Identify what important decision is missing. Do not silently guess.**

---

# What Orin is

Orin is an experiment in creating a durable, implementation-independent representation of a software project.

It aims to preserve things such as:

- purpose
- behaviour
- rules
- constraints
- concepts
- relationships
- workflows
- guarantees
- important decisions

The long-term question is whether these things can become the primary representation through which humans understand and evolve software.

---

# What Orin is not

Orin is **not** currently intended to be:

- a replacement syntax for Python or TypeScript
- a prompt wrapper around an AI coding assistant
- a low-code application builder
- a tool primarily for analysing existing codebases
- a system where generated code becomes the only source of truth

Orin does not assume that humans should manually define every implementation detail.

Quite the opposite.

The experiment is whether humans can increasingly focus on:

> **What must be true about the software?**

while AI increasingly handles:

> **How should this be implemented?**

---

# The current experiment

Orin is still early.

The current work focuses on proving the idea with small examples.

The project currently explores a flow similar to:

```text
Human request
        ↓
Readable Orin definition
        ↓
Semantic model
        ↓
Validation
        ↓
Identify missing consequential decisions
        ↓
Accepted project meaning
        ↓
Implementation
        ↓
Observable behaviour
```

The current password-reset example is the primary proof.

The goal is not yet to design a complete programming language or application platform.

The goal is to discover:

> **What is the smallest useful representation of a software project that can preserve its meaning independently from its implementation?**

---

# Design principles

## Meaning before implementation

The project should first be understandable in terms of what it does and what must remain true.

Implementation is secondary.

---

## Important decisions should be durable

If a decision materially affects the project, it should not be lost in conversation history or hidden inside generated code.

Once accepted, it should become part of the project's durable representation.

---

## AI assists; humans remain responsible for project meaning

AI can suggest, clarify and implement.

But consequential project decisions should be visible to the human.

---

## Not everything must be specified

Orin should not become a giant specification language.

Implementation freedom is valuable.

The goal is to record what matters while leaving AI free to decide what does not.

---

## The implementation is replaceable

Programming languages, frameworks and architectures may change.

The project meaning should remain.

---

## Internal complexity should not become user complexity

Orin may require sophisticated semantic models, validation and verification internally.

That does not mean users should have to understand those mechanisms.

The user experience should remain focused on defining and understanding the project.

---

# Repository structure

The repository separates implementations from tooling:

```text
implementations/
    Host-language implementations and execution backends

tooling/
    Authoring, inspection and analysis tools

docs/
    Specifications, design decisions and project documentation

examples/
    Human-readable Orin examples

tests/
    Conformance and behavioural verification
```

The structure is intended to reinforce an important architectural principle:

> **Tools help humans and AI work with the project. Implementations realise the project. Neither should become the definition of what the project means.**

---

# Current status

⚠️ **Experimental**

Orin is actively evolving.

The syntax, semantic model, architecture and implementation approach are not stable.

Breaking changes are expected.

The project is currently more interested in proving a useful idea than pretending the final design is already known.

---

# Why this project exists

The question behind Orin is:

> **If AI increasingly writes the implementation, what should humans program?**

One possible answer is:

> **Humans should increasingly define what software means.**

Not every implementation detail.

Not every line of code.

But the purpose, behaviour, rules and important decisions that make the project what it is.

Orin is an attempt to explore whether that can become a useful way to build software.

---

# Contributing

Orin is exploratory, and criticism is welcome.

The most useful feedback is not necessarily:

> "You should add feature X."

More interesting questions are:

- Is this representation actually easier to understand than code?
- Which decisions belong in project meaning?
- Which decisions should remain implementation freedom?
- When should AI ask the user instead of deciding?
- Can important project knowledge remain useful after the implementation changes?
- Would you want AI-assisted development to preserve this kind of project memory?

If you have thoughts, ideas or criticism, they are welcome.

---

# The short version

```text
Humans describe what software should do.

AI helps find important things that have not been decided.

Humans make consequential decisions.

Orin records what the project means.

AI chooses how best to implement it.

The implementation can change.

The project meaning remains.
```

> **That's the experiment.**
