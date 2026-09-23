# Shared-Tasks Semantic Boundary Audit

**Status:** Docs-only post-MVP evaluation artifact  
**Scope boundary:** This document audits existing retained shared-tasks fixtures
and diagnostics only. It does not authorize implementation, fixture rewrites,
runtime work, parser work, tooling work, or activation of shared-tasks as
current execution.

## Audit scope and repository-state note

The current repository state is still the password-reset MVP proof path.
Shared-tasks material is retained only as deferred advanced material in
`tests/conformance/` and deferred docs such as
[`ORIN-0005-first-complete-application.md`](./ORIN-0005-first-complete-application.md)
and
[`ORIN-0005-shared-tasks-to-ORIN-0004-alignment-brief.md`](./ORIN-0005-shared-tasks-to-ORIN-0004-alignment-brief.md).
The readable shared-tasks authoring example was intentionally removed from the
current primary path.

This audit therefore asks a narrower question than ORIN-0005 asked:

> If the password-reset semantic boundary is the reference point, what is the
> smallest durable semantic slice still visible inside the existing
> shared-tasks material, and what should be demoted to implementation freedom or
> process/provenance/history?

## Classification table

| Existing shared-tasks concept | Current examples in retained material | Classification | Audit conclusion |
| --- | --- | --- | --- |
| Module/application boundary | `shared-tasks/module`, module name, application slice identity | Durable project meaning | The existence of a bounded shared-tasks application slice is part of the meaning being discussed. |
| Entity types | `person`, `task-list`, `task` entity declarations | Durable project meaning | The domain distinguishes these entities; removing them would change what the slice is about. |
| Identity fields | `fields[].identity` on entity types | Durable project meaning | Stable identity is required for observable not-found, membership, assignment, and completion behavior. |
| Value types as named reusable constraints | `person-id`, `task-id`, `task-title`, `list-name` | Consequential accepted decision | Stable typing of IDs/titles affects behavior, but the current separate declaration style is still a modeling choice that should be explicitly accepted if kept. |
| Full field schemas and mutability details | `fields[]` structure beyond identity/title/name | Consequential accepted decision | These can be semantic when they affect observable validity, but the current fixture shape carries more structure than the password-reset boundary has proven necessary. |
| Relations as durable facts | `member-of`, `assigned-to`, list ownership/containment assumptions | Durable project meaning | Membership, assignment, containment, and ownership change authorization and visible results. |
| Relation cardinality encoding style | `cardinality: "many-to-many"` / `"many-to-one"` | Consequential accepted decision | Cardinality itself can be semantic, but the exact declaration form remains a modeling choice that should not be treated as automatically canonical. |
| States as named lifecycle facts | `open`, `completed`, lifecycle terminal state | Durable project meaning | The task lifecycle is observable through examples and workflow outcomes. |
| Transition declarations | `transitions` arrays on workflows | Durable project meaning | Allowed state changes and forbidden ones affect behavior directly. |
| Workflow inputs and outputs | `inputs`, `outputs`, actor/task parameters | Durable project meaning | What a workflow consumes and returns is part of the observable contract. |
| Stable workflow failure identities | `forbidden.member-required`, `validation.task-title` in cases | Durable project meaning | Distinguishing authorization, validation, and concurrency failures changes behavior. |
| Named capabilities as separate objects | `capability/*`, `requires`, `actorCapabilities` | Implementation freedom | The durable meaning is who may do what, not that authorization must be modeled through named capability objects and binding arrays. |
| Actor binding through workflow actor slots | `actor`, `actorCapabilities[].actor` | Consequential accepted decision | Actor context is semantic, but the current binding mechanism is one possible representation, not the only durable one. |
| Effects as explicit named external objects | `effect/persistent-entity-store.write.task-state`, `uses` | Implementation freedom | Persistence matters semantically, but explicit effect-object bookkeeping is one host-facing decomposition, not core meaning by itself. |
| Persistence and durability requirements | `durability`, persistent visibility across invocations | Durable project meaning | Whether task/list changes must survive later workflows is observable and cannot be silently varied away. |
| Failure/recovery/retry metadata | `failureModes`, `retryPolicy`, `recoveryBehavior` | Implementation freedom | These are implementation-policy or operational details unless a specific retry/compensation guarantee is made observable in acceptance behavior. |
| Acceptance examples | `shared-tasks.cases.json`, example outcomes | Durable project meaning | They are the strongest evidence of required observable behavior. |
| Example bookkeeping objects | `example` objects and `demonstrates` links | Process/provenance/history | Traceability from example to workflow is useful, but the link structure itself does not change behavior. |
| Evidence and evidence links | `evidence` objects, `evidenceLinks`, `verifies` | Process/provenance/history | These record how a claim is justified; they are not themselves the claim. |
| Model/version/status/kind metadata | `modelVersion`, object `status`, object `kind` tags | Process/provenance/history | These fields describe modeling state and serialization shape rather than required application behavior. |
| Readiness diagnostics and extension codes | `ORIN-R030`..`ORIN-R050`, readiness schema categories | Process/provenance/history | These are evaluation and governance artifacts about model completeness, not shared-tasks behavior itself. |
| Validation diagnostics and extension codes | `ORIN-E037`..`ORIN-E046` | Process/provenance/history | They constrain validator output and audit visibility, not end-user workflow behavior. |
| Object IDs | `shared-tasks/...` object identifiers | Process/provenance/history | Stable references are useful for tooling and traceability, but the exact ID strings are not the application's durable meaning. |
| Affected paths | JSON pointer `path` fields in readiness entries | Process/provenance/history | These locate fields inside fixtures for tooling; they do not change shared-tasks behavior. |
| Impact areas | `impactAreas: ["cost", "operability"]` | Process/provenance/history | These are decision-review annotations, not shared-tasks semantics. |
| Traceability arrays and dependency links | `requires`, `uses`, `affects`, `demonstrates`, `verifies` | Process/provenance/history | They capture dependency, audit, or explanation structure around the model rather than the minimum durable slice itself. |
| Uncertainty that blocks behavior | none in current retained shared-tasks cases; only non-consequential `audit-retention` uncertainty is shown | Consequential accepted decision | The password-reset boundary requires consequential uncertainties to be explicit, but this slice has not yet proven which shared-tasks uncertainties deserve canonical blocking treatment. |

