# Authoring Orin with an AI assistant

Instructions for any AI assistant. A person describes in plain English the
program they want. You write a readable `.orin` file that states what the
program must do. Implementation starts only after the person has read it.

Orin holds durable meaning: purpose, rules, observable examples, and open
questions. It is not a plan, a task list, or a design for how to build it.

## Steps

1. Read the request. Find the purpose, the rules, and concrete cases.
2. Ask the person questions (see below) only when needed.
3. Write the `.orin` file.
4. Self-check (see below).
5. Show the file. Explain it in two or three plain sentences. List the open
   uncertainties and ask the person to decide them.

## Syntax cheat sheet

Use the brace style. The current Python loader reads this style for any
file. (`examples/password-reset.orin` uses the outline style, which the
loader accepts only for that file. Same ideas, different layout.)

```text
module my-program {
  purpose "One sentence on why this exists."

  type thing-name                      // a plain kind of value

  entity thing {                       // something with identity
    field name thing-name identity
  }

  relation owned-by {
    from thing
    to other-thing
    cardinality many-to-one            // one-to-one, one-to-many,
  }                                    // many-to-one, many-to-many

  rule short-name {
    guarantee "Something that must always be true."
  }

  workflow do-something {
    input some-value
    outcome "What the person observes when it finishes."
  }

  example happy-case {
    given "The starting situation, with real values."
    when "What the person does."
    then "What they observe, with real values."
  }

  uncertainty open-question {
    question "A decision that changes behaviour and is not yet made."
  }
}
```

Rules of the format:

- Names use lowercase letters, digits, `-` and `.`. No spaces.
- Text sits in double quotes, on one line.
- `//` starts a comment line.
- Allowed inside `rule`: `guarantee`. Inside `workflow`: `input`,
  `outcome`, `recovery`. Inside `example`: `given`, `when`, `then`.
  Inside `uncertainty`: `question`, `impact`.
- Only use `type`, `entity`, `relation` when the idea matters to the
  person. Many programs only need `purpose`, `rule`, `example`,
  `uncertainty`.
- Order: `module`, `purpose`, types/entities, rules, workflows, examples,
  uncertainties.

## What goes in, what stays out

Put in:

- Rules: things that are always true or never allowed.
- Examples: concrete situations with real numbers or names, and the
  observable result.
- Uncertainties: decisions that change what a user sees or what is allowed.

Leave out:

- Technology choices, languages, databases, screens, file layout.
- Steps, plans, tasks, schedules, who does what.
- Status, dates, authorship, notes about this conversation.

If something is only a way of building the program, it is not Orin.

## Uncertainties instead of guessing

When the request does not settle something, ask: *would two reasonable
builders produce visibly different behaviour?* If yes, it is consequential.

- Do not pick an answer silently. Write an `uncertainty` with the question
  in plain words, and `impact` if useful.
- Do not write a rule that hides the guess as a fact.
- Small safe defaults (a count must not be negative) may become rules. Say
  so when you show the file, so the person can change them.
- If you are told the answer later, delete the `uncertainty` and write the
  answer as a `rule` and an `example`.
- Do not fill the file with trivia. Keep uncertainties to real decisions.
  Three to five is typical for a small program.

Typical consequential topics: who is allowed, what is limited and by how
much, what happens at the edge (empty, too many, late, repeated), what is
remembered and for how long, what is shown to whom, how money or time is
rounded.

## Asking the human

- Ask at most three questions at a time, in plain words, no Orin terms.
- Prefer questions answerable with an example: "If a member already has
  three books and asks for a fourth, what should happen?"
- Offer two or three options when you can, plus "not sure yet". "Not sure"
  becomes an `uncertainty`.
- If the request is clear enough to write a first draft, write it, and put
  the questions as uncertainties. A draft is easier to react to than a quiz.
- Never ask about technology unless the person raises it.

## Self-check before showing the file

1. Every `module` has a `purpose` of one sentence.
2. Each rule is something you could test with an example.
3. At least two examples: one normal, one edge or refusal. They use real
   values and the results are correct by hand.
4. No example contradicts a rule.
5. Every consequential gap is an `uncertainty`, not a guess.
6. Nothing in the file is a task, a plan, or a technology choice.
7. A non-programmer could read it and say "yes, that is what I meant".
8. It loads. If Python is already available, run from the repository root:

   ```text
   python -c "import sys; sys.path.insert(0,'implementations/python'); \
   from orin_parser import OrinParser; \
   m = OrinParser().parse_file('PATH/TO/FILE.orin'); \
   print([(d.code, d.message) for d in m.diagnostics()])"
   ```

   Expected: only `ORIN-E041` (open uncertainty) entries. Any other code
   means a syntax or reference mistake. Fix it and run again. Do not
   install anything just for this check; if no tool is available, check by
   hand against the cheat sheet.

## Handing over

Implementation work should begin only when the person has read the file
and either resolved the uncertainties or explicitly accepted building
around them. Orin files stay the source of truth: if behaviour changes,
change the `.orin` first.

See `authoring-examples/` for two complete requests and their results.
