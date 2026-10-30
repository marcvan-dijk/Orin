"""Export an Orin model as a readable specification document (md, json, html)."""

from __future__ import annotations

from html import escape
import json
from typing import Any

FORMATS = ("md", "json", "html")
GLOSSARY_KINDS = ("entity-type", "value-type", "state", "capability", "relation", "effect")
SECTIONS = ("Purpose", "Glossary", "Rules", "Decisions", "Open questions")


def _strs(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item if isinstance(item, str) else json.dumps(item, sort_keys=True) for item in value]
    return []


def _refs(value: Any) -> list[str]:
    return [item.get("id", "") if isinstance(item, dict) else str(item) for item in value] \
        if isinstance(value, list) else _strs(value)


def _definition(obj: dict) -> str:
    for key in ("definition", "description", "purpose"):
        if isinstance(obj.get(key), str):
            return obj[key]
    return " ".join(_strs(obj.get("claims")))


def _name(obj: dict) -> str:
    return str(obj.get("name") or obj.get("id") or "(unnamed)")


def build_document(document: dict) -> dict:
    """Return the plain structure shared by every output format."""
    module = document.get("module") if isinstance(document.get("module"), dict) else {}
    objects = [o for o in document.get("objects", []) if isinstance(o, dict)]
    examples = [o for o in objects if o.get("kind") == "example"]

    def examples_for(rule: dict) -> list[dict]:
        linked = set(_refs(rule.get("evidenceLinks")))
        found = []
        for ex in examples:
            targets = set(_refs(ex.get("demonstrates")) + _refs(ex.get("expects")) + _refs(ex.get("verifies")))
            if ex.get("id") in linked or rule.get("id") in targets:
                found.append(ex)
        return found

    rules, used = [], set()
    for rule in (o for o in objects if o.get("kind") == "rule"):
        linked = examples_for(rule)
        used.update(id(ex) for ex in linked)
        rules.append({"name": _name(rule), "statements": _strs(rule.get("claims")),
                      "status": str(rule.get("status", "")),
                      "examples": [{"name": _name(ex), "steps": _strs(ex.get("claims"))} for ex in linked]})
    other = [{"name": _name(ex), "steps": _strs(ex.get("claims"))}
             for ex in examples if id(ex) not in used]

    decisions, questions = [], []
    for obj in objects:
        kind, status = obj.get("kind"), str(obj.get("status", ""))
        if kind == "decision" or (kind == "uncertainty" and status != "unresolved"):
            resolution = obj.get("resolution")
            chosen = resolution.get("option") if isinstance(resolution, dict) else resolution
            rationale = obj.get("rationale") or obj.get("why_it_matters") or \
                (resolution.get("rationale") if isinstance(resolution, dict) else "")
            decisions.append({"name": _name(obj), "statement": " ".join(_strs(obj.get("claims"))),
                              "chosen": "" if chosen is None else str(chosen),
                              "rationale": str(rationale or ""), "status": status})
        elif kind == "uncertainty":
            options = [{"id": str(o.get("id", "")), "label": str(o.get("label", ""))}
                       for o in obj.get("options", []) if isinstance(o, dict)]
            questions.append({"name": _name(obj), "question": " ".join(_strs(obj.get("claims"))),
                              "why_it_matters": str(obj.get("why_it_matters", "")),
                              "blocking": bool(obj.get("consequential")), "options": options})

    return {
        "title": str(module.get("name") or "Untitled specification"),
        "purpose": str(module.get("purpose") or ""),
        "glossary": [{"term": _name(o), "kind": str(o.get("kind")), "meaning": _definition(o)}
                     for kind in GLOSSARY_KINDS for o in objects if o.get("kind") == kind],
        "rules": rules,
        "other_examples": other,
        "decisions": decisions,
        "open_questions": questions,
    }


def _md_text(text: str) -> str:
    return " ".join(str(text).split())


