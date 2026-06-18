# Avenue H20 - cover-equivalence arithmetic code

Author: Codex continuation with Locke scout memo. Date: 2026-06-17.
Status: legal collective-witness target; not a uniform all-data escape.

## HYPOTHESIS

Prior Total-Cover witnesses encode one selected cover:

```text
[(arity_1, seed_1), ...]
```

The legal collective alternative is to merge all covers that decode to the same
layer and arithmetic-code the layer under the public distribution induced by
all covers.

## MECHANISM

For a fixed public profile `(N,B,K,D,seed order,salt rule)`, let `c` be a cover
object and:

```text
x = expand(c)
C_x = { c : expand(c) = x }
Q(x) = sum_{c in C_x} 2^-L(c)
```

The encoder transmits `x` under public `Q`, not the rank of one cover inside
`C_x`.

The illegal version is:

```text
send rank(c in C_x)
```

That is circular because the decoder does not know `x` yet. If a checksum or
trial oracle provides `x`, that oracle is the hidden channel.

## DECODE

The decoder knows or is paid the public profile, inverts the arithmetic code
under `Q`, reconstructs `x`, and emits the previous layer. This is stateless
but computationally heavy because exact decoding needs a distribution over
cover-induced outputs.

## ACCOUNTING

Whole-cover equivalence coding can beat local witness streams by harvesting
duplicate descriptions:

```text
L_best_local(x) = min_c L(c)
L_collective(x) = -log2 sum_{c in C_x} 2^-L(c)
saving <= log2 |C_x|
```

This duplicate-cover entropy is real. But under uniform layers and public
full-support `Q`:

```text
E_uniform[-log2 Q(X)] = N*B + KL(U || Q) >= N*B
```

So it cannot become roughly-all-data uniform compression. It can only:

- improve local witness accounting for high-multiplicity layers;
- create a minority-win code;
- become source-shaped compression if real data is concentrated on high-`Q`
  layers.

## SCOUT SANITY

Locke reported a tiny exact sanity run, no repo files edited:

```text
N=12, B=1, K=4, R=16
all 4096 layers covered
cover-equivalence merge saved 8.62 bits on average vs best local cover
merged code averaged 12.26 bits vs 12 raw bits
```

That is the expected shape: duplicate witnesses are harvested, then the uniform
average lands back on the counting floor.

## NEXT KERNEL

Implement an exact `N <= 12` cover-equivalence DP:

```text
for every x in {0,1}^{N*B}:
  count M_x
  compute weighted mass Q(x)
  compute best local cover cost
  compute threshold set sizes A_T = |{x : min_cover_cost(x) <= T}|
```

Compare:

```text
best local witness bits
-log2 Q(x)
log2 A_T
raw N*B with public escape mixture
```

Acceptance bar: show the merged public `Q` recovers the remaining local witness
gap on a fixed profile without using conditional ranks, checksums, per-file
counts, or a target-trained model. Even if it works, it is a finite witness
improvement or source-prior lane, not a uniform all-data breakthrough.
