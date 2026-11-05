"""Original synthetic test font. No third-party font data or outlines."""
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from .fonts import save

CORPUS = "fi Á A\u0301"


def rectangle(x, y, width, height):
    pen = TTGlyphPen(None)
    pen.moveTo((x, y))
    pen.lineTo((x + width, y))
    pen.lineTo((x + width, y + height))
    pen.lineTo((x, y + height))
    pen.closePath()
    return pen.glyph()


def font_bytes():
    order = [".notdef", "space", "f", "i", "fi", "A", "Aacute", "acutecomb", "Z"]
    glyphs = {".notdef": rectangle(40, 0, 400, 650), "space": TTGlyphPen(None).glyph(),
              "f": rectangle(40, 0, 160, 700), "i": rectangle(80, 0, 100, 500),
              "fi": rectangle(40, 0, 420, 700), "A": rectangle(50, 0, 500, 650),
              "acutecomb": rectangle(220, 720, 140, 80), "Z": rectangle(40, 0, 480, 630)}
    composite = TTGlyphPen(glyphs)
    composite.addComponent("A", (1, 0, 0, 1, 0, 0))
    composite.addComponent("acutecomb", (1, 0, 0, 1, 0, 0))
    glyphs["Aacute"] = composite.glyph()
    builder = FontBuilder(unitsPerEm=1000, isTTF=True)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({32: "space", 102: "f", 105: "i", 65: "A", 193: "Aacute", 769: "acutecomb", 90: "Z"})
    builder.setupGlyf(glyphs)
    widths = {".notdef": 500, "space": 250, "f": 300, "i": 300, "fi": 550,
              "A": 600, "Aacute": 600, "acutecomb": 0, "Z": 600}
    builder.setupHorizontalMetrics({name: (widths[name], 0) for name in order})
    builder.setupHorizontalHeader(ascent=900, descent=-200)
    builder.setupNameTable({"familyName": "Corpus Synthetic", "styleName": "Regular",
                            "uniqueFontIdentifier": "Lofrano-Corpus-Synthetic-0.1.0",
                            "fullName": "Corpus Synthetic Regular", "psName": "CorpusSynthetic-Regular",
                            "version": "Version 0.1.0",
                            "copyright": "Copyright 2026 Lofrano Tecnologia",
                            "licenseDescription": "Original synthetic fixture, licensed under the MIT License.",
                            "licenseInfoURL": "https://lofranotecnologia.com.br"})
    builder.setupOS2(sTypoAscender=900, sTypoDescender=-200, usWinAscent=900, usWinDescent=200, fsType=0)
    builder.setupPost(keepGlyphNames=True)
    builder.setupMaxp()
    addOpenTypeFeaturesFromString(builder.font, """
        languagesystem DFLT dflt;
        languagesystem latn dflt;
        feature ccmp { sub A acutecomb by Aacute; } ccmp;
        feature liga { sub f i by fi; } liga;
        feature kern { pos A A -40; } kern;
    """)
    return save(builder.font)


def shaping_cases():
    def case(content, liga=1, kern=0):
        return {"text": content, "language": "en", "direction": "ltr", "script": "Latn",
                "features": {"liga": liga, "kern": kern, "ccmp": 1}}
    return [case("fi"), case("fi", liga=0), case("Á"), case("A\u0301"), case("AA", kern=1)]
