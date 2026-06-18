# H85 - Entropy-Budget Fertility

Date: 2026-06-17

## Question

H84 says repeatability needs high-entropy fertility: future compression value
must separate from mere source entropy deficit.

Is that kind of separation mathematically plausible, or does a uniform future
value tail rule it out?

Runnable artifact:

```text
model_analysis/birth_channel_research/H85-entropy_budget_fertility.py
```

## Model

Assume the uniform/content-blind future value tail:

```text
Pr_U[V >= s] = 2^-s
```

For a public source `P` with entropy deficit:

```text
delta = D(P || U)
```

the maximum `E_P[V]` is achieved by exponential tilting of the geometric value
distribution.

## Frontier

```text
delta      E[V]    lift    lift-delta   gamma
0.001000   1.0534  0.0534    0.0524    53.350
0.010000   1.1735  0.1735    0.1635    17.349
0.050000   1.4075  0.4075    0.3575     8.150
0.216226   1.9289  0.9289    0.7127     4.296
1.365022   3.9626  2.9626    1.5975     2.170
```

Minimum entropy budgets for finite margins:

```text
margin    delta needed
0.050000   0.000912
0.216226   0.017703
0.500000   0.101121
1.000000   0.457214
2.000000   2.393152
```

## Reading

This is an ideal upper bound, not a Telomere mechanism. It says a
high-entropy fertile source law is mathematically plausible: a small entropy
deficit can, in principle, create future value lift larger than the deficit.

That makes the H84 target worth pursuing:

```text
Find a public native syntax whose measured future-value tail behaves like
this, while uniform controls remain negative.
```

## Verdict

H85 does not solve arbitrary uniform recursion, but it keeps the biology-shaped
value/count separation lane alive.

The next experiment should measure the future-value tail of actual native
Telomere record syntax, not just its entropy or class membership.
