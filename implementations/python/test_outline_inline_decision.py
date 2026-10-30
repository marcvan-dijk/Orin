import tempfile
import unittest
from pathlib import Path

from implementations.python import orin_agent_core as core
from implementations.python.orin_parser import OrinParser

SOURCE = """module: shop.cart

purpose: A cart.

rules:
  - A cart holds items.

workflow: checkout
  input:
    cart

uncertainty: empty-cart
  blocking: yes
  question:
    May an empty cart be checked out?
  why: It changes what checkout means.
  affects: checkout, A cart holds items
  option: Refuse an empty cart.
  option: Allow an empty cart.
    explanation: Gift orders may be empty.
"""


class InlineDecisionTests(unittest.TestCase):
    def parse(self, text=SOURCE):
        return OrinParser().parse_outline(text)

    def uncertainty(self, model):
        return next(o for o in model.document["objects"] if o["kind"] == "uncertainty")

    def test_inline_fields_are_parsed(self):
        u = self.uncertainty(self.parse())
        self.assertEqual(u["why_it_matters"], "It changes what checkout means.")
        self.assertEqual(u["affected_objects"][0], "shop.cart/workflow/checkout")
        self.assertEqual([o["label"] for o in u["options"]],
                         ["Refuse an empty cart.", "Allow an empty cart."])
        self.assertEqual(u["options"][1]["explanation"], "Gift orders may be empty.")

    def test_plain_uncertainty_unchanged(self):
        u = self.uncertainty(self.parse(SOURCE.split("  why:")[0]))
        self.assertNotIn("options", u)
        self.assertNotIn("why_it_matters", u)

    def test_agent_inspect_shows_inline_decision(self):
        with tempfile.TemporaryDirectory(dir=".") as folder:
            path = Path(folder) / "cart.orin"
            path.write_text(SOURCE, encoding="utf-8")
            result = core.OrinDecisionAgent().inspect(path)
            text = core._format_inspection(result)
        prompt = result.decisions[0].prompt
        self.assertEqual(len(prompt.options), 2)
        self.assertIn("It changes what checkout means.", text)
        self.assertIn("Refuse an empty cart.", text)


if __name__ == "__main__":
    unittest.main()
