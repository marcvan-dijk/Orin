import unittest
from pathlib import Path

from shared_tasks import SharedTasksRuntime
from shared_tasks_conformance import run_fixture


class SharedTasksRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SharedTasksRuntime({"alice", "bob", "eve"})
        self.list_id = self.runtime.create_list("alice", "Project").output["list"]
        self.runtime.add_member("alice", self.list_id, "bob")

    def test_persistence_relationships_and_member_workflow(self):
        created = self.runtime.create_task("bob", self.list_id, "Write tests")
        listed = self.runtime.list_tasks("bob", self.list_id)

        self.assertTrue(created.ok)
        self.assertEqual(listed.output["tasks"][0]["title"], "Write tests")

    def test_outsider_cannot_view_or_change_membership(self):
        self.assertEqual(self.runtime.list_tasks("eve", self.list_id).failure, "forbidden.member-required")
        self.assertEqual(self.runtime.add_member("eve", self.list_id, "eve").failure, "forbidden.owner-required")

    def test_assignment_and_assignee_completion_transition(self):
        task_id = self.runtime.create_task("bob", self.list_id, "Ship feature").output["task"]
        self.assertTrue(self.runtime.assign_task("alice", task_id, "bob").ok)
        completed = self.runtime.complete_task("bob", task_id)

        self.assertTrue(completed.ok)
        self.assertEqual(completed.output["state"], "completed")
        self.assertEqual(completed.state_changes, ("open->completed",))

    def test_non_assignee_and_invalid_title_are_rejected_without_mutation(self):
        self.assertEqual(self.runtime.create_task("bob", self.list_id, "").failure, "validation.task-title")
        task_id = self.runtime.create_task("bob", self.list_id, "Private").output["task"]

        self.assertEqual(self.runtime.complete_task("alice", task_id).failure, "forbidden.assignee-required")
        self.assertEqual(self.runtime.tasks[task_id].state, "open")

    def test_completed_task_is_terminal_and_concurrent_winner_is_deterministic(self):
        task_id = self.runtime.create_task("bob", self.list_id, "One time").output["task"]
        results = self.runtime.complete_tasks_concurrently(["bob", "bob"], task_id)

        self.assertEqual([result.ok for result in results], [True, False])
        self.assertEqual(results[1].failure, "invalid-transition.task-already-completed")
        self.assertEqual(self.runtime.tasks[task_id].state, "completed")

    def test_missing_entities_are_defined_failures(self):
        self.assertEqual(self.runtime.list_tasks("alice", "missing").failure, "not-found.task-list")
        self.assertEqual(self.runtime.create_task("missing", self.list_id, "Task").failure, "not-found.person")


class SharedTasksConformanceTests(unittest.TestCase):
    def test_language_neutral_scenarios_drive_runtime(self):
        fixture = Path(__file__).parents[2] / "tests" / "conformance" / "shared-tasks.cases.json"

        for case_id, actual, expected in run_fixture(fixture):
            with self.subTest(case=case_id):
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()