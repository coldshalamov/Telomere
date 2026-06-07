# Telomere Math Model — Report

**Artifact set** (correction spec §8): `telomere_math_model.py` (primary; pure
formulas, no hashing), `telomere_toy_validator.py` (unit tests for the math —
not a viability artifact), `telomere_depth_sweep.csv` (325 rows, machine
readable), this report. All results below are **"under this model and these
assumptions"**; the assumptions are listed in §8 and each is sweepable.

---

## 1. Equations (the model, in full)

```
arity_cost(a):  1,2 -> 2 b;  3..5 -> 3 b;  a>5 -> swept families ext1/ext2/lb (§7)
J3D1_cost(p) = 3 + max(1, bitlen(p)) + p
record_cost(a,p) = arity_cost(a) + J3D1_cost(p)

pstar(r,a)  = largest p with record_cost(a,p) <= r
M_{a,D}(r)  = 2^min(pstar(r,a), D)          # seeds with payload<=D, record<=r
P_D(min_record <= r | S,a) = 1 - exp( -M_{a,D}(r) / 2^S )

gain tail:   P(gain >= g | S,a,D) = P_D(min_record <= S-g)     carried to g=288
state:       H_t[L]  (entry-length histogram; never collapsed to a mean)
spans:       exact a-fold convolutions of H_t's pmf
pass:        candidates -> renewal-corrected non-overlap selection ->
             replacement -> superposition state -> H_{t+1}
pass 1:      raw spans against the wrapped bar a*(b+3); leftovers wrap ONCE
superposition: retained mass per entry = P(min_record in [L, L+Delta]);
             conversion rate = window rate x 2^-E[extra bits]; modes off/approx/oracle
shuffle:     refresh parameter rho on window counts + separate decodability pricing
depth D:     free symbolic parameter (payload bits); 2^D seeds; swept 8..24000
```

## 2. Validation against the exact toy (b=6, D=19, N=3000)

| check | analytic | exact toy | status |
|---|---|---|---|
| pass-1 size | 140.000% | 140.400% | −0.4 pp (renewal occupancy approx) |
| first recursive sweep | E[acc]=8.7, of which 7.6 is the arity-1 coin-flip mass | 3 accepted | within band once the coin flip is conditioned (below) |
| refreshed passes | E[acc]≈8.6–8.7/pass | 3,3,2,2,0,2,3,6,3 | single Poisson draws around the non-coin-flip mean ≈1.1–2 plus the a1 flip |
| arity-1 lumpiness | E=7.6 **but** only seeds {0,1} qualify; P(zero for the whole run) = (7/8)² = 0.77 | observed 0 | modal outcome — MATCH |
| headroom law 1−e^(−2^−d) | .3935/.0606/.0039 at d=1/4/8 | .40–.44/.062/.0040 | MATCH |
| conditional mean gain | 2.172 | 2.17 | MATCH |

Disclosed honestly: the expectation model reports the *mean* over hash draws;
the tiny universe has small-count corners (the a1 coin flip) where one run sits
far from the mean. That is a property of tiny universes, not of the formulas.

## 3. THE MAP — final % of raw after T=8 passes (the §12 deliverable)

supo=approx(Δ=8), refresh=1.0 (layer-delimited, 16 b/pass metadata charged), ext1.

| b | A | D=16 | D=32 | D=128 | D=1024 | D=24000 |
|---|---|---|---|---|---|---|
| 16 | 5 | 118.622 | 118.193 | 115.071 | 115.071 | 115.071 |
| 16 | 16 | 118.622 | 118.193 | 111.099 | 106.699 | 106.699 |
| 16 | 64 | 118.622 | 118.193 | 111.099 | 101.970 | 102.067 |
| 24 | 5 | 112.448 | 112.447 | 110.061 | 110.059 | 110.059 |
| 24 | 16 | 112.448 | 112.447 | 110.060 | 104.726 | 104.726 |
| 24 | 64 | 112.448 | 112.447 | 110.060 | 101.863 | 101.443 |
| 32 | 5 | 109.403 | 109.358 | 108.238 | 108.129 | 108.129 |
| 32 | 16 | 109.403 | 109.358 | 108.238 | 103.524 | 103.545 |
| 32 | 64 | 109.403 | 109.358 | 108.238 | 101.865 | **101.083** |

