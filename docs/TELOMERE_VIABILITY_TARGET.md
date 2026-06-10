# Telomere Viability Target

**Current primary class: `math_candidate`** (fully charged in the proof
kernel; constituent primitives wire-proven; the full config has no wire
proof yet). Single empirical assumption: uniform hash law `P(match) = 2^-S`.

This file states the current best fully-charged configuration. The complete
result table with evidence classes is `docs/TELOMERE_RESULT_LEDGER.md`; the
machine-readable artifact is `model_analysis/proof_kernel/vnext_best.json`.

## Primary target (this revision)

`grid_heavy_phi0.5_S262144_J2` — v-next semantics:

- block bits: `8`; input model: `1,000,000` blocks (8 Mbit)
- alphabet `grid_heavy`: entry arities 1–2 (`00`,`01`), grid arities 3–4
  (`100`,`101`), BIT_LITERAL single (`110`), LITERAL_RUN (`111`) — Kraft = 1
- seed field: `J2D1` (min record 6 bits, payload cap 28) at depth 28
- pass-1 construction: φ = 0.5 of blocks exposed as singles; remaining mass
  in S0 = 262,144 literal runs (~15-bit average payload)
- refresh: **layer-masked expansion** `expand(seed) XOR mask(layer, offset)`
  — zero metadata, fixed public mask schedule, fresh = 1 every pass
  (law-validated; see ledger finding 1)
- selection: greedy deterministic; superposition delta 16 / cap 4 (earned)
- k_xor = 1 (single seed per record; MitM not needed — see ledger finding 6)

Results (`vnext_best.json`):

| metric | value |
| --- | ---: |
| ten-effective-pass minimum | **+0.9081 %/pass** |
| ten-effective-pass average | +0.9911 %/pass |
| pass-1 layer/raw | 1.5311 |
| raw payback pass | **81** |
| final/raw @ 11 / 50 / 100 | 1.386 / 1.096 / 0.958 |
| final/raw @ 200 / 500 | **0.8101 / 0.5409** |
| oracle bound (same config) | +0.9100 %/pass (greedy ≈ oracle) |
| refresh metadata | 0 bits/pass |
| uncharged passthrough | none (all run/single headers charged in-layer) |

Success bars: ≥0.1% ✓ · ≥0.2% ✓ · ≥0.5% breakthrough ✓ (non-oracle, fully
charged) · crossover ≤200 ✓ · ≤0.84@200 ✓ · ≤0.60@500 ✓ · **crossover <50 ✗**
(missing lever: pass-1 bloat; see frontier report).

## Compute story (separate from size accounting — never mixed)

Masked targets keep the seed table unsalted and shared: build `2^28`
expansions once (profile constant, shared across positions, passes, and
files), then ~O(1) masked lookups per window. Windows/pass at the modeled
1 MB input: ~1.5M junction+entry windows × 6 record kinds ≈ ~10M lookups per
pass; 81 passes to crossover, 500 to 0.54. See
`docs/INVESTOR_RESEARCH_BRIEF.md` for machine-tier tables.

## Reference floor (previous target, unchanged)

Audited BIT_LITERAL config (entry_state kernel): block 8, depth 96, J3D1,
permutation+swaps (3 bits/pass), variants 4, greedy: 0.1328 %/pass min,
payback 126 effective, 0.486 @ 500 — `bit_literal_target.json`. The v-next
kernel reproduces this lane conservatively (0.0994 %/pass under the same
constraints), so the two independently-built recurrences agree within ~25%
with the new kernel reading lower.

## Decode story per mechanism (proofs in model_analysis/proof_kernel/)

- BIT_LITERAL single `[110][8 raw]`: `bit_literal_decode_proof.py`
- LITERAL_RUN `[111][Lotus(bit_len)][payload]` (length-prefix; adversarial
  in-payload codewords; odd tail): `literal_run_decode_proof.py`
- layer-masked / salted expansion, nested two layers, zero metadata:
  `position_salt_decode_proof.py`
- k=2 XOR records (salted seed #1 + shared unsalted table):
  `mitm_xor_decode_proof.py`

All proofs assert exact round trip, self-delimitation, and
wire bits == charged bits.

## Reproduction

```powershell
python model_analysis/proof_kernel/vnext_search.py --stage rank
python model_analysis/proof_kernel/vnext_search.py --stage final
python model_analysis/proof_kernel/freshness_law_validation.py
```
