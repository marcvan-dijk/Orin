# Decision: expenses with no eligible approver are held

Resolves `finance.expense-approval/uncertainty/no-eligible-approver`.

**Decision.** When no one other than the submitter has a limit covering the
amount, the expense stays `submitted`. It is not approved, rejected, or
escalated automatically; it can be decided once an eligible approver exists.

**Rationale.**
- Rejecting would record a decision nobody with authority made, and
  `decision-is-final` would make it unrecoverable.
- Escalation needs an authority hierarchy the model does not define.
- Holding preserves `approver-limit-covers-amount` and `no-self-decision`
  without inventing new concepts.

**Where it lives.** Rule `uncovered-expense-is-held` and example
`no-eligible-approver` in `tests/conformance/expense-approval.resolved.model.json`;
cases in `expense-approval.resolved.cases.json`.
