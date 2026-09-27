# ORIN-0006: Next Evolution Roadmap

**Status:** Active post-MVP roadmap  
**Version:** 0.1.0  
**Date:** September 2026  
**Trigger:** After Track B semantic boundary audit completion

## Strategic thesis

The password-reset MVP proved that Orin can express intent, detect unresolved decisions, and lower to multiple implementations without losing behavior. But proof-of-concept is not adoption.

The next evolution must answer: **Can Orin remain minimal, scale to real applications, and create observable value?**

This roadmap focuses on three sequential pillars:

1. **Semantic Validation** — Prove shared-tasks doesn't bloat the model.
2. **Usability & Adoption** — Build the collaborative authoring experience.
3. **Real-world proof** — Demonstrate value in a concrete domain.

## Phase 1: Shared-Tasks Semantic Proof (6-8 weeks)

**Goal:** Demonstrate that Orin can express a multi-entity, multi-actor application with authorization and persistence without expanding the core semantic model.

### 1.1 Minimal shared-tasks design spec

**Deliverable:** `docs/SHARED-TASKS-MINIMAL-DESIGN.md`

Define the absolute smallest shared-tasks application that tests Orin beyond password-reset:

- **3 entities:** `Person`, `TaskList`, `Task`
- **3 key relationships:** `owns(Person, TaskList)`, `member-of(Person, TaskList)`, `contains(TaskList, Task)`
- **1 workflow:** `complete-task(actor: Person, task: Task) → Task`
- **2 critical rules:** "Only members can complete tasks", "Completion is terminal"
- **1 failure mode:** Unauthorized actor
- **4 acceptance examples:** Happy path, authorization failure, repeated completion, missing entity

**Constraint:** Must fit in ORIN-0002 kernel kinds (no new declarations, no new syntax).

**Acceptance criteria:**
- Design fits in the existing `entity-type`, `relation`, `workflow`, `capability`, `rule`, `effect` model.
- No new readiness codes required.
- Every observable behavior is expressed as a semantic claim or rule, not metadata.

### 1.2 Minimal semantic model

**Deliverable:** `tests/conformance/shared-tasks.minimal.model.json`

Create a language-neutral semantic fixture that:
- Uses only the password-reset model shape minus excess scaffolding.
- Defines the 3 entities with stable identities only (no field schema bloat).
- Expresses relationships as rules, not specialized relation objects.
- Declares the workflow with explicit inputs, outputs, and failure contract.
- Includes 4 acceptance examples.

**Constraint:** No `lifecycle`, `evidenceLinks`, `impactAreas`, `dataAccess`, `retryPolicy`, `failureModes`, or `recoveryBehavior` fields unless the behavior is externally observable.

### 1.3 Minimal runtime proof

**Deliverable:** Extend `implementations/python/shared_tasks.py`

Implement a deterministic reference runtime that:
- Loads the minimal model.
- Executes the complete-task workflow.
- Maintains TaskList and Task state.
- Enforces authorization based on membership.
- Rejects repeated completion.
- Reports authorization failures distinctly from not-found failures.

**Constraint:** Do not add a general persistence framework. Use simple in-memory state for the proof.

### 1.4 Semantic equivalence test

**Deliverable:** `implementations/typescript/src/shared_tasks_minimal.test.ts`

Verify that the TypeScript implementation produces identical observable results to Python.

**Acceptance criteria:**
- Both implementations pass all 4 examples.
- Authorization failures are reported identically.
- State transitions are deterministic.
- The semantic model is unchanged between runs.

### 1.5 Audit: Does it fit the model?

**Deliverable:** `docs/SHARED-TASKS-MODEL-VALIDATION.md`

Document:
- Which ORIN-0002 kinds were used and whether any new ones were needed.
- Which parts of the model required zero scaffolding.
- Which parts tempted toward bloat and were resisted.
- Whether the semantic boundary held.

**Exit condition:** If the model fits cleanly without new concepts, proceed to Phase 2. If not, halt and reassess.

---

## Phase 2: Adoption UX & Collaboration (6-8 weeks)

