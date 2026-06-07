# Telomere — Canonical Format Specification

**Status: single source of truth.** Where any other doc, comment, or code path
disagrees with this file, this file is correct and the other is drift to be
fixed. Written from the maintainer's design intent and reconciled against the
wire-format code (`src/header.rs`, `src/tlmr.rs`, `docs/FORMAT.md`) as of this
cleanup. Two things in here are *corrections* to the current implementation — the
**arity alphabet** (§2) and the **seed-index tier count** (§4);
they are marked **[DRIFT — FIX]**. Everything else documents behavior that is
already correct in the repo, including the EOF scheme.

---

## 1. The pass model

- The input file is split into fixed **blocks** of `B` bytes. The final block
  may be partial — its true length is `last_block_size ∈ 1..=B`.
- A **pass** walks the blocks once. For each position the searcher looks for a
  seed whose hash expansion reproduces the block (arity 1) or the next `a`
  contiguous blocks (arity `a`, 2..=5).
- **Monotonic non-bloat rule.** A block is replaced by a seed record **only if
  the record is strictly smaller than what it replaces.** Otherwise the block is
  emitted as a literal. Consequence: after the one-time initialization cost of a
  literal marker per unmatched block, a pass can never make the payload larger.
  (Superposition is the one accounting exception — see §7.)
- After a pass, the emitted record stream is the next layer's bytes. Multi-pass
  (`layer_count > 1`) re-blocks that stream and passes again.

---

## 2. The arity codeword alphabet  **[DRIFT — FIX]**

Every record begins with a prefix-free **arity codeword**. One selector bit
gives the width of the arity field; the field then names the arity or the
literal escape:

| meaning            | codeword | bits |
|--------------------|:--------:|:----:|
| arity 1 (1 block)  | `00`     | 2    |
| arity 2 (2 blocks) | `01`     | 2    |
| arity 3 (3 blocks) | `100`    | 3    |
| arity 4 (4 blocks) | `101`    | 3    |
| arity 5 (5 blocks) | `110`    | 3    |
| **literal**        | `111`    | 3    |

Selector bit `0` → a 1-bit arity field follows (`00`, `01`). Selector bit `1` →
a 2-bit arity field follows (`100`,`101`,`110`,`111`).

**This alphabet is Kraft-complete:** 2·2⁻² + 4·2⁻³ = ½ + ½ = **1.0**. Every bit
pattern of the code space is used; there are no aliases and no wasted codewords.
That is the whole efficiency argument, and it is also why **end-of-stream cannot
be a codeword** — there is no seventh slot (see §6).

> **[DRIFT — FIX]** The current `src/header.rs` encodes arity through the generic
> `J1D1` Lotus integer preset, which spends **{3, 5, 5, 5, 5, 6}** bits on these
> six symbols (literal = 6 bits). The canonical alphabet above spends
> **{2, 2, 3, 3, 3, 3}**. It is strictly cheaper on every symbol and is the
> intended design. Aligning to it is the single highest-value format fix in the
> repo: it roughly halves the per-block literal tax (e.g. 25% → 12.5% at B=3),
> which pulls the break-even multiplier down by ~2x. `FORMAT.md`'s "arity value
> = 5, 0..=4" description is the same drift and must be updated to match.

---

## 3. Record formats

A record is the arity codeword followed by its body.

**Literal record** (codeword `111`):
```
[111] [zero-pad to next byte boundary] [block_size raw bytes]
```
The literal carries no seed. The byte-align pad lets the raw block be `memcpy`'d.
The final block of the file is `last_block_size` bytes instead of `block_size`.

**Seed record** (codewords `00`/`01`/`100`/`101`/`110`):
```
[arity codeword] [Lotus seed index]
```
The decoder recovers the seed from its index, expands it with the
header-selected hasher, and appends `arity × block_size` bytes (the final span
honoring `last_block_size` if it reaches the file end).

