"""Generic generator: a runnable Python module for ANY valid Orin model.

It is the fallback when no dedicated generator exists. For every rule it emits one function that checks the
guarantees it can express (numeric bounds, non-empty values) and raises ``NotImplementedRule`` for the rest. For
every workflow that has transitions it emits a state machine; examples become executable checks. Nothing is
silently dropped: what cannot be checked is named in the module and in the report.
"""

import json
import re

_BOUND = re.compile(
    r"^(?:an?|the)?\s*(?P<fact>[A-Za-z][A-Za-z0-9 -]*?)\s+(?:is|are|must be|stays|never exceeds)?\s*"
    r"(?P<op>at most|no more than|at least|no less than)\s+(?P<n>-?\d+(?:\.\d+)?)\b", re.I)
_NON_EMPTY = re.compile(
    r"^(?:an?|the)?\s*(?P<fact>[A-Za-z][A-Za-z0-9 -]*?)\s+(?:is never empty|must not be empty|is not empty|"
    r"is always present|must be present)\b", re.I)
_LOWER = {"at most": "max", "no more than": "max", "at least": "min", "no less than": "min"}


class GenericError(Exception):
    """The model has nothing a generic generator can turn into code."""


def _short(object_id: object) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(object_id).rsplit("/", 1)[-1])[:100]


def _strings(obj: dict, key: str) -> list[str]:
    value = obj.get(key, [])
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _fact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _guarantee(claim: str) -> dict | None:
    match = _BOUND.match(claim.strip())
    if match:
        return {"kind": _LOWER[match.group("op").lower()], "fact": _fact(match.group("fact")),
                "value": float(match.group("n"))}
    match = _NON_EMPTY.match(claim.strip())
    if match:
        return {"kind": "non-empty", "fact": _fact(match.group("fact"))}
    return None


def _state_name(value: object) -> str:
    return _short(value)


def has_content(document: dict) -> bool:
    objects = document.get("objects", [])
    return isinstance(objects, list) and any(
        isinstance(o, dict) and o.get("kind") in ("rule", "workflow", "example") for o in objects)


def derive_ir(document: dict) -> dict:
    objects = document.get("objects", [])
    if not isinstance(objects, list):
        raise GenericError("malformed model: 'objects' must be a list")
    objs = [o for o in objects if isinstance(o, dict) and isinstance(o.get("id"), str)]
    by_id = {o["id"]: o for o in objs}

    def of(kind):
        return sorted((o for o in objs if o.get("kind") == kind), key=lambda o: o["id"])

    rules = []
    for rule in of("rule"):
        claims = _strings(rule, "claims")
        checks, open_claims = [], []
        for claim in claims:
            guarantee = _guarantee(claim)
            if guarantee:
                checks.append(dict(guarantee, claim=claim))
            else:
                open_claims.append(claim)
        rules.append({"id": rule["id"], "name": _short(rule["id"]), "checks": checks, "open": open_claims})

    workflows = []
    for wf in of("workflow"):
        transitions = [[_state_name(t.get("from")), _state_name(t.get("to"))]
                       for t in wf.get("transitions", []) if isinstance(t, dict)] \
            if isinstance(wf.get("transitions"), list) else []
        sources = {s for s, _ in transitions}
        targets = {d for _, d in transitions}
        initial = sorted(sources - targets or sources)[0] if transitions else None
        workflows.append({"id": wf["id"], "name": _short(wf["id"]), "transitions": transitions, "initial": initial,
                          "steps": _strings(wf, "steps")})

    examples = []
    for ex in of("example"):
        linked = [r for r in _strings(ex, "requires") if by_id.get(r, {}).get("kind") == "workflow"]
        examples.append({
            "id": ex["id"], "name": _short(ex["id"]), "workflows": linked,
            "expects": _strings(ex, "expects") or _strings(ex, "claims"),
        })
    return {"rules": rules, "workflows": workflows, "examples": examples}


def report(module_id: str, ir: dict) -> dict:
    checked = [{"rule": r["name"], "claim": c["claim"]} for r in ir["rules"] for c in r["checks"]]
    unimplemented = [{"rule": r["name"], "claim": c, "status": "NotImplementedRule"}
                     for r in ir["rules"] for c in r["open"]]
    return {"module": _short(module_id), "mode": "generic", "derivedRules": checked,
            "unimplementedRules": unimplemented,
            "workflows": [w["name"] for w in ir["workflows"]], "examples": [e["name"] for e in ir["examples"]]}


def _py_name(prefix: str, name: str, used: set) -> str:
    base = prefix + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    candidate, n = base, 2
    while candidate in used:
        candidate, n = f"{base}_{n}", n + 1
    used.add(candidate)
    return candidate


