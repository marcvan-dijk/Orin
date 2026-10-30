# Orin examples

These are **applications written in Orin**, not features or pricing plans for
Orin itself. Their purpose is to test whether readable, durable program
meaning can survive implementation changes.

## Primary path: password reset

Start with the [password-reset guide](docs/password-reset.md). It combines the
beginner walkthrough, proof and demo commands, and evidence boundaries in one
place. The readable program is [password-reset.orin](password-reset.orin).

The focus is to deepen this existing end-to-end proof: a person describes
the program, reviews the Orin, resolves important questions, and checks that
generated behavior matches it. The narrow MVP result is not proof of a
complete application or a successful real-user onboarding experience.

## Supporting applications

Keep these for regression checks and focused evaluation, not as parallel
product roadmaps.

| Program | Guide and purpose |
| --- | --- |
| [Expense approval](expense-approval.orin) | [Guide and accepted decision](docs/expense-approval.md): authorization, limits, and terminal decisions. |
| [Library lending](library-lending.orin) | [Guide and findings](docs/library-lending.md): deadlines, fees, reservations, and unresolved policies. |
| [Event booking](event-booking.orin) | [Findings](docs/event-booking.md): capacity, waiting lists, and cancellation refunds in the sample app. |
| [Subscription billing](subscription-billing.orin) | [Findings](docs/subscription-billing.md): recurring charges and lifecycle rules in the sample app. |
| [Shared tasks](shared-tasks.minimal.orin) | [Design and validation](docs/shared-tasks/README.md): relationships, authorization, and state changes; broader proposals remain deferred. |
| [Imports](imports/leave-request.orin) | A small module using [shared definitions](imports/shared-people.orin); import syntax is documented in the [grammar](../docs/ORIN-SYNTAX-GRAMMAR.md#imports). |

## Authoring exercises

[authoring/](authoring/README.md) contains small plain-English-to-Orin
exercises. They demonstrate readable authoring and explicit open questions;
they are not additional complete applications or new development workstreams.

## Where things belong

| Path | Contents |
| --- | --- |
| `examples/*.orin` | Existing application programs; stable paths used by tools and tests. |
| `examples/docs/` | Application guides, accepted domain decisions, and evaluation findings. |
| `examples/authoring/` | Small authoring exercises and their explanations. |
| `tests/conformance/` | Language-neutral models, decisions, observable cases, and evidence mapping. |
| `implementations/<language>/` | Executable backends, host-specific tests, dependencies, and setup. |

Language definitions and general authoring guidance are in
[docs/](../docs/README.md). Progress and priorities are recorded only in
[ORIN-0003](../docs/ORIN-0003-language-improvement-plan.md).
