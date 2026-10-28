import json
import unittest
from pathlib import Path

from orin_parser import OrinParser, OrinSourceError

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "conformance" / "orin-source-errors.cases.json"


class SourceErrorFixtureTests(unittest.TestCase):
    def test_fixtures(self):
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
        self.assertTrue(cases)
        for case in cases:
            with self.subTest(case["id"]):
                with self.assertRaises(OrinSourceError) as ctx:
                    OrinParser().parse(case["source"])
                self.assertEqual(ctx.exception.code, case["expectedDiagnostic"])
                self.assertEqual(ctx.exception.line, case["line"])


if __name__ == "__main__":
    unittest.main()
