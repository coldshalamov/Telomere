# Telomere V1 — Full Probability Model

Complete first-principles model for V1 seed-search compression. All numbers
from exact Lotus bit-cost functions (`header.rs`, `telomere_power_model.py`).
Reproducing script: `full_v1_model.py` in this directory.

## Core question

With uncapped seed lengths and conditional replacement, can brute-force
hash-preimage search reduce file size below raw input size?

**Answer: yes, given sufficient hit density.** The break-even multiplier
is finite and quantified for every format variant. The density target is
the open research question — not whether the mechanism works.

## Two classes of matches

This is where previous analyses went wrong. Matches that beat the literal
cost come in two classes:

1. **Beats-raw** (`record < raw_bits`): these actually compress below raw.
2. **Beats-literal-only** (`raw ≤ record < literal`): these reduce the file
   vs all-literal but stay above raw. They help, but they can't cross the
   line alone.

Only beats-raw matches drive net compression. The density sweep must track
both classes separately.

## Format variants

Three formats analyzed. All use Lotus J3D2 for seed indices.

**V1 Current (J1D1)** — what the code implements today.
Header: J1D1 Lotus (arity 1 = 3b, literal = 6b). Literal pad-to-byte +
raw data. Overhead per literal block: 8 bits (6b marker + 2b pad).

**Proposed (prefix-coded)** — the design Robin described.
Header: prefix code (arity 1 = 2b "00", arity 2 = 2b "01", arity 3 = 3b
"100", literal = 3b "111"). Bit-packed, no pad. Overhead: 3 bits.

**Minimal (1-bit flag)** — theoretical lower bound with self-delimiting seed.
1-bit type flag + Lotus seed. Overhead: 1 bit.

## Results summary

All at 1 MB input, arity 1.

| Format | BS | OH | Avg beats-raw | Save vs raw | P_raw | Break-even M | Max comp |
|---|---|---|---|---|---|---|---|
| V1 Current | 2 | 8b | 14.2b | 1.8b | 9.31e-4 | **875x** | 11.4% |
| V1 Current | 3 | 8b | 22.0b | 2.0b | 4.88e-4 | **1,638x** | 8.3% |
| V1 Current | 4 | 8b | 30.0b | 2.0b | 2.44e-4 | **3,272x** | 6.3% |
| Proposed | 2 | 3b | 13.2b | 2.8b | 9.31e-4 | **554x** | 17.6% |
| Proposed | 3 | 3b | 22.0b | 2.0b | 9.76e-4 | **614x** | 8.3% |
| Proposed | 4 | 3b | 30.0b | 2.0b | 4.88e-4 | **1,227x** | 6.3% |
| Minimal | 2 | 1b | 13.6b | 2.4b | 1.91e-3 | **155x** | 14.8% |

**Note on FINDINGS.md values.** FINDINGS.md reports 824x / 1,535x / 3,066x
for V1 Current. The difference is overhead accounting: FINDINGS.md uses 6
bits (marker only), this model uses 8 bits (marker + 2-bit pad-to-byte in
the all-literal baseline). Both are defensible. The pad cost is
context-dependent in mixed streams. Structural conclusions are identical
either way.

## Break-even formula

```
P_raw > OH / (avg_saving + OH)
```

Where:
- `P_raw` = probability a block has a beats-raw match
- `OH` = literal overhead bits above raw (format-dependent)
- `avg_saving` = raw_bits − avg_beats_raw_record (~2 bits, all formats)

The multiplier M = P_needed / P_base. A density-raising mechanism must
deliver M× the random baseline hit rate.

## Why avg saving is always ~2 bits

Lotus J3D2 value density doubles with each width increase: width w covers
2^w values, width w+1 covers 2^(w+1). Given a compressive match, the
saving S = span − record follows:

```
Pr(S ≥ k | compressive) ≈ 2^(−k)
E[S | compressive] ≈ 2 bits
```

Most compressive seeds are clustered near the budget boundary, saving 1–2
bits. Deeply compressive seeds (saving 10+ bits) are exponentially rare.
This holds regardless of span size.

## Density sweep (V1 Current, bs=2)

Shows file size at various density multipliers. Two-class model: P_raw and
P_lit tracked separately, capped at 1.0.

| M | P_raw | P_lit | File bytes | vs raw |
|---|---|---|---|---|
| 1x | 0.0009 | 0.125 | 1,484,353 | +484,353 |
| 100x | 0.093 | 1.000 | 1,332,634 | +332,634 |
| 500x | 0.465 | 1.000 | 1,149,390 | +149,390 |
| 875x | 0.815 | 1.000 | ~1,000,000 | **break-even** |
| 1,000x | 0.931 | 1.000 | 920,336 | **−79,664 (8.0%)** |
| 2,000x | 1.000 | 1.000 | 886,270 | −113,730 (11.4%) |

