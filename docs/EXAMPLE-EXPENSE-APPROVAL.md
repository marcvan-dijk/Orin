# Example: Expense Approval

A second small Orin program, showing the model works beyond password reset.

Files:
- `examples/expense-approval.orin` — the human-authored program
- `tests/conformance/expense-approval.structured.json` — structured semantic form
- `tests/conformance/expense-approval.model.json` — compact model
- `tests/conformance/expense-approval.cases.json` — observable cases

## Durable meaning

- An expense is approved only by an approver whose limit covers its amount.
- Nobody approves or rejects their own expense.
- A decision is final.
- A rejection carries a reason the submitter can see.

## Unresolved decision

`no-eligible-approver`: what happens when nobody except the submitter has a
limit covering the amount? (escalate, reject, or hold). It is consequential and
human-owned, so the program is **blocked** until it is decided.

## Check

```
python implementations/python/orin_agent_core.py inspect tests/conformance/expense-approval.structured.json
```
