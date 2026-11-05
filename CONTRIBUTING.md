# Contributing

Corpus Font Bundle is development version 0.1.0. Contributions should keep its contract small, inspectable and corpus-specific. General contact: https://lofranotecnologia.com.br . Use repository issues for non-sensitive bugs and proposals; use SECURITY.md for vulnerabilities.

Prepare the dependencies described in README.md, including local wheel build tooling. Then run:

```sh
python -m unittest discover -s tests
python -m corpus_font_bundle demo --assert
python -m corpus_font_bundle demo --assert --json
```

Tests and library calls must remain offline. Do not add native executable overrides, downloaded fonts, arbitrary shell commands, global signal-handler changes or model/API dependencies. Preserve actual HarfBuzz and WOFF2 tests rather than replacing them with mocks. Test-only boundary substitutions must remain inaccessible to callers.

Add independent literal expectations for synthetic regression fixtures, especially for changed layout behavior. Do not derive expected advances from the implementation under test. Add adversarial rejection tests for new input grammar. Any process-management change must address inherited SIGCHLD, parent EOF, output bounds and the final authorized signal before reaping.

Only original synthetic font data belongs in fixtures. Do not submit private client code, real personal data, credentials or third-party fonts without established redistribution rights. The code license does not relicense fonts passed by users. Never clear fsType to make a test pass.

Keep README.md and README.pt-BR.md aligned, update the precise contract before changing externally observable behavior, and record changes under the unreleased changelog. No publishing or deployment workflow is needed. Build tools may write temporary wheels during tests; generated artifacts do not belong in source contributions.
