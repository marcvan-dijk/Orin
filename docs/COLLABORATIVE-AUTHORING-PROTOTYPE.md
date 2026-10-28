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

Persisting decisions as model `decision` objects is an open question.

Run: `python -m unittest implementations.python.test_orin_proposal`
