# Shared Tasks: Minimal Design and Model Validation

This application example collects the minimal shared-tasks design (Phase 1.1)
and the subsequent model-fit evaluation (ORIN-0006 Phase 1.5). The minimal
executable slice was evaluated in Phases 1.1–1.4; the original instruction to
build its fixtures is historical, not unfinished work.

## Navigation and status

- [Readable minimal example](../../shared-tasks.minimal.orin)
- [Broader design proposal](./design-proposal.md): deferred ORIN-0005 stress-test
  proposal, not the scope of the completed minimal slice.
- [Semantic audit and ORIN-0004 alignment](./semantic-audit.md): historical
  evaluation of retained advanced fixtures, including unresolved modeling
  questions; not implementation authorization.
- [Language kernel](../../../docs/ORIN-0002-language-kernel.md) and
  [semantic model](../../../docs/ORIN-0004-semantic-model.md): language-level
  references, not application-specific design.
- [Development roadmap](../../../docs/development/ORIN-0006-next-evolution-roadmap.md)
  and [deferred index](../../../docs/development/BACKLOG.md): current work and
  deferred-work status. Historical phase recommendations below do not activate
  work; activation belongs in the
  [language improvement plan](../../../docs/ORIN-0003-language-improvement-plan.md).

## Why this minimal slice tests Orin

This is the smallest step beyond password-reset that forces multi-entity
behavior, relationship-based authorization, terminal state transitions, and
durable state change. It tests whether those observable claims fit existing
ORIN-0002 kernel kinds without new syntax, top-level declarations, or
implementation-specific schema detail.

## Entities and relationships

| Entity | Identity and durable relationships |
| --- | --- |
| Person | Stable `person-id`; can own lists, belong to lists, and be assigned tasks. |
| TaskList | Stable `list-id`; exactly one Person owner, zero or more Person members, zero or more tasks. |
| Task | Stable `task-id`; exactly one containing TaskList; observable state `open` or `completed`; optional Person assignee. |

These declarations express identity and durable relationships, not typed field
catalogs, storage schema, or host-language metadata.

| Relationship | Cardinality and observable constraints |
| --- | --- |
| `owns(Person, TaskList)` | One Person to many lists; only the owner may add/remove members; a list cannot become unowned. |
| `member-of(Person, TaskList)` | Many-to-many; only members can act on tasks; the owner is always implicitly a member. |
| `contains(TaskList, Task)` | One list to many tasks; every task belongs to exactly one list; creation requires an existing list; binding is fixed (no moving tasks). |

If a referenced list is missing at execution time, the workflow returns
`list-not-found` without changing state.

## `complete-task` contract

Input: `actor` (Person), `task` (Task). Output on success: the Task with updated
state.

Preconditions:

1. The task is `open`.
2. The actor is a member of its list.
3. If an assignee exists, the actor is that assignee.

On success, the task becomes `completed`, and that state persists across later
invocations. Completion is terminal: `completed` never returns to `open` in
this slice.

### Failures and deterministic precedence

Checks occur in this order; the first failing check determines the result:

1. Task existence: `task-not-found`.
2. Task-list existence: `list-not-found`.
3. Actor membership: `unauthorized`.
4. Assignee match, when an assignee exists: `not-assigned`.
5. Terminality: `already-completed`.

Thus membership or assignment failure prevents terminality evaluation for that
request. Only members may complete tasks; when assigned, a task may be completed
only by its assignee. Re-completion by an otherwise authorized actor fails with
`already-completed`.

Failure identities are semantic behavior, not tooling metadata. Every failure
leaves task state unchanged and returns a distinct identity. Repeated execution
under the same conditions yields the same failure.

## Acceptance examples

### 1. Member completes own task

1. A owns list X; B is a member; task T in X is assigned to B and is `open`.
2. Invoke `complete-task(B, T)`.
3. T becomes `completed`.
4. A subsequent query/invocation observes T as `completed`.

### 2. Non-member attempts completion

1. A owns X; C is not a member; T in X is assigned to A and is `open`.
2. Invoke `complete-task(C, T)`.
3. The result is `unauthorized`.
4. T remains `open`.

### 3. Repeated completion

1. T is already `completed`, its list still exists, and its assignee is still a
   member.
2. The authorized assignee invokes `complete-task(assignee, T)` again.
3. The result is `already-completed`.
4. T remains `completed`.

### 4. Missing task

1. A is a member of X; `T-MISSING` does not exist.
2. Invoke `complete-task(A, T-MISSING)`.
3. The result is `task-not-found`.
4. No state changes anywhere.

## Design scope and kernel mapping

The accepted minimal design includes three entities, three relationships, one
workflow with explicit preconditions/postconditions/failures, two behavioral
rules (member-only completion and terminal completion), and completion
durability.

| Shared-tasks concept | ORIN-0002 representation |
| --- | --- |
| Person, TaskList, Task with stable identity | `entity-type` |
| Ownership, membership, containment constraints | `relation` + `rule` |
| Complete-task operation | `workflow` |
| Who may complete | `capability` + `rule` |
| State change and persistence | `effect` + `rule` |
| Acceptance examples | Executable examples of the same observable claims |

Phase 1.1 deliberately excluded model JSON, conformance additions, parser,
runtime, and backend changes: those were later-phase work, not permanent
exclusions. API/storage/transport/runtime architecture details remained outside
the application meaning. Readiness-code expansion was excluded unless later
behavior proved it necessary.

The original Phase 1.2 handoff was to encode this exact slice in a neutral
model, add the four deterministic cases, validate Python/TypeScript parity, and
check whether any readiness extension was truly required (default: none).
It required review/acceptance of the design first.

## Model-validation evidence (Phase 1.5)

The evaluation reviewed the minimal design above and these artifacts:

- [Minimal model](../../../tests/conformance/shared-tasks.minimal.model.json)
- [Minimal cases](../../../tests/conformance/shared-tasks.minimal.cases.json)
- [Python conformance runner](../../../implementations/python/shared_tasks_conformance.py)
- [TypeScript minimal-case tests](../../../implementations/typescript/src/shared_tasks_minimal_cases.test.ts)

The recorded result was that the executable slice used only existing kernel
kinds: `value-type`, `entity-type`, `relation`, `state`, `capability`, `effect`,
`workflow`, `rule`, and `example`. No new top-level kind or syntax was required.

### What the evaluation established

- One workflow with deterministic outcomes and four explicit acceptance examples.
- Authorization and terminality expressed as rules and runtime outcomes.
- Cross-language parity verified directly against shared fixture cases.
- Language-neutral evidence first, host-language evidence second.
- No new `actor`/`role` kind, persistence-framework syntax, fixture
  schema/provenance expansion, or readiness-code expansion. Durability remained
  an effect contract.

### Caveat and historical exit decision

The semantic boundary **held with caveats**: success, authorization failure,
terminal failure, and missing-task failure remained explicit and testable, but
the model retained inherited `value-type` and `state` structure beyond the
strictest “identity + relationships only” reading. That was a future reduction
candidate, not a model-fit blocker.

The recorded exit decision was **Go to ORIN-0006 Phase 2**: no new core concepts
had been introduced, and deterministic behavior was executable and
cross-language verified. The historical recommendation was Phase 2.1
(decision-support agent expansion), preserving deterministic examples as the
primary evidence and adding no core kinds without new observable behavior.
This records the evaluation outcome, not a fresh instruction to implement that
phase or to expand Orin into an agent/workflow system.
