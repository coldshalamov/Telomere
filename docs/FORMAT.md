# Telomere `.tlmr` Format

This file is the source of truth for `.tlmr` version 1.

## Status

`.tlmr` v1 is a one-layer, byte-aligned, stateless container. It stores enough
metadata to choose the hasher and Lotus preset without CLI-side assumptions.
Recursive multi-pass files are not part of v1.

## Header Strategy

The active format replaces the old 3-byte experimental `TlmrHeader` with a
fixed 40-byte rich header. The old header could not record hasher kind, Lotus
preset, seed-depth limits, payload length, or layer count. Extending it would
have made the bit layout ambiguous, so v1 uses a new byte-oriented header.

All integer fields are big-endian.

| Offset | Size | Field | Value |
| ---: | ---: | --- | --- |
| 0 | 4 | magic | ASCII `TLMR` |
| 4 | 1 | format_version | `1` |
| 5 | 1 | header_len | `40` |
| 6 | 1 | lotus_preset | `1` |
| 7 | 1 | hasher_kind | `1 = blake3`, `2 = sha256` |
| 8 | 2 | block_size | bytes, valid `1..=16` |
| 10 | 2 | last_block_size | bytes, valid `1..=block_size` |
| 12 | 1 | max_seed_len | bytes, valid `1..=3` |
| 13 | 1 | max_arity | valid `1..=5` |
| 14 | 1 | hash_bits | valid `1..=64` |
| 15 | 1 | layer_count | `1` in v1 |
| 16 | 8 | original_len | decompressed byte length |
| 24 | 8 | payload_len | bytes after the 40-byte header |
| 32 | 8 | output_hash | low `hash_bits` bits of selected hasher digest |

The full file length must equal `40 + payload_len`.

## Lotus Preset 1

Payload records use the active Lotus 4-field codec:

```text
[mode][arity][jumpstarter(3)][len_bits][payload]
```

Arity field:

| Arity | Mode | Arity bits | Meaning |
| ---: | --- | --- | --- |
| 1 | `0` | `0` | one block |
| 2 | `0` | `1` | two blocks |
| 3 | `1` | `00` | three blocks |
| 4 | `1` | `01` | four blocks |
| 5 | `1` | `10` | five blocks |
| 0xFF | `1` | `11` | literal marker |

Arity `2` is valid. It is not reserved.

Length field:

- Compressed records carry seed payload bits.
- Literal records carry no Lotus payload; raw literal bytes immediately follow
  the literal marker record.
- `.tlmr` v1 requires seed payload bit lengths to be byte-aligned.
- Non-byte-aligned seed payloads are rejected.

## Payload Decoding

The decoder starts at byte offset 40 and repeatedly decodes one Lotus record:

- Literal record: copy `min(block_size, original_len - bytes_out)` bytes from
  the payload stream.
- Compressed record: interpret the byte-aligned payload as seed bytes, expand it
  with the header-selected hasher, and append `arity * block_size` bytes.

Decoding stops only when the payload is exhausted and `bytes_out == original_len`.
The final output hash must match `output_hash`.

## Hashers

Hasher id `1` is BLAKE3 XOF expansion. Hasher id `2` is SHA-256 expansion. The
selected hasher affects both seed expansion and output hash verification. A file
is not portable unless this field is honored.

## Limits

`.tlmr` v1 validates:

- `block_size` in `1..=16`
- `max_seed_len` in `1..=3`
- `max_arity` in `1..=5`
- `hash_bits` in `1..=64`
- `layer_count == 1`
- payload length exactly matches the file size

## Compatibility

No compatibility guarantee is made for pre-v1 files. Future versions must bump
`format_version` if any header field, Lotus preset, seed enumeration order, or
multi-pass decoding semantics change.