**Goal:** Make Orin collaborative and delightful, not just technically correct.

### 2.1 Decision-support agent expansion

**Deliverable:** Extend `tooling/python/orin_agent.py`

Enhance the agent to:
- Accept shared-tasks semantic models in addition to password-reset.
- Identify unresolved consequential decisions in the complete-task workflow.
- Propose resolution options with impact analysis.
- Apply human decisions and re-validate.

**Acceptance criteria:**
- Agent can load and analyze shared-tasks.minimal.model.json.
- Agent surfaces a realistic unresolved decision (e.g., "What happens if a non-member tries to complete a task?").
- Human selects a decision option.
- Agent produces a revised model with updated rules/examples.

### 2.2 VS Code extension polishing

**Deliverable:** Real UX improvements to `tooling/vscode-extension/`

- Syntax highlighting for Orin syntax.
- Outline/tree view showing module structure, workflows, rules, examples.
- Command to invoke agent inspection inline.
- Readiness status indicator (ready/blocked).
- Quick-fix suggestions for unresolved decisions.

**Acceptance criteria:**
- Opening password-reset.orin shows clear structure.
- Hovering over a workflow shows its purpose and actor context.
- Command palette has "Inspect with Orin Agent" that shows decisions.

### 2.3 First-user onboarding

**Deliverable:** `docs/ONBOARDING.md` + demo video script

Write a 10-minute walkthrough:
- Clone the repo.
- Open password-reset.orin.
- Understand the three core concepts: intent, decision, evidence.
- Run the agent inspection.
- Modify a decision.
- See impact on examples.
- Generate a backend (reference runtime or TypeScript).

**Acceptance criteria:**
- A developer unfamiliar with Orin can complete the walkthrough in 10 minutes.
- At the end, they understand why intent/decision/evidence separation matters.

### 2.4 Collaborative model authoring prototype

**Deliverable:** Sketch + minimal implementation of proposal/accept/reject flow

Design a UX where:
- AI suggests a change to a workflow or rule.
- Human sees exactly what changed and why.
- Human can accept, reject, ask for explanation, or propose an edit.
- Decision is recorded with rationale.

**Constraint:** Prototype only. Can be rough. Goal is to test whether the idea resonates.

---

## Phase 3: Real-world proof (8-12 weeks)

**Goal:** Demonstrate that Orin creates observable value in a concrete domain.

### 3.1 Domain selection

**Decision needed from the team:** Which real use case should be the first proof?

Candidates:
- **SaaS onboarding flow:** Signup → verification → payment → dashboard. Tests multi-step workflows, external effects (payment), and temporal constraints.
- **Content moderation:** Submission → review → decision → notification. Tests conditional logic, rules, and failure modes.
- **Invoice/expense approval:** Creation → routing → approval → payment. Tests state machines, authorization, and persistence.

**Recommendation:** Pick one with genuine team interest and where the observable behavior is well-understood.

### 3.2 Application design

**Deliverable:** `docs/ORIN-APP-{domain}.md`

Write the application in plain English:
- What are the core entities?
- What workflows matter?
- What rules are non-negotiable?
- What decisions are consequential?
- What could go wrong?

Use no Orin syntax yet.

### 3.3 Orin specification

**Deliverable:** `examples/{domain}.orin` or `examples/{domain}.model.json`

Express the application in Orin:
- Use the minimal model language from Phase 1.
- Declare entities, relationships, workflows, rules.
- Surface unresolved decisions.
- Write acceptance examples.

**Constraint:** Do not expand the language to accommodate the domain. Instead, be creative about expressing the domain within the existing model. If you hit a wall, document it.

### 3.4 Backend generation

**Deliverable:** Generated service code + tests

Lower the Orin model to:
- **Option A:** TypeScript/Node.js with Express or Fastify.
- **Option B:** Python with FastAPI.

Generated code should:
- Have typed endpoints matching the Orin workflows.
- Enforce the rules declared in Orin.
- Reject unauthorized operations.
- Return examples from the Orin model as snapshot tests.

### 3.5 Real-world execution

**Deliverable:** Deploy + operate the service

