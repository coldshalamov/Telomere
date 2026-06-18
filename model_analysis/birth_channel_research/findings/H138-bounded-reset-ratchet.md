# H138 - Bounded Reset Ratchet

## Question

Can rare reset/literalization events bound bad blowups while ordinary passes
keep a negative drift, giving maintained compression over arbitrary passes?

## Model

A reset caps damage but destroys accumulated recursive shrink. After `P` passes,
the final saving is governed by the good suffix since the last reset:

```text
expected_suffix_good = sum_{k=1..P} (1-eps)^k
```

If reset markers/literalization are visible in the recursive layer stack, they
also add:

```text
expected_marker_cost = P * eps * marker_bits
```

## Result

Representative rows with `marker=3` bits:

```text
P=4096, eps=0.01, s=1 bit/good pass:
  expected_suffix_good = 99.000
  marker cost = 122.880
  net/pass = -0.005830
  no-reset probability = ~0
  half-rate probability = ~0

P=4096, eps=0.001, s=1:
  expected_suffix_good = 982.412
  net/pass = 0.236847
  no-reset probability = 0.016605
  half-rate probability = 0.128861

P=4096, eps=0.0001, s=1:
  expected_suffix_good = 3360.642
  net/pass = 0.820169
  no-reset probability = 0.663902
  half-rate probability = 0.814802
```

To keep at least half the ideal all-good suffix with `90%` probability:

```text
P=64:
  eps <= 0.00328710173

P=256:
  eps <= 0.000822790351

P=4096:
  eps <= 0.000051444241

P=1,000,000:
  eps <= 0.000000210721
```

## Interpretation

A reset ratchet is useful bounded-loss engineering. It is not maintained
arbitrary-pass compression unless the reset probability shrinks like `O(1/P)`
or reaches zero.

If resets are common enough to be a real fallback, the final file only preserves
the suffix of good passes after the last reset. If resets are rare enough to
preserve roughly-all linear savings for huge `P`, then they are not the
mechanism maintaining match rate; some other near-total/witness/fertility
mechanism already did the hard work.

## Artifact

`model_analysis/birth_channel_research/H138-bounded_reset_ratchet.py`
