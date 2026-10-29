# Example: library lending

A stress test of the novice flow. English source paragraph:

> Members borrow books for 14 days. If a loan is returned late, a late fee
> accrues per day, capped at the book's price. Members with too many unpaid
> fees cannot borrow. Members can reserve a book that is out; when it comes
> back it is held for the first in the queue.

- Program: `examples/library-lending.orin`
- Decisions sidecar: `tests/conformance/library-lending.decisions.json`
  (the tools read it only when it sits next to the `.orin`; see gap 3)
- Decided model: `tests/conformance/library-lending.decided.json`

Open decisions: `reservation-hold-expiry` and `renewal-with-reservation`
(blocking), `lost-book-fee` (non-blocking, no options). Chosen in the decided
model: expire holds after 3 days; refuse renewal while a reservation exists.

Commands: `orin_cli check|readiness|inspect examples/library-lending.orin`, then
`decide ... --option <id> --out <file>`. Findings are in `LANGUAGE-GAPS-FOUND.md`.
