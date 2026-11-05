# Corpus Font Bundle

**Development version 0.1.0.** Original open-source software by [Lofrano Tecnologia](https://lofranotecnologia.com.br). [Português](README.pt-BR.md).

Build a TTF/WOFF2 bundle for an explicit Unicode corpus, then independently replay HarfBuzz shaping against the original font. Publication is refused if supplied cases change glyph names, clusters, offsets, advances or component-expanded outline fingerprints. This is evidence about those cases, not about untested text or every renderer.

## Install

Supported execution environment: Linux, CPython 3.13, `/usr/bin/hb-shape` 6.0.0 with the OT shaper, fontTools 4.68.0 and Brotli 1.2.1. See [qualification](docs/qualification.md) for exact pre-source provenance and limits. Runtime code, tests and demo never download dependencies.

On Debian Bookworm, prepare dependencies explicitly before going offline:

```sh
apt-get update
apt-get install --no-install-recommends libharfbuzz-bin=6.0.0+dfsg-3 libharfbuzz0b=6.0.0+dfsg-3
python -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
python -m pip install --only-binary=:all: --require-hashes -r requirements-build.lock
python -m pip install --no-build-isolation --no-deps .
```

System package installation requires the appropriate system administrator. No privileged container is required. The hash lock covers qualified platform-specific runtime artifacts; build tooling is separate and is not represented as reproducibly locked.

## Test and demonstrate

```sh
python -m unittest discover -s tests
python -m corpus_font_bundle demo --assert
python -m corpus_font_bundle demo --assert --json
```

Tests include real native shaping, WOFF2 decoding/replay, adversarial candidates, process cancellation and an offline wheel installation used from outside the checkout. Install `pip`, the tooling pinned in `requirements-build.lock` before running the installation test. No test skips native qualification.

Human-readable example output:

```text
Corpus Font Bundle — development 0.1.0
Glyphs: 9 -> 8; removed: Z
Replay: 5 cases matched original, TTF and decoded WOFF2
Advances: fi=550; f+i=600; Á=600; A+U+0301=600; AA=560+600
Missing Ω: MISSING_CHARACTER (count=1), no bundle
Repeat build: identical
Oracle: PASS
```

JSON output additionally includes computed artifact hashes. All demo inputs are synthetic; output directories are temporary. There are no bundled third-party fonts.

## Library example

```python
from pathlib import Path
from corpus_font_bundle import buildBundle, verifyBundle, BundleError
from corpus_font_bundle.fixture import font_bytes, CORPUS, shaping_cases

source = Path('synthetic.ttf')
source.write_bytes(font_bytes())
try:
    manifest = buildBundle(source, CORPUS, shaping_cases(), {'destination': 'example-bundle'})
    replay = verifyBundle(source, 'example-bundle')
    print(manifest['subset_glyph_count'])  # 8
except BundleError as error:
    print(error.as_dict())
```

The destination must not exist, even if empty. Both functions return the full replay manifest on success and raise sanitized `BundleError` values on failure. The source is opened read-only and checked again before publication.

For CLI use, save exact UTF-8 corpus bytes in `corpus.txt` and an array of case records in `cases.json`:

```json
[{"text":"fi","language":"en","direction":"ltr","script":"Latn","features":{"liga":1,"kern":0}}]
```

```sh
corpus-font-bundle build --font synthetic.ttf --corpus-file corpus.txt --cases-file cases.json --destination font-bundle
corpus-font-bundle verify --font synthetic.ttf --bundle font-bundle
```

Success is JSON on stdout; failures are JSON on stderr with exit code 1. Argument syntax errors use argparse and exit code 2. The CLI never prints source text, source paths or native stderr in application errors.

## Why this design?

Unicode coverage alone misses ligatures and positioning. FontTools supplies maintained parsing, substitution closure, subsetting and WOFF2 support; a separate HarfBuzz executable supplies actual shaping. Stable post names avoid comparing renumbered numeric glyph IDs. Maintained decomposing pens avoid hashing composite references that can renumber. A no-replace directory rename makes the three artifacts visible together only after comparison.

## Boundaries

- One static, non-color TrueType face with format-2 post names; no collections, CFF, variable fonts or font discovery.
- Corpus: at most 16,384 code points. Cases: 1–64, total text at most 16,384 code points, explicit language/script/direction/features. No normalization; `Á` and `A` + U+0301 remain distinct inputs.
- Source and each binary artifact: at most 16 MiB; post-parse glyph count: at most 4,096. Native decoders can allocate before metadata is inspected. This is **not a parser sandbox**.
- Five-second native child deadlines and 256 KiB combined stdout/stderr capture limits. See the signal-ownership design and OS-stall caveat in [design](docs/design.md).
- Conservative licensing admission rejects every nonzero `fsType`. Zero does not grant redistribution rights. All original name records are retained and checked; the MIT code license does not relicense caller fonts.
- No visual quality scoring, standards-wide conformance claim, telemetry, model/API dependency or deployment claim.

Read the precise [contract](docs/contract.md), [design](docs/design.md), [security policy](SECURITY.md) and [contribution guide](CONTRIBUTING.md). Repository: [martinlofranodeoliveira/corpus-font-bundle](https://github.com/martinlofranodeoliveira/corpus-font-bundle).

`PUBLISHED_IO_ERROR` reports an I/O failure after rename committed; the complete bundle is already visible and can be checked with `verifyBundle`. Validation failures before publication leave no bundle.
