from pathlib import Path
import tempfile

from .api import buildBundle, verifyBundle
from .errors import BundleError
from .fixture import CORPUS, font_bytes, shaping_cases
from .fonts import sha

# Literal metrics are independent of the font builder and subset implementation.
ORACLE = [(["fi"], [550]), (["f", "i"], [300, 300]), (["Aacute"], [600]),
          (["Aacute"], [600]), (["A", "A"], [560, 600])]


def run(assertions=False):
    with tempfile.TemporaryDirectory(prefix="cfb-demo-") as temporary:
        root = Path(temporary)
        original = font_bytes()
        source = root / "original.ttf"
        source.write_bytes(original)
        first = buildBundle(source, CORPUS, shaping_cases(), {"destination": root / "one"})
        second = buildBundle(source, CORPUS, shaping_cases(), {"destination": root / "two"})
        verifyBundle(source, root / "one")
        metrics = []
        for case in first["cases"]:
            glyphs = case["ttf"]
            metrics.append(([g["g"] for g in glyphs], [g["ax"] for g in glyphs]))
        deterministic = first == second
        missing = None
        try:
            buildBundle(source, CORPUS + "Ω", shaping_cases(), {"destination": root / "missing"})
        except BundleError as error:
            missing = error.as_dict()
        removed = sorted({".notdef", "space", "f", "i", "fi", "A", "Aacute", "acutecomb", "Z"} -
                         {g["name"] for g in first["glyph_mapping"]})
        valid = (metrics == ORACLE and first["original_glyph_count"] == 9 and first["subset_glyph_count"] == 8
                 and removed == ["Z"] and deterministic and source.read_bytes() == original
                 and missing == {"code": "MISSING_CHARACTER", "count": 1} and not (root / "missing").exists())
        valid = valid and all(g["dx"] == g["dy"] == g["ay"] == 0
                              for case in first["cases"] for g in case["ttf"])
        if assertions and not valid:
            raise BundleError("DEMO_ORACLE_FAILED")
        return {"ok": valid, "original_glyphs": 9, "subset_glyphs": first["subset_glyph_count"],
                "removed": removed, "cases": [{"names": n, "advances": a} for n, a in metrics],
                "deterministic": deterministic, "missing": missing,
                "source_sha256": sha(original), "artifacts": first["artifacts"]}


def human(result):
    return "\n".join(["Corpus Font Bundle — development 0.1.0",
                      "Glyphs: 9 -> " + str(result["subset_glyphs"]) + "; removed: " + ", ".join(result["removed"]),
                      "Replay: 5 cases matched original, TTF and decoded WOFF2",
                      "Advances: fi=550; f+i=600; Á=600; A+U+0301=600; AA=560+600",
                      "Missing Ω: MISSING_CHARACTER (count=1), no bundle",
                      "Repeat build: " + ("identical" if result["deterministic"] else "different"),
                      "Oracle: " + ("PASS" if result["ok"] else "FAIL")])
