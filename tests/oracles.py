"""Literal expectations, deliberately not calculated from production font metrics."""
EXPECTED = [(["fi"], [550]), (["f", "i"], [300, 300]), (["Aacute"], [600]),
            (["Aacute"], [600]), (["A", "A"], [560, 600])]
RETAINED = {".notdef", "space", "f", "i", "fi", "A", "Aacute", "acutecomb"}
