# H165 - Fertility Option DP

Date: 2026-06-18

## Question

Does same-interval witness multiplicity actually provide enough neutral
choice to make fertility-selected superposition cross the H164 threshold?

Runnable artifact:

```text
model_analysis/birth_channel_research/H165-fertility_option_dp.py
```

## Model

For each target interval, H165 samples the first matching source-cost bucket
under the uniform hash law. It then credits an optimistic same-cost fertility
option value:

```text
option_bits = E[log2(number of matching witnesses in winning bucket) | bucket nonempty]
```

This is not claimed as real future compression. It is an upper bound on how
much value the encoder could extract by choosing the most fertile witness among
same-visible-cost alternatives without storing a selector.

Two DP objectives are reported:

```text
raw   = current H162-style min raw cost
value = optimistic min(raw cost - option_bits)
```

## Results

Strict `seed_only`, `B=8`, `N=32`:

```text
K   D    code     obj    support  gain/item  opt/item  net/item  miss/rec  opt/rec  M_eq
5   80   exact    raw    0.4417   -3.9346    0.1086    -3.8260   8.2180    0.2268   1.170
5   80   exact    value  0.3167   -4.1760    0.1242    -4.0518   8.3795    0.2493   1.189
5   256  exact    raw    0.6917   -3.5335    0.0811    -3.4524   9.7254    0.2232   1.167
5   256  exact    value  0.6000   -3.3993    0.0772    -3.3221   9.5512    0.2169   1.162
5   512  exact    raw    0.8625   -3.3628    0.0675    -3.2953   10.5920   0.2126   1.159
5   512  exact    value  0.8625   -3.4361    0.0750    -3.3612   10.7465   0.2345   1.177
16  512  escape5  raw    0.8375   -3.1852    0.0589    -3.1263   11.0681   0.2045   1.152
16  512  escape5  value  0.8375   -3.2080    0.0630    -3.1450   11.0757   0.2175   1.163
```

## Reading

The H164 hurdle was:

```text
smallest strict miss = 8.361777 bits/selected-record
equivalent best-of-M choices M ~= 329
```

H165 finds:

```text
same-cost option value ~= 0.20 to 0.25 bits/selected-record
equivalent best-of-M choices M ~= 1.15 to 1.19
```

This happens because the first nonempty source-cost bucket is usually just
barely nonempty. There may be many matches at larger widths, but taking them
increases the visible seed cost; the value-aware DP cannot turn that into a
crossing because the extra multiplicity is paid by thicker witnesses.

## Verdict

Same-cost neutral witness multiplicity is far too small to pay the H162/H163
miss. Fertility-selected superposition remains possible only if it finds a
public recurrent fertility law that changes the future-value distribution, not
merely by choosing among ordinary same-cost seed alternatives.

The next fair kernel is `visible_selected`: actually emit the selected witness
stream, run the paid next-pass cover model over that stream, and compare against
best-of-same-budget random witnesses. H165 says the neutral-multiplicity upper
bound alone will not be enough.
