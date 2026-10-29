import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementations.python.codegen import generate as gen  # noqa: E402
from implementations.python.orin_agent_core import OrinDecisionAgent  # noqa: E402
from implementations.python.orin_model import SemanticModel  # noqa: E402

CONF = ROOT / "tests" / "conformance"
MINIMAL = CONF / "shared-tasks.minimal.model.json"
CASES = CONF / "shared-tasks.minimal.cases.json"
DECISION = "shared-tasks.minimal/uncertainty/non-member-assignee-completion"


def _resolved(option="membership-required"):
    return deepcopy(OrinDecisionAgent().apply_decision(MINIMAL, DECISION, option).model.document)


def _load(doc, tmp, name="shared_tasks_minimal_generated"):
    model_path = Path(tmp) / "model.json"
    model_path.write_text(json.dumps(doc), encoding="utf-8")
    target = gen.generate(model_path, Path(tmp) / "out")
    spec = importlib.util.spec_from_file_location(name, target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, target


def _setup(mod, setup):
    rt = mod.Runtime()
    # "owner" is an implicit member (relationship-constraints is a reported NotImplementedRule hook)
    for person in [setup["owner"], *setup["members"]]:
        rt.relate("member-of", person, setup["list"])
    task = setup.get("task")
    if task:
        rt.add_entity(task["id"], "task", task["state"])
        rt.relate("contains", task["list"], task["id"])
        if task.get("assignee"):
            rt.relate("assigned-to", task["assignee"], task["id"])
    return rt


class ModelDrivenSharedTasksTests(unittest.TestCase):
    def test_generated_module_exercises_every_example_case(self):
        cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            mod, _ = _load(_resolved(), tmp)
            self.assertEqual(len(cases), 4)
            for case in cases:
                with self.subTest(case=case["id"]):
                    rt = _setup(mod, case["setup"])
                    action, then = case["action"], case["then"]
                    before = {k: list(v) for k, v in rt.entities.items()}
                    result = rt.run(action["workflow"], action["actor"], action["task"])
                    self.assertEqual(result.ok, then["ok"])
                    self.assertEqual(result.failure, then.get("failure"))
                    if "taskState" in then:
                        self.assertEqual(rt.state_of(action["task"]), then["taskState"])
                    if then.get("persisted"):
                        self.assertEqual(rt.state_of(action["task"]), "completed")
                    if then.get("stateChanges") == "none":
                        self.assertEqual(rt.entities, before)

    def test_non_member_assignee_and_assignee_mismatch(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            mod, _ = _load(_resolved(), tmp)
            rt = _setup(mod, {"owner": "a", "members": ["b", "c"], "list": "l",
                              "task": {"id": "t", "list": "l", "state": "open", "assignee": "b"}})
            self.assertEqual(rt.run("complete-task", "c", "t").failure, "not-assigned")
            rt.relate("assigned-to", "z", "t")
            self.assertEqual(rt.run("complete-task", "z", "t").failure, "unauthorized")
            self.assertEqual(rt.state_of("t"), "open")
            with self.assertRaises(mod.CapabilityDenied):
                rt.run("complete-task", "b", "t", capabilities=set())

    def test_report_lists_not_implemented_rules_and_matches_module(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            mod, target = _load(_resolved(), tmp)
            report = json.loads(target.with_suffix(".report.json").read_text(encoding="utf-8"))
            names = {r["rule"] for r in report["unimplementedRules"]}
            self.assertEqual(names, {"relationship-constraints"})
            self.assertTrue(all(r["status"] == "NotImplementedRule" for r in report["unimplementedRules"]))
            self.assertEqual([r["id"] for r in report["unimplementedRules"]],
                             [r["id"] for r in mod.UNIMPLEMENTED_RULES])
            self.assertEqual(len(report["unimplementedRules"]), 3)
            with self.assertRaises(mod.NotImplementedRule):
                mod.Runtime().check_model_rules()

    def test_underivable_workflow_rule_fails_loudly_until_implemented(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            mod, target = _load(_resolved("assignee-may-complete"), tmp)
            report = json.loads(target.with_suffix(".report.json").read_text(encoding="utf-8"))
            hooks = [r for r in report["unimplementedRules"] if r["scope"] == "workflow"]
            self.assertEqual(len(hooks), 1)
            setup = {"owner": "a", "members": ["a"], "list": "l",
                     "task": {"id": "t", "list": "l", "state": "open", "assignee": "a"}}
            with self.assertRaises(mod.NotImplementedRule) as ctx:
                _setup(mod, setup).run("complete-task", "a", "t")
            self.assertIn(hooks[0]["id"], str(ctx.exception))
            rt = _setup(mod, setup)
            rt.hooks[hooks[0]["id"]] = lambda *_: None
            self.assertTrue(rt.run("complete-task", "a", "t").ok)

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            doc = _resolved()
            Path(tmp, "a").mkdir()
            Path(tmp, "b").mkdir()
            _, first = _load(doc, Path(tmp) / "a")
            _, second = _load(doc, Path(tmp) / "b")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.with_suffix(".report.json").read_bytes(),
                             second.with_suffix(".report.json").read_bytes())

    def test_contradictory_terminal_rule_is_refused(self):
        doc = _resolved()
        for obj in doc["objects"]:
            if obj.get("kind") == "workflow":
                obj["transitions"].append({"from": "shared-tasks.minimal/state/completed",
                                           "to": "shared-tasks.minimal/state/open"})
        with self.assertRaises(gen.GenerationError):
            gen.generate_source(SemanticModel(doc))

    def test_model_without_transitions_or_rules_is_refused(self):
        doc = _resolved()
        for obj in doc["objects"]:
            if obj.get("kind") == "workflow":
                obj["transitions"] = []
        with self.assertRaises(gen.GenerationError):
            gen.generate_source(SemanticModel(doc))
        doc = _resolved()
        doc["objects"] = [o for o in doc["objects"] if o.get("kind") != "rule"]
        with self.assertRaises(gen.GenerationError):
            gen.generate_source(SemanticModel(doc))

    def test_hostile_text_stays_inert(self):
        hostile = 'x"""\nINJECTED.append(1)\n"""@@IR@@ \u2028'
        doc = _resolved()
        for obj in doc["objects"]:
            if obj.get("kind") == "rule":
                obj["claims"] = obj["claims"] + [hostile]
            if obj.get("kind") == "module":
                obj["name"] = hostile
        doc["module"] = dict(doc.get("module", {}), id="m/" + hostile, name=hostile)
        source = gen.generate_source(SemanticModel(doc))
        ns = {"INJECTED": [], "__name__": "g"}
        exec(compile(source, "<g>", "exec"), ns)
        self.assertEqual(ns["INJECTED"], [])
        self.assertNotIn("\u2028", source)
        self.assertTrue(ns["UNIMPLEMENTED_RULES"])

    def test_original_minimal_model_also_generates(self):
        source = gen.generate_source(SemanticModel.from_json_file(MINIMAL))
        compile(source, "<g>", "exec")


if __name__ == "__main__":
    unittest.main()
