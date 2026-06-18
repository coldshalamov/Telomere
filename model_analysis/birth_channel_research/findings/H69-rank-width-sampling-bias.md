# H69 - Rank-Width Sampling Bias

Date: 2026-06-17

## Question

One scout found a concrete measurement caveat in the total-cover runner:
large-span first-hit ranks were rounded to a power-of-two integer before Lotus
payload width was computed. That can conservatively overcharge high-arity rows.

H69 calibrates the effect.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H69-rank_width_sampling_bias.py
```

The corrected path samples `log2(rank)` under the exponential-race law and
computes payload width from that log-rank. The old path rounded the rank up
first.

## Result

For 10,000 samples per target width:

```text
target_bits=192:
  corrected mean width = 190.6794
  old rounded mean width = 191.6794
  delta = +1.0000 bit/record
```

The same `+1.000000` old-minus-new mean appears across representative spans
`49,64,96,128,192,384,512`.

## Verdict

This correction matters for high-arity frontier measurement, but it is not by
itself a uniform-law breakthrough. The best current paid misses are still
governed by witness/cover entropy, normalized-Q conservation, and tail risk.

Any future refined all-block sweep should use the corrected log-rank width path.
