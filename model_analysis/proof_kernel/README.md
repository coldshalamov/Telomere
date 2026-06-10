# Telomere Proof Kernel

Evidence-level-4 mathematical kernel (see `docs/PROOF_TARGET.md`). It does not
run broad seed searches. It models exact seed-record hit probability,
current-layer entry recurrences with **computed freshness**, earned
superposition variants, **charged discrimination channels** for bit-layer
rechunking, refresh operators with decode contracts, selection bounds, and
concentration.

## Two invariants this revision enforces

1. **Freshness is computed, never assumed.** The seed search is deterministic:
   an unchanged window at an unchanged depth returns the same null forever.
   Windows split per pass into fresh mass (replacement cascade, equal-size
   swaps, charged permutation, chunk-boundary shift) and stale mass (only the
   incremental depth slice). `no_refresh` decays to cascade-only; the ledger
   reports the computed refresh coefficient.

2. **Unchanged chunks are not free.** A rechunked layer mixes records with
   verbatim chunks; the Kraft-complete arity alphabet cannot self-discriminate
   and replacement positions are content-dependent. Chunk lanes must carry a
   charged channel: `explicit_flag` (1 bit/element), `implicit_selector`
   (decode-by-replay with charged per-fire stuffing escapes — provably
   Kraft-dominated: gain mass ~ sum cnt*g*2^-S vs fire mass ~ sum cnt*2^g*2^-S,
   and 2^g > g), or `uncharged_diagnostic` (the old broken accounting, always
   `failed_audit_uncharged_passthrough`, kept only as the zero-escape bound).

## Modules

| file | role |
| --- | --- |
| `costs.py` | exact canonical v1 arity and Lotus/J3D1 costs; validates against `src/bin/v1_cost_table.rs` |
| `hit_distribution.py` | exact `M(a,r,D)`, fresh hit probabilities, incremental-depth stale channel |
| `entry_state.py` | freshness recurrence, charged channels, pass ledger |
| `span_distribution.py` | arity-a span distributions from current entry histograms |
| `selection_bounds.py` | left-to-right lower, greedy deterministic, oracle upper bound |
| `superposition_model.py` | earned retained variants and whole-window bundles |
| `refresh_model.py` | refresh operators with story A/B decode contracts and charged metadata |
| `implicit_selector.py` | exact Kraft escape economics + dominance verification |
| `bit_literal_decode_proof.py` | toy wire decode proof for the BIT_LITERAL primitive |
| `viability_search.py` | validation, lane×channel sweep, recurrences, audit gates, report writer |

## Current results

- **Audited target (requires BIT_LITERAL, a v-next primitive):** block 8 bits,
  depth 96, record-aligned (no rechunk), `permutation_plus_neutral_swaps`
  (3 charged bits/pass), 4 variants: **0.1328% min / 0.1623% avg** over ten
  effective passes, raw payback at effective pass **125**, final/raw 0.486 at
  pass 500. `viability_practical_candidate`. See
  `docs/TELOMERE_VIABILITY_TARGET.md` and `bit_literal_target.json`.
- **Canonical-v1 frontier (no new primitive):** same lane with 10-bit literal
  wrap: 0.0430% min — below target, no crossover ≤ 500.
  See `docs/TELOMERE_FRONTIER_REPORT.md`.
- **Re-classed:** the former headline (uncharged 4-bit rechunk, 0.53%/pass) is
  `failed_audit_uncharged_passthrough`. Charging its channel flips it negative
  (explicit flag −24.7%/pass; implicit selector −1.67%/pass).

## Reproduce

```powershell
python model_analysis/proof_kernel/viability_search.py --write-artifacts
python model_analysis/proof_kernel/bit_literal_decode_proof.py
cargo run --quiet --bin v1_cost_table   # re-pin exact costs locally
```

Artifacts: `best_config.json` (v1 frontier), `bit_literal_target.json`
(audited target), `sweep_summary.json`, `top_profiles.csv`,
`docs/TELOMERE_VIABILITY_TARGET.md`, `docs/TELOMERE_FRONTIER_REPORT.md`.

Note: this revision's artifacts were generated in a sandbox without cargo;
`costs.py` is unchanged from the revision pinned against the Rust probe, but
re-run the probe locally after any format work.
