# Design — development 0.1.0

## Pipeline and trust boundaries

1. Validate every public option and case before native work. Snapshot a no-follow regular source file with bounded reads. FIFOs are rejected by metadata before open; the subsequent nonblocking, no-follow open is checked against the admitted inode.
2. Parse with fontTools. Reject unsupported tables, missing stable names, nonzero embedding flags, excessive glyph count and missing corpus coverage.
3. Subset a fresh in-memory copy. Explicit options override dangerous defaults: preserve glyph names, fail on missing Unicode, retain `.notdef` outlines, keep substitution closure, retain layout features, retain all name records/locales and disable the optional HarfBuzz repacker.
4. Set fixed head timestamps; save TTF and WOFF2. Decode WOFF2 with fontTools, save that decoded TTF, and actually shape all three fonts sequentially.
5. Compare names, clusters, four position/advance integers and canonical decomposed outline fingerprints. Serialize evidence and mappings canonically. Re-read the source to detect intervening changes.
6. Only then create a marked same-parent staging directory, write and fsync all artifacts, and use Linux `renameat2(RENAME_NOREPLACE)` to publish it. There is no check-then-overwriting-rename fallback.

No handwritten font or shaping parser exists. JSON validation is a narrow interpretation of the qualified hb-shape utility output. FontTools' maintained `DecomposingRecordingPen` expands composite references so numeric component IDs cannot contaminate the fingerprint. Commands and coordinates are serialized in pen order; integer-valued floats and signed zero canonicalize to integers. No geometric tolerance or contour reordering is applied. This is stricter than visual similarity.

## Native process lifetime

A library caller can have threads or an ignored/reaping SIGCHLD handler. Therefore it never directly owns or signals hb-shape. It launches a fixed stdlib-only Python owner with isolated Python mode and a minimal environment. The owner resets SIGCHLD to SIG_DFL before launching its only child. The library never changes caller signal handlers.

The original private stdin pipe is the sole cancellation/lifetime channel. Request text is sent as JSON to the owner, then as bounded UTF-8 stdin to hb-shape using `--text-file=-`; it is never put in an argument or error message. No user executable, native output-file option or shell is accepted. The executable is fixed at `/usr/bin/hb-shape`. stdout and stderr have independent drain descriptors and a combined 256 KiB budget. stderr is discarded, not relayed.

The single-threaded owner arms Linux PDEATHSIG for its own native child only, with a parent-death race check. It does not arm PDEATHSIG against the potentially multithreaded library caller. Parent-process lifetime is instead represented by EOF on the private control pipe.

A five-second monotonic deadline starts before native launch. The owner uses `waitid(WNOWAIT)` for exit observation. On deadline, EOF, excessive output or internal failure it sends TERM, waits 50 ms, sends KILL, and only then reaps. An exited child remains unreaped throughout all authorized signaling, preventing PID reuse. Before Popen the owner captures its own PID; after arming the leaf child's parent-death signal, the child compares getppid against that captured value and exits126 on mismatch, including reparenting before the signal was armed. Normal exit consumes wait status only when output pipes have drained and no cancellation is outstanding. SIGINT/SIGTERM handlers in this isolated owner mark cancellation without raising asynchronous exceptions across a wait/reaped transition. There is no PID-existence probe, `/proc` ownership inference, process-group kill or reap-then-late-kill sequence.

The caller bounds the owner's protocol and closes its original control pipe on trouble. It has no numeric-PID fallback for the owner. Kernel uninterruptible sleep, filesystem stalls, interpreter failure or external interference can prevent timely reaping; the application deadline is not an OS execution sandbox. No global signal policy is installed to work around this.

## Publication and recovery

Staging names contain random ownership tokens; those tokens are not part of the deterministic manifest. Cleanup requires a matching marker, the original directory inode and only the three allowed regular artifact files. It never recursively traverses a tree. `recoverStage` addresses one explicit stage, does not scan directories and refuses unknown entries or missing markers. A crash between marker removal and rename can leave an unmarked orphan that recovery intentionally refuses. Published bundles have exactly three files and no staging marker.

Atomic visibility is distinct from power-loss durability: directory and file fsyncs are attempted, but storage hardware, filesystem behavior and an I/O failure after successful rename can leave a visible bundle while the caller receives the distinct `PUBLISHED_IO_ERROR` outcome. Differential-check failures occur before staging and cannot publish. A hostile same-user process can forge markers or race filesystem operations; markers are an accident-prevention mechanism, not an authorization boundary. Use trusted local working/output directories.

## Determinism and licensing

Identical input bytes, cases and qualified tool versions produce canonical manifests and matching TTF/WOFF2 hashes. Timestamp repair never modifies caller bytes. The manifest includes actual tool versions, so a different Python patch or libc is not silently treated as identical replay provenance.

All original name records, including IDs 13/14 and other locales, are retained and compared by a canonical digest of their raw records. OS/2 fsType is not cleared. Version 0.1.0 conservatively rejects any nonzero value. Applications must separately establish redistribution rights even when fsType is zero.

## Resource model

Application byte, corpus, case and post-parse glyph bounds are supplemented by 100,000 pen operations per shaped glyph, 1,000,000 operations per font's fingerprint cache, depth 32 for components, cycle detection, bounded manifests and bounded native output. Decoders and layout engines may allocate or perform significant work before these limits are inspected. Font parsing and Python pen work have no hard wall-clock sandbox. External isolation is needed for hostile font services.
