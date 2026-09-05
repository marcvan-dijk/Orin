"""Scenario runner for the language-neutral shared-task cases."""

import json
from pathlib import Path
from typing import Any

from orin_model import SemanticModel
from shared_tasks import SharedTasksRuntime, TaskResult


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    runtime = SharedTasksRuntime({"alice", "bob", "eve"})
    list_id: str | None = None
    task_id: str | None = None
    last: TaskResult | None = None
    for step in case["steps"]:
        action = step["action"]
        if action == "create-list":
            last = runtime.create_list(step["actor"], step["name"])
            list_id = last.output.get("list")
        elif action == "add-member":
            last = runtime.add_member(step["actor"], list_id, step["member"])
        elif action == "create-task":
            last = runtime.create_task(step["actor"], list_id, step["title"])
            task_id = last.output.get("task") or task_id
        elif action == "list-tasks":
            last = runtime.list_tasks(step["actor"], list_id)
        elif action == "complete-concurrently":
            results = runtime.complete_tasks_concurrently(step["actors"], task_id)
            return {"results": [result.ok for result in results], "finalState": runtime.tasks[task_id].state}
        else:
            raise ValueError(f"unsupported shared-task action: {action}")
        if last is not None and not last.ok:
            result = {"failure": last.failure}
            if action == "create-task":
                result["taskCount"] = len(runtime.tasks)
            return result
    output: dict[str, Any] = {"ok": last.ok if last else False}
    if task_id is not None:
        output["taskState"] = runtime.tasks[task_id].state
        output["taskTitle"] = runtime.tasks[task_id].title
    return output


def run_fixture(path: str | Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(case["id"], run_case(case), case["then"]) for case in fixture["cases"]]


def run_validation_fixture(path: str | Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    fixture_path = Path(path)
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    results: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for case in fixture["cases"]:
        model = SemanticModel.from_json_file(fixture_path.parent / case["model"])
        diagnostics = model.diagnostics()
        actual = {
            "compilation": model.compilation_status(),
            "diagnostics": sorted(diagnostic.code for diagnostic in diagnostics),
            "diagnosticEntries": [
                {
                    "code": diagnostic.code,
                    "objectId": diagnostic.object_id,
                    "message": diagnostic.message,
                }
                for diagnostic in diagnostics
            ],
        }
        results.append((case["id"], actual, case["then"]))
    return results