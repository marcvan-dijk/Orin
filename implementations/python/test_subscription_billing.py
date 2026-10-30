import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orin_parser import OrinParser, analyze

SOURCE = Path(__file__).resolve().parents[2] / "examples" / "subscription-billing.orin"


class SubscriptionBillingTest(unittest.TestCase):
    def test_only_blocking_uncertainties_are_diagnostics(self):
        codes = [d.code for d in analyze(SOURCE)]
        self.assertEqual(codes, ["ORIN-E041"] * 2)

    def test_readiness_blocks_only_on_open_decisions(self):
        report = OrinParser().parse_file(SOURCE).readiness_report().to_dict()
        self.assertEqual(report["status"], "blocked")
        blocking = [d for d in report["diagnostics"] if d["blocking"]]
        self.assertEqual({d["code"] for d in blocking}, {"ORIN-R201"})
        self.assertEqual(len(blocking), 2)

    def test_every_rule_example_link_exists(self):
        text = SOURCE.read_text(encoding="utf-8")
        examples = {line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("example:")}
        linked = set()
        for line in text.splitlines():
            if line.strip().startswith("proved-by:"):
                linked.update(n.strip() for n in line.split(":", 1)[1].split(","))
        self.assertTrue(linked)
        self.assertLessEqual(linked, examples)


if __name__ == "__main__":
    unittest.main()
