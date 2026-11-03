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

Use the outline style: `key: name`, then indented lines. This is the
standard layout. (An older brace style, `module name { ... }`, still loads
but is legacy. Do not write new files in it.) See
`examples/password-reset.orin` and `examples/shared-tasks.minimal.orin`.

```text
module: my-program

purpose:
  One sentence on why this exists.

rules:
  - Something that must always be true.
  - Something that is never allowed.

workflow: do-something
  input:
    some-value
  output:
    What the person observes when it finishes.

example: happy-case
  given:
    The starting situation, with real values.
  when:
    What the person does.
  then:
    What they observe, with real values.

uncertainty: open-question
  blocking: yes
  question:
    A decision that changes behaviour and is not yet made.
```

Rules of the format:

- Names use lowercase letters, digits, `-` and `.`. No spaces.
- A `key:` line starts at the left edge. Its content is indented by two
  spaces underneath it.
- Text is plain sentences. No quotes needed.
- `rules:` is a list; each item starts with `- `.
- Inside `workflow`: `input:` and `output:`. Inside `example`: `given:`,
  `when:`, `then:`. Inside `uncertainty`: `blocking: yes` and `question:`.
- Only add `type`, `entity`, `relation` when the idea matters to the
  person (see `examples/shared-tasks.minimal.orin`). Many programs only
  need `purpose`, `rules`, `example`, `uncertainty`.
- Order: `module`, `purpose`, rules, workflows, examples, uncertainties.

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
8. It loads. From the repository root run:

   ```text
   python -m tooling.python.orin_cli check PATH/TO/FILE.orin
   ```

   Expected: only `ORIN-E041` (open uncertainty) lines. Any other code
   means a syntax or reference mistake. Fix it and run again. Do not
   install anything just for this check; if Python is not available, check
   by hand against the cheat sheet.

## From draft to code

A draft with open uncertainties is not ready to build. Close each one in
one of two ways.

**A. Close it by hand.** The person decides. Then:

1. Delete the `uncertainty:` block.
2. Add the answer as a line under `rules:`.
3. Add an `example:` that shows it with real values.
4. Run `check` again. The `ORIN-E041` line for it should be gone.

**B. Let the agent decide from options.** Give the person two or three
choices, each with what it would change. Then record the choice and let the
tool update the model.

Options live in a file next to the model, named `<name>.decisions.json`
(for example `expense-approval.decisions.json`). The key is the full id of the
open question: `<module>/uncertainty/<name>`. A short name is not accepted.
Worked example for `signup.model.json`, saved as `signup.decisions.json`:

```json
{
  "decisions": {
    "event-signup/uncertainty/full-event": {
      "why_it_matters": "Decides what a person sees when the event is full.",
      "options": [
        {
          "id": "waitlist",
          "label": "Put the person on a waiting list.",
          "impact": ["Signup has a third outcome: waitlisted"],
          "rule_claims": [
            "When an event is full, a new signup is added to the waiting list."
          ]
        },
        {
          "id": "refuse",
          "label": "Refuse the signup with a clear message.",
          "impact": ["Signup is refused when the event is full"],
          "rule_claims": [
            "When an event is full, a new signup is refused."
          ]
        },
        {
          "id": "defer",
          "label": "Not decided yet.",
          "impact": [],
          "compilation": "blocked"
        }
      ]
    }
  }
}
```

Each option has an `id`, a `label`, its `impact`, and the rules it adds
(`rule_claims`). An option marked `"compilation": "blocked"` keeps the
question open. More detail: `tooling/python/README.md`. Run `inspect` to
check the file: the options should be listed.

You can also write the options inside the `.orin` file with `why:`, `affects:`
and `option: <text>` lines under the open question. Then no sidecar file is needed.

Then, from the repository root:

```text
python -m tooling.python.orin_cli check FILE
python -m tooling.python.orin_cli readiness FILE
python -m tooling.python.orin_cli decide MODEL --uncertainty NAME --option ID --write OUT
python -m tooling.python.orin_cli generate MODEL --decision ID --target python --out DIR
```

- `new NAME [--out DIR]` writes a small valid starter `.orin` file. Edit it,
  then run `check`. (The starter uses the older brace layout. Rewrite it in
  outline style, as in the cheat sheet above.)
- `check` finds mistakes and lists open questions.
- `readiness` says ready or blocked, and which decisions are still needed.
- `decide` applies one chosen option and writes the updated model.
- `generate` builds code (`--target python` or `typescript`) once nothing
  blocks it. `--decision` is an option id or a `.json` file like
  `{"option": "<id>"}`. For the example programs
  it writes full code. For your own program it writes a generic skeleton: one
  function per rule, a state machine from the workflow, and the examples as
  checks. Rules it cannot turn into code raise `NotImplementedRule`.

`check` and `readiness` take a `.orin` file or a model file. `generate` takes a model file
(`*.model.json`), the machine-readable form of the program. Run
`decide --help` for the current options. Exit code `0` means ready; `2` means a decision is still needed.
`orin_agent decide` is the same step and exits `4` when the decision is
accepted; `orin_cli decide` exits `0`. Use `--out` with `orin_cli decide`
and `--write` with `orin_agent decide`.

## Handing over

Implementation work should begin only when the person has read the file
and either answered the open questions or explicitly accepted building
around them. Orin files stay the source of truth: if behaviour changes,
change the `.orin` first.

See the [authoring exercises](../examples/authoring/README.md) for five
requests and their results.

## Experimental: collaborative authoring prototype

The collaborative-authoring prototype is an experiment, not part of Orin's
canonical language or semantic model. Its stdlib-only implementation is
`implementations/python/orin_proposal.py` (ORIN-0006 Phase 2.4).

A **Proposal** contains object-level `add`, `remove`, or `replace` changes
and a rationale. `diff(model, proposal)` shows the changes. A **Review**
supports `accept(rationale)`, `reject(rationale)`, `explain(question, answer)`,
and `counter(changes, rationale)` (a proposed edit). Inputs are never
mutated; accepting returns a new model.

`proposal_from_decision_option(model, prompt, option, rationale=None)` can
turn an `orin_agent_core` decision option into a proposal: it resolves the
uncertainty when present, adds or replaces rules with the option's claims,
and adds its examples. The default rationale is the option's label and
explanation. A blocked option such as `defer` raises `ValueError`; no
decision is made and the uncertainty stays open. Accepting applies the
proposal; rejecting leaves the model and uncertainty unchanged.

`save_decisions(path, records)` and `load_decisions(path)` persist prototype
decision records as a plain JSON list (a missing file loads as `[]`). Each
record has exactly an outcome (`accepted` or `rejected`), subject object ids,
a list of changes, and non-empty rationale. Only accept/reject produce
records. There are no status or timestamp fields; explanations and
counter-proposals are conversation, not model content. Persisting decisions
as model `decision` objects remains an open question.

Run the prototype tests with:

```text
python -m unittest implementations.python.test_orin_proposal
```

These APIs and records are experimental authoring-tool behavior. They do not
add syntax, semantic concepts, workflow states, or provenance fields to Orin.
