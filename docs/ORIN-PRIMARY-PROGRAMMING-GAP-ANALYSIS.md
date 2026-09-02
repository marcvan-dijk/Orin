# Orin Primary Programming Gap Analysis

**Status:** Current-state review  
**Date:** 2026-09-02  
**Scope:** Making Orin capable of defining and producing a complete new software application

## Executive conclusion

Orin is not yet a primary programming language for new applications. It is a
language-neutral semantic-model experiment with one password-reset vertical
slice. The repository demonstrates useful foundations:

- a stated separation between intent and generated implementation;
- stable semantic object identities and canonical comparison;
- explicit capabilities, effects, rules, workflows, examples, uncertainties,
  and evidence as design goals;
- a deterministic password-reset reference runtime;
- implementation policies that can alter a lowering plan without altering the
  canonical semantic model.

The central blocker is not syntax breadth. Orin lacks a complete, deterministic
semantic contract for an application and lacks a production path from that
contract to a runnable artifact. A developer can describe fragments of intent,
but cannot yet define all required application behavior, receive a complete
account of missing decisions, execute a general model, or generate and run a
new application primarily from Orin.

The highest-priority work is therefore:

1. make semantic completeness calculable;
2. make progressive refinement update one durable model;
3. define a deterministic executable intermediate representation;
4. add one complete application profile, initially web/service;
5. generate, verify, and run one application without hand-written target code.

## Current implementation boundary

The repository currently contains:

- ORIN-0001, a proposal for human-AI collaboration and acceptance;
- ORIN-0002, a proposal for the language kernel and compilation model;
- ORIN-0003, an implementation roadmap;
- ORIN-0004, a proposal for the language-independent semantic model;
- a provisional `examples/password-reset.orin` text file;
- language-neutral JSON fixtures under `tests/conformance/`;
- an optional Python implementation under `implementations/python/`.

The Python implementation currently provides:

- JSON model loading;
- canonicalization of declarations and unordered references;
- identity and dangling-reference checks;
- blocking for unresolved consequential uncertainty;
- a small line-oriented `.orin` parser;
- deterministic password-reset effects and token lifecycle behavior;
- a policy-aware lowering-plan experiment.

It does not yet provide a general compiler, complete semantic analyzer,
application profile, generated target artifact, deployment adapter, or running
application generated from Orin.

## Prioritized gaps

### P0: No complete application semantic contract

A developer cannot currently describe an application as a complete system. The
model names types, states, capabilities, effects, rules, workflows, examples,
and targets, but their required fields and legal relationships are not fully
defined or enforced.

Missing semantic contracts include:

- entities, fields, identifiers, lifecycle, and persistence meaning;
- relations, cardinality, ownership, and deletion behavior;
- complete inputs, outputs, errors, retries, timeouts, cancellation, and
  compensation;
- state transitions and transition guards;
- effect inputs, outputs, failure modes, data access, and authority;
- user-facing surfaces such as routes, forms, commands, views, and responses;
- sessions, identity, authentication, authorization, and secrets;
- data retention, migrations, transactions, consistency, and concurrency;
- operational requirements such as logging, metrics, health, backups, and
  recovery;
- non-functional requirements with measurable units and acceptance thresholds.

The existing fixture demonstrates that a workflow can be named, but not that a
complete application can be derived from it. The current validator does not
check relationship legality, type validity, state graphs, effect declarations,
workflow completeness, or capability authorization despite those being required
by ORIN-0004.

**Required outcome:** define a versioned completeness schema. The analyzer must
report missing information as structured diagnostics linked to affected objects,
with distinctions between required decisions, optional defaults, unresolved
assumptions, and implementation preferences.

### P0: No completeness or decision-discovery engine

Orin can block the known unresolved `rate-limit` uncertainty, but it cannot
determine what else must be decided before implementation. There is no
requirement matrix or dependency-driven question system.

For a new application, Orin must be able to answer:

- Which behavior is underspecified?
- Which information is required to compile?
- Which assumptions affect safety, privacy, cost, or operability?
- Which defaults are permitted and who authorized them?
- Which decisions affect only lowering?
- Which examples or generated artifacts become invalid when a decision changes?

The current `uncertainty` object is a useful seed, but it has no general
resolution lifecycle, typed alternatives, decision value, authority check, or
impact computation in the implementation.

**Required outcome:** add a semantic readiness analysis that produces a stable
set of blocking questions and affected-object paths. Readiness must be
reproducible from the model and declared policies, without asking an AI to
reinterpret the program.

