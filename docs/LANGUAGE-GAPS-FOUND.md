# Language and tool gaps found: library-lending stress test

Method: novice flow from an English paragraph to `examples/library-lending.orin`
(outline style), sidecar `tests/conformance/library-lending.decisions.json`,
then `python -m tooling.python.orin_cli check/readiness/inspect/decide/generate/examples`.
Core code was not changed. Ranked by severity.

## High

1. **Two blocking uncertainties crash validation with `ORIN-E004`.**
   Repro: `orin_cli check examples/library-lending.orin` with two
   `uncertainty:` blocks marked `blocking: yes` reports
   `duplicate object identity: library-lending/evidence/blocked`.
   Making one `blocking: no` removes it. Any real program has several
   decisions, so this is the worst gap. (Also noted in ORIN-SYNTAX-GRAMMAR.md.)
   Fix: derive the evidence id from the uncertainty id.

2. **`generate` is hardcoded to two modules.**
   Repro: `generate tests/conformance/library-lending.decided.json --target typescript --out X`
   gives `no generator for module "library-lending/module"; supported: account.password-reset/module, finance.expense-approval/module`.
   `--target python` fails differently: `model is missing required object: account.password-reset/workflow/request-reset`
   (it assumes password-reset, and the error does not name the real cause).
   `generate examples/library-lending.orin ...` says `generate needs a semantic model .json file`.
   Fix: produce a generic skeleton from the model, or say "no generator for module X" for every target.

3. **Decisions sidecar is found only next to the source, and the conformance location is not read.**
   Repro: with `tests/conformance/library-lending.decisions.json` alone,
   `inspect examples/library-lending.orin` says "Options: none defined yet".
   It works only when copied to `examples/library-lending.decisions.json`
   (I verified, then removed the copy). The repo convention puts fixtures in
   `tests/conformance/`. Fix: also search `tests/conformance/`, or take `--decisions PATH`.

4. **Decisions cannot be chained.**
   Repro: `decide ... --option expire-after-3-days --out a.json`, then
   `decide a.json --uncertainty <other> --option refuse-renewal --out b.json`
   gives `unknown decision option 'refuse-renewal'`, because the sidecar is looked
   up by the model's file name (`a.decisions.json`). Fix: embed the options in the decided model.
   Parallel decisions on the same source also produce independent models that must be merged by hand.

## Medium

5. **[done] No outline syntax for R020/R021/R040/R050.** Now `failure:`, `recovery:`, `after:` under `workflow:` and `proved-by:` under a rule; `examples/library-lending.orin` clears all 14 until the decisions add rules without evidence links (decision-created rules still need `evidenceLinks`). Original report: After both decisions, `readiness`
   still blocks with 14 items: failure behavior, recovery, postconditions, and
   a rule-to-example link for each rule (8 rules once the decisions add rules).
   `docs/LANGUAGE-REFERENCE.md` lists them but the outline has no syntax. A novice cannot clear them.
   Fix: allow `failure:`, `recovery:`, `after:` under `workflow:`, and `proved-by:` under `rule:`.
   Or automatically link a rule to an example that mentions it.

6. **`decide` hint prints wrong flags.** `check` suggests
   `decide F --option <id> --out library-lending.decided.json`, which is right, but
   `inspect`/README still mention `--write` (`decide -h` shows `--write` as an
   option in the agent-core usage, `orin_cli decide ... --write X` fails with
   `--out` required). Fix: one flag name.

7. **"Why it matters" repeats the question** and "Affected objects" is empty when no
   sidecar is present. A novice cannot supply them in the outline. Fix: inline
   `why:` and `affects:` keys on `uncertainty:`.

8. **Auto-generated rule ids are truncated slugs** (`a-loan-has-a-due`,
   `a-member-with-unpaid-fees`) that are unstable if wording changes, and
   sidecar `affected_objects` must guess them. Fix: allow `rule: name -` labels in the `rules:` list.

## Low

9. **Quantities are free text.** "14 days", fee cap, fee limit, and "3 days overdue"
   cannot be stated as values, so examples cannot be checked. Fix: typed constants (`constant: loan-days 14 days`).
10. **`check` says `valid (compilation: eligible)` while `readiness` says BLOCKED**
    for the same file. Two vocabularies confuse a novice. Fix: print a one-line pointer to readiness.
11. **`examples` exits 0 when no cases are found** ("No examples found ... looked for
    <name>.cases.json in tests/conformance and tests/conformance", same directory twice).
    There is no way to turn the in-source `example:` blocks into runnable cases.
12. **Non-blocking uncertainty is only a note**, so `lost-book-fee` has no way to
    get options via `decide` and is silently left out of the decided model.
