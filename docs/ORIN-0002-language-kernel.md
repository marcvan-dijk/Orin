# ORIN-0002: Language Kernel

**Status:** Proposed
**Version:** 0.1.0
**Audience:** Humans, AI systems, and compiler/tool authors

## Purpose

ORIN-0002 defines the first shape of the Orin programming language. Orin is a
language for expressing software meaning in a form that humans can review and
AI systems can transform without losing intent. In its first stage, Orin
generates suitable artifacts in established languages and platforms. In its
later stage, Orin becomes the durable human-facing source for systems whose
generated implementations are too complex to understand directly.

It is also a compilation model: the same Orin program MAY produce different
target artifacts when their observable behavior and constraints remain
satisfied.

ORIN-0001 defines how a human and AI reach decisions. ORIN-0002 defines what
they are deciding about: a typed semantic model with behavior, state, effects,
constraints, workflows, and evidence.

Orin MUST remain useful in both stages. It MUST be able to target existing
languages without requiring humans to learn those languages for every task, and
it MUST preserve enough semantic information for Orin itself to remain the
readable source when generated code grows beyond practical human comprehension.

## Core thesis

The best language for human-AI programming is neither prose nor conventional
source code alone. It is a shared semantic representation with two equal views:

- a human view that explains purpose, domain concepts, tradeoffs, and examples;
- a machine view that provides types, dependencies, effects, constraints, and
  compilation boundaries.

The views MUST refer to the same semantic objects. A comment that changes no
meaning is documentation; a statement that changes meaning MUST be represented
in the semantic model.

## Canonical program shape

Orin programs SHOULD follow a predictable module shape. This is the familiar
organization used, in different forms, by systems such as Ada packages, Java
classes, Rust modules, SQL schemas, and test-oriented specifications:

```text
module
   purpose and context
   imports and external contracts
   domain declarations
   state and relations
   capabilities and effects
   rules and invariants
   workflows and operations
   examples and acceptance
   evidence and targets
```

The order is a reading and dependency order, not a restriction on how a
compiler stores the model. A module MUST have one clear public purpose. Each
named declaration MUST have one semantic responsibility and a stable identity.

The canonical sections are:

| Section      | Answers                                                      |
| ------------ | ------------------------------------------------------------ |
| `purpose`    | Why does this module exist?                                  |
| `context`    | What facts and boundaries does it depend on?                 |
| `import`     | Which external concepts or capabilities are used?            |
| `type`       | What domain concepts exist, and what values are valid?       |
| `state`      | What observable conditions can hold?                         |
| `capability` | Who may perform which effect?                                |
| `rule`       | What must always or conditionally remain true?               |
| `workflow`   | How do events, decisions, concurrency, and recovery proceed? |
| `example`    | What observable behavior demonstrates acceptance?            |
| `target`     | Where may the model be projected, and under what budgets?    |
| `evidence`   | What proves the claims about the model or artifact?          |

Sections MAY be omitted when empty, but a declaration MUST NOT be hidden in a
free-form explanation if it changes program meaning. Human explanations MAY
appear beside declarations and SHOULD explain tradeoffs, not repeat syntax.

This gives AI systems stable navigation points: an AI can propose changing
`rule reset-token-single-use` or `workflow request-reset` without rewriting an
entire conversation. It gives humans a compact review surface: purpose and
constraints first, behavior next, proof last.

## Human-first authoring

The canonical module shape is an organizational model, not a memorization test.
New users MUST be able to begin with a plain-language goal and add structure
incrementally. The editor or AI MAY reveal the formal sections as they become
relevant.

Orin SHOULD provide three equivalent authoring modes:

1. **Conversation mode:** the human states a goal or correction in natural
   language; the AI proposes one semantic addition or question.
2. **Guided mode:** the editor presents the next useful unfinished field, such
   as an outcome, constraint, example, or risk, with a short explanation.
3. **Direct mode:** an experienced user edits the structured module directly.

All three modes MUST update the same semantic model. Switching modes MUST NOT
create a second source of truth or discard rationale, uncertainty, decisions,
or evidence.

### Pacing and autocomplete

Autocomplete in Orin is a **reviewable continuation**, not silent authorship.
For each completion, the AI MUST:

- show the proposed text or semantic change before applying it;
- identify whether it is a fact, inference, question, proposal, or decision;
- show which named objects and constraints it affects;
- offer accept, edit, reject, defer, and explain actions;
- avoid applying a consequential change merely because the cursor pauses or a
  completion is displayed.

The default completion SHOULD be the smallest useful next step, normally one
statement or one short block. The AI SHOULD prefer completing the current
thought over opening a new section, and SHOULD stop after a meaningful unit so
the human has time to think. It MAY offer larger transformations only as an
explicit, separately reviewable action.

The completion system MUST preserve a distinction between:

- **continuation:** finishing the human's current statement without adding a
  new commitment;
- **suggestion:** proposing a new behavior, constraint, or implementation;
- **question:** requesting information needed to proceed.

These MUST have visibly different presentation and semantic status. A
continuation MUST NOT smuggle in a new requirement. A suggestion MUST NOT be
treated as approved until the human accepts it.

