# Telomere Architecture

## What Telomere Is Now

Telomere is a Rust prototype for stateless lossless generative compression. The
active compressor:

- splits input into fixed-size byte blocks
- searches canonical seed space in length-first, big-endian order
- expands candidate seeds with BLAKE3 XOF or SHA-256
- accepts a candidate only when the Lotus record is smaller than the original
  span
- emits literal records for everything else
- writes a `.tlmr` v1 header that carries all decoding metadata

The production path is CPU/rayon. The GPU API is research-only and currently
uses deterministic CPU fallback semantics even when `--features gpu` is enabled.

## Main Modules

| Module | Role |
| --- | --- |
| `src/config.rs` | Runtime config and validation |
| `src/hasher.rs` | BLAKE3 and SHA-256 seed expansion |
| `src/seed.rs` | Canonical brute-force seed search |
| `src/seed_index.rs` | Seed index to seed bijection |
| `src/header.rs` | Lotus record encode/decode |
| `src/tlmr.rs` | `.tlmr` v1 file header |
| `src/compress.rs` | One-layer compression and run summary |
| `src/lib.rs` | Public API and decompression |
| `src/main.rs` | Supported `telomere` CLI |
| `src/bundler.rs` | Greedy non-overlapping span selection |
| `src/superposition.rs` | Candidate collection before bundling |

## What Lotus Means Here

Lotus is not a general-purpose integer codec in this repo. It is the concrete
4-field record format implemented in `src/header.rs`:

```text
[mode][arity][jumpstarter(3)][len_bits][payload]
```

For `.tlmr` v1:

- arity `1..=5` are compressed span arities
- arity `2` is valid
- literal marker is `0xFF`
- seed payloads must be byte-aligned
- literal records carry no Lotus payload and are followed by raw literal bytes

## Multi-Pass Position

The active `.tlmr` v1 format emits one-layer-decodable files. `--passes` remains
accepted as a compatibility knob, but v1 output records `layer_count = 1` and is
not recursively nested. Recursive compression can return only when a future
format version records enough layer metadata and the decoder actually implements
recursive decode.

## Explicitly Gone

The following are removed from the active architecture:

- old 3-byte active file header
- gloss table stubs
- gloss dump/debug binaries
- bloom filter placeholder
- broken fuzz crate targets
- speculative whitepaper docs that described unimplemented recursive convergence
- claims that ordinary random inputs are expected to shrink

## Research-Only Surface

The following remain research tools or internal diagnostics:

- `--features gpu`
- `src/bin/hash_precompute.rs`
- `src/bin/hash_dump.rs`
- `src/bin/hash_find.rs`
- `src/bin/seed_table.rs`
- `src/bin/block_histogram.rs`
- `src/bin/block_summary.rs`

See [TOOLS.md](TOOLS.md) for the full tool classification.
