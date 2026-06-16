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
  "atoms": 128,
  "trials": 24,
  "coverage_threshold": 0.95,
  "seed": 20260615,
  "block_bits": [
    8,
    12,
    24
  ],
  "max_arity": [
    5,
    8,
    16
  ],
  "modes": [
    "markov1_geometric_rank"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_geometric_rank | 24 | 5 | 67 | 1.000 | 0.4198 | 0.1399 | 0.7122 | 1.40 | 30.96 | 2.04 | 31.08 | 0.000 |
| markov1_geometric_rank | 24 | 8 | 67 | 1.000 | 0.3646 | 0.1215 | 0.7340 | 1.36 | 29.99 | 3.00 | 29.22 | 0.000 |
| markov1_geometric_rank | 24 | 16 | 67 | 1.000 | 0.3700 | 0.1233 | 0.7145 | 1.40 | 30.88 | 4.00 | 29.12 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_geometric_rank | 24 | 16 | 68 | 1.000 | 1.5465 | 0.5155 | 0.6973 | 1.43 | 31.62 | 4.00 | 28.23 | 0.000 |
| markov1_geometric_rank | 24 | 5 | 68 | 1.000 | 1.4105 | 0.4702 | 0.6982 | 1.43 | 31.56 | 2.06 | 30.31 | 0.000 |
| markov1_geometric_rank | 24 | 8 | 68 | 1.000 | 1.3581 | 0.4527 | 0.7197 | 1.39 | 30.57 | 3.00 | 28.49 | 0.000 |
| markov1_geometric_rank | 12 | 8 | 87 | 1.000 | -0.4168 | -0.2779 | 0.6227 | 1.61 | 16.05 | 3.00 | 16.97 | 0.669 |
| markov1_geometric_rank | 12 | 16 | 88 | 1.000 | -0.7220 | -0.4814 | 0.6257 | 1.60 | 15.99 | 4.00 | 16.39 | 1.154 |
| markov1_geometric_rank | 12 | 5 | 57 | 1.000 | -0.9260 | -0.6174 | 0.6471 | 1.55 | 15.40 | 2.12 | 17.89 | 1.431 |
| markov1_geometric_rank | 8 | 16 | 46 | 1.000 | -1.0798 | -1.0798 | 0.6276 | 1.59 | 9.53 | 4.00 | 10.51 | 1.720 |
| markov1_geometric_rank | 8 | 8 | 50 | 1.000 | -1.1014 | -1.1014 | 0.6305 | 1.59 | 9.54 | 3.00 | 11.46 | 1.747 |
| markov1_geometric_rank | 8 | 5 | 38 | 1.000 | -1.2141 | -1.2141 | 0.6400 | 1.56 | 9.44 | 2.14 | 12.30 | 1.897 |

## Mode Notes

- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.
- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.
- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.
- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.
- `width_classes*` modes use a small public global width set plus a per-record class id.
- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.
- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.

## Next Target

No evaluated row produced a cover.