### Guided choices

When a decision has a bounded set of meaningful alternatives, the authoring
interface SHOULD present a multiple-choice question instead of requiring the
developer to invent formal syntax. Each choice MUST show:

- the proposed semantic change or implementation policy;
- the objects and constraints it affects;
- assumptions, tradeoffs, and consequences;
- whether it blocks compilation or only changes lowering.

The developer MUST be able to choose an option, edit it, reject it, defer the
question, or request an explanation. Selecting an option is a proposal until
accepted. The accepted option becomes a semantic patch or policy record in the
same model used by direct authoring; the choice presentation is not a second
source of truth.

Example:

```text
AI question: What should happen when reset-email delivery is unavailable?

1. Return the standard confirmation and disclose nothing.
   Affects: workflow request-reset, rule response-does-not-disclose-account
2. Show a delivery error.
   Affects: workflow request-reset, example delivery-unavailable
3. Defer this decision.
   Effect: compilation remains blocked

[choose] [edit] [reject] [defer] [explain]
```

### Progressive disclosure

The human-facing view SHOULD show, in this order:

1. purpose and current goal;
2. the next unresolved question or proposed change;
3. affected constraints and examples;
4. details of types, effects, targets, and evidence on demand.

The editor SHOULD hide compiler-oriented detail until it helps a decision, but
MUST make every hidden assumption and affected semantic object discoverable.
AI explanations SHOULD use the user's domain language and SHOULD introduce a
technical term only when it adds precision.

### Learning and feedback

Orin MUST not require users to learn the entire vocabulary before producing a
valid program. The system SHOULD infer likely structure from ordinary language,
then show the smallest precise interpretation for review. Corrections SHOULD
teach the current model and MAY improve future suggestions, but MUST NOT silently
change the meaning of existing programs.

The first-use experience SHOULD measure whether a new user can complete a small
workflow, understand what the AI is proposing, and recover from a wrong
suggestion without consulting a language manual.

### Canonical interaction

The following illustrates the intended pacing. The user does not need to know
the keywords before starting:

```text
Human: I want people to reset their password without exposing whether an account exists.

AI continuation:
   purpose "Let a person recover an account without revealing whether it exists."
   [accept] [edit] [reject] [explain]

Human: accept

AI question:
   What must be true even when the email provider is unavailable?
   [answer] [defer] [show why this matters]

Human: Do not reveal whether the account exists, and do not lose the request.

AI suggestion:
   rule response-does-not-disclose-account {
      guarantee "Registered and unknown addresses receive indistinguishable responses."
   }
   Affects: workflow request-reset, example registered-address, example unknown-address
   [accept] [edit] [reject] [explain]
```

The formal module is the accumulated result of these accepted semantic steps.
The visible completion is intentionally small; the AI can still maintain the
larger model, dependency graph, and verification plan behind the editor.

## Kernel concepts

The language MUST provide these concepts without requiring a target language:

| Concept      | Purpose                                                      |
| ------------ | ------------------------------------------------------------ |
| `value`      | A typed piece of data with domain meaning                    |
| `entity`     | A thing with identity and lifecycle                          |
| `capability` | An authority to perform an effect                            |
| `state`      | Observable system condition                                  |
| `relation`   | A meaningful connection between entities                     |
| `rule`       | A condition that constrains valid behavior                   |
| `workflow`   | Ordered, concurrent, conditional, or compensating activities |
| `example`    | An executable, observable acceptance case                    |
| `effect`     | An interaction with the outside world                        |
| `evidence`   | A result supporting a claim about an artifact or behavior    |

The kernel MUST distinguish pure reasoning from effects. A compiler MUST be able
to identify where a program reads time, randomness, storage, network services,
secrets, user input, or other external state.

## Core and profiles

Orin is intended for general programming, but one universal vocabulary cannot
make every domain pleasant to use. The language therefore has a small universal
kernel plus domain profiles.

The kernel defines concepts that apply everywhere. A profile adds familiar
concepts, defaults, and checks for one domain while compiling to the same
semantic model. Profiles MUST NOT create a second programming model or weaken
kernel guarantees.

The initial profiles SHOULD include:

- **web:** pages, components, routes, forms, sessions, APIs, databases,
  browser/server boundaries, accessibility, and deployment;
- **service:** messages, jobs, retries, queues, scheduling, and observability;
- **data:** schemas, queries, transformations, lineage, and quality rules;
- **device:** sensors, actuators, timing, power, offline operation, and safety;
- **interface:** commands, events, files, protocols, and compatibility;
- **simulation:** entities, time, random variables, scenarios, and measurements.

A web profile MUST make it possible to describe at least:

```text
person -> page -> action -> workflow -> state/effect -> observable response
```

The profile SHOULD let a human say “people can reset their password” and let
the AI progressively propose the route, form, workflow, state, authorization,
error behavior, accessibility requirements, tests, and deployment plan. Each
addition remains a named semantic object that can be accepted or rejected
independently.