## Answers to the eight Track B audit questions

### 1. What is the smallest shared-tasks application boundary that still matters semantically?

The smallest durable boundary is: a shared-tasks service-shaped application in
which identified people interact with persistent task lists and tasks through a
small set of workflows. The module exists as a bounded application slice; the
exact file/module bookkeeping around it does not.

### 2. Which domain objects and identity facts remain in the core?

`person`, `task-list`, and `task` remain in the core, along with stable
identity for at least actors, lists, and tasks. Without stable identity the
slice cannot express membership, assignment, not-found behavior, or concurrent
completion outcomes deterministically.

### 3. Which field/value declarations are truly semantic, and which are over-modeled?

Identity-bearing and behavior-relevant fields are semantic. The current
fixture-level pattern of separate `value-type` objects plus explicit field
schemas may still be useful, but it is a larger representation choice than the
password-reset boundary has justified. The semantic minimum is that workflows
distinguish valid actor/list/task/title inputs and expose the observable data
they return.

### 4. Which relationships and lifecycle constraints clearly belong in durable meaning?

Membership, assignment, containment, ownership, and allowed task-state
transitions clearly belong in durable meaning because authorization and visible
results depend on them. The exact declaration syntax for cardinality and
lifecycle metadata does not yet belong in the core automatically.

### 5. What is semantic about workflows, inputs/outputs, and failures?

Workflow purpose, required inputs, observable outputs, and stable success/fail
distinctions are semantic. The advanced material correctly shows that shared
tasks needs more than password-reset here, but the current object shapes for
workflow internals are still one possible representation rather than proven
canonical form.

### 6. What is semantic about authorization and persistence, and what is merely mechanism?

It is semantic that only the right actor may view, create, assign, or complete
tasks, and that successful list/task changes persist across invocations. It is
not yet proven that Orin must express those guarantees through standalone
`capability` objects, `actorCapabilities` bindings, named `effect` objects,
durability enums, or recovery-policy fields.

### 7. Which retained diagnostics/readiness artifacts belong outside the semantic core?

