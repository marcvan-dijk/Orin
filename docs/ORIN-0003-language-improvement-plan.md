# ORIN-0003: Language Improvement Plan

**Status:** In progress  
**Version:** 0.1.0  
**Related specifications:** [ORIN-0001: Pairing Protocol](ORIN-0001-intent-spec.md), [ORIN-0002: Language Kernel](ORIN-0002-language-kernel.md)

## Purpose

This document turns the Orin vision and language-kernel proposal into an
implementation and research roadmap. It prioritizes executable semantics over
syntax, uses the password-reset example as the first vertical slice, and keeps
human-AI collaboration reviewable at every stage.

The immediate objective is not to build a complete programming language. It is
to prove that a small Orin program can express intent, detect unresolved risk,
execute acceptance examples, produce evidence, and lower to more than one
implementation target without losing its declared behavior.

## Current assessment

The repository has a clear language thesis, a provisional example, and the
first host-language reference slice:

- ORIN-0001 defines the human-AI decision and evidence boundary.
- ORIN-0002 defines the intended semantic concepts and compilation pipeline.
- `examples/password-reset.orin` demonstrates the proposed notation.
- Conformance fixtures remain language-neutral; executable reference tests live
  under a named host-language implementation folder.
- The provisional syntax is ahead of the formal semantic model.
- Workflow, effect, failure, and verification semantics need sharper rules.

The controlling hypothesis is:

> A small, target-independent semantic kernel can express the password-reset
> workflow precisely enough for deterministic execution and equivalent output
> from two different backends.

The first discriminating check is whether registered-address, unknown-address,
expired-token, token-reuse, and delivery-failure examples can execute against a
reference model while preserving the privacy and single-use rules.

## Guiding principles

1. Define meaning before punctuation.
2. Keep protocol metadata separate from program semantics.
3. Make consequential uncertainty explicit and compilation-blocking.
4. Treat examples as executable claims, not documentation.
5. Give every semantic object a stable identity.
6. Make effects and authority visible in the model.
7. Preserve evidence through every transformation.
8. Prefer a small complete vertical slice over a broad incomplete language.
9. Add profiles only by lowering them into the universal kernel.
10. Keep generated artifacts replaceable; keep Orin intent durable.

## Scope boundary

### ORIN-0002 language responsibilities

Orin should define:

- Domain values and entities
- State and state transitions
- Relations
- Rules and invariants
- Workflows
- Capabilities and authorization
- Effects
- Examples
- Targets
- Evidence about models and artifacts

### ORIN-0001 protocol responsibilities

The pairing protocol should define:

- Human and AI roles
- Interpretations and uncertainties
- Proposals and revisions
- Decisions and delegation
- Acceptance
- Provenance of collaborative actions

The specifications should reference one another without duplicating ownership.
`purpose`, `context`, `scope`, and `risk` may remain semantic module metadata;
`proposal`, `decision`, `delegation`, and `acceptance` should primarily remain
protocol records that refer to semantic objects.

## Workstreams

### Workstream A: Semantic model

Define a canonical intermediate representation before expanding the text
syntax.

Initial model objects:

- `Module`
- `Declaration`
- `ValueType`
- `EntityType`
- `State`
- `Relation`
- `Capability`
- `Rule`
- `Workflow`
- `Effect`
- `Example`
- `Uncertainty`
- `Target`
- `Evidence`

Every object must have:

- Stable identity
- Human-readable name
- Source location when available
- Revision identifier
- Declared relationships
- Provenance
- Semantic status

The model must distinguish facts, requirements, assumptions, proposals,
decisions, and evidence. These distinctions must affect compiler behavior, not
just editor presentation.

#### Deliverables

- Semantic-model specification
- Versioned machine-readable schema
- Canonical serialization
- Identity and reference rules
- Revision and change-tracking rules
- Model comparison and canonicalization utility

#### Acceptance criteria

- Two frontends can produce the same canonical model.
- Every reference resolves to exactly one object.
- A changed object can identify affected rules, examples, artifacts, and checks.
- Unresolved consequential assumptions are distinguishable from ordinary warnings.

### Workstream B: Minimal executable kernel

Implement only the concepts needed for the first complete workflow:

1. `module`
2. `purpose`
3. `context`
4. `type`
5. `state`
6. `capability`
7. `rule`
8. `workflow`
9. `example`
10. `uncertainty`
11. `evidence`

Defer general concurrency, deployment generation, speech input, cryptographic
signing, multi-user editing, and the full set of domain profiles until this
kernel is executable.