The seed's **physical position in the stream is its address** — nothing stores
"where" a match goes. The record sits exactly where the block(s) it reproduces
sat. This is correct in the repo and is a genuine strength of the design.

---

## 4. The Lotus seed-index field — five fields, two fixed

The seed index uses the unfolding Lotus integer codec. In the maintainer's
terms, a full seed record is **five fields, of which fields 1 and 3 are fixed
width and the rest unfold**:

1. arity-length selector — **1 bit, fixed**  ┐ together: the §2 arity codeword
2. arity field — 1–2 bits, unfolds           ┘
3. jumpstarter — **3 bits, fixed** — gives the width of field 4
4. payload-length — unfolds — gives the width of field 5
5. payload — the seed index bits

Because the codec uses its own length as a parameter, it approaches binary
efficiency at the limit (≈95–96% of raw binary for large indices), beating
LEB128 in the common case. The one unavoidable tax is field 3: *something* must
state the first length, and nothing can state its own, so the jumpstarter is
fixed.

> **[DRIFT — FIX] Confirmed canonical: the seed index is `J3D1`** — jumpstarter
> 3 bits, **one** unfolding tier — i.e. exactly the five fields above:
> `jumpstarter(3) → one length field → payload`. A two-tier code (`J3D2`) inserts
> a second length field (a length-of-length), making six fields; that is **not**
> the design.
>
> The current code uses `LOTUS_J_BITS=3, LOTUS_TIERS=2` (**J3D2**) for the seed
> index — so the seed field is drifted, the same way the arity field is.
> **Verify the parameter mapping against the codec, do not assume it:** the
> `lotus` crate is a *sibling* (`../lotus/src/lib.rs`) and is **not present in
> this repo checkout**, so the cleanup agent must obtain it and confirm
> bit-for-bit that its chosen `(J_BITS, TIERS)` emits the five-field J3D1 layout
> before changing the constants — then pin the result with a golden vector. (This
> is the disciplined move precisely because I could not read the crate this
> session to verify the tier-counting convention myself.)

---

## 5. File header (lean canonical layout)

Raw 5-byte prefix `TLMR` + 1 version byte (kept un-encoded so tooling can detect
the format without a Lotus parser), then a Lotus bit stream, then zero-pad to a
byte boundary so records start byte-aligned:

```
"TLMR" (4 bytes) | version (1 byte)
  Lotus(lotus_preset)
  Lotus(hasher_id)
  Lotus(block_size B)
  Lotus(last_block_size)
  Lotus(max_seed_len)
  Lotus(max_arity)
  Lotus(hash_bits)
  Lotus(layer_count)
  Lotus(original_len)        # decompressed byte length  — see §6
  Lotus(payload_bit_len)     # meaningful bits in the records payload — see §6
  [hash_bits raw bits: truncated output_hash]    # integrity — see §8
  [zero pad to byte boundary]
```

The "40-byte header" you were worried about is the **legacy** fixed layout. It
is already gone: `TLMR_FORMAT_VERSION = 2` replaced it with this variable
stream, and a test (`typical_header_is_smaller_than_legacy_40_bytes`) holds the
encoded header **≤ 20 bytes** for a normal config. So that worry is resolved.

> **[OPTIONAL — leaner still]** If you want to trim further: `block_size`,
> `max_seed_len`, `max_arity`, and `hasher_id` are constant across a build and
> could be folded into the version byte (a version implies a profile), as you
> suggested. This is amortized-once overhead, so it is low priority — record it
> as a "tidy later," not a blocker.

---

## 6. EOF / termination — **this is already correct in the repo**

You couldn't remember how EOF was handled and worried it was misconfigured.
**It isn't — it's one of the parts that's right, and it's sound.** Here is the
scheme and the proof it always decodes.

**Termination is out-of-band, by length — never an in-band marker.** Two header
fields carry it:

- `original_len` — the exact decompressed byte length.
- `payload_bit_len` — the exact number of meaningful bits in the record stream.

