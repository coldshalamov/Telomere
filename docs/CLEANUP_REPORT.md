# Cleanup Report

Generated for the canonical-format cleanup ending 2026-06-06.

## Phase Log

- Phase 1 commit: `77592f7` (`Align v1 record format with canonical spec`).
  - Replaced the v1 arity J1D1 record prefix with the canonical prefix-free alphabet.
  - Kept arity 1 and 2 at 2 bits, changed arity 3/4/5 and literal to 3-bit prefixes.
  - Changed the v1 seed index preset to J3D1 after confirming the sibling `../lotus` crate exposes that layout as `(J_BITS=3, TIERS=1)`.
  - Updated v1 record encoding, decoding, bit-length accounting, exports, `docs/FORMAT.md`, and golden tests.
  - Added native golden round-trip coverage for empty, 1 byte, partial-final-block, planted, and random files.
- Phase 2: skipped by instruction.
- Phase 3 manifest commit: `162a550` (`Inventory cleanup candidates`).
- Phase 3 cleanup commit: `eafa25e` (`Archive approved cleanup artifacts`).
- Phase 4 commit: `c79912d` (`Remeasure corrected format controls`).
  - Re-ran the bounded results generator only: `python scripts/generate_results.py`.
  - Moved generated machine JSON output from direct `docs/results.json` to ignored `target/generated-docs/results.json`; `docs/RESULTS.md` remains the committed evidence summary.
  - Updated two generated case notes whose old expected direction contradicted the corrected format measurements.
- Phase 5: this report plus two verification cleanups.
  - Removed a redundant `Ok(...?)` wrapper in `src/header.rs`.
  - Replaced a manual modulo padding check in `tests/full_roundtrip_audit.rs` with `is_multiple_of(8)` for Rust 1.94 clippy.

## Removed Or Archived

Local, not git:

- `target/`: cleaned with `cargo clean`; 43,410 files, 11,406,011,920 bytes.
- `src-tauri/target/`: cleaned with `cargo clean --manifest-path src-tauri/Cargo.toml`; 7,421 files, 3,339,537,476 bytes.
- `scripts/__pycache__/`: removed local cache; 107 files, 3,622,771 bytes.
- `.serena/cache/`: removed local cache; 1 file, 508,641 bytes.
- Total bytes reclaimed at cleanup time: 14,749,680,808 bytes. Later verification rebuilt `target/`.

`git rm`:

- `docs/candidate_runtime_verification/01-cargo-fmt-all-check.txt` through `10-python-scripts-generate-research-ledgers-py-check.txt`: generated verification transcripts, recoverable by rerunning the commands.

`git mv` to `docs/_archive/`:

- `.agent/brain/DECISIONS.md`, `MISTAKES.md`, `NEXT.md`, `PLAN.md`, `PROJECT.md`, `QUESTIONS.md`: archived agent state/provenance notes.
- `docs/agent_prompts/*.prompt.txt`: archived superseded prompt artifacts.
- `docs/agent_reports/manifest.json` and `docs/agent_reports/report_templates.json`: archived generated agent-report metadata.

Held:

- `docs/research_artifacts_snapshot.json`: kept. `src-tauri/src/main.rs` reads it at runtime via `load_research_artifacts_from_docs` before falling back to raw artifact files.
- `docs/source_family_cross_validation.json`: kept as-is.
- `scripts/doc_lint.py`: not touched.
- No commit in the provenance list was reverted.

## Format Sizes

- v1 arity prefix after Phase 1:
  - `00` = arity 1, `01` = arity 2.
  - `100` = arity 3, `101` = arity 4, `110` = arity 5.
  - `111` = literal marker.
- Literal marker width changed from 6 bits to 3 bits.
- Smallest compressed v1 record is now 7 bits: arity 1 prefix (2 bits) plus J3D1 seed index 0 (5 bits), pinned as packed byte `0x06`.
- v1 literal marker is now pinned as packed byte `0xe0`.
- Typical v1 header golden remains 18 bytes; typical v2 header golden remains 14 bytes.

