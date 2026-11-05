import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class InstallationTests(unittest.TestCase):
    def test_offline_wheel_install_and_external_cli(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="cfb-install-") as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            shutil.copytree(project / "corpus_font_bundle", source / "corpus_font_bundle",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for name in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copyfile(project / name, source / name)
            wheels = root / "wheels"
            wheels.mkdir()
            self.command([sys.executable, "-m", "pip", "wheel", "--no-index", "--no-deps",
                          "--no-build-isolation", "--wheel-dir", str(wheels), str(source)], root)
            wheel, = wheels.glob("*.whl")
            installed = root / "installed"
            self.command([sys.executable, "-m", "pip", "install", "--no-index", "--no-deps",
                          "--target", str(installed), str(wheel)], root)
            env = dict(os.environ, PYTHONPATH=str(installed))
            output = self.command([sys.executable, "-m", "corpus_font_bundle", "demo", "--assert", "--json"], root, env)
            self.assertIn('"ok": true', output)
            self.assertIn('"subset_glyphs": 8', output)

    def command(self, argv, cwd, env=None):
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-4000:])
        return result.stdout
