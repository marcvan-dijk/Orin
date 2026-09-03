# Orin Implementation Roadmap: Immediate Actions

**Date Created:** 2026-09-03  
**Scope:** M1 & M2 Task Breakdown  
**Priority:** Unblock semantic core validation → parser completion

---

## M1: Semantic Core (Week 1-3) — Detailed Tasks

### Task M1.1: Finalize & Validate Semantic Model Schema
**Owner:** Language Designer  
**Duration:** 2 days  
**Acceptance:** Schema validates all password-reset fixtures

**Subtasks:**
- [ ] Review current `semantic-model.json` in repo against ORIN-0004 spec
- [ ] Add missing fields: `capabilities`, `effects`, `persistence_contracts`, `readiness_status`
- [ ] Define error codes (e.g., `ORIN-E001: unresolved-reference`, `ORIN-E041: unresolved-consequential-uncertainty`)
- [ ] Create schema validator (JSON Schema or Pydantic)
- [ ] Test against all 3 fixtures: `password-reset.model.json`, `shared-tasks.model.json`, `authoring-choices.json`

**Deliverable:** `implementations/python/schema_validator.py` + `schema.json`

---

### Task M1.2: Identity & Reference Resolution
**Owner:** Python Dev  
**Duration:** 2 days  
**Acceptance:** All references resolve; duplicates detected; error codes emitted

**Subtasks:**
- [ ] Implement `ReferenceResolver` class:
  - Build symbol table from all declarations (types, entities, workflows, effects, rules)
  - Resolve every reference (by name/path)
  - Detect duplicates, circular references, undefined references
  - Emit `ORIN-E002`, `ORIN-E003`, etc. with source location
- [ ] Add identity stability check (objects can be compared by ID across serializations)
- [ ] Test against password-reset fixture
- [ ] Document any unresolvable references (defer to Phase 2)

**Deliverable:** `implementations/python/reference_resolver.py` + tests

---

### Task M1.3: Capability & Effect Linking
**Owner:** Python Dev  
**Duration:** 3 days  
**Acceptance:** Workflows cannot use effects without declaring required capabilities; compiler rejects violations

**Subtasks:**
- [ ] Define capability model (identity, scope, required-before, expiry, revocation)
- [ ] Implement effect binding:
  - Every effect declares `required_capabilities: [...]`
  - Every workflow declares `capabilities_used: [...]`
  - Validate: used ⊆ declared
  - Emit `ORIN-E010: unauthorized-effect` if violated
- [ ] Add persistence effect check (data durability contracts)
- [ ] Test on password-reset (should declare `email-delivery` capability for send-reset-email effect)
- [ ] Document capability scope model (who grants? when? how long?)

**Deliverable:** `implementations/python/capability_validator.py` + tests

---

### Task M1.4: Diagnostic Error System
**Owner:** Python Dev  
**Duration:** 2 days  
**Acceptance:** All errors have stable codes, human explanations, source locations, severity levels

**Subtasks:**
- [ ] Create `Diagnostic` class:
  - Fields: `code` (ORIN-EXXX), `message`, `source_location`, `severity` (error/warning/info), `affected_object`, `suggested_fix`
- [ ] Implement `DiagnosticCollector` (collect all errors before stopping)
- [ ] Add 10+ diagnostic types:
  - Unresolved reference
  - Duplicate identity
  - Invalid state transition
  - Unauthorized effect
  - Missing capability
  - Blocked uncertainty
  - Type mismatch
  - etc.
- [ ] Format for IDE display (VS Code extension can consume)
- [ ] Test that "rate-limit" unresolved produces `ORIN-E041` blocking compilation

**Deliverable:** `implementations/python/diagnostics.py` + diagnostic tests

---

### M1 Exit Criteria

```bash
# All 3 fixtures load, validate, serialize identically
$ python -m orin.validator tests/conformance/password-reset.model.json
✓ 0 errors, 0 warnings
✓ Identity count: 23, Reference count: 47
✓ Serializes identically after canonicalization

$ python -m orin.validator tests/conformance/shared-tasks.model.json
✓ 0 errors, 0 warnings

$ python -m orin.validator tests/conformance/authoring-choices.json
✓ 0 errors, 0 warnings
```

