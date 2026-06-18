# H61 - Scientific Phase Diagram

Date: 2026-06-17

## Question

The next work should behave like science: learn the response surface, keep the
currencies separate, and zero in on mechanisms that move a measured boundary.

H61 turns the current ledger into a phase diagram. It does not run seed search.
It asks how many honest bits still have to move for each class of mechanism:

```text
uniform arbitrary data
public stateless mechanism
source-shaped / fertility mechanism
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H61-scientific_phase_diagram.py
```

The kernel reports:

- closest uniform/public frontiers;
- exact paid witness gaps;
- public lane value-lift boundaries;
- near-total open/carry ledger costs;
- roughly-all coverage gates;
- recursive EOF length-path costs.

## Closest Honest Frontiers

The nearest rows by gap per atom are:

```text
H59 raw/Q mixture T1:        +0.053411 bits/layer, +0.000139 bits/atom
H58 frozen bucket Q:         +0.229195 bits/layer, +0.000597 bits/atom
H12 perfect-credit upper:    +0.008196 bits/atom
H7 raw first-hit cover:      +0.011929 bits/atom
H9 fixed slack 0:            +0.012314 bits/atom
```

These are very close numerically, but under the uniform law a public code cannot
have negative expected excess:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

So the tiny H58/H59 misses are not "almost arbitrary-data compression" unless a
candidate supplies a non-hidden way to evade that KL boundary.

## Paid Witness Gaps

For the total-cover witness branch:

```text
H12 perfect-credit upper bound: missing 0.746 bits/record, 0.008196 bits/atom
H7 raw first-hit total cover:   missing 1.357 bits/record, 0.011929 bits/atom
H9 fixed slack 0:               missing 1.261 bits/record, 0.012314 bits/atom
```

This is the engineering target if the mechanism stays uniform and paid: remove
about `0.75-1.36` bits per selected record without hiding a selector.

## Public Lane Boundary

A public position/phase lane can be statelessly decoded, but its cost moves to
match supply:

```text
lane_loss = -log2(1 - (1-r)^d)
```

Representative value lift needed per selected record:

```text
r=0.10,d=16: standalone 0.296 bits; with H7 gap 1.653 bits
r=0.10,d=64: standalone 0.002 bits; with H7 gap 1.359 bits
r=0.25,d=16: standalone 0.015 bits; with H7 gap 1.372 bits
r=0.50,d=4:  standalone 0.093 bits; with H7 gap 1.450 bits
```

So public lanes are plausible as decode geometry, but they need a real
fertility/value lift. They do not create one automatically.

## Near-Total State Ledger

If almost everything rewrites each pass, open/carry metadata is not the main
bottleneck:

```text
P=64,eps=0.010:     0.140566 bits/atom
P=4096,eps=0.001:   0.023407 bits/atom
```

This validates the user's instinct that total-cover or near-total-cover is the
right branch. It removes the birth/open problem only after the paid witness
problem is solved.

## Roughly-All Gate

For arbitrary uniform data, a paid `S`-bit saving can cover at most `2^-S` of
inputs. To make that winning set cover almost all source probability, the source
must be non-uniform by a huge amount:

```text
S=8,c=0.90:    required lift 230.4, KL deficit 6.731569 bits
S=128,c=0.90:  required lift 3.06254e38, KL deficit 114.731004 bits
```

This is the sharp split:

- uniform arbitrary-data recursion is blocked by counting;
- source-shaped recursion is possible only if the source lift is named and
  measured.

## EOF / Board / Best-Of Reading

EOF/non-prefix coding can be real for one known fixed length. The recursive
problem is the intermediate length path:

```text
P=64,S=128: length-path cost 123.171434 bits
P=64,S=256: length-path cost 201.566936 bits
```

Best-of and checksum lanes have the same character. They are allowed as
candidates, but the profile identity, arrangement, checksum, or path has to fit
inside the measured frontier gap.

## Decision Rules

1. If a candidate claims uniform arbitrary-data compression, it must beat the
   public-code KL check without a hidden selector.
2. If a candidate is a public stateless lane, score the lane loss and witness
   gap before calling it compression.
3. If a candidate is source-shaped or biology-like, name the non-uniform source
   lift explicitly. That may be the missing piece, but it is not arbitrary-data
   compression.
4. If a candidate uses final boards, checksums, best-of profiles, EOF, or trial
   decode, keep it alive only if the paid ledger is below the closest frontier
   gap.

## Current Best Target

The most promising honest target is not another hidden selector. It is:

```text
public/stateless total-cover geometry
+ a measured non-uniform fertility/source law
+ uniform negative controls
+ paid witness below the H58/H59 frontier
```

That is the closest way to make the DNA analogy concrete without smuggling the
answer through a side channel.
