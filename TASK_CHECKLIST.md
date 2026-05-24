# Telomere Checklist

This checklist tracks the current v1 hardening surface. The canonical details
live in `docs/`.

## Done In Current v1 Direction

- [x] Replace active 3-byte file header with 40-byte `.tlmr` v1 header.
- [x] Record hasher kind in the file format.
- [x] Record Lotus preset/version in the file format.
- [x] Record layer count and lengths so v1 decoding is unambiguous.
- [x] Make v1 output one-layer-decodable only.
- [x] Keep arity `2` as a valid compressed arity.
- [x] Reject non-byte-aligned seed payloads during `.tlmr` decode.
- [x] Add config validation for core format limits.
- [x] Remove slow max-seed-len-3 defaults from normal test paths.
- [x] Delete broken fuzz crate targets.
- [x] Mark GPU as research-only while keeping `--features gpu` buildable.
- [x] Remove gloss and bloom stubs.
- [x] Remove disabled gloss binaries.
- [x] Delete `error.log` and ignore future logs.
- [x] Generate `docs/RESULTS.md` and `docs/results.json` from a script.

## Still Research, Not Production Claims

- [ ] Real GPU/OpenCL acceleration.
- [ ] Recursive multi-pass `.tlmr` format and decoder.
- [ ] Large-scale performance artifacts beyond the small generated mechanism
      checks.
- [ ] Consolidation or removal of research hash-table tools.
- [ ] Backward compatibility policy for any pre-v1 experimental files.

## Required Release Gates

- [ ] `cargo fmt --all -- --check`
- [ ] `cargo clippy --all-targets -- -D warnings`
- [ ] `cargo test --all-targets`
- [ ] `cargo check --features gpu --all-targets`
- [ ] `python scripts/doc_lint.py`
