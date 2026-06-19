# H175 - State-Carrying Transducer DP

Date: 2026-06-18

## Question

Build the first proof-kernel for the state-carrying hash transducer:

```text
G(q_i, a_i, s_i) = (x_i, q_{i+1})
```

The decoder starts from public `q0=0`, reads records in order, regenerates the
target span, observes digest tail bits as `q_{i+1}`, and continues. The file
still stores only:

```text
[arity][seed witness]
```

No salt field is stored. The accounting rule is:

```text
observing q_{i+1} is free
conditioning q_{i+1} to a requested value costs supply
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py
```

## Kernel

For each reachable trellis state `(position, q)`, H175 samples exact matching
witness counts from the J3D1 payload-width buckets and uses an optimal
full-cover DP over the sampled edge set.

Policies:

```text
shortest   keep one shortest witness only
equal      keep all witnesses with the shortest record cost
slack:N    keep all witnesses within N bits of the shortest record cost
```

The state tail does not change the data-prefix match probability. The optional
`--condition-tail-bits` flag is the control: it asks for specific tail bits and
therefore reduces hit probability by the corresponding factor.

## Exact V1/J3D1 Smoke Rows

Command:

```text
python model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py --items 8 --trials 50 --block-bits 8 --max-arity 5 --depth 24 --state-bits 0 --state-bits 8 --policy shortest --policy equal --policy slack:2 --policy slack:4
```

Rows were uncapped: `pruned=0`, `trunc=0`.

```text
B K D  r policy    support  edgeHit  choice/h  outBits  gain/atom  states
8 5 24 0 shortest  1.0000   0.6213   1.0000     86.06    -2.7575       1
8 5 24 0 equal     1.0000   0.6307   1.0000     85.38    -2.6725       1
8 5 24 0 slack:2   1.0000   0.6260   1.0000     86.00    -2.7500       1
8 5 24 0 slack:4   1.0000   0.6373   1.0000     86.48    -2.8100       1
8 5 24 8 shortest  1.0000   0.8144   1.0000     85.36    -2.6700      63
8 5 24 8 equal     1.0000   0.8616   1.4118     83.48    -2.4350     218
8 5 24 8 slack:2   1.0000   0.7648   4.9272     81.92    -2.2400     256
8 5 24 8 slack:4   1.0000   0.6901  17.0399     81.80    -2.2250     256
```

Reading:

- State-carrying surface choice is real: `r=8, slack:4` improves the one-pass
  miss from `-2.81` bits/atom in the `r=0` slack row to `-2.225` bits/atom.
- The lift comes from decoder-visible state alternatives, not a stored salt.
- The row is still paid-negative: output is `81.80` bits for `64` input bits.

## Observe Versus Condition Control

Command:

```text
python model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py --items 8 --trials 50 --block-bits 8 --max-arity 5 --depth 24 --state-bits 8 --policy slack:4 --condition-tail-bits 8
```

Result:

```text
support=1.0000
edgeHit=0.4147
choice/h=1.0000
outBits=137.98
gain/atom=-9.2475
states=1
```

Requiring eight particular tail bits collapses the option cloud and pushes the
miss from `-2.225` to `-9.2475` bits/atom. This is exactly the desired audit:
observed control tail is free; requested control tail is paid in witness supply.

## Tiny Two-Pass Recurrence Check

Command:

```text
python model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py --items 8 --passes 2 --trials 20 --block-bits 8 --max-arity 5 --depth 24 --state-bits 8 --policy slack:4
```

Result:

```text
pass1 support=1.0000
two-pass support=0.4000
pass1 outBits=81.65
pass1 gain/atom=-2.20625
mean final log2 rho=0.76289
```

The selected surface does not yet create a self-sustaining recurrent law. The
second pass often has no full cover at this depth, and completed trials expand
relative to the original layer.

## Labeled Custom-Arity Probe

V1 exact arity coding only supports `K<=5`. A clearly labeled fixed-width
custom arity row:

```text
python model_analysis/birth_channel_research/H175-state_carrying_transducer_dp.py --items 8 --trials 50 --block-bits 4 --max-arity 8 --depth 24 --state-bits 8 --policy slack:4 --arity-code fixed
```

Result:

```text
B=4,K=8,D=24,r=8,fixed arity
support=1.0000
edgeHit=0.9865
choice/h=15.5545
outBits=43.28 for 32 input bits
gain/atom=-1.4100
states=256
```

This is closer, but it is not an exact V1 row and still does not cross.

## Verdict

H175 validates the mechanism without upgrading it into a claim:

```text
state tail observation creates real decoder-visible future-state choices
bounded slack can use those choices to improve paid full-cover cost
conditioning the tail immediately pays the expected supply bill
the tested V1/J3D1 rows remain paid-negative
two-pass recurrence does not yet sustain full cover
```

The next kernel should keep this transducer but reduce the search space before
running the full pasted grid. The practical target is:

```text
beam or value-iteration over (position, q)
+ exact support/gain ledger
+ 2-16 pass log2 rho distribution
+ no hidden anchors unless r/A is charged explicitly
```

Uncapped `r=16` and broader `D=80` rows were already large enough to become a
trellis-scaling problem during this first build. That is not a research
failure; it is the expected encoder-side cost of turning surface-choice
superposition into an actual dynamic program.
