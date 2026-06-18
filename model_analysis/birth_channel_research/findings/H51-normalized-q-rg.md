# H51 - normalized collective-cover reproduction diagnostics

Date: 2026-06-17

## Question

Can the H29/H44 collective-cover distribution be the paid witness that makes
recursive all-block compression cross?

Mechanism:

```text
Q_raw(x) = sum over covers c expanding to x of 2^-L(c)
Q(x) = Q_raw(x) / Z
paid_bits(x) = -log2 Q(x)
```

This is stateless and removes the selected-cover rank. The decoder
arithmetic-decodes the previous layer under public `Q`; it does not need to
know which cover generated the layer.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H51-normalized_q_rg.py
```

H51 reuses H29's exact tiny exhaustive universe. It reports:

- expected normalized code bits;
- excess over raw;
- `avg log2 rho` as a reproduction diagnostic;
- fraction of individual strings below raw;
- best raw-escape mixture weight.

Expected bits are the honest uniform criterion. `avg log2 rho` cannot override
Kraft/counting accounting.

## Results

```text
N=10,B=1,K=4,D=8:
  raw = 10
  avg bits = 10.160503
  excess = 0.160503
  avg log2 rho = 0.019699
  below raw fraction = 0.416016
  escape alpha = 0.00

N=12,B=1,K=4,D=8:
  raw = 12
  avg bits = 12.221970
  excess = 0.221970
  avg log2 rho = 0.023437
  below raw fraction = 0.373779
  escape alpha = 0.00

N=10,B=1,K=4,D=10:
  raw = 10
  avg bits = 10.118241
  excess = 0.118241
  avg log2 rho = 0.014542
  below raw fraction = 0.425781
  escape alpha = 0.00

N=8,B=2,K=4,D=8:
  raw = 16
  avg bits = 17.384658
  excess = 1.384658
  avg log2 rho = 0.112760
  below raw fraction = 0.181320
  escape alpha = 0.00
```

## Reading

Collective-cover `Q` is the cleanest legal way to avoid transmitting the
selected cover. It works for some strings: up to `42.5781%` of strings in these
tiny rows fall below raw under public `Q`.

But once normalized, uniform average is above raw:

```text
E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n
```

The best raw escape mixture chooses `alpha=0` in every row. That means the
public `Q` prior is not useful for roughly-all uniform layers at this scale.

## Verdict

H51 does not produce maintained uniform recursive compression. It does identify
the honest role of collective covers:

- a Telomere-native source prior;
- a minority-win lane;
- a way to remove selected-cover metadata when the source really follows `Q`;
- a measurement of required source lift, equal to the excess bits above raw.

The closest exact row here needs only `0.118241` bits of source/prior lift for
`N=10,B=1,K=4,D=10`, but that is still positive under uniform data. Any
claim that `Q` crosses must either demonstrate a non-uniform source matching
the public prior or locate and pay the hidden normalization/profile/fallback
channel.