**Effort:** ~9 days (2+2+3+2)  
**Owner Allocation:** Python Dev 60%, Language Designer 30% (review decisions)

---

## M2: Parser & Interpreter (Week 4-7) — Detailed Tasks

### Task M2.1: Complete `.orin` Parser → Model Mapping
**Owner:** Python Dev  
**Duration:** 3 days  
**Acceptance:** `examples/password-reset.orin` → `password-reset.model.json` (canonically equivalent)

**Subtasks:**
- [ ] Review current parser in `implementations/python/orin_parser.py`
- [ ] Ensure it emits semantic model objects (not AST):
  - `Module` → name, purpose, context, imports
  - `Type` → identity, fields, validations
  - `Entity` → identity, fields, relations
  - `State` → identity, values
  - `Workflow` → identity, inputs, outputs, steps, effects
  - `Rule` → identity, condition, consequence
  - `Effect` → identity, boundary, side effects
  - `Capability` → identity, required scope, duration
  - `Example` → identity, preconditions, steps, assertions
  - `Uncertainty` → identity, blocking status, options
- [ ] Preserve source locations (line, column) for all objects
- [ ] Test: parse → serialize → parse again → canonical equality
- [ ] Handle unsupported syntax gracefully (emit `ORIN-E099: unsupported-feature`)

**Deliverable:** Updated `implementations/python/orin_parser.py` with integration tests

---

### Task M2.2: Deterministic Interpreter (State Machine + Fake Adapters)
**Owner:** Python Dev  
**Duration:** 4 days  
**Acceptance:** Execute password-reset workflow deterministically; all effects use fake adapters

**Subtasks:**
- [ ] Build state machine executor:
  - Load model + initial state
  - Execute workflow steps sequentially
  - Maintain state transitions log (for audit)
  - Report final state + outputs
- [ ] Implement fake adapters (no real external calls):
  - `AccountStoreAdapter` (in-memory dict, configurable lookup results)
  - `EmailDeliveryAdapter` (log sent emails, configurable success/failure)
  - `ClockAdapter` (fixed/deterministic time)
  - `TokenGeneratorAdapter` (deterministic, repeatable tokens)
  - `RateLimiterAdapter` (policy-aware; can be "unresolved")
- [ ] Execute workflow for each example:
  - Step 1: Request received
  - Step 2: Account lookup
  - Step 3: Token creation (if applicable)
  - Step 4: Email send (if applicable)
  - Step 5: Response
- [ ] Record execution trace:
  - Input values
  - State transitions (before → after)
  - Rules evaluated (pass/fail/N/A)
  - Effects called + results
  - Final output
- [ ] Handle errors gracefully (email-provider-fail, account-store-fail, etc.)

**Deliverable:** `implementations/python/interpreter.py` + fake adapters + execution traces

---

### Task M2.3: Execute 5 Core Examples
**Owner:** Python Dev + QA  
**Duration:** 3 days  
**Acceptance:** All 5 examples run deterministically; outputs match expectations

**Examples to implement:**

1. **Registered Address** → Stored token, email sent, standard response
2. **Unknown Address** → No token created, no email, standard response (same as registered)
3. **Expired Token** → Workflow rejects token as expired, standard response
4. **Email Delivery Failure** → Token created, email fails, standard response + log
5. **Rate-Limit Unresolved** → Compilation blocked; `ORIN-E041` error