The compiler must reject:

- Unknown references
- Duplicate identities
- Invalid state transitions
- Effects without required capabilities
- Workflows using undeclared effects
- Examples referring to nonexistent concepts
- Contradictory guarantees
- Accepted output with blocked evidence
- Compilation with unresolved consequential uncertainty

### Workstream C: Workflow semantics

Workflows are the core behavioral abstraction and need precise semantics.
Define:

- Inputs and outputs
- Preconditions and postconditions
- State reads and writes
- Effects
- Errors
- Retries
- Timeouts
- Cancellation
- Compensation
- Ordering
- Idempotency
- Authorization requirements

For `request-reset`, the reference model should represent at least:

```text
request received
  -> request normalized
  -> account lookup performed
  -> reset token conditionally created
  -> reset message conditionally sent
  -> indistinguishable response returned
```

Define behavior for:

- Existing accounts
- Unknown accounts
- Expired tokens
- Reused tokens
- Email-provider failure
- Account-store failure
- Repeated requests
- Exceeded rate limits
- Unresolved rate-limit policy

### Workstream D: Parser and semantic analyzer

Implement the provisional `.orin` frontend after the model and workflow rules
are defined.

```text
.orin text
  -> tokens
  -> syntax tree
  -> semantic model
  -> diagnostics
```

The parser should handle modules, nested blocks, named declarations, strings,
identifiers, lists, simple values, references, and attributes.

The semantic analyzer should handle name resolution, type checking, capability
checking, state-graph validation, rule linkage, workflow validation, example
validation, and uncertainty blocking.

Semantic decisions must not be hidden in parser code. This keeps structured,
conversational, and diagrammatic frontends possible later.

Diagnostics should include:

- Stable error code
- Source location
- Human explanation
- Affected semantic object
- Suggested correction when appropriate
- Severity and blocking behavior

Example:

```text
ORIN-E041 unresolved consequential uncertainty:
rate-limit affects account-abuse risk and must be decided before compilation
```

### Workstream E: Executable examples and reference interpreter

Examples are Orin's first testing language. Convert the current prose examples
into controlled, executable claims while preserving a human-readable form.

The deterministic interpreter should:

- Establish initial state
- Apply workflow inputs
- Simulate declared effects
- Produce observable outputs
- Record state transitions
- Evaluate rules
- Emit evidence
- Use fake adapters for external systems

Use deterministic adapters for the clock, token generation, account storage,
email delivery, and rate limiting. The interpreter must not call real services.

Initial examples:

- Registered address
- Unknown address
- Expired token
- Reused token
- Email-provider unavailable
- Account-store unavailable
- Repeated request
- Rate-limit decision unresolved
- Indistinguishable responses
- Capability denied

### Workstream F: Effects and capabilities

Every external effect must declare:

- Effect identity
- Inputs and outputs
- Required authority
- Data accessed
- Failure modes
- Retry behavior
- Side effects
- Verification boundary

Capabilities must model authority rather than act as descriptive comments. Define
ownership, acquisition, delegation, scope, expiry, and revocation.

The compiler and interpreter must prevent an unauthorized workflow from being
accepted or executed.

### Workstream G: Rules and verification

Split generic rules into useful categories:

- Invariant: always true
- Precondition: required before an operation
- Postcondition: true after successful completion
- Temporal rule: constrained by time
- Authorization rule: controls access
- Privacy rule: restricts disclosure
- Resource rule: controls budgets

Verification should report exactly one of:

```text
pass
fail
blocked
not-applicable
```

Each result must link to its rule or claim, model revision, inputs, tool
versions, environment, and resulting artifact. `accepted` remains a human
decision and must not be treated as a check result.

### Workstream H: Structured frontend

Add a JSON or YAML interchange frontend after the text frontend is stable. It
should support tools, snapshot tests, semantic-model exchange, and AI-generated
proposals.

Conformance test:

```text
text input       -> canonical model A
structured input -> canonical model B
assert canonicalize(A) == canonicalize(B)
```

The structured representation is an interchange format, not necessarily the
preferred human authoring experience.

### Workstream I: Multiple backends

Start with two deliberately small targets:

#### Backend 1: Reference runtime

Produces a runnable interpreter package, transition logs, example results, and
evidence records.

#### Backend 2: TypeScript service artifact

Produces typed domain structures, workflow code, effect interfaces, generated
test fixtures, and verification tests.

