"""Emit a standalone unittest file from the examples of an Orin model.

The generated tests do not import any generated or reference code. They talk to an
implementation through a small adapter, so a hand-written implementation can be checked too.

Adapter interface (the only thing an implementation must provide):

    def observe(example_name: str) -> Iterable[str]:
        # Run the situation described by the example and return the observable
        # outcomes that happened, written as the same kebab-case names the model
        # uses in `expects` (for example "standard-confirmation").

Tell the tests where the adapter is with the environment variable ORIN_ADAPTER,
as "package.module:function" (the function may also be a name of an object with an
`observe` method). Without it, the tests are skipped.

Usage: python -m implementations.python.codegen.example_tests <model.json> <outdir>
"""

import argparse
import json
import re
import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

from orin_model import SemanticModel  # noqa: E402


class ExampleTestsError(Exception):
    """Raised when a model has no usable examples."""


_TEMPLATE = '''"""Example tests generated from Orin module @@MODULE@@.

Adapter: set ORIN_ADAPTER="package.module:function". The function takes the example
name (a string) and returns the observable outcomes (strings) of that example.
Each outcome listed in the model's `expects` must be returned. Extra outcomes are allowed.
"""

import importlib
import os
import unittest

EXAMPLES = @@EXAMPLES@@


def load_adapter():
    spec = os.environ.get("ORIN_ADAPTER", "")
    if ":" not in spec:
        return None
    module_name, _, attribute = spec.partition(":")
    target = getattr(importlib.import_module(module_name), attribute)
    return getattr(target, "observe", target)


class ExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observe = staticmethod(load_adapter()) if load_adapter() else None

    def check(self, name, expects):
        if self.observe is None:
            self.skipTest('set ORIN_ADAPTER="package.module:function" to run these tests')
        observed = set(self.observe(name))
        missing = [item for item in expects if item not in observed]
        self.assertEqual(missing, [], f"example {name!r} did not show: {missing}; observed {sorted(observed)}")

@@METHODS@@

if __name__ == "__main__":
    unittest.main()
'''


def _examples(model: SemanticModel) -> list[dict]:
    objects = model.document.get("objects", [])
    found = []
    for obj in objects if isinstance(objects, list) else []:
        if not isinstance(obj, dict) or "/example/" not in str(obj.get("id")):
            continue
        expects = obj.get("expects")
        if isinstance(expects, list) and expects and all(isinstance(e, str) for e in expects):
            name = obj.get("name") if isinstance(obj.get("name"), str) else str(obj["id"]).rsplit("/", 1)[-1]
            found.append({"id": str(obj["id"]), "name": name, "expects": expects})
    return found


def generate_tests_source(model: SemanticModel) -> str:
    examples = _examples(model)
    if not examples:
        raise ExampleTestsError("model has no examples with expected outcomes")
    module = model.document.get("module", {})
    module_id = module.get("id", "unknown") if isinstance(module, dict) else "unknown"
    methods = []
    used: set[str] = set()
    for example in examples:
        base = "test_" + re.sub(r"[^a-z0-9]+", "_", example["name"].lower()).strip("_")
        method, number = base, 2
        while method in used:
            method, number = f"{base}_{number}", number + 1
        used.add(method)
        methods.append(
            f"    def {method}(self):\n"
            f"        example = EXAMPLES[{len(used) - 1}]\n"
            f"        self.check(example[\"name\"], example[\"expects\"])\n"
        )
    values = {
        "MODULE": re.sub(r"[^A-Za-z0-9._/-]", "_", str(module_id))[:200],
        "EXAMPLES": json.dumps([{"name": e["name"], "expects": e["expects"]} for e in examples], indent=4),
        "METHODS": "\n".join(methods),
    }
    return re.sub(r"@@([A-Z]+)@@", lambda m: values[m.group(1)], _TEMPLATE)


def output_name(model: SemanticModel) -> str:
    module = model.document.get("module", {})
    module_id = str(module.get("id", "model")) if isinstance(module, dict) else "model"
    return re.sub(r"[^a-z0-9]+", "_", module_id.lower()).strip("_") + "_example_tests.py"


def write_tests(model: SemanticModel, outdir: Path) -> Path:
    source = generate_tests_source(model)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / output_name(model)
    path.write_text(source, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("outdir")
    args = parser.parse_args(argv)
    try:
        path = write_tests(SemanticModel.from_json_file(args.model), Path(args.outdir))
    except (ExampleTestsError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
