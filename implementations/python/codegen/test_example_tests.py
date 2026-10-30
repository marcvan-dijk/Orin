import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "tests" / "conformance" / "password-reset.model.json"
PYTHON_DIR = ROOT / "implementations" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from orin_model import SemanticModel  # noqa: E402
from password_reset import AccountStore, EmailProvider, PasswordResetRuntime  # noqa: E402
from codegen import example_tests  # noqa: E402

CAPABILITIES = {"person.request-password-reset", "system.send-reset-message"}


def reference_observe(name):
    """Adapter for the reference implementation: maps example names to outcomes."""
    exists = name == "registered-address"
    runtime = PasswordResetRuntime(AccountStore({"person@example.com"} if exists else set()), EmailProvider())
    result = runtime.request_reset("person@example.com", CAPABILITIES)
    return [result.response, "reset-message-sent" if result.reset_message == "sent" else "reset-message-not-sent"]


def wrong_observe(name):
    return ["standard-confirmation"]


class ExampleTestsTest(unittest.TestCase):
    def run_generated(self, adapter):
        with tempfile.TemporaryDirectory(dir=ROOT) as out:
            path = example_tests.write_tests(SemanticModel.from_json_file(MODEL), Path(out))
            env = dict(os.environ, ORIN_ADAPTER=adapter,
                       PYTHONPATH=os.pathsep.join([str(ROOT), str(PYTHON_DIR)]))
            return subprocess.run([sys.executable, str(path)], env=env, capture_output=True, text=True)

    def test_reference_implementation_passes(self):
        result = self.run_generated("implementations.python.codegen.test_example_tests:reference_observe")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 2 tests", result.stderr)

    def test_wrong_implementation_fails(self):
        result = self.run_generated("implementations.python.codegen.test_example_tests:wrong_observe")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reset-message-sent", result.stderr)

    def test_skipped_without_adapter(self):
        result = self.run_generated("")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped", result.stderr)

    def test_model_without_examples_is_rejected(self):
        with self.assertRaises(example_tests.ExampleTestsError):
            example_tests.generate_tests_source(SemanticModel({"module": {"id": "x"}, "objects": []}))

    def test_cli_emit_tests(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as out:
            result = subprocess.run(
                [sys.executable, "-m", "tooling.python.orin_cli", "generate", str(MODEL),
                 "--target", "python", "--emit", "tests", "--out", out],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(list(Path(out).glob("*_example_tests.py")))


if __name__ == "__main__":
    unittest.main()
