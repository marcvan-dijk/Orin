"""Seeded mutation/robustness tests: the parser may only raise OrinSourceError."""
import random
import shutil
import signal
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orin_parser import OrinParser, OrinSourceError, analyze

ROOT = Path(__file__).resolve().parents[2]
FILES = sorted((ROOT / "examples").glob("*.orin")) + sorted((ROOT / "examples" / "authoring").glob("*.orin"))
KEYWORDS = ["rule", "example", "uncertainty", "decision", "field", "context", "entity", "purpose", "given", "when", "then"]
JUNK = ["\t", "\ufeff", "é☃𝄞", "x" * 20000, " " * 400, "\r", "\x00", "\u2028"]
CASE_SECONDS = 2
PER_FILE = 25


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def mutate(rng: random.Random, text: str) -> str:
    lines = text.split("\n")
    kind = rng.choice(["delete", "dup", "reorder", "truncate", "tab", "crlf", "bom", "unicode", "long", "indent", "swap"])
    i = rng.randrange(len(lines))
    if kind == "delete":
        del lines[i]
    elif kind == "dup":
        lines.insert(i, lines[i])
    elif kind == "reorder":
        j = rng.randrange(len(lines))
        lines[i], lines[j] = lines[j], lines[i]
    elif kind == "truncate":
        return text[: rng.randrange(len(text) + 1)]
    elif kind == "tab":
        lines[i] = "\t" + lines[i]
    elif kind == "crlf":
        return "\r\n".join(lines).replace("\r\n", "\r", rng.randrange(2))
    elif kind == "bom":
        return "\ufeff" + text if rng.random() < 0.5 else text[:i] + "\ufeff" + text[i:]
    elif kind == "unicode":
        lines[i] += rng.choice(JUNK)
    elif kind == "long":
        lines[i] += "x" * rng.choice([5000, 100000])
    elif kind == "indent":
        lines[i] = " " * rng.choice([1, 3, 50, 2000]) + lines[i].lstrip()
    else:
        words = lines[i].split(" ")
        for k, w in enumerate(words):
            if w in KEYWORDS:
                words[k] = rng.choice(KEYWORDS)
        lines[i] = " ".join(words)
    return "\n".join(lines)


class ParserRobustnessTests(unittest.TestCase):
    def setUp(self):
        signal.signal(signal.SIGALRM, _alarm)

    def tearDown(self):
        signal.alarm(0)

    def _run(self, name, text):
        signal.alarm(CASE_SECONDS)
        try:
            OrinParser().parse_outline(text, Path(name))
        except OrinSourceError as error:
            self.assertTrue(error.file, f"{name}: error lacks file")
            self.assertGreaterEqual(error.line, 1, f"{name}: error lacks line")
            self.assertGreaterEqual(error.column, 1)
        except _Timeout:
            self.fail(f"{name}: parser hung (> {CASE_SECONDS}s)")
        except Exception as error:  # noqa: BLE001
            self.fail(f"{name}: {type(error).__name__} escaped: {error}")
        finally:
            signal.alarm(0)

    def test_mutations_only_raise_source_errors(self):
        self.assertTrue(FILES)
        for path in FILES:
            base = path.read_text(encoding="utf-8")
            rng = random.Random(f"orin-robustness:{path.name}")
            for n in range(PER_FILE):
                text = base
                for _ in range(rng.randint(1, 3)):
                    text = mutate(rng, text)
                with self.subTest(file=path.name, case=n):
                    self._run(str(path), text)

    def test_analyze_never_raises_on_mutations(self):
        scratch = Path(__file__).resolve().parent / "_robustness_scratch"
        scratch.mkdir(exist_ok=True)
        try:
            for path in FILES:
                base = path.read_text(encoding="utf-8")
                rng = random.Random(f"orin-analyze:{path.name}")
                for n in range(5):
                    target = scratch / f"{path.stem}-{n}.orin"
                    target.write_bytes(mutate(rng, mutate(rng, base)).encode("utf-8", "surrogatepass"))
                    with self.subTest(file=path.name, case=n):
                        signal.alarm(CASE_SECONDS)
                        try:
                            result = analyze(target)
                        finally:
                            signal.alarm(0)
                        self.assertIsInstance(result, list)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_invalid_utf8_reports_source_error(self):
        scratch = Path(__file__).resolve().parent / "_robustness_scratch"
        scratch.mkdir(exist_ok=True)
        try:
            bad = scratch / "bad.orin"
            bad.write_bytes(b"\xff\xfe\x00bad")
            with self.assertRaises(OrinSourceError) as ctx:
                OrinParser().parse_file(bad)
            self.assertTrue(ctx.exception.file)
            self.assertEqual(ctx.exception.line, 1)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_crlf_and_bom_parse_same_as_lf(self):
        parser = OrinParser()
        for path in FILES:
            lf = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            expected = parser.parse_outline(lf, path)
            for label, text in (("crlf", lf.replace("\n", "\r\n")), ("bom", "\ufeff" + lf), ("bom+crlf", "\ufeff" + lf.replace("\n", "\r\n"))):
                with self.subTest(file=path.name, variant=label):
                    self.assertEqual(parser.parse_outline(text, path).document, expected.document)

    def _file_variant(self, label, encode):
        scratch = Path(__file__).resolve().parent / "_robustness_scratch"
        scratch.mkdir(exist_ok=True)
        try:
            for path in FILES:
                lf = path.read_text(encoding="utf-8").replace("\r\n", "\n")
                expected = OrinParser().parse_file(path)
                target = scratch / f"{path.stem}-{label}.orin"
                target.write_bytes(encode(lf))
                with self.subTest(file=path.name, variant=label):
                    self.assertEqual(OrinParser().parse_file(target).document, expected.document)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_crlf_files_parse_same_as_lf(self):
        self._file_variant("crlf", lambda t: t.replace("\n", "\r\n").encode())

    # Bug: parse_file does not strip a UTF-8 BOM, so _is_outline fails and ORIN-P001 is raised.
    def test_bom_files_parse_same_as_lf(self):
        self._file_variant("bom", lambda t: b"\xef\xbb\xbf" + t.encode())


if __name__ == "__main__":
    unittest.main()
