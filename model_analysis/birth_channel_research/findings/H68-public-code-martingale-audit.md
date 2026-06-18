# H68 - Public Code Martingale Audit

Date: 2026-06-17

## Question

Can repeated public `Q` models or raw/Q mixtures exploit geometric shrink while
still respecting uniform expected-length conservation?

H68 runs a finite exact-domain audit. For a public normalized distribution `Q`
over `n`-bit layers:

```text
L(x) = -log2 Q(x)
W(x) = Q(x) / U(x) = 2^(n-L(x))
E_U[W] = 1
E_U[L] = n + KL(U||Q) >= n
```

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H68-public_code_martingale_audit.py
```

## Representative Results

On an exact `2^8` domain:

```text
spiky public Q:
  excess = +0.336062 bits
  E[W] = 1
  Pr(save >= 1 bit) = 0.0625

lane public Q:
  excess = +0.419518 bits
  E[W] = 1
  Pr(save >= 1 bit) = 0.25

raw/Q mixture alpha=.75:
  excess = +0.047701 bits
  E[W] = 1
  Pr(save >= 1 bit) = 0
```

The hidden best-of profile row reports a gain only because profile identity is
not paid. In this toy run its hidden selector gain is `1.009249` bits. A public
mixture restores the normalized `excess >= 0` check.

## Verdict

This is the finite-domain version of the H57-H59 boundary. Public `Q` can move
which strings win and can create source/fertility targets, but under uniform
data it cannot make expected length negative. Repeated exploitation is a
martingale/optional-stopping trap unless the stop/profile/path selector is
public or paid.
