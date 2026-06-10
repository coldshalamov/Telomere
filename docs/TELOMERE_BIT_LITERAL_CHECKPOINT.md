# BIT_LITERAL Checkpoint

**Status: wire-proven primitive** (`wire_proven_candidate` as a primitive;
the audited config that uses it remains `math_candidate`). This file pins
the definition, the proof artifacts, and what is still missing for
`implemented_codec_result`.

## Definition (exact)

```
BIT_LITERAL = [literal codeword][block_bits raw bits]      (zero pad, none)
```

- The literal codeword is whatever the layer's alphabet assigns (3 bits
  `111` in the canonical alphabet; `110` in mixed run alphabets; 2 bits in
  the `single_cheap` profile). The codeword spend is a decoder-public
  profile constant.
- `block_bits` is a fixed profile constant (or layer-descriptor field —
  then charged in the layer descriptor).
- The final tail is governed out-of-band by `original_len` /
  `payload_bit_len` / `last_block_size` (FORMAT_CANONICAL.md §6): the tail
  literal carries `last_block_size` raw bits under the same marker; no
  in-band terminator exists or is needed.
- No byte pad: the v1 writer's pad-to-byte is a memcpy convenience, not a
  decodability requirement. BIT_LITERAL removes it: 3 bits overhead instead
  of 8 (byte-aligned) or 10 (worst case).

## Why it matters

The literal wrap is the dominant pass-1 cost and the floor under every
later-pass budget. At block 8: worst-case pad costs 10 bits/block (pass-1
ratio 2.21), byte-aligned 8 (1.97), BIT_LITERAL 3 (1.375). In the audited
config the BIT_LITERAL-vs-byte-aligned difference alone is worth
0.085 pp/pass of sustained rate (ablation in `bit_literal_target.json`).

## Proof artifacts (all passing)

| claim | artifact |
| --- | --- |
| literal-only stream round-trips; zero pad carries nothing | `bit_literal_decode_proof.py` |
| mixed seed-record + BIT_LITERAL stream round-trips, prefix-free, self-delimiting | `bit_literal_decode_proof.py` |
| charged bits == wire bits, record-exact | `bit_literal_decode_proof.py` (assert), re-parse checks in `position_salt_decode_proof.py` |
| tail literal by out-of-band length | `literal_run_decode_proof.py` (odd-length tail case) |
| previous bitstream recovered exactly before inner parse | nested two-layer cases in `position_salt_decode_proof.py` |
| J3D1 reference layout golden vectors incl. tier boundaries | `cost_pin.py` → `cost_pin_report.json` |

Reference-layout note: the 3-bit jumpstarter stores `tier_width − 1`
(tw ∈ 1..8 → payload widths 1..508). The previous reference encoder stored
`tw` directly — it wasted the zero slot and could not represent payload
widths ≥ 254. Widths and costs are unchanged by the fix; no prior numbers
move. Wire compatibility with the sibling `../lotus` crate still requires a
local golden-vector pin (crate absent from this checkout).

## The audited config that uses it (reference floor)

Block 8, depth 96, J3D1, record-aligned, permutation+neutral-swaps
(3 charged bits/pass), variants cap 4, greedy: **0.1328 %/pass min over ten
effective passes, payback at effective pass 126, final/raw 0.486 @ 500**
(`bit_literal_target.json`). Now superseded as primary by the v-next
masked-expansion config (see `TELOMERE_VIABILITY_TARGET.md`), but unchanged
as the conservative reference floor — and it requires only ONE new
primitive, which is this one.

## What is still missing for `implemented_codec_result`

1. A v-next reference encoder/decoder pair in `src/` implementing
   BIT_LITERAL behind a profile flag (bit-aligned writer; the current v1
   writer pads to byte).
2. `cargo test` round-trip + cost-equality tests mirroring
   `bit_literal_decode_proof.py` at the Rust wire level.
3. Lotus-crate golden vectors (layout pin above).

Until then: treat every BIT_LITERAL-dependent number as model-level, marked
`math_candidate`, with the primitive itself decode-proven at toy scale.
