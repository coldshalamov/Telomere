# H91 - Witness Kraft Boost Budget

Date: 2026-06-17

## Question

H90 says no public law over a fixed witness family can cross unless that
family's Kraft mass is above `1`.

How much honest boost would a real mechanism have to provide?

Runnable artifact:

```text
model_analysis/birth_channel_research/H91-witness_kraft_boost_budget.py
```

## Model

Use the exact H74/H89 finite domain:

```text
B=1, N=12, K=6, D=8
```

Recompute both selected-best and all-description masses after multiplying every
record/edge weight by:

```text
2^bonus
```

This models an honest per-record cost reduction or equivalent free match-supply
boost. The target is:

```text
Z_bonus >= 1
```

## Result

```text
family             base Z       flat bits  record bits  records/word
best selected      0.221606134  2.173930   1.086792        2.000
all descriptions   0.676912187  0.562959   0.277599        2.028
```

## Reading

The selected-witness family is far from crossing. It needs either:

```text
2.173930 flat bits/word
```

or about:

```text
1.086792 bits/record
```

The collective all-description family is much closer:

```text
0.562959 flat bits/word
0.277599 bits/record
```

This is the sharpest constructive target exposed by H89/H90.

## Verdict

The next breakthrough lane should focus on the collective/all-description
family, not selected best-cover records.

Any candidate must explain where roughly `0.28` honest bits per record come
from in this toy domain, and then show the same mechanism scales without paying
the bits back as delimiters, source profiles, birth/pass labels, final-board
coordinates, or rare-tail losses.
