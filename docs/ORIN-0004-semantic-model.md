# ORIN-0004: Semantic Model

**Status:** Proposed  
**Version:** 0.1.0  
**Related specifications:** [ORIN-0001: Pairing Protocol](ORIN-0001-intent-spec.md), [ORIN-0002: Language Kernel](ORIN-0002-language-kernel.md), [ORIN-0003: Language Improvement Plan](ORIN-0003-language-improvement-plan.md)

## Purpose

ORIN-0004 defines the language-independent semantic model for Orin. It is the
meaning that every frontend must produce and every backend must consume. The
model is not a file format, parser AST, editor document, AI prompt, runtime, or
target-language representation.

A frontend MAY accept `.orin` text, structured data, conversation, diagrams, or
another input. It is conforming only when it produces an equivalent semantic
model. A backend MAY produce code, configuration, tests, infrastructure, or a
reference execution, but it must preserve the model's accepted claims.

## Design constraints

The model MUST:

- Represent intent without requiring a target language.
- Give every semantic object a stable identity.
- Distinguish facts, requirements, assumptions, proposals, decisions, and evidence.
- Make references and affected objects inspectable.
- Represent unresolved consequential uncertainty explicitly.
- Support deterministic canonicalization and comparison.
- Preserve source and provenance information without making either semantic.

The model MUST NOT:

- Encode parser-specific syntax-tree details as language meaning.
- Treat generated artifacts as the source of intent.
- Treat a passing check as human acceptance.
- Allow a target backend to weaken a requirement silently.

## Model structure

A semantic model contains one `module` and zero or more named declarations.
Declarations form a directed graph through typed references.

Initial declaration kinds are:

```text
module
value-type
entity-type
relation
state
capability
effect
rule
workflow
example
uncertainty
target
evidence
```

The first executable slice may implement only the kinds required by the
password-reset example. Unsupported kinds must produce a diagnostic rather than
being silently discarded.

### Common object shape

Every semantic object has these fields:

```text
object {
  id: stable identity
  kind: declaration kind
  name: local display name
  status: semantic status
  claims: typed semantic properties
  references: links to other objects
  source: optional source location
  provenance: optional origin record
}
```

`source` and `provenance` explain where an object came from. They do not change
its meaning. `claims` and `references` do.

## Stable identity

An object's identity is the module-qualified declaration name plus its kind:

```text
account.password-reset/rule/reset-token-single-use
account.password-reset/workflow/request-reset
account.password-reset/example/unknown-address
```

Identity rules:

1. Identity is case-sensitive.
2. A module cannot contain two objects with the same kind and name.
3. Renaming an object creates an explicit identity migration; it is not inferred
   from position or similar text.
4. Revisions do not change object identity.
5. Anonymous parser nodes are not semantic objects.
6. References use identity, never source line or array position.

A frontend may preserve a user-provided identifier, but it must validate that
identifier and map it deterministically to the canonical identity.

## Semantic status

The model distinguishes the state of a claim from the state of a collaboration
exchange.

### Claim status

A semantic claim has exactly one primary status:

- `fact`: observed or externally supplied information.
- `requirement`: behavior or condition the result must satisfy.
- `assumption`: an unresolved premise used for reasoning.
- `derived`: produced by semantic analysis from other claims.

### Collaboration status

A proposal or decision may be attached to a claim without changing its claim
status:

- `proposed`: suggested but not authorized.
- `accepted`: explicitly authorized by the relevant authority.
- `rejected`: explicitly declined.
- `deferred`: intentionally left undecided.

ORIN-0001 owns the full lifecycle of proposals and decisions. ORIN-0004 only
stores links to those records and the resulting claim revision.

A backend MUST NOT compile a consequential `proposed`, `rejected`, or unresolved
`assumption` claim as if it were an accepted requirement.

## Core declaration semantics

### Module

A module is the boundary of one coherent purpose. It contains declarations,
context facts, imports, and module-level risks. A module has one public identity
and may reference external contracts through imports.

