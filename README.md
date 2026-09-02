# Orin

### The substrate for intent‑driven, AI‑native software systems

Orin is a research project creating the next programming language for human-AI
pairing: a language where people express purpose and constraints, AI systems
help refine and transform them, and compilers produce efficient artifacts in
whatever target technology fits the job.

Modern programming languages make humans translate meaning into machine-shaped
instructions. Orin asks a different question:

**What if the source of truth is not code, but intent?**

---

## 🌐 Vision

Software today encodes _how_ things work.
Orin explores a future where humans and AI share the _why_, the _what_, and
the proof that the result is acceptable:

- **What should happen**
- **Why it should happen**
- **Constraints that must always hold**
- **Policies, permissions, and guarantees**
- **Desired system state and acceptable outcomes**

The implementation becomes a generated, optimized, verifiable artifact — not
the thing humans maintain as their primary source.

---

## 🔍 Motivation

Across decades, software development has climbed abstraction layers:

Machine Code → Assembly → Procedural → OO → High‑Level → Cloud → Declarative → ?

Orin investigates the next jump:

**Human ↔ AI ↔ Intent Language → Verified Artifact**

This shift mirrors successful intent‑driven systems:

- SQL (declare desired data)
- Terraform (declare desired infrastructure)
- Kubernetes (declare desired cluster state)
- Policy engines (declare rules)
- Formal methods (declare invariants)

Orin aims to generalize this pattern into a unified substrate.

## Why Orin Exists

In the near term, Orin should generate the most suitable programming artifact
for the job. That may mean JavaScript or TypeScript for a web application,
Python for data work, C# or Java for a service, Rust or C++ for performance,
SQL for data operations, or another established language and platform.

The human should describe the goal, domain, constraints, and acceptance
criteria. Orin and its AI tools should choose an appropriate implementation,
explain the tradeoffs, generate the artifact, and verify that it satisfies the
intent.

Over time, generated systems may become too large or specialized for humans to
understand directly. At that point, Orin becomes the durable human-facing
language: people describe what the system must achieve in Orin, while the
compiler continues to generate whatever target code is most suitable.

This gives Orin two stages:

1. **Now:** an intent and reasoning layer that produces efficient code in
   existing languages.
2. **Later:** the human-AI programming language used to describe, evolve, and
   verify systems whose generated implementations are too complex to maintain
   directly.

The generated code is an implementation. Orin remains the understandable
source of intent.

---

## 🧩 Core Ideas

Orin explores how an AI‑native specification system might unify:

- Domain models
- Business rules
- Constraints & invariants
- Security & permissions
- Performance requirements
- Workflows & processes
- Data relationships
- Integration contracts

The goal:  
A complete description of _intent_, from which implementations can be generated,
verified, audited, and continuously maintained.

---

## 🛠 What Orin Is (and Isn’t)

**Orin is:**

- A conceptual framework
- A research space
- A prototype playground
- A place to explore executable specifications and human-AI collaboration
- A foundation for future tooling, languages, and runtimes

**Orin is not:**

- A conventional programming language with one fixed runtime or target
- A framework
- A product
- A replacement for existing systems (yet)

---

## 📂 Repository Structure

```text
README.md                         Project vision and entry point
docs/ORIN-0001-intent-spec.md     Pair-programming protocol proposal
docs/ORIN-0002-language-kernel.md  Human-AI programming language proposal
docs/ORIN-0003-language-improvement-plan.md  Implementation and research roadmap
docs/ORIN-0004-semantic-model.md  Language-independent semantic model
examples/password-reset.orin      Protocol session example
tests/conformance/                 Language-neutral conformance fixtures
```

## 🚦 Where to Go Next

The next step is to define both halves of the new programming model: the
collaboration protocol and the language that gives the collaboration durable
meaning. The language must let humans and AI work on the same semantic model,
then lower that model into efficient code, configuration, tests, or other
artifacts.

Humans should not have to memorize Orin's full semantic vocabulary. They can
start with a goal in ordinary language, while AI offers small, reviewable
completions. The structured program is progressively revealed as the human
adds constraints, examples, workflows, and decisions.

The first proposed standard is [ORIN-0001: Pairing Protocol](docs/ORIN-0001-intent-spec.md).
It defines a deliberately small unit of collaboration containing:

- a human goal and its context
- the AI's interpretation and explicit uncertainties
- questions that require human authority
- proposed changes and their intended effects
- human decisions and acceptance criteria
- verification evidence tied to the resulting artifact

ORIN-0002 also defines the human-facing authoring model: conversation, guided,
and direct editing are three views of the same program, and autocomplete is a
paced proposal that never silently commits consequential behavior.

The recommended research loop is:

1. Test ORIN-0001 against real pair-programming sessions.
2. Define ORIN-0002's smallest target-independent semantic kernel.
3. Build one parser and interpreter/compiler for the kernel.
4. Lower the same intent into at least two different target technologies.
5. Compare generated efficiency and verification evidence against hand-written baselines.

Orin is intentionally not tied to one output language. Its own language is the
shared semantic workspace; target languages are compilation outputs.

The universal kernel is extended through domain profiles. A web profile can
express pages, routes, forms, sessions, APIs, data, accessibility, security,
and deployment while preserving the same human-AI workflow and compiling to
different web architectures.
