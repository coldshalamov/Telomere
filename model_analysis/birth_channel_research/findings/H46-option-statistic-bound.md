# H46 - high-arity option-statistic bound

Date: 2026-06-17

## Question

How much does the user's "many bundle choices per block" idea buy in the best
case?

An interior atom belongs to:

```text
M(K) = 1 + 2 + ... + K = K(K+1)/2
```

candidate intervals. If those were independent first-hit races, the best rank
gets an ideal shift of about:

```text
log2 M(K)
```

## Local option dividend

H46 rows:

```text
K=5:   M=15,    log2 M=3.907
K=16:  M=136,   log2 M=7.087
K=64:  M=2080,  log2 M=11.022
K=128: M=8256,  log2 M=13.011
K=256: M=32896, log2 M=15.006
```

This validates the intuition. Higher arity creates a real order-statistic
dividend before non-overlap and witness coding.

## Current gap as effective choices

The current paid frontier does not need a huge extra factor if it could be
captured for free:

```text
H7 raw first-hit delta: miss=1.357 bits/record -> 2.562 extra choices
H9 fixed slack 0:       miss=1.261 bits/record -> 2.397 extra choices
H12 perfect-credit UB:  miss=0.746 bits/record -> 1.677 extra choices
```

So the live target is deceptively close: a public selected-extreme law that
saves another `~1.3 bits/record` would cross the measured high-arity paid rows.

## Why that is not automatically a loophole

For an independent race with target length `L` and `M` choices:

```text
E[log2 R_min] ~= L - log2(M) - 0.833
```

Representative H46 rows:

```text
B=4, arity=128, K=128:
  L=512, log2M=13.011, E log2 Rmin=498.156

B=8, arity=128, K=128:
  L=1024, log2M=13.011, E log2 Rmin=1010.156
```

The rank dividend is real, but a complete decoder-visible representation still
has to name enough about the selected cover. H7 at `B=4,K=128` shows the
problem in current units:

```text
avg arity = 113.78
raw span bits ~= 455.120
H7 avg rank bits = 453.542
observed rank shift = 1.578 bits/record
remaining paid miss = 1.357 bits/record
```

Much of the ideal local dividend is consumed by non-overlap, arity language,
frontier conditioning, and the width/delta residual.

A scout cross-check states the same bound in selector terms. If `J` is the
winning option and `R_min` is the minimum rank, then up to lattice/tie noise:

```text
H(J) ~= log2 M
H(R_min) ~= L - log2 M + O(1)
H(J, R_min) ~= L + O(1)
```

So the local `log2 M` rank-width discount is canceled if the decoder must also
learn which option won. The only legal ways to keep the discount are to derive
`J` publicly from already-decoded state, to fold it into a normalized public
whole-layer distribution, or to pay it as arity/cover/width/profile metadata.

## Conservation check

A better public selected-extreme law may improve a selected-cover witness. But
if it creates a complete stateless code for uniform `n`-bit layers, the induced
normalized public distribution `Q` obeys:

```text
E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n
```

So a positive uniform all-data average cannot come from better modeling alone.
If a selected-extreme law seems to cross, the bill must be found in one of:

- normalization/support loss;
- arity/width residuals;
- a selector/profile/referee;
- incomplete coverage plus fallback;
- a non-uniform source/fertility prior.

## Verdict

High arity remains the right place to look for finite improvements. The option
dividend is real and quantitatively large. The nearest honest target is:

```text
public selected-extreme residual model
conditioned only on decoder-visible facts
saves >= 1.36 bits/selected record
held-out profile fixed before evaluation
uniform normalized-Q control remains honest
```

If that model crosses on source-shaped data and fails on uniform controls, it
is a valid Telomere-native source/fertility lane. If it claims to cross on
roughly all uniform data, H44 says the hidden bill must still be located.

## Artifact

`model_analysis/birth_channel_research/H46-option_statistic_bound.py`
