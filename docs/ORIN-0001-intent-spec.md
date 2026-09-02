# ORIN-0001: Pairing Protocol

**Status:** Proposed
**Version:** 0.1.0
**Audience:** Humans and AI systems collaborating on any software artifact

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**,
and **MAY** in this document are to be interpreted as described in BCP 14
(RFC 2119 and RFC 8174) when, and only when, they appear in all capitals.

## Abstract

ORIN-0001 defines the smallest reviewable unit of human-AI pair programming: a
**pairing exchange**. An exchange records what the human wants, what the AI
believes that means, what remains uncertain, what was proposed, and what the
human accepted.

The resulting artifact may be code, configuration, a test, a design, a query,
or a future Orin program. The artifact is a projection of the exchange, not its
authoritative source.

## Design goals

- Keep human intent and AI interpretation distinct.
- Make uncertainty visible before an irreversible action.
- Preserve human authority over goals, constraints, and acceptance.
- Allow the output medium to be selected per task.
- Produce a durable trail of decisions and evidence.

Non-goals for version 0.1 are a new programming language, a required data
format, automatic deployment, and a complete domain-modeling notation.

## Exchange model

Each exchange MUST contain:

| Element          | Meaning                                               |
| ---------------- | ----------------------------------------------------- |
| `goal`           | The human's desired outcome                           |
| `context`        | Relevant system, domain, and repository facts         |
| `scope`          | Included work, excluded work, and affected boundaries |
| `constraints`    | Invariants, policies, budgets, and requirements       |
| `risks`          | Potential harm, failure modes, and impact             |
| `roles`          | Human authority, AI role, and delegated capabilities  |
| `interpretation` | The AI's current understanding                        |
| `uncertainties`  | Questions or assumptions that could change the result |
| `proposal`       | A concrete artifact change and its intended effect    |
| `decision`       | Human approval, rejection, revision, or delegation    |
| `acceptance`     | Observable conditions for success                     |
| `evidence`       | Checks and results connected to the artifact          |

An exchange MAY use any serialization. A representation MUST preserve ordering,
authors, revisions, and the distinction between statements, proposals, and
decisions.

The protocol SHOULD use the following requirement shapes:

- **goal:** who wants what, and why
- **constraint:** what MUST or MUST NOT be true
- **example:** Given a known context, when an event occurs, then an observable
  outcome follows
- **risk:** what can go wrong, for whom, and with what severity
- **decision:** which authority chose among alternatives and why

Examples SHOULD be short, domain-level, and observable. They SHOULD avoid
implementation details and SHOULD be executable by an adapter when practical.
Three to five steps is a useful default for one example; larger behavior SHOULD
be split into multiple examples or rules.

## Workflow semantics

An exchange is a workflow, not a transcript. It MUST preserve the causal order
of its meaningful events while MAY omit conversational tokens that do not change
intent, authority, or evidence.

The minimum lifecycle is:

```text
captured -> interpreted -> clarifying -> proposed -> decided -> verified -> accepted
                                      \-> rejected
                                      \-> abandoned
```

- `captured`: the human goal and context are recorded.
- `interpreted`: the AI states its understanding and separates facts from
  inferences.
- `clarifying`: consequential uncertainties are open.
- `proposed`: a bounded change, alternatives, risks, and expected effects are
  stated.
- `decided`: a human or explicitly delegated authority chooses what may happen.
- `verified`: checks have produced evidence.
- `accepted`: the human accepts the result as satisfying the goal.
- `rejected`: the proposal or its evidence is declined.
- `abandoned`: work stops without acceptance.

Every transition MUST have an actor, a timestamp, and a reason. A transition
MAY be retried, but repeating it MUST be idempotent or produce a new revision.
A consequential action MUST declare its rollback or recovery strategy before
execution, unless the human explicitly accepts that it is irreversible.

Delegation MUST be explicit about the authority, capability, scope, expiry, and
revocation rule. Delegation to an AI MUST NOT include authority to redefine the
human goal or acceptance criteria.

## Normative behavior

1. The AI MUST separate observed facts from inferences and proposals.
2. The AI MUST surface uncertainty that could affect behavior, security,
   privacy, cost, or data loss.
3. The AI MUST ask for clarification rather than silently choose a consequential
   default.