### Value type

A value type defines valid values with domain meaning. Primitive storage types
are implementation details. Units, normalization, and validation constraints
belong to the value type.

### Entity type

An entity type identifies things whose identity and lifecycle matter. Its state
is observable through declared states and relations.

### Relation

A relation connects named objects and declares its cardinality or meaning when
that distinction affects behavior, authorization, or generated storage.

### State

A state is an observable condition, not an implementation variable. A state may
be entered, left, or read by a workflow. State transitions must be explicit when
they affect a rule or example.

### Capability

A capability is authority to perform one or more effects. It is not a user role
label. A capability declaration must identify its owner or issuing authority,
scope, expiry, and revocation behavior when those affect safety.

### Effect

An effect crosses the model boundary to read or change external state. Examples
include reading a store, sending a message, reading time, generating
randomness, accessing a secret, or accepting user input.

Every effect must declare its required capability, inputs, outputs, data access,
failure modes, retry behavior, and verification boundary.

### Rule

A rule is a claim that constrains valid models, states, transitions, or outputs.
The initial rule categories are:

- `invariant`
- `precondition`
- `postcondition`
- `temporal`
- `authorization`
- `privacy`
- `resource`

A rule must identify the objects it constrains and the evidence that can test
it. A natural-language explanation may accompany a rule, but executable checks
must use structured claims.

### Workflow

A workflow describes observable behavior over inputs, states, effects, and
outputs. It must declare its required capabilities, preconditions, transitions,
postconditions, failure behavior, and recovery behavior where applicable.

A workflow does not imply a particular process, thread model, database, or
network protocol unless those are declared semantic constraints.

### Example

An example is an executable acceptance claim. It contains initial conditions,
inputs or events, expected observations, and optional expected state changes.
Examples must reference semantic objects rather than relying only on prose.

### Uncertainty

An uncertainty records a question or assumption whose answer may affect the
model. It must identify its authority and affected objects.

An uncertainty is consequential when resolving it could change behavior,
security, privacy, cost, data loss, authorization, or resource requirements. A
consequential unresolved uncertainty blocks compilation unless an authorized
policy explicitly permits proceeding.

### Evidence

Evidence records the result of a check or an assertion about a model or artifact.
It must identify the claim evaluated, its inputs, the responsible activity or
agent, and its status.

Evidence statuses are:

```text
pass
fail
blocked
not-applicable
```

`accepted` is not an evidence status. It is an authority decision represented by
ORIN-0001 and linked to the evidence.

## References and graph integrity

References are typed edges:

```text
references(source, target, relationship)
```

Initial relationships include:

```text
declares
imports
reads
writes
requires
authorizes
constrains
transitions-to
uses-effect
demonstrates
verifies
affects
supersedes
```

A model is invalid when:

- A reference target does not exist.
- A relationship is not permitted for the source and target kinds.
- A capability does not authorize a required effect.
- An example refers to undeclared behavior.
- A rule claims to constrain an object outside its module without an import.
- A superseded revision is used without an explicit compatibility relation.

The analyzer should report the complete affected-object path for a diagnostic.
For example, changing `rate-limit` should identify the account-abuse risk,
`request-reset` workflow, affected examples, targets, and verification checks.

## Canonicalization

Canonicalization produces a deterministic semantic representation for equality,
comparison, caching, and conformance testing.

A canonical model must:

1. Normalize identifiers according to the identity rules.
2. Normalize equivalent scalar values and declared units.
3. Sort declarations by canonical identity.
4. Sort unordered references by relationship and target identity.
5. Preserve order for workflow transitions and ordered effects.
6. Exclude source locations, formatting, comments, and non-semantic provenance
   from semantic equality.
7. Include model version and semantic statuses.

Two frontends are semantically equivalent when their canonical models are
equal. A change in source formatting alone must not create a semantic revision.

## Implementation policies

