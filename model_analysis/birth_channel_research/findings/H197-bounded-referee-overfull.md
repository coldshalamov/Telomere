# H197 - Bounded Referee / Hidden-Lane Overfull Closure

## Conjecture

```text
An overfull ambiguous witness family can create more short candidates than a
prefix/Kraft code would allow, and a bounded checksum/referee can cheaply prune
the survivors during stateless decode.
```

This tests the last H195-adjacent hidden-channel route: omit lane or selector
bits, let the decoder trial-decode candidates, and use a small fixed referee to
choose the right one.

## Kernel

`H197-bounded_referee_overfull.py`

The kernel has two parts:

1. Exact coalescence toy:

```text
raw N-bit target -> visible K-bit ambiguous witness
candidate count per item = 2^(N-K)
```

2. H195 hidden-lane bill:

```text
q_single  = witness Kraft mass for one public lane
q_hidden  = lanes * q_single       # lane id omitted
surplus   = log2(q_hidden)
lane_bill = ceil(log2(lanes))
```

For checksums, one true candidate among `M` candidates is unique with
probability at least `u` only if:

```text
c ~= log2(M) - log2(-ln(u))
```

At `u=0.99`, this is:

```text
c ~= log2(M) + 6.636612
```

## Result

Exact coalescence toy:

```text
raw=2, visible=1, R=1:
  apparent gain = 1
  selector bits = 1
  exact net     = 0
  checksum@99   = 7.636612
  checksum net  = -6.636612

raw=2, visible=1, R=32:
  apparent gain = 32
  selector bits = 32
  exact net     = 0
  checksum@99   = 38.636612
  checksum net  = -6.636612
```

H195 hidden lane example:

```text
Wmax=8, lanes=20:
  q_hidden = 1.015625
  apparent surplus = 0.022368
  lane selector bits = 5
  exact net = -4.977632
  checksum net at 99% = -11.614245

Wmax=8, lanes=32:
  q_hidden = 1.625000
  apparent surplus = 0.700440
  lane selector bits = 5
  exact net = -4.299560
  checksum net at 99% = -10.936173
```

The broad default table's best hidden-lane exact row is still negative:

```text
Wmax=16, lanes=256:
  apparent surplus = 4.285402
  lane selector bits = 8
  exact net = -3.714598
```

## Bill

Overfullness creates surplus only by leaving multiple possible readings. Exact
lossless decode needs:

```text
selector bits >= log2(candidate count)
```

A checksum/referee cannot beat this asymptotically; it replaces exact selection
with high-probability uniqueness and adds a reliability margin.

## Mutation

Bounded referees can make finite toys decode and are useful as positive controls
or safety checks. They do not create maintained arbitrary-uniform recursive
drift. The next live constructive direction should move back toward generated /
reachable developmental regimes, but make them more Telomere-native than H183
and keep the reachable-set membership tax explicit.

