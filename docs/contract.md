# Public contract — development 0.1.0

This document defines the supported subset, not broad OpenType/WOFF2 conformance.

## Python API

```python
buildBundle(font, corpus, shapingCases, options) -> dict
verifyBundle(font, bundle) -> dict
recoverStage(stage) -> {'removed': True}
```

Paths are strings or string-valued `os.PathLike` objects. No NUL, byte paths or `..` components. All directory components are opened without following symlinks. Parent directories must already exist. Inputs must be regular files, not symlinks, devices, sockets or FIFOs. The filesystem must support Linux no-replace directory rename. Source and output directories must be trusted local locations.

`options` is a plain dict with exactly `destination`, a new bundle directory path. No timeout, executable, parser, feature-filter, filename or resource-limit overrides exist. Unknown options are errors. Boolean feature values are not integers for this API.

`corpus` is a nonempty Unicode string, strict UTF-8 encodable, NUL-free, at most 16,384 code points. Its exact encoding is hashed; no NFC/NFD conversion, trimming or newline removal occurs. Every corpus character requires a non-.notdef best-cmap mapping, including spaces and control characters if supplied. Missing characters return `MISSING_CHARACTER` and a count of distinct missing code points, never silently substituted glyphs.

`shapingCases` is a plain list of 1–64 plain dicts, each with exactly:

- `text`: nonempty, strict UTF-8, all characters drawn from the corpus; C0 controls and DEL are prohibited. Sum of all case text lengths is at most 16,384 code points. Repetition need not match corpus occurrence counts.
- `language`: 2–8 ASCII letters followed by zero or more hyphen-separated 1–8 ASCII alphanumeric subtags; maximum 63 characters. This is an allowlisted language-tag subset, not a general BCP 47 validator.
- `script`: four ASCII letters, passed explicitly to HarfBuzz.
- `direction`: `ltr` or `rtl` only.
- `features`: plain dict, at most 32 four-character ASCII tags matching `[A-Za-z][A-Za-z0-9]{3}`, each with an integer value 0–65535. An empty dict explicitly selects HarfBuzz defaults. Tags not supplied retain HarfBuzz defaults. Ranges, alternate shapers and arbitrary utility switches are unsupported.

One static TrueType face with `glyf`, `loca`, `head`, `maxp`, `hmtx`, `cmap`, `post`, `name` and `OS/2` is required. Post format 2 names must be stable and unique. Collections, CFF/CFF2, variable, color and embedded bitmap tables listed in `fonts.FORBIDDEN` are refused. Unknown ancillary tables are subject to fontTools' subset behavior, not a preservation guarantee. fsType must be exactly zero. This does not establish legal permission.

Source and each binary artifact are limited to 16 MiB. Glyph count is inspected after parsing and must be 1–4,096. These are not decoder-allocation guarantees. Manifest size is at most 4 MiB. Fingerprints additionally have operation, depth and coordinate limits described in design.md.

## Artifacts and replay

The destination contains exactly `bundle.ttf`, `bundle.woff2`, `manifest.json`. Canonical JSON uses sorted keys, UTF-8, no insignificant spacing, a final LF and no duplicate keys or non-finite values. Schema identifier: `corpus-font-bundle/1`. No source path is recorded. The manifest contains:

- exact corpus and UTF-8 digest; original source digest;
- tool versions, development version, original/subset counts;
- artifact SHA-256 hashes;
- retained name-record digest and fsType;
- stable-name/original-GID/subset-GID mapping in subset order;
- ordered cases with exact parameters and original/TTF/decoded-WOFF2 results.

Each glyph result has `g`, `cl`, `dx`, `dy`, `ax`, `ay`, `outline`. The first six fields come from hb-shape JSON; `outline` is SHA-256 of canonical component-expanded pen commands. Numeric GIDs are recorded only as mappings, never used as identity. A .notdef shaped result is refused. All supplied cases must match exactly across original, candidate TTF and decoded WOFF2, including clusters. No coverage of untested text, features, scripts or engines is implied. No pixel rendering or hinting equivalence is claimed.

