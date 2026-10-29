"""Claim-driven generation for models whose rules are prose claims and whose workflows have no transitions.

Recognised claim shapes become generic, named constraints (deadline, capped accrual, threshold block, once only,
exclusive holder, FIFO queue hand-off, blocked-while). Nothing is application specific: names come from the claim
text. Values the model names but does not fix (a rate, a limit, a cap) are required runtime parameters and are
listed in the report. Every claim no shape matches is a loud NotImplementedRule hook.
"""

import pprint
import re

from .model_driven import ModelDrivenError, _ident, _list, _short, _text

_NUM = r"(\d{1,6})"
_UNIT = r"(second|minute|hour|day|week)s?"
_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}

_PATTERNS = (
    ("accrual", re.compile(
        r"\baccrues? for each " + _UNIT + r"\b.*?\b(?:never|not) exceeds? (?:the )?(?P<cap>[a-z][a-z -]{0,60}?)\.?$", re.I)),
    ("threshold-block", re.compile(
        r"\bwith (?P<measure>[a-z][a-z -]{0,40}?) (?:above|over|exceeding) (?:the )?(?P<limit>[a-z][a-z -]{0,40}?) "
        r"(?:cannot|may not|must not) (?P<action>[a-z]+)\b", re.I)),
    ("blocked-while", re.compile(
        r"\b(?:cannot|may not|must not) be (?P<action>[a-z]+) while (?P<condition>[a-z][a-z ]{0,80}?)\.?$", re.I)),
    ("once-only", re.compile(r"\b(?:cannot|may not|must not) be (?P<action>[a-z]+) again\b", re.I)),
    ("exclusive-holder", re.compile(r"\b(?:is|are) (?P<state>[a-z][a-z ]{0,30}?) to at most one (?P<holder>[a-z]+)\b", re.I)),
    ("deadline", re.compile(r"\b" + _NUM + r" " + _UNIT + r" after (?P<anchor>[a-z][a-z ]{0,60}?)\.?$", re.I)),
    ("queue-offer", re.compile(r"\bheld for the first (?P<member>[a-z]+) in the queue\b", re.I)),
    ("queue-pass", re.compile(r"\bpasses to the next (?P<member>[a-z]+) in the queue\b", re.I)),
)


def has_prose_rules(document: dict) -> bool:
    objects = document.get("objects", [])
    return isinstance(objects, list) and any(
        isinstance(o, dict) and o.get("kind") == "rule" and isinstance(o.get("claims"), list) and o["claims"]
        for o in objects)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60]


def _constraint(kind: str, match, rname: str, index: int) -> dict:
    cid = f"{rname}.{index}"
    group = match.groupdict()
    base = {"id": _ident(cid), "kind": kind, "rule": rname}
    if kind == "accrual":
        unit = match.group(1).lower()
        return {**base, "unit": unit, "cap": _slug(group["cap"]), "rate_param": f"{_ident(cid)}.rate"}
    if kind == "threshold-block":
        return {**base, "measure": _slug(group["measure"]), "limit": _slug(group["limit"]),
                "action": _slug(group["action"]), "failure": f"refused-{_slug(group['action'])}"}
    if kind == "blocked-while":
        return {**base, "action": _slug(group["action"]), "condition": _slug(group["condition"]),
                "failure": f"refused-{_slug(group['action'])}"}
    if kind == "once-only":
        return {**base, "action": _slug(group["action"]), "failure": f"already-{_slug(group['action'])}"}
    if kind == "exclusive-holder":
        return {**base, "holder": _slug(group["holder"]), "state": _slug(group["state"]), "failure": "already-held"}
    if kind == "deadline":
        unit = match.group(2).lower()
        return {**base, "amount": int(match.group(1)), "unit": unit, "anchor": _slug(group["anchor"]),
                "expires": bool(re.search(r"\bexpires?\b", match.string, re.I))}
    return {**base, "member": _slug(group["member"])}


def derive_ir(document: dict) -> dict:
    objects = document.get("objects", [])
    if not isinstance(objects, list):
        raise ModelDrivenError("malformed model: 'objects' must be a list")
    rules = sorted((o for o in objects if isinstance(o, dict) and o.get("kind") == "rule"
                    and isinstance(o.get("id"), str)), key=lambda o: o["id"])
    constraints, hooks, derived = [], [], []
    for rule in rules:
        rname = _short(rule["id"])
        for claim in (c for c in _list(rule, "claims") if isinstance(c, str)):
            text = claim.strip()
            for kind, pattern in _PATTERNS:
                match = pattern.search(text)
                if match:
                    constraints.append(_constraint(kind, match, rname, len(constraints)))
                    derived.append({"rule": rname, "claim": _text(claim), "constraint": constraints[-1]["id"]})
                    break
            else:
                hooks.append({"id": f"hook.{rname}.{len(hooks)}", "rule": rname, "scope": "model",
                              "claim": _text(claim)})
    if not constraints:
        raise ModelDrivenError("model has no checkable rules")
    parameters = []
    for c in constraints:
        if c["kind"] == "accrual":
            parameters += [c["rate_param"], c["cap"]]
        elif c["kind"] == "threshold-block":
            parameters += [c["measure"], c["limit"]]
    open_questions = sorted(
        _short(o["id"]) for o in objects if isinstance(o, dict) and o.get("kind") == "uncertainty"
        and o.get("status") == "unresolved" and isinstance(o.get("id"), str))
    return {
        "constraints": constraints,
        "parameters": sorted(set(parameters)),
        "unimplemented": hooks,
        "derived": derived,
        "structural": [],
        "openQuestions": open_questions,
        "unitSeconds": dict(_UNIT_SECONDS),
    }


