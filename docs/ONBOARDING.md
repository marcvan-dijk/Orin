# Orin onboarding: 10-minute walkthrough

Orin is a way to write down **what a program must do**. AI and code
implementations decide **how** it is built. The Orin file stays the source of
truth when the code changes.

You need only `git`, and `python` (3.10 or newer) for steps 4 to 6. Step 7 also
uses `node` (22.6 or newer). All commands run from the repository root.

## 1. Clone (1 minute)

```bash
git clone https://github.com/<owner>/Orin.git
cd Orin
```

Use the URL of the repository you are working from.

## 2. Open the example (2 minutes)

Open [`examples/password-reset.orin`](../examples/password-reset.orin). It is
plain text. You do not need to know any programming language to read it.

- `purpose`: the goal in one sentence.
- `rules`: things that must always be true.
- `workflow`: the operation, in short steps.
- `example`: a situation (`given`, `when`, `then`) you can observe.
- `uncertainty`: an important question that nobody has answered yet.

## 3. Three ideas: intent, decision, evidence (2 minutes)

| Idea | Meaning | In the example |
| --- | --- | --- |
| **Intent** | What the program is for, and what must be true. | `purpose` and `rules` |
| **Decision** | A choice that changes the result and a human must make. | `uncertainty: rate-limit` |
| **Evidence** | Something you can check to see the intent is kept. | the two `example` blocks and the tests |

Why keep them apart? Intent should not change when code changes. A decision
should never be guessed silently by AI or by a developer. Evidence tells you
if an implementation really keeps the intent.

## 4. Run the agent (1 minute)

```bash
python -m tooling.python.orin_agent inspect examples/password-reset.orin
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

Look at **Affected objects**. This is the impact: the decision touches one
workflow and both examples.

## 5. Make a decision (2 minutes)

Choose an option. The output file goes in a folder you choose; here, `out/`.

```bash
mkdir -p out
python -m tooling.python.orin_agent decide \
  tests/conformance/password-reset.model.json \
  --uncertainty account.password-reset/uncertainty/rate-limit \
  --option five-per-15m-per-address-and-origin \
  --write out/five.json
```

Real output (exit code `4` means "decision accepted"):

```text
Accepted decision: five-per-15m-per-address-and-origin
Updated compilation: eligible
Wrote revised semantic artifact to <your path>/out/five.json
```

Now change your mind. Run the same command with the other option:

```bash
python -m tooling.python.orin_agent decide \
  tests/conformance/password-reset.model.json \
  --uncertainty account.password-reset/uncertainty/rate-limit \
  --option three-per-hour-per-address \
  --write out/three.json
```

Compare the two results:

```bash
diff out/five.json out/three.json
```

Only one rule line differs:

```text
<         "Password reset requests are limited to 5 attempts per 15 minutes for the same email address and network origin.",
---
>         "Password reset requests are limited to 3 attempts per hour for the same email address, regardless of network origin.",
```

Check that the program is now ready:

```bash
python -m tooling.python.orin_agent inspect out/three.json
```

It prints `Ready: no blocking consequential decisions remain.` and exits `0`.
The `defer` option is refused (exit code `3`): it produces no new file and the program stays blocked.

## 6. See the effect on the examples (1 minute)

The examples (`registered-address`, `unknown-address`) are the evidence. They
were listed as affected in step 4, and they stay true for both choices: the
person always gets the same confirmation. Only the rate-limit rule changed.
This is the point of Orin: the decision is visible and recorded, and the
evidence tells you what must still be true.

## 7. Run the proof for two implementations (1 minute)

Orin does not yet have a general code generator. The repository has a small
proof that turns the accepted meaning into two different implementation plans
and checks the same behaviour for both.

```bash
python implementations/python/password_reset_proof.py
```

Real output (shortened):

```text
"blockedCompilation": "blocked",
"resolvedCompilation": "eligible",
"canonicalMeaningStableAcrossVariants": true,
```

"Canonical meaning" here means the one agreed meaning of the program. It stays
the same for both variants (`low-latency-managed` and `simple-portable`). Only
the implementation choices differ. It also lists the eight behaviour cases that
any implementation must pass.

Run the checks. The TypeScript reference runtime is one such implementation:

```bash
python implementations/python/test_orin_model.py PasswordResetProofRunTests.test_password_reset_end_to_end_derivation_proof
node --test --experimental-strip-types implementations/typescript/src/password_reset_proof.test.ts
```

Expected: `Ran 1 test ... OK`, then `# pass 4` and `# fail 0`.

## What you learned

- **Intent** is written once and does not depend on code.
- A **decision** is explicit. Nothing is built until a human makes it.
- **Evidence** checks any implementation against the intent.

Next: [`ORIN-SYNTAX-GUIDE.md`](./ORIN-SYNTAX-GUIDE.md) and
[`PASSWORD-RESET-MVP-DEMO-RUNBOOK.md`](./PASSWORD-RESET-MVP-DEMO-RUNBOOK.md).
Delete the `out/` folder when you are done.
