"""Deterministic reference runtime for the shared task-list application."""

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class Person:
    id: str


@dataclass
class TaskList:
    id: str
    owner: str
    name: str
    members: set[str] = field(default_factory=set)


@dataclass
class Task:
    id: str
    list_id: str
    title: str
    assignee: str
    state: Literal["open", "in-progress", "completed"] = "open"


@dataclass(frozen=True)
class TaskResult:
    ok: bool
    output: dict[str, Any] = field(default_factory=dict)
    failure: str | None = None
    state_changes: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()


class SharedTasksRuntime:
    """Execute shared-task workflows against one deterministic persistent store."""

    def __init__(self, people: set[str] | None = None):
        self.people = {person_id: Person(person_id) for person_id in (people or set())}
        self.lists: dict[str, TaskList] = {}
        self.tasks: dict[str, Task] = {}
        self._next_list_id = 1
        self._next_task_id = 1

    def create_list(self, actor: str, name: str) -> TaskResult:
        if not self._known_person(actor):
            return self._failure("not-found.person")
        if not name.strip():
            return self._failure("validation.list-name")
        list_id = f"list-{self._next_list_id}"
        self._next_list_id += 1
        self.lists[list_id] = TaskList(list_id, actor, name, {actor})
        return TaskResult(True, {"list": list_id, "owner": actor, "name": name}, state_changes=("created",), effects=("store.write.task-list",))

    def add_member(self, actor: str, list_id: str, member: str) -> TaskResult:
        task_list = self.lists.get(list_id)
        if not self._known_person(actor):
            return self._failure("not-found.person")
        if task_list is None:
            return self._failure("not-found.task-list")
        if not self._known_person(member):
            return self._failure("not-found.person")
        if task_list.owner != actor:
            return self._failure("forbidden.owner-required")
        task_list.members.add(member)
        return TaskResult(True, {"list": list_id, "member": member}, state_changes=("member-added",), effects=("store.write.member-of",))

    def create_task(self, actor: str, list_id: str, title: str) -> TaskResult:
        task_list = self.lists.get(list_id)
        if not self._known_person(actor):
            return self._failure("not-found.person")
        if task_list is None:
            return self._failure("not-found.task-list")
        if actor not in task_list.members:
            return self._failure("forbidden.member-required")
        if not title.strip():
            return self._failure("validation.task-title")
        task_id = f"task-{self._next_task_id}"
        self._next_task_id += 1
        self.tasks[task_id] = Task(task_id, list_id, title, actor)
        return TaskResult(True, {"task": task_id, "state": "open", "assignee": actor}, state_changes=("task-created",), effects=("store.write.task",))

    def assign_task(self, actor: str, task_id: str, member: str) -> TaskResult:
        task = self.tasks.get(task_id)
        if task is None:
            return self._failure("not-found.task")
        task_list = self.lists[task.list_id]
        if actor not in task_list.members:
            return self._failure("forbidden.member-required")
        if member not in task_list.members:
            return self._failure("validation.assignee-must-be-member")
        task.assignee = member
        return TaskResult(True, {"task": task_id, "assignee": member}, state_changes=("task-assigned",), effects=("store.write.assigned-to",))

    def complete_task(self, actor: str, task_id: str) -> TaskResult:
        task = self.tasks.get(task_id)
        if task is None:
            return self._failure("not-found.task")
        if task.assignee != actor:
            return self._failure("forbidden.assignee-required")
        if task.state != "open":
            return self._failure("invalid-transition.task-already-completed")
        task.state = "completed"
        return TaskResult(True, {"task": task_id, "state": "completed"}, state_changes=("open->completed",), effects=("store.write.task-state",))

    def list_tasks(self, actor: str, list_id: str) -> TaskResult:
        task_list = self.lists.get(list_id)
        if task_list is None:
            return self._failure("not-found.task-list")
        if actor not in task_list.members:
            return self._failure("forbidden.member-required")
        items = [{"task": task.id, "title": task.title, "state": task.state, "assignee": task.assignee} for task in self.tasks.values() if task.list_id == list_id]
        return TaskResult(True, {"tasks": items}, effects=("store.read.task-list", "store.read.task"))

    def complete_tasks_concurrently(self, actor_ids: list[str], task_id: str) -> tuple[TaskResult, ...]:
        """Apply simultaneous requests in deterministic input order."""
        return tuple(self.complete_task(actor, task_id) for actor in actor_ids)

    def _known_person(self, person_id: str) -> bool:
        return person_id in self.people

    @staticmethod
    def _failure(code: str) -> TaskResult:
        return TaskResult(False, failure=code)