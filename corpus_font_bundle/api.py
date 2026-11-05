import os
from pathlib import Path
import tempfile

from . import fonts, manifest, toolchain, validation
from .errors import BundleError
from .files import Stage, directory_fd, read_in, read_regular


def _admit(source, corpus):
    font = fonts.load(source)
    try:
        fonts.coverage(font, corpus)
    finally:
        font.close()


def buildBundle(font, corpus, shapingCases, options):
    """Publish after validation; PUBLISHED_IO_ERROR identifies post-commit I/O failure."""
    stage = None
    try:
        destination = validation.options(options)
        cases = validation.cases(corpus, shapingCases)
        source_path = validation.path(font)
        source = read_regular(source_path)
        _admit(source, corpus)
        tools = toolchain.versions()
        ttf = fonts.subset_bytes(source, corpus)
        woff = fonts.encode(ttf)
        with tempfile.TemporaryDirectory(prefix="cfb-work-") as temporary:
            result = manifest.evidence(source, ttf, woff, corpus, cases, tools, Path(temporary))
        if read_regular(source_path) != source:
            raise BundleError("INPUT_CHANGED")
        stage = Stage(destination)
        try:
            stage.write("bundle.ttf", ttf)
            stage.write("bundle.woff2", woff)
            stage.write("manifest.json", validation.canonical(result))
            stage.publish()
        finally:
            stage.close()
        return result
    except BundleError:
        raise
    except OSError:
        code = "PUBLISHED_IO_ERROR" if stage is not None and stage.published else "IO_ERROR"
        raise BundleError(code) from None
    except Exception:
        raise BundleError("BUILD_FAILED") from None


def verifyBundle(font, bundle):
    """Replay an existing bundle against its immutable original font snapshot."""
    try:
        source_path = validation.path(font)
        bundle_path = validation.path(bundle)
        fd = directory_fd(bundle_path)
        try:
            raw = read_in(fd, "manifest.json", validation.MANIFEST_LIMIT)
            ttf = read_in(fd, "bundle.ttf")
            woff = read_in(fd, "bundle.woff2")
            if set(os.listdir(fd)) != {"bundle.ttf", "bundle.woff2", "manifest.json"}:
                raise BundleError("INVALID_BUNDLE")
        finally:
            os.close(fd)
        recorded = validation.parse_json(raw)
        if type(recorded) is not dict or recorded.get("schema") != manifest.SCHEMA:
            raise BundleError("INVALID_MANIFEST")
        corpus = recorded.get("corpus")
        records = recorded.get("cases")
        if type(records) is not list or not 1 <= len(records) <= validation.CASE_LIMIT:
            raise BundleError("INVALID_MANIFEST")
        if any(type(item) is not dict or "parameters" not in item for item in records):
            raise BundleError("INVALID_MANIFEST")
        cases = validation.cases(corpus, [item["parameters"] for item in records])
        source = read_regular(source_path)
        _admit(source, corpus)
        tools = toolchain.versions()
        if recorded.get("tools") != tools:
            raise BundleError("TOOLCHAIN_MISMATCH")
        with tempfile.TemporaryDirectory(prefix="cfb-replay-") as temporary:
            actual = manifest.evidence(source, ttf, woff, corpus, cases, tools, Path(temporary))
        if raw != validation.canonical(actual):
            raise BundleError("MANIFEST_MISMATCH")
        if read_regular(source_path) != source:
            raise BundleError("INPUT_CHANGED")
        return actual
    except BundleError:
        raise
    except OSError:
        raise BundleError("IO_ERROR") from None
    except Exception:
        raise BundleError("VERIFY_FAILED") from None
