# Telomere `.tlmr` Format

This file is the source of truth for `.tlmr` versions 1 and 2.

## Status

`.tlmr` v1 is a one-layer stateless container with a 5-byte raw magic+version
prefix followed by a Lotus bit stream that carries both the header and the
records payload. `.tlmr` v2 adds explicit recursive layer descriptors for the
indexed and streaming search engines. Both store enough metadata to choose the
hasher and Lotus preset without CLI assumptions.

## V1 file structure

Every byte beyond the 5-byte magic+version prefix is part of a single Lotus
bit stream. The header section is byte-aligned at its end with zero pad so the
records payload begins at a byte offset; the records payload itself is bit
packed with no per-record byte padding.

```text
File layout:
  bytes 0..4   = "TLMR" magic
  byte  4      = format version = 2
  bit stream from byte 5:
    Lotus J3D2(lotus_preset)
    Lotus J3D2(hasher_id)
    Lotus J3D2(block_size)
    Lotus J3D2(last_block_size)
    Lotus J3D2(max_seed_len)
    Lotus J3D2(max_arity)
    Lotus J3D2(hash_bits)
    Lotus J3D2(layer_count)
    Lotus J3D2(original_len)
    Lotus J3D2(payload_bit_len)
    [hash_bits raw bits of output_hash]
    [zero pad to byte boundary]
  payload_bit_len bits of records, each:
    Lotus J1D1(arity_value)         # 0..=4 = arities 1..=5, value 5 = literal
    if not literal: Lotus J3D2(seed_index)
    if literal: [zero pad to byte boundary] [block_size raw bytes]
  [<=7 trailing zero pad bits to byte-align EOF]
```

The total file length on disk is

```text
V1_MAGIC_VERSION_LEN (=5) + ceil(header_bits / 8) + ceil(payload_bit_len / 8)
```

after each section is independently zero-padded to a byte boundary.

`format_version` is currently `2`. (Version `1` was the legacy fixed 40-byte
header described under "Compatibility" below; the constant `TLMR_FORMAT_VERSION`
in `src/tlmr.rs` carries the current value.) `lotus_preset` is `2`.
`hasher_id` is `1 = blake3` or `2 = sha256`. Other field ranges:

| Field | Range |
| --- | --- |
| `block_size` | `1..=16` |
| `last_block_size` | `1..=block_size` |
| `max_seed_len` | `1..=3` |
| `max_arity` | `1..=5` |
| `hash_bits` | `1..=64` |
| `layer_count` | `1` in v1 |
| `original_len` | decompressed byte length |
| `payload_bit_len` | meaningful bit count in the records payload section |
| `output_hash` | low `hash_bits` bits of the selected hasher digest |

## V1 record encoding

Every record begins with a Lotus J1D1 arity value. J1D1 admits exactly six
codepoints (`0..=5`), so the arity discriminator and the literal escape share
the same field rather than being two separate flags:

| Arity value | Encoded value | Meaning |
| ---: | ---: | --- |
| arity 1 | `0` | one block |
| arity 2 | `1` | two blocks |
| arity 3 | `2` | three blocks |
| arity 4 | `3` | four blocks |
| arity 5 | `4` | five blocks |
| literal | `5` | literal marker |

J1D1 (jumpstarter bits = 1, tiers = 1) is the smallest Lotus preset that
admits six values. In J1D1 the first three codepoints take 3 bits and the last
three take 5 bits; the literal marker (value `5`) takes 6 bits because it sits
in the largest tier.

Compressed records (arity 1..=5) follow the arity value with a Lotus
J3D2-encoded seed index. The index identifies a canonical seed under the
file's `max_seed_len` enumeration order; `src/seed_index.rs` provides the
`index_to_seed` bijection used by the decoder. Small indices encode in fewer
bits — a record with arity 1 and seed index 0 is 9 bits total (3 arity bits +
6 seed-index bits).

