# Uncapped Seed Search Derivation (V1 Format)

Full accounting for: *with uncapped seed lengths and arity bundling, does
brute-force hash-preimage search reduce the expected size of uniformly
random data?*

All numbers use exact Lotus J3D2 and J1D1 functions from the codebase.
Verified against `model_analysis/FINDINGS.md` and reproducible via
`model_analysis/full_v1_model.py`.

> **History.** A previous version of this file used V2 format (3-field
> records with 40-bit literal fragmentation cost per match). V1 uses
> fixed-size blocks with no fragmentation. This version corrects the
> format and the conclusions.

## What's correct in the argument

1. **Each seed has a positive probability of compressive match.** At every
   span size, a finite set of seed indices have records shorter than the
   span. That set is nonempty.

2. **With uncapped search, compressive matches accumulate.** The expected
   number of compressive matches is positive and grows with file size.

3. **Conditional replacement ensures the file never bloats.** A match is
   only committed when `record_bits < literal_bits`. The floor is the
   all-literal file — no worse than raw + overhead.

4. **The codec is deterministic and decodable.**

## V1 record format

A V1 record for arity `a` with seed index `i`:

```
Compressed: J1D1(a-1) + J3D2(i)     — bit-packed, no padding
Literal:    J1D1(5) + pad-to-byte + raw data
```

At arity 1, block_size 2 (span = 16 bits):
- Literal cost: 6 + 2 + 16 = 24 bits (overhead = 8 bits above raw)
- Best match:   3 + 6 = 9 bits (seed_index = 0, saves 7 bits vs raw)
- Budget:       record < 24 → seed field < 21 → indices 0..509

## Two classes of matches

Matches that beat the literal cost split into two groups:

| Class | Condition | Effect | Count (bs=2) |
|---|---|---|---|
| Beats-raw | record < 16 bits | Compresses below raw | 61 seeds |
| Beats-literal-only | 16 ≤ record < 24 | Better than literal, worse than raw | 8,128 seeds |

**Only beats-raw matches drive net compression.** Beats-literal-only
matches reduce the file vs all-literal but cannot cross below raw.

## Expected saving per match

Lotus J3D2 value density doubles per width: width w covers 2^w values.
Among beats-raw matches, the saving S = raw − record follows:

```
E[S | beats-raw] ≈ 2 bits
```

Most compressive seeds are near the budget boundary, saving 1–2 bits.
This holds regardless of span size — it's a property of the Lotus density
distribution.

## Per-block economics

For a file of N blocks at arity 1, block_size 2:

```
Literal block:     24 bits (8 bits above raw)
Avg beats-raw:     14.2 bits (1.8 bits below raw)
```

Break-even condition — file < raw:

```
P_raw × avg_rec_raw + (1 − P_raw) × literal < raw
P_raw × 14.2 + (1 − P_raw) × 24 < 16
P_raw > 8 / (8 + 1.8) = 0.816
```

Against the base probability P_raw = 9.31 × 10⁻⁴:

```
Break-even multiplier = 0.816 / 9.31e-4 = 877×
```

**At ~877× density improvement, the file crosses below raw size.**

Note: FINDINGS.md reports 824× using 6-bit overhead (marker only, no pad).
The difference is whether pad-to-byte is counted as literal overhead. Both
are defensible; the structural result is the same.

## At 100% beats-raw match rate

If every block has a beats-raw match (density multiplier > ~1,075×):

```
File = N × avg_rec_raw / 8 = 500,000 × 14.2 / 8 = 886,270 bytes
Compression: 11.4%
```

This is the theoretical maximum for V1 format at bs=2, arity 1.

## With the Proposed format (3-bit literal, no pad)

Robin's described format uses prefix-coded arity (2–3 bits) and 3-bit
literal marker with no pad-to-byte:

```
Literal: 3 + 16 = 19 bits (overhead = 3 bits)
Best match: 2 + 6 = 8 bits
```

Break-even:

```
P_raw > 3 / (3 + 2.8) = 0.517
M = 0.517 / 9.31e-4 = 555×
```

Max compression at 100% match: 17.6%. Lower overhead → earlier break-even
and higher ceiling.

## What DOESN'T work: deeper search alone

The gap = span_bits − log2(N_comp_raw) ≈ 10 bits at bs=2. Deeper search
adds seeds at higher Lotus cost, keeping the gap pinned. Raw compute alone
does not cross into net compression. The gap is a format constant.

## What DOES work: the three levers

1. **Lower literal overhead.** V1 Current (8b) → Proposed (3b) → Minimal
   (1b). Each reduction cuts the break-even multiplier.

2. **Higher avg saving per match.** Preferentially finding low-index seeds
   (saving 5–7 bits instead of 1–2) raises E[S] and lowers the break-even.

3. **Density mechanisms.** Transforms, dictionaries, or schema-native
   representations that raise the base hit probability P_raw directly.

These multiply. A format with 3-bit overhead AND a mechanism delivering
555× density achieves net compression on random data at bs=2.

## The floor guarantee

Conditional replacement ensures the file never exceeds all-literal size.
At base rates (no density mechanism), V1 at bs=2 produces a ~1.48 MB file
for 1 MB input (all-literal baseline 1.5 MB, minus a few KB from the rare
beats-literal matches). The floor is the all-literal file, not infinity.

## What this derivation proves

The mechanism **can** produce net compression. The break-even multiplier is
finite (555–877× at bs=2 depending on format). Whether a practical density
mechanism exists for real data is the open research question. The model
quantifies exactly how much density is needed — that's a target, not an
impossibility result.

## Full model

See `model_analysis/FULL_V1_MODEL.md` for the complete model covering all
format variants, density sweeps, multi-pass, superposition, and aggregate
arity. Reproducing script: `model_analysis/full_v1_model.py`.
