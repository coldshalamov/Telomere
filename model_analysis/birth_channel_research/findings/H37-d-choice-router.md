# H37 - d-choice self-routing / cuckoo placement

Date: 2026-06-17

## Question

Can cuckoo-style self-routing, minimal perfect hashing, or egg-carton placement
let the decoder recover ready status and final position without per-record
metadata?

Mechanism:

```text
record has d public candidate cells
decoder uses a canonical router / matching rule
```

This is stateless and parseable. The question is whether route choice carries
content-dependent information for free.

## Public active/fertile lanes

If an active or fertile lane occupies public fraction `r`, one candidate pays:

```text
supply_loss = -log2(r)
```

With `d` independent public candidate cells, the chance at least one candidate
is in the lane is:

```text
f = 1 - (1-r)^d
supply_loss = -log2(f)
```

H37 examples:

```text
r=0.10,d=1:  f=0.100000, loss=3.322 bits
r=0.10,d=4:  f=0.343900, loss=1.540 bits
r=0.10,d=8:  f=0.569533, loss=0.812 bits
r=0.10,d=16: f=0.814698, loss=0.296 bits

r=0.01,d=16: f=0.148542, loss=2.751 bits
```

This is a real constant-factor improvement over a single public lane. It lowers
the value-lift threshold for H28/H36 fertility lanes.

## Exact destination

If placement must identify a particular destination among `Q` cells, `d`
choices save only `log2(d)` bits:

```text
destination_supply_loss ~= log2(Q/d)
```

H37 examples:

```text
Q=1,000,000,d=1:  loss=19.932 bits
Q=1,000,000,d=16: loss=15.932 bits
Q=1,000,000,d=64: loss=13.932 bits
```

So d-choice routing helps constants, not the fundamental coordinate bill.

## Matching ambiguity

Small exact routing graphs show many valid matchings:

```text
Q=16,m=8,d=2: matchings=16,   ambiguity=4.000 bits
Q=16,m=8,d=3: matchings=1321, ambiguity=10.367 bits
Q=16,m=8,d=4: matchings=7456, ambiguity=12.864 bits
```

A canonical matching is free only because the decoder chooses it publicly. If
the encoder chooses a matching after seeing content, the ambiguity bits are a
paid route selector.

Board/slot bills remain:

```text
holes/occupancy: log2 C(Q,m)
ordered slots:   log2 P(Q,m)
```

## Stable compaction

Boundary-only compaction is cheap when active records are a public prefix:

```text
N=1,000,000,r=0.10,m=100,000: boundary/open=0.000199 bits
```

But if the active set is content-selected, the hidden subset bill is:

```text
log2 C(N,m) / m
```

H37:

```text
N=1,000,000,r=0.10: subset/open=4.690 bits
N=1,000,000,r=0.50: subset/open=2.000 bits
```

This matches H21/H35.

## Verdict

d-choice routing is useful stateless machinery and slightly improves the live
fertility-lane target. It is not an unpriced placement channel:

- public lane membership has reduced but nonzero supply loss;
- exact destination still pays coordinate supply;
- encoder-selected matchings are metadata;
- arbitrary ready subsets still pay `log2 C(N,m)`;
- arbitrary order/holes still pay board or permutation entropy.

Best use:

```text
H28 public fertility class
+ H36 developmental source/fertility law
+ H37 d-choice routing to lower lane supply loss
+ H30 public dither for freshness
```

Then require measured:

```text
value_lift > -log2(1-(1-r)^d)
```

with uniform controls negative.

## Artifact

`model_analysis/birth_channel_research/H37-d_choice_router.py`
