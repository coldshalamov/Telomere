# H102 - Public Lane Local Class Grammar

Date: 2026-06-18

## Question

H99/H101 price visible seed parity as a paid readiness channel. But what if the
seed witness does not have to carry the class? A public lane/position could tell
the decoder which epoch grammar applies, and the witness could be a local rank
inside that grammar's seed class.

Runnable artifact:

```text
model_analysis/birth_channel_research/H102-public_lane_local_class_grammar.py
```

## Mechanism

Use a fixed public two-epoch lane rule:

```text
pass t:
  current lane opens using grammar G[t mod 2]
  old lane carries using grammar G[(t - 1) mod 2]
  old lane must be refreshed or literalized before it can age again
```

For current records, the witness is not a global seed index whose low bit must
be visible. It is a local index in the public class-specific enumerator:

```text
seed = G[class].seed_at(local_rank)
```

So `W` witness bits name `2^W` seeds inside the class. This avoids the one-bit
seed-supply loss from visible even/odd seeds. It is honest only if the lane that
selects the class is public or paid.

## Counting Sanity

For arbitrary content-selected ready/carry membership, a boundary is not enough:

```text
N=1,000,000, R/N=0.50:
  boundary/open = 0.000040 bits
  subset/open   = 1.999979 bits

N=1,000,000, R/N=0.99:
  boundary/open = 0.000020 bits
  subset/open   = 0.081601 bits
```

A fixed public lane has one valid membership pattern, so the class is free as a
decode observation. A content-selected lane pays subset entropy.

## Result

Visible global seed class:

```text
positive iff margin_per_record > class_loss
```

Public lane plus local class grammar:

```text
positive iff margin_per_record > 0
```

Content-selected lane plus local class grammar:

```text
positive iff margin_per_record > H(q) / q
```

Current paid rows still fail because their base margins are negative:

```text
H7 public-lane q=1:  -0.011927 bits/atom
H9 public-lane q=1:  -0.012314 bits/atom
H12 public-lane q=1: -0.008196 bits/atom
```

But a separate collective mechanism worth only `+0.28` bits/record would survive
this lane geometry:

```text
hyp +0.28, q=1:
  visible global parity, class_loss=1.000000 -> -0.007200 bits/atom
  public lane local grammar                  -> +0.002800 bits/atom
```

## Verdict

This is the cleanest surviving stateless-decode shape found in this branch:

```text
public two-epoch lanes
+ class-local seed enumeration
+ mandatory old-cohort refresh/literalization
+ separate paid witness mechanism with margin > 0
```

It does not create compression by itself. It removes the per-record visible
parity tax by moving readiness into public geometry. The remaining hard target
is now narrower: find a paid forced-rewrite witness mode with positive base
margin. Collective/all-description coding remains the nearest place to search.