Both backends must satisfy the same examples and rules. Compare observable
behavior, guarantees, and measured budgets rather than generated-source shape.

### Workstream J: Web profile

Add the web profile only after the universal workflow kernel works. Initially
support:

- Application
- Page
- Route
- Form
- User action
- Server workflow
- Response
- Accessibility declaration

Lower each profile concept into kernel concepts so the profile cannot bypass
effects, capabilities, rules, or evidence.

The password-reset web slice should generate a page, form, route, standard
response, accessibility checks, security examples, and explicit integration
boundaries.

### Workstream K: Human-AI authoring

Build the pairing experience around stable semantic objects rather than whole
file rewrites.

Each AI proposal should show:

- Proposed semantic change
- Proposal type
- Affected objects
- Added or removed constraints
- New assumptions
- Affected examples
- Verification impact
- Rollback action

Support accept, edit, reject, defer, explain, and compare actions. Proposals and
decisions must remain separate from accepted program state.

### Workstream L: Provenance and evidence

Begin with local append-only records. Store:

- Program revision
- Proposal revision
- Decision actor and timestamp
- Artifact identifier or hash
- Check inputs and results
- Tool and environment versions
- Human acceptance decision

Do not introduce a graph database or signing system until the record model has
been exercised in real sessions. The record should still preserve entity,
activity, and agent relationships from ORIN-0001.

## Milestones

### Milestone 1: Semantic core

**Status:** In progress. The Python reference slice under
`implementations/python/` loads JSON, canonicalizes declaration/reference
ordering, validates identities and references, and blocks unresolved
consequential uncertainty. Its focused tests pass under Python 3.13 via the
Windows `py` launcher. The next iteration must add relationship, type, and
capability checks without moving host-language code into shared namespaces.

**Deliver:** semantic model, identity rules, references, canonical serialization,
and validation errors.

**Exit condition:** a model can be loaded, validated, compared, and serialized
without depending on the `.orin` parser.

### Milestone 2: Executable vertical slice

**Status:** In progress. The isolated Python reference runtime now models the
initial request-reset state machine and deterministic account-store and email
provider effect boundaries. The minimal `.orin` parser/analyzer now loads the
provisional password-reset source and preserves context, imports, source
locations, and the intentional rate-limit blocker. Token expiry, single-use
protection, repeated requests, and account-store failure behavior are covered
by the reference runtime. Remaining tasks are parser semantic mapping and
execution of the unresolved-rate-limit case.

**Deliver:** `.orin` parser, analyzer, password-reset state model, deterministic
interpreter, and initial executable examples.

**Exit condition:** valid examples pass, invalid examples fail, and unresolved
`rate-limit` blocks compilation.

### Milestone 3: Evidence

**Deliver:** rule checks, example results, blocked-state reporting, and local
provenance records.

**Exit condition:** every check identifies the claim it evaluates and can be
reproduced from recorded inputs and versions.

### Milestone 4: Target independence

**Deliver:** structured frontend, reference runtime backend, TypeScript backend,
and equivalence tests.

**Exit condition:** both frontends produce equivalent models and both backends
produce equivalent observable results for the first vertical slice.

### Milestone 5: Web profile

**Deliver:** page, route, form, response, accessibility checks, and generated web
artifact.

**Exit condition:** the web profile lowers to the same kernel semantics and does
not introduce an alternate programming model.

### Milestone 6: Human-AI collaboration

**Deliver:** semantic proposals, review actions, decisions, revisions, and
explanations of affected objects.

**Exit condition:** a human can accept, revise, reject, and recover from an AI
proposal without losing rationale or silently changing accepted behavior.

### Milestone 7: Research validation

**Deliver:** ten real human-AI programming sessions, findings, and a revised
specification.

**Exit condition:** the team can identify which parts of the protocol and kernel
capture important decisions and which parts add unnecessary friction.

## Immediate implementation sequence

1. [done] Specify the canonical semantic model.
2. [done] Define the initial password-reset state machine and effect boundaries
   in `implementations/python/password_reset.py`.
3. [done] Add language-level fixtures under `tests/conformance/`; keep any future
   host-language runners separate from the fixtures.
4. [in progress] Implement the semantic validator; the current Python slice covers
   identity uniqueness, reference resolution, canonical ordering, and
   consequential-uncertainty blocking. Add relationship/type/capability checks.
5. [done] Make unresolved `rate-limit` block compilation.
6. [done] Implement the minimal `.orin` parser and analyzer in the separate
   `implementations/python/` host-language folder. It parses the password-reset
   example, qualifies local references, and rejects unsupported syntax.
