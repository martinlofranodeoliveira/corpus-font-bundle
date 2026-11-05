from unittest.mock import patch

from corpus_font_bundle import fonts, verifyBundle
from corpus_font_bundle.validation import canonical, parse_json
from support import Workspace


class VerificationTests(Workspace):
    def test_missing_substitution_cannot_publish(self):
        real = fonts.subset_bytes

        def broken(source, corpus):
            font = fonts.load(real(source, corpus))
            try:
                del font["GSUB"]
                return fonts.save(font)
            finally:
                font.close()

        with patch("corpus_font_bundle.fonts.subset_bytes", broken):
            self.error("SHAPING_CHANGED", self.build)
        self.assert_unpublished()

    def test_gpos_loss_cannot_publish(self):
        real = fonts.subset_bytes

        def broken(source, corpus):
            font = fonts.load(real(source, corpus))
            try:
                del font["GPOS"]
                return fonts.save(font)
            finally:
                font.close()

        with patch("corpus_font_bundle.fonts.subset_bytes", broken):
            self.error("SHAPING_CHANGED", self.build)
        self.assert_unpublished()

    def test_outline_tamper_with_unchanged_metrics_fails(self):
        real = fonts.subset_bytes

        def broken(source, corpus):
            font = fonts.load(real(source, corpus))
            try:
                glyph = font["glyf"]["fi"]
                glyph.coordinates[0] = (glyph.coordinates[0][0] + 10, glyph.coordinates[0][1])
                return fonts.save(font)
            finally:
                font.close()

        with patch("corpus_font_bundle.fonts.subset_bytes", broken):
            self.error("SHAPING_CHANGED", self.build)
        self.assert_unpublished()

    def test_manifest_and_woff_are_actually_checked(self):
        self.build()
        file = self.destination / "manifest.json"
        original = file.read_bytes()
        parsed = parse_json(original)
        parsed["cases"][0]["ttf"][0]["ax"] = 551
        file.write_bytes(canonical(parsed))
        self.error("MANIFEST_MISMATCH", lambda: verifyBundle(self.font, self.destination))
        file.write_bytes(original)
        (self.destination / "bundle.woff2").write_bytes(b"wOF2broken")
        self.error("INVALID_WOFF2", lambda: verifyBundle(self.font, self.destination))
        self.assertEqual(self.font.read_bytes(), self.original)

    def test_duplicate_json_and_extra_bundle_file_rejected(self):
        self.build()
        file = self.destination / "manifest.json"
        original = file.read_bytes()
        file.write_bytes(b'{"schema":1,"schema":2}')
        self.error("INVALID_JSON", lambda: verifyBundle(self.font, self.destination))
        file.write_bytes(original)
        (self.destination / "extra").write_bytes(b"x")
        self.error("INVALID_BUNDLE", lambda: verifyBundle(self.font, self.destination))