Literal records carry no Lotus seed-index payload. After the literal marker
the encoder zero-pads to the next byte boundary so the raw block bytes that
follow can be `memcpy`'d directly. Each literal record covers one block; its
length is `block_size` bytes, or `last_block_size` bytes when the literal is
the final block of the file.

Records pack back-to-back inside the payload bit stream. There is no per-
record byte padding except the 0..7 alignment pad inside each literal record
described above. The final byte of the file may contain up to 7 trailing zero
pad bits, which decoders verify and discard.

## V2 file structure

V2 mirrors the v1 strategy: a 5-byte raw magic+version prefix followed by
a Lotus bit stream that carries the header, all layer descriptors, and the
outer payload. `format_version` is `3` and `lotus_preset` is `2`. Each layer's
records payload is a flat bit-packed stream of seed-span and literal records
(see "V2 records" below).

```text
File layout:
  bytes 0..4   = "TLMR" magic
  byte  4      = format version = 3
  bit stream from byte 5:
    Lotus J3D2(lotus_preset)
    Lotus J3D2(hasher_id)
    Lotus J3D2(seed_order_version)
    Lotus J3D2(layer_count)
    Lotus J3D2(hash_bits)
    Lotus J3D2(original_len)
    Lotus J3D2(outer_payload_bit_len)
    [hash_bits raw bits of output_hash]
    layer_count copies of:
      Lotus J3D2(decoded_len)
      [hash_bits raw bits of decoded_hash]
      Lotus J3D2(max_seed_len)
      Lotus J3D2(max_span_len)
      Lotus J3D2(block_size)
      Lotus J3D2(tier_policy)        # 1 = seed-span, 2 = public-preset-selective
      Lotus J3D2(span_step)
    [zero pad to byte boundary]
  outer_payload_bit_len bits of outermost layer payload
  [<=7 trailing zero pad bits to byte-align EOF]
```

Field ranges:

| Field | Range |
| --- | --- |
| `format_version` | `3` |
| `lotus_preset` | `2` |
| `seed_order_version` | currently `1` |
| `layer_count` | `1..=255`, stored outermost-to-innermost |
| `hash_bits` | `1..=64` |
| `original_len` | final decompressed byte length |
| `outer_payload_bit_len` | meaningful bit count in the outer payload section |
| `output_hash` | low `hash_bits` bits of the final output digest |
| `decoded_len` (per layer) | bytes produced by that layer |
| `decoded_hash` (per layer) | low `hash_bits` bits of that layer's decoded bytes |
| `max_seed_len` (per layer) | `1..=u8::MAX`; `1` when `tier_policy = 2` |
| `max_span_len` (per layer) | `1..=u16::MAX` |
| `block_size` (per layer) | `1..=u16::MAX` |
| `tier_policy` (per layer) | `1 = seed-span records`, `2 = public-preset-selective transform` |
| `span_step` (per layer) | `1..=u16::MAX` (search step for tier 1; public preset version for tier 2) |

Layer descriptors are stored outermost to innermost. The payload that follows
them is the outermost encoded layer. Decoding applies each descriptor in
order, verifies `decoded_hash`, and feeds the decoded bytes into the next
layer.

## V2 records

For `tier_policy = 1` each layer's payload is a flat bit stream of seed-span
and literal records, packed back-to-back:

| Record | Bit layout | Meaning |
| --- | --- | --- |
| seed span | `Lotus J3D2(tag=0) Lotus J3D2(span_len - 1) Lotus J3D2(seed_index)` | recover the seed via `index_to_seed`, expand it, and append `span_len` bytes |
| literal | `Lotus J3D2(tag=1) Lotus J3D2(len - 1) [zero pad to byte boundary] [len raw bytes]` | copy `len` raw literal bytes after verifying the alignment padding is all zero |

There is no `lotus_byte_count`, no per-record byte tag, and no raw `u16
span_len`. Lotus integers are self-delimiting; the only raw bytes inside a
`tier_policy = 1` record are the alignment-padded literal payload bytes. As a
headline, the smallest seed-span record (`span_len = 8`, `seed_index = 0`,
`max_seed_len = 1`) is 22 bits — about 45% smaller than the pre-Wave-B byte-
tagged framing.

