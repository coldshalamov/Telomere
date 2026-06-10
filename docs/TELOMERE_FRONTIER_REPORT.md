# Telomere Frontier Report

What the current proof kernel does NOT yet reach, where the frontier sits,
and the missing multipliers. Companion to `TELOMERE_VIABILITY_TARGET.md`
(what is reached) and `TELOMERE_RESULT_LEDGER.md` (every result + class).

## Open bar: raw crossover < 50 passes

Best fully-charged payback this revision: **pass 81**
(`grid_heavy_phi0.5_S262144_J2`). The binding constraint is pass-1 bloat:
the junction-dense states that sustain ~1 %/pass cost 1.44–1.59× at pass 1
(headers for ~256k runs + 500–750k singles), and ~0.4–0.5 of that must be
re-earned before crossover. The ε-bloat end exists (1.0027× at S0=1024,
validated) but is junction-starved (+0.0002 %/pass — rate needs junctions).

Missing multiplier to <50: hold ≥0.7 %/pass at pass-1 bloat ≤ ~1.15 — i.e.
**~3× better rate-per-header-bit** than the current frontier. Candidate
levers, in order of expected value:

1. **Adaptive segmentation schedules** (start ε-bloat, split runs only where
   records land — re-segmentation is charged but only spent on demonstrated
   hit neighborhoods; the kernel currently models static S0 only).
2. **Cheaper junctions**: 2-bit run marker layers (`run_cheap` alphabet) on
   early passes via layer-indexed alphabet schedules (zero metadata).
3. **Trajectory optimization** over (φ, S0, depth, alphabet) per pass — the
   500-pass recurrence is cheap to differentiate numerically; greedy
   per-pass settings are probably not optimal (ledger: handoff priority 5,
   still open).

## Frontier structure (151 fully-charged configs)

See `model_analysis/proof_kernel/charts/bloat_payback_frontier.png` and
`vnext_top_profiles.csv`. Shape: payback is minimized at interior mixes
(φ≈0.25–0.5, S0≈N/4..N/15, J2D1, masked) — 68–93 passes; rate is maximized
at junction-saturated mixes (φ=0.75, S0=N/4) — ~1.0–1.02 %/pass; the pure
ends (φ=1 BIT_LITERAL-only; φ=0 giant runs) are dominated.

## Dead and bounded lanes (do not relearn)

- Position-only salted refresh: **dead by deadlock** (measured zero accepts
  from pass 3; analytic cause; layer-indexed masking is the fix).
- Bit-rechunk with uncharged passthrough: `failed_audit`; with explicit
  flags −24.7 %/pass; with replay escapes −1.67 %/pass and Kraft-dominated
  at every point (`implicit_selector.py` ledger).
- k=2 XOR records at B=8: ~9× rate cost; bounded niche at spans ≥ ~60 bits.
- Naive grid windows without clean/dirty pricing: the walk DP exists because
  short runs laundered dirty mass as clean (fixed this revision; leaders
  re-priced 1.17 → 1.01 %/pass).

## Theorem targets still open (handoff priority 6)

- Format-independent upper bound on sustained %/pass given (literal floor,
  gap structure). The implicit-selector dominance proof generalizes the
  rechunk family only.
- Monotone ε-bloat property of LITERAL_RUN profiles (model-validated;
  needs a proof over all pass schedules).
- Permutation pair-exhaustion boundary T ~ N (moot for masked lanes,
  relevant if masking is ever restricted).

## Reproduction

```powershell
python model_analysis/proof_kernel/vnext_search.py --stage rank
python model_analysis/proof_kernel/vnext_search.py --stage final
```
