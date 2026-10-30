# Development backlog and retained context

This folder is for **developing Orin**, not for defining an Orin program.
Plans, experiments, historical assessments, and internal tooling proposals
are not part of the language.

The [implementation log](../ORIN-0003-language-improvement-plan.md) is the
single place for completed work and the exact next step. The
[evolution roadmap](ORIN-0006-next-evolution-roadmap.md) is longer-term
context, not a second task queue.

## What to prioritize

Deepen the existing password-reset path: a novice describes a program,
reviews readable Orin, resolves consequential questions, generates an
implementation, and checks its observable behavior. Keep the existing other
applications as regression and evaluation material. A gap found in one
application is evidence to assess, not automatic permission for another
language feature or another example.

## Deferred reference material

| Material | Purpose |
| --- | --- |
| [ORIN-0004 semantic model](../ORIN-0004-semantic-model.md) | Proposed long-term language foundation; not a description of everything implemented today. |
| [Primary programming gap analysis](ORIN-PRIMARY-PROGRAMMING-GAP-ANALYSIS.md) | Broader completeness analysis retained for later evaluation. |
| [Shared-tasks application proposal](../../examples/docs/shared-tasks/design-proposal.md) | Deferred broader application design. |
| [Shared-tasks semantic audit](../../examples/docs/shared-tasks/semantic-audit.md) | Historical boundary evaluation and alignment findings. |
| [Supporting application guides](../../examples/README.md#supporting-applications) | Existing examples, evidence, and language/tool findings. |

Activate future work through the implementation log after showing how it
helps the main end-to-end proof. Do not treat older "next step" or delivery
dates in historical documents as current instructions.

## Retained MVP and refocus conclusions

These conclusions consolidate the former implementation roadmap, MVP plan,
and refocus assessment:

- Password reset remains the primary proof application before broader
  expansion.
- Consequential ambiguity must remain explicit and block generation until
  a person makes a decision.
- Generated implementations are replaceable evidence, not the source of
  project meaning.
- A reader must understand the accepted meaning without reading generated
  code.
- Conformance examples must run deterministically, and implementation
  variation must preserve the required observable behavior.

The [password-reset guide](../../examples/docs/password-reset.md) contains
the walkthrough and proof commands. The
[conformance index](../../tests/conformance/README.md) records evidence and
its limits; the narrow MVP result is not proof of a complete novice product
experience.

## Optional internal skills integration

The former skills integration note is retained here as a tooling boundary,
not a user requirement. Keep an integration only when it measurably improves
short reviewable proposals, generated-artifact review, or long-session
quality checks.

- No skill setup is required to understand `.orin` or inspect fixtures.
- Skills must not define or change semantic meaning.
- Skill integration does not demonstrate product completeness.
- Any executable wiring stays under the appropriate host-language tooling
  or implementation folder.
- `.orin`, the semantic model, and conformance fixtures stay language-neutral.
  Their behavior must be unchanged when optional skills are unavailable.
