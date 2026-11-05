import json
import subprocess
import sys

from corpus_font_bundle.fixture import CORPUS, shaping_cases
from support import Workspace


class CliTests(Workspace):
    def invoke(self, *args):
        return subprocess.run([sys.executable, "-m", "corpus_font_bundle", *map(str, args)],
                              capture_output=True, text=True, timeout=60)

    def test_cli_build_verify_and_safe_error(self):
        corpus = self.root / "corpus.txt"
        cases = self.root / "cases.json"
        corpus.write_bytes(CORPUS.encode("utf-8"))
        cases.write_text(json.dumps(shaping_cases()), encoding="utf-8")
        result = self.invoke("build", "--font", self.font, "--corpus-file", corpus,
                             "--cases-file", cases, "--destination", self.destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])
        result = self.invoke("verify", "--font", self.font, "--bundle", self.destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        corpus.write_text(CORPUS + "Ω", encoding="utf-8")
        result = self.invoke("build", "--font", self.font, "--corpus-file", corpus,
                             "--cases-file", cases, "--destination", self.root / "missing")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr), {"ok": False, "error": {"code": "MISSING_CHARACTER", "count": 1}})
        self.assertNotIn(str(self.root), result.stderr)

    def test_demo_machine_and_human_output(self):
        machine = self.invoke("demo", "--assert", "--json")
        self.assertEqual(machine.returncode, 0, machine.stderr)
        data = json.loads(machine.stdout)
        self.assertTrue(data["deterministic"])
        self.assertEqual(data["removed"], ["Z"])
        human = self.invoke("demo", "--assert")
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn("Oracle: PASS", human.stdout)
