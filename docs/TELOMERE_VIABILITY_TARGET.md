# Telomere Viability Target

This report separates per-pass drift from raw-size payback. A configuration
is a viability target only if it clears the current-layer floor, uses a
deterministic selector, survives conservative variant discounting, and shows
`final/raw < 1.0` within `200` effective passes.

Current primary class: `viability_practical_candidate`.

## Category Winners

| category | min current delta % | final/raw 11 | final/raw 200 | final/raw 500 | payback effective pass | selector | rechunk | variants cap | class |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| `highest_per_pass_drift` | 0.527368 | 2.113318600 | 0.777941814 | 0.159232551 | 152 | `oracle_weighted_interval` | `3` | 16 | `component_oracle_upper_bound` |
| `highest_per_pass_drift_deterministic` | 0.522658 | 2.114374738 | 0.785327173 | 0.163043829 | 153 | `greedy_largest_gain` | `3` | 16 | `viability_high_working_state` |
| `fastest_raw_payback` | 0.502443 | 1.099451108 | 0.424348701 | 0.093637239 | 29 | `greedy_largest_gain` | `4` | 16 | `viability_high_working_state` |
| `best_practical_memory_compute` | 0.489717 | 2.121718950 | 0.838942909 | 0.192363245 | 164 | `greedy_largest_gain` | `4` | 4 | `viability_practical_candidate` |

## Configuration

- block bits: `8`
- arity cap: `5`
- seed-depth bits: `16`
- depth schedule bits: `[16]`
- initial literal overhead bits: `10`
- rechunk schedule bits: `4`
- selection policy: `greedy_largest_gain`
- refresh rule: `superposition_derived_refresh`
- superposition: `{'prune_delta_bits': 8, 'max_variants_per_position': 4, 'equal_size_allowed': False, 'bloat_tolerant_retained': True}`
- refresh metadata bits per pass: `0`
- rechunk metadata bits per pass: `0` because the chunk size is fixed by
  this decoder profile; a multiplexed implementation must charge its profile ID.
- final charged/raw ratio after `11` modeled passes: `2.121718950`
- final/raw after `50` passes: `1.752016905`
- final/raw after `100` passes: `1.370680724`
- final/raw after `200` passes: `0.838942909`
- final/raw after `500` passes: `0.192363245`
- raw payback modeled pass: `165`
- raw payback effective pass: `164`
- ten-effective-pass minimum: `0.489717%`
- ten-effective-pass average: `0.489717%`
- concentration radius at alpha `1e-9`: `±0.990406` percentage points
- max expected live variants per entry: `4.000000`
- working variant entries proxy: `17827820.16`
- max optimistic/conservative multiplier ratio: `1.008065`

## Raw-Crossover Curve

| modeled passes | final/raw |
| ---: | ---: |
| 11 | 2.121718950 |
| 50 | 1.752016905 |
| 100 | 1.370680724 |
| 200 | 0.838942909 |
| 500 | 0.192363245 |

## Audit Verdict

- earned variants, not cap assumed: `True`
- actual gain path: `conservative discounted opportunity multiplier`
- optimistic independent-combo gain: reported in the ledger only as an upper-bound diagnostic
- selector viable without side table: `True`
- oracle upper bound: `False`
- raw crossover within 200 effective passes: `True`
- final collapse serializes encoder-only retained state: `False`
- refresh/rechunk decodable: `True`
- metadata sidecar OK: `True`
- compute/memory profile: `practical_capped`

## Ablation Table

| disabled mechanism | active change | min current delta % | contribution vs best | final/raw 11 | final/raw 200 | payback effective pass | class |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `no_equal_size_replacements` | False | 0.489717 | 0.000000 | 2.121718950 | 0.838942909 | 164 | `viability_practical_candidate` |
| `no_retained_bloat` | True | 0.445929 | -0.043789 | 2.132505345 | 0.916317377 | 180 | `viability_practical_candidate` |
| `no_superposition` | True | 0.445929 | -0.043789 | 2.132505345 | 0.916317377 | 180 | `viability_practical_candidate` |
| `no_rechunk` | True | 0.044460 | -0.445257 | 2.218564102 | n/a | none | `frontier_below_0_1` |
| `no_phase_rotation` | False | 0.489717 | 0.000000 | 2.121718950 | 0.838942909 | 164 | `viability_practical_candidate` |
| `greedy_instead_of_oracle` | False | 0.489717 | 0.000000 | 2.121718950 | 0.838942909 | 164 | `viability_practical_candidate` |

