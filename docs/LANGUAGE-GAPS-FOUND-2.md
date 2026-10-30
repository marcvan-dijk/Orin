# Language and tool gaps found: event-booking stress test (round 2)

Method: a novice turned this paragraph into `examples/event-booking.orin`
(outline style, documented syntax only):

> An event has a fixed number of seats. An attendee can book a seat if one is
> free, and joins a waiting list if the event is full. When a booking is
> cancelled, the first attendee on the waiting list gets the seat. A cancelled
> booking is refunded by a policy that depends on how early the attendee
> cancels. An attendee cannot hold two bookings for the same event.

Two open decisions: `refund-amount` and `waitlist-offer-expiry`. Options are in
`tests/conformance/event-booking.decisions.json`. Core code was not changed.
Tests: `python -m unittest implementations.python.test_event_booking`.

Good news (round 1 gaps now fixed): two blocking uncertainties work (no
`ORIN-E004`), the sidecar is found in `tests/conformance/`, decisions chain
(`decide a.json --uncertainty ... --out b.json`), `failure:`/`recovery:`/
`after:`/`proved-by:` clear readiness, and `generate --target python|typescript`
works for any module. The full flow
`check -> readiness -> inspect -> decide -> decide -> readiness -> generate` ran.

Ranked by severity.

## High

1. **Capacity cannot be stated as a value.**
   "An event never has more confirmed bookings than its capacity" is free text,
   so `generate` makes it a `NotImplementedRule` hook. There is no way to say
   `capacity` is a named parameter of the event.
   Repro: `python -m tooling.python.orin_cli decide ...` twice, then
   `generate b.json --target python --out build`; look at `IR["unimplemented"]`
   for `an-event-never-has-more` and `parameters: []`.
   Fix: a documented outline form for named parameters/constants
   (`parameter: capacity` with a unit/type) and a "limit" claim pattern.

2. **Tiered numbers in decision claims are not understood.**
   `refund-policy` ("7 or more days ... in full", "1 to 6 days ... half",
   "event day ... not refunded") becomes three hooks, not a table. Refund
   tiers are a very common policy shape.
   Repro: same as 1; see hooks `refund-policy.3/.4/.5`.
   Fix: a claim pattern or documented structure for tiers (threshold -> outcome).

3. **Outline docs and CLI disagree about inline `options:`.**
   `inspect` says "add an inline `options:` block to this uncertainty", but
   `docs/LANGUAGE-REFERENCE.md` and `ORIN-SYNTAX-GRAMMAR.md` say outline
   `options:` is not supported. A novice following the docs must write JSON.
   Repro: `python -m tooling.python.orin_cli inspect examples/event-booking.orin`
   (before the sidecar exists) and read `docs/LANGUAGE-REFERENCE.md`
   "Not supported yet".
   Fix: document the inline form (with `why:`, `affects:`, option claims) or
   remove the hint.

## Medium

4. **No way to model booking states or the waiting list in outline style.**
   "confirmed / waitlisted / cancelled" and "queue order" can only be prose.
   Using `state:` or `entity:` switches the file to detailed mode, where
   plural `rules:` and `steps:` are not checked (grammar section 6), and
   needs JSON-only items (R001, R010, R030...). The novice has to choose
   between readable and checked.

5. **Source `example:` blocks cannot run.**
   Repro: `python -m tooling.python.orin_cli examples examples/event-booking.orin`
   prints "No examples found ... looked for <name>.cases.json" and exits 0.
   The 5 examples in the file are not executable, and the examples that a
   decision adds (`early-cancel-full-refund`, ...) exist only in the sidecar.
   Exit 0 with nothing run can look like success.

6. **Decision-created rules are not linked to evidence, yet readiness is READY.**
   `refund-policy` and `waitlist-offer-expiry` have no `proved-by`.
   Repro: after both decisions, `readiness b.json` prints READY, and
   `docs/LANGUAGE-GAPS-FOUND.md` item 5 said R040 would block them.
   Either the check is too weak or the docs are stale; a novice cannot tell
   whether the decided policy is proved by any example.

7. **Rule ids are truncated slugs.**
   `an-event-never-has-more`, `an-attendee-who-books-a`,
   `when-a-confirmed-booking-is`. Two rules with the same first words would
   collide, and sidecar `affected_objects` must guess these names.
   Repro: `python -c` load, or look at hook ids in the generated file.
   Fix: allow a short label per rule, e.g. `- seat-limit: An event never ...`.

## Low

8. **Exit codes differ for the same state.** `check` exits 1 and `readiness`
   exits 2 when only decisions are open. `check` says "PROBLEMS" for a file
   with no mistakes, only open questions.
   Repro: `check examples/event-booking.orin; echo $?` then `readiness ...`.

9. **Next-step hint uses a made-up output name.** After the first `decide`,
   `check a.json` suggests `--out a.decided.json`, and for the source it
   suggests `--out event-booking.decided.json` in the current directory.
   Fine, but the hint chooses a different `--option` each time (first option
   id), which may look like a recommendation.

10. **`generate` needs a `.json` model.** `generate examples/event-booking.orin
    --target typescript --out X` says "generate needs a semantic model .json
    file". A file with no open decisions could be generated directly, or the
    error could say "run decide first".

11. **Only one `why:` text.** "Why it matters" lives only in the sidecar; the
    `.orin` file has no place for it, so without the sidecar `inspect` repeats
    the question as the reason.

12. **Waiting-list order and refund timing are "observable behaviour" in prose
    only.** Examples say "added to the end of the waiting list", but no
    checkable form exists (see 1, 4, 5).
