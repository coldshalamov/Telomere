# Telomere Viability Target

Under this model, the configuration below reaches the stated current-layer
net expected compression target for ten effective passes after charged metadata.

## Configuration

- block bits: `8`
- arity cap: `5`
- seed-depth bits: `32`
- depth schedule bits: `[32]`
- initial literal overhead bits: `10`
- rechunk bits: `4`
- selection policy: `oracle_weighted_interval`
- refresh rule: `superposition_derived_refresh`
- superposition: `{'prune_delta_bits': 16, 'max_variants_per_position': 16, 'equal_size_allowed': False, 'bloat_tolerant_retained': True}`
- refresh metadata bits per pass: `0`
- rechunk metadata bits per pass: `0` because the chunk size is fixed by
  this decoder profile; a multiplexed implementation must charge its profile ID.
- final charged/raw ratio after `11` modeled passes: `2.104283231`
- ten-effective-pass minimum: `0.508922%`
- ten-effective-pass average: `0.508922%`
- concentration radius at alpha `1e-9`: `±0.994405` percentage points

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

## Pass Ledger

| pass | depth bits | literal overhead | bits before | bits after | current delta % | raw delta % | accepted windows | avg variants | max multiplier |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 32 | 10 | 8000000.00 | 17715476.27 | -121.443453 | -121.443453 | 11841.2969 | 16.0000 | 1.2052 |
| 2 | 32 | 0 | 17715476.27 | 17625318.25 | 0.508922 | 1.126975 | 54607.7003 | 16.0000 | 1.1828 |
| 3 | 32 | 0 | 17625318.25 | 17535619.06 | 0.508922 | 1.121240 | 54329.7894 | 16.0000 | 1.1828 |
| 4 | 32 | 0 | 17535619.06 | 17446376.37 | 0.508922 | 1.115534 | 54053.2928 | 16.0000 | 1.1828 |
| 5 | 32 | 0 | 17446376.37 | 17357587.85 | 0.508922 | 1.109856 | 53778.2034 | 16.0000 | 1.1828 |
| 6 | 32 | 0 | 17357587.85 | 17269251.20 | 0.508922 | 1.104208 | 53504.5139 | 16.0000 | 1.1828 |
| 7 | 32 | 0 | 17269251.20 | 17181364.12 | 0.508922 | 1.098589 | 53232.2173 | 16.0000 | 1.1828 |
| 8 | 32 | 0 | 17181364.12 | 17093924.31 | 0.508922 | 1.092998 | 52961.3065 | 16.0000 | 1.1828 |
| 9 | 32 | 0 | 17093924.31 | 17006929.51 | 0.508922 | 1.087435 | 52691.7744 | 16.0000 | 1.1828 |
| 10 | 32 | 0 | 17006929.51 | 16920377.44 | 0.508922 | 1.081901 | 52423.6141 | 16.0000 | 1.1828 |
| 11 | 32 | 0 | 16920377.44 | 16834265.85 | 0.508922 | 1.076395 | 52156.8184 | 16.0000 | 1.1828 |

## Large-File Concentration

The concentration bound uses the proof-kernel bounded-differences radius over
the effective current-entry count. At the configured `1,000,000` raw input
blocks this radius is a loose finite-size bound, not a claim that every
file of that size clears the target with alpha `1e-9`. Because the radius
scales as `1/sqrt(N)`, the entries below give the large-file scale where
the radius falls below each target margin.

- evaluated entry count: `4230094`
- concentration entry bits: `4`
- radius at alpha `1e-9`: `±0.994405` percentage points
- entries for radius <= margin to `0.1%`: `25014685`
- entries for radius <= margin to `0.2%`: `43830664`

## Assumptions And Proof Boundary

- Uniform seed-prefix match law.
- Encoder-only variants are not serialized until selected.
- Refresh decode follows the named profile rule and charged metadata.
- Rechunk decode follows the fixed profile schedule and charged metadata.
- The model operates on current encoded entry bits after pass 1.
- Concentration uses the bounded-differences radius reported in `best_config.json`.

## Reproduction

```powershell
python model_analysis/proof_kernel/viability_search.py --write-artifacts
```
