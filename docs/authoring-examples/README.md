# Authoring examples

Each example is a plain-English request and the `.orin` file an AI should
write from it. See `../AUTHORING-WITH-AI.md` for the method.

Both files load with `implementations/python/orin_parser.py`
(`OrinParser().parse_file(path)`). The only diagnostics are `ORIN-E041`,
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

## Note on syntax

`../../examples/password-reset.orin` uses the readable outline style. The
current Python loader parses that style only for that one file. Any other
file must use the brace style shown here to load today.
