# H149 - Decode-Composition Capacity

Date: 2026-06-18

## Question

Can a final top-layer stream decode through larger intermediate layers and
eventually shrink to a bottom file, with no stop marker, branch selector, or
sidecar?

Runnable artifact:

```text
model_analysis/birth_channel_research/H149-decode_composition_capacity.py
```

## Model

The kernel builds a tiny fixed public record language:

```text
[fixed arity bits][J3D1 seed witness]
```

with SHA-like seed expansion. It enumerates every valid top-layer record stream
up to a small bit cap, applies the public decoder for a fixed number of passes,
and counts which `n`-bit bottom strings are reached by a top stream of length:

```text
<= n - saved_bits
```

There is no stop depth, no branch choice, and no intermediate selector. If an
intermediate layer is larger, it must itself be a valid record stream for the
next decode pass.

## Results

Default high-arity custom toy:

```text
B=1,K=16,D=4,stream_cap=18,output_cap=24
valid top streams = 476
```

One pass has a few lucky short addresses:

```text
P=1,n=16,saved=4:
  reachable outputs = 13
  coverage = 0.000198
  mean saving on reached = 4.538462 bits
```

But fixed two-pass composition collapses:

```text
P=2:
  composed streams = 3
  reachable outputs at n=1..16,saved=1 = 0

P=3:
  composed streams = 0
```

Slightly wider high-arity toy:

```text
B=1,K=32,D=3,stream_cap=20,output_cap=40
valid top streams = 980

P=1,n=32,saved=4:
  reachable outputs = 37
  coverage = 8.615e-09
  mean saving on reached = 13.702703 bits

P=2:
  composed streams = 1
  reachable outputs at n=16,24,32 = 0
```

## Reading

Upward expansion is possible in the high-arity custom language, but repeatable
stateless recursion is much harsher: the first decoded layer has to be a valid
record stream by accident. That self-parse event is the support bottleneck.

Every successful multi-pass path is just one final top-layer address. Coverage
stays below the ordinary final-length counting bound, and any missing branch or
stop choice would have to be visible or paid.

## Verdict

H149 strengthens H148: the failure is not just poor greedy choice, it is
fixed-decoder self-parse support. The next constructive route must deliberately
make the output record language closed or fertile under the same decoder, and
then pay the Kraft/support cost of that closure.
