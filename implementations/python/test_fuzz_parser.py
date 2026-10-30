"""Seeded fuzzing of the parser and CLI: only OrinSourceError may escape, never a hang or a crash.

Also checks that `generate --out` never writes outside the requested directory.
"""
import contextlib
import io
import json
import random
import shutil
import signal
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orin_parser import OrinParser, OrinSourceError, analyze

EXAMPLES = sorted((ROOT / "examples").glob("*.orin"))
HERE = Path(__file__).resolve().parent
SECONDS = 2
PER_FILE = 40


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def mutate(rng: random.Random, text: str) -> str:
    lines = text.split("\n")
    i = rng.randrange(len(lines))
    kind = rng.choice(["delete", "dup", "swap", "bytes", "indent", "nest", "huge", "empty"])
    if kind == "delete":
        del lines[i]
    elif kind == "dup":
        lines[i:i] = [lines[i]] * rng.choice([1, 2, 50])
    elif kind == "swap":
        j = rng.randrange(len(lines))
        lines[i], lines[j] = lines[j], lines[i]
    elif kind == "bytes":
        chars = list(lines[i])
        for _ in range(rng.randint(1, 8)):
            pos = rng.randrange(len(chars) + 1)
            chars.insert(pos, chr(rng.choice([0, 1, 9, 13, 127, 0xA0, 0xE9, 0x2028, 0xFEFF, 0x1D11E, rng.randrange(32, 127)])))
        lines[i] = "".join(chars)
    elif kind == "indent":
        lines[i] = " " * rng.choice([1, 3, 7, 500, 100000]) + lines[i].lstrip()
    elif kind == "nest":
        depth = rng.choice([50, 500, 3000])
        lines[i:i] = ["  " * d + "- level" for d in range(depth)]
    elif kind == "huge":
        lines[i] += "x" * 1_000_000
    else:
        lines = [""]
    return "\n".join(lines)


class FuzzParserTests(unittest.TestCase):
    def setUp(self):
        signal.signal(signal.SIGALRM, _alarm)
        self.scratch = Path(tempfile.mkdtemp(prefix="_fuzz_scratch_", dir=HERE))

    def tearDown(self):
        signal.alarm(0)
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _guard(self, label, func):
        signal.alarm(SECONDS)
        try:
            return func()
        except OrinSourceError:
            return None
        except _Timeout:
            self.fail(f"{label}: hung for more than {SECONDS}s")
        except RecursionError:
            self.fail(f"{label}: recursed without limit")
        except Exception as error:  # noqa: BLE001
            self.fail(f"{label}: {type(error).__name__} escaped: {error}")
        finally:
            signal.alarm(0)

    def test_parse_mutations(self):
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            base = path.read_text(encoding="utf-8")
            rng = random.Random(f"orin-fuzz-parse:{path.name}")
            for n in range(PER_FILE):
                text = base
                for _ in range(rng.randint(1, 3)):
                    text = mutate(rng, text)
                with self.subTest(file=path.name, case=n):
                    self._guard(f"{path.name}#{n}", lambda: OrinParser().parse_outline(text, path))

    def test_analyze_and_cli_check_mutations(self):
        from tooling.python import orin_cli

        for path in EXAMPLES:
            base = path.read_text(encoding="utf-8")
            rng = random.Random(f"orin-fuzz-cli:{path.name}")
            for n in range(6):
                target = self.scratch / f"{path.stem}-{n}.orin"
                target.write_bytes(mutate(rng, mutate(rng, base)).encode("utf-8", "surrogatepass"))

                def run():
                    analyze(target)
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        return orin_cli.main(["check", str(target)])

                with self.subTest(file=path.name, case=n):
                    code = self._guard(f"{path.name}#{n}", run)
                    self.assertIn(code, (None, 0, 1, 2, 3))

    def test_deep_nesting_and_huge_indent_alone(self):
        base = EXAMPLES[0].read_text(encoding="utf-8")
        cases = {
            "deep": base + "\n" + "\n".join("  " * d + "- level" for d in range(5000)),
            "indent": base + "\n" + " " * 200000 + "rule",
            "line": base + "\n" + "x" * 1_000_000,
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self._guard(label, lambda: OrinParser().parse_outline(text, EXAMPLES[0]))


class GeneratePathTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix="_fuzz_scratch_", dir=HERE))

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_crafted_module_ids_stay_inside_out_dir(self):
        from tooling.python import orin_cli

        source = json.loads((ROOT / "tests" / "conformance" / "library-lending.decided.json").read_text(encoding="utf-8"))
        evil = ["../../escape", "..\\..\\escape", "/etc/escape", "a/../../b", "\x00x", "x" * 5000, "..", ""]
        for n, name in enumerate(evil):
            model = json.loads(json.dumps(source))
            model["module"]["name"] = name
            model["module"]["id"] = name
            work = self.scratch / f"case{n}"
            out = work / "out"
            work.mkdir(parents=True, exist_ok=True)
            model_path = work / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            with self.subTest(name=name[:20]):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    try:
                        orin_cli.main(["generate", str(model_path), "--target", "python", "--out", str(out)])
                    except SystemExit:
                        pass
                self.assertEqual({p.name for p in work.iterdir()} - {"out", "model.json"}, set())
                self.assertFalse((self.scratch / "escape.py").exists())
                for written in out.rglob("*") if out.exists() else []:
                    self.assertTrue(written.resolve().is_relative_to(out.resolve()), written)


if __name__ == "__main__":
    unittest.main()
