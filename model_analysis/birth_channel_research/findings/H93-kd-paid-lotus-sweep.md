# H93 - Paid Extended-Arity Lotus K/D Sweep

Date: 2026-06-17

## Question

H92 found collective Kraft crossings for `K>5`, but those rows used an
optimistic extension cost that omitted Lotus witness-width metadata.

Do those crossings survive if the extended arity records pay:

```text
ceil(log2(K)) + J3D1(seed_payload_width)
```

while `K<=5` continues to use exact V1 costs?

Runnable artifact:

```text
model_analysis/birth_channel_research/H93-kd_paid_lotus_sweep.py
```

## Result

No paid crossings.

Best selected row:

```text
K=12, D=12, log2 Z_best=-6.054405, Z_best=0.015047
```

Best collective row:

```text
K=12, D=12, log2 Z_total=-5.301885, Z_total=0.025350
```

The H92 positive rows disappeared once the J3D1 width field was paid.

## Reading

This is a direct anti-reward-hack check. Higher `K` and deeper `D` can create
many more local opportunities, but in this exact tiny domain the paid Lotus
witness metadata more than consumes that gain.

The conclusion is not "larger arity can never matter." It is:

```text
under this paid extended-arity Lotus model, K/D alone does not make witness
Kraft mass cross 1.
```

## Verdict

The H92 crossing was an underpriced-witness artifact. The next constructive
route cannot be merely "increase K/D" under paid Lotus accounting; it needs a
new collective witness code, a different paid record grammar, or an actual
source/fertility law that survives H90's Kraft accounting.