7. [done] Add token expiry, token reuse, repeated-request, and account-store
   failure semantics to the reference runtime.
8. [done] Expand the parser grammar for structured context, imports, effects,
   and source locations without adding host-language requirements to `.ori`.
   The parser preserves context/imports and source lines; effect declarations
   are accepted for the next semantic-linking increment.
9. [next] Model unresolved rate-limit execution as a blocked example rather
   than silently choosing a policy.
10. [next] Link parsed effects and imports to workflow references and validate
    their declared capabilities.
11. Generate evidence for passing and blocked examples.
12. Add the structured frontend and model-equivalence tests.
13. Add the second backend.
14. Revise ORIN-0001 and ORIN-0002 based on implementation findings.

## Test strategy

Tests should be layered:

### Model tests

- Identity uniqueness
- Reference resolution
- Type validity
- Dependency ordering
- Revision comparison

### Semantic tests

- Capability enforcement
- State transition validity
- Rule contradiction detection
- Uncertainty blocking
- Effect declaration requirements

### Example tests

- Happy paths
- Failure paths
- Security and privacy cases
- Temporal behavior
- Repeated and concurrent requests

### Frontend conformance tests

- Text and structured input equivalence
- Stable diagnostics
- Source-location preservation
- Round-trip canonicalization

### Backend tests

- Equivalent outputs
- Preserved constraints
- Artifact inspection
- Generated test execution
- Runtime evidence collection

### Regression tests

Every discovered semantic bug should become a permanent test before the
implementation is changed further.

## Measures of success

Technical measures:

- All first-slice examples execute deterministically.
- No unresolved consequential uncertainty compiles.
- Both backends satisfy the same observable claims.
- Every accepted artifact has linked evidence.
- Semantic changes identify affected artifacts and checks.

Human measures:

- A new user can create a small workflow without memorizing the full vocabulary.
- Users understand what the AI proposed and what it assumed.
- Users can reject a wrong proposal without damaging the accepted model.
- Users can review intent faster than equivalent generated source.
- Users can explain why an artifact was accepted.

Efficiency measures:

- Response latency
- Memory use
- Artifact size
- Runtime cost
- External calls
- Verification time

Efficiency must be measured against declared objectives. Shorter generated source
is not, by itself, an optimization success.

## Risks and mitigations

| Risk                                                                       | Mitigation                                                               |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| The kernel becomes a second general-purpose programming language too early | Keep the first implementation limited to one complete workflow.          |
| Prose remains ambiguous                                                    | Require typed declarations, explicit effects, and executable examples.   |
| Syntax decisions constrain semantics                                       | Maintain the canonical model independently from the parser.              |
| AI suggestions silently change behavior                                    | Use semantic patches, affected-object displays, and explicit acceptance. |
| Profiles bypass core guarantees                                            | Lower every profile construct into kernel objects.                       |
| Evidence becomes decorative metadata                                       | Make checks and compilation depend on evidence status.                   |
| Multiple targets drift semantically                                        | Use shared examples and cross-backend equivalence tests.                 |
| Security claims are too vague                                              | Encode privacy, authorization, temporal, and abuse cases as rules.       |
| Tooling overwhelms new users                                               | Use progressive disclosure and small reviewable proposals.               |

## Open decisions

The following decisions should be made through implementation experiments rather
than settled by abstract preference:

- JSON, YAML, or another structured interchange format
- Exact type and unit syntax
- Whether `entity` and `value` are separate type constructors
- State-machine notation and concurrency model
- Error and compensation semantics
- Canonical evidence serialization
- Identity format and revision strategy
- Which checks are static versus executable
- Target equivalence definition
- Human identity and delegated-authority representation
- Profile extension and versioning rules

## Definition of done for the first release

The first experimental release is complete when a user can:

1. Open the password-reset Orin module.
2. Understand its purpose, risks, capabilities, rules, and workflow.
3. Run executable examples without real external services.
4. See that unresolved rate limiting blocks compilation.
5. Decide the rate-limit policy and rerun compilation.
6. Inspect evidence for each accepted claim.
7. Generate two target artifacts.
8. Compare their observable results.
9. Review a semantic change as a bounded AI proposal.
10. Accept or reject that proposal without losing provenance.

At that point Orin will have demonstrated its central claim: intent can remain
the durable source while implementations, tooling, and targets evolve around
it.
