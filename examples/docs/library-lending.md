# Library lending

This example stress-tests the novice flow from an English request:

> Members borrow books for 14 days. If a loan is returned late, a late fee
> accrues per day, capped at the book's price. Members with too many unpaid
> fees cannot borrow. Members can reserve a book that is out; when it comes
> back it is held for the first in the queue.

## Program and decisions

- [Human-readable program](../library-lending.orin)
- [Decisions sidecar](../../tests/conformance/library-lending.decisions.json)
- [Decided model](../../tests/conformance/library-lending.decided.json)

The open decisions are `reservation-hold-expiry` and
`renewal-with-reservation` (blocking), plus `lost-book-fee` (non-blocking, with
no options). The decided model chooses to expire holds after three days and
refuse renewal while a reservation exists.

Reading these files requires no host runtime. For the optional Python tools,
run from the repository root:

```text
python -m tooling.python.orin_cli check examples/library-lending.orin
python -m tooling.python.orin_cli readiness examples/library-lending.orin
python -m tooling.python.orin_cli inspect examples/library-lending.orin
```

The decision command shape is
`python -m tooling.python.orin_cli decide <file> --option <id> --out <file>`.
This is not a guaranteed end-to-end generation recipe: the historical
experiment found sidecar-discovery and decision-chaining limitations below.
In particular, its tools read the sidecar only beside the `.orin` source,
not at the linked conformance location.

## Historical stress-test findings

This section consolidates the original language/tool gap report. Its method
was English paragraph → outline-style source → conformance decisions sidecar →
`python -m tooling.python.orin_cli check/readiness/inspect/decide/generate/examples`.
Core code was not changed during that experiment.

**These are historical findings, not a current bug inventory or roadmap
instructions.** Reproductions, error text, severity, and possible remedies
record what the experiment found or proposed; they do not establish that
today's tools still behave that way. Only item 5 was explicitly marked
completed in the original report. No new syntax or implementation work is
requested here.

### High-severity findings

1. **Two blocking uncertainties crashed validation with `ORIN-E004`.**
   `orin_cli check examples/library-lending.orin` with two `uncertainty:`
   blocks marked `blocking: yes` reported
   `duplicate object identity: library-lending/evidence/blocked`.
   Making one `blocking: no` removed the error. This was the highest-ranked
   finding because a real program can have several consequential decisions;
   it was also noted in the syntax grammar. The report proposed deriving the
   evidence identity from the uncertainty identity.

2. **Generation was hardcoded to two modules.**
   `generate tests/conformance/library-lending.decided.json --target typescript --out X`
   reported
   `no generator for module "library-lending/module"; supported: account.password-reset/module, finance.expense-approval/module`.
   Python instead reported
   `model is missing required object: account.password-reset/workflow/request-reset`,
   assuming password reset without identifying the real cause.
   `generate examples/library-lending.orin ...` reported
   `generate needs a semantic model .json file`.
   The proposed alternatives were a generic model-derived skeleton or a
   consistent “no generator for module X” diagnostic for every target.

3. **Sidecar discovery missed the conformance location.**
   With only `tests/conformance/library-lending.decisions.json`,
   `inspect examples/library-lending.orin` said “Options: none defined yet”.
   Copying the sidecar to `examples/library-lending.decisions.json` worked;
   the experiment removed that copy afterwards. The proposed remedies were
   searching `tests/conformance/` or accepting `--decisions PATH`.

4. **Decisions could not be chained.**
   After `decide ... --option expire-after-3-days --out a.json`,
   `decide a.json --uncertainty <other> --option refuse-renewal --out b.json`
   reported `unknown decision option 'refuse-renewal'`: sidecar lookup used
   the new basename (`a.decisions.json`). Parallel decisions on the original
   source also created independent models needing manual merging. The report
   proposed embedding options in the decided model.

### Medium-severity findings

5. **[done in the original report] Outline syntax for R020/R021/R040/R050.**
   Initially, after both decisions, readiness still blocked with fourteen
   items: workflow failure behaviour, recovery, postconditions, and
   rule-to-example links (eight rules after decision-created additions).
   The language reference listed these concepts but the outline could not
   express them. The reported resolution added `failure:`, `recovery:`,
   `after:` under `workflow:` and `proved-by:` under a rule. The example then
   cleared those fourteen diagnostics until decisions introduced rules
   without evidence links; decision-created rules still needed `evidenceLinks`.
   The original alternatives had been explicit syntax or automatic linking
   when an example mentions a rule.

6. **Decision hints disagreed on flags.**
   `check` suggested `decide F --option <id> --out library-lending.decided.json`,
   but `inspect` and the README mentioned `--write`. Agent-core
   `decide -h` showed `--write`, while `orin_cli decide ... --write X` failed
   because it required `--out`. The proposed remedy was one flag name.
   These are different command surfaces; use the documented command's own
   flags rather than interchanging them.

7. **Decision context was missing from outline authoring.**
   “Why it matters” repeated the question and “Affected objects” was empty
   without a sidecar. A novice could not supply either in the outline.
   The report proposed inline `why:` and `affects:` on `uncertainty:`.

8. **Generated rule identities depended on wording.**
   Truncated slugs such as `a-loan-has-a-due` and
   `a-member-with-unpaid-fees` changed when prose changed, while sidecar
   `affected_objects` had to guess them. The report proposed explicit
   `rule: name -` labels in the `rules:` list.

### Low-severity findings

9. **Quantities were free text.** “14 days”, fee cap, fee limit, and “3 days
   overdue” were not values the example checker could use. Typed constants,
   for example `constant: loan-days 14 days`, were a proposed remedy, not
   syntax introduced by this guide.

10. **Check and readiness used confusingly different gates.**
    The same file could be “valid (compilation: eligible)” in `check` but
    “BLOCKED” in `readiness`. The proposed remedy was a one-line readiness
    pointer.

11. **Missing runnable cases did not fail.**
    `examples` exited `0` with “No examples found”, listing
    `tests/conformance` twice in its `<name>.cases.json` search. In-source
    `example:` blocks had no conversion to runnable cases. A successful
    command exit was therefore not evidence of exercised behaviour.

12. **The non-blocking question remained only a note.**
    `lost-book-fee` had no route to options through `decide` and was silently
    omitted from the decided model. The selected hold/renewal policies do not
    establish that this separate uncertainty was resolved.
