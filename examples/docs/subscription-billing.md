# Language and tool gaps found #3: subscription-billing stress test

**Purpose:** Retained findings from a supporting application, not Orin's
language specification or an active feature queue. Subscription charges
belong to this sample application, not to the use of Orin.
See the [example catalogue](../README.md) for the primary proof path.

Method: a novice wrote `examples/subscription-billing.orin` (plans, monthly
charge, failed-payment grace period, cancellation, proration) in outline style,
using only syntax from `LANGUAGE-REFERENCE.md`. Then ran
`python -m tooling.python.orin_cli check/readiness/inspect/decide/generate/examples`.
Core code was not changed. Test: `implementations/python/test_subscription_billing.py`.
Ranked by severity.

What worked: the file loads; all 6 rules link to examples with `proved-by:`;
workflows with `failure:`/`recovery:`/`after:` raise no R020/R021/R050;
`check` and `readiness` name the 2 blocking decisions clearly (exit 1 and 2).

## High

1. **A decision cannot be given options in documented syntax.**
   Repro: `orin_cli inspect examples/subscription-billing.orin` shows
   `Options: none defined yet`, and
   `orin_cli decide examples/subscription-billing.orin --option x --out o.json`
   fails (`no open decision offers option 'x'`). The only documented way is a
   `.decisions.json` sidecar with a long JSON shape. An inline `option:` form
   now exists in `orin_outline_uncertainty.py`, but it is not in
   `LANGUAGE-REFERENCE.md` or the grammar, so a novice cannot find it.
   Fix: document `why:`, `affects:`, `option:` in both docs.

2. **Decisions still cannot be chained.**
   Repro (with a sidecar for both uncertainties next to the source):
   `decide S --uncertainty .../proration-method --option by-day --out a.json`
   works, then
   `decide a.json --uncertainty .../downgrade-timing --option at-period-end --out b.json`
   gives `unknown decision option 'at-period-end'`. Doing the second decision on
   the source works, but gives a separate model (`c.json`) that still has the
   first question open. A program with 2 decisions can never reach "eligible"
   through the CLI. Fix: put the options into the decided model.

3. **`generate` cannot take a `.orin` file or an unknown module.**
   Repro: `generate examples/subscription-billing.orin --target python --out o`
   gives `generate needs a semantic model .json file`. On a partly decided model,
   `generate a.json --target python` says `needs 1 decision(s)`, and
   `--decision at-period-end` says `no open decision offers option ...`. So
   I could not see what happens for a module that has no generator.
   Fix: accept `.orin`, and say clearly "no generator for module X".

## Medium

4. **A decision-made rule has no example link (ORIN-R040).**
   After deciding `downgrade-timing`, readiness blocks with
   `R040 - Link this rule to an example ... subscription-billing/rule/downgrade-timing`.
   The author cannot add `proved-by:` to a rule that the tool created.
   Fix: let an option name `proved-by` examples, or link the option's example
   automatically.

5. **"Why it matters" repeats the question, and impact areas are always
   `cost, operability, privacy, safety`.** Money rules like proration really
   affect cost only. Repro: `orin_cli inspect examples/subscription-billing.orin`.
   Fix: take impact areas from an `affects:`-like key.

6. **`examples` finds nothing for a source file.**
   Repro: `orin_cli examples examples/subscription-billing.orin` prints
   `No examples found ... <name>.cases.json` and exits 0. A novice with 7
   written `example:` blocks gets "none found" with a success code. Prose
   examples cannot run, and the message does not say so.
   Fix: say "examples are prose only; add a .cases.json to run them".

## Low

7. **A non-blocking uncertainty is shown as "Optional hardening" using the
   same code `ORIN-R201`** as blocking ones. Repro: `orin_cli readiness`.
   It is easy to read it as a second blocker.

8. **Numbers and money have no place in the model.** "plan costs 20", "7 days",
   "proration" live only in prose, so nothing can check them. This is by
   design for outline style, but the gap is real for billing. Not a bug; note
   for a future typed-example form.

9. **`python -m unittest implementations.python.test_x` fails** (no package
   `implementations`). Use `discover -s implementations/python -t . -p "test_x*"`.

10. **Parser was briefly broken by a parallel edit** (`NameError:
    parse_inline_decision`) and `check`/`inspect` crashed with a traceback
    instead of a short message. Fixed a minute later by its owner.
