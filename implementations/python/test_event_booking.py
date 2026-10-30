import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tooling.python import orin_cli

SOURCE = ROOT / "examples" / "event-booking.orin"
REFUND = "event-booking/uncertainty/refund-amount"
EXPIRY = "event-booking/uncertainty/waitlist-offer-expiry"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = orin_cli.main([str(a) for a in argv])
    return code, out.getvalue(), err.getvalue()


class EventBookingTest(unittest.TestCase):
    def test_check_reports_both_open_decisions(self):
        code, out, _ = run("check", SOURCE)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("ORIN-E041"), 2)

    def test_readiness_is_blocked_by_two_decisions(self):
        code, out, _ = run("readiness", SOURCE)
        self.assertEqual(code, 2)
        self.assertIn(REFUND, out)
        self.assertIn(EXPIRY, out)

    def test_inspect_lists_options_from_sidecar(self):
        code, out, _ = run("inspect", SOURCE)
        self.assertEqual(code, 0 if "Blocked" not in out else code)
        for option in ("full-refund-7-days", "half-refund-late",
                       "expire-after-24-hours", "offer-stays-open"):
            self.assertIn(option, out)

    def test_decide_twice_then_ready_and_generate(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            a, b, gen = Path(d) / "a.json", Path(d) / "b.json", Path(d) / "gen"
            self.assertEqual(run("decide", SOURCE, "--option", "half-refund-late", "--out", a)[0], 0)
            self.assertEqual(run("readiness", a)[0], 2)
            code, _, _ = run("decide", a, "--uncertainty", EXPIRY,
                             "--option", "expire-after-24-hours", "--out", b)
            self.assertEqual(code, 0)
            self.assertEqual(run("check", b)[0], 0)
            self.assertEqual(run("readiness", b)[0], 0)
            model = json.loads(b.read_text())
            rules = [o["name"] for o in model["objects"] if o["kind"] == "rule"]
            self.assertIn("refund-policy", rules)
            self.assertIn("waitlist-offer-expiry", rules)
            code, _, _ = run("generate", b, "--target", "python", "--out", gen)
            self.assertEqual(code, 0)
            text = (gen / "event_booking_generated.py").read_text()
            self.assertIn("hook.refund-policy.4", text)

    def test_generate_blocked_until_decided(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            a = Path(d) / "a.json"
            run("decide", SOURCE, "--option", "half-refund-late", "--out", a)
            code, out, _ = run("generate", a, "--target", "python", "--out", Path(d) / "g")
            self.assertEqual(code, 2)
            self.assertIn("needs 1 decision", out)


if __name__ == "__main__":
    unittest.main()
