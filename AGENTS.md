# Telomere - Agent Conventions

## Project Overview

Telomere is an experimental stateless lossless generative compression prototype.
The `.tlmr` v1 writer emits one-layer-decodable files only. The indexed
`.tlmr` v2 writer supports recursive layers with explicit descriptors. Each
compressed record stores a seed span whose selected hasher expansion reproduces
the original bytes; unmatched bytes are literal records.

Canonical docs:

- `docs/ARCHITECTURE.md`
- `docs/FORMAT.md`
- `docs/RESEARCH_PROGRAM.md`
- `docs/RESULTS.md`
- `docs/RELEASE_CHECKLIST.md`

## Architecture Map

| Module | Purpose |
| --- | --- |
| `src/hasher.rs` | `SeedExpander` trait plus BLAKE3/SHA-256 implementations |
| `src/seed.rs` | rayon-parallel brute-force seed search |
| `src/seed_index.rs` | canonical index-to-seed bijection |
| `src/header.rs` | Lotus record codec, arity 1-5 plus literal (J1D1 value 5 on the wire) |
| `src/tlmr.rs` | `.tlmr` v1 header: 5-byte `TLMR` magic + version prefix followed by a Lotus bit stream that carries header fields and records |
| `src/tlmr_v2.rs` | `.tlmr` v2 recursive header, descriptors, and records |
| `src/seed_expansion_index.rs` | exact generated-prefix seed expansion index |
| `src/indexed.rs` | indexed v2 compression and span selection |
| `src/streaming.rs` | CPU stratified target-span streaming matcher |
| `src/compress.rs` | one-layer compression and run summaries |
| `src/config.rs` | runtime config and validation |
| `src/lib.rs` | public API and decompression |
| `src/main.rs` | supported `telomere` CLI |

## Critical Constraints

- Seed enumeration order is consensus-critical: 1-byte seeds first, then 2-byte,
  then 3-byte, each bucket in big-endian order.
- Lotus arity 2 is valid. It is not reserved.
- The literal marker on the wire is Lotus J1D1 value `5` (6 bits in J1D1's
  largest tier). `0xFF` is an internal in-memory `DecodedHeader.arity` sentinel
  only; it never appears on the wire.
- `.tlmr` v1 is a 5-byte raw `TLMR` magic + version prefix followed by a single
  Lotus bit stream. The bit stream carries hasher kind, Lotus preset, layer
  count, lengths, and output hash, then the records payload. The total
  on-disk size is variable, not a fixed 40-byte header.
- `.tlmr` v1 compressed records encode the canonical seed index via the Lotus
  J3D2 tiered integer codec (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`). The codec
  is provided by the sibling crate at `../lotus/src/lib.rs`.
- `.tlmr` v1 `layer_count` is always `1`; recursive output must use `.tlmr` v2.
- Indexed lookup must compare `expand(seed)[0..span_len]` to target spans, never
  `hash(target_span)` to `hash(seed)`.
- Indexed compression groups active spans into equal-length tiers before lookup.
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
- digest-prefix hash-table tools that implied `hash(block) == hash(seed)` matching
- placeholder `lotus_core` exports
- Kolyma-as-spec source prologues; `kolyma.pdf` is a symbolic corpus only

## Verification Before Completion

Run these gates after protocol or docs changes:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/doc_lint.py
```