An implementation policy guides lowering without becoming part of semantic
meaning. Policies may express preferences such as low latency, simplicity,
managed services, relational persistence, or deployment to existing
infrastructure. They belong in an `implementationPolicies` section of a
structured model or an equivalent `policy implementation` block in a text
frontend.

Policies MUST NOT change requirements, rules, examples, state transitions,
effects, capabilities, or observable outputs. A backend MAY use a policy to
choose a target artifact, storage arrangement, scheduling strategy, or
deployment plan. Policy data is excluded from canonical semantic equality but
preserved for lowering and artifact provenance.

Changing only implementation policies MUST produce the same canonical semantic
model and the same example results. It MAY produce a different target plan or
generated artifact. A policy that changes behavior is a requirement and MUST be
represented as a semantic claim instead.

## Revision and change impact

A model revision is an immutable snapshot identified by its parent revision and
content digest. A new revision may add, remove, rename, or change semantic
objects, but it must preserve object identity when the object is intentionally
unchanged.

Each semantic change should produce an impact set:

```text
changed object
  -> dependent rules
  -> dependent workflows
  -> dependent examples
  -> dependent targets
  -> dependent evidence
```

A backend must invalidate or rerun evidence affected by a changed claim. Evidence
from an earlier revision cannot silently certify a later revision.

## Compilation gate

A frontend may produce a model containing unresolved assumptions. Compilation
must then evaluate the gate:

```text
if consequential unresolved uncertainty exists:
  result = blocked
else if model errors exist:
  result = fail
else:
  result = eligible
```

`eligible` means that compilation may begin. It does not mean that the resulting
artifact is verified or accepted.

The password-reset example intentionally contains a consequential unresolved
`rate-limit` uncertainty. Its initial model should therefore be valid enough for
inspection but blocked for compilation until an authorized decision resolves the
question.

## Password-reset normalization

The provisional example maps to the following semantic objects:

```text
module account.password-reset
value-type account.password-reset/email
value-type account.password-reset/reset-token
state account.password-reset/state/account-exists
state account.password-reset/state/reset-requested
state account.password-reset/state/reset-token-issued
capability account.password-reset/capability/person.request-password-reset
capability account.password-reset/capability/system.send-reset-message
rule account.password-reset/rule/reset-token-expiry
rule account.password-reset/rule/reset-token-single-use
workflow account.password-reset/workflow/request-reset
example account.password-reset/example/registered-address
example account.password-reset/example/unknown-address
uncertainty account.password-reset/uncertainty/rate-limit
evidence account.password-reset/evidence/<revision-specific-id>
```

The following relationships must be representable:

```text
request-reset requires person.request-password-reset
request-reset uses account-store
request-reset uses email-provider
request-reset constrained-by reset-token-expiry
request-reset constrained-by reset-token-single-use
registered-address demonstrates request-reset
unknown-address demonstrates request-reset
rate-limit affects request-reset
rate-limit affects account-takeover risk
blocked evidence verifies the unresolved rate-limit claim
```

The current prose guarantee that registered and unknown addresses receive the
same response remains a privacy requirement. It must be attached to a rule and
referenced by both examples before an implementation can claim verification.

## Conformance requirements

A conforming semantic implementation must demonstrate:

- Equivalent canonical output for two differently formatted inputs.
- Stable identities across a non-semantic formatting revision.
- A diagnostic for an unknown reference.
- A diagnostic for an unauthorized effect.
- A blocked compilation result for unresolved `rate-limit`.
- An impact set when `rate-limit` changes.
- Separate evidence status and human acceptance state.
- Preservation of workflow ordering where it affects observable behavior.

## Deferred semantics

The following are intentionally left for later specifications:

- Full concurrency and memory-model semantics
- Cryptographic identity and signatures
- Cross-organization authority
- Distributed transaction semantics
- Resource optimization strategy
- Profile-specific declarations
- Target-specific escape hatches
- Natural-language interpretation confidence

Those features may extend the model, but must not redefine the distinctions and
invariants established here.
