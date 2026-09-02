# ORIN-0005: First Complete Application

**Status:** Proposal only  
**Version:** 0.1.0  
**Scope:** One complete vertical application slice before adding broad language features

## Decision

The first complete application should be a **shared task list service**.
Multiple people can belong to a task list, create tasks, assign tasks to
members, and move tasks through a small lifecycle.

This is a better next proof than expanding password reset because it requires
several application fundamentals at once:

- actors with identity;
- persistent entities;
- a relationship between actors and a list;
- explicit state transitions;
- permissions that vary by relationship;
- workflows with validated inputs;
- observable results and failures;
- executable acceptance examples.

It is deliberately a service-shaped application rather than a web-specific
application. A CLI, HTTP service, desktop client, or another interface can
invoke the same workflows later. The first reference slice should use one
simple command interface or in-memory adapter while preserving the semantic
boundary.

## Application behavior

The application has three semantic entities:

- `person`: an actor with a stable identity;
- `task-list`: a persistent collection owned by a person;
- `task`: a persistent item belonging to one task list.

A task has the states `open`, `in-progress`, and `completed`.

The initial workflows are:

1. `create-list(owner, name)` creates a task list owned by the actor.
2. `add-member(actor, list, member)` adds a member when the owner authorizes it.
3. `create-task(actor, list, title)` creates an open task for a member.
4. `assign-task(actor, task, member)` assigns a task to a list member.
5. `complete-task(actor, task)` moves an assigned task to completed.
6. `list-tasks(actor, list)` returns tasks only when the actor belongs to the list.

Minimum rules:

- A task belongs to exactly one task list.
- A list has exactly one owner.
- Only the owner can add members.
- Only a list member can create or view tasks.
- Only the task assignee can complete a task.
- A completed task cannot return to `open` in this first slice.
- Empty task titles are rejected.
- Unknown actors, lists, tasks, and non-members produce defined failures.
- A successful state change is visible in the workflow result.

## Acceptance examples

The first conformance fixture should include at least these examples:

| Example                      | Observable acceptance claim                                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- |
| owner-creates-list           | An identified owner creates a persistent empty list.                                                    |
| owner-adds-member            | The owner adds a member, and membership is observable.                                                  |
| member-creates-task          | A member creates an `open` task in the list.                                                            |
| member-views-tasks           | A member receives the task list.                                                                        |
| outsider-cannot-view         | A non-member receives an authorization failure and no tasks.                                            |
| outsider-cannot-add-member   | A non-owner cannot change membership.                                                                   |
| assignee-completes-task      | The assignee moves the task from `open` to `completed`.                                                 |
| non-assignee-cannot-complete | A different member receives an authorization failure.                                                   |
| invalid-title                | An empty title fails validation and creates no task.                                                    |
| completed-task-is-terminal   | Completing a completed task or reopening it fails without changing state.                               |
| missing-entity               | Unknown actor, list, or task produces a defined not-found failure.                                      |
| concurrent-completion        | Two completion requests have one successful transition; the other observes the already-completed state. |

The examples test behavior, not a particular database, API framework, or
storage schema.

## Current model versus required model

The existing model already provides useful building blocks:

- `module` for the application boundary;
- `value-type` for names, identifiers, and titles;
- `entity-type` as a declared kernel kind, although it is not implemented in
  the reference validator or parser;
- `relation` as a declared kernel kind, also not implemented in the reference
  slice;
- `state` for task lifecycle states;
- `capability` for authority;
- `rule` for invariants and authorization requirements;
- `workflow` for operations;
- `example` for acceptance cases;
- `effect` for persistence and other external boundaries;
- `uncertainty` and `evidence` for readiness and verification.

The missing pieces are therefore not a new general-purpose feature set. They
are the minimum executable shape and validation rules for these existing
concepts.

## Minimum semantic additions

### 1. Entity schema with identity and fields

**Required concept:** `entity-type` must define a stable identity field and a
small typed set of fields. A field needs a name, value type, required/optional
status, and whether it is mutable.

**1. Behaviour requiring it:** The runtime must distinguish Alice, a task list,
and a task; store task titles and assignees; and return those values from
workflows.