Readiness extension codes, validation diagnostics, evidence-link requirements,
affected-object paths, and deterministic diagnostic ordering belong outside the
shared-tasks semantic core. They are useful evaluation/governance artifacts for
tooling parity and auditability, but they are not the application's durable
meaning.

### 8. What should happen to traceability-heavy metadata if work resumes later?

It should remain external by default. If future work resumes, object IDs,
version/status metadata, evidence graphs, impact annotations, and readiness or
validation codes should be treated as tooling/provenance layers unless a
specific field is shown to change observable shared-tasks behavior or to encode
an accepted consequential decision that must block silent AI choice.

## Main conceptual confusions and contradictions with `docs/SEMANTIC-BOUNDARY.md`

1. **Password-reset demoted scaffolding that shared-tasks still treats as core.**
   `docs/SEMANTIC-BOUNDARY.md` demotes workflow-step scaffolding, effect/capability
   structure, and bookkeeping metadata. The retained shared-tasks material still
   elevates those patterns into large fixture surfaces.
2. **Readiness/completeness artifacts drift into semantic-seeming model space.**
   The readiness extension fixtures and schema make model-completeness reporting
   look like language meaning, even though the password-reset boundary says
   readiness is computed governance output rather than stored canonical meaning.
3. **Evidence-link requirements contradict the subtraction direction.**
   Password-reset reduced evidence bookkeeping from the core, but shared-tasks
   readiness currently blocks on `rule.evidenceLinks`, which turns provenance
   structure back into a required semantic-looking contract.
4. **Capability/effect decomposition risks reifying one implementation style.**
   The advanced fixtures assume explicit capability objects, effect objects, and
   binding arrays instead of first proving that the same authorization/persistence
   claims could be preserved through a smaller semantic form.
5. **Stable IDs, affected paths, and diagnostic codes risk being mistaken for the language.**
   These are valuable for conformance tooling, but the current retained material
   makes them much more visible than the underlying shared-tasks behavioral
   claims they are supposed to support.

## What clearly remains in the core

- A bounded shared-tasks application slice
- Persistent people, task lists, and tasks with stable identity
- Membership, ownership, containment, and assignment facts where they affect
  visible behavior
- Task lifecycle states and allowed/forbidden transitions
- Workflow contracts at the level of observable inputs, outputs, and stable
  failures
- Authorization outcomes such as member-required, owner-required, and
  assignee-only completion
- Acceptance examples that prove the observable outcomes above

## What clearly moves out of the core

- `modelVersion`, object `status`, and most `kind` bookkeeping
- Standalone capability and effect object graphs as mandatory canonical form
- Actor-capability binding arrays as the required way to express authorization
- Recovery-policy, retry-policy, and failure-mode metadata unless made directly
  observable
- Example/evidence bookkeeping objects and cross-link arrays
- Readiness schemas, readiness codes, validation codes, deterministic diagnostic
  ordering rules, and JSON pointer affected paths
- Impact-area annotations, target declarations, and traceability-heavy
  `requires`/`uses`/`affects`/`verifies` scaffolding when they serve review or
  tooling rather than behavior

## What remains genuinely uncertain

- Whether shared-tasks needs explicit reusable `value-type` declarations in the
  canonical core, or only typed workflow/entity constraints
- Whether cardinality should be preserved as first-class semantic structure or
  can be derived from smaller ownership/membership rules
- Whether any shared-tasks uncertainty should be promoted to a consequential
  blocking decision the way password-reset promoted `rate-limit`
- Whether a future minimal shared-tasks core can express authorization and
  persistence without the current capability/effect object decomposition
- Whether acceptance examples alone are enough to keep some current field-level
  detail out of the core, or whether a small additional structured contract is
  still necessary

## Recommended next step

**The single smallest post-MVP change that would most improve conceptual clarity is: record an explicit project-manager decision in `docs/ORIN-0003-language-improvement-plan.md` choosing whether future shared-tasks work should remain a deferred evaluation artifact or be reactivated for a later, separately authorized semantic-minimization pass before any implementation work begins.**

## Non-authorization statement

This document is an audit recommendation only. It does **not** authorize
implementation, fixture reduction, parser/runtime changes, new syntax, new
diagnostics, or activation of shared-tasks as active execution work.