### P0: No executable intermediate representation

The current path stops at a model and a narrow Python experiment. There is no
fully specified intermediate representation for application execution. The
password-reset runtime is hand-written Python behavior, not a lowering of a
general workflow representation.

Consequences:

- workflow meaning is partly embedded in host-language code;
- other backends have no authoritative execution contract;
- generated artifacts cannot be compared against a shared operational meaning;
- error and recovery behavior cannot be reproduced generally.

**Required outcome:** define an executable IR with explicit values, state,
transitions, pure operations, effects, capabilities, errors, time, retries,
and observable outputs. The reference interpreter must execute this IR rather
than contain workflow-specific semantics.

### P0: No path to a complete generated application

The documented compilation pipeline is:

```text
Orin intent -> semantic model -> verified IR -> target plan -> target artifact -> evidence
```

The implementation currently reaches only a partial semantic model and a
hand-authored reference runtime. There is no generated source tree, dependency
manifest, schema migration, infrastructure definition, test bundle, packaging,
or process that starts the result.

A developer therefore cannot do the essential programming loop:

```text
write Orin -> compile -> run application -> observe behavior -> refine Orin
```

**Required outcome:** choose one initial application target and implement an
end-to-end generator, preferably a small web/service application with a local
runtime, persistent store, and testable external effects. The generated result
must be runnable from a clean checkout using documented host tooling that stays
outside the language-neutral fixtures.

### P1: Progressive formalisation is specified but not implemented

ORIN-0002 describes conversation, guided, and direct authoring as equivalent
views of one model. The repository implements none of these authoring flows.
The `.orin` parser accepts only a narrow direct syntax and has no semantic patch
or revision mechanism.

There is currently no way to:

- begin with a natural-language goal;
- convert that goal into a reviewable structured proposal;
- accept, edit, reject, or defer one semantic change;
- preserve the accepted model while adding later constraints;
- show the next missing decision based on model dependencies;
- prove that conversation mode and direct mode produce the same canonical model.

The language must not solve this by making natural language itself the runtime
semantics. Natural language should produce explicit proposals or questions;
accepted structured claims must become the executable source.

Bounded decisions should be offered as multiple-choice questions when that is
clearer than asking the developer to write formal syntax. Each option must show
its semantic or lowering effect, affected objects, tradeoffs, and whether it
blocks readiness. Choosing an option is still a reviewable proposal; only an
accepted option updates the durable model.

**Required outcome:** implement a deterministic semantic patch format and a
small guided authoring loop. AI may propose text or claims, but only accepted
patches alter the model. Add conformance tests for incremental refinement and
rejection without model loss.

### P1: Determinism exists only in a narrow slice

Canonicalization and the password-reset adapters are deterministic, which is a
useful proof point. Determinism is not yet a property of Orin programs as a
whole:

- parser coverage is incomplete;
- semantic validation is incomplete;
- policy validation is absent;
- no executable IR exists;
- no general interpreter exists;
- no artifact generation is reproducible;
- no model revision digest or dependency lock is implemented;
- AI interpretation is still required at the natural-language boundary;
- time, randomness, storage, and external effects have no general deterministic
  adapter contract.

**Required outcome:** once accepted, a model must compile from canonical model
plus explicit toolchain, target, policy, and adapter versions. The compiler
must not consult an AI to determine meaning. AI can propose changes before
acceptance and explain results after compilation, but execution must use the
accepted model and deterministic IR.

### P1: Intent versus implementation needs a typed policy boundary

The new `implementationPolicies` experiment is directionally correct. The
policy variants compare equal semantically and produce different lowering
plans. That proves the intended distinction in one case, but the boundary is
not yet enforceable generally.

Remaining issues:

- there is no policy schema or validation of allowed keys and values;
- there is no test that a policy cannot alter a rule, effect, capability, state,
  or example result;
- `require relational persistence` can be either a semantic constraint or a
  lowering preference, but the model has no explicit distinction between those
  meanings;
- target plans are simple dictionaries, not real backend decisions;
- generated artifacts and evidence are not compared across policy variants;
- policy conflicts, unavailable infrastructure, and unmet budgets have no
  deterministic result.

**Required outcome:** classify declarations as semantic requirements, budgets,
or lowering policies. A policy may select among implementations that satisfy
requirements. If a developer truly requires relational persistence as behavior
or a compatibility constraint, that requirement must be represented separately
from a preference for a relational implementation. Compilation must fail when a
policy cannot be satisfied rather than silently changing meaning.

### P1: No application profile or user-facing system model

