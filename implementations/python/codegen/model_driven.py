"""Model-driven generation: derive a small rule/transition IR from model objects, emit a generic state machine.

The IR (plain dicts/lists/strings) is derived only from workflow ``transitions``, rule ``requires``/``claims``,
state/relation declarations and example ``expects``. Claims that no recognised pattern can turn into a guard are
never dropped: they become explicit ``NotImplementedRule`` hooks listed in the IR and in the generated report.
"""

import pprint
import re

_FAIL = re.compile(r"\bfails? with ([A-Za-z][A-Za-z0-9-]*)")
_NON_MEMBER = re.compile(r"^non-members?\b.*\bfails? with ([A-Za-z][A-Za-z0-9-]*)", re.I)
_MEMBERSHIP_RESTATEMENT = re.compile(r"\brequires\b.*\bmembership\b", re.I)
_ASSIGNEE = re.compile(r"\bactor must match assignee or fail with ([A-Za-z][A-Za-z0-9-]*)", re.I)
_REPEATED = re.compile(r"\b(?:repeated|attempts?)\b.*\bfails? with ([A-Za-z][A-Za-z0-9-]*)", re.I)
_NO_BACK = re.compile(r"\bdo(?:es)? not transition back to ([A-Za-z][A-Za-z0-9-]*)", re.I)
_EXPECT_FAILURE = re.compile(r"^failure = ([A-Za-z][A-Za-z0-9-]*)$")


class ModelDrivenError(Exception):
    """The model cannot be mechanically turned into a state machine."""


def _ident(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9._/-]", "_", str(value))[:200]


