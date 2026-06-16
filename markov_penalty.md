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
    5,
    8
  ],
  "modes": [
    "markov1_arith_width_lotus_payload",
    "markov1_penalty_0.05",
    "markov1_penalty_0.10",
    "markov1_penalty_0.15",
    "markov1_penalty_0.20"
  ]
}
```

## First Positive Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 5 | 68 | 1.000 | 0.0196 | 0.0065 | 0.7025 | 1.42 | 31.41 | 2.07 | 32.11 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 8 | 68 | 1.000 | 0.0542 | 0.0181 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.17 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_arith_width_lotus_payload | 24 | 8 | 68 | 1.000 | 0.0542 | 0.0181 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.17 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 5 | 68 | 1.000 | 0.0196 | 0.0065 | 0.7025 | 1.42 | 31.41 | 2.07 | 32.11 | 0.000 |
| markov1_penalty_0.05 | 24 | 8 | 168 | 1.000 | -2.2601 | -0.7534 | 0.6346 | 1.58 | 34.65 | 3.00 | 38.47 | 3.561 |
| markov1_penalty_0.10 | 24 | 8 | 168 | 1.000 | -2.2918 | -0.7639 | 0.6346 | 1.58 | 34.65 | 3.00 | 38.52 | 3.611 |
| markov1_penalty_0.05 | 24 | 5 | 120 | 1.000 | -2.3116 | -0.7705 | 0.6368 | 1.57 | 34.56 | 2.14 | 39.25 | 3.630 |
| markov1_penalty_0.15 | 24 | 8 | 168 | 1.000 | -2.3235 | -0.7745 | 0.6346 | 1.58 | 34.65 | 3.00 | 38.57 | 3.661 |
| markov1_penalty_0.10 | 24 | 5 | 120 | 1.000 | -2.3435 | -0.7812 | 0.6368 | 1.57 | 34.56 | 2.14 | 39.30 | 3.680 |
| markov1_penalty_0.20 | 24 | 8 | 168 | 1.000 | -2.3553 | -0.7851 | 0.6346 | 1.58 | 34.65 | 3.00 | 38.62 | 3.711 |
| markov1_penalty_0.15 | 24 | 5 | 120 | 1.000 | -2.3753 | -0.7918 | 0.6368 | 1.57 | 34.56 | 2.14 | 39.35 | 3.730 |
| markov1_penalty_0.20 | 24 | 5 | 120 | 1.000 | -2.4071 | -0.8024 | 0.6368 | 1.57 | 34.56 | 2.14 | 39.40 | 3.780 |

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