**Decoding one layer.** Read records sequentially. Each record is
self-delimiting: the arity codeword (§2) is prefix-free, so the decoder always
knows whether a seed index follows and how many output bytes the record yields
(literal → `block_size`/`last_block_size`; arity `a` → `a × block_size`). The
decoder appends bytes and **stops the instant `bytes_out == original_len`**, then
verifies that the remaining bits up to `payload_bit_len` are zero pad and that
the file ends there.

**Partial final block.** Handled by `last_block_size`: the final emitted block is
truncated to `last_block_size` bytes. This covers the "EOF of the starting file
once split into blocks" problem you remembered as tricky.

**Why there is no in-band terminator (and why your experiments fought it).** The
arity alphabet is Kraft-complete (§2) — all six codewords are spent on arity
1–5 and literal. There is **no seventh codeword** to mean "stop," and minting one
would enlarge the alphabet and tax every record. So end-of-stream *must* live in
the header as a length. That is not a workaround; given a full alphabet it is the
only correct design. (This is the answer to "is 111 the termination marker?" —
no: `111` is the literal codeword; termination is `original_len`.)

### Decodability proof (single layer)
1. The decoder knows `original_len` before reading any record.
2. Each record yields ≥ 1 output byte, so `bytes_out` strictly increases.
3. Therefore `bytes_out == original_len` is reached after finitely many records.
4. Each record's end is unambiguous (prefix-free codeword + fixed/unfolding
   fields), so the decoder never loses sync mid-stream.
5. After the stopping record, bits `bytes_out`-boundary … `payload_bit_len` are
   checked zero; the file must end at `5 + ceil(header_bits/8) +
   ceil(payload_bit_len/8)`. ∎

---

## 7. Multi-pass (layers) and superposition

**Layers.** For `layer_count = L > 1`, the file stores `L` layer descriptors,
outermost-to-innermost, each with its own `payload_bit_len`. Decoding peels
layers in order: decode the outer record stream (bounded by its
`payload_bit_len`) to produce the next layer's bytes, re-block, repeat, until the
**innermost layer reproduces exactly `original_len` bytes** whose hash matches
`output_hash`. Each layer's termination is the same out-of-band length argument
as §6, so the whole chain is decodable by induction on `L`.

**Superposition** (the `236A`/`236B` mechanism). When a match is found that is
*not* compressive, the block may be retained in superposition: the original
becomes `236A`, the non-compressive seed becomes `236B`, and a later pass may
find a compressive match for `236B` that beats `236A`, at which point the
replacement is committed. This is decoder-invisible — only the finally selected
records reach the wire. It is the one case where a pass tracks a candidate that
is momentarily larger; it never ships a larger record.

> **[CONFIRM]** The current repo gates `layer_count = 1` in v1 (`tlmr.rs`
> asserts it) and routes recursion through a separate v2 path. The canonical
> intent is a single recursive format. The cleanup should unify these rather
> than maintain two — see the cleanup plan, Phase 2.

---

## 8. Integrity

The header stores `hash_bits` low bits of the selected hasher's digest of the
**original** file (`output_hash`). After a full decode to `original_len` bytes,
the decoder recomputes and compares. This is your "truncated hash for fidelity"
idea, already present. `hash_bits` is tunable (default 13 in code); 32 or 64
bits gives stronger collision resistance for archival use at a few amortized
bytes.

---

## 9. Open decisions to confirm (collected)

1. **Header leanness: fold constants into version?** §5. Low priority.
2. **Unify v1/v2 into one recursive format.** §7.

*(Resolved this session: the seed-index codec is **J3D1**, §4 — confirmed by the
maintainer. It is now a drift fix, not an open question.)*

Everything else in this document is canonical. The EOF scheme (§6) and the
position-as-address design (§3) are correct as-is; the two load-bearing
corrections are the arity alphabet (§2) and the seed-index tier count (§4).