## Equations

For arity `a`, span size `S`, seed-depth `D`, and record budget `r`:

```text
M(a,r,D) = count(seed records with canonical J3D1 cost <= r and seed index < 2^D)
p(min_record <= r | S,a,D,m) = 1 - exp(-M(a,r,D) * m / 2^S)
E[gain per window] = sum_{g>=1} p(min_record <= S-g | S,a,D,m)
net_delta_pct_current = 100*(bits_before - bits_after - charged_metadata_bits)/bits_before
```

`m` is the retained-variant opportunity multiplier after per-entry
superposition and whole-window retained bundles. Rechunking changes only the
profile-known current entry boundaries; it does not remove bits from
`bits_before` and does not add file-specific side information.
The model reports optimistic independent-combo multipliers, but charged
expected gain uses the conservative shared-entry discount.

## Cost Table

The table below is generated from the exact Python cost model after validating
against `cargo run --quiet --bin v1_cost_table`.

| payload width | J3D1 bits | arity 1 | arity 2 | arity 3 | arity 4 | arity 5 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | 7 | 7 | 8 | 8 | 8 |
| 2 | 7 | 9 | 9 | 10 | 10 | 10 |
| 3 | 8 | 10 | 10 | 11 | 11 | 11 |
| 4 | 9 | 11 | 11 | 12 | 12 | 12 |
| 5 | 10 | 12 | 12 | 13 | 13 | 13 |
| 6 | 12 | 14 | 14 | 15 | 15 | 15 |
| 7 | 13 | 15 | 15 | 16 | 16 | 16 |
| 8 | 14 | 16 | 16 | 17 | 17 | 17 |
| 9 | 15 | 17 | 17 | 18 | 18 | 18 |
| 10 | 16 | 18 | 18 | 19 | 19 | 19 |
| 11 | 17 | 19 | 19 | 20 | 20 | 20 |
| 12 | 18 | 20 | 20 | 21 | 21 | 21 |
| 13 | 19 | 21 | 21 | 22 | 22 | 22 |
| 14 | 21 | 23 | 23 | 24 | 24 | 24 |
| 15 | 22 | 24 | 24 | 25 | 25 | 25 |
| 16 | 23 | 25 | 25 | 26 | 26 | 26 |
| 17 | 24 | 26 | 26 | 27 | 27 | 27 |
| 18 | 25 | 27 | 27 | 28 | 28 | 28 |
| 19 | 26 | 28 | 28 | 29 | 29 | 29 |
| 20 | 27 | 29 | 29 | 30 | 30 | 30 |
| 21 | 28 | 30 | 30 | 31 | 31 | 31 |
| 22 | 29 | 31 | 31 | 32 | 32 | 32 |
| 23 | 30 | 32 | 32 | 33 | 33 | 33 |
| 24 | 31 | 33 | 33 | 34 | 34 | 34 |
| 25 | 32 | 34 | 34 | 35 | 35 | 35 |
| 26 | 33 | 35 | 35 | 36 | 36 | 36 |
| 27 | 34 | 36 | 36 | 37 | 37 | 37 |
| 28 | 35 | 37 | 37 | 38 | 38 | 38 |
| 29 | 36 | 38 | 38 | 39 | 39 | 39 |
| 30 | 38 | 40 | 40 | 41 | 41 | 41 |
| 31 | 39 | 41 | 41 | 42 | 42 | 42 |
| 32 | 40 | 42 | 42 | 43 | 43 | 43 |

## Metadata Accounting

