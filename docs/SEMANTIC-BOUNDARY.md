# Semantic Boundary: Durable Meaning vs. Scaffolding

This note defines what Orin must preserve from the password-reset proof and what can vary.

## Classification table

| Category | Keep in canonical meaning? | Password-reset examples |
| --- | --- | --- |
| Durable project meaning | Yes | Module purpose, privacy/token rules, observable example outcomes, unresolved consequential uncertainty (`rate-limit`), authority=`human` |
| Implementation scaffolding | No (optional tooling/implementation layer) | Workflow step prose, value-types, state declarations, capabilities/effects, rule category tags, dependency/link arrays |
| Process/provenance/history | No (external records) | Status fields, model/fixture versioning, evidence bookkeeping objects, traceability metadata |

## Five critical audit questions

1. **If this field changes, does required observable behavior change?**
   - If yes, it is durable meaning.
2. **Does this field encode an accepted consequential decision?**
   - If yes, preserve it durably and prevent silent AI guessing.
3. **Can two correct implementations differ on this field while passing the same behavioral cases?**
   - If yes, it is implementation freedom/scaffolding.
4. **Is this field mainly for collaboration history or traceability?**
   - If yes, keep it outside minimal canonical meaning.
5. **Can readiness/blocking be derived from model content instead of stored status?**
   - Yes. Compilation is computed from unresolved consequential uncertainties.

## What can be removed without breaking the proof

The proof still holds after removing non-semantic metadata such as object `status`, `kind` tags in password-reset fixture, rule `category`, dependency/provenance arrays, and stored compilation state. The blocked/eligible gate is computed from unresolved consequential uncertainty, while observable behavior cases remain unchanged.