Profiles are convenience and domain knowledge, not target lock-in. A web module
MAY compile to a server-rendered application, a browser application with an
API, a native client, or another architecture if the declared behavior,
security, accessibility, performance, and deployment constraints are preserved.

### Web profile example

The following is illustrative rather than a new syntax requirement:

```text
web application account-recovery {
   page request-reset {
      route "/reset-password"
      accepts email
      on submit invoke request-reset
      shows standard-confirmation
   }

   workflow request-reset {
      preserves response-does-not-disclose-account
      uses account-store
      sends email through email-provider
   }

   accessibility request-reset {
      keyboard-complete
      labels-all-controls
      announces standard-confirmation
   }
}
```

The compiler decides whether `page`, `workflow`, and `accessibility` become
HTML, client code, server code, tests, infrastructure, or another artifact. The
human reviews the behavior and constraints rather than hand-maintaining every
projection.

## Human-AI design requirements

1. Every semantic object MUST have a stable identity so a human or AI can refer
   to it across revisions.
2. The language MUST preserve the distinction between fact, requirement,
   assumption, proposal, decision, and evidence.
3. An unresolved assumption that can change behavior, safety, security, privacy,
   cost, or data loss MUST be represented explicitly; compilation MUST stop or
   require an authorized policy for it.
4. The AI MAY suggest alternatives, transformations, and optimizations, but it
   MUST NOT silently change a goal, constraint, capability, or acceptance rule.
5. A human-readable explanation MUST be derivable from the semantic model, and
   the machine model MUST be inspectable from that explanation.
6. A revision MUST preserve links from changed semantics to affected artifacts,
   checks, and decisions.

## Semantics before syntax

The `.orin` notation is provisional. The language specification MUST define
meaning independently from punctuation, file format, editor, model provider, or
target runtime. A conforming frontend MAY accept text, diagrams, structured
data, speech-derived input, or another representation if it produces the same
semantic model.

The semantic model MUST support:

- domain types and explicit units rather than unexplained primitives;
- preconditions, postconditions, invariants, and temporal constraints;
- authorization and data-access boundaries;
- errors, retries, timeouts, cancellation, and compensation;
- concurrency and ordering where they affect observable behavior;
- resource budgets such as latency, memory, energy, and cost;
- versioned external contracts and compatibility rules.

## Compilation model

Compilation is a series of inspectable transformations:

```text
Orin intent
  -> semantic model
  -> verified intermediate representation
  -> target plan
  -> target artifact
  -> execution evidence
```

Each transformation MUST declare what it preserves and what it assumes. A
target backend MAY optimize representation, scheduling, storage, parallelism,
or deployment, but it MUST preserve required observable behavior and MUST NOT
weaken constraints.

When multiple implementations satisfy the same model, the compiler SHOULD choose
the one that best satisfies declared budgets and SHOULD explain the tradeoff.
Efficiency MUST be measurable against declared objectives; it MUST NOT mean
shorter generated source by default.

Implementation policies such as “optimize for low latency”, “prefer managed
services”, or “deploy to existing infrastructure” guide this choice. They are
lowering preferences, not system behavior. Changing a policy MAY change the
target plan or artifact, but MUST preserve the semantic model, acceptance
examples, rules, capabilities, effects, and observable behavior. A condition
that must hold belongs in the semantic model even when it also influences
implementation selection.

## Verification model

Verification is layered:

1. **Model checks** validate types, references, capabilities, and contradictions.
2. **Rule checks** validate invariants, policies, and resource budgets where
   static reasoning is possible.
3. **Example checks** execute observable acceptance cases.
4. **Artifact checks** inspect the generated target and its dependencies.
5. **Runtime checks** compare actual behavior and resource use with declared
   expectations.

Every check MUST report `pass`, `fail`, `blocked`, or `not-applicable`, identify
its inputs and tool versions, and link to the semantic claims it evaluates.
`accepted` is a human decision, not a synonym for `pass`.

## Target independence and escape hatches

Orin SHOULD compile to multiple targets, including existing languages and
non-code artifacts. A target-specific escape hatch MAY be used when the kernel
cannot express a required capability, but it MUST declare:

- the target and version;
- the imported effects and authority;
- the semantic claims it implements;
- the verification boundary;
- the portability and optimization cost.

An escape hatch is a consciously marked boundary, not an invitation to hide
ordinary implementation details in generated source.

## First implementation milestone

Implement the semantic kernel for one workflow with:

- two frontends: the provisional `.orin` notation and a structured form;
- one interpreter for deterministic examples;
- two backends that produce observably equivalent artifacts;
- one small web profile covering a page, route, form, and workflow;
- model, rule, example, and artifact evidence;
- a deliberate unresolved assumption that blocks compilation until decided.

The milestone succeeds only if a human can review the model faster than
equivalent conventional source and the generated artifacts meet declared
behavior and efficiency objectives.

## Open questions

- Which semantic concepts belong in the immutable kernel versus profiles?
- How should the language express uncertainty without making every statement
  probabilistic?
- Which optimization decisions should be delegated to AI, and what evidence is
  required for each risk level?
- How can multiple humans and AI systems edit one semantic model concurrently?
- Which target backends provide the strongest early proof of target independence?
