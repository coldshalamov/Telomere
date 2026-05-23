# Lotus Primitive — Self-Contained Reference for Telomere

**Purpose**: This document contains everything Telomere needs to know about the Lotus codec. It is a condensed, self-contained extract from the canonical Lotus implementation so that Telomere agents never need to consult the sibling `lotus/` repository.

**Last synced**: 2026-05-22  
**Canonical source**: `lotus` crate (https://github.com/lotus-codec/lotus) — for reference only.

---

## 1. What Lotus Is

Lotus is a **parametric bit-level integer codec** that maps every fixed-width bitstring into contiguous integer ranges while remaining self-delimiting through a bounded tier chain and jumpstarter.

It sits between dense fixed-width encodings and universal codes. It reclaims representational density by unfolding bitstrings into consecutive integers, then restores prefix-decodability via a `(J, d)`-parameterized tier system.

**Core properties**:
- **Density reclaiming**: every distinct bitstring is assigned to a unique integer in contiguous ranges.
- **Configurable envelope**: `(J, d)` controls representable range and overhead profile.
- **Bit-level framing**: naturally bit-oriented; `bit_len` is authoritative.
- **Self-delimiting**: no external length prefix required.

---

## 2. The (J, d) Parameterization

- `J` = jumpstarter width in bits (1–3 typical). Determines how many immediate width states exist.
- `d` = number of recursive tiers for describing larger widths.

**Presets** (recommended for Telomere):
- `LOTUS_J2D1` — balanced, good for 1–3 bit values (current default in Telomere header.rs)
- `LOTUS_J1D2` — potentially superior for Telomere's skewed small-value distribution (arity 1, short lengths)
- `LOTUS_J3D1` — larger immediate range, higher fixed overhead

**Trade-off**:
- Larger `J` → more fixed header cost per value, but wider immediate width.
- Larger `d` → can represent very large values, but adds tier overhead.

**Telomere-specific note**: Our value distribution is heavily skewed toward tiny arities (1, 3–6) and short-to-medium length fields (0–255 bits). The tuning matrix in `docs/LOTUS_TUNING.md` will decide the final preset.

---

## 3. API Surface (Canonical)

### Core Functions

```rust
// Encode a value with explicit framing metadata (preferred)
lotus_encode_u64_framed(value: u64, j_bits: u8, tiers: u8)
    -> Result<EncodedLotus, LotusError>

// Decode
lotus_decode_u64(bytes: &[u8], j_bits: u8, tiers: u8)
    -> Result<(u64, usize), LotusError>  // (value, bits_consumed)
```

### Framed Result Type

```rust
pub struct EncodedLotus {
    pub bytes: Vec<u8>,   // MSB-first bitstream
    pub bit_len: usize,   // exact number of meaningful bits
}
```

**Important**: Lotus is **bit-oriented**, not byte-oriented. The final byte may contain trailing zero padding bits. Always use `bit_len` for framing.

### Errors

```rust
pub enum LotusError {
    JumpstarterOverflow,  // payload exceeds jumpstarter capacity
    UnexpectedEof,        // insufficient bits
    InvalidEncoding,      // malformed Lotus sequence
    ValueTooLarge,        // exceeds algorithmic range for (J,d)
}
```

---

## 4. Framing Semantics (Critical for Telomere)

- Every Lotus field (arity, length, payload) is encoded as a single Lotus codeword.
- The header layout used by Telomere (mode + arity + jumpstarter + len_bits + payload) is a **composition** of multiple Lotus fields.
- Telomere's `encode_lotus_header(arity, payload_bits, payload_bit_len)` builds a composite header on top of the primitive Lotus codec.
- **Self-delimiting guarantee**: after reading one complete Lotus codeword, the reader knows exactly how many bits were consumed. No external markers.

**Telomere usage pattern**:
1. Encode arity field (small integer, 1–6 or 0xFF for literal)
2. Encode length field (bit length of the following payload)
3. Encode payload (seed bits or literal bits)
4. The composite bitstream is what gets written to the `.tlmr` file.

---

## 5. Bit Ordering & Packing

- All Lotus operations are **MSB-first**.
- `BitWriter` / `BitReader` in the canonical implementation handle the packing.
- Telomere's `pack_bits(&[bool]) -> Vec<u8>` is a compatible MSB-first packer.

**Warning**: Mixing little-endian or LSB-first logic will produce non-interoperable headers.

---

## 6. Telomere-Specific Adaptations

Telomere currently maintains a hand-rolled 4-field Lotus variant in `src/header.rs`:
- `encode_lotus_arity_bits`
- `encode_lotus_len_bits`
- `encode_lotus_header`
- `decode_lotus_*` counterparts

**Migration goal (M0)**: Replace or wrap the hand-rolled version with the canonical Lotus crate so that:
- All arity/length/payload fields use the same `(J, d)` preset.
- The preset is recorded in the file format version.
- Future changes to Lotus are centralized in one dependency.

**Current Telomere implementation note** (as of 2026-05-22):
- `src/header.rs` uses a **fixed 3-bit jumpstarter** (`jumpstarter(3)` in the layout comment).
- The length field is encoded as `L = jumpstarter + 1` bits with contiguous codes across each `L`.
- This is **not** the full parametric `(J, d)` model; it is a simplified J=3, d=1-like encoding with a custom arity layer on top.
- The `encode_lotus_len_bits` / `decode_lotus_len_bits` functions implement the tier chain directly rather than calling a generic Lotus primitive.

Until the migration is complete, `src/header.rs` remains the **authoritative** implementation for Telomere. The `LOTUS_PRIMITIVE.md` document above describes the *target* canonical behavior that the migration aims to reach.

---

## 7. Recommended (J, d) Starting Point for Telomere

Start with `J=2, d=1` (current) for compatibility.

After running the tuning matrix (`docs/LOTUS_TUNING.md`), evaluate whether `J=1, d=2` yields lower average bits-per-value for Telomere's actual emitted values (arity 1/3–6, length 0–255, payload 8–256 bits).

**Decision record** will be written to `docs/LOTUS_TUNING.md` and frozen in the file format.

---

## 8. References (Internal Only)

- `src/header.rs` — current Telomere Lotus implementation
- `docs/LOTUS_TUNING.md` — generated benchmark of (J, d) presets on Telomere workloads
- `RESEARCH_PLAN.md` §11.1 — detailed rationale for the tuning experiment
- `TASK_CHECKLIST.md` — M0 item "Lotus Canonicalization & (J, d) Decision"

No external Lotus repository access is required after this document is present.

---

**This document makes the Telomere repository self-sufficient with respect to the Lotus primitive.**
