# H44 - normalized collective-cover witness

Date: 2026-06-17

## Question

Can a whole-cover public distribution avoid paying for the selected cover?

Mechanism:

```text
Q_raw(x) = sum over covers c expanding to x of 2^-L(c)
Q(x) = Q_raw(x) / Z
Z = sum_x Q_raw(x)
```

The latent cover is never transmitted. The decoder arithmetic-decodes the
previous layer under fixed public `Q`. This is Telomere-native and stateless:
no selected-cover rank, no open/carry channel, no birth-pass channel.

## Why H44 is sharper than H29

H29 measured the duplicate-cover mass and a raw escape mixture. H44 adds the
actual public-code normalization. If `Q` covers all `n`-bit layers:

```text
E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n
```

So a public collective cover can be a source prior, but it cannot average below
raw for uniform roughly-all data.

## Exact tiny rows

H44 reuses H29's exhaustive tiny universe and exact V1/J3D1 costs.

```text
atoms B K D  raw  best-local  raw -log Q_raw  Z           norm bits  excess
10    1 4 8   10  29.068359   22.197609       0.00023794  10.160503  0.160503
12    1 4 8   12  33.455322   26.245017       0.00006007  12.221970  0.221970
10    1 4 10  10  29.068359   21.438129       0.00039118  10.118241  0.118241
8     2 4 8   16  30.581253   27.040001       0.00124009  17.384658  1.384658
```

Duplicate-cover saving versus the best local selected cover is real. The
normalized public code still has positive excess over raw on uniform layers.

## Verdict

This is the cleanest accounting for the "whole cover as one object" idea:

- it is stateless;
- it is order-insensitive;
- it harvests duplicate cover descriptions;
- it can compress data drawn from the public `Q` source;
- it does not compress uniform roughly-all data on average.

This does not mean collective covers are useless. It means their valid role is
source-shaped Telomere or a public fertility prior, not a hidden selected-cover
escape.

## Artifact

`model_analysis/birth_channel_research/H44-normalized_collective_cover.py`
