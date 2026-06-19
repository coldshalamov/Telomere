# H163 - Extended-Arity Item DP

Date: 2026-06-18

## Question

Can the user's higher-arity intuition flip H162 positive if the arity grammar is
extended and paid explicitly?

Runnable artifact:

```text
model_analysis/birth_channel_research/H162-item_stream_cover_dp.py
```

H163 uses the H162 item-stream DP with two labeled hypothetical arity codes:

```text
fixed   = every arity 1..K costs ceil(log2 K) bits
escape5 = current arity 1..5 costs remain; arity >5 costs 3 + ceil(log2(K-5))
```

These are record-only recursive-layer probes. They are not current V1 wire
format claims.

## Results

All rows are strict `seed_only`, `B=8`, `N=32`.

```text
K   D    code     trials  support  gain/item
5   80   exact    500     0.338    -4.057877
8   80   fixed    500     0.286    -4.491696
8   80   escape5  500     0.344    -4.104651
16  80   fixed    500     0.266    -5.235432
16  80   escape5  500     0.306    -4.081291
32  80   fixed    500     0.270    -5.918519
32  80   escape5  500     0.310    -4.127218
5   256  exact    300     0.603    -3.524344
16  256  fixed    300     0.653    -3.881378
16  256  escape5  300     0.663    -3.546954
5   512  exact    120     0.817    -3.476722
16  512  escape5  120     0.833    -3.266563
```

## Reading

Higher arity does not currently provide the expected crossover in this model.

With `fixed`, the arity header thickens every item. The target grammar becomes
heavier before the DP can exploit the extra cover options, so K8/K16/K32 are
worse than exact K5 at D80.

With `escape5`, higher arities are available but expensive. The DP mostly keeps
using short arities, so the result hugs K5. At very deep D, K16 escape improves
support and narrows the miss slightly, but it remains about `3.27` bits/item
negative at D512 and still has less than full support.

This is a useful false-negative guard: it is not a tiny underpowered seed search.
The harness samples the exact analytic edge law for the stated search depth,
then gives the encoder a non-greedy full-cover DP.

## Verdict

Extended arity alone does not solve maintained stateless recursion under the
tested record-only item grammar. The missing piece is not simply "allow K>5" or
"do not choose first found"; H162/H163 already give the cover selector the best
available local choices and pay the arity channel.

The least-dead higher-arity branch is:

```text
escape-style high arity + a custom item witness language
```

The custom witness must reduce the several-bits-per-item H162/H163 miss without
hiding boundary, width, or selector information. A fixed arity code is not the
right direction unless a later source law strongly favors large arities.
