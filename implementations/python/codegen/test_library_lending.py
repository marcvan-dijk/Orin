import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementations.python.codegen import generate as gen  # noqa: E402

CONF = ROOT / "tests" / "conformance"
DECIDED = CONF / "library-lending.decided.json"
SOURCE = ROOT / "examples" / "library-lending.orin"
DAY = 86400


def _generate(model, out, decisions=None):
    target = gen.generate(model, out, decisions)
    spec = importlib.util.spec_from_file_location("library_lending_generated", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, target


def _cid(mod, kind, rule):
    return next(c["id"] for c in mod.IR["constraints"] if c["kind"] == kind and c["rule"] == rule)


class LibraryLendingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.mod, cls.target = _generate(DECIDED, Path(cls.tmp.name) / "out")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def runtime(self):
        rate = next(p for p in self.mod.IR["parameters"] if p.endswith(".rate"))
        return self.mod.Runtime(params={rate: 2, "price-of-the-book": 5, "fee-limit": 10, "unpaid-fees": 0})

    def test_report_has_no_hooks_but_lists_parameters_and_open_question(self):
        report = json.loads(self.target.with_suffix(".report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["unimplementedRules"], [])
        self.assertEqual(report["openQuestions"], ["lost-book-fee"])
        self.assertIn("fee-limit", report["requiredParameters"])
        self.assertEqual(len(report["derivedRules"]), 9)

    def test_on_time_loan(self):
        rt = self.runtime()
        self.assertEqual(rt.threshold_failure(_cid(self.mod, "threshold-block", "a-member-with-unpaid-fees"), 0), None)
        self.assertIsNone(rt.acquire(_cid(self.mod, "exclusive-holder", "a-copy-is-on-loan"), "copy-1", "ann"))
        self.assertEqual(rt.deadline(_cid(self.mod, "deadline", "a-loan-has-a-due"), 0), 14 * DAY)
        self.assertEqual(rt.acquire(_cid(self.mod, "exclusive-holder", "a-copy-is-on-loan"), "copy-1", "bob"),
                         "already-held")

    def test_late_return_fee_is_per_day_and_capped(self):
        rt = self.runtime()
        due = rt.deadline(_cid(self.mod, "deadline", "a-loan-has-a-due"), 0)
        fee = _cid(self.mod, "accrual", "a-late-fee-accrues-for")
        units = rt.units_overdue(fee, due, due + 3 * DAY)
        self.assertEqual((units, rt.accrued(fee, units)), (3, 5))
        self.assertEqual(rt.accrued(fee, 2), 4)
        self.assertEqual(rt.accrued(fee, 40), 5)
        once = _cid(self.mod, "once-only", "a-returned-loan-cannot-be")
        self.assertIsNone(rt.once(once, "loan-1"))
        self.assertEqual(rt.once(once, "loan-1"), "already-returned")

    def test_fee_block(self):
        rt = self.runtime()
        block = _cid(self.mod, "threshold-block", "a-member-with-unpaid-fees")
        self.assertEqual(rt.threshold_failure(block, 11), "refused-borrow")
        self.assertIsNone(rt.threshold_failure(block, 10))

    def test_reserved_return_and_hold_expiry(self):
        rt = self.runtime()
        rt.enqueue("book-1", "cy")
        rt.enqueue("book-1", "di")
        offer = _cid(self.mod, "queue-offer", "a-reservation-is-held-for")
        self.assertEqual(rt.offer_first(offer, "book-1", 100), "cy")
        expiry = _cid(self.mod, "deadline", "hold-expiry")
        self.assertFalse(rt.is_expired(expiry, 100, 100 + 3 * DAY))
        self.assertTrue(rt.is_expired(expiry, 100, 101 + 3 * DAY))
        self.assertEqual(rt.pass_on(_cid(self.mod, "queue-pass", "hold-expiry"), "book-1", 200 + 3 * DAY), "di")

    def test_renewal_refused_while_reserved(self):
        rt = self.runtime()
        cid = _cid(self.mod, "blocked-while", "renewal-with-reservation")
        self.assertEqual(rt.blocked_failure(cid, True), "refused-renewed")
        self.assertIsNone(rt.blocked_failure(cid, False))

    def test_missing_parameter_is_loud(self):
        with self.assertRaises(self.mod.MissingParameter):
            self.mod.Runtime().threshold_failure(_cid(self.mod, "threshold-block", "a-member-with-unpaid-fees"), 1)

    def test_orin_source_with_decisions_matches_model_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            with self.assertRaises(gen.GenerationError):
                gen.generate(SOURCE, out)
            target = gen.generate(SOURCE, out, ["reservation-hold-expiry=expire-after-3-days",
                                                "renewal-with-reservation=refuse-renewal"])
            self.assertEqual(target.read_bytes(), self.target.read_bytes())
            self.assertEqual([p.name for p in out.iterdir() if p.name.startswith(".")], [])

    def test_unmatched_claim_becomes_hook(self):
        doc = json.loads(DECIDED.read_text(encoding="utf-8"))
        doc["objects"].append({"id": "library-lending/rule/odd", "kind": "rule", "name": "odd",
                               "status": "accepted", "claims": ["Staff are friendly."]})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            mod, target = _generate(path, Path(tmp) / "out")
            report = json.loads(target.with_suffix(".report.json").read_text(encoding="utf-8"))
            self.assertEqual([h["claim"] for h in report["unimplementedRules"]], ["Staff are friendly."])
            with self.assertRaises(mod.NotImplementedRule):
                mod.Runtime().check_model_rules()

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            again = gen.generate(DECIDED, Path(tmp))
            self.assertEqual(again.read_bytes(), self.target.read_bytes())


if __name__ == "__main__":
    unittest.main()
