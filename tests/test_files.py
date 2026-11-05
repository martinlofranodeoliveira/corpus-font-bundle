import os
from unittest.mock import patch

from corpus_font_bundle import recoverStage
from corpus_font_bundle.files import Stage, read_regular
from support import Workspace


class FileTests(Workspace):
    def test_fifo_rejected_before_open_and_symlink_rejected(self):
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with patch("corpus_font_bundle.files.os.open", wraps=os.open) as opened:
            self.error("NOT_REGULAR_FILE", lambda: read_regular(fifo))
            self.assertFalse(any(call.args and call.args[0] == "fifo" for call in opened.call_args_list))
        link = self.root / "link"
        link.symlink_to(self.font)
        self.error("NOT_REGULAR_FILE", lambda: read_regular(link))

    def test_no_replace_even_when_destination_appears_after_stage(self):
        stage = Stage(self.destination)
        for name in ("bundle.ttf", "bundle.woff2", "manifest.json"):
            stage.write(name, b"fixture")
        self.destination.mkdir()
        sentinel = self.destination / "sentinel"
        sentinel.write_bytes(b"keep")
        try:
            self.error("DESTINATION_EXISTS", stage.publish)
        finally:
            stage.close()
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertFalse(any(p.name.startswith(".cfb-stage-") for p in self.root.iterdir()))

    def test_existing_destination_unchanged(self):
        self.destination.mkdir()
        sentinel = self.destination / "sentinel"
        sentinel.write_bytes(b"keep")
        self.error("DESTINATION_EXISTS", self.build)
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertEqual(self.font.read_bytes(), self.original)

    def test_recovery_requires_marker_and_flat_owned_contents(self):
        stage = Stage(self.destination)
        name = stage.name
        os.close(stage.fd)
        os.close(stage.parent)
        stage_path = self.root / name
        (stage_path / "unexpected").write_bytes(b"preserve")
        self.error("UNOWNED_STAGE", lambda: recoverStage(stage_path))
        self.assertTrue((stage_path / "unexpected").exists())
        (stage_path / "unexpected").unlink()
        self.assertEqual(recoverStage(stage_path), {"removed": True})
        self.assertFalse(stage_path.exists())
        unmarked = self.root / (".cfb-stage-" + "a" * 32)
        unmarked.mkdir()
        self.error("RECOVERY_FAILED", lambda: recoverStage(unmarked))
        self.assertTrue(unmarked.exists())

    def test_oversize_rejected_without_reading(self):
        file = self.root / "large"
        with file.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        self.error("INPUT_LIMIT", lambda: read_regular(file))
