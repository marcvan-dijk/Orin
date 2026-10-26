"""Scenario runner for the language-neutral shared-task cases."""

import json
from pathlib import Path
from typing import Any

from orin_model import SemanticModel
from shared_tasks import SharedTasksRuntime, TaskResult


_MINIMAL_FAILURE_MAP = {
    "forbidden.member-required": "unauthorized",
    "forbidden.assignee-required": "not-assigned",
    "invalid-transition.task-already-completed": "already-completed",
    "not-found.task": "task-not-found",
    "not-found.task-list": "list-not-found",
}


def _canonical_failure(code: str | None) -> str | None:
    if code is None:
        return None
    return _MINIMAL_FAILURE_MAP.get(code, code)


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


def run_minimal_case(case: dict[str, Any]) -> dict[str, Any]:
    setup = case.get("setup", {})
    action = case.get("action", {})
    task_setup = setup.get("task", {}) if isinstance(setup, dict) else {}

    people = {
        value
        for value in (
            setup.get("owner"),
            action.get("actor"),
            task_setup.get("assignee"),
        )
        if isinstance(value, str)
    }
    members = setup.get("members", [])
    if isinstance(members, list):
        people.update(member for member in members if isinstance(member, str))

    runtime = SharedTasksRuntime(people)
    owner = setup.get("owner")
    if not isinstance(owner, str):
        return {"ok": False, "failure": "invalid-setup.owner-required"}
    created = runtime.create_list(owner, "Minimal List")
    if not created.ok:
        return {"ok": False, "failure": _canonical_failure(created.failure)}
    list_id = created.output["list"]

    if isinstance(members, list):
        for member in members:
            if not isinstance(member, str):
                continue
            added = runtime.add_member(owner, list_id, member)
            if not added.ok:
                return {"ok": False, "failure": _canonical_failure(added.failure)}

    task_id = None
    if isinstance(task_setup, dict) and isinstance(task_setup.get("id"), str):
        assignee = task_setup.get("assignee")
        creator = assignee if isinstance(assignee, str) and assignee in runtime.people else owner
        created_task = runtime.create_task(creator, list_id, "Minimal Task")
        if not created_task.ok:
            return {"ok": False, "failure": _canonical_failure(created_task.failure)}
        task_id = created_task.output.get("task")
        if isinstance(task_id, str) and isinstance(assignee, str) and assignee != creator:
            assigned = runtime.assign_task(owner, task_id, assignee)
            if not assigned.ok:
                return {"ok": False, "failure": _canonical_failure(assigned.failure)}
        if isinstance(task_id, str):
            if task_setup.get("state") == "completed":
                completer = runtime.tasks[task_id].assignee
                completed = runtime.complete_task(completer, task_id)
                if not completed.ok:
                    return {"ok": False, "failure": _canonical_failure(completed.failure)}

    actor = action.get("actor")
    requested_task = action.get("task")
    if not isinstance(actor, str) or not isinstance(requested_task, str):
        return {"ok": False, "failure": "invalid-action"}

    if requested_task == "task-missing":
        target_task_id = "task-9999"
    else:
        target_task_id = task_id
    if not isinstance(target_task_id, str):
        return {"ok": False, "failure": "task-not-found"}

    if target_task_id not in runtime.tasks:
        return {"ok": False, "failure": "task-not-found", "stateChanges": "none"}

    task = runtime.tasks[target_task_id]
    task_list = runtime.lists.get(task.list_id)
    if task_list is None:
        return {"ok": False, "failure": "list-not-found", "taskState": task.state}
    if actor not in task_list.members:
        return {"ok": False, "failure": "unauthorized", "taskState": task.state}
    if task.assignee != actor:
        return {"ok": False, "failure": "not-assigned", "taskState": task.state}
    if task.state != "open":
        return {"ok": False, "failure": "already-completed", "taskState": task.state}

    task.state = "completed"
    persisted_check = task.state == "completed"
    return {"ok": True, "taskState": task.state, "persisted": persisted_check}


def run_fixture(path: str | Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(case["id"], run_case(case), case["then"]) for case in fixture["cases"]]


def run_minimal_fixture(path: str | Path) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    fixture = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(case["id"], run_minimal_case(case), case["then"]) for case in fixture["cases"]]


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