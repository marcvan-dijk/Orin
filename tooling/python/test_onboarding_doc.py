"""Runs the commands in docs/ONBOARDING.md so the walkthrough cannot rot.

Run from anywhere: python tooling/python/test_onboarding_doc.py
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "ONBOARDING.md"
COPIED = ("tooling", "tests", "examples", "implementations")

# (command fragment, expected exit code, text expected in output)
EXPECTATIONS = [
    ("inspect examples/password-reset.orin", 2, ["Compilation: blocked", "Affected objects:",
                                                  "account.password-reset/uncertainty/rate-limit"]),
    ("--option five-per-15m", 4, ["Accepted decision: five-per-15m-per-address-and-origin",
                                  "Updated compilation: eligible"]),
    ("--option three-per-hour", 4, ["Accepted decision: three-per-hour-per-address"]),
    ("diff out/five.json", 1, ["5 attempts per 15 minutes", "3 attempts per hour"]),
    ("inspect out/three.json", 0, ["Ready: no blocking consequential decisions remain."]),
    ("password_reset_proof.py", 0, ['"blockedCompilation": "blocked"', '"resolvedCompilation": "eligible"',
                                    '"canonicalMeaningStableAcrossVariants": true']),
    ("test_orin_model.py", 0, ["OK"]),
    ("node --test", 0, ["pass 4", "fail 0"]),
]
SKIPPED_PREFIXES = ("git clone", "cd ", "mkdir")


def doc_commands():
    text = DOC.read_text(encoding="utf-8")
    commands = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        for command in re.sub(r"\\\n\s*", " ", block).splitlines():
            command = command.strip()
            if command:
                commands.append(command)
    return commands


class OnboardingDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        for name in COPIED:
            shutil.copytree(ROOT / name, self.work / name,
                            ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        (self.work / "out").mkdir()

    def run_command(self, command):
        return subprocess.run(command, shell=True, cwd=self.work, text=True,
                              capture_output=True, timeout=120)

    def test_every_documented_command_has_an_expectation(self):
        for command in doc_commands():
            if command.startswith(SKIPPED_PREFIXES):
                continue
            self.assertTrue(any(key in command for key, _, _ in EXPECTATIONS),
                            f"no expectation for documented command: {command}")

    def test_walkthrough_commands(self):
        ran = set()
        for command in doc_commands():
            if command.startswith(SKIPPED_PREFIXES):
                continue
            for key, code, needles in EXPECTATIONS:
                if key in command:
                    if key == "node --test" and not shutil.which("node"):
                        break
                    result = self.run_command(command)
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, code, f"{command}\n{output}")
                    for needle in needles:
                        self.assertIn(needle, output, command)
                    ran.add(key)
                    break
        self.assertGreaterEqual(len(ran), len(EXPECTATIONS) - 1)

    def test_defer_is_refused_without_writing_a_file(self):
        result = self.run_command(
            "python -m tooling.python.orin_agent decide tests/conformance/password-reset.model.json "
            "--uncertainty account.password-reset/uncertainty/rate-limit --option defer "
            "--write out/defer.json")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertFalse((self.work / "out" / "defer.json").exists())


if __name__ == "__main__":
    unittest.main()
