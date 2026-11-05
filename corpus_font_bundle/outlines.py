import math

from fontTools.pens.recordingPen import DecomposingRecordingPen

from .errors import BundleError
from .fonts import sha
from .validation import canonical


class BoundedPen(DecomposingRecordingPen):
    def __init__(self, glyphset, name):
        super().__init__(glyphset, skipMissingComponents=False)
        self.stack = [name]

    def record(self, operation, points):
        if len(self.value) >= 100_000:
            raise BundleError("OUTLINE_LIMIT")
        self.value.append((operation, points))

    def moveTo(self, p):
        self.record("moveTo", (p,))

    def lineTo(self, p):
        self.record("lineTo", (p,))

    def curveTo(self, *p):
        self.record("curveTo", p)

    def qCurveTo(self, *p):
        self.record("qCurveTo", p)

    def closePath(self):
        self.record("closePath", ())

    def endPath(self):
        self.record("endPath", ())

    def addComponent(self, name, transform):
        if name in self.stack or len(self.stack) >= 32:
            raise BundleError("INVALID_COMPONENT")
        self.stack.append(name)
        try:
            super().addComponent(name, transform)
        finally:
            self.stack.pop()


def normalize(value):
    if value is None or type(value) is str:
        return value
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 2**31:
        raise BundleError("INVALID_OUTLINE")
    return int(value) if value == int(value) else value


class Fingerprints:
    def __init__(self, font):
        self.glyphset = font.getGlyphSet()
        self.cache = {}
        self.operations = 0

    def get(self, name):
        if name not in self.cache:
            try:
                pen = BoundedPen(self.glyphset, name)
                self.glyphset[name].draw(pen)
                self.operations += len(pen.value)
                if self.operations > 1_000_000:
                    raise BundleError("OUTLINE_LIMIT")
                self.cache[name] = sha(canonical(normalize(pen.value)))
            except BundleError:
                raise
            except Exception:
                raise BundleError("INVALID_OUTLINE") from None
        return self.cache[name]
