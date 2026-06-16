# Total-Cover Lotus Crossover Results

This branch fully rewrites every layer. There are no carried records,
open/carry maps, birth-pass tags, sparse hit bitmaps, final-position
notes, or PCTB ledgers in these numbers. A record is only
`[arity][seed witness]`.

The model samples uniform-hash first-hit seed ranks for every interval
and runs an optimal non-overlapping full-cover DP. A row is counted as
first-positive only if full-cover rate is at least `0.95`
and charged gain is positive.

## Run Config

```json
{
  "atoms": 64,
  "trials": 8,
  "coverage_threshold": 0.95,
  "seed": 20260615,
  "block_bits": [
    12,
    24
  ],
  "max_arity": [
    2,
    8
  ],
  "modes": [
    "arith_arity_width_lotus_payload",
    "arity2_exact_j3d1",
    "arity2_arith_width_lotus_payload"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arith_arity_width_lotus_payload | 24 | 8 | 92 | 1.000 | 0.0039 | 0.0013 | 0.6387 | 1.57 | 34.50 | 3.00 | 34.88 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arith_arity_width_lotus_payload | 24 | 8 | 92 | 1.000 | 0.0039 | 0.0013 | 0.6387 | 1.57 | 34.50 | 3.00 | 34.88 | 0.000 |
| arith_arity_width_lotus_payload | 12 | 8 | 80 | 1.000 | -0.0223 | -0.0149 | 0.6543 | 1.53 | 15.35 | 3.00 | 15.47 | 0.034 |
| arith_arity_width_lotus_payload | 12 | 2 | 24 | 1.000 | -0.3355 | -0.2237 | 0.7383 | 1.35 | 13.69 | 1.00 | 15.74 | 0.454 |
| arith_arity_width_lotus_payload | 24 | 2 | 48 | 1.000 | -0.3487 | -0.1162 | 0.7656 | 1.31 | 28.85 | 1.00 | 30.86 | 0.455 |
| arity2_arith_width_lotus_payload | 12 | 2 | 24 | 1.000 | -0.3511 | -0.2341 | 0.7383 | 1.35 | 13.69 | 1.00 | 15.76 | 0.476 |
| arity2_arith_width_lotus_payload | 24 | 2 | 48 | 1.000 | -0.3643 | -0.1214 | 0.7656 | 1.31 | 28.85 | 1.00 | 30.88 | 0.476 |
| arity2_arith_width_lotus_payload | 24 | 8 | 49 | 1.000 | -0.4134 | -0.1378 | 0.7559 | 1.32 | 29.33 | 3.00 | 29.36 | 0.547 |
| arity2_arith_width_lotus_payload | 12 | 8 | 25 | 1.000 | -0.4428 | -0.2952 | 0.7637 | 1.31 | 13.32 | 3.00 | 13.34 | 0.580 |
| arity2_exact_j3d1 | 12 | 2 | 24 | 1.000 | -2.9727 | -1.9818 | 0.5781 | 1.73 | 18.19 | 1.00 | 24.96 | 5.142 |
| arity2_exact_j3d1 | 12 | 8 | 25 | 1.000 | -3.0273 | -2.0182 | 0.5488 | 1.82 | 19.59 | 3.00 | 24.42 | 5.516 |
| arity2_exact_j3d1 | 24 | 8 | 49 | 1.000 | -3.6113 | -1.2038 | 0.5469 | 1.83 | 41.67 | 3.00 | 47.58 | 6.604 |
| arity2_exact_j3d1 | 24 | 2 | 48 | 1.000 | -3.6270 | -1.2090 | 0.5664 | 1.77 | 40.01 | 1.00 | 47.86 | 6.403 |

## Mode Notes

- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.
- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.
- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.
- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.
- `width_classes*` modes use a small public global width set plus a per-record class id.
- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.
- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.

## Next Target

The best paid custom first-positive row is `arith_arity_width_lotus_payload` at `B=24, K=8, D=92`, with gain `0.0039` bits/input atom.