At M > ~1,000, P_raw saturates and compression plateaus at max = 11.4%.

## Density sweep (Proposed, bs=2)

| M | P_raw | P_lit | File bytes | vs raw |
|---|---|---|---|---|
| 1x | 0.0009 | 0.008 | 1,186,490 | +186,490 |
| 100x | 0.093 | 0.777 | 1,086,506 | +86,506 |
| 500x | 0.465 | 1.000 | 965,717 | **−34,283 (3.4%)** |
| 554x | 0.516 | 1.000 | ~1,000,000 | **break-even** |
| 1,000x | 0.931 | 1.000 | 842,148 | −157,852 (15.8%) |
| 2,000x | 1.000 | 1.000 | 823,770 | −176,230 (17.6%) |

Lower overhead → earlier break-even and higher max compression.

## Conditional replacement

The system never commits a record worse than literal. Floor = all-literal
file size. At base rates (no density mechanism), conditional replacement
saves a few KB vs all-literal but cannot reach raw — the beats-literal-only
matches reduce the gap but don't cross it.

## Multi-pass

Each pass works on the new byte landscape. With conditional commit, savings
compound but diminish. At base rates, multi-pass converges quickly (each
pass saves ~1% less than the previous). Multi-pass does NOT close the gap
to raw without a density mechanism — it's working the same probability
space with slightly different byte patterns.

## Superposition

A block can hold a non-compressive match in reserve (original = block A,
seed match = block B). Later passes see block B's bytes and may find a
compressive match for it. The probability of second-level matches is the
same order as first-level (same Lotus structure, same span size). This
is a real mechanism but doesn't change the base-rate economics — it
effectively adds one more trial at the same probability.

## Gap invariance

The gap = span_bits − log2(N_comp) does not close with deeper search.
Adding more seed indices adds them at higher Lotus cost, keeping the gap
constant. At bs=2 arity 1: gap = 10.1 bits across all search depths.

**Raw compute alone does not cross into net compression.** The gap is a
format-overhead constant.

## Three levers

The break-even decomposes into three independent levers:

1. **Literal overhead** — format design. V1 Current: 8b. Proposed: 3b.
   Minimal: 1b. Going from 8b to 3b cuts the break-even multiplier ~40%.

2. **Average saving per match** — seed selection strategy. Currently ~2
   bits (geometric boundary). Preferentially finding low-index seeds
   (high savings) would increase this.

3. **Base hit probability** — density mechanisms. Transforms, dictionaries,
   grammar tables that make real data align with seed expansions. This is
   the main research lever. The break-even quantifies exactly how much
   improvement is needed.

## What this proves

1. **The mechanism works.** Given sufficient density, every format variant
   achieves net compression. The break-even is finite.

2. **Format overhead is the dominant lever in the design space.** V1
   Current (8b OH) needs 875x density. Proposed (3b OH) needs 554x.
   Minimal (1b OH) needs 155x. A 7-bit reduction in literal overhead
   cuts the required density 5.6×.

3. **The gap is real but not a death sentence.** It's a quantified
   parameter: ~10 bits at bs=2 in V1, ~9 bits in Proposed. The
   break-even multiplier translates this gap into an engineering target.

4. **Smaller block sizes have better economics.** bs=2 dominates at every
   format. The break-even grows roughly linearly with block size.

## Corrections to prior analyses

**UNCAPPED_DERIVATION.md** uses V2 format (3-field records, 40-bit
fragmentation cost per literal split). V1 has no fragmentation — it uses
fixed-size blocks. The V2 analysis concludes "net per match ≈ −38 bits"
which is correct for V2 but inapplicable to V1. V1's per-match economics
are net positive for beats-raw matches (saving ~2 bits each) with only
6–8 bits literal overhead per non-matched block.

**Previous model version** (in this session) incorrectly concluded "V1
Current CANNOT compress at ANY density" because it used beats-literal
probability for the density sweep instead of beats-raw. The corrected
model shows all formats can compress.

## Open question

The break-even multiplier is the engineering target. At bs=2 with the
Proposed format, a density mechanism delivering 554× the random hit rate
enables net compression. Whether such a mechanism exists for real data —
via reversible transforms, public presets, dictionaries, or schema-native
representations — is the open research question.

The schema-native dictionary probe (VIABILITY level 45) is the only
experimental lane that has flickered positive.
