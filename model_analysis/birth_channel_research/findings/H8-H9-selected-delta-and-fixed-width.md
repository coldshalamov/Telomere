# Avenue H8/H9 — selected-delta residual and canonical fixed width

Author: Codex continuation with two read-only subagent checks. Date:
2026-06-17.
Status: current follow-up after H7's raw first-hit delta near miss.

## HYPOTHESIS

H7 found the closest paid Total-Cover witness mode so far:

```text
B=4,K=128,D=512
raw first-hit delta law + public suffix arity model
gain = -0.011929 bits/input atom
missing = 1.357 bits/selected record
```

Two possible ways to close the remaining gap:

1. selected-delta residual law: tune a public temperature or residual model
   for the selected cover, not the raw first-hit process;
2. canonical width: make payload width decoder-derived, eliminating the delta
   stream entirely.

## H8 MECHANISM

Runnable kernel:

- `../H8-total_cover_objective_beta.py`

H8 uses the normalized public law:

```text
P_beta(delta | L,D) ∝ P_raw(delta | L,D) * 2^(beta * delta)
L = arity * B
```

Unlike H7's likelihood-fit tilted mode, H8 chooses beta by Total-Cover train
gain on independent uniform-law samples, freezes it, then evaluates held-out.
This is honest only as a public profile parameter. A beta selected per file or
after seeing held-out data would be metadata.

## H8 RESULT

`refuted-as-one-parameter-crossover`

Coarse run:

```text
command: --train-trials 8 --eval-trials 4 --iterations 2
         --beta-start -0.3 --beta-stop 0.5 --beta-step 0.2

train-selected beta = 0.500
held-out gain       = -0.021201 bits/input atom
best held-out beta  = 0.100, -0.017357 bits/input atom
```

Narrower run:

```text
command: --train-trials 16 --eval-trials 8 --iterations 2
         --beta-start -0.1 --beta-stop 0.2 --beta-step 0.1

train-selected beta = 0.200
held-out gain       = -0.016322 bits/input atom
best held-out beta  = 0.000, -0.013714 bits/input atom
```

The train objective overfits. The held-out diagnostic prefers beta near zero,
which is the H7 raw law. A one-parameter public selected-delta temperature does
not close the `~1.36` bits/record gap.

## H9 MECHANISM

Runnable kernel:

- `../H9-total_cover_fixed_slack.py`

H9 tests a canonical fixed-width witness:

```text
width_bits = min(D, arity * B - slack)
```

The decoder derives `width_bits` from public constants and the decoded arity,
then reads exactly that many seed bits. This is a custom fixed-width witness
over the first `2^width_bits` seeds. It does **not** claim the larger Lotus
`payload_width <= W` seed set for only `W` bits.

## H9 RESULT

`refuted-as-crossover, close-miss`

Small smoke run:

```text
command: --train-trials 8 --eval-trials 4 --iterations 2 --slacks 0 1 2 3

best row: slack 0
gain = -0.007750 bits/input atom
```

Stronger bounded run:

```text
command: --train-trials 32 --eval-trials 16 --iterations 3 --slacks 0 1 2

slack 0: gain = -0.012314 bits/input atom, missing = 1.261 bits/record
slack 1: gain = -0.018427 bits/input atom
slack 2: gain = -0.018589 bits/input atom
```

Fixed slack removes the delta stream but gives the savings back through
fixed-width padding and reduced match supply. Slack `0` is competitive with H7
raw but not better in the stronger held-out run. More aggressive slack looks
positive on train and loses held-out.

## ACCOUNTING TRAPS CLOSED

- Beta/profile choice is free only if frozen by public spec/profile. Per-file
  choice is metadata.
- Held-out beta is diagnostic only. The valid H8 row is the train-selected beta.
- Fixed width is only free if the eligible seed set is exactly what the fixed
  bits can name. H9 charges `W` bits for `2^W` seeds; it does not take Lotus's
  `~2^(W+1)` cumulative seed set for free.
- Canonical width preserves stateless decode but can discard the order-statistic
  value of variable witness widths.

## CURRENT FRONTIER

H7 remains the best stable paid row in this branch:

```text
raw first-hit delta law:
  gain = -0.011929 bits/input atom
  missing = 1.357 bits/record

fixed slack 0:
  gain = -0.012314 bits/input atom
  missing = 1.261 bits/record
```

The two rows are close, but neither crosses. The remaining target is not a
simple one-parameter tilt or scalar fixed width. A future candidate must either:

1. exploit a real selected-cover residual invariant worth more than
   `~1.3 bits/record`, or
2. use a richer public canonical width schedule that saves delta bits without
   losing the same value in rank padding and match supply.

Under the uniform/content-blind requirement, any such schedule must be public
and held-out. Per-file schedule selection, adaptive tables, or checksum-pruned
width ambiguity would move the missing bits into a hidden channel.
