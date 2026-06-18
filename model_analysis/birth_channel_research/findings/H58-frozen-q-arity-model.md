# H58 - frozen public-Q arity model

Date: 2026-06-17

## Question

H57 used a uniform legal-arity model inside normalized collective `Q`. Can a
better public arity law move the frontier?

The model must be public/frozen:

```text
train q(a | context) on independent uniform-law samples
freeze q
evaluate held-out target layers
```

No target-file counts, selected-cover metadata, or post-eval profile selection
are allowed.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H58-frozen_q_arity_model_rg.py
```

For each interval:

```text
C_i,a ~ Poisson(2^(w-aB))
edge mass = C_i,a * q(a | context) * 2^-w
```

The frozen public code remains:

```text
paid_bits(x) = n - log2(Q_raw(x)) + log2(E_uniform[Q_raw(X)])
```

The arity model is trained with posterior counts over all latent covers on
independent synthetic layers. Contexts tested:

- `global`;
- `bucket`, a remaining-atoms bucket.

## Results

Smoke:

```text
B=4,K=64,D=256,N=96,trials=3,train=4:
  global excess = +0.859728
  bucket excess = +0.632807
```

Small frontier scout:

```text
B=4,K=256,D=1024,N=256,trials=4,train=4:
  global excess = +1.132684
  bucket excess = -0.043395  # finite-sample illusion

B=4,K=384,D=1536,N=384,trials=4,train=4:
  global excess = +0.694816
  bucket excess = +0.260565
```

The apparent negative K256 bucket row was rerun with more held-out samples:

```text
B=4,K=256,D=1024,N=256,bucket,trials=48,train=8:
  avg excess = +0.095833
  mean log2 rho = +0.000135

B=4,K=384,D=1536,N=384,bucket,trials=48,train=8:
  avg excess = +0.229195
  mean log2 rho = +0.000215
```

## Reading

H58 improves the H57 frontier. Compare:

```text
H57 uniform Q, K384: +1.426544 expected excess bits
H58 bucket Q,  K384: +0.229195 expected excess bits
```

That is real movement in the right direction, but it is not a crossing. The
scout's theorem is the governing check:

```text
E_U[-log2 Q(X)] = n + KL(U || Q) >= n
```

Conditioning on a frozen trained public model does not change that:

```text
E_X[-log2 Q_T(X) | T] = n + KL(U || Q_T) >= n
```

So a negative held-out finite sample should be treated as noise or a bug until
it survives exact normalization and enough samples. In H58, the negative
four-sample row vanished at `48` samples.

## Verdict

Frozen public arity modeling is the strongest legal improvement to normalized
`Q` so far, reducing the high-K expected excess to about `+0.23` bits in the
tested row. It still does not solve maintained roughly-all-data compression.

The next honest question is whether a fully priced raw/stopping mixture can
harvest the minority wins without a hidden selector. H59 tests that.