ORIN-0002 proposes web and other profiles, but none is implemented. The current
password-reset example describes a backend workflow only. It cannot define a
complete application boundary containing users, screens, routes, input
validation, responses, sessions, accessibility, configuration, or deployment.

**Required outcome:** implement one profile by lowering it into the kernel. A
small web/service profile should cover application, route, form or command,
workflow invocation, response, identity, persistence, configuration, and
health. Every profile construct must map to kernel objects and remain subject to
the same rules and evidence.

### P1: Verification and evidence are planned, not operational

Examples currently assert a few outcomes, and tests execute Python behavior, but
there is no general evidence record tied to a model revision, claim, inputs,
tool versions, environment, artifact, and result. There is also no distinction
in the implementation between a passing example and a verified generated
artifact.

**Required outcome:** make examples executable against the IR and generated
application. Emit reproducible evidence with statuses `pass`, `fail`, `blocked`,
or `not-applicable`. Compilation must never turn human acceptance into check
success.

### P2: Revision, impact, and change safety are absent

The specifications require stable identity and affected-object paths, but the
implementation has no immutable revision, content digest, semantic diff, or
impact graph. A developer cannot safely change one requirement and know which
workflows, examples, artifacts, and evidence must be rerun.

**Required outcome:** add model revisions, semantic patches, canonical digests,
impact analysis, and evidence invalidation. This is necessary for progressive
formalisation and for keeping generated applications aligned with Orin source.

### P2: External contracts and deployment are absent

Imports are currently preserved as names, not contracts. Effects do not carry
implemented schemas or adapters. Targets do not describe a supported runtime,
configuration, infrastructure, or deployment operation.

**Required outcome:** define versioned contracts for external effects and one
local deployment target first. Add explicit configuration/secrets boundaries,
health checks, migration handling, and a reproducible run command.

## Answers to the five questions

### 1. Semantic completeness

**Current answer: No.** Orin can represent one unresolved uncertainty and a
small set of declarations, but it cannot calculate all information needed to
implement a new system. The validator reports only a narrow set of structural
errors and the known consequential uncertainty.

**Acceptance bar:** given a partially defined application, Orin emits a stable,
complete readiness report with blocking decisions, allowed defaults, affected
objects, and the reason each item matters. A model is implementation-ready only
when every required semantic field and external contract is resolved.

### 2. Progressive formalisation

**Current answer: Specified, not implemented.** The documents describe a good
three-mode workflow, but the repository has no conversation/guided frontend,
semantic patch protocol, acceptance store, or equivalence tests between authoring
modes.

**Acceptance bar:** start from a plain-language goal, accept small structured
proposals, add constraints and examples incrementally, and compile the same
model that direct authoring would produce. Rejected or deferred proposals must
leave accepted behavior unchanged.

### 3. Deterministic semantics

**Current answer: Partially, for the password-reset experiment only.** Model
canonicalization, deterministic adapters, and token behavior provide a narrow
baseline. General accepted Orin models still depend on unimplemented analysis
and hand-written host behavior.

**Acceptance bar:** canonical model plus pinned compiler, IR, target, policy, and
adapter versions produces the same IR, diagnostics, artifact manifest, and
example results. No AI call may be required to determine accepted meaning.

### 4. Intent versus implementation

**Current answer: Partially demonstrated.** `implementationPolicies` are
excluded from semantic canonicalization and can change a reference lowering
plan. The distinction is not yet typed, validated, or proven on generated
applications.

**Acceptance bar:** two policy sets produce different valid artifacts and
identical canonical semantic models, observable example results, rules,
capabilities, and effect contracts. Unsatisfied policies fail compilation
without weakening semantic requirements.

### 5. Execution

**Current path:**

```text
password-reset.orin
  -> small Python line parser
  -> partial JSON-like SemanticModel
  -> narrow structural diagnostics
  -> hand-written Python password-reset runtime
```

The intended path adds IR, target planning, artifact generation, and evidence,
but those stages are not implemented. There is no generated application to
start, inspect, configure, migrate, or deploy.

**Minimum missing path:**

```text
Orin source
  -> deterministic frontend
  -> complete semantic model
  -> readiness gate
  -> executable IR
  -> verified target plan
  -> generated application, tests, schema, and deployment files
  -> local run
  -> executable examples and evidence
  -> semantic refinement
```

## Prioritized implementation roadmap

### Phase 0: Establish the primary-programming contract

1. Define the minimum complete application model and required fields.
2. Define semantic requirements, measurable budgets, assumptions, and lowering
   policies as distinct model categories.
