# H140 - Slack-Refresh Supply Bound

Date: 2026-06-18

## Question

The partial-refresh idea says:

```text
allow +1/+2 bit matches,
search all bundle placements containing each block,
replace enough blocks to keep future targets fresh,
choose the smallest/non-overlapping matches afterward.
```

Is the resulting option pressure real, and does it survive parseable witness
accounting?

Runnable artifact:

```text
model_analysis/birth_channel_research/H140-slack_refresh_supply_bound.py
```

## Model

For a central atom, H140 computes:

```text
lambda = sum over arities k of k * Pr(interval of arity k has a slack-legal seed)
q      = 1 - exp(-lambda)
```

The factor `k` is the number of placements of a length-`k` interval that contain
the central atom, so this explicitly counts the bundle-placement multiplier.
The search frontier is fixed to `D = K * B`.

Two ledgers are compared:

```text
local_width_oracle:
  arity bits + raw local payload bits
  underpriced because the decoder does not know the payload boundary

j3d1_parseable:
  arity bits + exact J3D1 payload-width syntax
  parseable under the current proof-kernel cost law
```

For partial refresh, any content-selected ready/carry set still owes at least
`H2(q)` bits per input atom unless the layout is public or decoder-derived.

## Results

The optimistic oracle shows the user's option-pressure argument is real:

```text
local_width_oracle, B=4,K=5,slack=0:
  q = 0.894601

local_width_oracle, B=4,K=5,slack=2:
  q = 0.999877
```

Exact J3D1 sharply reduces the same supply:

```text
j3d1_parseable, B=4,K=32,slack=0:
  lambda = 0.106613
  q = 0.101126
  H2(q)/q = 4.672923 bits per rewritten atom

j3d1_parseable, B=4,K=32,slack=2:
  lambda = 0.419967
  q = 0.342932
  H2(q)/q = 2.704901 bits per rewritten atom

j3d1_parseable, B=4,K=32,slack=4:
  lambda = 1.612839
  q = 0.800679
  H2(q)/q = 0.899946 bits per rewritten atom

j3d1_parseable, B=8,K=32,slack=2:
  q = 0.184346
  H2(q)/q = 3.740208 bits per rewritten atom
```

First `K` where option supply reaches the target with `D=K*B`:

```text
j3d1 B=4 slack=2: q>=0.10 at K=5, but q>=0.50 not reached by K=4096
j3d1 B=4 slack=4: q>=0.50 at K=5, but q>=0.90 not reached by K=4096
j3d1 B=8 slack=2: q>=0.10 at K=5, but q>=0.50 not reached by K=4096
```

## Reading

The quadratic placement multiplier is not a mirage. It can absolutely make the
unpaid local-width lattice look compressive and fresh.

The current paid blocker is narrower: the decoder must know payload width and
record boundaries. Exact J3D1 spends enough of the option dividend that +1/+2
slack usually leaves a medium replacement fraction with a large `H2(q)` bill.

This matches H110: local-width oracle rows cross, but parseable J3D1 rows miss.

## Verdict

The partial-refresh sweet spot remains a live target generator, not a solved
codec. A successful version must preserve the local-width-oracle supply while
making payload boundaries and the selected ready/carry layout public,
decoder-derived, or collectively coded below the J3D1 plus `H2(q)` bill.
