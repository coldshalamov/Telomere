# Telomere Viability Target

**Audited configuration meeting the 0.1% ten-effective-pass target under
the corrected proof kernel** (computed freshness, charged discrimination
channels, all metadata charged). It requires one v-next format primitive,
stated explicitly below and proven decodable at toy scale.

Class: `viability_practical_candidate`.

## Required format primitive: BIT_LITERAL

Canonical v1 literals pad to the next byte after the 3-bit marker (a
memcpy convenience). This profile replaces them with **bit-aligned
literals**: `[111][block_bits raw bits]`, zero pad. Records remain
prefix-free and self-delimiting; termination stays out-of-band
(`original_len` / `payload_bit_len`); the tail block uses
`last_block_size` as before. Decode proof at toy scale (mixed seed +
literal stream, wire bits == charged bits, exact round-trip):
`model_analysis/proof_kernel/bit_literal_decode_proof.py`.

The model identified this primitive, not benchmarking: the pass-1
literal tax dominates the raw-crossover curve, and the pad is 70% of it.

## Configuration

- block bits: `8`
- arity cap: `5`
- depth schedule bits: `[96]` (profile constant)
- literal overhead bits: `3` (BIT_LITERAL marker, zero pad)
- rechunk: `none` — record-aligned recursion, no discrimination channel needed
- selection policy: `greedy_largest_gain` (deterministic, no side table)
- refresh operator: `permutation_plus_neutral_swaps` (story `B_in_layer`,
  `3` charged bits/pass; computed late
  refresh coefficient `0.8006`)
- superposition: `{'prune_delta_bits': 16, 'max_variants_per_position': 4, 'equal_size_allowed': True, 'bloat_tolerant_retained': True}` (encoder-only, earned, collapsed before output)

## Results

- ten-effective-pass minimum: `0.132828%` (target `0.1%`)
- ten-effective-pass average: `0.162257%` (stretch `0.2%`)
- pass-1 charged ratio: `1.362347` (literal initialization)
- raw payback effective pass: `125` (gate `<= 200`)

## Raw-Crossover Curve

| modeled passes | final/raw |
| ---: | ---: |
| 11 | 1.340402302 |
| 50 | 1.226668681 |
| 100 | 1.071908476 |
| 200 | 0.832233401 |
| 500 | 0.485771323 |

## Audit Verdict

- uncharged-passthrough gate ok: `True`
- earned variants, not cap assumed: `True`
- selector viable without side table: `True`
- oracle upper bound: `False`
- raw crossover within 200 effective passes: `True`
- refresh decodable: `True` (story `B_in_layer`, file-specific: `False`)
- metadata sidecar ok: `True`
- encoder-only state serialized: `False`
- freshness modeled (not assumed): `True`

## Ablation Table (ten-effective-pass minimum)

| change | min % | delta vs target | pass-1 ratio |
| --- | ---: | ---: | ---: |
| (target config) | 0.132828 | 0.000000 | 1.3623 |
| `byte_aligned_literal_instead (8 bits)` | 0.048433 | -0.084396 | 1.9706 |
| `worst_case_pad_literal_instead (10 bits)` | 0.042277 | -0.090551 | 2.2139 |
| `no_permutation_refresh` | 0.000000 | -0.132828 | 1.3623 |
| `no_neutral_swaps` | 0.131864 | -0.000964 | 1.3623 |
| `no_superposition` | 0.116844 | -0.015984 | 1.3640 |
| `variants_16_instead_of_4` | 0.135988 | +0.003160 | 1.3620 |

## Metadata Accounting

- pass-1 literal wrap: 3 bits per raw block, charged in pass 1
- refresh: 3 bits per pass (pass-indexed permutation selector), charged
- rechunk metadata: none (no rechunk)
- no per-file sidecar, table, manifest, seed map, selector map, or model
- retained variants are encoder working state, never serialized unless selected

## Equations

```text
M(a,r,D) = count(seed records with canonical J3D1 cost <= r and seed index < 2^D)
p(min_record <= r | S,a,D,m) = 1 - exp(-M(a,r,D) * m / 2^S)   [fresh windows]
p_stale uses M(a,r,D_t) - M(a,r,D_prev)                        [stale windows]
E[gain per window] = sum_{g>=1} p(min_record <= S-g)
net_delta_pct_current = 100*(bits_before - bits_after - charged_metadata_bits)/bits_before
```

