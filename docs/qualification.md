# Qualification provenance and reproduction

Development version: 0.1.0. This records the qualified toolchain and reproducible validation commands.

The qualified environment is CPython 3.13.18, Linux x64, glibc 2.36, fontTools 4.68.0, Brotli 1.2.1 and Debian HarfBuzz 6.0.0 (`libharfbuzz-bin` / `libharfbuzz0b` version `6.0.0+dfsg-3`). CI uses the public Python Bookworm base pinned to `sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f` and installs the explicit dependencies before running tests as UID1000 with empty capability sets and no-new-privileges.

The resolved runtime hashes are in requirements.lock. They describe the resolved platform artifacts, not invented hashes for every distribution. Installation on another architecture may fail closed on the hash constraint. Resolve and review a separate platform lock rather than disabling verification silently. Actual resolved build-tool hashes are separately pinned in `requirements-build.lock`: setuptools84.2.1, wheel0.48.0 and packaging26.3. The build backend versions in `pyproject.toml` match this tooling.

An independent synthetic-font probe uses literal metrics: fi/ligation=550, separate f/i=300+300, precomposed and decomposed Aacute=600, and AA kerning=560+600. Offsets and vertical advances were zero. The package fixture and tests are original implementations. The tests carry literal oracles and exercise real tools; the independent probe also checks GPOS kerning and missing-character rejection.

Runtime admission checks Python 3.13/Linux and exact fontTools, Brotli and hb-shape versions. It records actual Python patch and libc versions. Patch/libc provenance differences make replay manifests differ. Qualification is not automatically transferred to a different toolchain merely because installation succeeds.

Reproduce after preparing dependencies:

```sh
python -m unittest discover -s tests
python -m corpus_font_bundle demo --assert --json
```

Tests require the real native utility. They cover the exact original nine/subset eight glyph contract, four required cases plus GPOS, WOFF2 decode/replay, missing Ω, malicious GSUB/GPOS/outline candidates, pairwise deterministic artifacts, immutable originals, no-replace publication, FIFO/symlink admission, bounded output, cancellation, ignored SIGCHLD and offline wheel installation. No tests or demo download packages.

## Primary references

- FontTools subsetting options: https://fonttools.readthedocs.io/en/latest/subset/index.html
- FontTools WOFF2 API: https://fonttools.readthedocs.io/en/latest/ttLib/woff2.html
- Maintained decomposing pens: https://fonttools.readthedocs.io/en/latest/pens/recordingPen.html
- HarfBuzz utilities: https://harfbuzz.github.io/utilities.html
- OS/2 embedding flags: https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype
- WOFF2 Recommendation, 2024-08-08: https://www.w3.org/TR/2024/REC-WOFF2-20240808/

Qualification exercised installed FontBuilder/feaLib APIs. This project does not assert complete implementation of the standards behind those libraries.
