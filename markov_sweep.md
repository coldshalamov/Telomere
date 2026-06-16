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
    "markov1_arith_width_lotus_payload",
    "arith_arity_width_lotus_payload"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 8 | 5 | 15 | 1.000 | 0.0133 | 0.0133 | 0.7633 | 1.31 | 8.10 | 2.01 | 8.47 | 0.000 |
| markov1_arith_width_lotus_payload | 8 | 8 | 16 | 1.000 | 0.1222 | 0.1222 | 0.7432 | 1.35 | 8.27 | 3.00 | 7.61 | 0.000 |
| markov1_arith_width_lotus_payload | 8 | 16 | 15 | 1.000 | 0.1085 | 0.1085 | 0.7549 | 1.32 | 8.13 | 4.00 | 6.47 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 5 | 23 | 1.000 | 0.0764 | 0.0509 | 0.7627 | 1.31 | 13.25 | 2.00 | 13.65 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 8 | 23 | 1.000 | 0.0548 | 0.0366 | 0.7640 | 1.31 | 13.28 | 3.00 | 12.65 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 16 | 23 | 1.000 | 0.0414 | 0.0276 | 0.7598 | 1.32 | 13.37 | 4.00 | 11.76 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 5 | 47 | 1.000 | 0.0871 | 0.0290 | 0.7627 | 1.31 | 29.01 | 2.00 | 29.38 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 8 | 47 | 1.000 | 0.0269 | 0.0090 | 0.7861 | 1.27 | 28.12 | 3.00 | 27.52 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 16 | 47 | 1.000 | 0.0550 | 0.0183 | 0.7630 | 1.31 | 29.03 | 4.00 | 27.44 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 5 | 48 | 1.000 | 0.1553 | 0.0518 | 0.7487 | 1.34 | 29.54 | 2.00 | 29.88 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 16 | 49 | 1.000 | 0.1437 | 0.0479 | 0.7467 | 1.34 | 29.64 | 4.00 | 28.00 | 0.000 |
| markov1_arith_width_lotus_payload | 8 | 8 | 16 | 1.000 | 0.1222 | 0.1222 | 0.7432 | 1.35 | 8.27 | 3.00 | 7.61 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 8 | 49 | 1.000 | 0.1208 | 0.0403 | 0.7679 | 1.30 | 28.77 | 3.00 | 28.14 | 0.000 |
| markov1_arith_width_lotus_payload | 8 | 16 | 15 | 1.000 | 0.1085 | 0.1085 | 0.7549 | 1.32 | 8.13 | 4.00 | 6.47 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 5 | 23 | 1.000 | 0.0764 | 0.0509 | 0.7627 | 1.31 | 13.25 | 2.00 | 13.65 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 8 | 23 | 1.000 | 0.0548 | 0.0366 | 0.7640 | 1.31 | 13.28 | 3.00 | 12.65 | 0.000 |
| markov1_arith_width_lotus_payload | 12 | 16 | 23 | 1.000 | 0.0414 | 0.0276 | 0.7598 | 1.32 | 13.37 | 4.00 | 11.76 | 0.000 |
| markov1_arith_width_lotus_payload | 8 | 5 | 15 | 1.000 | 0.0133 | 0.0133 | 0.7633 | 1.31 | 8.10 | 2.01 | 8.47 | 0.000 |
| arith_arity_width_lotus_payload | 12 | 8 | 87 | 1.000 | -0.1913 | -0.1276 | 0.6227 | 1.61 | 16.05 | 3.00 | 16.62 | 0.307 |
| arith_arity_width_lotus_payload | 8 | 16 | 46 | 1.000 | -0.1922 | -0.1922 | 0.6276 | 1.59 | 9.53 | 4.00 | 9.10 | 0.306 |
| arith_arity_width_lotus_payload | 24 | 8 | 192 | 1.000 | -0.1961 | -0.0654 | 0.6475 | 1.54 | 33.90 | 3.00 | 34.55 | 0.303 |
| arith_arity_width_lotus_payload | 24 | 5 | 120 | 1.000 | -0.2005 | -0.0668 | 0.6318 | 1.58 | 34.78 | 2.14 | 36.27 | 0.317 |
| arith_arity_width_lotus_payload | 24 | 16 | 232 | 1.000 | -0.2017 | -0.0672 | 0.6273 | 1.59 | 35.06 | 4.00 | 34.76 | 0.321 |
| arith_arity_width_lotus_payload | 12 | 5 | 57 | 1.000 | -0.2028 | -0.1352 | 0.6471 | 1.55 | 15.40 | 2.12 | 16.79 | 0.313 |
| arith_arity_width_lotus_payload | 12 | 16 | 88 | 1.000 | -0.2052 | -0.1368 | 0.6257 | 1.60 | 15.99 | 4.00 | 15.60 | 0.328 |
| arith_arity_width_lotus_payload | 8 | 8 | 50 | 1.000 | -0.2242 | -0.2242 | 0.6305 | 1.59 | 9.54 | 3.00 | 10.07 | 0.356 |
| arith_arity_width_lotus_payload | 8 | 5 | 38 | 1.000 | -0.2813 | -0.2813 | 0.6400 | 1.56 | 9.44 | 2.14 | 10.84 | 0.440 |

## Mode Notes

- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.
- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.
- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.
- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.
- `width_classes*` modes use a small public global width set plus a per-record class id.
- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.
- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.

## Next Target

No paid custom first-positive row crossed in this run. The nearest target is `arith_arity_width_lotus_payload` at `B=12, K=8, D=87`, gain `-0.1913` bits/input atom and missing `0.307` bits/record.
