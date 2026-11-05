from pathlib import Path
import tempfile
import unittest

from corpus_font_bundle import BundleError, buildBundle
from corpus_font_bundle.fixture import CORPUS, font_bytes, shaping_cases


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cfb-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.font = self.root / "source.ttf"
        self.original = font_bytes()
        self.font.write_bytes(self.original)
        self.destination = self.root / "bundle"

    def build(self):
        return buildBundle(self.font, CORPUS, shaping_cases(), {"destination": self.destination})

    def error(self, code, action):
        with self.assertRaises(BundleError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def assert_unpublished(self):
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.font.read_bytes(), self.original)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["source.ttf"])
