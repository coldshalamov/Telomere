# Telomere Proof Kernel

This directory is the evidence-level-4 mathematical kernel described in
`docs/PROOF_TARGET.md`. It does not run broad seed searches. It models exact
seed-record hit probability, current-layer entry recurrences, superposition,
refresh rules, deterministic bitstream rechunking, selection bounds, and
concentration.

## Modules

| file | role |
| --- | --- |
| `costs.py` | exact canonical v1 arity and Lotus/J3D1 costs; validates against `src/bin/v1_cost_table.rs` |
| `hit_distribution.py` | exact `M(a,r,D)`, hit probabilities, and full gain tails |
| `entry_state.py` | `H_t[L, kind, variant_state]` state recurrence and pass ledger |
| `span_distribution.py` | arity-a span distributions from current entry histograms |
| `selection_bounds.py` | left-to-right lower selector, greedy deterministic estimate, oracle upper bound |
| `superposition_model.py` | retained neutral/bloat variants, whole-window bundles, and opportunity multipliers |
| `refresh_model.py` | refresh rules, charged metadata, and decode proof sketches |
| `concentration.py` | bounded-differences radius for large files |
| `viability_search.py` | validation, innovation loop, bounded sweep, recurrence, and report writer |

Legacy exploratory helpers (`run_surface.py`, `state_recurrence.py`,
`superposition.py`, and `break_even_surface.py`) are not the acceptance path for
the current proof target.

## Reproduce

```powershell
python model_analysis/proof_kernel/viability_search.py --write-artifacts
```

The command writes the compact acceptance artifacts:

- `model_analysis/proof_kernel/best_config.json`
- `model_analysis/proof_kernel/sweep_summary.json`
- `model_analysis/proof_kernel/top_profiles.csv`
- `docs/TELOMERE_VIABILITY_TARGET.md`

## Current Successful Profile

The current generated success path uses a fixed decoder profile with:

- `block_bits = 8`
- `arity_cap = 5`
- `depth_schedule_bits = [16]`
- `initial_literal_overhead_bits = 10`
- `rechunk_schedule_bits = [4]`
- `refresh = superposition_derived_refresh`
- retained bloat enabled, equal-size retained variants disabled, prune delta `8`,
  max variants `4`

The report also preserves faster high-working-state and oracle upper-bound
category winners separately. `best_config.json` points at the practical capped
profile when it clears the raw-crossover gate.

The fixed 4-bit rechunk changes only the next pass's profile-known entry
boundaries. It preserves the charged bitstream length and assumes no per-file
sidecar or selector map. If an implementation multiplexes profiles, it must
charge the profile selector separately.

The cost probe can also be run directly:

```powershell
cargo run --quiet --bin v1_cost_table
```
