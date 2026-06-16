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
    24
  ],
  "max_arity": [
    8
  ],
  "modes": [
    "arith_arity_width_lotus_payload",
    "markov1_arith_width_lotus_payload",
    "markov1_joint_dp"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 8 | 47 | 1.000 | 0.0269 | 0.0090 | 0.7861 | 1.27 | 28.12 | 3.00 | 27.52 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 8 | 49 | 1.000 | 0.1208 | 0.0403 | 0.7679 | 1.30 | 28.77 | 3.00 | 28.14 | 0.000 |
| arith_arity_width_lotus_payload | 24 | 8 | 192 | 1.000 | -0.1961 | -0.0654 | 0.6475 | 1.54 | 33.90 | 3.00 | 34.55 | 0.303 |
| markov1_joint_dp | 24 | 8 | 192 | 1.000 | -1.7746 | -0.5915 | 0.6445 | 1.55 | 34.06 | 3.00 | 37.16 | 2.753 |

## Mode Notes

- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.
- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.
- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.
- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.
- `width_classes*` modes use a small public global width set plus a per-record class id.
- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.
- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.

## Next Target

No paid custom first-positive row crossed in this run. The nearest target is `arith_arity_width_lotus_payload` at `B=24, K=8, D=192`, gain `-0.1961` bits/input atom and missing `0.303` bits/record.