def _text(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9._/ ,;:()'=-]", "_", str(value))[:300]


def _short(object_id: object) -> str:
    return _ident(str(object_id).rsplit("/", 1)[-1])


def _list(obj: dict, key: str) -> list:
    value = obj.get(key, [])
    if not isinstance(value, list):
        raise ModelDrivenError(f"malformed model: {key} of {_ident(obj.get('id'))} must be a list")
    return value


def _strings(obj: dict, key: str) -> list[str]:
    return [v for v in _list(obj, key) if isinstance(v, str)]


def has_transition_workflows(document: dict) -> bool:
    objects = document.get("objects", [])
    return isinstance(objects, list) and any(
        isinstance(o, dict) and o.get("kind") == "workflow" and isinstance(o.get("transitions"), list) and o["transitions"]
        for o in objects
    )


def derive_ir(document: dict) -> dict:
    objects = document.get("objects", [])
    if not isinstance(objects, list):
        raise ModelDrivenError("malformed model: 'objects' must be a list")
    objs = {o["id"]: o for o in objects if isinstance(o, dict) and isinstance(o.get("id"), str)}
    kinds = lambda kind: [o for o in objs.values() if o.get("kind") == kind]  # noqa: E731
    states = sorted(_short(o["id"]) for o in kinds("state"))
    relations = {}
    for rel in kinds("relation"):
        ends = [e.get("type") for e in _list(rel, "endpoints") if isinstance(e, dict)]
        if len(ends) == 2:
            relations[rel["id"]] = ends

    workflows = {}
    for wf in sorted(kinds("workflow"), key=lambda o: o["id"]):
        transitions = [t for t in _list(wf, "transitions") if isinstance(t, dict)]
        if not transitions:
            continue
        inputs = {i.get("name"): i.get("type") for i in _list(wf, "inputs") if isinstance(i, dict)}
        actor = wf.get("actor")
        subject = next((n for n, t in inputs.items() if n != actor and objs.get(t, {}).get("kind") == "entity-type"), None)
        if actor not in inputs or subject is None:
            raise ModelDrivenError(f"workflow {_ident(wf['id'])} needs an actor input and an entity subject input")
        caps = sorted({_short(c.get("capability")) for c in _list(wf, "actorCapabilities")
                       if isinstance(c, dict) and c.get("actor") == actor})
        workflows[wf["id"]] = {
            "name": _short(wf["id"]),
            "actor": _ident(actor),
            "actor_type": _short(inputs[actor]),
            "subject": _ident(subject),
            "subject_type": _short(inputs[subject]),
            "requires": sorted(_short(c) for c in _strings(wf, "requires")),
            "capabilities": caps,
            "transitions": [[_short(t.get("from")), _short(t.get("to"))] for t in transitions],
            "guards": [],
            "hooks": [],
            "_subject_type_id": inputs[subject],
            "_actor_type_id": inputs[actor],
        }

    # failure names declared by examples for a workflow, e.g. "failure = task-not-found"
    for example in kinds("example"):
        for wf_id in _strings(example, "requires"):
            wf = workflows.get(wf_id)
            if not wf:
                continue
            for expect in _strings(example, "expects"):
                match = _EXPECT_FAILURE.match(expect.strip())
                if match and match.group(1) == f"{wf['subject_type']}-not-found":
                    guard = {"kind": "entity-exists", "failure": _ident(match.group(1)), "rule": _short(example["id"])}
                    if guard not in wf["guards"]:
                        wf["guards"].append(guard)

    outgoing = {}
    for wf in workflows.values():
        for src, dst in wf["transitions"]:
            outgoing.setdefault(src, set()).add(dst)
    unimplemented, derived, structural, deferred = [], [], [], []

    def _rel_by_endpoints(first, second):
        for rid, ends in sorted(relations.items()):
            if ends == [first, second]:
                return rid
        return None

    for rule in sorted(kinds("rule"), key=lambda o: o["id"]):
        requires = _strings(rule, "requires")
        linked = list(requires)
        for example in kinds("example"):
            if rule["id"] in _strings(example, "requires"):
                linked.extend(_strings(example, "requires"))
        attached = [workflows[r] for r in dict.fromkeys(linked) if r in workflows]
        required_states = [_short(r) for r in requires if objs.get(r, {}).get("kind") == "state"]
        claims = [c for c in _list(rule, "claims") if isinstance(c, str)]
        rname = _short(rule["id"])
        if not attached:
            for claim in claims:
                unimplemented.append({"id": f"hook.{rname}.{len(unimplemented)}", "rule": rname, "scope": "model",
                                      "claim": _text(claim)})
            continue
        pending = []
        for claim in claims:
            made = False
            for wf in attached:
                guard = _derive_guard(claim, rule, requires, objs, relations, wf, outgoing, required_states,
                                      _rel_by_endpoints, structural)
                if guard:
                    made = True
                    if guard is not True and guard not in wf["guards"]:
                        wf["guards"].append(guard)
            if made:
                derived.append({"rule": rname, "claim": _text(claim)})
            else:
                pending.append(claim)
        deferred.extend((rname, claim, attached) for claim in pending)

    # a restatement of membership is covered when some rule already yields a matching membership guard
    for rname, claim, attached in deferred:
        fail = _FAIL.search(claim)
        restates = _MEMBERSHIP_RESTATEMENT.search(claim) or (fail and re.search(r"\bnon-members?\b", claim, re.I))
        covered = restates and all(
            any(g["kind"] == "actor-related" and (not fail or g["failure"] == fail.group(1)) for g in wf["guards"])
            for wf in attached)
        if covered:
            derived.append({"rule": rname, "claim": _text(claim)})
            continue
        hook = {"id": f"hook.{rname}.{len(unimplemented)}", "rule": rname, "scope": "workflow", "claim": _text(claim)}
        unimplemented.append(hook)
        for wf in attached:
            wf["hooks"].append(hook["id"])

    for wf in workflows.values():
        if not any(g["kind"] != "entity-exists" for g in wf["guards"]) and not wf["hooks"]:
            raise ModelDrivenError(f"workflow {wf['name']} has no checkable rules")
        wf.pop("_subject_type_id")
        wf.pop("_actor_type_id")
    targets = {dst for wf in workflows.values() for _, dst in wf["transitions"]}
    sources = {src for wf in workflows.values() for src, _ in wf["transitions"]}
    return {
        "states": states,
        "initial": sorted(sources - targets)[0] if sources - targets else sorted(sources)[0],
        "relations": {_short(rid): [_short(e) for e in ends] for rid, ends in sorted(relations.items())},
        "workflows": {wf["name"]: wf for _, wf in sorted(workflows.items())},
        "unimplemented": unimplemented,
        "derived": derived,
        "structural": structural,
    }


def _derive_guard(claim, rule, requires, objs, relations, wf, outgoing, required_states, rel_by_ends, structural):
    """Return a guard dict, True for a structurally verified claim, or None when not derivable."""
    rname = _short(rule["id"])
    subject, actor = wf["_subject_type_id"], wf["_actor_type_id"]
    match = _NON_MEMBER.match(claim.strip())
    if match:
        member = next((r for r in requires if _short(r) == "member-of" and relations.get(r, [None, None])[0] == actor), None)
        if member:
            via = rel_by_ends(relations[member][1], subject)
            if via:
                return {"kind": "actor-related", "relation": _short(member), "via": _short(via),
                        "failure": _ident(match.group(1)), "rule": rname}
        return None
    match = _ASSIGNEE.search(claim)
    if match:
        rel = next((r for r in requires if relations.get(r) == [actor, subject]), None)
        if rel:
            return {"kind": "assignee-matches", "relation": _short(rel), "failure": _ident(match.group(1)),
                    "rule": rname}
        return None
    match = _REPEATED.search(claim)
    if match:
        terminal = [s for s in required_states if not outgoing.get(s)]
        if terminal:
            return {"kind": "terminal-state", "state": terminal[0], "failure": _ident(match.group(1)), "rule": rname}
        return None
    match = _NO_BACK.search(claim)
    if match:
        target = _ident(match.group(1))
        for state in required_states:
            if target in outgoing.get(state, ()):
                raise ModelDrivenError(f"rule {rname} forbids {state}->{target} but a workflow transition allows it")
            structural.append({"rule": rname, "claim": _text(claim)})
            return True
    return None


def render_ir(ir: dict) -> str:
    return pprint.pformat(ir, sort_dicts=True, width=100)


def report(module_id: str, ir: dict) -> dict:
    return {
        "module": _ident(module_id),
        "mode": "model-driven",
        "derivedRules": ir["derived"],
        "structurallyVerifiedRules": ir["structural"],
        "unimplementedRules": [
            {"id": h["id"], "rule": h["rule"], "scope": h["scope"], "claim": h["claim"], "status": "NotImplementedRule"}
            for h in ir["unimplemented"]
        ],
    }


def output_stem(module: dict) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", str(module.get("name") or module.get("id") or "").lower()).strip("_")
    if not name or name[0].isdigit():
        name = "model_" + name if name else "model"
    return f"{name[:80]}_generated"


TEMPLATE = '''"""Generated by Orin codegen from model @@MODULE@@. Do not edit; regenerate instead.

Model-driven state machine: guards and transitions come from the model; rules the generator could not derive
are explicit NotImplementedRule hooks (see UNIMPLEMENTED_RULES) and fail loudly when reached.
"""

from dataclasses import dataclass

MODULE_ID = @@MODULE@@
IR = @@IR@@
UNIMPLEMENTED_RULES = tuple(IR["unimplemented"])


class NotImplementedRule(Exception):
    """A model rule that codegen could not derive mechanically and nobody has implemented."""


class CapabilityDenied(Exception):
    """Raised when the actor lacks a capability the workflow requires."""


@dataclass(frozen=True)
class Result:
    ok: bool
    failure: str = None
    state: str = None
    state_changes: tuple = ()


class Runtime:
    """Facts: entities (id -> [type, state]) and relations (name -> set of (a, b))."""

    def __init__(self, hooks=None):
        self.entities = {}
        self.relations = {name: set() for name in IR["relations"]}
        self.hooks = dict(hooks or {})

    def add_entity(self, entity_id, entity_type, state=None):
        self.entities[entity_id] = [entity_type, state or IR["initial"]]

    def relate(self, relation, first, second):
        self.relations[relation].add((first, second))

    def state_of(self, entity_id):
        return self.entities[entity_id][1]

    def _hook(self, hook_id, workflow, actor, subject):
        handler = self.hooks.get(hook_id)
        if handler is None:
            hook = next(h for h in IR["unimplemented"] if h["id"] == hook_id)
            raise NotImplementedRule(f"{hook_id} (rule {hook['rule']}): {hook['claim']}")
        return handler(self, workflow, actor, subject)

    def check_model_rules(self):
        """Run hooks for rules not tied to a workflow; unimplemented ones raise NotImplementedRule."""
        for hook in IR["unimplemented"]:
            if hook["scope"] == "model":
                failure = self._hook(hook["id"], None, None, None)
                if failure:
                    return failure
        return None

    def _guard_failure(self, guard, wf, actor, subject):
        kind = guard["kind"]
        if kind == "entity-exists":
            entity = self.entities.get(subject)
            return None if entity and entity[0] == wf["subject_type"] else guard["failure"]
        if kind == "actor-related":
            containers = {a for a, b in self.relations[guard["via"]] if b == subject}
            allowed = any((actor, c) in self.relations[guard["relation"]] for c in containers)
            return None if allowed else guard["failure"]
        if kind == "assignee-matches":
            assignees = {a for a, b in self.relations[guard["relation"]] if b == subject}
            return None if not assignees or actor in assignees else guard["failure"]
        if kind == "terminal-state":
            return guard["failure"] if self.state_of(subject) == guard["state"] else None
        raise ValueError(kind)

    def run(self, workflow, actor, subject, capabilities=None):
        wf = IR["workflows"][workflow]
        granted = set(wf["capabilities"] if capabilities is None else capabilities)
        for capability in wf["requires"]:
            if capability not in granted:
                raise CapabilityDenied(capability)
        for guard in wf["guards"]:
            if guard["kind"] == "entity-exists":
                failure = self._guard_failure(guard, wf, actor, subject)
                if failure:
                    return Result(False, failure)
        for guard in wf["guards"]:
            if guard["kind"] in ("actor-related", "assignee-matches"):
                failure = self._guard_failure(guard, wf, actor, subject)
                if failure:
                    return Result(False, failure, self.state_of(subject))
        for guard in wf["guards"]:
            if guard["kind"] == "terminal-state":
                failure = self._guard_failure(guard, wf, actor, subject)
                if failure:
                    return Result(False, failure, self.state_of(subject))
        for hook_id in wf["hooks"]:
            failure = self._hook(hook_id, workflow, actor, subject)
            if failure:
                return Result(False, failure, self.state_of(subject))
        current = self.state_of(subject)
        for src, dst in wf["transitions"]:
            if src == current:
                self.entities[subject][1] = dst
                return Result(True, None, dst, (f"{src}->{dst}",))
        return Result(False, "invalid-transition." + current, current)
'''
