import tempfile
import unittest
from pathlib import Path

from .orin_parser import OrinParser

ROOT = Path(__file__).parents[2]
EXAMPLES = ROOT / "examples" / "imports"
BASE = "module: {name}\n\npurpose:\n  Test.\n\n{extra}"


class ImportTests(unittest.TestCase):
    def write(self, folder, name, body):
        path = Path(folder) / f"{name}.orin"
        path.write_text(body, encoding="utf-8")
        return path

    def test_example_resolves_qualified_references(self):
        model = OrinParser().parse_file(EXAMPLES / "leave-request.orin")
        self.assertEqual(model.diagnostics(), [])
        rule = next(o for o in model.document["objects"] if o["id"] == "leave-request/rule/manager-decides")
        self.assertEqual(rule["requires"], ["shared-people/rule/no-self-decision"])
        imported = {o["id"] for o in model.document["objects"] if o.get("imported")}
        self.assertIn("shared-people/entity-type/person", imported)

    def test_import_by_module_id(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, "other-file", "module: shared.things\n\ntype: thing-id\n")
            main = self.write(d, "main", "module: main\n\nimports:\n  - shared.things\n\n"
                              "entity: box\n  identity:\n    id things:thing-id\n")
            model = OrinParser().parse_file(main)
        self.assertEqual(model.diagnostics(), [])
        box = next(o for o in model.document["objects"] if o["id"] == "main/entity-type/box")
        self.assertEqual(box["fields"][0]["type"], "shared.things/value-type/thing-id")

    def test_missing_import(self):
        with tempfile.TemporaryDirectory() as d:
            main = self.write(d, "main", "module: main\n\nimports:\n  - ./nope.orin\n\ntype: a\n")
            codes = [x.code for x in OrinParser().parse_file(main).diagnostics()]
        self.assertIn("ORIN-I001", codes)

    def test_cyclic_import(self):
        with tempfile.TemporaryDirectory() as d:
            a = self.write(d, "a", "module: a\n\nimports:\n  - ./b.orin\n\ntype: x\n")
            self.write(d, "b", "module: b\n\nimports:\n  - ./a.orin\n\ntype: y\n")
            diagnostics = OrinParser().parse_file(a).diagnostics()
        self.assertTrue(any(x.code == "ORIN-I002" and "a.orin -> b.orin -> a.orin" in x.message for x in diagnostics))

    def test_unknown_qualified_name(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, "lib", "module: lib\n\ntype: known\n")
            main = self.write(d, "main", "module: main\n\nimports:\n  - ./lib.orin\n\n"
                              "entity: box\n  identity:\n    id lib:missing\n")
            codes = [x.code for x in OrinParser().parse_file(main).diagnostics()]
        self.assertIn("ORIN-I005", codes)


if __name__ == "__main__":
    unittest.main()
