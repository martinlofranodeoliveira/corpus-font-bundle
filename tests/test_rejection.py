import copy
from unittest.mock import patch

from corpus_font_bundle import buildBundle, fonts
from corpus_font_bundle.fixture import CORPUS, shaping_cases
from support import Workspace


class RejectionTests(Workspace):
    def call(self, corpus=CORPUS, cases=None, options=None):
        return buildBundle(self.font, corpus, shaping_cases() if cases is None else cases,
                           {"destination": self.destination} if options is None else options)

    def test_missing_before_native_work(self):
        with patch("corpus_font_bundle.toolchain.versions", side_effect=AssertionError("native called")):
            error = self.error("MISSING_CHARACTER", lambda: self.call(CORPUS + "ΩΩ"))
        self.assertEqual(error.count, 1)
        self.assert_unpublished()

    def test_options_and_case_grammar_before_native(self):
        bad = [None, [], {"destination": self.destination, "timeout": 99}, {"destination": True}]
        with patch("corpus_font_bundle.toolchain.versions", side_effect=AssertionError("native called")):
            for options in bad:
                if options is None:
                    self.error("INVALID_OPTIONS", lambda: buildBundle(self.font, CORPUS, shaping_cases(), None))
                else:
                    self.error("INVALID_OPTIONS" if type(options) is not dict or "timeout" in options else "INVALID_PATH",
                               lambda o=options: self.call(options=o))
            for value in (True, -1, 65536, "1"):
                cases = shaping_cases()
                cases[0]["features"]["liga"] = value
                self.error("INVALID_FEATURES", lambda c=cases: self.call(cases=c))
            cases = shaping_cases()
            cases[0]["language"] = "en --output-file=bad"
            self.error("INVALID_CASES", lambda: self.call(cases=cases))
        self.assert_unpublished()

    def test_text_and_case_limits(self):
        self.error("INVALID_TEXT", lambda: self.call("A" * 16385))
        self.error("INVALID_TEXT", lambda: self.call("A\0"))
        self.error("INVALID_TEXT", lambda: self.call("\ud800"))
        self.error("INVALID_CASES", lambda: self.call(cases=shaping_cases() * 13))
        cases = copy.deepcopy(shaping_cases())
        cases[0]["text"] = "Z"
        self.error("CASE_OUTSIDE_CORPUS", lambda: self.call(cases=cases))
        self.assert_unpublished()

    def test_restricted_embedding_is_not_erased(self):
        font = fonts.load(self.original)
        font["OS/2"].fsType = 0x100
        restricted = fonts.save(font)
        font.close()
        self.font.write_bytes(restricted)
        self.error("FONT_RESTRICTED", self.build)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.font.read_bytes(), restricted)

    def test_bad_font_and_glyph_limit(self):
        self.font.write_bytes(b"not a font")
        self.error("UNSUPPORTED_FONT", self.build)
        self.assertFalse(self.destination.exists())
        font = fonts.load(self.original)
        self.addCleanup(font.close)
        font["maxp"].numGlyphs = 4097
        self.error("GLYPH_LIMIT", lambda: fonts.inspect(font))