Reading (conditional language): final size **decreases in D until each arity
tier saturates** (an arity-a bundle needs D ≳ a·b − framing, i.e. ~2^(a·b)
hashes per span), **decreases in A** (framing amortized over more blocks), and
**decreases in b** (marker diluted). Minimum swept cell: 101.083% at
(b=32, A=64, D=24000, T=8).

## 4. Net size vs depth (b=24, A=5) — "as D grows from feasible to absurd"

112.537 (D=8) → 112.448 (16) → 112.303 (48) → 111.028 (96) → 110.061 (128) →
110.059 (1024) → **110.059 (24000)**. A staircase: each step is one arity tier
saturating; **beyond D=128 the curve is constant to D=24000** under this model.
Compute column: D is log2(hashes per span); the last step costs ~2^120 hashes
per span to reach.

## 5. Gain distribution (carried in full, never a mean)

Accepted-gain percentiles at b=24, A=5, D=1024 (CSV rows): p50=2, p90=4, p99=7,
max=20 bits — the tail halves per added bit, exactly the validated headroom
law. The 288-bit tail is propagated through every pass; nothing is collapsed
to 2.17.

## 6. Superposition (state, swept; not a search shortcut)

At b=24, A=5, D=1024: retained ≈ 108 candidates/pass at Δ=8 (computed mass),
conversions ≈ 5.1×10⁻⁴/pass; at A=64: retained 1.9, conversions 2.0×10⁻⁷.
Final % across Δ ∈ {0,1,2,4,8,16,32,64}: identical to 4 decimals (110.0587).
**Upper bound (oracle: alternates carry zero extra bits): also 110.0587.**
Statement: under this model, retained-state routing changes the outcome by less
than 10⁻³ pp at every swept (Δ, D); the oracle bound shows this is not an
artifact of the approximation.

## 7. Shuffle / refresh — priced, not dismissed

| rule | decodable | metadata | refresh |
|---|---|---|---|
| none | yes | 0 | 0 after first sweep |
| pairswap / rotate / affine / PRP, in-place | **no (order recovery)** | — | 50–100% |
| **layer-delimited (any rule)** | **yes** | ~16 b/pass | rule's rate |
| between fully-expanded layers | yes | layer descriptors | 100% |
| virtual (discovery only) | yes | 0 | 0 shippable |

The toy's decode failure was a *format finding about in-place shuffles*; layer
delimitation repairs it at ~16 b/pass. At N=12000, b=24 the refreshed trickle
(≈1–2 b/pass here) is below the metadata cost, so refresh=0 edges out 1.0
(110.037 vs 110.059). The trickle scales with n while metadata is fixed, so the
sign of (trickle − metadata) is size-dependent — conditional, and now priced.

Wide-arity codec families at (b=24, A=64, D=24000): ext1 101.443%,
ext2 101.378%, lb (non-prefix-free lower bound) 101.378% — labeled assumptions,
spread ≈ 0.07 pp.

## 8. Sensitivity (what moves these tables)

1. uniform match law P(hit)=2^−S per seed (everything descends from it);
2. later-pass spans obey the same law (no expander-correlated structure);
3. wide-arity codec family (swept; 0.07 pp at A=64);
4. first-match pricing with full geometric tail (carried to 288 b);
5. renewal-approximation selection (validator: −0.4 pp at pass 1, b=6).

## 9. §12 acceptance answers

For (b, A, D, T) the model returns E[final_bits/raw] via `multi_pass()`; per-pass
gain distributions are in the CSV. As D grows feasible→absurd the result steps
down at each arity-saturation depth and is then **constant in D** (§4). Within
the swept region (b ≤ 32, A ≤ 64, D ≤ 24000, T ≤ 8, Δ ≤ 64) the minimum
predicted final size is **101.083% of raw**; the break-even surface
(final = 100%) is **not intersected inside the swept region**. Along the arity
axis the pass-1 floor follows ≈ 100·(1 + framing(A)/(A·b)), which decreases
toward 100 as A grows with D ≥ A·b − framing; the model prices that depth at
~2^(A·b) hashes per span. These statements are conditional on §8; change an
assumption and the tables recompute.
