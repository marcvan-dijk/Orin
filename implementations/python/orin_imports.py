"""Resolve `imports:` in outline .orin files.

Import forms (one per list item):
    - ./shared-types.orin            a relative path
    - ./shared-types.orin as shared  the same, with a chosen alias
    - finance.shared                 a module id (found next to the file)

A qualified reference is written  alias:name  or  alias:kind/name,
for example  shared:person-id  or  shared:rule/no-self-decision.
Only referenced objects are copied into the importing model, marked "imported".
"""

import re
from pathlib import Path
from typing import Any

REFERENCE_LISTS = ("requires", "uses", "affects", "constrainedBy", "demonstrates", "verifies", "evidenceLinks")
QUALIFIED = re.compile(r"^([A-Za-z][\w-]*):([A-Za-z][\w./-]*)$")


def _parse_item(item: str) -> tuple[str, str | None]:
    match = re.match(r"^(.*\S)\s+as\s+([A-Za-z][\w-]*)$", item.strip())
    return (match.group(1), match.group(2)) if match else (item.strip(), None)


def _module_name(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").removeprefix("\ufeff").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("//"):
                match = re.match(r"^module:\s*(\S+)", stripped)
                return match.group(1) if match else None
    except (OSError, UnicodeDecodeError):
        return None
    return None


def resolve_import(target: str, base: Path) -> Path | None:
    """Find the file for an import target, relative to the importing file's folder."""
    folder = base.parent
    if target.endswith(".orin") or "/" in target or "\\" in target:
        candidate = (folder / target).resolve()
        return candidate if candidate.is_file() else None
    direct = folder / f"{target}.orin"
    if direct.is_file():
        return direct.resolve()
    for candidate in sorted(folder.glob("*.orin")):
        if _module_name(candidate) == target:
            return candidate.resolve()
    return None


def _default_alias(target: str, imported_name: str | None) -> str:
    stem = imported_name or Path(target).stem
    return re.sub(r"[^\w-]", "-", stem.split(".")[-1])


def _load(path: Path, parser: Any):
    return parser.parse_file(path, resolve_imports=False)


def _find_cycle(path: Path, parser: Any, stack: list[Path], seen: set[Path]) -> list[Path] | None:
    if path in stack:
        return stack[stack.index(path):] + [path]
    if path in seen:
        return None
    seen.add(path)
    try:
        model = _load(path, parser)
    except ValueError:
        return None
    for item in model.document.get("module", {}).get("imports", []):
        target = resolve_import(_parse_item(item)[0], path)
        if target is not None:
            cycle = _find_cycle(target, parser, stack + [path], seen)
            if cycle:
                return cycle
    return None


def apply_imports(model: Any, path: Path, parser: Any) -> None:
    """Resolve imports of `model` (parsed from `path`), rewriting qualified references.

    Problems are stored in document["importDiagnostics"] and shown by model.diagnostics().
    """
    document = model.document
    module = document.get("module", {})
    items = module.get("imports") or []
    problems: list[dict[str, Any]] = []
    path = Path(path).resolve()
    modules: dict[str, dict[str, Any]] = {}

    def problem(code: str, message: str) -> None:
        problems.append({"code": code, "message": message, "objectId": module.get("id")})

    for item in items:
        target, alias = _parse_item(item)
        found = resolve_import(target, path)
        if found is None:
            external = alias is None and re.fullmatch(r"[\w-]+", target) is not None
            if external:
                continue  # a bare name with no file is an external contract, not a file import
            problem("ORIN-I001", f"import not found: {target}. Check the path or the module id.")
            continue
        cycle = _find_cycle(found, parser, [path], set())
        if cycle:
            problem("ORIN-I002", "import cycle: " + " -> ".join(p.name for p in cycle))
            continue
        try:
            imported = _load(found, parser)
        except ValueError as error:
            problem("ORIN-I003", f"imported file cannot be read: {target}: {str(error).splitlines()[0]}")
            continue
        alias = alias or _default_alias(target, imported.document.get("module", {}).get("name"))
        if alias in modules:
            problem("ORIN-I004", f"import alias used twice: {alias}. Use 'as' to choose another alias.")
            continue
        modules[alias] = imported.document

    objects = document.setdefault("objects", [])
    present = {o.get("id") for o in objects if isinstance(o, dict)}

    def lookup(text: str) -> str | None:
        match = QUALIFIED.match(text)
        if not match or match.group(1) not in modules:
            return None
        alias, name = match.groups()
        wanted_kind, _, wanted_name = name.rpartition("/")
        matches = [o for o in modules[alias].get("objects", []) if isinstance(o, dict)
                   and o.get("name") == wanted_name and (not wanted_kind or o.get("kind") == wanted_kind
                                                          or o.get("kind") == f"{wanted_kind}-type")]
        if len(matches) != 1:
            reason = "is ambiguous; write alias:kind/name" if matches else "does not exist in the imported module"
            problem("ORIN-I005", f"qualified reference {text} {reason}.")
            return text
        found = matches[0]
        copy_with_dependencies(found, modules[alias])
        return found["id"]

    def copy_with_dependencies(found: dict[str, Any], source: dict[str, Any]) -> None:
        if found["id"] in present:
            return
        objects.append({**found, "imported": True})
        present.add(found["id"])
        by_id = {o.get("id"): o for o in source.get("objects", []) if isinstance(o, dict)}
        for field in REFERENCE_LISTS:
            for target in found.get(field, []) if isinstance(found.get(field), list) else []:
                if target in by_id:
                    copy_with_dependencies(by_id[target], source)
        for field, key in (("fields", "type"), ("endpoints", "type")):
            for entry in found.get(field, []) if isinstance(found.get(field), list) else []:
                if isinstance(entry, dict) and entry.get(key) in by_id:
                    copy_with_dependencies(by_id[entry[key]], source)

    def rewrite(owner: dict[str, Any]) -> None:
        for field in REFERENCE_LISTS:
            if isinstance(owner.get(field), list):
                owner[field] = [lookup(v) or v if isinstance(v, str) else v for v in owner[field]]
        for field, key in (("fields", "type"), ("endpoints", "type"), ("inputs", "type"), ("outputs", "type"),
                           ("actorCapabilities", "capability")):
            for entry in owner.get(field, []) if isinstance(owner.get(field), list) else []:
                if isinstance(entry, dict) and isinstance(entry.get(key), str):
                    entry[key] = lookup(entry[key]) or entry[key]

    for obj in list(objects):
        if isinstance(obj, dict) and not obj.get("imported"):
            rewrite(obj)
    if problems:
        document["importDiagnostics"] = problems
