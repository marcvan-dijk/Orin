# Password reset

Start with this human request:

> Let a person reset a password without revealing whether the account exists.

The [beginner walkthrough](#beginner-walkthrough) is the primary path. Follow it
before the [deeper proof runbook](#deeper-proof-runbook),
[decision-change evidence](#decision-change-evidence),
[scripted demo and recording](#scripted-demo-and-recording), or
[semantic boundary](#semantic-boundary) sections.

## Beginner walkthrough

Orin is a way to write down **what a program must do**. AI and code
implementations decide **how** it is built. The Orin file stays the source of
truth when the code changes.

Reading the `.orin` file needs no host runtime. To execute this walkthrough,
you need `git` and Python. Node is only for the optional TypeScript check at
the end of step 7. Exact versions are in
[Requirements](../../README.md#try-it). Unknown words: [glossary](../../docs/GLOSSARY.md).
All commands run from the repository root. If `python` is not found, use
`python3` (Windows: `py`). On Windows PowerShell, see the note in the README;
every command below is on one line.

### 1. Clone (1 minute)

```bash
git clone https://github.com/marcvan-dijk/Orin.git
cd Orin
```

If you work from a fork, use the URL of your fork.

### 2. Open the example (2 minutes)

Open [`examples/password-reset.orin`](../password-reset.orin). It is
plain text. You do not need to know any programming language to read it.

- `purpose`: the goal in one sentence.
- `rules`: things that must always be true.
- `workflow`: the operation, in short steps.
- `example`: a situation (`given`, `when`, `then`) you can observe.
- `uncertainty`: an open question that nobody has answered yet.

### 3. Three ideas: intent, decision, evidence (2 minutes)

| Idea | Meaning | In the example |
| --- | --- | --- |
| **Intent** | What the program is for, and what must be true. | `purpose` and `rules` |
| **Decision** | The answer to an open question. A human must make it. | `uncertainty: rate-limit` |
| **Evidence** | Something you can check to see the intent is kept. | the two `example` blocks and the tests |

Why keep them apart? Intent should not change when code changes. A decision
should never be guessed silently by AI or by a developer. Evidence tells you
if an implementation really keeps the intent.

### 4. Check the example and run the agent (2 minutes)

From here on, every command uses one file:
`tests/conformance/password-reset.model.json`. It is the same program as
`examples/password-reset.orin`, written in a form tools read (the "semantic
model"; see the [glossary](../../docs/GLOSSARY.md)). Use it in steps 4 and 5, and the
output files in `out/` after that.

First ask the checker if the program is complete:

```bash
python -m tooling.python.orin_cli check tests/conformance/password-reset.model.json
```

It prints `PROBLEMS:` and the open question (`ORIN-E041`), and exits `1`.
For a longer list of what is missing, run:

```bash
python -m tooling.python.orin_cli readiness tests/conformance/password-reset.model.json
```

It prints `BLOCKED:` and exits `2`. Now ask the agent about the open decision:

```bash
python -m tooling.python.orin_agent inspect tests/conformance/password-reset.model.json
```

The last part of the real output looks like this:

```text
Compilation: blocked
Validation: blocked
Blocked: 1 consequential decision(s) remain unresolved.

1. account.password-reset/uncertainty/rate-limit
   Question: What rate limit applies per address and network origin?
   ...
   Affected objects:
   - account.password-reset/workflow/request-reset
   - account.password-reset/example/registered-address
   - account.password-reset/example/unknown-address
   Options:
   - five-per-15m-per-address-and-origin: ...
   - three-per-hour-per-address: ...
   - defer: ...
```

The exit code is `2`, which means "blocked". Orin does not build the program
while an important decision is open. (Note: the agent gives its own, more exact
version of the question than the short text in the `.orin` file.)

#### What the readiness codes mean

Each line of `readiness` starts with a code. `ORIN-R201` is the one real
open question here: `rate-limit`. The other `ORIN-R0xx` lines
are optional hardening: extra detail (who may do a thing, what happens on
failure, which evidence proves a rule) that makes a program safer to build.
Notes marked `ORIN-R3xx` never block. You can ignore the hardening lines on
your first run; only decisions (`R2xx`) must be answered before code is made.

Look at **Affected objects**. This is the impact: the decision touches one
workflow and both examples.

### 5. Make a decision (2 minutes)

Choose an option. The model file is the same one as in step 4. The output
goes in `out/`.

```bash
mkdir out
python -m tooling.python.orin_agent decide tests/conformance/password-reset.model.json --uncertainty account.password-reset/uncertainty/rate-limit --option five-per-15m-per-address-and-origin --write out/five.json
```

Real output (exit code `4` means "decision accepted"; it is not an error, but
a script that expects `0` will see it as a failure):

```text
Accepted decision: five-per-15m-per-address-and-origin
Updated compilation: eligible
Wrote revised semantic artifact to <your path>/out/five.json
```

Now change your mind. Run the same command with the other option:

```bash
python -m tooling.python.orin_agent decide tests/conformance/password-reset.model.json --uncertainty account.password-reset/uncertainty/rate-limit --option three-per-hour-per-address --write out/three.json
```

Compare the two results (`diff` exits `1` when files differ; that is normal):

```bash
diff out/five.json out/three.json
```

Only one rule line differs:

```text
<         "Password reset requests are limited to 5 attempts per 15 minutes for the same email address and network origin.",
---
>         "Password reset requests are limited to 3 attempts per hour for the same email address, regardless of network origin.",
```

Check that the decision is closed:

```bash
python -m tooling.python.orin_cli check out/three.json
python -m tooling.python.orin_agent inspect out/three.json
```

The first prints `OK: out/three.json is valid (compilation: eligible).` The
second prints `Ready: no blocking consequential decisions remain.` Both exit `0`.
The `defer` option is refused (exit code `3`): it produces no new file and the program stays blocked.

### 6. See the effect on the examples (1 minute)

The examples (`registered-address`, `unknown-address`) check that the person
gets the same confirmation for a registered or unknown address. They stay true
for both choices, but do **not** test the rate limit. The decision also changes
generated runtime behaviour: the first choice permits five requests per 15
minutes per address and origin; the second permits three per hour per address,
regardless of origin. Over either limit, no email is sent, but the same
confirmation is returned. Shared generated-runtime conformance cases now
exercise both policies; see [Decision-change evidence](#decision-change-evidence).

### 7. Generate code and run the proof (2 minutes)

Now that the decision is made, generate a small Python implementation from the
decided model:

```bash
python -m tooling.python.orin_cli generate out/three.json --target python --out out/generated
```

It writes `out/generated/password_reset_generated.py` and exits `0`. If a
decision is still open, `generate` refuses to run (exit `1`).

The repository also has a small proof that turns the accepted meaning into two
different implementation plans and checks the same behaviour for both.

```bash
python implementations/python/password_reset_proof.py
```

The output is long. To find the lines below, filter it by hand: in Bash add
`| grep canonical`; in PowerShell add `| Select-String canonical`. Real output
(shortened):

```text
"blockedCompilation": "blocked",
"resolvedCompilation": "eligible",
"canonicalMeaningStableAcrossVariants": true,
```

"Canonical meaning" here means the one agreed meaning of the program. It stays
the same for both variants (`low-latency-managed` and `simple-portable`). Only
the implementation choices differ. It also lists the eight behaviour cases that
any implementation must pass.

Run the Python check:

```bash
python implementations/python/test_orin_model.py PasswordResetProofRunTests.test_password_reset_end_to_end_derivation_proof
```

Expected: `Ran 1 test ... OK`.

**Optional (needs Node; see [Requirements](../../README.md#try-it)).** The TypeScript reference runtime is
another implementation. You can skip this and still finish the walkthrough:

```bash
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
```

Expected: `# pass 4` and `# fail 0`.

### What you learned

- **Intent** is written once and does not depend on code.
- A **decision** is explicit. Nothing is built until a human makes it.
- **Evidence** checks any implementation against the intent.

Words: [glossary](../../docs/GLOSSARY.md). Next: the deeper sections below.
Delete only the walkthrough's generated `out/` files when you are done; do not
remove unrelated work if the directory already existed.

## Real beginner observation

Use the existing walkthrough with a beginner; this is a checklist, not a
reported user result.

- Let the participant read the meaning, resolve the open rate-limit question,
  generate an implementation, change the accepted policy, and observe whether
  generated behaviour differs.
- Do not coach past friction. Record what confused them and whether they
  complete the task unaided.
- Reading the `.orin` file needs no host runtime. Running the walkthrough
  requires Python; the optional TypeScript check requires Node.
- Success means the participant can explain the rules and observe changed
  generated behaviour without reading the implementation.

## Deeper proof runbook

For a five-minute presentation, read the opening human request, inspect the
`.orin` purpose/rules/workflow/examples/uncertainty, then show the proof from
step 7. No knowledge of Python or TypeScript is needed to read the meaning.
AI can help turn the request into readable Orin, but this demo does not
measure or automate that authoring step.

Inspect [`password-reset.model.json`](../../tests/conformance/password-reset.model.json):

- `account.password-reset/uncertainty/rate-limit` is consequential and unresolved.
- `unresolved: ["account.password-reset/uncertainty/rate-limit"]` records that fact.
- There is no stored `compilation.status`. Readiness (`blocked`/`eligible`) is
  computed from unresolved consequential uncertainties, not persisted as
  workflow metadata.

### Proof acceptance gate

Use the Python proof run, Python proof check, and optional TypeScript proof
check already listed in step 7. For the full cross-runtime gate, also run the
TypeScript proof itself:

```text
node --experimental-strip-types implementations/typescript/src/password_reset_proof.ts
```

Both proof runs must show `blockedCompilation: "blocked"`,
`resolvedCompilation: "eligible"`, `canonicalMeaningStableAcrossVariants: true`,
two policy variants with different `derivedArtifact`, and password-reset
`behaviorCases`. These are implementation-plan variants
(`low-latency-managed`, `simple-portable`), not the two rate-limit decisions.

**PASS** the full gate only if all four proof/test commands exit `0`, both
runs have those fields, and variant behaviour agrees. The Python check reports
`Ran 1 test ... OK`; the TypeScript checks report `# pass 4`, `# fail 0`.
**FAIL** if a command fails, fields differ, or variant behaviour diverges.
Skipping Node completes the beginner path, but not the cross-runtime gate.

This demonstrates visible consequential ambiguity, deterministic testable
password-reset behaviour, and implementation freedom without making generated
code the source of truth. It is not a request for shared-tasks work, roadmap
expansion, dependencies, new runners, or unrelated refactoring.

## Decision-change evidence

This is a narrower question than implementation-plan variation: change one
accepted rate-limit decision, regenerate, and inspect what actually moves.
Run from the repository root with the Python standard library:

```text
python -m tooling.python.demo_decision_change
python -m unittest tooling.python.test_demo_decision_change
```

The demo applies each option through the public
`OrinDecisionAgent.apply_decision`, generates with
`python -m implementations.python.codegen.generate`, and replays the shared
rate-limit fixture through `replay_case`. It reports `changed_rate_limit_cases`
and `rate_limits`, along with the code diff and byte-identical blocks.
[`password-reset.rate-limit.cases.json`](../../tests/conformance/password-reset.rate-limit.cases.json)
contains 10 cases, 62 requests per policy, and two policies. The eight
original shared behavior cases remain separate: they contain no rate-limit
scenarios and remain the scope of the original reference proofs.

### Measured password-reset result

- The hand-written template parses claim text into constants by regex.
  The diff is 3 lines removed and 3 added, all `RATE_LIMIT_*` constants:
  `5/900/True` becomes `3/3600/False`.
- 18 of 19 top-level generated blocks stay byte-identical: token expiry,
  single use, no-disclosure, capabilities, and response shape. The nineteenth
  block is the constants header.
- The new generated-runtime tests apply the shared rate-limit fixture to
  generated Python and TypeScript. `implementations/python/parity_check.py`
  verifies both generated runtimes against the shared expectations.
- A means five requests per fifteen minutes per address **and origin**;
  B means three per hour per address, regardless of origin. Over either limit,
  the person still gets standard confirmation and no message is sent.
- The fixture follows current implementation behavior. The exact rolling-window
  boundary is not expressly specified by the original policy prose, so these
  cases do not establish it as newly accepted language meaning.

### Honest comparison and limits

The original comparison counted 163 lines in
`implementations/python/password_reset.py` and 107 in
`implementations/typescript/src/password_reset.ts`. At the time, those
hand-written runtimes had no rate limiting; the original reference proofs
exercised the eight behavior cases, not the new generated-runtime fixture.
The fair comparison is a human **adding** the rule, not changing an existing
constant:

| | Orin | Hand-written |
| --- | --- | --- |
| Source edited | One decision choice | Rule logic per runtime, plus origin plumbing |
| Lines changed by hand | Zero (regenerated) | Estimated 10–15 per runtime |
| Review surface | Six-line diff | Whole-function diff |
| Re-test | Same cases replayed | Author updates examples |

No controlled hand-coding comparison or timing was performed; effort figures
are estimates. Whether option text matches stakeholder intent remains a human
judgement. Runtimes are in-memory and single-process: persistence, concurrency,
clock skew, and cheap behaviour-restructuring decisions are not demonstrated.
Python/TypeScript parity of **decision-change** behaviour is not established
by the original proof-run gate above; the separate generated-runtime parity
check is described under [Measured password-reset result](#measured-password-reset-result).

The original three-application experiment also ran:

```text
python -m tooling.python.demo_decision_change --app expense-approval
python -m tooling.python.demo_decision_change --app shared-tasks
```

Its results are bounded findings, not claims of general generation:

| Application | Observed generated change | Evidence and limitation |
| --- | --- | --- |
| Password reset | Constants only; 18/19 blocks unchanged | 8/8 shared cases pass both ways; 3/6 demo probes flip |
| Expense approval | Zero lines between escalate, reject, and stay-submitted | 10/10 cases encode stay-submitted; Python ignored the option, TypeScript accepted only stay-submitted |
| Shared tasks, minimal | About 13 lines of IR/report text and one `NotImplementedRule` hook | membership-required: 4/4; assignee-may-complete: 3/4 because member-completes raises; non-member assignee remains unauthorized under both |

Only one of those three applications automatically changed behaviour, and
only by filling constants. Expense escalate/reject and the shared-tasks
assignee hook still required human implementation. The expense finding and
accepted hold policy are detailed in [expense approval](expense-approval.md).
The shared-tasks generator was model-driven (`codegen/model_driven.py`); its
loud hook surfaced a new rule rather than silently implementing it.

## Scripted demo and recording

### Automated novice flow

The standard-library-only script narrates the human request, checks the
existing `.orin` source (blocked), applies a decision through the imported
`implementations/python/orin_agent_core.py`, rechecks (ready), generates with
`implementations.python.codegen.generate`, and replays
`tests/conformance/password-reset.cases.json` locally without test helpers.

```text
python -m tooling.python.demo_novice_flow
python -m tooling.python.demo_novice_flow --app expense-approval
python -m unittest tooling.python.test_demo_novice_flow
```

Sources carry no decision options, so the script applies the decision to the
matching `tests/conformance/<app>.model.json`. Expense approval uses its
`<app>.decisions.json` sidecar, selects the first offered option that does not
keep compilation blocked, and replays
`tests/conformance/expense-approval.resolved.cases.json`. This substitution
does not prove every offered policy is implemented; see the negative result
above. Output uses a scratch directory **inside the repository**, removed
afterwards. Exit `1` means a step or case failed.

### Three-minute recording script

Use a large terminal font, speak slowly, and use short sentences. Follow the
primary walkthrough's commands rather than maintaining a second sequence.
Before recording, ensure `out/` exists (`mkdir -p out` in Bash).

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00 | Title: “Orin: write what software must do” | “If AI writes the code, what should people write? Orin says: the meaning of the program.” |
| 0:20 | Open `examples/password-reset.orin` (step 2) | “Here is the purpose, the rules, two examples, and one open question: rate limit.” |
| 0:50 | Intent/decision/evidence table (step 3) | “Intent: what must be true. Decision: a human choice. Evidence: a check that intent is kept.” |
| 1:10 | Run the check and agent inspection from step 4 | “Blocked. It lists the decision, options, workflow, and both examples. It does not guess.” |
| 1:40 | Choose five-per-15m (step 5) | “I choose five requests per fifteen minutes. The decision is accepted.” |
| 2:00 | Choose three-per-hour and show the diff (step 5) | “I change my mind. Only one rule line changes. The examples stay true.” |
| 2:20 | Generate (step 7) | “The decision is made, so Orin generates code.” |
| 2:25 | Run the Python proof (step 7) | “The same meaning gives two implementation plans. The meaning does not change.” |
| 2:45 | Optional Node test (step 7), `# pass 4` | “Evidence checks the implementation. Code can change; intent, decisions, and evidence stay.” |
| 2:55 | End card: `examples/docs/password-reset.md` | “Try the beginner walkthrough.” |

The original recording script checked `.orin` directly; using the model in
step 4 keeps the recording and primary beginner path consistent.

## Semantic boundary

### Durable meaning versus scaffolding

| Category | Keep in canonical meaning? | Password-reset examples |
| --- | --- | --- |
| Durable project meaning | Yes | Purpose, privacy/token rules, observable outcomes, consequential `rate-limit` uncertainty, human decision authority |
| Implementation scaffolding | No; optional tooling/implementation layer | Workflow step prose, value types, state declarations, capabilities/effects, rule category tags, dependency/link arrays |
| Process/provenance/history | No; external records | Status fields, model/fixture versioning, evidence bookkeeping, traceability metadata |

Workflow ordering belongs to meaning only when a rule or observable example
makes that ordering consequential; prose alone is implementation guidance.

### Five audit questions

1. If this field changes, does required observable behaviour change? If yes,
   it is durable meaning.
2. Does it encode an accepted consequential decision? Preserve that durably;
   never let AI guess silently.
3. Can two correct implementations differ here while passing the same
   behavioural cases? If yes, it is implementation freedom/scaffolding.
4. Is it mainly collaboration history or traceability? Keep it outside minimal
   canonical meaning.
5. Can readiness/blocking be derived instead of stored? Yes: compilation is
   computed from unresolved consequential uncertainties.

The proof survives removal of non-semantic object `status`, password-reset
fixture `kind` tags, rule `category`, dependency/provenance arrays, and stored
compilation state. The blocked/eligible gate remains derived, and observable
behaviour cases remain unchanged.
