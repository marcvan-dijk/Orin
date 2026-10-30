import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tooling.python import orin_cli, orin_diff

C = Path(__file__).resolve().parents[2] / "tests" / "conformance"
OLD = str(C / "expense-approval.model.json")
NEW = str(C / "expense-approval.resolved.model.json")


def run(*argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = orin_cli.main(list(argv))
    return code, out.getvalue()


class DiffTests(unittest.TestCase):
    def test_resolved_vs_unresolved(self):
        code, out = run("diff", OLD, NEW, "--json")
        self.assertEqual(code, 0)
        details = {c["detail"] for c in json.loads(out)["changes"]}
        self.assertIn("Rule added: uncovered-expense-is-held", details)
        self.assertIn("Example added: no-eligible-approver", details)
        self.assertIn("Uncertainty closed (resolved): no-eligible-approver", details)

    def test_text_and_reverse(self):
        _, out = run("diff", OLD, NEW)
        self.assertIn("Uncertainty closed", out)
        _, out = run("diff", NEW, OLD)
        self.assertIn("Rule removed: uncovered-expense-is-held", out)
        self.assertIn("Uncertainty re-opened", out)

    def test_same_file_and_order_ignored(self):
        _, out = run("diff", OLD, OLD)
        self.assertEqual(out.strip(), "No change in meaning.")
        doc = json.loads(Path(OLD).read_text())
        doc["objects"].reverse()
        for o in doc["objects"]:
            for k in ("claims", "expects"):
                if k in o:
                    o[k].reverse()
        from implementations.python.orin_model import SemanticModel
        base = SemanticModel.from_json_file(OLD).canonical()
        self.assertFalse(orin_diff.diff_models(base, SemanticModel(doc).canonical())["changed"])

    def test_changed_claim(self):
        a = {"module": {"id": "m/module"}, "objects": [{"id": "m/rule/r", "claims": ["A"]}]}
        b = {"module": {"id": "m/module"}, "objects": [{"id": "m/rule/r", "claims": ["B"]}]}
        r = orin_diff.diff_models(a, b)
        self.assertEqual(r["changes"][0]["detail"], "Rule changed: r")


if __name__ == "__main__":
    unittest.main()
