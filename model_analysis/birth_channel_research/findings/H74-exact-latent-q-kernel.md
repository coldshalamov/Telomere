# H74 - Exact Latent Whole-Cover Q Kernel

Date: 2026-06-17

## Question

What if the selected Total-Cover parse is never transmitted?

Instead define a frozen public whole-layer distribution:

```text
Q_raw(x) = sum over all covers/descriptions that generate x of 2^-L(desc)
Q(x)     = Q_raw(x) / sum_y Q_raw(y)
```

The decoder arithmetic-decodes the previous layer under public `Q`. This is
the cleanest version of "whole-cover witness coding" because duplicate covers
and overlap advantages are real, but selected-cover identity is not a side
channel.

Runnable artifact:

```text
model_analysis/birth_channel_research/H74-exact_latent_q_kernel.py
```

## Exact Uniform Tests

H74 enumerates every string in a tiny domain, builds a deterministic public
random seed/cover distribution, normalizes it, and reports:

- `E_U[-log2 Q(X)] - n`;
- fraction of strings favored by `Q`;
- duplicate-cover gain;
- best fully priced raw/`Q` mixture alpha.

Representative runs:

```text
B=2,N=8,K=4,D=8, domain=65536
  Q excess over raw:        +1.673076 bits
  fraction with Q(x)>U(x):   0.168701
  avg duplicate-cover gain:  3.421352 bits
  best raw/Q alpha:          0.00

B=1,N=12,K=6,D=8, domain=4096
  Q excess over raw:        +1.814795 bits
  fraction with Q(x)>U(x):   0.255127
  avg duplicate-cover gain:  2.644706 bits
  best raw/Q alpha:          0.00

B=4,N=4,K=4,D=8, domain=65536
  Q excess over raw:        +6.803412 bits
  fraction with Q(x)>U(x):   0.036591
  avg duplicate-cover gain:  2.799114 bits
  best raw/Q alpha:          0.00
```

## Reading

The attractive part is real:

```text
duplicate covers create favored strings
Q can strongly reduce selected-cover metadata for those strings
```

But under uniform inputs:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

So the same public `Q` necessarily hurts other strings enough that the uniform
average stays above raw. The honest raw/`Q` mixture chooses `alpha=0` in the
tested exact domains.

## Verdict

Latent whole-cover `Q` remains the cleanest source-shaped witness language, but
it is not a structure-free uniform escape.

Constructive next target:

```text
predeclare a public high-Q fertility class
+ measure source enrichment c*
+ measure recursive retention p_FF / background inflow p_OF
+ require uniform negative controls
```

That is the same biological/source-shaped branch identified by H62/H63/H70,
now tested against the strongest collective witness language.
