# Telomere — Probability Model Results

First-principles probability model for Telomere's generative seed-search
compression. All results use exact Lotus bit-cost functions extracted from the
codebase (`scripts/telomere_power_model.py`), verified in Wolfram, and
reproducible via the interactive tool (`telomere_model.html`) in this folder.

## The model

A span of `s` bits is compressible when a seed index `i` exists such that
`expand(seed(i))[0..s] == target` and encoding `i` plus record metadata costs
fewer than `s` bits. Under cryptographic hash expansion, each seed hits a given
`s`-bit target with probability `2^{-s}`, independently.

The **compressive seed count** `N_comp` is the number of seed indices whose
Lotus-encoded record costs strictly less than `s` bits. A compressive match
occurs with probability:

    P = 1 - (1 - 2^{-s})^{N_comp}  ≈  N_comp * 2^{-s}   (for small P)

The **gap** = `s - log2(N_comp)` determines this probability. When gap > 0,
`P < 1` and compression is probabilistic. The gap is set entirely by record
format overhead.

## Lotus encoding — exact bit costs

Telomere uses the Lotus self-delimiting integer codec. Two configurations:

**J3D2** (`j_bits=3, tiers=2`) — used for seed indices, span lengths, and V2 tags:

| Value range | Bit cost | Overhead above log2(v+1) |
|---|---|---|
| 0 | 6 | 6.0 |
| 1–4 | 9 | 7.0–6.7 |
| 5–12 | 10 | 7.4–6.4 |
| 13–28 | 11 | 7.2–6.1 |
| 29–60 | 12 | 7.1–6.1 |
| 61–124 | 14 | 8.0–7.0 |
| 125–252 | 15 | 8.0–7.0 |
| 253–508 | 16 | 8.0–7.0 |

Overhead oscillates between ~6 and ~8 bits and grows as O(log log v).
Proportionally, overhead shrinks (100% at value 0, ~16% at value 253).
But the gap depends on **absolute** overhead, which is always 6–8 bits.

Note: J3D2 costs are not monotonically stepped — there are gaps in the cost
function (e.g. no values have cost 7, 8, or 13) due to the tiered width
structure.

**J1D1** (`j_bits=1, tiers=1`) — used for arity headers in V1:

| Value | Meaning | Bit cost |
|---|---|---|
| 0 | arity 1 | 3 |
| 1 | arity 2 | 5 |
| 2 | arity 3 | 5 |
| 3 | arity 4 | 5 |
| 4 | arity 5 | 5 |
| 5 | literal | 6 |

## Record formats and their gaps

**V1 record**: `J1D1(arity_value) + J3D2(seed_index)`

For arity `a`, span = `a * block_size * 8` bits. Record cost =
`J1D1(a-1) + J3D2(seed_index)`. A seed is compressive when this total < span bits.

At block_size=4 (32 bits per block):

| Arity | Span bits | Header | Budget | N_comp | Gap | P_base |
|---|---|---|---|---|---|---|
| 1 | 32 | 3 | 29 | 1,048,574 | 12.0 | 2.44 × 10^{-4} |
| 2 | 64 | 5 | 59 | 5.63 × 10^{14} | 15.0 | 3.05 × 10^{-5} |
| 3 | 96 | 5 | 91 | 6.04 × 10^{23} | 17.0 | 7.63 × 10^{-6} |
| 4 | 128 | 5 | 123 | 2.60 × 10^{33} | 17.0 | 7.63 × 10^{-6} |
| 5 | 160 | 5 | 155 | 5.58 × 10^{42} | 18.0 | 3.81 × 10^{-6} |

The gap grows with arity in V1 (12 bits at arity 1, up to 18 at arity 5)
because the relationship between span bits and Lotus tier boundaries is
nonlinear. Arity 1 has the best economics.

**V2 record**: `J3D2(tag=0) + J3D2(span_len-1) + J3D2(seed_index)`

Three Lotus fields. Theoretical format gap (span - log2(N_comp)) is ~23–26
bits at practical span sizes. However, V2's N_comp is so large that at
search depths 2–8 the effective gap is ~32 bits — set by available seed
count, not format overhead. `POWER_MODEL.md` reports 31.99 bits, which
correctly reflects this search-depth-limited regime.

**Minimal (theoretical)**: 1-bit type flag + Lotus-encoded seed. Gap ~ 9–11 bits
(the 1-bit flag saves 2 bits vs V1's 3-bit header, but the Lotus seed cost
remains). Break-even multiplier drops to ~155x at bs=2 (vs 824x in V1) due to
the 1-bit literal overhead. With ideal encoding (no Lotus overhead), gap reduces
to ~1 bit, but no practical self-delimiting code achieves this.

## Gap invariance

The gap does not close with deeper seed search. Increasing max seed length
from depth 2 to depth 8 adds more seeds, but the Lotus cost of encoding
those larger indices grows at the same rate. The gap stays pinned.

This is the key structural result: **raw compute (deeper search) does not
by itself cross into net compression.** The gap is a format-overhead
constant, not a search-depth variable.

What *does* change the effective gap:

1. **Format choice**: V1 gap ranges 12–18; V2 gap is ~32. Format matters.
2. **Density-raising mechanisms**: Transforms, dictionaries, or presets that
   make target spans more likely to appear in the seed expansion space
   effectively multiply the hit rate.

