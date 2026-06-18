# H153 - Cloud Q Conservation

Date: 2026-06-18

## Question

Can the H152 superposition cloud be made honest by converting all alternate
intermediates into a public arithmetic distribution, instead of selecting one
visible final stream or storing a hidden rank?

Runnable artifact:

```text
model_analysis/birth_channel_research/H153-cloud_q_conservation.py
```

## Model

For every bottom word `x`, H153 reuses the H152 paid V1/J3D1 tiny family and
sums the two-pass cloud:

```text
q_raw(x) = sum_c mass({ y : decode(y) = c }) where c decodes to x
```

The first-pass intermediate `c` is still limited by the same slack cap as H152.
The honest public arithmetic distribution is:

```text
Q(x) = q_raw(x) / Z
Z = sum_x q_raw(x)
```

For uniform target words:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

If `Q` has holes, H153 also tests the raw/Q mixture:

```text
Q_alpha = (1-alpha) U + alpha Q
```

## Results

Focused H152 rows:

```text
N4,K4,D7,slack12:
  Z = 2.796e-06
  reachable = 1.000000
  normalized Q cross entropy = 6.126916 bits
  Q excess over raw = +2.126916 bits
  selected explicit CE = 31.187500 bits
  cloud gap = 6.612638 bits
  best raw/Q alpha = 0.000000

N5,K5,D8,slack10:
  Z = 1.298e-05
  normalized Q cross entropy = 7.831486 bits
  Q excess over raw = +2.831486 bits
  cloud gap = 6.029432 bits
  best raw/Q alpha = 0.000000

N6,K5,D7,slack18:
  Z = 1.237e-08
  normalized Q cross entropy = 7.456567 bits
  Q excess over raw = +1.456567 bits
  selected explicit CE = 41.593750 bits
  cloud gap = 7.868868 bits
  best raw/Q alpha = 0.000000
```

## Reading

The H152 cloud is real local option mass. But once the decoder is allowed to
use that whole cloud without a hidden branch, the cloud has become a public
distribution `Q`. On roughly-all uniform data, the `KL(U||Q)` term is positive.
The best honest mixture therefore chooses raw-only.

This closes the obvious "make the superposition cloud arithmetic-coded" escape
for the uniform/stateless branch. It remains useful as:

```text
1. a source-shaped public-Q codec, if a real non-uniform source law is named;
2. a paid rank/arithmetic side channel, if its bits are counted;
3. a diagnostic for finding visible selected-stream fertility.
```

It is not a free recursive compression channel.

## Verdict

The constructive target after H153 is narrower:

```text
do not try to spend the whole unselected cloud;
find a visible final witness grammar where selected-stream lift itself crosses.
```

The cloud can guide search, but the decoder cannot receive the cloud for free.
