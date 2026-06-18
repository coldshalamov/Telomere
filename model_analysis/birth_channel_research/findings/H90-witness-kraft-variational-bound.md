# H90 - Witness Kraft Variational Bound

Date: 2026-06-17

## Question

H89 showed that `Q`-score soft laws improve actual witness savings but remain
negative. Could a better public law over the same witness family cross, or is
the whole fixed family bounded below zero?

Runnable artifact:

```text
model_analysis/birth_channel_research/H90-witness_kraft_variational_bound.py
```

## Theorem

Let `U` be uniform over `M` raw words. Let a public witness family assign each
word a Kraft weight:

```text
w(x) = 2^-cost(x)
```

Define actual saving:

```text
S(x) = log2(M) + log2 w(x)
```

Then for any public source law `P`:

```text
E_P[S] - D(P || U) = log2 Z - D(P || w/Z)
```

where:

```text
Z = sum_x w(x)
```

So:

```text
sup_P [E_P[S] - D(P || U)] = log2 Z
```

with equality at:

```text
P*(x) = w(x) / Z
```

## Exact H89 Domain

```text
family             Z             log2 Z
best selected      0.221606134   -2.173930
all descriptions   0.676912187   -0.562959
```

Equality-law details:

```text
family             H(P*)      D(P*||U)   E_P*[S]
best selected      10.035690  1.964310  -0.209620
all descriptions   10.634978  1.365022   0.802063
```

The equality law can have positive expected selected saving, but after paying
the source-law deficit, the net margin is exactly `log2 Z`.

## Reading

H89's negative result is not a bad tilt. It is a Kraft mass bound.

For the fixed selected-witness family, no public native law over the same
outputs can cross because `Z_best < 1`. The collective all-description family
is closer, but still cannot cross because `Z_total < 1`.

## Verdict

The next constructive target is not "find a better public tilt." It is:

```text
increase honest witness Kraft mass above 1, or add a new public invariant
whose visible-state bill is paid.
```

Any claimed mechanism must show where the missing Kraft mass comes from without
moving the bits into witness delimiters, profile selectors, final boards, or
birth/pass ledgers.
