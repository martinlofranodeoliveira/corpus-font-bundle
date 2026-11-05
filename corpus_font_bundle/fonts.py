import hashlib
import io

from fontTools import subset
from fontTools.ttLib import TTFont

from .errors import BundleError
from .validation import FONT_LIMIT, GLYPH_LIMIT, canonical

TIMESTAMP = 2082844800
FORBIDDEN = {"fvar", "gvar", "CFF ", "CFF2", "COLR", "CPAL", "CBDT", "CBLC", "sbix", "SVG ", "EBDT", "EBLC", "EBSC"}
REQUIRED = {"glyf", "loca", "head", "maxp", "hmtx", "cmap", "post", "name", "OS/2"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(data):
    if len(data) > FONT_LIMIT:
        raise BundleError("INPUT_LIMIT")
    if data[:4] != b"\x00\x01\x00\x00":
        raise BundleError("UNSUPPORTED_FONT")
    try:
        font = TTFont(io.BytesIO(data), recalcTimestamp=False, lazy=False)
        inspect(font)
        return font
    except BundleError:
        raise
    except Exception:
        raise BundleError("INVALID_FONT") from None


def inspect(font):
    if font.flavor is not None or not REQUIRED <= set(font.keys()) or FORBIDDEN & set(font.keys()):
        raise BundleError("UNSUPPORTED_FONT")
    if not 1 <= font["maxp"].numGlyphs <= GLYPH_LIMIT:
        raise BundleError("GLYPH_LIMIT")
    order = font.getGlyphOrder()
    if len(order) != font["maxp"].numGlyphs or len(set(order)) != len(order) or order[0] != ".notdef":
        raise BundleError("INVALID_FONT")
    if font["post"].formatType != 2.0:
        raise BundleError("STABLE_NAMES_REQUIRED")
    if font["OS/2"].fsType != 0:
        raise BundleError("FONT_RESTRICTED")
    return order


def coverage(font, corpus):
    cmap = font.getBestCmap() or {}
    missing = {ord(c) for c in corpus if ord(c) not in cmap or cmap[ord(c)] == ".notdef"}
    if missing:
        raise BundleError("MISSING_CHARACTER", count=len(missing))


def names_digest(font):
    records = sorted([n.nameID, n.platformID, n.platEncID, n.langID, n.string.hex()]
                     for n in font["name"].names)
    return sha(canonical(records))


def same_metadata(original, candidate):
    if original["OS/2"].fsType != candidate["OS/2"].fsType or names_digest(original) != names_digest(candidate):
        raise BundleError("METADATA_CHANGED")


def save(font, *, flavor=None):
    font.recalcTimestamp = False
    font["head"].created = TIMESTAMP
    font["head"].modified = TIMESTAMP
    font.flavor = flavor
    stream = io.BytesIO()
    font.save(stream, reorderTables=True)
    data = stream.getvalue()
    if len(data) > FONT_LIMIT:
        raise BundleError("OUTPUT_LIMIT")
    return data


def subset_bytes(source, corpus):
    font = load(source)
    try:
        coverage(font, corpus)
        opts = subset.Options()
        opts.glyph_names = True
        opts.ignore_missing_unicodes = False
        opts.notdef_glyph = True
        opts.notdef_outline = True
        opts.recommended_glyphs = False
        opts.layout_features = ["*"]
        opts.layout_closure = True
        opts.name_IDs = ["*"]
        opts.name_languages = ["*"]
        opts.name_legacy = True
        opts.harfbuzz_repacker = False
        worker = subset.Subsetter(options=opts)
        worker.populate(unicodes=sorted({ord(c) for c in corpus}))
        worker.subset(font)
        return save(font)
    finally:
        font.close()


def encode(ttf):
    font = load(ttf)
    try:
        return save(font, flavor="woff2")
    finally:
        font.close()


def decode(woff):
    if len(woff) > FONT_LIMIT or woff[:4] != b"wOF2":
        raise BundleError("INVALID_WOFF2")
    try:
        font = TTFont(io.BytesIO(woff), recalcTimestamp=False, lazy=False)
        try:
            font.flavor = None
            inspect(font)
            return save(font)
        finally:
            font.close()
    except BundleError:
        raise
    except Exception:
        raise BundleError("INVALID_WOFF2") from None
