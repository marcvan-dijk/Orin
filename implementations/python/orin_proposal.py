"""Rough prototype of a proposal/accept/reject flow for model changes (stdlib only).

A Proposal is a diff of object-level model changes plus a rationale. A human
can accept, reject, ask for an explanation, or propose an edit. Only accepted
or rejected outcomes become durable decision meaning (a decision with
rationale); explanations and counter-edits are conversation, not model content.
"""
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Change:
    op: str  # "add" | "remove" | "replace"
    object_id: str
    new: dict = None


@dataclass
class Proposal:
    changes: list
    rationale: str
    explanations: list = field(default_factory=list)  # asked-for context, not meaning


def load_model(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index(model):
    return {o["id"]: o for o in model["objects"]}


def diff(model, proposal):
    """Human-readable lines showing exactly what would change."""
    objs = _index(model)
    lines = []
    for c in proposal.changes:
        if c.op == "add":
            lines.append(f"+ {c.object_id}: {json.dumps(c.new, sort_keys=True)}")
        elif c.op == "remove":
            lines.append(f"- {c.object_id}: {json.dumps(objs[c.object_id], sort_keys=True)}")
        elif c.op == "replace":
            old, new = objs[c.object_id], c.new
            for k in sorted(set(old) | set(new)):
                if old.get(k) != new.get(k):
                    lines.append(f"~ {c.object_id}.{k}: {json.dumps(old.get(k))} -> {json.dumps(new.get(k))}")
    return lines


def apply(model, proposal):
    """Return a new model with the changes applied; the input is untouched."""
    out = copy.deepcopy(model)
    objs = out["objects"]
    for c in proposal.changes:
        ids = [o["id"] for o in objs]
        if c.op == "add":
            if c.object_id in ids:
                raise ValueError(f"already exists: {c.object_id}")
            objs.append(copy.deepcopy(c.new))
        elif c.object_id not in ids:
            raise ValueError(f"unknown object: {c.object_id}")
        elif c.op == "remove":
            objs.pop(ids.index(c.object_id))
        elif c.op == "replace":
            objs[ids.index(c.object_id)] = copy.deepcopy(c.new)
        else:
            raise ValueError(f"unknown op: {c.op}")
    return out


class Review:
    """One human review of a proposal against a base model."""

    def __init__(self, model, proposal):
        self.model = model
        self.proposal = proposal
        self.decisions = []

    def explain(self, question, answer):
        self.proposal.explanations.append({"question": question, "answer": answer})

    def counter(self, changes, rationale):
        """Human proposes an edit: returns a replacement proposal, nothing decided."""
        return Review(self.model, Proposal(changes, rationale))

    def _record(self, outcome, rationale):
        if not rationale:
            raise ValueError("a decision requires a rationale")
        self.decisions.append({
            "outcome": outcome,
            "subjects": [c.object_id for c in self.proposal.changes],
            "change": diff(self.model, self.proposal),
            "rationale": rationale,
        })

    def accept(self, rationale):
        new_model = apply(self.model, self.proposal)
        self._record("accepted", rationale)
        return new_model

    def reject(self, rationale):
        self._record("rejected", rationale)
        return self.model