For `tier_policy = 2` the layer payload is a public-preset framed stream that
decodes directly to the layer's decoded bytes. Descriptor fields are
reinterpreted:

| Field | Meaning |
| --- | --- |
| `max_seed_len` | must be `1`; preset seeds are one byte |
| `max_span_len` | public codeword length; currently `16` bytes |
| `block_size` | minimum token length selected by the preset; currently `13` |
| `span_step` | public preset version; currently `3` |

The public-preset frame format is a Lotus J3D2 bit-stream. Frame tags are
encoded as Lotus integers (not raw bytes), matching the unified preset used
elsewhere in the file format:

| Frame | Bits |
| --- | --- |
| Codeword | `J3D2(PUBLIC_PRESET_FRAME_TAG_CODEWORD = 0)` then 0–7 zero pad bits to byte boundary then `max_span_len` raw codeword bytes |
| Literal | `J3D2(PUBLIC_PRESET_FRAME_TAG_LITERAL = 1)` then `J3D2(len - 1)` then 0–7 zero pad bits to byte boundary then `len` raw literal bytes |

The codeword frame is the common case and is assigned the shorter Lotus value
(`0`). The byte-alignment pad bits let decoders `memcpy` the raw payload
segment without bit-shifting; all pad bits are zero and the decoder rejects
non-zero pads.

Preset token-to-seed mapping is fixed by the implementation's public token
list: token index `i` maps to seed byte `[i]`, and the codeword is
`expand([i])[0..max_span_len]` using the file header's selected hasher.
Decoders must reject unknown codewords and codeword collisions.

## Encoding presets

Telomere uses two Lotus presets:

