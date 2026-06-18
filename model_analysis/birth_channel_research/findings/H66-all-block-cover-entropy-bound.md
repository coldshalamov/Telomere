# H66 - All-Block Cover Entropy Bound

Date: 2026-06-17

## Question

The user’s all-block intuition is important:

```text
with max arity K, each interior atom belongs to 1+2+...+K possible intervals
choosing the best bundle should improve the next pass
```

H66 prices the part that is easy to miss: after seeing content, choosing a
non-overlapping total cover is itself a selector unless the cover is encoded by
a paid public distribution.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H66-all_block_cover_entropy_bound.py
```

The number of cover shapes for `N` atoms with parts `1..K` is:

```text
C(N,K) = sum_{a=1..K} C(N-a,K)
```

Its entropy rate is:

```text
h_K = log2(lambda_K)
sum_{a=1..K} lambda_K^-a = 1
```

As `K` grows, `h_K -> 1 bit/atom`.

## Representative Results

```text
K=5:   local log2 M = 3.907, cover entropy = 0.975225 bits/atom
K=16:  local log2 M = 7.087, cover entropy = 0.999989 bits/atom
K=128: local log2 M = 13.011, cover entropy = 1.000000 bits/atom
```

So the local interval-option dividend grows like `2 log2 K`, but the legal
cover-shape selector budget is already basically `1 bit/atom` by small K.

Current paid misses are much smaller per atom:

```text
H12: 0.008196 bits/atom
H7:  0.011927 bits/atom
H9:  0.012314 bits/atom
H58: 0.000597 bits/atom
H59: 0.000139 bits/atom
```

That explains why the branch feels close: the hidden cover-choice reservoir is
much larger than the remaining miss. But it cannot be counted as free.

## Verdict

High arity absolutely creates real option pressure and near-boundary rows. The
problem is that the chosen cover is content-selected. There are only three
legal ways to use it:

1. store/encode the selected cover, paying up to `h_K` bits/atom;
2. use a normalized public collective `Q`, which obeys
   `E_U[-log2 Q(X)] = n + KL(U||Q) >= n`;
3. make the cover public/canonical before seeing content, losing the
   best-of-options dividend.

So high arity alone does not solve repeatable stateless compression on roughly
all uniform data. It remains valuable as a constant mover and as a source-shaped
fertility target, but not as a free all-data crossover.
