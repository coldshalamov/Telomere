# H143 - Near-Total Public-Board Bound

Date: 2026-06-18

## Question

Can a public board or egg-carton layout avoid the partial-refresh bitmap by
making almost every public slot open, with only rare exceptions?

Runnable artifact:

```text
model_analysis/birth_channel_research/H143-near_total_public_board_bound.py
```

## Model

H143 is deliberately generous. For each input atom it allows the encoder to use
the cheapest successful interval among every public candidate interval that
contains that atom. It charges:

```text
expected cheapest-success record delta
+ H2(eps)
+ eps * log2(P-1)
+ optional exception fallback bits
```

It does not charge cover conflicts or winner selection, so a miss here is a
strong miss for any real public board under the same witness law.

## Results

Compressive or near-flat slack does not get near the H128 opening target:

```text
B4,K32,slack=2:
  q = 0.342931792
  eps = 0.657068208
  expected record delta = +0.029757626 bits/atom

H124 lane apparent, P=4096:
  required q = 0.998998607
  best q for slack<=2 = 0.342931792
  opening gap = 0.656066815
```

Large slack can make opening near-total, but it is a bloat regime:

```text
B4,K128,slack=8:
  q = 1.000000000
  expected record delta = +0.032630301 bits/atom
  total delta at P=4096,F=0 = +0.032630302

B4,K512,slack=8:
  q = 0.998289571
  expected record delta = +0.058738833 bits/atom
  total delta at P=4096,F=0 = +0.097450168
```

Best optimistic rows are still positive:

```text
P=2, best total delta = +0.005282481 bits/atom
P=64, best total delta among near-total rows = +0.032630302 bits/atom
P=4096, best near-total row = +0.032630302 bits/atom
```

## Reading

Public near-total geometry is still a useful decode idea: it can remove the
birth/open bitmap if the board is almost all open. But under exact J3D1, the
conditions split:

```text
cheap/compressive records -> too sparse
near-total records        -> bloating
```

## Verdict

No current public-board route crosses under content-blind uniform accounting.
The branch needs a separate witness/fertility mechanism that makes the success
set both near-total and net-negative.
