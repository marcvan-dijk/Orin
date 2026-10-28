import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from orin_proposal import (Change, Proposal, Review, apply, diff, load_decisions, load_model,
                           proposal_from_decision_option, save_decisions)

try:
    from implementations.python.orin_agent_core import NON_MEMBER_PROMPT
except ImportError:  # run from implementations/python
    from python.orin_agent_core import NON_MEMBER_PROMPT

FIXTURE = Path(__file__).parents[2] / "tests" / "conformance" / "shared-tasks.minimal.model.json"
RULE = "shared-tasks.minimal/rule/completion-is-terminal"


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model(FIXTURE)
        self.before = copy.deepcopy(self.model)
        rule = copy.deepcopy(next(o for o in self.model["objects"] if o["id"] == RULE))
        rule["name"] = "completion-is-final"
        self.proposal = Proposal([Change("replace", RULE, rule)], "clearer wording")

    def test_diff_shows_exact_change(self):
        self.assertEqual(
            diff(self.model, self.proposal),
            [f'~ {RULE}.name: "completion-is-terminal" -> "completion-is-final"'],
        )

    def test_accept_applies_and_records_decision_with_rationale(self):
        review = Review(self.model, self.proposal)
        new = review.accept("wording matches glossary")
        self.assertEqual(self.model, self.before)
        self.assertEqual(next(o for o in new["objects"] if o["id"] == RULE)["name"], "completion-is-final")
        d = review.decisions[0]
        self.assertEqual((d["outcome"], d["rationale"], d["subjects"]), ("accepted", "wording matches glossary", [RULE]))
        self.assertNotIn("timestamp", d)

    def test_reject_leaves_model_and_records_rationale(self):
        review = Review(self.model, self.proposal)
        self.assertEqual(review.reject("terminal is the established term"), self.before)
        self.assertEqual(review.decisions[0]["outcome"], "rejected")

    def test_decision_requires_rationale(self):
        with self.assertRaises(ValueError):
            Review(self.model, self.proposal).accept("")

    def test_explain_records_no_decision(self):
        review = Review(self.model, self.proposal)
        review.explain("why?", "readability")
        self.assertEqual(review.decisions, [])
        self.assertEqual(len(self.proposal.explanations), 1)

    def test_counter_edit_is_new_undecided_proposal(self):
        review = Review(self.model, self.proposal)
        second = review.counter([Change("remove", RULE)], "drop it instead")
        self.assertEqual(review.decisions, [])
        self.assertTrue(diff(self.model, second.proposal)[0].startswith("- "))
        self.assertEqual(len(apply(self.model, second.proposal)["objects"]), len(self.model["objects"]) - 1)

    def test_invalid_changes_rejected(self):
        with self.assertRaises(ValueError):
            apply(self.model, Proposal([Change("remove", "nope")], "x"))
        with self.assertRaises(ValueError):
            apply(self.model, Proposal([Change("add", RULE, {"id": RULE})], "x"))


class DecisionOptionTests(unittest.TestCase):
    def setUp(self):
        self.model = load_model(FIXTURE)
        self.before = copy.deepcopy(self.model)
        self.prompt = NON_MEMBER_PROMPT
        self.option = self.prompt.option("assignee-may-complete")
        self.proposal = proposal_from_decision_option(self.model, self.prompt, self.option)

    def test_accept_applies_option_and_records_decision(self):
        review = Review(self.model, self.proposal)
        new = review.accept("assigned work must finish")
        self.assertEqual(self.model, self.before)
        ids = {o["id"]: o for o in new["objects"]}
        rule = ids[self.prompt.rule_id]
        self.assertEqual(rule["claims"], list(self.option.rule_claims))
        self.assertIn(self.option.examples[0]["id"], ids)
        d = review.decisions[0]
        self.assertEqual(d["outcome"], "accepted")
        self.assertEqual(d["subjects"], [self.prompt.rule_id, self.option.examples[0]["id"]])
        self.assertEqual(set(d), {"outcome", "subjects", "change", "rationale"})

    def test_reject_keeps_model_and_uncertainty_open(self):
        model = copy.deepcopy(self.model)
        model["objects"].append({"id": self.prompt.uncertainty_id, "kind": "uncertainty", "status": "unresolved"})
        proposal = proposal_from_decision_option(model, self.prompt, self.option)
        review = Review(model, proposal)
        self.assertEqual(review.reject("not ready"), model)
        self.assertEqual(review.decisions[0]["outcome"], "rejected")
        accepted = Review(model, proposal).accept("ok")
        status = next(o for o in accepted["objects"] if o["id"] == self.prompt.uncertainty_id)["status"]
        self.assertEqual(status, "accepted")

    def test_blocked_option_cannot_be_proposed(self):
        with self.assertRaises(ValueError):
            proposal_from_decision_option(self.model, self.prompt, self.prompt.option("defer"))

    def test_decisions_round_trip_as_plain_json_list(self):
        review = Review(self.model, self.proposal)
        review.accept("because")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "decisions.json"
            self.assertEqual(load_decisions(path), [])
            save_decisions(path, review.decisions)
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), list)
            self.assertEqual(load_decisions(path), review.decisions)


if __name__ == "__main__":
    unittest.main()
