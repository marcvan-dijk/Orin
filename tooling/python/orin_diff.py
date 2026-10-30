"""Show what MEANING changed between two Orin model versions.

Formatting and ordering are ignored: models are compared by object id after
canonical normalisation.
"""
from __future__ import annotations

from typing import Any

_SKIP_FIELDS = {"id"}
_LABELS = {"rule": "rule", "example": "example", "decision": "decision",
           "uncertainty": "uncertainty", "workflow": "workflow"}


def _kind(obj_id: str, obj: dict[str, Any]) -> str:
    parts = obj_id.split("/")
    if len(parts) >= 2 and parts[-2] in _LABELS:
        return parts[-2]
    return str(obj.get("kind") or "other")


def _index(canonical: dict[str, Any]) -> dict[str, dict[str, Any]]:
    objects = {o["id"]: o for o in canonical.get("objects", []) if isinstance(o, dict) and "id" in o}
    module = canonical.get("module")
    if isinstance(module, dict) and "id" in module:
        objects.setdefault(module["id"], module)
    return objects


def _norm(value: Any) -> Any:
    # Lists of claims/steps/expects are compared as sets only when all items are strings
    # and the field is not an ordered one (steps).
    return value


def _field_changes(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    changes = []
    for field in sorted((set(old) | set(new)) - _SKIP_FIELDS):
        a, b = old.get(field), new.get(field)
        if field != "steps" and isinstance(a, list) and isinstance(b, list):
            try:
                if sorted(a) == sorted(b):
                    continue
            except TypeError:
                pass
        if a != b:
            changes.append({"field": field, "old": a, "new": b})
    return changes


def diff_models(old_canonical: dict[str, Any], new_canonical: dict[str, Any]) -> dict[str, Any]:
    old, new = _index(old_canonical), _index(new_canonical)
    entries = []
    for obj_id in sorted(set(old) | set(new)):
        if obj_id not in old:
            entries.append({"id": obj_id, "kind": _kind(obj_id, new[obj_id]), "change": "added",
                            "fields": []})
        elif obj_id not in new:
            entries.append({"id": obj_id, "kind": _kind(obj_id, old[obj_id]), "change": "removed",
                            "fields": []})
        else:
            fields = _field_changes(old[obj_id], new[obj_id])
            if fields:
                entries.append({"id": obj_id, "kind": _kind(obj_id, new[obj_id]),
                                "change": "changed", "fields": fields})
    for entry in entries:
        entry["name"] = entry["id"].split("/")[-1]
        entry["detail"] = _detail(entry)
    return {"changed": bool(entries), "changes": entries,
            "summary": {k: sum(1 for e in entries if e["kind"] == k) for k in
                        sorted({e["kind"] for e in entries})}}


def _detail(entry: dict[str, Any]) -> str:
    kind, change, name = entry["kind"], entry["change"], entry["name"]
    if kind == "uncertainty":
        if change == "added":
            return f"Uncertainty opened: {name}"
        if change == "removed":
            return f"Uncertainty removed: {name}"
        status = [f for f in entry["fields"] if f["field"] == "status"]
        if status and status[0]["new"] == "resolved":
            return f"Uncertainty closed (resolved): {name}"
        if status and status[0]["old"] == "resolved":
            return f"Uncertainty re-opened: {name}"
        return f"Uncertainty changed: {name}"
    if kind == "decision":
        return {"added": f"Decision made: {name}", "removed": f"Decision removed: {name}",
                "changed": f"Decision changed: {name}"}[change]
    label = {"rule": "Rule", "example": "Example", "workflow": "Workflow"}.get(kind, f"Object ({kind})")
    return f"{label} {change}: {name}"


def render_text(report: dict[str, Any]) -> str:
    if not report["changed"]:
        return "No change in meaning."
    lines = [f"{len(report['changes'])} change(s) in meaning:"]
    for entry in report["changes"]:
        lines.append(f"  - {entry['detail']}")
        for f in entry["fields"]:
            lines.append(f"      {f['field']}: {f['old']!r} -> {f['new']!r}")
    return "\n".join(lines)