def render(module_id: str, ir: dict) -> str:
    """Return module source; every model-derived value travels through one JSON string literal."""
    used: set = set()
    rule_fns = [(_py_name("rule_", r["name"], used), r) for r in ir["rules"]]
    wf_fns = [(_py_name("workflow_", w["name"], used), w) for w in ir["workflows"]]
    ex_fns = [(_py_name("example_", e["name"], used), e) for e in ir["examples"]]
    parts = [
        f'"""Generated by Orin generic codegen from model {re.sub(r"[^A-Za-z0-9._/-]", "_", module_id)}. '
        'Do not edit; regenerate instead."""\n',
        "import json\n",
        f"MODULE_ID = {json.dumps(module_id)}",
        f"_IR = json.loads({json.dumps(json.dumps(ir, sort_keys=True))})",
        "_RULES = {r['name']: r for r in _IR['rules']}",
        "_WORKFLOWS = {w['name']: w for w in _IR['workflows']}",
        "_EXAMPLES = {e['name']: e for e in _IR['examples']}",
        _RUNTIME,
    ]
    for fn, rule in rule_fns:
        parts.append(f"def {fn}(**facts):\n"
                     f"    \"\"\"Check rule {rule['name']}.\"\"\"\n    return check_rule({json.dumps(rule['name'])}, facts)\n")
    for fn, wf in wf_fns:
        parts.append(f"def {fn}():\n"
                     f"    \"\"\"New state machine for workflow {wf['name']}.\"\"\"\n"
                     f"    return StateMachine({json.dumps(wf['name'])})\n")
    for fn, ex in ex_fns:
        parts.append(f"def {fn}():\n"
                     f"    \"\"\"Run example {ex['name']}.\"\"\"\n    return check_example({json.dumps(ex['name'])})\n")
    parts.append("RULES = {" + ", ".join(f"{json.dumps(r['name'])}: {fn}" for fn, r in rule_fns) + "}")
    parts.append("WORKFLOWS = {" + ", ".join(f"{json.dumps(w['name'])}: {fn}" for fn, w in wf_fns) + "}")
    parts.append("EXAMPLES = {" + ", ".join(f"{json.dumps(e['name'])}: {fn}" for fn, e in ex_fns) + "}")
    return "\n".join(parts) + "\n"


_RUNTIME = '''
import re

_STATE_EXPECT = re.compile(r"^(?:[A-Za-z][\\w-]*\\.)?state\\s*=\\s*([A-Za-z][\\w-]*)$")

class NotImplementedRule(Exception):
    """A guarantee or step that this generator cannot express as code; an implementation must supply it."""


class RuleViolation(Exception):
    """A checked guarantee does not hold."""


class IllegalTransition(Exception):
    """The workflow does not allow this transition."""


def check_rule(name, facts):
    """Check expressible guarantees against facts; raise NotImplementedRule for the others."""
    rule = _RULES[name]
    for check in rule["checks"]:
        if check["fact"] not in facts:
            raise NotImplementedRule(f"rule {name}: fact '{check['fact']}' is needed to check: {check['claim']}")
        value = facts[check["fact"]]
        if check["kind"] == "max" and not value <= check["value"]:
            raise RuleViolation(f"rule {name}: {check['claim']}")
        if check["kind"] == "min" and not value >= check["value"]:
            raise RuleViolation(f"rule {name}: {check['claim']}")
        if check["kind"] == "non-empty" and (value is None or value == "" or value == [] or value == ()):
            raise RuleViolation(f"rule {name}: {check['claim']}")
    if rule["open"]:
        raise NotImplementedRule(f"rule {name}: not expressible as code: {rule['open'][0]}")
    return True


class StateMachine:
    """State machine from the workflow transitions. A workflow without transitions has no machine."""

    def __init__(self, name):
        workflow = _WORKFLOWS[name]
        if not workflow["transitions"]:
            raise NotImplementedRule(f"workflow {name} has no transitions; steps: {workflow['steps']}")
        self.name = name
        self.state = workflow["initial"]
        self._allowed = {}
        for src, dst in workflow["transitions"]:
            self._allowed.setdefault(src, set()).add(dst)

    def can_move(self, target):
        return target in self._allowed.get(self.state, ())

    def move(self, target):
        if not self.can_move(target):
            raise IllegalTransition(f"workflow {self.name}: {self.state} -> {target} is not allowed")
        self.state = target
        return self.state


def _reachable(workflow):
    machine = StateMachine(workflow["name"])
    seen, todo = {machine.state}, [machine.state]
    while todo:
        for nxt in machine._allowed.get(todo.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen


def check_example(name):
    """Run what can be checked: expected states must be reachable. Anything else raises NotImplementedRule."""
    example = _EXAMPLES[name]
    open_expects = []
    for expect in example["expects"]:
        match = _STATE_EXPECT.match(expect.strip())
        workflows = [_WORKFLOWS[_short_id(w)] for w in example["workflows"] if _short_id(w) in _WORKFLOWS]
        if not match or not workflows:
            open_expects.append(expect)
            continue
        if not any(match.group(1) in _reachable(w) for w in workflows if w["transitions"]):
            raise AssertionError(f"example {name}: state {match.group(1)} is not reachable")
    if open_expects:
        raise NotImplementedRule(f"example {name}: not expressible as code: {open_expects[0]}")
    return True


def run_examples():
    """Map each example name to 'passed' or 'not-implemented: <reason>'."""
    results = {}
    for name in _EXAMPLES:
        try:
            check_example(name)
            results[name] = "passed"
        except NotImplementedRule as error:
            results[name] = f"not-implemented: {error}"
        except AssertionError as error:
            results[name] = f"failed: {error}"
    return results


def _short_id(object_id):
    return object_id.rsplit("/", 1)[-1]
'''
