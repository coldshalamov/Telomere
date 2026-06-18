# H128 - Near-Total Exception Threshold

## Question

If public-coordinate geometry makes almost every slot open, how small must the
exception set be for its ledger to fit under the measured H124 raw-fallback
margin?

Ledger model:

```text
H2(eps) + eps * log2(P - 1)
```

## Result

The required coverage is extremely high.

For the measured H124 margins:

```text
margin 0.014587 bits/atom/pass:
  P=2     eps <= 0.001326  coverage >= 99.8674%
  P=64    eps <= 0.000826  coverage >= 99.9174%
  P=4096  eps <= 0.000604  coverage >= 99.9396%

margin 0.023438 bits/atom/pass:
  P=2     eps <= 0.002296  coverage >= 99.7704%
  P=64    eps <= 0.001386  coverage >= 99.8614%
  P=4096  eps <= 0.001001  coverage >= 99.8999%
```

Even an optimistic `0.10 bits/atom/pass` margin only allows about `0.47%`
exceptions by `P=4096`.

## Interpretation

Public near-total boards remain a mathematically live shape, but the target box
is tiny. A candidate must maintain roughly `99.8-99.94%` public opening under
the currently measured margins before exception metadata is affordable.

## Artifact

`model_analysis/birth_channel_research/H128-near_total_exception_threshold.py`