TTF and decoded WOFF2 head timestamps are fixed to 2082844800 in the TrueType epoch. All source name records and fsType are checked unchanged. Layout closure and all supported layout feature tables are retained by fontTools, but only supplied behavior is qualified.

`buildBundle` returns the manifest after no-replace publication. All differential checks precede staging. Input is never written; its bytes are read again before publication. Concurrent external mutation after that check is outside the transaction. Existing destinations are never overwritten. `PUBLISHED_IO_ERROR` means rename already committed and a later synchronization/close operation failed: the complete destination remains visible, and the caller can replay it with `verifyBundle`. Validation failures before that commit publish no bundle.

`verifyBundle` requires the original font, re-admits every artifact with no-follow reads, decodes WOFF2 again, performs real shaping again and reconstructs the entire manifest. Exact canonical bytes must match, not merely selected hashes. Exact recorded runtime provenance must match current provenance. Verification does not repair or modify a bundle and does not authenticate its publisher; SHA-256 is integrity evidence, not a signature.

Recovery accepts only one explicit marked staging directory with the expected token and allowed flat regular contents. It does not remove published bundles or unmarked leftovers.

## Errors and CLI

`BundleError.code` and optional `count` are sanitized. `as_dict()` is machine-readable. Stable categories include:

- Validation: `INVALID_OPTIONS`, `INVALID_PATH`, `INVALID_TEXT`, `INVALID_CASES`, `INVALID_FEATURES`, `CASE_OUTSIDE_CORPUS`, `INVALID_JSON`.
- Admission: `NOT_REGULAR_FILE`, `INPUT_LIMIT`, `INPUT_CHANGED`, `UNSUPPORTED_FONT`, `INVALID_FONT`, `GLYPH_LIMIT`, `STABLE_NAMES_REQUIRED`, `FONT_RESTRICTED`, `MISSING_CHARACTER`.
- Replay: `UNQUALIFIED_TOOLCHAIN`, `TOOLCHAIN_MISMATCH`, `INVALID_WOFF2`, `INVALID_SHAPE_OUTPUT`, `INVALID_OUTLINE`, `INVALID_COMPONENT`, `OUTLINE_LIMIT`, `METADATA_CHANGED`, `GLYPH_MAPPING_CHANGED`, `TIMESTAMP_CHANGED`, `SHAPING_CHANGED`.
- Native boundary: `NATIVE_TIMEOUT`, `NATIVE_OUTPUT_LIMIT`, `NATIVE_CANCELLED`, `NATIVE_PROTOCOL`, `NATIVE_FAILED`, `NATIVE_OWNER_FAILED`.
- Publication/verification: `OUTPUT_LIMIT`, `MANIFEST_LIMIT`, `DESTINATION_EXISTS`, `INCOMPLETE_STAGE`, `ATOMIC_PUBLICATION_UNAVAILABLE`, `ATOMIC_PUBLICATION_FAILED`, `PUBLISHED_IO_ERROR`, `UNOWNED_STAGE`, `RECOVERY_FAILED`, `INVALID_BUNDLE`, `INVALID_MANIFEST`, `MANIFEST_MISMATCH`.
- Sanitized fallback categories: `IO_ERROR`, `BUILD_FAILED`, `VERIFY_FAILED`; demo oracle failure: `DEMO_ORACLE_FAILED`.

Unsupported or corrupt fonts can be refused in more than one category depending on the first failing inspection. Raw parser/native exceptions are not public API. No source text/path is included in application errors.

CLI commands are `build`, `verify`, `recover`, `demo`. Build corpus files are at most 65,536 UTF-8 bytes; case JSON files at most 128 KiB. Application success uses exit 0 and JSON stdout (demo defaults to human output); application failure uses exit 1 and JSON stderr. Argparse syntax errors use exit 2 and ordinary usage text. `demo --assert --json` is the offline machine-readable oracle entry point.