**Subtasks:**
- [ ] Map each example to `password-reset.cases.json` case
- [ ] Implement expected outputs (assertions) for each
- [ ] Run interpreter on each case
- [ ] Compare actual vs. expected (state, output, rules, effects)
- [ ] Generate evidence record for each (claim + inputs + outputs)
- [ ] Document assumptions (what's "standard response"? what privacy guarantees hold?)

**Deliverable:** `tests/conformance/password-reset-examples.py` + 5 passing tests

---

### Task M2.4: Rate-Limit Blocking
**Owner:** Language Designer + Python Dev  
**Duration:** 2 days  
**Acceptance:** Model with unresolved `rate-limit` cannot compile; clear error

**Subtasks:**
- [ ] Define "consequential uncertainty":
  - Rate-limit policy affects abuse-prevention guarantees
  - Workflow depends on it (decision point: retry or reject?)
  - Cannot execute safely without it
- [ ] Implement blocking logic:
  - Compiler scans for `uncertainty` objects marked as `blocking: true`
  - If any unresolved → emit `ORIN-E041: unresolved-consequential-uncertainty`
  - Compilation fails; user must resolve (choose policy)
- [ ] Add policy resolution mechanism:
  - User decides: "rate-limit = 5-per-minute" OR "defer to runtime"
  - Update model with decision
  - Recompile (should succeed)
- [ ] Test:
  - Compile password-reset without rate-limit decision → fail
  - Add decision → succeed

**Deliverable:** `implementations/python/uncertainty_blocker.py` + policy resolution UI sketch

---

### M2 Exit Criteria

```bash
# Parse .orin → model
$ python -m orin.parser examples/password-reset.orin
✓ Parsed; 47 semantic objects created
✓ Source locations preserved
✓ rate-limit uncertainty marked as unresolved

# Try to compile (should fail)
$ python -m orin.compiler examples/password-reset.orin
✗ ORIN-E041: unresolved-consequential-uncertainty: rate-limit affects abuse-prevention and must be decided before compilation

# Resolve rate-limit
$ echo "policy { rate-limit = '5-per-minute' }" >> examples/password-reset.orin

# Compile (should succeed)
$ python -m orin.compiler examples/password-reset.orin
✓ Compilation successful
✓ Generated: reference-runtime.py, password-reset-service.ts

# Run examples
$ python -m orin.test tests/conformance/password-reset-examples.py
✓ registered-address: PASS
✓ unknown-address: PASS
✓ expired-token: PASS
✓ email-delivery-failure: PASS
✓ rate-limit-unresolved: PASS (error caught)
✓ 5/5 examples passed
```

**Effort:** ~12 days (3+4+3+2)  
**Owner Allocation:** Python Dev 70%, QA 40%, Language Designer 20% (design decisions)

---

## M3: TypeScript Backend (Week 8-10) — Detailed Tasks

### Task M3.1: Load Semantic Model in TypeScript
**Owner:** TypeScript Dev  
**Duration:** 2 days  
**Acceptance:** Parse JSON model; reconstruct semantic objects

**Subtasks:**
- [ ] Create TypeScript types matching Python semantic model
- [ ] Implement model loader (JSON → TypeScript objects)
- [ ] Validate identity/reference resolution (same as Python)
- [ ] Test: load `password-reset.model.json` → execute equivalence check

**Deliverable:** `implementations/typescript/src/model/loader.ts` + tests

---

### Task M3.2: Generate Typed Domain & Workflow Code
**Owner:** TypeScript Dev  
**Duration:** 3 days  
**Acceptance:** Generate `Account`, `PasswordReset` workflow, effect interfaces

**Subtasks:**
- [ ] Template generator (Handlebars or similar):
  - For each Entity → TypeScript class (fields, getters, setters)
  - For each Workflow → class with typed inputs/outputs/steps
  - For each Effect → interface (what it requires, what it returns)
  - For each Rule → function that evaluates condition
- [ ] Generate dependency injection setup (for adapters)
- [ ] Generate test fixtures (mock entities, helper functions)
- [ ] Example output:
  ```typescript
  class Account {
    id: string;
    email: string;
    registered: boolean;
    constructor(data) { ... }
  }
  
  class PasswordResetWorkflow {
    async execute(input: PasswordResetInput): Promise<PasswordResetOutput> {
      // Generated steps...
    }
  }
  ```

**Deliverable:** `implementations/typescript/src/codegen/` + generated example

---

### Task M3.3: Execute Same 5 Examples (TypeScript)
**Owner:** TypeScript Dev + QA  
**Duration:** 3 days  
**Acceptance:** TypeScript backend produces identical results to Python interpreter

**Subtasks:**
- [ ] Create fake adapters (same behavior as Python):
  - `AccountStoreAdapter` (in-memory)
  - `EmailDeliveryAdapter` (log-only)
  - etc.
- [ ] Run each of 5 examples
- [ ] Capture execution traces (state, outputs, rules, effects)
- [ ] Compare with Python results:
  - Same state transitions
  - Same final output
  - Same rule evaluations
  - Same effects called
- [ ] Document any differences (investigate + explain)

**Deliverable:** `implementations/typescript/tests/password-reset.test.ts` + 5 passing tests + comparison report

---

### Task M3.4: Equivalence Tests & Documentation
**Owner:** TypeScript Dev + QA  
**Duration:** 2 days  
**Acceptance:** Both backends provably equivalent; end-to-end docs

**Subtasks:**
- [ ] Create test harness:
  - Load model once
  - Run Python interpreter on 5 examples → capture results
  - Run TypeScript backend on 5 examples → capture results
  - Compare outputs (state, rules, effects, final output)
  - Emit equivalence report
- [ ] Document equivalence definition:
  - "Equivalent" = identical state transitions + observable outputs + rule checks
  - Not code shape, not performance
  - Differences documented if semantically non-breaking
- [ ] Write end-to-end walkthrough:
  - How to generate from model
  - How to run examples
  - How to compare backends
  - Where evidence is recorded

**Deliverable:** `tests/equivalence_test.py` + end-to-end guide

---

### M3 Exit Criteria

```bash
$ python tests/equivalence_test.py
✓ Python backend: 5/5 examples passed
✓ TypeScript backend: 5/5 examples passed
✓ Equivalence check: 100% (state, output, rules identical)
✓ Evidence records created for both backends
✓ Report: implementations/typescript/EQUIVALENCE-REPORT.md
```

**Effort:** ~10 days (2+3+3+2)  
**Owner Allocation:** TypeScript Dev 80%, QA 50%, Language Designer 10%

---

## M4: Evidence & Polish (Week 11-12) — Detailed Tasks

### Task M4.1: Evidence Records & Verification Results
**Owner:** Python Dev  
**Duration:** 2 days  
**Acceptance:** Every example run produces auditable evidence

**Subtasks:**
- [ ] Define evidence schema:
  ```json
  {
    "claim_id": "registered-address-success",
    "claim_text": "When registered address requests reset, email is sent",
    "model_id": "password-reset-v1",
    "execution_date": "2026-09-03T14:23:00Z",
    "tool_version": "orin-0.1.0",
    "inputs": { "address": "user@example.com" },
    "state_before": { "accounts": [...] },
    "state_after": { "accounts": [...], "tokens": [...] },
    "outputs": { "response": "standard-confirmation" },
    "rules_evaluated": [
      { "rule": "privacy", "result": "pass" },
      { "rule": "single-use", "result": "pass" }
    ],
    "effects_called": [
      { "effect": "lookup-account", "result": "found" },
      { "effect": "create-token", "result": "success" },
      { "effect": "send-email", "result": "success" }
    ]
  }
  ```
- [ ] Implement evidence recording in interpreter
- [ ] Implement evidence recording in TypeScript backend
- [ ] Generate evidence for all 5 examples
- [ ] Create verification report (all rules pass? all effects successful? anything blocked?)

**Deliverable:** `implementations/python/evidence.py` + recorded evidence files

---

### Task M4.2: Documentation & Walkthroughs
**Owner:** Language Designer  
**Duration:** 2 days  
**Acceptance:** New user can follow docs end-to-end without help

**Subtasks:**
- [ ] **README update:**
  - Link to MVP-PLAN.md
  - Quick-start: "How to run password-reset examples in 5 minutes"
  - Architecture diagram (model → parser → interpreter → evidence)
- [ ] **Implementation guide:**
  - How the semantic model works
  - How to add a new example
  - How to run both backends
  - How to interpret evidence
- [ ] **Example walkthroughs:**
  - Registered address (step-by-step)
  - Unknown address (what privacy guarantee holds?)
  - Email delivery failure (where does it fail? what's the output?)
  - Rate-limit blocking (why can't we compile?)
- [ ] **VS Code extension guide:**
  - How to use "Analyze Current File" command
  - What diagnostics mean (ORIN-EXXX codes)
  - How to fix errors
- [ ] **API documentation:**
  - Python: `semantic_model`, `parser`, `interpreter`, `evidence`
  - TypeScript: `model/loader`, `codegen`, `runtime`

**Deliverable:** Docs in `docs/IMPLEMENTATION-GUIDE.md`, README updates, code examples

---

### Task M4.3: Final Conformance Tests & CI/CD
**Owner:** QA  
**Duration:** 2 days  
**Acceptance:** Every commit verifies: parse, validate, run examples, equivalence, evidence

**Subtasks:**
- [ ] Create GitHub Actions workflow:
  ```yaml
  - Lint Python/TypeScript
  - Python: model validation
  - Python: parser test
  - Python: interpreter test (5 examples)
  - TypeScript: compile
  - TypeScript: backend test (5 examples)
  - Equivalence test
  - Evidence verification
  ```
- [ ] Add test coverage reports
- [ ] Add documentation validation (links, code snippets work)
- [ ] Test on Windows + macOS + Linux
- [ ] Document how to run locally:
  ```bash
  python -m pytest tests/
  cd implementations/typescript && npm test
  python tests/equivalence_test.py
  ```

**Deliverable:** `.github/workflows/main.yml` + CI status badge in README

---

### Task M4.4: Definition of Done Verification
**Owner:** Language Designer  
**Duration:** 1 day  
**Acceptance:** All 10 items demonstrable end-to-end

**Subtasks:**
- [ ] Create demo script that validates all 10 items:
  ```bash
  1. Open examples/password-reset.orin ✓
  2. Parse & understand purpose/rules ✓
  3. Run 5 examples (Python) ✓
  4. See rate-limit blocks compilation ✓
  5. Decide policy & recompile ✓
  6. Inspect evidence (JSON records) ✓
  7. Generate reference runtime ✓
  8. Generate TypeScript service ✓
  9. Compare observable behavior ✓
  10. End-to-end walkthrough docs ✓
  ```
- [ ] Record demo video (5-10 min) showing all 10 items
- [ ] Create MVP release notes (what works, what's known limitations)

**Deliverable:** `demo-script.sh` + release notes + (optional) demo video

---

### M4 Exit Criteria

```bash
$ ./demo-script.sh
✓ All 10 definition-of-done items verified
✓ Both backends pass all 5 examples
✓ Evidence records created and auditable
✓ Documentation complete and verified
✓ CI/CD green on all platforms
✓ MVP release ready
```

**Effort:** ~7 days (2+2+2+1)  
**Owner Allocation:** Python Dev 20%, TypeScript Dev 20%, QA 60%, Language Designer 50%

---

## Timeline Summary

```
Week 1-3   M1: Semantic Core     (~9 days)  
Week 4-7   M2: Parser & Interp   (~12 days)
Week 8-10  M3: TypeScript Backend (~10 days)
Week 11-12 M4: Evidence & Polish  (~7 days)
           Total: ~38 days ≈ 7.5 weeks (8-12 week estimate includes buffer)
```

---

## Risk Mitigation Quick Actions

| Risk | Detection | Mitigation |
|------|-----------|-----------|
| Semantic model changes late | Weekly model review | Freeze model after M1.4; changes require impact analysis |
| Parser too complex | End of M2.1 | Keep it thin; unsupported syntax → error, not feature |
| Backend divergence | Daily equivalence check | Write equivalence test first; both backends must pass it |
| Evidence overhead | M4.1 review | Evidence is structured JSON; no runtime cost analysis yet |
| Documentation lag | M4.2 start | Write docs as code is written; maintain example code snippets |

---

## Handoff Criteria (M4 → M5)

Before starting web profile or AI authoring:

- [ ] All 10 MVP definition-of-done items verified
- [ ] Both backends pass equivalence tests
- [ ] Evidence model works for audit trails
- [ ] Zero critical bugs
- [ ] Specification updated based on learnings
- [ ] Team comfortable with semantic model (won't need major changes for web profile)

**Timeline:** If M4 complete by week 12, earliest web profile start = week 13 (Phase 2)

---

**Questions to resolve before starting:**

1. **Token generation determinism:** How to ensure `generate-token()` produces same token when re-run? (Solution: deterministic seed based on email + timestamp)
2. **Rate-limit policy format:** JSON? Syntax in `.orin` file? (Suggest: structured; update model)
3. **Email adapter behavior:** Log to file? In-memory? (Suggest: both; configurable)
4. **TypeScript backend target:** Express server? Just classes? (Suggest: just classes + interfaces; deployment later)
5. **Evidence storage:** Local files? Database? (Suggest: local JSON files for MVP)

