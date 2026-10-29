"""The shared-tasks.minimal outline source must load to the same meaning as its JSON model."""

import json
import unittest
from pathlib import Path

from orin_parser import OrinParser

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "examples" / "shared-tasks.minimal.orin"
MODEL = ROOT / "tests" / "conformance" / "shared-tasks.minimal.model.json"


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k != "source"}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


class SharedTasksSourceEquivalenceTests(unittest.TestCase):
    def test_source_matches_json_model_plus_open_question(self):
        loaded = _strip(OrinParser().parse_file(SOURCE).document)
        expected = _strip(json.loads(MODEL.read_text(encoding="utf-8")))

        uncertainties = [o for o in loaded["objects"] if o["kind"] == "uncertainty"]
        self.assertEqual([u["name"] for u in uncertainties], ["non-member-completion"])
        loaded["objects"] = [o for o in loaded["objects"] if o["kind"] not in ("uncertainty", "evidence")]

        def by_id(doc):
            return {o["id"]: o for o in doc["objects"]}

        self.assertEqual(loaded["module"], expected["module"])
        self.assertEqual(by_id(loaded), by_id(expected))


if __name__ == "__main__":
    unittest.main()
