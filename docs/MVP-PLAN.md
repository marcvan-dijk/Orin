# Orin MVP Plan (Refocused)

## Thesis to prove

A human can define password-reset behavior in Orin meaning-first form, Orin can block unresolved consequential ambiguity, and multiple implementations can preserve the same observable behavior.

## In scope (strict)

- Password-reset as the primary and only required beginner slice.
- Language-neutral semantic fixture and executable conformance cases.
- Deterministic semantic checks and canonicalization.
- Consequential ambiguity gate (`rate-limit`) that blocks compilation.
- At least one reference execution path plus implementation-equivalence evidence.

## Out of scope (for this MVP)

- Broad domain expansion.
- Full profile surface (web UI/deployment breadth).
- Feature-complete IDE experience.
- Operationally detailed AI-skill workflows in the primary user path.

## MVP acceptance gate

1. Password-reset meaning is understandable from Orin artifacts without reading generated code.
2. Unresolved consequential ambiguity is surfaced and blocks compile/readiness.
3. Conformance examples run deterministically.
4. Semantic meaning remains stable under non-semantic formatting changes.
5. Implementation variation does not change required observable behavior.

## Director 1-day demo gate (hard)

Pass this increment only when all of the following are true in a single 1-day run:

1. The demo stays on password-reset only (no shared-tasks or broader profile slices).
2. The `rate-limit` consequential decision is explicit, human-chosen, and recorded in project artifacts (ORIN-0001 decision-completion).
3. Readiness/compile blocks until any consequential ambiguity is resolved; no silent defaults.
4. Deterministic conformance evidence is produced for the password-reset MVP proof path.

If any gate item fails, STOP. Fix only the missing gate evidence; do not start post-MVP implementation work.

## Immediate execution order

1. Keep password-reset docs and fixtures as the canonical path.
2. Keep semantic checks focused on deterministic meaning and ambiguity gating.
3. Keep implementation experiments internal to `implementations/<language>/`.
4. Treat shared-tasks and broader application modeling as advanced follow-up.