- **J3D2** (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`): jumpstarter bits = 3, two
  tiers of variable-width framing. Used for seed indices, sizes, counts, and
  every other Lotus integer in the format except the v1 arity field.
- **J1D1** (`LOTUS_ARITY_J_BITS = 1`, `LOTUS_ARITY_TIERS = 1`): jumpstarter
  bits = 1, one tier of framing. Used only for the v1 arity field, because
  arity is a 6-value enum (1..=5 plus literal) and J1D1 is the smallest preset
  that admits six codepoints. The preset is deliberately narrower than J3D2 so
  we pay only the bits the arity alphabet requires.

The canonical Lotus codec implementation lives in the sibling crate at
[`../../lotus/src/lib.rs`](../../lotus/src/lib.rs). Each variable-width Lotus
field uses sliding-window encoding with no aliases: width `n` covers values
`2^n - 2` through `2^(n+1) - 3`, i.e. exactly `2^n` codepoints. Width 1 covers
`{0, 1}`, width 2 covers `{2..5}`, width 3 covers `{6..13}`, and so on.

J3D2 was chosen because it spans the `max_seed_len ∈ 1..=3` index range
(`256 + 65 536 + 16 777 216` seeds) while keeping small-index records short.
`encode_v1_record_into_writer` / `decode_v1_record_from_reader` in
`src/header.rs` and `v2_seed_span_record_into_writer` /
`v2_literal_record_into_writer` in `src/tlmr_v2.rs` are the canonical
encoders.

## What is not Lotus, and why

The format is otherwise wall-to-wall Lotus, but a few elements are raw:

- **Magic bytes** (`"TLMR"`) — file detection. Decoders must be able to
  classify the format before parsing any Lotus bits.
- **Format version byte** — discriminator for decoder dispatch (v1 vs v2).
- **Hash output bits** (per-file `output_hash`, per-layer `decoded_hash`) —
  truncated hash digests are uniform random and incompressible, so they ship
  as a raw `hash_bits`-wide chunk inside the Lotus stream rather than as a
  Lotus codeword.
- **Literal payload bytes** — these are the data being preserved. Compressing
  them is the rest of the system's job. The 0..7 zero pad bits before each
  literal payload exist so decoders can `memcpy` the bytes directly off the
  bit stream without a slow per-bit read.
- **Trailing pad bits** — up to 7 zero bits at the very end of the file
  exist solely to byte-align EOF. They carry no semantic meaning and decoders
  must verify they are zero.

## Decoding

V1 decoders dispatch by reading the magic and version byte, then reading the
Lotus header bit stream, then reading records from the payload bit stream
until `bytes_out == original_len`. Each record is one of:

- **Literal**: arity value = `5`. Skip 0..7 zero pad bits to the next byte
  boundary, then copy `block_size` (or `last_block_size`, if this is the
  final block) raw bytes into the output.
- **Compressed**: arity value `0..=4` (arity 1..=5). Decode a Lotus J3D2 seed
  index, recover the seed via `index_to_seed`, expand the seed with the
  header-selected hasher, and append `arity * block_size` bytes.

When `bytes_out == original_len`, the decoder verifies any remaining bits in
`payload_bit_len` are zero pad and that the file ends after that bit count.
The final output hash must match `output_hash`.

V2 decoders dispatch by reading the magic and version byte, then the Lotus
header and `layer_count` layer descriptors, then the outer-layer payload.
Layers are decoded outermost-to-innermost: the outer payload is decoded under
the outermost descriptor, the result is fed into the next descriptor, and so
on until the innermost layer reproduces `original_len` bytes whose digest
matches `output_hash`. Each `tier_policy = 1` layer decodes records as
described above; each `tier_policy = 2` layer decodes a public-preset framed
stream directly to its decoded bytes.

## Hashers

Hasher id `1` is BLAKE3 XOF expansion. Hasher id `2` is SHA-256 expansion. The
selected hasher affects both seed expansion and output hash verification. A file
is not portable unless this field is honored.

## Validation

V1 decoders reject input that violates any of:

- field-range constraints from the "V1 file structure" table above
- `layer_count == 1`
- `last_block_size in 1..=block_size`
- `payload_bit_len` matches the bit count consumed by parsing all records
  back to `bytes_out == original_len`
- trailing pad bits (after `payload_bit_len`) are all zero
- file length equals `5 + ceil(header_bits/8) + ceil(payload_bit_len/8)`

V2 decoders reject input that violates any of:

- field-range constraints from the "V2 file structure" table above
- per-layer `decoded_hash` matches the digest of that layer's decoded bytes
- `outer_payload_bit_len` matches the bit count consumed by parsing the
  outermost layer
- unsupported `tier_policy` values, invalid `span_step`/`max_seed_len`
  combinations under `tier_policy = 2`, and malformed transform frames

## Compatibility

### Production Support Policy

For the current release candidate, `.tlmr` v1 is the only
production-supported file format. The supported v1 contract is:

- writers emit the current `format_version` (`2`), `lotus_preset = 2`,
  `layer_count = 1`, Lotus J1D1/J3D2 records, and authoritative hasher
  metadata
- readers must honor `hasher_id`, `lotus_preset`, `layer_count`,
  `payload_bit_len`, and output-hash validation
- future production releases must continue to read v1 files or ship a
  standalone migration tool before removing v1 decode support

`.tlmr` v2 (format_version `3`) is experimental. The current decoder can read
v2 files written by this repository, including recursive layer descriptors,
but v2 is not a production compatibility target yet. A release must not
promise long-term v2 stability until the v2 format is promoted by a release
checklist update and a new production proof matrix.

No compatibility guarantee is made for pre-`TLMR` files. The old experimental
3-byte header and the legacy fixed 40-byte v1 header (`format_version = 1`)
are not auto-detected, migrated, or decoded by the production path. They must
fail as unsupported input unless a standalone migration tool explicitly
recognizes them and rewrites them into a documented versioned container.

Future versions must bump `format_version` if any header field, Lotus preset,
seed enumeration order, or multi-pass decoding semantics change.

Migration rules are intentionally conservative:

- never silently reinterpret an unsupported header as a supported one
- never migrate by dropping hasher, Lotus preset, seed-order, layer, length, or
  output-hash metadata
- standalone migration tools must name both source and target format versions
  and must verify that decompressed bytes match before writing the target file

Transform preconditioners are not part of `.tlmr` v1. A file that was
preprocessed by a reversible transform is just bytes to v1 unless a future
version explicitly records the transform kind and metadata needed to invert
it.

### V2 layer descriptor interpretation

For `tier_policy = 1`, descriptor fields retain their search meanings:
`max_seed_len`, `max_span_len`, `block_size`, and `span_step` describe the
compressor's seed/span search limits.

For `tier_policy = 2`, the descriptor's `max_seed_len`/`max_span_len`/
`block_size`/`span_step` fields are reinterpreted per the table in "V2
records" above.

Decompression never requires an index. The seed expansion index is only a
compression-time accelerator. `span_step` is recorded so a v2 file can describe
whether the compressor searched the normal block grid or a finer sub-block
candidate grid; decoders validate it as `1..=block_size` and `<= max_span_len`,
but reconstruction does not depend on repeating the search for `tier_policy = 1`.
For `tier_policy = 2`, `span_step` is a preset version instead. Decoders reject
unsupported descriptor policies, invalid span steps or preset versions,
malformed transform frames, layer lengths above the caller's output or memory
limit, and layer hashes that do not fit `hash_bits`.

Index directories are not part of the `.tlmr` compatibility contract, but the
current `TIDX` index manifest records `hasher`, `seed_order_version`,
`max_seed_len`, `max_span_len`, and tier record counts. Tier files are sorted
fixed-width generated-prefix records so the mmap backend can binary-search exact
target bytes. The builder writes these tier files through chunked external
sorting and deduplication; readers must still verify every returned seed by
regenerating bytes before emission.

Most transform preconditioners are not part of `.tlmr` v2.
`docs/TRANSFORM_SWEEPS.md` measures external research transforms only. The sole
format-native transform currently defined is experimental
`public-preset-selective` (`tier_policy = 2`); promoting it or any other
transform to production requires a release checklist update that freezes the
preset token table, compatibility guarantees, migration rules, and dictionary
identity.

## Indexed Search Semantics

Indexed and streaming compression use exact generated-prefix lookup:

```text
expand(seed)[0..span_len] == target_span
```

It must not use `hash(target_span) == hash(seed)` as a match rule. Compression
groups active spans into equal-length lookup tiers, deduplicates identical span
queries, verifies every hit by re-expanding the seed, and then selects
non-overlapping positive-saving spans deterministically. The default candidate
start step is `block_size`; experimental sub-block runs may use a smaller
`span_step` such as `1` to test alignment sensitivity. The indexed backend
looks up target spans in reusable generated-prefix seed tiers. The streaming
backend indexes target spans and enumerates each seed once across all active
tiers. When the experimental `--target-chunk-bytes` option is used, indexed v2
builds bounded target-span chunks before querying the index, while streaming v2
builds one bounded target-table chunk at a time and rescans the canonical seed
order for each chunk. This lowers peak target-table memory at the cost of
repeated chunk-local lookup work.

Indexed/streaming JSON telemetry is not part of the `.tlmr` byte format, but it
is part of the supported experimental CLI/API surface for measuring search
cost. Tier telemetry reports `target_windows`, `unique_spans`, `lookup_count`,
`candidate_hits_raw`, `candidate_hits_profitable`, `candidate_hits`,
`duration_ms`, and `estimated_target_table_bytes`. Streaming aggregate and layer
telemetry also report `seeds_scanned` and `seed_expansions`, which are equal in
the default CPU implementation because each canonical seed is expanded once to
the maximum active span length. Chunked streaming may report higher
`seed_expansions` because each chunk has an independent target table scan.
Chunked indexed runs may report multiple per-chunk rows for the same span tier.
