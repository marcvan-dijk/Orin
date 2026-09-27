# Shared Tasks Minimal Design (Phase 1.1)

## 1) Executive summary: Why this slice tests Orin

This slice is the smallest step beyond password-reset that still forces Orin to
express multi-entity behavior, relationship-based authorization, terminal state
transitions, and durable state change. It tests whether these observable claims
fit inside existing ORIN-0002 kernel kinds without adding syntax, new top-level
declarations, or implementation-specific schema detail.

## 2) Entities: identity and relationships (no schema bloat)

### Person
- Identity: stable `person-id`
- Can own task lists
- Can be a member of task lists
- Can be assigned to tasks

### TaskList
- Identity: stable `list-id`
- Has exactly one owner (a Person)
- Has zero or more members (Persons)
- Contains zero or more tasks

### Task
- Identity: stable `task-id`
- Belongs to exactly one TaskList
- Has observable state `open` or `completed`
- May have an assignee (Person)

Entities in this slice only declare identity and durable relationships. They do
not introduce typed field catalogs, storage schema, or host-language metadata.

## 3) Relationships: endpoints, cardinality, observable constraints

### owns(Person, TaskList)
- Cardinality: one Person to many TaskLists
- Observable constraint: only owner may add/remove members
- Terminal constraint: a TaskList cannot become unowned

### member-of(Person, TaskList)
- Cardinality: many-to-many
- Observable constraint: only members can act on tasks in the list
- Owner inclusion: owner is always implicitly a member

### contains(TaskList, Task)
- Cardinality: one TaskList to many Tasks; each Task belongs to exactly one list
- Observable constraint: task creation requires an existing TaskList
- Terminal constraint: task-to-list binding is fixed in this slice (no moving)
- Failure surface: if a referenced list is missing at execution time, the
  workflow returns `list-not-found` and performs no state change

## 4) Workflow: complete-task

### Signature
- Input: `actor` (Person), `task` (Task)
- Output: `task` (Task with updated state on success)

### Preconditions
1. `task.state` is `open`
2. `actor` is a member of `task.list`
3. If task has an assignee, `actor` is that assignee

### Postconditions
1. `task.state` becomes `completed`
2. The completed state persists across later invocations

### Observable failures
- `unauthorized` — actor is not a member of the list
- `not-assigned` — actor is not the assignee when assignee exists
- `already-completed` — task is already completed
- `task-not-found` — referenced task does not exist
- `list-not-found` — task’s list does not exist

### Deterministic failure precedence
To keep outcomes deterministic, `complete-task` evaluates checks in this order:
1. task existence (`task-not-found`)
2. task list existence (`list-not-found`)
3. actor membership (`unauthorized`)
4. task state terminality (`already-completed`)
5. assignee match when assignee exists (`not-assigned`)

`already-completed` is therefore defined for requests that already satisfy
existence and membership checks.

## 5) Rules

### Rule A: Only members can complete tasks
- Non-member completion attempts fail with `unauthorized`
- Members can complete only their own assigned tasks when assignment exists

### Rule B: Completion is terminal
- `completed` never transitions back to `open` in this slice
- Re-completing an already completed task fails with `already-completed`

## 6) Failures: distinct and observable

Failure identities are part of semantic behavior, not tooling metadata. On any
failure:
- task state does not change
- caller receives a distinct failure identity
- repeated execution under same conditions yields same failure identity

This keeps behavior deterministic and reviewable across implementations.

## 7) Acceptance examples (deterministic, step-by-step)

### Example 1: Happy path — member completes own task
1. Setup: A owns list X; B is member of X; task T in X is assigned to B and is `open`
2. Action: `complete-task(B, T)`
3. Result: T state becomes `completed`
4. Follow-up observation: subsequent query/invocation sees T as `completed`

### Example 2: Authorization failure — non-member attempts completion
1. Setup: A owns list X; C is not member of X; task T in X is assigned to A and is `open`
2. Action: `complete-task(C, T)`
3. Result: failure `unauthorized`
4. Follow-up observation: T remains `open`

### Example 3: Terminal state — repeated completion fails
1. Setup: task T is already `completed`; T still references an existing list; assignee is still a member of that list
2. Action: authorized assignee calls `complete-task(assignee, T)` again
3. Result: failure `already-completed`
4. Follow-up observation: T remains `completed`

### Example 4: Missing entity — task not found
1. Setup: A is a member of list X; task `T-MISSING` does not exist
2. Action: `complete-task(A, T-MISSING)`
3. Result: failure `task-not-found`
4. Follow-up observation: no state changes anywhere

## 8) Design decisions: included scope and deliberate exclusions

### Included
- Three entities with stable identifiers
- Three relationships with observable constraints
- One workflow with explicit preconditions/postconditions/failures
- Two behavioral rules and one explicit unauthorized failure mode
- State durability requirement for completion outcome

### Deliberately excluded in Phase 1.1
- No semantic model JSON fixture (Phase 1.2)
- No parser/runtime/backend changes
- No conformance fixture additions
- No API/storage/transport/runtime architecture details
- No readiness-code expansion unless later behavior proves it is required

## 9) Mapping to ORIN-0002 kernel kinds

| Shared-tasks concept | ORIN-0002 kind(s) used |
| --- | --- |
| Person, TaskList, Task with stable identity | `entity-type` |
| owns/member-of/contains constraints | `relation` + `rule` |
| complete-task operation | `workflow` |
| who is allowed to complete | `capability` + `rule` |
| completion state change and persistence requirement | `effect` + `rule` |
| acceptance examples above | executable acceptance examples (same observable claims) |

This design introduces no new top-level declaration kinds and no new syntax.

## 10) Next steps: validation tasks and Phase 1.2 build

1. Encode this exact slice in `tests/conformance/shared-tasks.minimal.model.json`
2. Keep only ORIN-0002 kernel-kind constructs required for observable behavior
3. Add deterministic acceptance fixtures for the four examples
4. Validate parity in Python and TypeScript conformance runners
5. Confirm whether any readiness extension is truly required by new observable behavior (default expectation: none)

Phase 1.2 starts only after this design is reviewed and accepted as the
authoritative minimal shared-tasks scope.
