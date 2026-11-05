import platform
import sys

import brotli
import fontTools

from .errors import BundleError
from .shaping import native


def versions():
    if sys.platform != "linux" or sys.version_info[:2] != (3, 13):
        raise BundleError("UNQUALIFIED_TOOLCHAIN")
    if fontTools.__version__ != "4.68.0" or brotli.__version__ != "1.2.1":
        raise BundleError("UNQUALIFIED_TOOLCHAIN")
    raw = native({"action": "version"})
    try:
        first = raw.decode("utf-8", "strict").splitlines()[0]
    except (UnicodeError, IndexError):
        raise BundleError("UNQUALIFIED_TOOLCHAIN") from None
    if first != "hb-shape (HarfBuzz) 6.0.0":
        raise BundleError("UNQUALIFIED_TOOLCHAIN")
    libc, libc_version = platform.libc_ver()
    return {"python": platform.python_version(), "fonttools": fontTools.__version__,
            "brotli": brotli.__version__, "harfbuzz": "6.0.0", "shaper": "ot",
            "libc": libc, "libc_version": libc_version}