4. A proposal MUST state its intended effect and the acceptance conditions it
   claims to satisfy.
5. Only a human decision or an explicitly delegated policy can authorize a
   consequential proposal.
6. Verification MUST report `pass`, `fail`, or `blocked`, with evidence.
7. A failed or blocked check MUST prevent the artifact from being presented as
   accepted.
8. Every artifact MUST retain enough provenance to identify the exchange,
   proposal revision, and verification results.
9. Verification SHOULD include environment, tool, input, and version details
   sufficient to reproduce the check.
10. Evidence MUST distinguish an observed result from an AI inference or a human
    assertion.

## Example session

The canonical session is [`examples/password-reset.orin`](../examples/password-reset.orin).

```text
goal: Let a person recover an account without revealing whether it exists.
context:
  repository: Orin
  risk: Account enumeration and reset-token abuse
scope:
  includes: Password-reset request behavior
  excludes: Email-provider selection and account recovery UI
constraints:
  - Reset tokens expire after 15 minutes.
  - Reset tokens are single-use.
risks:
  - impact: Account takeover or account enumeration
    severity: high
roles:
  human: Owns the goal, constraints, and acceptance decision.
  ai: May propose changes and run delegated checks.
interpretation:
  outcome: Registered and unknown addresses receive indistinguishable responses.
uncertainties:
  - question: What rate limit applies per address and network origin?
    authority: human
proposal:
  artifact: implementation-independent behavior
  guarantees:
    - Reset tokens expire after 15 minutes.
    - Reset tokens are single-use.
decision: pending
acceptance:
  - Registered and unknown addresses produce the same response.
evidence: blocked until the rate-limit decision is resolved.
```

## Conformance evidence

A conforming implementation produces an evidence record containing:

- the exchange and proposal revisions
- the resulting artifact identifiers or content hashes
- check results and their timestamps
- unresolved questions and their disposition
- human decisions and the identities that made them

Evidence is append-only for a release. Corrections create a new record rather
than rewriting a previous result.

Evidence SHOULD be modeled as relationships among at least these roles:

- **entity:** a goal, proposal, artifact, input, or result
- **activity:** an interaction, transformation, or verification
- **agent:** a human, AI, tool, or external system responsible for an activity

This keeps provenance useful without requiring one serialization or one trust
model. Cryptographic signing, content hashes, access control, and retention
policy are profile choices and MUST be selected for the risk of the exchange.

## Design lineage

ORIN-0001 combines established practices while keeping their implementation
choices optional:

- [BCP 14](https://www.rfc-editor.org/info/bcp14) supplies precise normative
  requirement words.
- [Gherkin](https://cucumber.io/docs/gherkin/reference/) supplies short,
  domain-readable Given/When/Then examples and observable outcomes.
- [BPMN](https://www.omg.org/spec/BPMN/2.0/) supplies the principle that a
  workflow can be understandable to stakeholders and independent of its
  implementation environment.
- [JSON Schema](https://json-schema.org/learn/getting-started-step-by-step)
  supplies the distinction between a document and constraints on that
  document; ORIN-0001 intentionally does not require JSON.
- [NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final) supplies the need to
  integrate security practices throughout development rather than bolt them on
  at the end.
- [W3C PROV](https://www.w3.org/TR/prov-overview/) supplies the entity,
  activity, and agent vocabulary for provenance; ORIN-0001 uses the concept
  without requiring RDF or a graph database.

ORIN-0001 does not attempt to replace these standards. It composes their most
useful ideas around the missing collaboration boundary: how a human and an AI
reach, authorize, revise, and verify a decision together.

## Open questions for the next revision

- Should contracts use YAML, JSON, or a dedicated human-friendly format?
- How should an exchange compose across service and organizational boundaries?
- Which profiles are needed for low, medium, and high-risk work?
- How should human identity, AI identity, and delegated authority be represented?
- Which invariants can be checked statically, and which require execution?
- How should a human revoke approval after an artifact or environment changes?

## First research milestone

Collect ten real human-AI programming sessions and test whether the protocol
captures the decisions that matter without recording every conversational
token. From those sessions, define:

1. the smallest exchange state machine,
2. the minimum durable record for replay and review, and
3. the boundary between human authority and delegated AI action.

Do not commit to a programming language until these boundaries are stable.
