import unittest

from orin_parser import OrinParser, OrinSourceError
from orin_suggest import levenshtein, suggest


def parse_error(source):
    with unittest.TestCase().assertRaises(OrinSourceError) as ctx:
        OrinParser().parse(source)
    return ctx.exception


class SuggestTests(unittest.TestCase):
    def test_levenshtein(self):
        self.assertEqual(levenshtein("kitten", "sitting"), 3)
        self.assertEqual(levenshtein("", "abc"), 3)

    def test_suggest(self):
        self.assertEqual(suggest("entiti", ["entity", "rule"]), "entity")
        self.assertIsNone(suggest("zzzzzz", ["entity", "rule"]))

    def test_misspelled_keyword(self):
        error = parse_error("module m {\n  entitty U {\n  }\n}\n")
        self.assertEqual(error.code, "ORIN-P002")
        text = str(error)
        self.assertIn('Did you mean "entity"?', text)
        self.assertIn("Valid here:", text)
        self.assertIn("^", text)

    def test_misspelled_attribute(self):
        error = parse_error('module m {\n  entity U {\n    purpse "x"\n  }\n}\n')
        self.assertEqual(error.code, "ORIN-P005")
        self.assertIn('Did you mean "purpose"?', str(error))

    def test_context_and_policy(self):
        error = parse_error('module m {\n  context {\n    repositry "x"\n  }\n}\n')
        self.assertIn('Did you mean "repository"?', str(error))
        error = parse_error('module m {\n  policy implementation {\n    prefr "x"\n  }\n}\n')
        self.assertIn('Did you mean "prefer"?', str(error))

    def test_no_guess_when_far(self):
        error = parse_error("module m {\n  qqqqqqqq thing\n}\n")
        self.assertNotIn("Did you mean", str(error))
        self.assertIn("Valid here:", str(error))


if __name__ == "__main__":
    unittest.main()