**2. Why the existing model cannot express it:** ORIN-0004 names
`entity-type`, but the current common object shape has no field schema, identity
field, or executable value constraints. The current validator cannot type-check
or persist an entity.

**3. Classification:** Semantic. Identity, fields, mutability, and value
validation change observable behavior. The storage representation is not
semantic.

**4. Composition possibility:** A collection of `value-type` declarations plus
rules could describe some fields informally, but cannot provide one typed,
addressable entity or guarantee field presence. It is insufficient without an
entity schema.

**5. Failure without it:** Tasks cannot be reliably identified, assigned, or
returned; duplicate and missing entities cannot be handled deterministically.

### 2. Relationship cardinality and ownership

**Required concept:** `relation` must define endpoints, cardinality, and any
ownership rule. The first relationships are `owns(person, task-list)`,
`member-of(person, task-list)`, `contains(task-list, task)`, and
`assigned-to(task, person)`.

**1. Behaviour requiring it:** Authorization depends on whether an actor owns
or belongs to a list, and task validity depends on exactly one containing list.

**2. Why the existing model cannot express it:** `relation` is named in the
specification but has no implemented shape for endpoints, cardinality,
uniqueness, or lifecycle behavior. A bare reference cannot tell the runtime
which person is a member of which list.

**3. Classification:** Semantic. Relationships affect identity, authorization,
and observable query results. Indexes, join tables, and foreign keys are
lowering concerns.

**4. Composition possibility:** Workflows could carry ad hoc references, but
that duplicates relationship meaning and cannot express a reusable cardinality
or ownership invariant. Composition is not sufficient.

**5. Failure without it:** Outsiders could not be distinguished from members,
multiple owners could be accepted, and tasks could be detached or attached to
multiple lists.

### 3. Explicit transition contract

**Required concept:** A workflow must declare state reads, allowed transitions,
transition guards, and state writes. For this slice, `complete-task` explicitly
allows `open -> completed` and rejects `completed -> open`.

**1. Behaviour requiring it:** Completing a task changes its state, and illegal
or repeated transitions must fail without changing state.

**2. Why the existing model cannot express it:** The current runtime has token
state but no general entity state machine. Existing `state` declarations are
names only, and `workflow` objects do not contain ordered transitions or guards.

**3. Classification:** Semantic. Allowed transitions and their failure results
are observable. Locking strategy and transaction mechanism are implementation
concerns.

**4. Composition possibility:** A `rule` could describe a transition in prose,
but prose is not enough for deterministic execution. Workflows plus rules can
compose only after a structured transition form exists.

**5. Failure without it:** The runtime could silently reopen completed tasks,
accept invalid transitions, or disagree between backends about repeated
requests.

### 4. Typed workflow input, output, and failure contract

**Required concept:** Each workflow needs named typed inputs, an output shape,
and declared failures with stable identifiers. Validation rules must attach to
inputs or transitions.

**1. Behaviour requiring it:** `create-task` needs an actor, list, and non-empty
title; callers must distinguish success from not-found, validation, and
authorization failures.

**2. Why the existing model cannot express it:** The current parser stores
workflow inputs as untyped names, and runtime results are specific to password
reset. There is no general output or failure schema.

**3. Classification:** Semantic. Input validity, failure identity, and output
shape are part of the observable contract. Serialization format and transport
status codes are lowering concerns.

**4. Composition possibility:** `value-type`, `rule`, and `workflow` can provide
pieces, but there is no single contract linking them to named parameters and
failure outcomes. It needs a small structured workflow contract, not a new
programming paradigm.

**5. Failure without it:** Different generated targets could accept different
inputs or expose different errors while claiming to implement the same Orin
workflow.

### 5. Actor authorization context

**Required concept:** A workflow invocation must carry an identified actor and
capabilities must be evaluated against that actor and the relevant object.

**1. Behaviour requiring it:** The owner may add members; members may create and
view tasks; only the assignee may complete a task.

**2. Why the existing model cannot express it:** Capabilities currently appear
as unscoped strings passed to the password-reset runtime. They do not bind an
actor to an object, relationship, acquisition, or authorization decision.

