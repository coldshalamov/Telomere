# H110 - Partial-Refresh Pareto Frontier

Date: 2026-06-18

## Question

Can the user's partial-refresh idea have a real sweet spot if we allow slightly
bloating records, choose the best non-overlapping intervals, and replace enough
atoms to keep future match opportunities fresh?

Runnable artifact:

```text
model_analysis/birth_channel_research/H110-partial_refresh_pareto.py
```

## Model

For each sampled layer and slack limit `s`, H110 computes the Pareto frontier:

```text
for each rewritten atom count r:
  cheapest interval cover delta among records with cost <= raw_span + s
```

Then it applies two lower-bound stateless prices:

```text
H2 ready/carry lower bound = N * H2(r/N)
literal fallback lower bound = 3 bits for each unreplaced atom
```

Modes:

```text
j3d1_parseable:
  fixed arity code + J3D1 payload-width cost

local_width_oracle:
  fixed arity code + raw local payload bits
  underpriced because the decoder is not told where the payload ends

zero_arity_oracle:
  raw local payload bits only
  lower-bound microscope, not a parseable record language
```

## Result

The parseable and oracle rows split sharply.

Best parseable J3D1 rows:

```text
q >= 10%:
  B4_K128_D512, slack=8
  H2 delta = +0.524497 bits/input atom

q >= 50%:
  B4_K128_D512, slack=8
  H2 delta = +0.653950 bits/input atom
```

Best local-width oracle rows:

```text
q >= 10%:
  B4_K16_D64, slack=4
  H2 delta = -0.111979 bits/input atom

q >= 50%:
  B4_K16_D64, slack=4
  H2 delta = -0.111979 bits/input atom
```

Best zero-arity oracle row:

```text
q >= 50%:
  B8_K32_D256, slack=2
  H2 delta = -1.472656 bits/input atom
```

Representative table excerpt:

```text
config        mode                s   H2 q10   H2 q50
B4_K128_D512 j3d1_parseable      8   +0.5245  +0.6540
B4_K16_D64   local_width_oracle  4   -0.1120  -0.1120
B8_K32_D256  local_width_oracle  4   -0.0508  -0.0508
B8_K64_D512  local_width_oracle  8   -0.0469  -0.0469
B8_K32_D256  zero_arity_oracle   2   -1.4727  -1.4727
```

## Reading

This is not a solution, but it is a useful positive signal:

```text
the partial-refresh match lattice has enough option pressure
```

The failure is narrower:

```text
parseable payload-width / boundary syntax spends the option dividend
```

The local-width oracle is not honest because the decoder does not know where a
raw local seed payload ends. J3D1 makes the payload self-delimiting, but its
width overhead turns the same frontier positive by about `+0.52` to `+0.65`
bits/atom at the useful replacement fractions.

## Verdict

The other agent's claimed partial-refresh gain could have been seeing the
local-width-oracle effect. That effect is real enough to keep the lane alive as
a target, but not as a completed stateless codec.

The next concrete target is:

```text
derive payload width/boundary from a public invariant
or code the width stream collectively below the J3D1 bill
while preserving stateless parseability and paying ready/carry layout
```

Any proposed fix must pass the H106-H109 accounting gates. If the width class,
boundary, or selected interval set is content-selected and not decoder-derived,
the missing bits are just metadata under a different name.
