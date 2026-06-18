# H112 - Frozen Public Width/Delta Law

Date: 2026-06-18

## Question

H111 showed a split: a counts-free collective delta stream crossed, but paying
the per-file delta counts did not. Can a public frozen law replace that hidden
per-file histogram?

Runnable artifact:

```text
model_analysis/birth_channel_research/H112-frozen_width_delta_law.py
```

## Model

The stream shape is parseable:

```text
arity stream -> public target bits
delta stream under frozen P(delta | context)
payload bits
```

The public model is trained on independent uniform-law covers and then frozen
before held-out evaluation. Rows still include the optimistic H2 ready/carry
lower bound and do not charge full cover-shape placement.

## Result

Default diagnostic, targeting the strongest H111 counts-free crossing:

```text
B4_K16_D64, slack=4, qmin=0.10

ctx                   train      held-out
global                +0.2697    +0.2531 bits/atom
arity_bucket          +0.2583    +0.2907 bits/atom
target_arity_bucket   +0.2734    +0.3163 bits/atom
```

Baselines from the same row:

```text
local oracle:  -0.157812 bits/atom
fixed delta:   +0.417187 bits/atom
J3D1:          +0.532663 bits/atom
```

## Verdict

The frozen public law does not replace the hidden per-file histogram in the
ordinary H2-charged partial-refresh branch. The local option pressure is real,
but this public model still leaves about `0.25` bits/atom of bloat on held-out
uniform covers.

This result motivated H113/H114: move readiness out of the H2 map with a paid
two-epoch seed-class channel, then retry the frozen delta law.
