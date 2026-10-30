import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tooling.python import orin_agent, orin_cli

ROOT = Path(__file__).resolve().parents[2]
SOURCE = str(ROOT / "examples" / "password-reset.orin")
NO_OPTIONS = str(ROOT / "examples" / "shared-tasks.minimal.orin")
OPTION = "three-per-hour-per-address"


def call(main, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class DecideParityTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.out = str(Path(self.dir.name) / "decided.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_agent_accepts_cli_flags(self):
        for flags in (["--option", OPTION, "--out", self.out],
                      ["--decide", OPTION, "--write", self.out],
                      [f"--decide={OPTION}", f"--out={self.out}"]):
            code, _, _ = call(orin_agent.main, "decide", SOURCE, *flags)
            self.assertEqual(code, 4)
            self.assertTrue(Path(self.out).is_file())
            Path(self.out).unlink()

    def test_agent_old_flags_and_short_uncertainty(self):
        code, _, _ = call(orin_agent.main, "decide", SOURCE, "--uncertainty", "rate-limit",
                          "--option", OPTION, "--write", self.out)
        self.assertEqual(code, 4)

    def test_agent_friendly_gives_zero(self):
        code, _, _ = call(orin_agent.main, "decide", SOURCE, "--option", OPTION,
                          "--out", self.out, "--friendly")
        self.assertEqual(code, 0)

    def test_agent_invalid_option_is_exit_3(self):
        code, _, err = call(orin_agent.main, "decide", SOURCE, "--option", "nope", "--out", self.out)
        self.assertEqual(code, 3)
        self.assertIn("invalid input", err)

    def test_cli_accepts_agent_flags(self):
        code, _, _ = call(orin_cli.main, "decide", SOURCE, "--decide", OPTION, "--write", self.out)
        self.assertEqual(code, 0)
        self.assertTrue(Path(self.out).is_file())

    def test_cli_invalid_option_is_exit_3(self):
        code, _, _ = call(orin_cli.main, "decide", SOURCE, "--option", "nope", "--out", self.out)
        self.assertEqual(code, 3)

    def test_hint_mentions_option_blocks_not_options_key(self):
        _, out, _ = call(orin_agent.main, "inspect", NO_OPTIONS)
        self.assertIn("`option: <id>` blocks", out)
        self.assertNotIn("inline `options:`", out)


if __name__ == "__main__":
    unittest.main()
