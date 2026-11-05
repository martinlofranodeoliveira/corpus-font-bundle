import os
from unittest.mock import patch

from corpus_font_bundle import buildBundle, verifyBundle, fonts
from corpus_font_bundle.fixture import CORPUS, shaping_cases
from oracles import EXPECTED, RETAINED
from support import Workspace


class BuildTests(Workspace):
    def test_full_contract_and_determinism(self):
        first = self.build()
        second_dir = self.root / "second"
        second = buildBundle(self.font, CORPUS, shaping_cases(), {"destination": second_dir})
        self.assertEqual(first, second)
        self.assertEqual(first["original_glyph_count"], 9)
        self.assertEqual(first["subset_glyph_count"], 8)
        self.assertEqual({g["name"] for g in first["glyph_mapping"]}, RETAINED)
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), ["bundle.ttf", "bundle.woff2", "manifest.json"])
        for artifact in ("bundle.ttf", "bundle.woff2"):
            self.assertEqual((self.destination / artifact).read_bytes(), (second_dir / artifact).read_bytes())
        self.assertEqual(first, verifyBundle(self.font, self.destination))
        for record, (names, advances) in zip(first["cases"], EXPECTED):
            self.assertEqual(record["original"], record["ttf"])
            self.assertEqual(record["ttf"], record["woff2"])
            self.assertEqual([g["g"] for g in record["woff2"]], names)
            self.assertEqual([g["ax"] for g in record["woff2"]], advances)
        self.assertEqual(self.font.read_bytes(), self.original)
        original = fonts.load(self.font.read_bytes())
        self.addCleanup(original.close)
        self.assertEqual(len(original.getGlyphOrder()), 9)

    def test_name_records_and_timestamps(self):
        self.build()
        original = fonts.load(self.original)
        subset = fonts.load((self.destination / "bundle.ttf").read_bytes())
        self.addCleanup(original.close)
        self.addCleanup(subset.close)
        self.assertEqual(fonts.names_digest(original), fonts.names_digest(subset))
        self.assertEqual(subset["head"].created, 2082844800)
        self.assertEqual(subset["head"].modified, 2082844800)
        self.assertEqual(subset["OS/2"].fsType, 0)
        self.assertTrue({13, 14} <= {n.nameID for n in subset["name"].names})
        self.assertEqual(subset["post"].formatType, 2.0)

    def test_post_rename_io_failure_reports_visible_commit(self):
        real_fsync = os.fsync

        def fail_after_commit(fd):
            if self.destination.exists():
                raise OSError("synthetic post-commit storage failure")
            return real_fsync(fd)

        with patch("corpus_font_bundle.files.os.fsync", side_effect=fail_after_commit):
            self.error("PUBLISHED_IO_ERROR", self.build)
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()),
                         ["bundle.ttf", "bundle.woff2", "manifest.json"])
        self.assertEqual(verifyBundle(self.font, self.destination)["subset_glyph_count"], 8)
        self.assertEqual(self.font.read_bytes(), self.original)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["bundle", "source.ttf"])
