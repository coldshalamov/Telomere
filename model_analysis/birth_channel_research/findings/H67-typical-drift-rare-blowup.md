# H67 - Typical Drift / Rare Blowup

Date: 2026-06-17

## Question

H49-H59 use `E[log2 rho] < 0` as the repeated-pass reproduction target. That is
the right local diagnostic, but it is not by itself the full goal:

```text
repeatable stateless compression over roughly all data for arbitrary P
```

Under uniform content-blind coding, expected length cannot fall below raw. So a
negative geometric drift can coexist with conservation only through rare large
expansions.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H67_typical_drift_rare_blowup.py
```

Toy law:

```text
rho = a < 1 with probability 1-eps
rho = b > 1 with probability eps
choose b so E[rho] = 1
```

## Representative Results

For `a=0.99, eps=0.01`, conservation requires:

```text
b = 1.990
E[log2 rho] = -0.004427
```

But over passes:

```text
P=64:   Pr(at least one blowup) = 0.474404
P=256:  Pr(at least one blowup) = 0.923686
P=4096: Pr(at least one blowup) = ~1.0
```

For `eps=0.001`:

```text
P=64:   Pr(at least one blowup) = 0.062025
P=256:  Pr(at least one blowup) = 0.225957
P=4096: Pr(at least one blowup) = 0.983395
```

## Verdict

A negative mean log-rho row is not enough for the user’s arbitrary-pass,
roughly-all-data goal. It must also report tail risk.

To keep roughly-all success for arbitrary `P`, the bad fraction must shrink like
`O(1/P)` or be exactly zero. Exact zero bad fraction with net shrink is an
injective compression of all uniform inputs, which hits the counting wall.

So future all-block RG rows should carry both:

```text
E[log2 rho]
tail / blowup probability over P passes
```

This does not invalidate the reproduction-number harness. It sharpens its claim
boundary.