3. Define implementation readiness states and diagnostic codes.
4. Define the executable IR boundary and preservation rules.
5. Add one complete application acceptance scenario beyond the existing isolated
   workflow, including user boundary, persistence, external effect, and run
   command.

**Exit condition:** the specification can identify exactly what is missing from
a new application definition and what an implementation is required to produce.

### Phase 1: Complete the language-neutral kernel

1. Implement schema validation for all required declaration kinds.
2. Implement typed references and legal relationship validation.
3. Implement entities, relations, fields, state transitions, effects, errors,
   capabilities, and workflow contracts.
4. Implement readiness analysis and affected-object paths.
5. Implement semantic patches, immutable revisions, canonical digests, and
   impact analysis.
6. Keep all conformance fixtures host-language neutral.

**Exit condition:** a structured model can describe a complete small service and
produce deterministic readiness diagnostics without a parser or AI.

### Phase 2: Build progressive formalisation

1. Extend the text frontend to map all supported syntax into the model.
2. Define a proposal/decision format for natural-language and guided input,
   including bounded multiple-choice questions.
3. Implement accept, edit, reject, defer, and explain as model operations.
4. Ensure every accepted proposal becomes a semantic patch with provenance.
5. Prove conversation, guided, and direct inputs converge to the same canonical
   model.

**Exit condition:** a developer can start with a goal and refine one model until
readiness is complete, without silently acquiring unreviewed behavior.

### Phase 3: Make accepted meaning executable

1. Define and version the executable IR.
2. Build a general reference interpreter with deterministic clock, randomness,
   persistence, network, and message adapters.
3. Lower workflows, state transitions, capabilities, and effects into the IR.
4. Execute examples and emit structured evidence.
5. Make unresolved required decisions block compilation; do not choose hidden
   defaults.

**Exit condition:** accepted models execute reproducibly without AI and produce
observable results and evidence.

### Phase 4: Deliver one complete application target

1. Implement a small web/service profile lowered into the kernel.
2. Add routes or commands, input validation, responses, identity, sessions,
   persistence, configuration, and health behavior.
3. Generate one runnable target application, tests, database schema/migrations,
   and local deployment configuration.
4. Support a clean local run command and an inspectable artifact manifest.
5. Verify the generated application against the same examples used by the IR.

**Exit condition:** a developer can define a small new application primarily in
Orin, run it locally, and refine the Orin source from observed acceptance cases.

### Phase 5: Prove target and policy independence

1. Add a second target plan or backend.
2. Compile two policy variants such as low-latency/managed and
   simple/portable.
3. Compare canonical semantics, IR behavior, examples, rules, and effect
   contracts.
4. Compare generated artifact manifests and record policy tradeoffs.
5. Fail deterministically when a policy conflicts with a requirement or cannot
   be satisfied.

**Exit condition:** implementation strategy can evolve without changing what the
application means.

### Phase 6: Operational completeness

1. Add versioned external contracts and adapters.
2. Add migrations, configuration, secrets boundaries, logging, metrics, health,
   backup, and recovery semantics.
3. Add revision-aware evidence invalidation and regeneration.
4. Add reproducible packaging and one deployment target.
5. Test upgrades and semantic changes as new application revisions.

**Exit condition:** Orin defines not only application behavior but the minimum
operational system needed to run and evolve it safely.

## Explicit non-goals

This roadmap does not turn Orin into an existing-code analysis, migration, or
governance product. It does not prioritize repository ingestion, reverse
engineering, code inventory, legacy modernization, or policy auditing of
pre-existing systems.

Generated target code and external services remain implementation boundaries.
They are needed to produce a new application, but they must be outputs or
explicit contracts of an Orin definition, never a second source of semantic
meaning.

## Definition of primary-programming readiness

Orin is ready to serve as a primary way to define a small new application when a
developer can:

1. state a goal in natural language or direct Orin;
2. progressively accept structured requirements, domain concepts, workflows,
   constraints, examples, and implementation policies;
3. receive deterministic diagnostics for every missing implementation-critical
   decision;
4. accept the complete semantic model and compile without AI reinterpretation;
5. run executable examples against a reference IR;
6. generate a runnable application, tests, persistence schema, configuration,
   and local deployment artifacts;
7. change lowering policies and obtain different valid artifacts with unchanged
   semantic behavior;
8. inspect reproducible evidence and refine the same Orin source.

Until these conditions are met, Orin is a promising semantic kernel prototype,
not yet a primary programming medium for new software systems.