## Phase 4 Measurements

Case matrix manifest after the generator-note correction: `41bd7a863c019c91d4ced1dbede08e209b38efc131859de77f8d7aba261c0a9c`.

| case | before | after | change |
| --- | ---: | ---: | ---: |
| deterministic-bytes | 64 -> 120 (+56, +87.50%) | 64 -> 100 (+36, +56.25%) | 20 bytes less bloat |
| planted-sha256-arity2 | 256 -> 168 (-88, -34.38%) | 256 -> 76 (-180, -70.31%) | 92 bytes better |
| streaming-planted-span4-control | 1024 -> 1107 (+83, +8.11%) | 1024 -> 411 (-613, -59.86%) | now emits compact fixed-span records |
| indexed-planted-span8 | 1024 -> 720 (-304, -29.69%) | 1024 -> 379 (-645, -62.99%) | 341 bytes better |
| streaming-planted-span8 | 1024 -> 720 (-304, -29.69%) | 1024 -> 379 (-645, -62.99%) | 341 bytes better |
| streaming-planted-span12 | 1020 -> 505 (-515, -50.49%) | 1020 -> 261 (-759, -74.41%) | 244 bytes better |
| streaming-random-null-1k | 1024 -> 1107 (+83, +8.11%) | 1024 -> 1055 (+31, +3.03%) | 52 bytes less bloat |
| streaming-planted-density10 | 1024 -> 1068 (+44, +4.30%) | 1024 -> 986 (-38, -3.71%) | crossed break-even |
| streaming-planted-density50 | 1024 -> 915 (-109, -10.64%) | 1024 -> 719 (-305, -29.79%) | 196 bytes better |
| streaming-planted-offset1 | 1025 -> 1108 (+83, +8.10%) | 1025 -> 1056 (+31, +3.02%) | 52 bytes less bloat |
| streaming-recursive-offset-pass2 | 1025 -> 759 (-266, -25.95%) | 1025 -> 1056 (+31, +3.02%) | current path stops after non-compressive first layer |
| streaming-structured-json-control | 6814 -> 6897 (+83, +1.22%) | 6814 -> 6846 (+32, +0.47%) | 51 bytes less bloat |
| kolyma-pdf-streaming-control | 2602639 -> 2602839 (+200, +0.01%) | 2602639 -> 2602871 (+232, +0.01%) | 32 bytes more bloat |

Notes:

- The planted and most control cases improved under the corrected accounting.
- `kolyma-pdf-streaming-control` is the one control exception in this bounded rerun: it still selected zero spans and bloated only by +0.01%, but by 32 bytes more than before.
- `python scripts/generate_viability.py` was attempted and stopped with `FileNotFoundError: docs/sweeps.json`. Rehydrating the broad missing artifact set was not done because the cleanup instructions forbid broad new searches or matrix regeneration outside the requested generator path.

## Invariants And Tests

- Golden tests pin the 3-bit literal marker and 7-bit arity-1/J3D1 seed record.
- `tests/full_roundtrip_audit.rs::canonical_golden_roundtrips` verifies byte-exact round trips, matching hashes, file-length identity, decode halt at `original_len`, and zero trailing pad behavior across the required fixture classes.
- `cargo test --all-targets` passed before Phase 1, after Phase 1, after Phase 3 manifest, after Phase 3 cleanup, and after Phase 4.
- Final Phase 5 verification passed:
  - `cargo fmt --all -- --check`
  - `cargo clippy --all-targets -- -D warnings`
  - `cargo test --all-targets`
  - `cargo check --features gpu --all-targets`
  - `python scripts/doc_lint.py`
  - `python scripts/generate_results.py --check`

## Open CONFIRM Items

- `docs/FORMAT_CANONICAL.md` Section 7 still contains the v1/v2 unification `[CONFIRM]`. Phase 2 was explicitly skipped, so this remains open and was not guessed.
