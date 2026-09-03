# Orin MVP Project Plan

**Status:** Active  
**Goal:** Prove password-reset can be expressed in intent form, execute deterministically, and lower to 2 backends  
**Timeline:** 8-12 weeks  
**Success:** 10-item definition of done (see Section 4)

---

## 1. Scope: Password-Reset Only

### In Scope
- Semantic model for password-reset workflow
- Deterministic interpreter with fake adapters
- Python parser → semantic model
- 2 executable backends (reference + TypeScript)
- Example scenarios (registered, unknown, token-expired, email-fail, rate-limit-blocked)
- Evidence collection (what ran, what passed/failed)

### Out of Scope
- Web UI or form generation
- AI-assisted authoring
- Multi-user collaboration
- Other workflows/applications
- General programming language features
- Production deployment tooling

---

## 2. MVP Milestones (Simplified)

### M1: Semantic Core (Week 1-3)
**Done:** Model loads, validates, serializes cleanly

**Tasks:**
- [ ] Finalize semantic model JSON schema (Day 1-2)
- [ ] Identity/reference validation (Day 3-4)
- [ ] Capability & effect linking (Day 5-6)
- [ ] Error codes & diagnostics (Day 7)

**Exit:** Zero validation errors on `password-reset.model.json`

---

### M2: Parser & Interpreter (Week 4-7)
**Done:** `.orin` file → model → execution

**Tasks:**
- [ ] Complete `.orin` parser mapping (Day 1-3)
- [ ] Deterministic interpreter (state machine + adapters) (Day 4-7)
- [ ] Execute 5 core examples (Day 8-10)
- [ ] Rate-limit blocking (Day 11)

**Exit:** All 5 examples pass; rate-limit blocks compilation

---

### M3: Second Backend (Week 8-10)
**Done:** TypeScript backend produces equivalent results

**Tasks:**
- [ ] TypeScript semantic model loader (Day 1-3)
- [ ] Generate typed structures + workflow (Day 4-6)
- [ ] Run same 5 examples (Day 7-8)
- [ ] Equivalence tests (Day 9-10)

**Exit:** Both backends pass the same examples; observable behavior identical

---

### M4: Evidence & Polish (Week 11-12)
**Done:** Every check is auditable; release ready

**Tasks:**
- [ ] Evidence records (claim + inputs + outputs) (Day 1-3)
- [ ] Documentation & walkthroughs (Day 4-6)
- [ ] Final conformance tests (Day 7-8)

**Exit:** All 10 items in definition of done verified

---

## 3. Definition of Done (10-Item Gate)

A user can:

1. [ ] Open `examples/password-reset.orin`
2. [ ] Understand its purpose, rules, and workflow
3. [ ] Run 5 executable examples (registered address, unknown, expired token, email-fail, rate-limit-blocked)
4. [ ] See that rate-limit uncertainty blocks compilation
5. [ ] Decide the policy and recompile
6. [ ] Inspect evidence (what ran, what passed)
7. [ ] Generate reference runtime artifact
8. [ ] Generate TypeScript service artifact
9. [ ] Compare both artifacts' observable behavior (identical)
10. [ ] Document the full flow end-to-end

**Gate:** All 10 verifiable in <30 min demo

---

## 4. Minimal Resource Plan

| Role | Time | Responsibility |
|------|------|-----------------|
| You (Design) | 50% | Model decisions, semantic rules, spec updates |
| Python Dev | 60% | Parser, interpreter, validator |
| TypeScript Dev | 40% | Backend, test equivalence |
| QA | 20% | Conformance tests, example validation |

**Total:** ~2 FTE for 12 weeks

---

## 5. Immediate Next Steps (This Week)

1. [ ] Decide: JSON or YAML for model schema? (1 day decision)
2. [ ] Finalize 5 core examples (1-2 days)
3. [ ] Complete capability/effect linking in validator (2-3 days)
4. [ ] Test conformance fixtures end-to-end (1-2 days)

**Output:** Milestone 1 exit criteria met

---

## 6. Blockers & Risks

| Issue | Mitigation |
|-------|-----------|
| Semantic model still evolving | Freeze for M1; defer edge cases to Phase 2 |
| Parser/interpreter complexity | Keep both as thin as possible; focus on password-reset only |
| Backend equivalence undefined | Define "equivalent" = same observable state + outputs |
| Rate-limit blocking unclear | Make it a compilation error; no silent defaults |

---

## 7. Success Metric

**Can we build TWO different implementations of password-reset from the same intent specification and prove they behave identically?**

If yes → MVP success → ready for Phase 2 (web profile, AI authoring, etc.)

---

**Next sync:** After M1 completion  
**Repo home:** [Orin](https://github.com/marcvan-dijk/Orin)
