# H142 - Intrinsic Boundary Optimizer

Date: 2026-06-18

## Question

If payload width is hidden inside the seed witness, what is the best possible
price under:

```text
optimal Kraft seed classes,
residue/modulus seed classes,
terminator/self-sync seed languages,
neutral multiplicity discounts?
```

Runnable artifact:

```text
model_analysis/birth_channel_research/H142-intrinsic_boundary_optimizer.py
```

## Model

H142 uses the H120 pooled width ledger as the live target:

```text
local-width oracle delta = -0.055664 bits/atom/pass
selected rate            =  0.036133 records/atom/pass
measured H(W)            =  5.341012 bits/record
```

The width/boundary channel must therefore cost at most:

```text
break-even H(W) = 0.055664 / 0.036133 = 1.540537 bits/record
```

For intrinsic seed classes, the exact continuous optimizer under Kraft is:

```text
min sum_w p(w) log2(2^w / N_w)
subject to sum_w N_w * 2^-w <= 1

N_w = p(w) * 2^w
loss = H(W)
```

## Results

Main target:

```text
H120_seed118_pooled:
  local delta       = -0.055664 bits/atom/pass
  selected/atom     = 0.036133
  measured H(W)     = 5.341012 bits/record
  break-even H(W)   = 1.540537 bits/record
  total after H(W)  = +0.137322 bits/atom/pass
```

Even an artificial half-entropy profile misses:

```text
hypothetical_half_entropy:
  H(W)              = 2.670506 bits/record
  break-even H(W)   = 1.540537 bits/record
  total             = +0.040829 bits/atom/pass
```

Residue classes:

```text
residue64 loss = 6.000000 bits/record
optimal Kraft for H120 profile = 5.341012 bits/record
```

Terminator/self-sync examples:

```text
0^4 terminator, total len 32: loss = 6.310489 bits
0^5 terminator, total len 64: loss = 7.356225 bits
```

Neutral multiplicity discounts:

```text
lambda=0.1, class=1/2: effective loss = 0.964383 bits
lambda=1.0, class=1/2: effective loss = 0.683949 bits
lambda=4.0, class=1/2: effective loss = 0.183118 bits
lambda=16,  class=1/2: effective loss = 0.000484 bits
```

The discount is only large when expected matches per target are already large;
that is the near-total or bloating regime, not the compressive rare-match
regime.

## Reading

This closes the width-hiding variants more sharply than H120:

```text
optimal intrinsic class loss = H(W)
H120 measured H(W)           = 5.341012
needed to cross              = 1.540537
```

Terminator and self-sync schemes are ordinary prefix languages, so they pay by
reducing seed inventory. Residue classes are just fixed class fractions unless
their probabilities are tuned to the public selected-width law. Neutral
multiplicity can discount class loss, but only after match supply is already
large enough that the record is flat or bloating.

## Verdict

No intrinsic-boundary codec crosses. The next live route is not "hide width in
the seed"; it is to change the selected-width distribution itself, make width
public from a real near-total board invariant, or find a genuine fertility law
that makes high-match multiplicity coexist with net-negative record cost.