def render_ir(ir: dict) -> str:
    return pprint.pformat(ir, sort_dicts=True, width=100)


def report(module_id: str, ir: dict) -> dict:
    return {
        "module": _ident(module_id),
        "mode": "claim-driven",
        "derivedRules": ir["derived"],
        "requiredParameters": ir["parameters"],
        "openQuestions": ir["openQuestions"],
        "structurallyVerifiedRules": ir["structural"],
        "unimplementedRules": [
            {"id": h["id"], "rule": h["rule"], "scope": h["scope"], "claim": h["claim"], "status": "NotImplementedRule"}
            for h in ir["unimplemented"]
        ],
    }


TEMPLATE = '''"""Generated by Orin codegen from model @@MODULE@@. Do not edit; regenerate instead.

Claim-driven constraints (see IR). Times are seconds. Parameters the model names but does not fix must be
supplied to Runtime(params=...). Claims codegen could not derive are NotImplementedRule hooks.
"""

MODULE_ID = @@MODULE@@
IR = @@IR@@
UNIMPLEMENTED_RULES = tuple(IR["unimplemented"])
_BY_ID = {c["id"]: c for c in IR["constraints"]}


class NotImplementedRule(Exception):
    """A model rule that codegen could not derive mechanically and nobody has implemented."""


class MissingParameter(Exception):
    """A value the model names (rate, limit, cap) but does not fix was not supplied."""


class Runtime:
    def __init__(self, params=None, hooks=None):
        self.params = dict(params or {})
        self.hooks = dict(hooks or {})
        self.holders = {}
        self.done = set()
        self.queues = {}
        self.offers = {}

    def _c(self, cid, kind):
        constraint = _BY_ID[cid]
        if constraint["kind"] != kind:
            raise ValueError(f"{cid} is a {constraint['kind']} constraint, not {kind}")
        return constraint

    def _param(self, name):
        if name not in self.params:
            raise MissingParameter(name)
        return self.params[name]

    def hook(self, hook_id, *args):
        handler = self.hooks.get(hook_id)
        if handler is None:
            hook = next(h for h in IR["unimplemented"] if h["id"] == hook_id)
            raise NotImplementedRule(f"{hook_id} (rule {hook['rule']}): {hook['claim']}")
        return handler(self, *args)

    def check_model_rules(self):
        for hook in IR["unimplemented"]:
            self.hook(hook["id"])

    def deadline(self, cid, start):
        c = self._c(cid, "deadline")
        return start + c["amount"] * IR["unitSeconds"][c["unit"]]

    def is_expired(self, cid, start, now):
        return now > self.deadline(cid, start)

    def units_overdue(self, cid, due, now, unit=None):
        seconds = IR["unitSeconds"][unit or _BY_ID[cid]["unit"]]
        return max(0, int((now - due) // seconds))

    def accrued(self, cid, units):
        c = self._c(cid, "accrual")
        return min(units * self._param(c["rate_param"]), self._param(c["cap"]))

    def threshold_failure(self, cid, amount):
        c = self._c(cid, "threshold-block")
        return c["failure"] if amount > self._param(c["limit"]) else None

    def blocked_failure(self, cid, condition_holds):
        c = self._c(cid, "blocked-while")
        return c["failure"] if condition_holds else None

    def once(self, cid, key):
        c = self._c(cid, "once-only")
        if (cid, key) in self.done:
            return c["failure"]
        self.done.add((cid, key))
        return None

    def acquire(self, cid, resource, holder):
        c = self._c(cid, "exclusive-holder")
        if self.holders.get((cid, resource), holder) != holder:
            return c["failure"]
        self.holders[(cid, resource)] = holder
        return None

    def release(self, cid, resource):
        self._c(cid, "exclusive-holder")
        self.holders.pop((cid, resource), None)

    def enqueue(self, queue, member):
        self.queues.setdefault(queue, []).append(member)

    def _offer(self, queue, now):
        waiting = self.queues.get(queue, [])
        if not waiting:
            self.offers.pop(queue, None)
            return None
        self.offers[queue] = (waiting[0], now)
        return waiting[0]

    def offer_first(self, cid, queue, now):
        self._c(cid, "queue-offer")
        return self._offer(queue, now)

    def pass_on(self, cid, queue, now):
        self._c(cid, "queue-pass")
        waiting = self.queues.get(queue, [])
        if waiting:
            waiting.pop(0)
        return self._offer(queue, now)
'''
