# H133 - Common-Cause Batch Witness

## Question

Can one base witness derive several child witnesses and avoid paying the
per-record boundary/width bill?

This tests a tempting biology-shaped idea:

```text
one common cause -> many child records
```

If the children are independent uniform hash outputs, the honest accounting is
an m-fold convolution of the ordinary record masses. If the batch claims a
shared-overhead discount without removing equal mass elsewhere, the symbol
grammar becomes overfull.

## Model

H108 exact recurrence:

```text
Z_0 = 1
Z_n = sum_A W_A Z_{n-A}
```

Batch mass:

```text
W_batch = W_base * W_base * ... * W_base
```

Public mixtures are allowed:

```text
W = lambda W_base + (1-lambda) W_batch
```

Discounted batches are reported but marked invalid when:

```text
sum_A W_A > 1
```

## Result

Exact `Fraction` recurrence over H108 `custom_record`, `B=1,N=12`.

```text
base_custom_record:
  log2 symbol mass = 0.000000
  log2 Z_N = -1.781751
  valid = true

batch_only m=2:
  log2 symbol mass = 0.000000
  log2 Z_N = -2.897549
  valid = true

batch_only m=3:
  log2 symbol mass = 0.000000
  log2 Z_N = -2.993887
  valid = true

batch_only m=4:
  log2 symbol mass = 0.000000
  log2 Z_N = -3.371130
  valid = true
```

The best public base/batch mixture selected the base grammar:

```text
best valid log2 Z_N = -1.781751
```

The attractive rows require overfull symbol mass:

```text
discounted_batch m=2, discount=2:
  log2 symbol mass = 2.000000
  log2 Z_N = 1.220990
  valid = false

discounted_batch m=2, discount=3:
  log2 symbol mass = 3.000000
  log2 Z_N = 3.612808
  valid = false
```

## Interpretation

Common-cause batching is not a free boundary escape under the uniform hash law.
If the derived child witnesses are independent, the batch is just a
redistribution of the same Kraft mass and can be worse than the base record
family. If the batch saves bits by fiat, the savings appears as positive
`log2(symbol mass)`, i.e. an overfull code.

This keeps one narrower door open: a real batch witness would need a genuine
joint law or recursive fertility transfer, not independent child seeds. That
belongs to the fertility/operator branch, not to ordinary higher arity or
record-boundary amortization.

## Artifact

`model_analysis/birth_channel_research/H133-common_cause_batch_witness.py`
