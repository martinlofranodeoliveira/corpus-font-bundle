import base64
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

from .errors import BundleError
from .validation import canonical, parse_json

OWNER_LIMIT = 384 * 1024


def native(request):
    owner = Path(__file__).with_name("_owner.py")
    try:
        process = subprocess.Popen([sys.executable, "-I", str(owner)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True, close_fds=True,
                                   env={"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8"})
    except OSError:
        raise BundleError("NATIVE_OWNER_FAILED") from None
    selector = selectors.DefaultSelector()
    output = bytearray()
    failure = None
    try:
        process.stdin.write(canonical(request))
        process.stdin.flush()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 8
        cancelled = False
        while selector.get_map():
            if time.monotonic() >= deadline:
                if cancelled:
                    failure = "NATIVE_OWNER_FAILED"
                    break
                process.stdin.close()  # Sole authorization channel; never signal an owner PID.
                cancelled = True
                deadline = time.monotonic() + 2
            for key, _ in selector.select(0.05):
                block = os.read(key.fd, 65536)
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    output.extend(block)
                    if len(output) > OWNER_LIMIT:
                        failure = "NATIVE_OWNER_FAILED"
                        break
            if failure:
                break
    except (OSError, ValueError):
        failure = "NATIVE_OWNER_FAILED"
    finally:
        selector.close()
        process.stdin.close()
        process.stdout.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            # Do not introduce an unsafe numeric-PID fallback. The closed private
            # pipe cancels this fixed owner; a stuck OS syscall is not sandboxed.
            failure = "NATIVE_OWNER_FAILED"
    if failure:
        raise BundleError(failure)
    response = parse_json(bytes(output))
    if type(response) is not dict or type(response.get("ok")) is not bool:
        raise BundleError("NATIVE_PROTOCOL")
    if not response["ok"]:
        allowed = {"NATIVE_TIMEOUT", "NATIVE_OUTPUT_LIMIT", "NATIVE_CANCELLED", "NATIVE_PROTOCOL", "NATIVE_FAILED", "NATIVE_OWNER_FAILED"}
        code = response.get("code")
        raise BundleError(code if code in allowed else "NATIVE_PROTOCOL")
    try:
        return base64.b64decode(response["stdout"], validate=True)
    except (KeyError, ValueError, TypeError):
        raise BundleError("NATIVE_PROTOCOL") from None


def shape(font_path, case, fingerprints):
    value = parse_json(native({"action": "shape", "font": str(font_path), "case": case}))
    if type(value) is not list or len(value) > 16_384:
        raise BundleError("INVALID_SHAPE_OUTPUT")
    result = []
    for glyph in value:
        if type(glyph) is not dict or set(glyph) != {"g", "cl", "dx", "dy", "ax", "ay"}:
            raise BundleError("INVALID_SHAPE_OUTPUT")
        name = glyph["g"]
        if type(name) is not str or name == ".notdef" or name not in fingerprints.glyphset:
            raise BundleError("INVALID_SHAPE_OUTPUT")
        for key in ("cl", "dx", "dy", "ax", "ay"):
            if type(glyph[key]) is not int or abs(glyph[key]) > 2**31 - 1:
                raise BundleError("INVALID_SHAPE_OUTPUT")
        if not 0 <= glyph["cl"] <= len(case["text"].encode("utf-8")):
            raise BundleError("INVALID_SHAPE_OUTPUT")
        result.append({**glyph, "outline": fingerprints.get(name)})
    return result
