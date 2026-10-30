"""Explain an Orin model in plain English. Deterministic: no AI, no network.

The output lets a person check: "Is this what I meant?"
"""

from __future__ import annotations


def _short(ref) -> str:
    """Readable name from an id like 'mod/kind/some-name' or a {name, type} dict."""
    if isinstance(ref, dict):
        ref = ref.get("name") or ref.get("id") or ""
    text = str(ref).rsplit("/", 1)[-1]
    return text.replace("-", " ").replace("_", " ")


def _sentence(text) -> str:
    text = str(text).strip()
    if text and text[-1] not in ".?!":
        text += "."
    return text


def _names(items) -> str:
    names = [_short(i) for i in items or []]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _by_kind(objects, kind):
    return [o for o in objects if isinstance(o, dict) and o.get("kind") == kind]


def _claims(obj) -> list[str]:
    return [_sentence(c) for c in obj.get("claims") or [] if str(c).strip()]


def _is_open(obj) -> bool:
    return obj.get("status") == "unresolved"


def _resolved_text(obj) -> str:
    resolution = obj.get("resolution")
    if isinstance(resolution, dict):
        resolution = resolution.get("label") or resolution.get("option") or resolution.get("id")
    return _sentence(resolution) if resolution else ""


def _section(title: str, lines: list[str]) -> list[str]:
    return ["", title, "-" * len(title), *lines]


def explain_document(doc: dict) -> str:
    module = doc.get("module") or {}
    objects = doc.get("objects") or []
    name = _short(module.get("name") or "this program")
    out = [f"What this says: {name}", "=" * (len("What this says: ") + len(name))]

    purpose = module.get("purpose")
    out += _section("Purpose", [_sentence(purpose) if purpose else
                                "No purpose is written yet. Add one line that says why this exists."])

    context = module.get("context") or {}
    if context:
        out += _section("Background",
                        [f"- The {_short(k)} is: {_sentence(v)}" for k, v in context.items()])

    things = []
    for kind, label in (("entity-type", "thing"), ("value-type", "kind of value"),
                        ("state", "state it can be in"), ("relation", "link")):
        found = _by_kind(objects, kind)
        if found:
            things.append(f"- {label.capitalize()}s: {_names(found)}.")
    for ent in _by_kind(objects, "entity-type"):
        fields = [f for f in ent.get("fields") or [] if isinstance(f, dict)]
        if fields:
            things.append(f"- Each {_short(ent)} has: {_names(fields)}.")
    for rel in _by_kind(objects, "relation"):
        ends = [_short(e.get("type")) for e in rel.get("endpoints") or [] if isinstance(e, dict)]
        if len(ends) == 2:
            how = f" ({_short(rel['cardinality'])})" if rel.get("cardinality") else ""
            things.append(f"- {_short(rel).capitalize()}: {ends[0]} to {ends[1]}{how}.")
    caps = _by_kind(objects, "capability")
    if caps:
        things.append(f"- Things people or systems may do: {_names(caps)}.")
    if things:
        out += _section("Words and ideas it uses", things)

    rules = _by_kind(objects, "rule")
    lines = []
    for rule in rules:
        for claim in _claims(rule):
            lines.append(f"- {claim}")
    if lines:
        out += _section("Rules (always true)", lines)

    flows = _by_kind(objects, "workflow")
    lines = []
    for flow in flows:
        head = f"- {_short(flow).capitalize()}"
        if flow.get("inputs"):
            head += f" (needs: {_names(flow['inputs'])})"
        lines.append(head + ":")
        for key, label in (("claims", "Always"), ("postconditions", "When done"),
                           ("failureBehavior", "If it fails"),
                           ("recoveryBehavior", "To recover")):
            lines += [f"    {label}: {_sentence(c)}" for c in flow.get(key) or []]
    if lines:
        out += _section("What it does", lines)

    examples = _by_kind(objects, "example")
    lines = []
    for ex in examples:
        claims = _claims(ex)
        lines.append(f"Story: {_short(ex).capitalize()}")
        if len(claims) == 3:
            lines += [f"  Start: {claims[0]}", f"  What happens: {claims[1]}", f"  Result: {claims[2]}"]
        else:
            lines += [f"  {c}" for c in claims]
            if ex.get("expects"):
                lines.append(f"  Expected: {_names(ex['expects'])}.")
        lines.append("")
    if lines:
        out += _section("Examples as stories", lines[:-1])

    decided, open_ = [], []
    for unc in _by_kind(objects, "uncertainty"):
        question = " ".join(_claims(unc)) or _sentence(unc.get("question") or _short(unc))
        if _is_open(unc):
            weight = "must be answered before building" if unc.get("consequential") \
                else "can wait"
            open_.append(f"- {question} ({weight})")
            if unc.get("why_it_matters"):
                open_.append(f"    Why it matters: {_sentence(unc['why_it_matters'])}")
            for opt in unc.get("options") or []:
                if isinstance(opt, dict) and opt.get("label"):
                    open_.append(f"    Choice: {_sentence(opt['label'])}")
        else:
            answer = _resolved_text(unc)
            decided.append(f"- {question}" + (f" Answer: {answer}" if answer else ""))
    out += _section("Open questions", open_ or ["- None. Nothing is waiting for an answer."])

    for rule in rules:
        if rule.get("status") == "accepted" and rule.get("claims"):
            decided.append(f"- Rule accepted: {_short(rule)}.")
    out += _section("What is decided", decided or ["- Nothing is decided yet."])

    if any(_is_open(u) and u.get("consequential") for u in _by_kind(objects, "uncertainty")):
        verdict = "Not ready: answer the open questions first."
    else:
        verdict = "Nothing blocks building."
    out += ["", f"Summary: {len(rules)} rule(s), {len(flows)} workflow(s), "
                f"{len(examples)} example(s), {sum(1 for o in open_ if o.startswith('- '))} "
                f"open question(s). {verdict}",
            "Is this what you meant? If not, change the .orin file and run explain again."]
    return "\n".join(out)