Freshness per pass: arity-1 windows re-roll only when their entry content
changed (replacement cascade + equal-size swaps); arity>=2 windows are
fully refreshed by the charged pass-indexed permutation. The retained-
variant multiplier applies to fresh windows only.

## Compute Estimate (separate from compressed size)

- candidate windows per pass: ~`5,000,000` (arity 1..5 sliding)
- worst-case full-depth search: `2^96` expansions per window —
  datacenter/ASIC-scale framing; the depth schedule is the compute knob and
  the gap is search-depth-invariant past the record-budget ceiling
- raw payback needs `~125` passes; per-pass
  expected accepted windows and gain are in the pass ledger below

## Pass Ledger (first 11 modeled passes)

| pass | depth bits | literal overhead | bits before | bits after | current delta % | raw delta % | accepted windows | fresh a1 | fresh multi | refresh coeff | swap mass | stale gain | discrim bits | avg variants | conservative multiplier | rechunk | channel |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 96 | 3 | 8000000.00 | 10898778.50 | -36.234731 | -36.234731 | 12006.7085 | 1.0000 | 1.0000 | 1.0000 | 0.00 | 0.00 | 0.00 | 4.0000 | 1.2300 | none | `records_only` |
| 2 | 96 | 0 | 10898778.50 | 10871710.51 | 0.248358 | 0.338350 | 13076.1158 | 1.0000 | 1.0000 | 1.0000 | 7632.37 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 3 | 96 | 0 | 10871710.51 | 10857269.81 | 0.132828 | 0.180509 | 6418.9430 | 0.0211 | 1.0000 | 0.8042 | 158.39 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 4 | 96 | 0 | 10857269.81 | 10842400.20 | 0.136955 | 0.185870 | 6212.9480 | 0.0068 | 1.0000 | 0.8014 | 50.53 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 5 | 96 | 0 | 10842400.20 | 10826940.25 | 0.142588 | 0.193249 | 6101.5839 | 0.0066 | 1.0000 | 0.8013 | 47.94 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 6 | 96 | 0 | 10826940.25 | 10810915.59 | 0.148007 | 0.200308 | 5994.3366 | 0.0065 | 1.0000 | 0.8013 | 46.89 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 7 | 96 | 0 | 10810915.59 | 10794353.17 | 0.153201 | 0.207030 | 5889.8206 | 0.0065 | 1.0000 | 0.8013 | 45.88 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 8 | 96 | 0 | 10794353.17 | 10777278.64 | 0.158180 | 0.213432 | 5787.9253 | 0.0064 | 1.0000 | 0.8013 | 44.91 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 9 | 96 | 0 | 10777278.64 | 10759716.11 | 0.162959 | 0.219532 | 5688.5457 | 0.0064 | 1.0000 | 0.8013 | 43.96 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 10 | 96 | 0 | 10759716.11 | 10741688.72 | 0.167545 | 0.225342 | 5591.6113 | 0.0063 | 1.0000 | 0.8013 | 43.04 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |
| 11 | 96 | 0 | 10741688.72 | 10723218.42 | 0.171950 | 0.230879 | 5497.0322 | 0.0063 | 1.0000 | 0.8013 | 42.15 | 0.00 | 0.00 | 4.0000 | 1.2520 | none | `records_only` |

## Cost Table

Exact canonical v1 record costs (validated against
`src/bin/v1_cost_table.rs`; re-pin locally with cargo after any format change).

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

## v1 frontier without the primitive

Under canonical v1 literals (8-10 bit overhead) the best audited
deterministic config is the same lane at `0.042950%` min — below target,
no crossover within 500 passes. See `TELOMERE_FRONTIER_REPORT.md`.
The previous headline (uncharged 4-bit rechunk, `0.5325%`) is re-classed
`failed_audit_uncharged_passthrough`: chunk/record discrimination was
never charged, and charging it flips the lane negative (explicit flag
`-24.7%/pass`; implicit decode-by-replay `-1.67%/pass`, provably
Kraft-dominated at every swept point).

## Reproduction

```powershell
python model_analysis/proof_kernel/viability_search.py --write-artifacts
python model_analysis/proof_kernel/bit_literal_decode_proof.py
```
