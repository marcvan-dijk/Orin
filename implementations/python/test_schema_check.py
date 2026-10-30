import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import schema_check

CONFORMANCE = Path(__file__).resolve().parents[2] / "tests" / "conformance"
SCHEMA = schema_check.load_schema(CONFORMANCE / "model.schema.json")
PATTERNS = ("*.model.json", "*.decided.json", "*.structured.json")


def fixtures():
    for pattern in PATTERNS:
        yield from sorted(CONFORMANCE.glob(pattern))


def load(name):
    return json.loads((CONFORMANCE / name).read_text(encoding="utf-8"))


class SchemaCheckTests(unittest.TestCase):
    def test_every_model_fixture_is_valid(self):
        paths = list(fixtures())
        self.assertGreater(len(paths), 10)
        for path in paths:
            with self.subTest(fixture=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(schema_check.validate(SCHEMA, data), [])

    def test_mutations_are_invalid(self):
        def drop_objects(m):
            del m["objects"]

        def unknown_kind(m):
            m["objects"][0]["kind"] = "banana"

        def bad_status(m):
            m["objects"][0]["status"] = "maybe"

        def extra_property(m):
            m["objects"][0]["surprise"] = 1

        def missing_name(m):
            del m["objects"][0]["name"]

        def empty_id(m):
            m["objects"][0]["id"] = ""

        def module_not_object(m):
            m["module"] = "shared-tasks"

        def bad_cardinality(m):
            next(o for o in m["objects"] if o.get("kind") == "relation")["cardinality"] = "lots"

        def bad_durability(m):
            next(o for o in m["objects"] if o.get("kind") == "effect")["durability"] = "forever"

        def workflow_requires_string(m):
            next(o for o in m["objects"] if o.get("kind") == "workflow")["requires"] = "x"

        def uncertainty_flag_string(m):
            next(o for o in m["objects"] if o.get("kind") == "uncertainty")["consequential"] = "yes"

        def bad_source_line(m):
            m["module"]["source"] = {"line": 0}

        mutations = [
            drop_objects, unknown_kind, bad_status, extra_property, missing_name,
            empty_id, module_not_object, bad_cardinality, bad_durability,
            workflow_requires_string, uncertainty_flag_string, bad_source_line,
        ]
        base = load("shared-tasks.model.json")
        base["objects"].append({
            "id": "shared-tasks/uncertainty/u", "kind": "uncertainty", "name": "u",
            "status": "unresolved", "consequential": True, "authority": "human",
        })
        self.assertEqual(schema_check.validate(SCHEMA, base), [])
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                model = copy.deepcopy(base)
                mutate(model)
                self.assertNotEqual(schema_check.validate(SCHEMA, model), [])

    def test_checker_basics(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"enum": [1]}}}
        self.assertEqual(schema_check.validate(schema, {"a": 1}), [])
        self.assertNotEqual(schema_check.validate(schema, {"a": True}), [])
        self.assertNotEqual(schema_check.validate(schema, {}), [])


if __name__ == "__main__":
    unittest.main()
