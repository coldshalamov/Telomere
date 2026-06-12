# Telomere Architecture

## What Telomere Is Now

Telomere is a Rust prototype for stateless lossless generative compression. The
active compressor:

- splits input into fixed-size byte blocks
- searches canonical seed space in length-first, big-endian order
- expands candidate seeds with BLAKE3 XOF or SHA-256
- accepts a candidate only when the Lotus record's on-wire bit cost is
  strictly smaller than the original span's bit count (`span_len * 8`)
- emits literal records for everything else
- writes a `.tlmr` v1 header that carries all decoding metadata

The indexed research compressor adds a second path:

- builds exact generated-prefix seed tiers once per hasher/search window
- aligns active spans into equal-length tables before lookup
- verifies each hit by seed expansion, not by digest equality
- selects non-overlapping spans by deterministic savings
- writes recursive `.tlmr` v2 files with explicit layer descriptors

The streaming research compressor is the whitepaper-aligned CPU path:

- builds equal-length target span tables from the current layer
- enumerates canonical seeds once per pass
- expands each seed to the maximum active span length
- checks that generated prefix against every active tier
- emits verified candidates into the same deterministic selector used by the
  indexed v2 path

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
| `src/seed_expansion_index.rs` | Exact generated-prefix seed index |
| `src/indexed.rs` | Indexed v2 compression and span selection |
| `src/streaming.rs` | CPU stratified target-span streaming matcher |
| `src/tlmr_v2.rs` | `.tlmr` v2 recursive header and records |

## What Lotus Means Here

Telomere uses the Lotus tiered integer codec end-to-end. The canonical Lotus
implementation lives in the sibling crate at
[`../../lotus/src/lib.rs`](../../lotus/src/lib.rs); `src/header.rs` and
`src/tlmr_v2.rs` route every header field, arity discriminator, and seed
index through that crate's `BitWriter`/`BitReader` streaming API. There is no
local Lotus reimplementation and no byte-tagged framing — both `.tlmr` v1 and
`.tlmr` v2 are wall-to-wall Lotus bit streams from byte 5 onward (the only
raw prefix is the four magic bytes plus the version byte that selects the
decoder).

Two presets are used:

