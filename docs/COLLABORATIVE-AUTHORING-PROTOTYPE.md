# Collaborative Authoring Prototype (ORIN-0006 Phase 2.4)

Rough prototype: `implementations/python/orin_proposal.py` (stdlib only).

- **Proposal** = object-level changes (`add`/`remove`/`replace`) + rationale.
- **Diff**: `diff(model, proposal)` shows exactly what changes.
- **Human responses** (`Review`): `accept(rationale)`, `reject(rationale)`,
  `explain(question, answer)`, `counter(changes, rationale)` (propose an edit).
- **Durable meaning**: only accept/reject yield a decision record — outcome,
  subjects, change, rationale. No status fields or timestamps; explanations and
  counter-edits are conversation, not model content. Rationale is required.
- Inputs are never mutated; `accept` returns a new model.

## Decision agent connection and decision-record format

`proposal_from_decision_option(model, prompt, option, rationale=None)` turns an
`orin_agent_core` decision option (e.g. shared-tasks
`non-member-assignee-completion`) into a Proposal: resolve the uncertainty (if
present), add/replace the rule with the option's claims, add its examples. The
default rationale is the option's label and explanation. Blocked options such as
`defer` raise `ValueError`: nothing is decided, so the uncertainty stays open.
`accept` applies the proposal; `reject` leaves the model (and uncertainty) as is.

`save_decisions(path, records)` / `load_decisions(path)` use a plain JSON list
(missing file = `[]`). Each record has exactly:

```json
{"outcome": "accepted" | "rejected",
 "subjects": ["object-id", "..."],
 "change": ["+ id: {...}", "~ id.key: old -> new", "- id: {...}"],
 "rationale": "non-empty text"}
```

No status or timestamp fields.

Persisting decisions as model `decision` objects is an open question.

Run: `python -m unittest implementations.python.test_orin_proposal`
