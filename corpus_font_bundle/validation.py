import json
import os
import re

from .errors import BundleError

FONT_LIMIT = 16 * 1024 * 1024
CORPUS_LIMIT = 16_384
CASE_LIMIT = 64
MANIFEST_LIMIT = 4 * 1024 * 1024
GLYPH_LIMIT = 4096
TAG = re.compile(r"[A-Za-z][A-Za-z0-9]{3}\Z", re.ASCII)
LANGUAGE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z", re.ASCII)
SCRIPT = re.compile(r"[A-Za-z]{4}\Z", re.ASCII)


def text(value, *, limit=CORPUS_LIMIT):
    if type(value) is not str or not value or len(value) > limit or "\0" in value:
        raise BundleError("INVALID_TEXT")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError:
        raise BundleError("INVALID_TEXT") from None
    return value


def path(value):
    try:
        value = os.fspath(value)
    except TypeError:
        raise BundleError("INVALID_PATH") from None
    if type(value) is not str or not value or "\0" in value or ".." in value.split("/"):
        raise BundleError("INVALID_PATH")
    return value


def options(value):
    if type(value) is not dict or set(value) != {"destination"}:
        raise BundleError("INVALID_OPTIONS")
    return path(value["destination"])


def cases(corpus, value):
    text(corpus)
    if type(value) is not list or not 1 <= len(value) <= CASE_LIMIT:
        raise BundleError("INVALID_CASES")
    result = []
    total = 0
    available = set(corpus)
    for case in value:
        if type(case) is not dict or set(case) != {"text", "language", "direction", "script", "features"}:
            raise BundleError("INVALID_CASES")
        content = text(case["text"])
        total += len(content)
        if total > CORPUS_LIMIT or any(ord(c) < 32 or ord(c) == 127 for c in content):
            raise BundleError("INVALID_CASES")
        if not set(content) <= available:
            raise BundleError("CASE_OUTSIDE_CORPUS")
        language = case["language"]
        script = case["script"]
        if type(language) is not str or len(language) > 63 or not LANGUAGE.fullmatch(language):
            raise BundleError("INVALID_CASES")
        if type(script) is not str or not SCRIPT.fullmatch(script):
            raise BundleError("INVALID_CASES")
        if type(case["direction"]) is not str or case["direction"] not in ("ltr", "rtl"):
            raise BundleError("INVALID_CASES")
        features = case["features"]
        if type(features) is not dict or len(features) > 32:
            raise BundleError("INVALID_FEATURES")
        for key, val in features.items():
            if type(key) is not str or not TAG.fullmatch(key) or type(val) is not int or not 0 <= val <= 65535:
                raise BundleError("INVALID_FEATURES")
        result.append({"text": content, "language": language, "direction": case["direction"],
                       "script": script, "features": dict(sorted(features.items()))})
    return result


def _pairs(items):
    result = {}
    for key, val in items:
        if key in result:
            raise ValueError("duplicate")
        result[key] = val
    return result


def parse_json(data):
    try:
        return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    except (UnicodeError, ValueError, RecursionError):
        raise BundleError("INVALID_JSON") from None


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")
