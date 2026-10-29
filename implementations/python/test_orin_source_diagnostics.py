import tempfile
import unittest
from pathlib import Path

from orin_parser import OrinParser, OrinSourceError, analyze


def parse_error(text):
    with unittest.TestCase().assertRaises(OrinSourceError) as ctx:
        OrinParser().parse(text)
    return ctx.exception


class SourceDiagnosticsTests(unittest.TestCase):
    def test_missing_module(self):
        error = parse_error('purpose "x"\n')
        self.assertEqual((error.code, error.line, error.column), ("ORIN-P001", 1, 1))
        self.assertIn("module", error.hint)

    def test_unsupported_syntax_reports_line_and_column(self):
        error = parse_error('module m {\n  purpose "x"\n  bogus thing\n}\n')
        self.assertEqual((error.code, error.line, error.column), ("ORIN-P002", 3, 3))
        self.assertIn("bogus thing", str(error))
        self.assertIn("Suggested fix", str(error))

    def test_unterminated_block_points_at_block_start(self):
        error = parse_error('module m {\n  entity User {\n    purpose "x"\n')
        self.assertEqual((error.code, error.line), ("ORIN-P003", 2))

    def test_missing_quotes(self):
        error = parse_error('module m {\n  purpose no quotes\n}\n')
        self.assertEqual((error.code, error.line), ("ORIN-P004", 2))

    def test_bad_field(self):
        error = parse_error('module m {\n  type text\n  entity User {\n    field name\n  }\n}\n')
        self.assertEqual((error.code, error.line), ("ORIN-P008", 4))

    def test_file_name_included_and_analyze_message(self):
        with tempfile.TemporaryDirectory(dir=".") as folder:
            path = Path(folder) / "broken.orin"
            path.write_text('module m {\n  oops\n}\n', encoding="utf-8")
            with self.assertRaises(OrinSourceError) as ctx:
                OrinParser().parse_file(path)
            self.assertEqual(ctx.exception.file, str(path))
            self.assertIn(f"{path}:2:3", str(ctx.exception))
            self.assertIn("Suggested fix", analyze(path)[0].message)

    def test_missing_file(self):
        with self.assertRaises(OrinSourceError) as ctx:
            OrinParser().parse_file("does-not-exist.orin")
        self.assertEqual(ctx.exception.code, "ORIN-P012")

    def test_still_a_value_error(self):
        self.assertIsInstance(parse_error("nothing"), ValueError)

    def test_valid_source_unchanged(self):
        model = OrinParser().parse('module m {\n  purpose "x"\n}\n')
        self.assertIsNotNone(model)


if __name__ == "__main__":
    unittest.main()