- **J3D2** (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`) — used for seed indices,
  sizes, counts, and every other Lotus integer in both v1 and v2. Three-bit
  jumpstarter, two levels of sliding-window tier framing.
- **J1D1** (`LOTUS_ARITY_J_BITS = 1`, `LOTUS_ARITY_TIERS = 1`) — used only
  for the v1 arity discriminator. Six codepoints (`0..=5`) cover arities
  1..=5 and the literal escape; J1D1 is the smallest preset that admits six
  values, so the arity field costs exactly the bits the alphabet requires.

A compressed v1 record packs as `Lotus J1D1(arity_value) Lotus
J3D2(seed_index)` back-to-back inside the layer's bit stream. A v1 literal
record packs as `Lotus J1D1(arity_value=5)` followed by 0..7 zero pad bits to
the next byte boundary and then `block_size` raw bytes. A v2 seed-span record
packs as three J3D2 values (`tag=0`, `span_len-1`, `seed_index`); a v2
literal record packs as two J3D2 values (`tag=1`, `len-1`), 0..7 zero pad
bits, and `len` raw bytes.

For `.tlmr` v1:

- arity `1..=5` are compressed span arities, encoded as J1D1 values `0..=4`
- arity `2` is valid
- the literal marker is the J1D1 value `5` (6 bits in J1D1)
- compressed records carry a Lotus J3D2 canonical seed index; the decoder
  recovers the seed bytes through `index_to_seed`
- literal records carry no seed-index payload and are followed (after byte
  alignment) by raw literal bytes

## Multi-Pass Position

The active `.tlmr` v1 format emits one-layer-decodable files. `--passes` remains
accepted as a compatibility knob, but v1 output records `layer_count = 1` and is
not recursively nested.

The indexed and streaming paths emit `.tlmr` v2 files. v2 records explicit
outer-to-inner layer descriptors, so recursive decompression is unambiguous and
does not need a compression-time index.

## Stratified Lookup Model

The whitepaper lookup principle is represented as equal-length tiers. A pass
collects candidate spans on a configured start grid, groups them by byte length,
and deduplicates identical spans. The default start step is `block_size`, but v2
also has an experimental `--span-step` option for sub-block alignment sweeps
such as byte-step starts. The reusable indexed backend stores exact generated
prefixes for the same tier lengths. The streaming backend instead stores the
target spans and streams seed expansions through those tables, so each seed is
expanded once and compared against all active span lengths.

Current implementation status:

- CPU/RAM exact-prefix tiers are implemented.
- A memory-mapped sorted tier backend is implemented for on-disk indexes.
- Index construction uses chunked external sorting: seeds are enumerated once,
  generated-prefix records are spilled per tier, and merge/dedup writes the
  mmap-ready tier files without first materializing the full index map.
- A CPU streaming matcher over target span tiers is implemented.
- Indexed and streaming v2 have explicit experimental `--target-chunk-bytes`
  paths that build bounded target-table chunks. Indexed chunking repeats
  chunk-local index lookups; streaming chunking rescans seeds per chunk. This
  is deterministic fixture evidence for lower peak table memory, not full
  process RSS containment or production sizing proof.
- Sub-block span-step metadata and tests are implemented for indexed/streaming
  v2; this is a research alignment knob, not a new v1 compatibility rule.
- Indexed and streaming v2 telemetry reports candidates, selected-span records,
  literals, bundles, tier hits, bounded work accounting, layer payload bytes,
  and stop reason through CLI JSON and Tauri IPC. Per-tier telemetry records
  target windows, unique spans, lookup counts, raw/profitable hits, and
  estimated target-table bytes; streaming layers additionally record seeds
  scanned and seed expansions. Tauri also converts selected spans into a
  bounded lattice sample for operator visualization.
- GPU/ASIC streaming comparison remains research-only.

## Candidate Selection Contract

The active v2 engine uses a flat candidate model, not recursive
superposition. A candidate is valid only when:

- `expand(seed)[0..span_len] == target_span`
- its v2 seed-span record's on-wire bit cost is strictly less than
  `span_len * 8` (the byte-rounded form is also exposed via
  `v2_seed_span_record_byte_len` for telemetry but the profit gate is
  bit-accurate)
- it lies on the configured v2 candidate-start grid

All valid candidates for a layer are passed to deterministic weighted interval
selection. The selector maximizes total byte savings across non-overlapping
spans, then prefers more covered bytes, fewer seed bytes, and the existing
dynamic-programming path on exact ties. The implementation stores scalar scores
and backpointers rather than cloning selected-span vectors into every state, so
large planted fixtures exercise the selector without quadratic memory growth.
Recursive passes operate only on the selected layer payload, never on
unresolved candidate alternatives.

The older `src/superposition.rs` machinery remains part of the legacy/brute
research surface. It is not the `.tlmr` v2 wire-format contract, and v2 files do
not serialize alternative candidates. The formal research contract for that
surface lives in `docs/CANDIDATE_LATTICE.md`.

## Explicitly Gone

The following are removed from the active architecture:

- old 3-byte active file header
- gloss table stubs
- gloss dump/debug binaries
- bloom filter placeholder
- broken fuzz crate targets
- speculative whitepaper docs that described unimplemented recursive convergence
- claims that ordinary random inputs are expected to shrink
- digest-prefix hash-table binaries that compared `hash(block)` to `hash(seed)`
- placeholder `lotus_core` exports that implied a future external Lotus codec
- code comments that treated `kolyma.pdf` as a protocol specification

## Research-Only Surface

The following remain research tools or internal diagnostics:

- `--features gpu`
- `src/bin/seed_table.rs`
- `src/bin/block_summary.rs`
- transform/preconditioner sweeps in `docs/TRANSFORM_SWEEPS.md`
- `kolyma.pdf` as a symbolic binary/PDF control corpus

See [TOOLS.md](TOOLS.md) for the full tool classification.

Transform preconditioners are not part of `.tlmr` v1 or `.tlmr` v2. ADR-0001
records the current policy: transform-only wins must not be presented as
Telomere seed-span wins unless telemetry shows selected generated spans and a
future format version records enough metadata to decode the transform.