## Aggregate arity

Each arity level is an independent trial — arity 1 searches 1-block spans,
arity 2 searches 2-block spans, etc. A position is compressible if *any*
arity level finds a compressive match.

At block_size=4, arity 1 dominates completely. P_1 = 2.44 × 10^{-4} while
P_2 = 3.05 × 10^{-5} (8x smaller). P_3 through P_5 are negligible.
Aggregate improvement: ~1.12x. This holds at other block sizes too —
aggregate arity is real but modest.

## Break-even analysis

The **break-even multiplier** is the hit-rate gain (over random baselines)
needed for expected savings to exceed expected literal overhead across a
whole file.

Per-span economics at arity 1:
- Compressive match: saves `span_bits - header - seed_cost` bits.
  Average saving per match: ~2 bits (dominated by seeds near the budget
  boundary).
- Literal fallback: costs 6 bits overhead (J1D1 literal marker = 6 bits).
- Break-even condition: `P × (avg_saving + literal_overhead) > literal_overhead`
  i.e. `P > 6 / (2 + 6) = 0.75`

This is the core constraint. 75% of spans must find compressive matches
for net compression. Against the base probabilities:

| Block size | Span bits | P_base | Break-even multiplier |
|---|---|---|---|
| 2 | 16 | 9.31 × 10^{-4} | **824x** |
| 3 | 24 | 4.88 × 10^{-4} | **1,535x** |
| 4 | 32 | 2.44 × 10^{-4} | **3,066x** |
| 8 | 64 | 1.22 × 10^{-4} | **6,144x** |
| 16 | 128 | 3.05 × 10^{-5} | **24,576x** |

Smaller block sizes have better economics. Block_size=2 (16-bit spans) is
the most favorable regime in V1 format, requiring an 824x density
improvement.

The break-even is hard because the average savings per match is only ~2 bits
while the literal overhead is 6 bits per span. Each compressive match must
"pay for" ~3 literal spans' overhead.

## What determines the break-even

Three independent levers:

1. **Literal overhead** (currently 6 bits in V1). Lower literal overhead
   directly reduces the break-even. A 1-bit literal flag would cut the
   multiplier roughly 6x. Format design is a lever.

2. **Average savings per match** (~2 bits in V1). Currently dominated by
   seeds near the budget boundary that save only 1 bit. If a mechanism
   could preferentially find LOW-index seeds (high savings), this improves.

3. **Base hit probability** (P_base). A dictionary or transform that makes
   natural data more likely to align with seed expansions raises P directly.

These multiply: a format with 2-bit literal overhead AND a dictionary giving
10x density improvement could achieve break-even at bs=4.

## What is proven

1. **The mechanism works.** Planted data compresses (256 -> 168 bytes for
   `planted-sha256-arity2`). Codec, search, and accounting are correct.

2. **The probability model is exact.** Lotus bit costs are computed from the
   actual codec algorithm, not approximated. Results match `POWER_MODEL.md`.

3. **The gap is search-depth-invariant.** Deeper search does not close the
   gap. This is analytic, not empirical.

4. **Format overhead matters.** V1's 2-field format has gap 12 at bs=4;
   V2's 3-field format has gap ~32. The choice of record format is a major
   lever.

5. **The break-even target is quantified.** At block_size=2 with V1 format,
   824x density improvement enables net compression. At bs=4, it's 3,066x.
   These are concrete engineering targets.

6. **Average savings per match is ~2 bits**, regardless of span size. This is
   because compressive seeds are exponentially concentrated near the budget
   boundary.

## What is open

1. **Whether a practical density-raising mechanism exists.** The break-even
   says what's needed. Whether a dictionary, transform, or preset can deliver
   that on real data — at any block size — is the open question.

2. **Optimal record format.** The 6-bit literal overhead in V1 is a major
   driver of the break-even. A format with lower literal overhead (even 2–3
   bits) would substantially change the economics. Exploring minimal
   self-delimiting formats is a concrete research direction.

3. **Schema-native dictionary performance.** The level 45 probe in
   `VIABILITY.md` is the only lane that has flickered positive. It promoted
   once before level 46 blocked it on paired shadow controls. This is a lead,
   not a result.

4. **Preferential low-index matching.** If a mechanism could bias toward
   low-index seeds (which save more bits per match), the average savings
   per match would increase, reducing the break-even multiplier.

5. **Multi-pass behavior with density mechanisms.** The model currently covers
   single-pass compression. Whether subsequent passes can compound gains on
   already-compressed output is unstudied.

## Methodology

All Lotus bit-cost computations use the exact algorithm from
`scripts/telomere_power_model.py` (lines 367–408), which matches the Lotus
crate at `../lotus/src/lib.rs`. The `lotus_width_for_value` and
`lotus_encoded_bit_len` functions are ported faithfully to the interactive
tool's JavaScript.

Verification covers: Lotus bit costs for value ranges 0–1000, N_comp
calculations at multiple block sizes and depths, aggregate arity
probabilities, break-even multiplier derivation, and average savings per
compressive match.

The interactive tool (`telomere_model.html`) implements the same model and
lets any parameter be varied to explore the space.