**3. Classification:** Semantic. Who may cause a state change is observable
security behavior. Tokens, sessions, roles, and middleware are implementation
mechanisms unless explicitly constrained.

**4. Composition possibility:** `entity-type person`, relations, and rules can
compose the policy, but only if the workflow has an actor input and the model
has a structured authorization predicate. A separate role system is not
needed for this slice.

**5. Failure without it:** Any caller with a generic capability could add
members, read private tasks, or complete another person's task.

### 6. Persistence boundary

**Required concept:** Declare which entities and relationship changes survive
between workflow invocations, plus the effects that read and write them.

**1. Behaviour requiring it:** A list created in one invocation must be visible
when a later invocation adds a member or creates a task.

**2. Why the existing model cannot express it:** `effect` exists only as a name
in the current model and the password-reset store is a host-language adapter.
There is no semantic read/write contract or durable lifecycle declaration.

**3. Classification:** The requirement that data survives is semantic. The
choice of SQLite, a relational service, files, or another store is an
implementation policy or lowering concern.

**4. Composition possibility:** `entity-type`, `relation`, and read/write
effects can compose persistence if effects have typed inputs/outputs and
failure modes. No new storage technology concept is needed.

**5. Failure without it:** Every workflow invocation could start empty, making
creation, membership, assignment, and acceptance examples impossible to run as
one application.

## Concepts deliberately not added

The following are not minimum semantic additions for this slice:

- `actor` as a new declaration kind: use an `entity-type` with identity and
  attach actor context to workflows;
- `role` as a new language concept: use capabilities plus relationships and
  authorization rules;
- `database`, `table`, `API`, `HTTP`, `web page`, or `UI`: these are profile or
  lowering concepts, not required to define the service behavior;
- `repository`, `ORM`, `SQL`, or `managed service`: implementation policies or
  lowering choices;
- generic event sourcing, distributed transactions, or a full concurrency
  model: the first slice needs only a deterministic transition conflict rule;
- AI-specific runtime semantics: AI may assist authoring, but accepted meaning
  must execute without AI reinterpretation.

## Minimal composed model

The first complete model should use existing kernel kinds plus the six focused
additions above:

```text
module shared-tasks
  value-types: person-id, list-name, task-id, task-title
  entities: person, task-list, task
  relations: owns, member-of, contains, assigned-to
  states: open, in-progress, completed
  capabilities: create-list, manage-members, manage-tasks, complete-task
  rules: membership, ownership, non-empty-title, terminal-completion
  workflows: create-list, add-member, create-task, assign-task,
             complete-task, list-tasks
  effects: persistent-entity-store.read, persistent-entity-store.write
  examples: acceptance and failure cases above
```

The six additions are mostly completion of concepts already named by the
semantic model:

1. entity field and identity schemas;
2. relation endpoint/cardinality schemas;
3. structured state transition contracts;
4. typed workflow contracts;
5. actor-bound authorization context;
6. persistence read/write and durability contracts.

They should be added as the smallest schema fields and validation rules that
make this model executable, not as broad new top-level abstractions.

## End-to-end proof boundary

The reference slice is complete when this deterministic path works:

```text
structured task-list model
  -> readiness diagnostics
  -> accepted executable workflow model
  -> deterministic reference runtime
  -> persistent test adapter
  -> generated conformance tests
  -> observable results and failures
```

The first implementation may use a simple local persistence adapter and one
host language under `implementations/<language>/`. That adapter is a test
implementation, not part of Orin's meaning. The conformance fixtures and model
remain language-neutral.

The proof must demonstrate:

- persistence across separate workflow calls;
- authorization based on actor and relationship;
- valid and invalid state transitions;
- input validation before mutation;
- deterministic not-found and authorization failures;
- one concurrent completion winner without claiming a general distributed
  concurrency guarantee;
- identical acceptance results when the adapter is replaced by another
  implementation.

## Recommendation for the next implementation increment

Do not expand the language horizontally yet. Implement the six additions only
for the shared task list model, starting with entity/field and relationship
schemas, then workflow contracts and state transitions, then actor-bound
persistence and generated examples. Update ORIN-0003 after review of this
proposal. No implementation is included in this document.
