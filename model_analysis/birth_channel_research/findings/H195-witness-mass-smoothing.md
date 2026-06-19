# H195 - Public Multi-Salt Witness-Mass Smoothing

## Conjecture

```text
Many public decoder-known salt lanes can keep exact-witness supply fresh and
smooth the induced witness distribution enough that the leftover raw fallback
becomes negative-drift on arbitrary uniform layers.
```

This is the strongest mutation of H190-H194 that does not use sparse carried
records, birth-pass maps, hit maps, or final-position ledgers. Every record is
opened by the current pass. The only new syntax is a public lane id, priced as a
fixed prefix when more than one lane is available.

## Kernel

`H195-witness_mass_smoothing.py`

For each target width `N`, exact V1/J3D1 payload frontier `Wmax`, and public
lane count `L`, the kernel enumerates the tiny output universe and hashes every
exact witness label:

```text
output = H(public_lane, payload_width, rank) mod 2^N
length = record_cost_for_payload_width(1, payload_width) + ceil(log2 L)
s_x    = sum 2^-length for witnesses landing on x
q      = sum_x s_x
Q(x)   = (1-q)/2^N + s_x
```

The paid mean for arbitrary uniform `N`-bit targets is:

```text
E_U[-log2 Q(X)]
gain = N - E_U[-log2 Q(X)]
```

## Result

Bounded default:

```text
N=8,Wmax=8,lanes=16,mode=all:
  q=0.050781, support=256/256, gain=-0.000956 bits/layer

N=12,Wmax=8,lanes=16,mode=all:
  q=0.050781, support=3537/4096, gain=-0.009665 bits/layer

N=16,Wmax=8,lanes=16,mode=all:
  q=0.050781, support=7629/65536, gain=-0.035389 bits/layer
```

Larger public lane probes show the expected smoothing:

```text
N=8,Wmax=8,lanes=4096,mode=all:
  q=0.050781, support=256/256, gain=-0.000005239 bits/layer

N=12,Wmax=8,lanes=512,mode=all:
  q=0.050781, support=4096/4096, gain=-0.000517 bits/layer

N=16,Wmax=8,lanes=256,mode=all:
  q=0.050781, support=56594/65536, gain=-0.009580 bits/layer
```

This is a real maintained-supply effect: more public lanes reduce witness-mass
variance, increase support, and push the miss toward zero while keeping nonzero
witness mass. It still does not cross.

## Bill

Let `U` be uniform over the layer outputs. Since the leftover raw fallback and
all witnesses form a normalized decodable distribution `Q`:

```text
E_U[-log2 Q(X)] = N + D(U || Q) >= N
```

Equality is possible only when the aggregate witness mass is exactly uniform:

```text
s_x = q / 2^N for every x
```

Public lanes can approach that limit by the law of large numbers, but with lane
ids paid they approach a tie, not negative drift. If lane ids are not paid, the
extra supply is a hidden syntax channel and the Kraft mass overfills. If only
high-mass outputs are promoted, the missing entropy becomes a source/support
restriction.

## Mutation

H195 is the cleanest arbitrary-uniform near-tie so far with nonzero witness
effect and non-collapsing support. The next attack cannot merely add more
public independent salts. It must change one of these conditions:

```text
1. produce a normalized Q whose average under the actual source is not uniform,
   and pay the source/reachable membership tax;
2. find a legitimate overfull-looking mechanism whose referee/ambiguity bill is
   bounded below the surplus;
3. use public salt lanes only as a smoothing component inside a separate
   non-uniform generated/reachable regime.
```