- initial literal overhead charged: `10` bits per raw block in pass 1
- refresh metadata charged: `0` bits per pass
- accumulated profile/rechunk sidecar bits: `0` in this fixed-profile model
- no per-file sidecar, table, manifest, seed map, selector map, or model is assumed
- retained variants are encoder working state only and are not serialized unless selected
- final size is counted after collapsing to the selected path
- compact sweep summary and experiment registry: `model_analysis/proof_kernel/sweep_summary.json`

## Pass Ledger

| pass | depth bits | literal overhead | bits before | bits after | current delta % | raw delta % | accepted windows | avg variants | equal | bloat retained | bundled | conservative multiplier | optimistic multiplier | discount | rechunk | residual bits |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 1 | 16 | 10 | 8000000.00 | 17827820.16 | -122.847752 | -122.847752 | 9341.0117 | 2.9589 | 0.0000 | 1.9589 | 0.5902 | 1.1500 | 1.1593 | 1.0081 | 4 | 0.1618 |
| 2 | 16 | 0 | 17827820.16 | 17740514.23 | 0.489717 | 1.091324 | 52995.9159 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 2.2305 |
| 3 | 16 | 0 | 17740514.23 | 17653635.85 | 0.489717 | 1.085980 | 52736.3856 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 3.8518 |
| 4 | 16 | 0 | 17653635.85 | 17567182.93 | 0.489717 | 1.080661 | 52478.1262 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 2.9319 |
| 5 | 16 | 0 | 17567182.93 | 17481153.39 | 0.489717 | 1.075369 | 52221.1316 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 1.3871 |
| 6 | 16 | 0 | 17481153.39 | 17395545.14 | 0.489717 | 1.070103 | 51965.3955 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 1.1442 |
| 7 | 16 | 0 | 17395545.14 | 17310356.14 | 0.489717 | 1.064863 | 51710.9118 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 0.1400 |
| 8 | 16 | 0 | 17310356.14 | 17225584.32 | 0.489717 | 1.059648 | 51457.6744 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 0.3213 |
| 9 | 16 | 0 | 17225584.32 | 17141227.65 | 0.489717 | 1.054458 | 51205.6771 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 3.6452 |
| 10 | 16 | 0 | 17141227.65 | 17057284.08 | 0.489717 | 1.049295 | 50954.9139 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 0.0785 |
| 11 | 16 | 0 | 17057284.08 | 16973751.60 | 0.489717 | 1.044156 | 50705.3787 | 4.0000 | 0.0000 | 3.0000 | 1.3007 | 1.1293 | 1.1357 | 1.0057 | 4 | 3.5984 |

## Large-File Concentration

The concentration bound uses the proof-kernel bounded-differences radius over
the effective current-entry count. At the configured `1,000,000` raw input
blocks this radius is a loose finite-size bound, not a claim that every
file of that size clears the target with alpha `1e-9`. Because the radius
scales as `1/sqrt(N)`, the entries below give the large-file scale where
the radius falls below each target margin.

- evaluated entry count: `4264321`
- concentration entry bits: `4`
- radius at alpha `1e-9`: `±0.990406` percentage points
- entries for radius <= margin to `0.1%`: `27540847`
- entries for radius <= margin to `0.2%`: `49834231`

## Assumptions And Proof Boundary

- Uniform seed-prefix match law.
- Encoder-only variants are not serialized until selected.
- Refresh decode follows the named profile rule and charged metadata.
- Rechunk decode follows the fixed profile schedule and charged metadata.
- The model operates on current encoded entry bits after pass 1.
- Concentration uses the bounded-differences radius reported in `best_config.json`.
- High per-pass drift without raw crossover is labeled as a component, not as
  a viable net-compression path.
- A profile using `oracle_weighted_interval` is an upper bound until a
  deterministic selector with no side table matches it.
- Registry rows are compact machine-readable rows in `sweep_summary.json`;
  evaluated row count: `12`.

## Reproduction

```powershell
python model_analysis/proof_kernel/viability_search.py --write-artifacts
```
