# H176 - Finite-State Mixed-Radix Width

## Conjecture

If witness width is a public decoder-derived function, a total-cover layer can
omit per-record Lotus width delimiters and pack seed ranks as a mixed-radix
stream:

```text
record_i = [arity_i][rank_i in public inventory R_i]
layer_payload_bits = ceil(sum_i log2 R_i)
```

This branch has no sparse open/carry, birth-pass, hit-map, final-position, or
PCTB ledger. The bill is only arity bits, rank bits, any public grammar selector,
and fallback if a full cover fails.

## Model

`H176-finite_state_mixed_radix_width.py` samples a random-oracle interval-cover
trellis.

The strict Lotus-bucket inventory is depth-clamped:

```text
C_D(w) = min(count_le(w), 2^D) - min(count_le(w-1), 2^D)
```

That correction matters at the search frontier. At width `D`, the reachable
bucket is not `2^D`; most of that formal bucket lies outside the searched seed
frontier.

The kernel tests:

- exact V1 arity code for `K<=5`;
- a paid custom fixed arity code for `K>5`, cost `ceil(log2 K)`;
- public schedules such as `arity_margin:s`, where
  `width = target_bits - arity_bits - s`;
- union schedules such as `union_arity_margin:-1,2`, charged by the rank over
  the union inventory.

## Results

Representative strict rows:

| row | support pass 1 | support pass P | inline gain/atom | packed gain/atom | reading |
| --- | ---: | ---: | ---: | ---: | --- |
| V1 `B4,K5,D24,N16,r4,arity_margin:0,P2` | 0.125 | 0.000 | 0.000000 | 0.000000 | flat is already too sparse |
| V1 `B4,K5,D24,N16,r4,arity_margin:1,P2` | 0.000 | 0.000 | 0.000000 | 0.000000 | strict saving loses support |
| V1 `B4,K5,D32,N32,r4,union:-2,2,P2` | 0.967 | 0.383 | -0.734644 | -0.521013 | bloat buys support but expands |
| V1 `B4,K5,D32,N32,r4,union:-2,2,P3` | 0.967 | 0.075 | -0.734644 | -0.521013 | support tail keeps thinning |
| fixed `B4,K8,D40,N32,r4,arity_margin:0,P2` | 0.058 | 0.000 | 0.031250 | 0.031250 | small pass-one win, no recursion |
| fixed `B4,K64,D260,N128,r4,union:-2,3,P2` | 0.975 | 0.000 | -0.083734 | -0.063902 | high arity lowers bloat/atom, still expands |
| fixed `B4,K128,D520,N128,r4,union:-1,2,P2` | 0.133 | 0.033 | -0.074219 | -0.050781 | nearest high-K miss in this sweep |

`K=64/128` confirms the user's high-arity intuition in one direction: the bloat
needed to keep support becomes small per input atom as average arity grows. It
does not flip negative in this public-width/rank language.

## Bill

For `arity_margin:s`, record cost is approximately:

```text
arity_bits + rank_bits = target_bits - s
```

The edge supply is:

```text
P(edge for arity a) ~= 2^-(arity_bits(a) + s)
```

Thus strict saving (`s>0`) reduces cover supply exactly where it creates paid
compression. Negative slack (`s<0`) makes the cover supercritical but expands.

## Mutation

H176 does not solve maintained recursion. It sharpens the next target:

1. use H177's Kraft bound as the no-go for public per-record savings;
2. test only mechanisms that add a real supply boost after paying for it:
   equal-cost witness lookahead, generated/reachable closed regimes, or a
   canonical placement/cocycle scheme whose extra routes are genuinely public;
3. treat any positive packed-only row as a target until a parser-equivalent
   recursive surface exists.
