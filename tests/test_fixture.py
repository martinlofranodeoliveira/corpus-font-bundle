from corpus_font_bundle import fonts, toolchain
from corpus_font_bundle.fixture import CORPUS, shaping_cases
from corpus_font_bundle.outlines import Fingerprints
from corpus_font_bundle.shaping import shape
from oracles import EXPECTED
from support import Workspace


class FixtureTests(Workspace):
    def test_original_has_nine_and_independent_native_metrics(self):
        self.assertEqual(toolchain.versions()["harfbuzz"], "6.0.0")
        font = fonts.load(self.original)
        self.addCleanup(font.close)
        self.assertEqual(font.getGlyphOrder(), [".notdef", "space", "f", "i", "fi", "A", "Aacute", "acutecomb", "Z"])
        fingerprints = Fingerprints(font)
        for case, (names, advances) in zip(shaping_cases(), EXPECTED):
            actual = shape(self.font, case, fingerprints)
            self.assertEqual([g["g"] for g in actual], names)
            self.assertEqual([g["ax"] for g in actual], advances)
            for g in actual:
                self.assertEqual((g["dx"], g["dy"], g["ay"]), (0, 0, 0))
        self.assertIn("Á", CORPUS)
        self.assertIn("A\u0301", CORPUS)
        self.assertNotEqual("Á".encode(), "A\u0301".encode())

    def test_expanded_composite_equals_component_path(self):
        font = fonts.load(self.original)
        self.addCleanup(font.close)
        fp = Fingerprints(font)
        self.assertNotEqual(fp.get("Aacute"), fp.get("A"))
        self.assertEqual(len(fp.get("Aacute")), 64)
