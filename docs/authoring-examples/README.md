# Authoring examples

Each example is a plain-English request and the `.orin` file an AI should
write from it. See `../AUTHORING-WITH-AI.md` for the method.

All files load with the Orin checker. The only diagnostics are `ORIN-E041`,
one per open uncertainty. That is intended: the AI did not guess.

## 1. Tip calculator → `tip-calculator.orin`

> I want a small tool where I type in a restaurant bill, a tip percentage and
> how many people are at the table, and it tells me what each person pays.

What to notice:

- The person never said how to round, so it became `uncertainty rounding`.
- Numbers in the examples were chosen so a human can check them by hand.
- "At least 1 person" was not stated. It is a small, safe default, written as
  a rule so the person can see and change it.

## 2. Book lending → `book-lending.orin`

> Our book club has about 30 members and 200 books. I want to keep track of
> who has borrowed which book. Nobody should be able to hog books.

What to notice:

- "Hog books" became a limit rule (3 books). The number is a guess the
  person should confirm.
- Due dates and who may record loans change behaviour, so each is an
  `uncertainty`, not a silent choice.
- Names like `member-name` are plain `type` declarations; the AI did not
  invent storage, screens or technology.

## 3. Support tickets → `support-ticket.orin`

> We handle customer problems by email. I want each one tracked from when it
> comes in until it is fixed, and nothing should get lost.

Shape: a state machine. States and allowed moves are rules; skipping a step
is an example. Reopening a ticket is an `uncertainty`.

## 4. Document access → `document-access.orin`

> People in our company keep documents. Owners decide who can look at or
> change them. Others should not see what they have no right to.

Shape: access control. "Cannot see it exists" is a stated rule. Orphaned
documents and company-wide sharing are `uncertainty` items.

## 5. Invoice reminders → `invoice-reminders.orin`

> If a customer hasn't paid an invoice a week after it's due, remind them,
> but don't spam them.

Shape: time-based. Day counts and limits are rules; examples use concrete
dates. Time zone and weekends are `uncertainty` items.

## Test

`python implementations/python/test_authoring_examples.py` (from that folder)
parses every example and checks the only diagnostics are `ORIN-E041`, one per
`uncertainty`.

## Note on syntax

All five files use the outline style (`key: name`), the same layout as
`../../examples/password-reset.orin`. Older files may use a brace style
(`module name { ... }`); it still loads but is legacy. Do not write new files
in it.

## Check one file

From the repository root:

```text
python -m tooling.python.orin_cli check docs/authoring-examples/tip-calculator.orin
```

It lists each open uncertainty as `ORIN-E041`. That is expected here.
