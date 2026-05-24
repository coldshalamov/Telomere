# Telomere

Telomere is an experimental, lossless, stateless generative compression
prototype. It splits input into fixed-size blocks, searches deterministic seed
space, and replaces a block span with a shorter Lotus-encoded `(arity, seed)`
record only when the record is smaller than the original span. Blocks that do
not have a compressive seed are emitted as literal records.

Telomere is not a universal compressor. Random or ordinary data usually gets
larger, especially at seed depth 1. Negative delta is expected only on data that
contains planted or naturally recurring spans that are reproduced by short hash
seeds.

## Install

```powershell
cargo build --release
```

The main binary is `telomere`.

## CLI

```text
telomere compress [OPTIONS] <INPUT> <OUTPUT>
telomere decompress [OPTIONS] <INPUT.tlmr> <OUTPUT>
```

Compression options:

```text
--seed-depth <N>       Maximum seed length in bytes, default 1
--passes <N>           Accepted for compatibility, default 1
--checkpoint-every <N> Parsed but checkpointing is not implemented
--memory-limit <LIMIT> Limit syntax: 100%, 4GB, 512MB, 64KB
--hasher <KIND>        blake3 or sha256, default blake3
--verify               Decompress after writing the in-memory result
--json                 Print RunSummary JSON to stdout
--block-size <N>       Block size in bytes, default 4, valid 1..=16
--force                Overwrite an existing output file
```

Decompression options:

```text
--force                Overwrite an existing output file
--hasher <KIND>        Legacy compatibility flag; .tlmr v1 uses the file header
```

Examples:

```powershell
cargo run -- compress input.bin output.tlmr --block-size 4 --seed-depth 1 --json --verify
cargo run -- decompress output.tlmr restored.bin --force
cargo run -- compress planted.bin planted.tlmr --hasher sha256 --block-size 2 --seed-depth 1 --force
```

## File Format

The canonical format reference is [docs/FORMAT.md](docs/FORMAT.md).

Current `.tlmr` files use a fixed 40-byte v1 header followed by byte-aligned
Lotus records. The header records:

- magic bytes `TLMR`
- format version `1`
- Lotus preset version `1`
- hasher kind, `blake3` or `sha256`
- block size and final block size
- maximum seed length and arity limits
- hash bit width
- layer count, currently always `1`
- original length, payload length, and truncated output hash

The old 3-byte `TlmrHeader` is gone from the active file format because it could
not record hasher kind, Lotus preset, or enough metadata to decode multi-pass
output unambiguously.

## Lotus In This Repository

Lotus means the active 4-field record codec in `src/header.rs`:

```text
[mode][arity][jumpstarter(3)][len_bits][payload]
```

Arity values `1..=5` are valid compressed spans. Arity `2` is valid and is not
reserved. The literal marker is `0xFF`. In `.tlmr` v1, seed payloads must be
byte-aligned; non-byte-aligned seed payloads are rejected by the decoder.

## Multi-Pass Semantics

`.tlmr` v1 emits one-layer-decodable files only. The CLI still accepts
`--passes` for compatibility, but the active writer caps v1 output to one layer
and records `layer_count = 1`. Recursive multi-pass output would require a
future format version with explicit nested-layer metadata and recursive decode.

## Performance Expectations

- Seed depth 1 checks 256 seeds per span and is fast enough for tests.
- Seed depth 2 checks 65,536 additional seeds per span and is slow-ish.
- Seed depth 3 checks 16,777,216 additional seeds per span and is expensive.
- Unit and integration tests should use `max_seed_len = 1`.
- Random data should not be expected to compress.

See [docs/RESULTS.md](docs/RESULTS.md) for generated local results and
[scripts/generate_results.py](scripts/generate_results.py) for the reproduction
script.

## Supported And Removed Pieces

Supported:

- main `telomere compress` and `telomere decompress` CLI
- `.tlmr` v1 one-layer decode
- BLAKE3 and SHA-256 seed expansion
- Lotus arity `1..=5`, including arity `2`
- literal fallback records

Research-only:

- `--features gpu`, which currently builds a deterministic CPU fallback under
  the GPU API
- hash table inspection and precompute tools in `src/bin`

Removed:

- gloss tables and gloss binaries
- bloom filter stubs
- broken fuzz crate targets
- old speculative whitepaper docs that claimed recursive convergence or random
  data compression as current behavior

## Verification

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/doc_lint.py
```
