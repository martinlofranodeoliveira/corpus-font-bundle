# Security policy

## Reporting

Use GitHub private vulnerability reporting:

https://github.com/martinlofranodeoliveira/corpus-font-bundle/security/advisories/new

Do not put exploit fonts, sensitive corpus text, personal information or credentials in public issues. General contact is through https://lofranotecnologia.com.br . No response-time commitment is specified.

## Scope and limitations

Development 0.1.0 processes font formats using fontTools, Brotli and native HarfBuzz. Byte/glyph/corpus/output limits are application safeguards, not a native decoder sandbox. Parsing can allocate before glyph count inspection, and Python parsing/outline work has no hard execution deadline. Use additional external isolation for untrusted-font services.

Only trusted local source/output directories are supported. No-follow opens and marked cleanup reduce accidental traversal and deletion; markers do not defend against a hostile same-user process. The output parent must support Linux no-replace directory rename. Publication visibility is atomic. A post-rename I/O failure returns `PUBLISHED_IO_ERROR` with the complete destination already visible; power-loss durability is not guaranteed.

The isolated native owner does not replace caller signal handlers. Native cancellation uses the original private pipe; the owner signals only its unreaped child. Uninterruptible kernel operations or external process interference can defeat timely cleanup. There is no unsafe numeric owner-PID kill fallback.

Replay establishes equivalence only for supplied cases and the recorded toolchain. Manifest hashes are not authentication, legal permission or a visual-quality guarantee. All nonzero fsType values are rejected conservatively, and zero still requires independent licensing review. Do not redistribute third-party fonts merely because verification passed.

There is no telemetry, tracking, network service, secret configuration or runtime model/API dependency in this project.
