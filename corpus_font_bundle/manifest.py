from . import fonts
from .errors import BundleError
from .outlines import Fingerprints
from .shaping import shape
from .validation import MANIFEST_LIMIT, canonical

SCHEMA = "corpus-font-bundle/1"


def evidence(source, ttf, woff, corpus, cases, tools, work):
    decoded = fonts.decode(woff)
    blobs = [source, ttf, decoded]
    loaded = []
    try:
        loaded = [fonts.load(data) for data in blobs]
        original, candidate, web = loaded
        for item in loaded:
            fonts.coverage(item, corpus)
        fonts.same_metadata(original, candidate)
        fonts.same_metadata(original, web)
        original_order = original.getGlyphOrder()
        order = candidate.getGlyphOrder()
        if order != web.getGlyphOrder() or not set(order) <= set(original_order):
            raise BundleError("GLYPH_MAPPING_CHANGED")
        for item in (candidate, web):
            if item["head"].created != fonts.TIMESTAMP or item["head"].modified != fonts.TIMESTAMP:
                raise BundleError("TIMESTAMP_CHANGED")
        paths = [work / "original.ttf", work / "candidate.ttf", work / "decoded.ttf"]
        for file, data in zip(paths, blobs):
            file.write_bytes(data)
        pens = [Fingerprints(item) for item in loaded]
        records = []
        for case in cases:
            actual = [shape(file, case, pen) for file, pen in zip(paths, pens)]
            if actual[0] != actual[1] or actual[1] != actual[2]:
                raise BundleError("SHAPING_CHANGED")
            records.append({"parameters": case, "original": actual[0], "ttf": actual[1], "woff2": actual[2]})
        original_ids = {name: index for index, name in enumerate(original_order)}
        mapping = [{"name": name, "original_gid": original_ids[name], "subset_gid": index}
                   for index, name in enumerate(order)]
        result = {"schema": SCHEMA, "development_version": "0.1.0", "tools": tools,
                  "source_sha256": fonts.sha(source), "corpus": corpus,
                  "corpus_utf8_sha256": fonts.sha(corpus.encode("utf-8")),
                  "artifacts": {"bundle.ttf": fonts.sha(ttf), "bundle.woff2": fonts.sha(woff)},
                  "licensing": {"fsType": original["OS/2"].fsType, "name_records_sha256": fonts.names_digest(original)},
                  "original_glyph_count": len(original_order), "subset_glyph_count": len(order),
                  "glyph_mapping": mapping, "cases": records}
        if len(canonical(result)) > MANIFEST_LIMIT:
            raise BundleError("MANIFEST_LIMIT")
        return result
    finally:
        for item in loaded:
            item.close()
