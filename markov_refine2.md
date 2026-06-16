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
  "atoms": 256,
  "trials": 48,
  "coverage_threshold": 0.95,
  "seed": 20260615,
  "block_bits": [
    24
  ],
  "max_arity": [
    8
  ],
  "modes": [
    "arith_arity_width_lotus_payload",
    "markov1_arith_width_lotus_payload",
    "markov2_arith_width_lotus_payload"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 8 | 68 | 1.000 | 0.0542 | 0.0181 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.17 | 0.000 |
| markov2_arith_width_lotus_payload | 24 | 8 | 43 | 1.000 | 0.0479 | 0.0160 | 0.9461 | 1.06 | 23.72 | 3.00 | 22.32 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 8 | 68 | 1.000 | 0.0542 | 0.0181 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.17 | 0.000 |
| markov2_arith_width_lotus_payload | 24 | 8 | 43 | 1.000 | 0.0479 | 0.0160 | 0.9461 | 1.06 | 23.72 | 3.00 | 22.32 | 0.000 |
| arith_arity_width_lotus_payload | 24 | 8 | 168 | 1.000 | -0.4075 | -0.1358 | 0.6346 | 1.58 | 34.65 | 3.00 | 35.55 | 0.642 |

## Mode Notes

- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.
- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.
- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.
- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.
- `width_classes*` modes use a small public global width set plus a per-record class id.
- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.
- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.

## Next Target

No paid custom first-positive row crossed in this run. The nearest target is `arith_arity_width_lotus_payload` at `B=24, K=8, D=168`, gain `-0.4075` bits/input atom and missing `0.642` bits/record.