- Deploy to a test environment.
- Invite a small group to use it.
- Collect feedback on UX and behavior.
- Trace observed behavior back to Orin intent.

### 3.6 Impact report

**Deliverable:** `docs/ORIN-APP-{domain}-RETROSPECTIVE.md`

Document:
- What worked?
- What was surprising?
- Did the durable-intent model make a difference?
- What would make it better?
- Should Orin scale to more domains?

---

## Cross-cutting: Continuous refinement

### Specification updates

After each phase, update:
- `ORIN-0001`: Add or clarify protocol patterns discovered in practice.
- `ORIN-0002`: Refine the semantic kernel based on what worked and what tempted to bloat.
- `ORIN-0003`: Log completed work and update next steps.
- `SEMANTIC-BOUNDARY.md`: Add domain-specific examples of durable vs. scaffolding.

### Testing discipline

Every phase must have:
- **Language-neutral fixtures** that define the proof.
- **Python reference implementation** that loads and executes the fixtures.
- **TypeScript validation** that the Python output is reproducible.
- **No silent assumptions.** If behavior is unclear, it's a design gap.

### Documentation-first decisions

Before implementing, decide:
- Is this semantic or scaffolding?
- Is this an unresolved decision that should block compilation?
- Does this enable a new observable behavior, or just make tooling easier?
- Can the current model express this, or do we truly need new syntax?

---

## Success metrics

### Phase 1 (Shared-tasks semantic proof)
- ✅ Minimal model loads, validates, and executes.
- ✅ Identical results from Python and TypeScript.
- ✅ No new ORIN-0002 kinds required.
- ✅ No new readiness codes required.
- ✅ Semantic boundary held.

### Phase 2 (Adoption UX)
- ✅ VS Code extension feels native.
- ✅ First-time user completes onboarding in 10 minutes.
- ✅ Agent can inspect shared-tasks and password-reset.
- ✅ At least one team member says "I see why this matters."

### Phase 3 (Real-world proof)
- ✅ Real application expressed in Orin.
- ✅ Code generated and executed.
- ✅ Behavior matches the declared intent.
- ✅ At least one observable advantage over writing the application in hand-crafted code.

---

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Shared-tasks requires new model concepts | Document the gap; decide whether to extend the model or accept the limitation. Do not silently add scaffolding. |
| UX improvements take longer than expected | Prioritize agent + CLI before polishing VS Code. Collaboration can be skeletal and still prove the idea. |
| Real-world domain is too complex for the model | Pick a simpler domain or break it into smaller workflows. Don't try to make Orin general-purpose to solve one outlier. |
| Generated code is ugly or non-idiomatic | Accept imperfection in Phase 3. The proof is that intent is preserved, not that generated code is production-perfect. |
| No team interest in real-world proof | Start with an internal use case (e.g., documenting an existing service in Orin retrospectively). Proof doesn't require external adoption. |

---

## Decision gates

### After Phase 1 (go/no-go)
- **Go:** Shared-tasks model is clean, no new concepts, semantic boundary held. Proceed to Phase 2.
- **No-go:** Model required significant expansion or scaffolding. Halt and reassess whether Orin's thesis is valid at scale.

### After Phase 2 (go/no-go)
- **Go:** UX is usable, first-user feedback is positive. Proceed to Phase 3.
- **No-go:** Adoption UX is too hard or doesn't resonate. Consider whether Orin is meant for collaborative teams or solo engineers.

### After Phase 3 (decision)
- **Scale:** Observable value was demonstrated. Invest in ecosystem and broader adoption.
- **Refine:** Value was unclear; go deeper with more domains or different UX.
- **Archive:** Orin is a beautiful proof but not a practical tool. Document findings and move on.

---

## Next immediate step

**Activate Phase 1.1:** Define minimal shared-tasks design spec.

Owner: Coding agent  
Timeline: 1-2 days  
Deliverable: `docs/SHARED-TASKS-MINIMAL-DESIGN.md`  
Blocker: None—proceed immediately

After Phase 1.1 is complete and reviewed, activate Phase 1.2.

