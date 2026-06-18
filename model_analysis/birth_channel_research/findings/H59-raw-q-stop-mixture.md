# H59 - raw/Q stop mixture

Date: 2026-06-17

## Question

Can a fully priced raw escape / stop mixture harvest the minority wins from
normalized collective `Q`?

Forbidden shortcut:

```text
emit min(raw, Q)
```

That is a hidden selector unless the selection bit is paid. H59 uses a public
normalized mixture instead:

```text
M(x) = (1-alpha) * U_n(x) + alpha/T * sum_t Q_t(x)
```

The raw escape and stop/pass choice are paid by the mixture weights. Alpha is
trained on independent uniform-law samples, then frozen for held-out eval.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H59-raw_q_stop_mixture.py
```

For sampled `Q` lengths:

```text
L_t(x) = -log2 Q_t(x)
L_M(x) = n - log2((1-alpha) + alpha/T * sum_t 2^(n-L_t(x)))
```

## Results

Smoke:

```text
B=4,K=128,D=512,N=160,T=1:
  alpha = 0
  eval excess = 0

B=4,K=128,D=512,N=160,T=4:
  alpha = 0
  eval excess = 0
```

Frontier scout:

```text
B=4,K=384,D=1536,N=384,T=1:
  train alpha = 0.2
  train excess = -0.007130
  eval excess = +0.053411
  eval mean log2 rho = +0.000050

B=4,K=384,D=1536,N=384,T=4:
  train alpha = 0
  eval excess = 0
```

## Reading

This closes the obvious "use Q only when it helps" escape in its public-mixture
form. A small train sample can choose a nonzero `alpha`, but held-out expected
bits remain positive. With four stop lanes, the best public mixture chose raw
only.

The theorem behind the result:

```text
M_alpha = (1-alpha)U + alpha Q
E_U[-log2 M_alpha(X)] = n + KL(U || M_alpha) >= n
```

The same holds for a finite public mixture of stop/pass/lane distributions.

## Accounting

Paid:

- raw escape probability `(1-alpha)`;
- stop/lane probability `alpha/T`;
- normalized `Q_t` for each public lane.

Derived:

- no explicit stop selector;
- no kept-if-shrinks bit;
- no target-trained alpha.

Hidden if omitted:

- per-file choice of raw vs Q;
- post-eval alpha selection;
- checksum/referee bits if trial decode is used to pick the lane;
- bits-back tape deficit if a latent reservoir is used to choose winners.

## Verdict

H59 does not produce a maintained all-data crossing. It confirms that raw
escape and bounded stopping can be made stateless and fully priced, but the
best public mixture either:

- chooses raw only; or
- overfits train and remains positive on held-out expected bits.

This makes H58's `+0.229195` expected-excess frontier a sharper target, not a
solved path.
