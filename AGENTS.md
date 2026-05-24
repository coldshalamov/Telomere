# Telomere - Agent Conventions

## Project Overview

Telomere is an experimental stateless lossless generative compression prototype.
The active `.tlmr` v1 writer emits one-layer-decodable files only. Each
compressed record stores a Lotus `(arity, seed)` pair whose selected hasher
expansion reproduces the original bytes; unmatched bytes are literal records.

Canonical docs:

- `docs/ARCHITECTURE.md`
- `docs/FORMAT.md`
- `docs/RESULTS.md`
- `docs/RELEASE_CHECKLIST.md`

## Architecture Map

| Module | Purpose |
| --- | --- |
| `src/hasher.rs` | `SeedExpander` trait plus BLAKE3/SHA-256 implementations |
| `src/seed.rs` | rayon-parallel brute-force seed search |
| `src/seed_index.rs` | canonical index-to-seed bijection |
| `src/header.rs` | Lotus record codec, arity 1-5 plus literal 0xFF |
| `src/tlmr.rs` | 40-byte `.tlmr` v1 header |
| `src/compress.rs` | one-layer compression and run summaries |
| `src/config.rs` | runtime config and validation |
| `src/lib.rs` | public API and decompression |
| `src/main.rs` | supported `telomere` CLI |

## Critical Constraints

- Seed enumeration order is consensus-critical: 1-byte seeds first, then 2-byte,
  then 3-byte, each bucket in big-endian order.
- Lotus arity 2 is valid. It is not reserved.
- Literal marker is `0xFF`.
- `.tlmr` v1 header is 40 bytes and records hasher kind, Lotus preset, layer
  count, lengths, and output hash.
- `.tlmr` v1 seed payloads must be byte-aligned.
- `.tlmr` v1 `layer_count` is always `1`; do not emit recursive output without
  a new format version and decoder support.
- The header-selected hasher is authoritative during decompression.

## Test And Performance Rules

- Use `max_seed_len = 1` in normal unit and integration tests.
- Do not add ignored tests to make `cargo test --all-targets` look green.
- Seed depth 2 is slow-ish; seed depth 3 is expensive.
- Random data is expected to bloat, not compress.
- Negative delta claims must come from generated artifacts or planted/structured
  test data.

## Removed From Active Architecture

- gloss tables and gloss binaries
- bloom filter stubs
- broken fuzz crate targets
- the old active 3-byte file header
- speculative recursive convergence claims

## Verification Before Completion

Run these gates after protocol or docs changes:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/doc_lint.py
```
