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
| markov1_penalty_0.05 | 24 | 5 | 69 | 1.000 | 0.0656 | 0.0219 | 0.6876 | 1.45 | 32.07 | 2.09 | 32.76 | 0.000 |
| markov1_penalty_0.05 | 24 | 8 | 68 | 1.000 | 0.0192 | 0.0064 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.22 | 0.000 |
| markov1_penalty_0.10 | 24 | 5 | 69 | 1.000 | 0.0313 | 0.0104 | 0.6876 | 1.45 | 32.07 | 2.09 | 32.81 | 0.000 |
| markov1_penalty_0.10 | 24 | 8 | 69 | 1.000 | 0.0489 | 0.0163 | 0.6894 | 1.45 | 31.96 | 3.00 | 31.77 | 0.000 |
| markov1_penalty_0.15 | 24 | 5 | 70 | 1.000 | 0.0384 | 0.0128 | 0.6797 | 1.47 | 32.43 | 2.10 | 33.19 | 0.000 |
| markov1_penalty_0.15 | 24 | 8 | 69 | 1.000 | 0.0144 | 0.0048 | 0.6894 | 1.45 | 31.96 | 3.00 | 31.82 | 0.000 |
| markov1_penalty_0.20 | 24 | 5 | 70 | 1.000 | 0.0044 | 0.0015 | 0.6797 | 1.47 | 32.43 | 2.10 | 33.24 | 0.000 |
| markov1_penalty_0.20 | 24 | 8 | 70 | 1.000 | 0.0254 | 0.0085 | 0.6815 | 1.47 | 32.32 | 3.00 | 32.21 | 0.000 |

## Nearest Miss / Best Rows

| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| markov1_penalty_0.10 | 24 | 8 | 70 | 1.000 | 0.0936 | 0.0312 | 0.6815 | 1.47 | 32.32 | 3.00 | 32.11 | 0.000 |
| markov1_penalty_0.05 | 24 | 5 | 69 | 1.000 | 0.0656 | 0.0219 | 0.6876 | 1.45 | 32.07 | 2.09 | 32.76 | 0.000 |
| markov1_penalty_0.15 | 24 | 8 | 70 | 1.000 | 0.0595 | 0.0198 | 0.6815 | 1.47 | 32.32 | 3.00 | 32.16 | 0.000 |
| markov1_penalty_0.15 | 24 | 5 | 71 | 1.000 | 0.0578 | 0.0193 | 0.6764 | 1.48 | 32.59 | 2.11 | 33.33 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 8 | 68 | 1.000 | 0.0542 | 0.0181 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.17 | 0.000 |
| markov1_penalty_0.10 | 24 | 5 | 69 | 1.000 | 0.0313 | 0.0104 | 0.6876 | 1.45 | 32.07 | 2.09 | 32.81 | 0.000 |
| markov1_penalty_0.20 | 24 | 8 | 70 | 1.000 | 0.0254 | 0.0085 | 0.6815 | 1.47 | 32.32 | 3.00 | 32.21 | 0.000 |
| markov1_penalty_0.20 | 24 | 5 | 71 | 1.000 | 0.0240 | 0.0080 | 0.6764 | 1.48 | 32.59 | 2.11 | 33.38 | 0.000 |
| markov1_arith_width_lotus_payload | 24 | 5 | 68 | 1.000 | 0.0196 | 0.0065 | 0.7025 | 1.42 | 31.41 | 2.07 | 32.11 | 0.000 |
| markov1_penalty_0.05 | 24 | 8 | 68 | 1.000 | 0.0192 | 0.0064 | 0.7013 | 1.43 | 31.43 | 3.00 | 31.22 | 0.000 |

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