def render_md(doc: dict) -> str:
    out = [f"# {_md_text(doc['title'])}", "", "## Purpose", "",
           _md_text(doc["purpose"]) or "No purpose is written yet.", "", "## Glossary", ""]
    out += [f"- **{_md_text(g['term'])}** ({g['kind']}): {_md_text(g['meaning']) or 'No definition yet.'}"
            for g in doc["glossary"]] or ["No domain terms."]
    out += ["", "## Rules", ""]
    for rule in doc["rules"]:
        out.append(f"### {_md_text(rule['name'])}")
        out += ["", *(_md_text(s) for s in rule["statements"]), ""]
        for ex in rule["examples"]:
            out.append(f"- Example {_md_text(ex['name'])}: " + " ".join(_md_text(s) for s in ex["steps"]))
        out.append("")
    if not doc["rules"]:
        out += ["No rules.", ""]
    if doc["other_examples"]:
        out += ["### Other examples", ""]
        out += [f"- {_md_text(ex['name'])}: " + " ".join(_md_text(s) for s in ex["steps"])
                for ex in doc["other_examples"]]
        out.append("")
    out += ["## Decisions", ""]
    for d in doc["decisions"]:
        line = f"- **{_md_text(d['name'])}**: {_md_text(d['statement'])}"
        if d["chosen"]:
            line += f" Chosen: {_md_text(d['chosen'])}."
        if d["rationale"]:
            line += f" Why: {_md_text(d['rationale'])}"
        out.append(line)
    if not doc["decisions"]:
        out.append("No decisions recorded.")
    out += ["", "## Open questions", ""]
    for q in doc["open_questions"]:
        out.append(f"- **{_md_text(q['name'])}**{' (blocking)' if q['blocking'] else ''}: "
                   f"{_md_text(q['question'])}")
        if q["why_it_matters"]:
            out.append(f"  - Why it matters: {_md_text(q['why_it_matters'])}")
        out += [f"  - Option {_md_text(o['id'])}: {_md_text(o['label'])}" for o in q["options"]]
    if not doc["open_questions"]:
        out.append("No open questions.")
    return "\n".join(out) + "\n"


_CSS = ("body{font-family:sans-serif;max-width:48em;margin:2em auto;padding:0 1em;line-height:1.5}"
        "h1,h2{border-bottom:1px solid #ccc}code{background:#eee;padding:0 .2em}")


def render_html(doc: dict) -> str:
    e = escape

    def li(items: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""

    parts = [f"<h1>{e(doc['title'])}</h1>",
             f"<h2>Purpose</h2><p>{e(doc['purpose']) or 'No purpose is written yet.'}</p>",
             "<h2>Glossary</h2>" + (
                 "<dl>" + "".join(f"<dt>{e(g['term'])} <small>({e(g['kind'])})</small></dt>"
                                  f"<dd>{e(g['meaning'])}</dd>" for g in doc["glossary"]) + "</dl>"
                 if doc["glossary"] else "<p>No domain terms.</p>"),
             "<h2>Rules</h2>"]
    for rule in doc["rules"]:
        parts.append(f"<h3>{e(rule['name'])}</h3>" + "".join(f"<p>{e(s)}</p>" for s in rule["statements"])
                     + li([f"Example {e(x['name'])}: {e(' '.join(x['steps']))}" for x in rule["examples"]]))
    if not doc["rules"]:
        parts.append("<p>No rules.</p>")
    if doc["other_examples"]:
        parts.append("<h3>Other examples</h3>" + li(
            [f"{e(x['name'])}: {e(' '.join(x['steps']))}" for x in doc["other_examples"]]))
    parts.append("<h2>Decisions</h2>" + (li([
        f"<strong>{e(d['name'])}</strong>: {e(d['statement'])}"
        + (f" Chosen: {e(d['chosen'])}." if d["chosen"] else "")
        + (f" Why: {e(d['rationale'])}" if d["rationale"] else "") for d in doc["decisions"]])
        or "<p>No decisions recorded.</p>"))
    qs = []
    for q in doc["open_questions"]:
        qs.append(f"<strong>{e(q['name'])}</strong>{' (blocking)' if q['blocking'] else ''}: {e(q['question'])}"
                  + (f"<br>Why it matters: {e(q['why_it_matters'])}" if q["why_it_matters"] else "")
                  + li([f"Option {e(o['id'])}: {e(o['label'])}" for o in q["options"]]))
    parts.append("<h2>Open questions</h2>" + (li(qs) or "<p>No open questions.</p>"))
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{e(doc['title'])}</title><style>{_CSS}</style></head><body>\n"
            + "\n".join(parts) + "\n</body></html>\n")


def export(document: dict, fmt: str) -> str:
    if fmt not in FORMATS:
        raise ValueError(f"unknown format '{fmt}'; use one of: {', '.join(FORMATS)}")
    doc = build_document(document)
    if fmt == "json":
        return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return render_md(doc) if fmt == "md" else render_html(doc)
