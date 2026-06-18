# H54 - selector referee budget

Date: 2026-06-17

## Question

Can the existing trial-decode checksum/referee pay for adaptive Total-Cover
profile choices, such as the H53 global slack ladder, without an explicit
selector stream?

This is the honest version of "try several decodes and keep the one that
checks out." It is stateless execution, but the checksum is a finite selector
budget.

## Mechanism

For one global profile choice per pass:

```text
S = number of public profiles
P = passes
C = checksum/referee bits
lambda = safety bits
candidate profile sequences = S^P
ambiguity bits = P * log2(S)
```

The referee is safe only while:

```text
P * log2(S) <= C - lambda
```

So:

```text
P_max = floor((C - lambda) / log2(S))
```

This is H25's global referee law specialized to global Total-Cover selectors.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H54-selector_referee_budget.py
```

Default run:

```text
python model_analysis\birth_channel_research\H54-selector_referee_budget.py
```

Representative selector capacities with `lambda=32`:

```text
C=64,  S=3:  20.190 global selectors
C=128, S=3:  60.569 global selectors
C=256, S=3: 141.328 global selectors

C=256, S=4: 112.000 global selectors
C=256, S=8:  74.667 global selectors
```

Pass-sequence safety examples:

```text
C=256, S=3, P=128: safe, margin 21.125 bits after safety
C=256, S=3, P=256: over budget by 181.750 bits after safety
C=128, S=3, P=64:  over budget by 5.438 bits after safety
```

## Interaction with H53

The current H53 row does not merely fail because the selector is expensive:

```text
H53 paid S={0,1,2}, B4 K192 D768:   +0.004480 mean log2 rho
H53 unpaid S={0,1,2}, B4 K192 D768: +0.001973 mean log2 rho
```

The unpaid lower bound still expands. A checksum/referee can select among
candidate profile sequences; it cannot make a positive unpaid reproduction
number negative.

## Accounting

Stored/paid:

- checksum/referee bits `C`, if not already charged in the layer/file format;
- otherwise the finite ambiguity budget consumed from that checksum;
- any selector entropy beyond `C - lambda`.

Derived:

- trial-decode candidate profile sequences;
- public profile alphabet `S`;
- checksum failure of wrong candidates inside the finite budget.

Hidden if omitted:

- `P * log2(S)` bits of profile-sequence identity;
- false survivors once `P * log2(S) > C - lambda`;
- the selector stream if the mechanism is claimed over arbitrary passes.

## Verdict

A checksum can honestly referee a finite number of adaptive global selectors.
It cannot create an unbounded stateless selector channel.

For the current H53 slack ladder, the selector-referee trick is not enough even
inside the finite window because the unpaid row still expands. For a future row
where:

```text
unpaid mean log2 rho < 0
paid mean log2 rho > 0
```

the checksum-referee version would be a bounded finite-pass demo, with max
passes set by `P_max`. It would not satisfy the active goal of arbitrary-pass
maintained compression unless a unique decoder invariant removes the selector
entropy completely.
