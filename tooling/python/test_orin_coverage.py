import contextlib
import io
import json
from pathlib import Path
import unittest

from tooling.python import orin_cli

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orin_cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def report(name):
    code, out, _ = run("coverage", str(EXAMPLES / name), "--json")
    assert code == 0, code
    return json.loads(out)


class CoverageTests(unittest.TestCase):
    def test_all_examples_run_both_formats(self):
        files = sorted(EXAMPLES.glob("*.orin"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path.name):
                code, out, _ = run("coverage", str(path))
                self.assertEqual(code, 0)
                self.assertIn("Rules proved by an example:", out)
                data = report(path.name)
                for key in ("rules", "unprovedRules", "orphanExamples",
                            "workflowsWithoutFailureExample",
                            "unusedCapabilities", "unusedStates"):
                    self.assertIn(key, data)

    def test_strict_exit_matches_unproved_rules(self):
        for path in sorted(EXAMPLES.glob("*.orin")):
            with self.subTest(path.name):
                expected = 1 if report(path.name)["unprovedRules"] else 0
                self.assertEqual(run("coverage", str(path), "--strict")[0], expected)
                self.assertEqual(run("coverage", str(path))[0], 0)

    def test_library_lending_fully_proved(self):
        data = report("library-lending.orin")
        self.assertEqual(data["unprovedRules"], [])
        self.assertEqual(data["orphanExamples"], [])
        self.assertEqual(data["workflowsWithoutFailureExample"], [])

    def test_shared_tasks_links_through_example_requires(self):
        data = report("shared-tasks.minimal.orin")
        self.assertEqual([_.rsplit("/", 1)[-1] for _ in data["unprovedRules"]],
                         ["relationship-constraints"])
        self.assertEqual([_.rsplit("/", 1)[-1] for _ in data["orphanExamples"]],
                         ["missing-entity-task-not-found"])

    def test_password_reset_unused_items(self):
        data = report("password-reset.orin")
        self.assertEqual(len(data["unusedStates"]), 3)
        self.assertEqual(len(data["unusedCapabilities"]), 1)
        self.assertEqual(len(data["unprovedRules"]), 2)

    def test_subscription_billing_failure_gaps(self):
        gaps = report("subscription-billing.orin")["workflowsWithoutFailureExample"]
        self.assertEqual(len(gaps), 2)

    def test_text_output_uses_plain_hints(self):
        _, out, _ = run("coverage", str(EXAMPLES / "password-reset.orin"))
        self.assertIn("Rules with no example (2):", out)
        self.assertIn("Add an example that shows each rule", out)


if __name__ == "__main__":
    unittest.main()
