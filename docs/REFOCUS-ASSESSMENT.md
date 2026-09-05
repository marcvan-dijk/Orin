# Orin Refocus Assessment

## What Orin currently is

Orin is a language-neutral semantic-kernel prototype with a strong password-reset proof slice, post-MVP shared-tasks validation material, and substantial internal planning/spec material. The repository already shows deterministic model handling, consequential-uncertainty blocking, and host-language reference runtimes under `implementations/`.

## What Orin should become

Orin should be the primary human-readable program meaning, while generated source stays replaceable implementation detail. The near-term proof is narrow: a human-defined meaning model for password reset that is deterministic, ambiguity-gated, and implementation-equivalent across multiple targets.

## Component classification

| Component | Classification | Why |
|---|---|---|
| Core thesis (`README`, ORIN-0002/0004 concepts) | CORE | Defines Orin as meaning-first programming for AI-native software. |
| Password-reset `.orin` + conformance fixtures | CORE | Primary executable proof of intent, ambiguity gate, deterministic behavior. |
| Semantic model + canonicalization + diagnostics | CORE | Required to keep meaning stable and inspectable across frontends/backends. |
| Consequential uncertainty (`rate-limit` gate) | CORE | Demonstrates that unresolved consequential ambiguity blocks implementation. |
| Reference Python runtime/parser/validator | SUPPORTING | Practical host-language proof of semantics, not Orin itself. |
| Conformance infrastructure (`tests/conformance/*`) | SUPPORTING | Shared evidence contract for deterministic meaning and equivalence checks. |
| Lowering policy experiment | SUPPORTING | Shows implementation can vary while semantic behavior stays fixed. |
| Shared-tasks slice | ADVANCED | Useful post-MVP proof, but not the beginner or MVP center. |
| VS Code extension | SUPPORTING | Helpful authoring aid; not a completeness signal for Orin itself. |
| Julius Skills integration docs | INTERNAL | Internal AI workflow optimization; should not burden beginner path. |
| Large phase-by-phase expansion plans | DISTRACTION | Premature breadth weakens focus on proving the core hypothesis now. |

## Keep / simplify / strip / internalize

### Keep
- Password-reset as canonical first program.
- Semantic model and deterministic conformance orientation.
- Consequential ambiguity gate language and evidence framing.
- Host-language isolation under `implementations/<language>/`.

### Simplify
- Top-level positioning and onboarding around one proof path.
- MVP and roadmap docs to strict thesis validation scope.
- Beginner-facing vocabulary to purpose/rules/workflow/examples first.

### Strip
- Beginner-path references implying broad feature completeness.
- Premature multi-phase operational detail in primary planning docs.
- Example declarations that do not affect current semantic proof.

### Keep internal
- Deep compiler/lowering architecture detail.
- Julius Skills operational mechanics.
- Advanced shared-tasks expansion planning.

## MVP should prove

1. Humans can express program meaning (intent, rules, outcomes) in Orin for password reset.
2. Orin explicitly surfaces consequential ambiguity and blocks compilation until decided.
3. Accepted meaning is deterministic and testable via language-neutral conformance fixtures.
4. Different implementations can be derived without changing Orin meaning, and equivalent observable behavior provides evidence.
