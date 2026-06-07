# Telomere exact toy model — Layer 1 report (the grounding wire)

**What this is.** The explicit recursive state machine demanded by the modeling
correction report: real entry objects, real seed enumeration to a stated depth
bound, canonical arity codes, J3D1 records, once-only literal marker,
"a block is a block is a block" recursion, explicit superposition state with a
prune delta, deterministic shuffles, strict and tolerated-bloat replacement,
pass-by-pass ledger, and decode verification. No mean-field shortcuts: nothing
in the pass loop is an average.

**What this is not.** A Telomere-scale theoretical claim. The universe is tiny
(b = 6, depth 2^19) so that enumeration is exact; its job is to ground the
distributional layer (Layer 2), which carries depth/block-size/arity as free
parameters. Per the correction report: if Layer 2 disagrees with this machine
at the same settings, Layer 2 is wrong.

Configuration: b = 6 bits, N = 3000 blocks (raw 18,000 bits), arity 1–5
(canonical codes), J3D1, depth 2^19 seeds (exact within bound), prune Δ = 16,
10 passes (8 for F-modes), input: uniform blocks, RNG seed 42.
Full per-pass data: `telomere_model_results.csv`.

---

## 1. Mode comparison (the requested A–F ledger)

| mode | configuration | final % of raw | decode verification |
|---|---|---|---|
| A | one pass only | 140.400% | **PASS** |
| B | + recursion (entry semantics) | 140.344% | **PASS** |
| C | B + superposition (Δ=16) | 140.344% | **PASS** |
| D | B + deterministic affine shuffle | 140.183% | **FAIL — order recovery** (§4) |
| E | D + superposition (Δ=16) | 140.183% | FAIL — order recovery |
| F1 | E + tolerated bloat ≤ 1 bit (8 passes) | 140.228% | FAIL — order recovery |
| F4 | E + tolerated bloat ≤ 4 bits (8 passes) | 142.900% | FAIL — order recovery |

Approved-language summary: **under this exact model at this depth bound**, no
configuration crosses 100%; recursion alone adds −0.056 pp once and stalls
(repeat adjacencies yield no new windows); shuffling sustains small per-pass
gains (−0.22 pp over 9 passes, still decaying); superposition retains state but
converts nothing at Δ=16 (§3); tolerated bloat at 1 bit is noise-level and at
4 bits compounds monotonically upward (§5).

## 2. Pass dynamics (selected; full table in CSV)

Mode B: pass 2 accepts 3 windows (saved 10 b), passes 3–10 accept 0 — without
adjacency refresh the window set is exhausted after one recursive sweep.

Mode D (shuffle): accepts per pass stay alive: 3, 3, 2, 2, 0, 2, 3, 6, 3 over
passes 2–10 (mostly arity-2 windows over 9-bit literal pairs), each saving
1–10 b. The refresh columns in the CSV show the affine permutation delivering
50–100% new windows per arity each pass, which is exactly what keeps the
accept rate nonzero. The per-pass yield is ~2–10 b on a 25,250 b file
(≈ −0.02 pp/pass) and decays as short literal pairs are consumed.

## 3. Superposition, explicitly modeled (not a ceiling argument)

State actually carried: 1,947 retained alternate candidates (noncompressive
exact arity-1 matches within Δ=16; the 236A/236B pattern), 0 pruned at Δ=16.
Window generation enumerates all main/alt combinations (≤ 2^A per window).

Result at this depth: **0 alt-involving windows ever produced an accepted
record in modes C and E** (10 passes). In F4, 5 conversions occurred but only
under a 4-bit tolerated-bloat bar, inside a net-bloating run. Mechanism visible
in the ledger: alternate forms are *longer* than mains, so alt-containing spans
are longer targets, which need *deeper* first matches — at depth 2^19 those
matches are absent. Whether deeper search changes the conversion rate is a
Layer-2 question; at this bound the retained state found nothing to convert
into.

## 4. The decode-verification finding (the toy doing its job)

Every no-shuffle mode round-trips: parse → expand recursively → original
blocks, bit-exact (A, B, C: PASS). This confirms untagged in-place recursion
("a block is a block") is self-describing without birth-pass metadata — the
design claim, verified by machine.

Every shuffle mode fails order recovery: all hash expansions verify (no
content corruption), but the original block *order* cannot be reconstructed
from the final stream. Mechanism: inverting pass t's permutation requires first
rebuilding the pre-merge entry list of pass t, which requires knowing which
records were born in pass t — information the wire deliberately does not carry.
Merges interleaved with permutations compose into a data-dependent reordering
the decoder cannot replay. Two repair directions, both with costs the current
zero-bit accounting does not charge: (i) per-layer delimitation
(FORMAT_CANONICAL §7 layer descriptors) so each layer can be fully parsed,
expanded one level, and un-permuted before recursing — amortized header cost;
(ii) restricting shuffles to schedules that commute with merging. Until one is
specified, mode D/E/F sizes are conditional results: the −0.22 pp shuffle
benefit is real in the ledger but not yet legally decodable in this
implementation. This is a format fork for the maintainer to rule on, not a
verdict.

## 5. Tolerated bloat

tol = 1: net effect indistinguishable from strict mode at this sample size
(140.228% vs 140.183% at differing pass counts; per-pass deltas are within
Poisson noise of each other). tol = 4: monotone compounding upward, +2.5 pp in
7 passes — committed losses are not recovered by later harvests at this depth.

## 6. Cross-checks against the analytic layer

- Pass-1 entry count and size (140.400%) sit where the canonical cost table
  puts them for b = 6 at this depth (the marker is 50% of a block; arity wins
  pull 150% down to 140.4%).
- The stall in mode B and the sustained-but-decaying yield in mode D are the
  behaviors the mean-field recurrence assumed; the toy now grounds them with
  explicit state. The recurrence's zero-bit-shuffle assumption, however, is
  **flagged** by §4 — it priced the permutation at 0 bits without a decodable
  construction. Layer 2 must carry that as a conditional.

## 7. Next artifact (Layer 2)

`telomere_distributional_model.py`: H_t[L, type] histograms, exact span-length
convolutions, full gain distributions P(gain ≥ g | S, A) (no 2.17-bit
constant), replacement-policy comparison (left-to-right / greedy / oracle),
superposition as state-mass with prune-delta sweep, shuffle as refresh-rate
parameter conditioned on §4, depth as a free parameter to theoretical ranges,
arity-codec families for A > 5. Validated against this toy at matched settings
before any scaled run is reported.
