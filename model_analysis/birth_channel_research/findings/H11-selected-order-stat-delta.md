# Avenue H11 - selected-order-statistic delta law

Author: Codex continuation with read-only subagent critique. Date:
2026-06-17.
Status: final low-dimensional H7/H10 follow-up.

## HYPOTHESIS

H7's public raw first-hit delta law remained the closest stable paid row:

```text
B=4, K=128, D=512
raw first-hit delta law -> about -0.012 to -0.015 bits/input atom
```

The remaining delta/slack bill might be overcharged if the selected cover's
width is priced as an ordinary legal first hit. A public model could instead
price the selected width as an order statistic: the best of several effective
choices visible through the Total-Cover DP's overlap pressure.

## MECHANISM

Runnable kernel:

- `../H11-total_cover_order_stat_delta.py`

For a raw first-hit width random variable `W`, H11 tests:

```text
P_sel(W=w | min(W_1..W_m) <= D, context)
  = (S_raw(w-1)^m - S_raw(w)^m) / (1 - S_raw(D)^m)
```

where:

- `S_raw(w) = P_raw(W > w)`;
- `m = m_eff(context)` is a frozen public function;
- context can include decoder-visible quantities such as remaining atoms and
  arity;
- the arity model is trained only on independent uniform-law samples and must
  be frozen as a public profile.

The conditioning is important. The law is not allowed to assume that every
latent draw was already encodable inside `D`; it may only condition on the
selected minimum fitting the decoder's frontier.

## RESULT

`refuted-as-crossover`

Corrected constant-law run:

```text
command:
python model_analysis\birth_channel_research\H11-total_cover_order_stat_delta.py ^
  --train-trials 24 --eval-trials 16 --iterations 3 ^
  --constant-m 1 2 4 8 16
```

| law | train gain/atom | eval gain/atom | missing bits/record | result |
| --- | ---: | ---: | ---: | --- |
| m1 | -0.015072 | -0.019154 | 2.012 | worse than H7 |
| m2 | -0.013983 | -0.019864 | 1.769 | worse than H7 |
| m4 | -0.005738 | -0.017817 | 1.258 | still negative |
| m8 | +0.003257 | -0.014353 | 0.919 | best held-out diagnostic, not train-selected |
| m16 | +0.017711 | -0.017810 | 1.027 | train-selected, negative held-out |

The honest train-selected public-profile row is `m16`, with held-out
`-0.017810` bits/input atom. The best held-out diagnostic row is `m8`, with
`-0.014353` bits/input atom. Selecting `m8` because it won held-out would be
model-selection leakage, so it was tested once more as a frozen candidate.

Independent frozen `m8` check:

```text
command:
python model_analysis\birth_channel_research\H11-total_cover_order_stat_delta.py ^
  --train-trials 24 --eval-trials 16 --iterations 3 ^
  --constant-m 8 --seed 9001

result:
m8 -> -0.017956 bits/input atom, missing 1.149 bits/record
```

Same-seed baselines:

```text
H7 raw first-hit delta -> -0.017439 bits/input atom
H9 fixed slack 0      -> -0.013061 bits/input atom
```

So H11 does not beat the current paid witness frontier. It occasionally makes a
diagnostic row look close, but the advantage does not survive the public-profile
selection discipline or an independent frozen-law seed.

## ACCOUNTING TRAPS CLOSED

- `m_eff` is free only as a frozen public profile. Choosing it per file or after
  seeing held-out rows is metadata.
- The arity model is free only if frozen from independent uniform-law training.
  If fit from the target file, its counts/profile must be transmitted.
- The frontier condition is paid by `P(min <= D)`. The kernel does not assume
  all hidden alternatives were frontier-legal.
- H11 is a surrogate for DP selection pressure, not the exact DP generative law.
  A positive result would require stability across seeds/trials, not just one
  diagnostic held-out row.

## NEXT

The low-dimensional selected-delta branch is now mostly exhausted. The next
non-redundant targets are:

1. **Recursive-fertility cover objective**: keep the same stateless
   `[arity][seed witness]` stream, but optimize a cover for current gain plus a
   public estimate of next-layer fertility. A two-pass DP kernel should test
   whether next-pass match supply can improve without adding a hidden channel.
2. **Joint enumerative selected-cover code**: price the whole selected cover as
   one canonical object instead of independent record fields. The falsifier is
   whether the selected-cover entropy rate can save at least the remaining
   roughly `1.2` to `1.4` bits/record without per-file tables.

