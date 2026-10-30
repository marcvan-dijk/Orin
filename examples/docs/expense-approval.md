# Expense approval

This small application tests durable meaning beyond password reset. Reading
the program and fixtures requires no host runtime; the commands below use the
optional Python tooling and run from the repository root.

## Program and fixtures

- [Human-authored program](../expense-approval.orin)
- [Structured semantic form](../../tests/conformance/expense-approval.structured.json)
- [Compact model](../../tests/conformance/expense-approval.model.json)
- [Observable cases](../../tests/conformance/expense-approval.cases.json)
- [Resolved model](../../tests/conformance/expense-approval.resolved.model.json)
- [Resolved cases](../../tests/conformance/expense-approval.resolved.cases.json)

## Durable meaning

- An expense is approved only by an approver whose limit covers its amount.
- Nobody approves or rejects their own expense.
- A decision is final.
- A rejection carries a reason the submitter can see.

## Unresolved model and accepted decision

The original model leaves
`finance.expense-approval/uncertainty/no-eligible-approver` unresolved: what
happens when nobody except the submitter has a limit covering the amount?
Escalate, reject, or hold are consequential alternatives requiring human
authority. That model is **blocked** until the question is decided.

Inspect it:

```text
python implementations/python/orin_agent_core.py inspect tests/conformance/expense-approval.structured.json
```

### Accepted policy: hold the expense

When no one other than the submitter has a limit covering the amount, the
expense stays `submitted`. It is not approved, rejected, or escalated
automatically; it can be decided once an eligible approver exists.

Why:

- Rejecting would record a decision nobody with authority made, and
  `decision-is-final` would make it unrecoverable.
- Escalation needs an authority hierarchy the model does not define.
- Holding preserves `approver-limit-covers-amount` and `no-self-decision`
  without inventing new concepts.

The resolved model records rule `uncovered-expense-is-held` and example
`no-eligible-approver`; the resolved cases make the observable outcome explicit.
The unresolved source/model and resolved fixture are different artifacts:
recording a decision in one does not silently resolve the others.

## Supporting demos and evidence limits

```text
python -m tooling.python.demo_novice_flow --app expense-approval
python -m tooling.python.demo_decision_change --app expense-approval
```

The [scripted novice flow](password-reset.md#automated-novice-flow) checks the
source, applies options to the conformance model with its decisions sidecar,
generates Python, and replays the resolved cases. It chooses the first offered
option that does not keep compilation blocked; that alone does **not** prove
the option's behaviour is implemented.

The original [decision-change experiment](password-reset.md#decision-change-evidence)
found a **negative result**: the Python hand-written template produced zero
changed lines between escalate, reject, and stay-submitted, because it ignored
the option. All ten shared cases passed under all choices because they encoded
stay-submitted. Demo-only probes showed escalate/reject still left the expense
submitted. TypeScript generation accepted only stay-submitted. The agent
prompt offered only escalate/reject, so the experiment used the shipped
resolved model for its stay-submitted comparison.

These are bounded experimental findings, not new policy or roadmap
instructions. A recorded option is not evidence that generated behaviour
realises it; escalate/reject needed human implementation in that experiment.
