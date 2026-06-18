# H57 - normalized collective-Q percolation RG

Date: 2026-06-17

## Question

Can a normalized collective-cover distribution remove the selected-cover /
witness-boundary bill at the H52/H53 high-arity frontier?

Instead of choosing one cover and transmitting its selected witness fields,
define:

```text
Q_raw(x) = sum over all matching covers c -> x of 2^-L(c)
Q(x)     = Q_raw(x) / Z
paid_bits(x) = -log2 Q(x)
```

This is stateless if `Q` is public and normalized. The decoder arithmetic-
decodes the previous layer under `Q`; the selected cover is latent.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H57-normalized_q_percolation_rg.py
```

For each interval `(i,a)`:

```text
w(a) = min(D, aB)
C_i,a ~ Poisson(2^(w-aB))
edge mass = C_i,a * 2^-(w + arity_cost(remaining,a))
```

The public normalization uses expected edge mass:

```text
E[C_i,a] * 2^-(w + arity_cost) = 2^(-aB - arity_cost)
```

For raw size `n=N*B`:

```text
paid_bits(x) = n - log2(Q_raw(x)) + log2(E_uniform[Q_raw(X)])
```

The default row uses a uniform legal-arity model. That is not necessarily the
best possible public arity model, but it is honest and selector-free.

## Results

Smoke:

```text
B=4,K=32,D=128,N=64,trials=3:
  avg paid bits = 256.737998
  avg excess = +0.737998
  mean log2 rho = +0.004152
```

H52/H53 frontier scout:

```text
B=4,K=128,D=512,N=160,trials=8:
  avg excess = +1.737096
  mean log2 rho = +0.000533

B=4,K=192,D=768,N=192,trials=8:
  avg excess = +2.386885
  mean log2 rho = +0.001191

B=4,K=256,D=1024,N=256,trials=24:
  avg excess = +1.470987
  mean log2 rho = +0.000427

B=4,K=384,D=1536,N=384,trials=64:
  avg excess = +1.426544
  mean log2 rho = +0.000166

B=4,K=512,D=2048,N=512,trials=24:
  avg excess = +1.280098
  mean log2 rho = +0.000197
```

Coverage was `1.000` in all listed rows.

## Reading

This is the closest high-K uniform log-rho surface so far, but it still does
not cross. The important split is:

```text
mean log2 rho       = repeated-pass/geometric diagnostic
avg paid bits - raw = uniform expected-length diagnostic
```

For a roughly-all-data lossless code, expected paid bits under the uniform
source must not be above raw. H57 remains above raw. A negative geometric
diagnostic by itself would be suspect unless expected length also crosses.

H57 therefore confirms the second scout's recommendation as the right axis:
collective `Q` attacks the actual selected-cover/witness-boundary bill. But in
the tested public uniform-arity form, normalization returns the savings.

## Accounting

Stored/paid:

- public arity model;
- normalized arithmetic code under `Q`;
- raw length/padding as usual.

Derived:

- selected cover is latent;
- witness multiplicity contributes to `Q_raw`;
- no per-cover rank, selector, or birth/open channel.

Hidden if omitted:

- normalization constant `Z`;
- model-selection cost if the arity model is trained on the target file;
- fallback/escape bits if zero-mass or high-cost layers are not covered.

## Verdict

Normalized collective cover is the best current witness-boundary axis, but the
tested uniform public model still expands:

```text
best listed H57: +0.000166 mean log2 rho, +1.426544 expected excess bits
```

The next Q work should be either:

- a frozen public arity model trained on independent uniform-law samples, with
  model-selection cost fixed before evaluation; or
- a proof that any normalized public `Q` over uniform data must keep
  `E[-log2 Q(X)] >= n`, leaving only source-shaped/fertility priors.

Do not promote H57 as a crossing. It is a near-boundary measurement and a
useful target for any future mechanism claiming to remove the last
`~0.0001-0.001` log-rho gap.
