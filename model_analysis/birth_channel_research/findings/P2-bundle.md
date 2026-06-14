# P2 — Bundle survivor-count lane (the only un-refuted thread, tested at scale)

**Toy:** `model_analysis/birth_channel_research/P2-bundle_survivor.py`
(real SHA-256; exact open/carry survivor count; the J3D1 Lotus variable-length
grammar from `P2-explosion-budget_exact.py` so the length pin actually bites).

```
AVENUE:    Bundles (arity-2) — extend B-ambiguity_survivor_count (singles, S=T^R)
           with a REAL explosion check (q_bundle < 1, the one thing bundles have).
HYPOTHESIS: q_bundle only LOWERS THE BASE of an exponential survivor count
           (mechanism a); the affine-stride geometric filter is content-blind and
           does NOT pin the epoch to O(1) (refuting mechanism b). Expected the
           singles impossibility to reappear with a larger — still finite — free
           knee, because bundles carry a length pin singles lack.
RESULT:    confirms-impossibility (mechanism a). Bundles are the singles
           impossibility with a BIGGER intercept K, not a new free channel.
EVIDENCE:  proven-by-construction (survivor count, real SHA) + proven-by-math
           (multiplicative law) + measured (q_bundle exact vs Monte-Carlo;
           base law vs randomized-seed ensemble).
CURRENCY:  structure (free ~E=9.36 bits) buys a FINITE intercept (knee K=2^E≈657
           passes); past K the slope is paid in STORED-BITS (checksum width).
NEXT:      arity-3+ raises E further (bigger K) but the slope log2(T)-E is
           unchanged — the wall is the same, just further out.
```

## The load-bearing distinction, settled: (a) not (b)

The task framed the decisive question:

- **(a)** the explosion check merely **lowers the base** of `S = base^R`
  (`base = 1 + (G−1)·q_bundle`, still > 1) → survivors **exponential** in R →
  fails at scale by Lane-E multiplicativity; OR
- **(b)** a **hard arithmetic constraint** (the affine-stride fingerprint) pins
  each bundle's epoch to **O(1)** candidates → survivors **polynomial** in R →
  a real free channel.

**Result: (a), measured.** The content-blind geometric filter admits `G ≈ T`
distinct epoch candidates for early bundles — **no** arithmetic pin. The only
thing that thins them is the probabilistic explosion check `q_bundle`, and it
only multiplies the base down from `T` (singles' value) toward
`1 + (T−1)·q_bundle`. The base stays **strictly > 1**, so `S = base^R` is
exponential. `(b)` would require `base → 1`, i.e. `(G−1)·q_bundle → 0`, which a
constant-grammar q cannot deliver while `G ≈ T`.

I deliberately did **not** fit a curve over small R (which fakes polynomial,
since `base^R ≈ 1 + R(base−1)` near base=1). I exhibited the functional form
directly: `ln(mean S_epoch)` is **linear in R** with slope `ln(base)` — the
signature of an exponential.

## Two ambiguities, kept separate (the task is about EPOCH)

Re-expansion `H(seed | p{k})` depends on `(seed, k)` **only**, not on the
placement `(q, F)`. So all placements of a given epoch share **one** parse
event: an epoch survives the explosion check iff that single event passes.
Therefore the toy reports two distinct counts:

- **`S_epoch`** = distinct surviving birth **epochs k** — the birth-epoch
  channel, the quantity the whole problem is about.
- **`S_branch`** = surviving decode **branches `(k,q,F)`** — what the checksum
  referee must actually resolve. `S_branch ≥ S_epoch` because the same epoch can
  have multiple geometric placements (e.g. T=1000, R=4: `S_epoch ≈ 48`,
  `S_branch ≈ 165`). The checksum bill is therefore *at least* the epoch
  ambiguity, often larger.

Both are exponential in R; the verdict is identical for either.

## The key numbers (real grammar, B=8, arity-2)

**q_bundle (the explosion-check survival prob for a wrong salt):**
- EXACT: `avalid(2, 16) / 2^16 = 100 / 65536 = 0.001526` → `E = 9.356 bits`.
- Monte Carlo (200k uniform 16-bit digests): `0.001675` → agreement 9.8% (OK;
  cross-check confirms the recursive-descent parser matches the combinatorial
  count — no hidden parser bug faking a small q).
- `q_bundle < 1` **strictly** — the qualitative break from singles, where
  opening always yields one valid item so `q = 1`, `S = T^R`, `base = T`.

**The free-reach knee:** `K = 1/q_bundle = 2^E = 2^9.36 ≈ 655 passes.`
This *reconciles the refuted "5.66 free passes" folklore*: 5.66 = 2^2.5 was the
E=2.5 (singles length-pin) special case; the **law is `K = 2^E`**, and arity-2's
bigger length pin (E=9.36) just buys a bigger K.

**Per-bundle base law (R=1): `base = 1 + (G−1)·q_bundle`** — analytic (zero
variance) confirmed by a randomized-seed ensemble (300 trials, a *different*
valid bundle seed each trial so wrong-epoch survival genuinely varies):

| T    | G (epochs) | (T−1)·q | base analytic | mean S_epoch (300 trials) |
|-----:|-----------:|--------:|--------------:|--------------------------:|
| 20   | 20   | 0.029 | 1.029 | 1.040 |
| 100  | 100  | 0.151 | 1.151 | 1.100 |
| 300  | 300  | 0.456 | 1.456 | 1.507 |
| 655  | 655  | 0.998 | 1.998 | 1.943 |
| 1000 | 1000 | 1.524 | 2.524 | 2.427 |
| 2000 | 2000 | 3.050 | 4.050 | 4.140 |
| 4000 | 4000 | 6.102 | 7.102 | 6.903 |

**Compounding (S_epoch = base^R, exponential in R)** — randomized ensemble:

| T    | base | S_epoch R=1 | R=2 | R=3 | R=4 |  | S_branch R=4 |
|-----:|-----:|------------:|----:|----:|----:|--|-------------:|
| 1000 | 2.52 | 2.7  | 3.6  | 16.7  | 47.6  || 165 |
| 2000 | 4.05 | 3.8  | 17.6 | 50.0  | 130.3 || 546 |
| 4000 | 7.10 | 6.8  | 49.9 | 209.6 | 796.7 || 1159 |

`ln(mean S_epoch)` tracks `R·ln(base)` linearly across every T → `S = base^R`,
**exponential in R**.

**Correctness guard:** every run reports `true_ok = True` — the true epoch is
always among the survivors. This asserts the geometric-candidate generation is a
faithful copy of `v1_roundtrip_proof.py` lines 173–183 (a geometry bug would
drop the true epoch and the flag would flip).

## Why the law is multiplicative (the keystone)

Each planted bundle has a **distinct seed and per-pass salt**, so its
wrong-epoch re-expansions are **independent uniform digests**. Whether each
distinct epoch survives is therefore an **independent** event. Independent
per-bundle survivor counts **multiply**:

```
E[S_epoch(R)] = ∏_i (1 + (G_i − 1)·q_bundle) ≈ base^R      (G_i ≈ T for early births)
```

The single assumption it all hinges on is the **uniform hash law** (it makes
wrong-salt re-expansions independent uniform digests, hence `q_bundle` constant
and the count multiplicative) — the same keystone the singles lanes identified.

**Conservative isolation:** the count isolates the bundle channel (no
cross-bundle slot-filling). In the full DFS, cross-filling only *adds* pruning
(lowers the base) — it can never bend an exponential into a polynomial — so this
is the conservative way to exhibit the multiplicative law.

## Counting gate (mandatory; the BRIEF master gate)

> If this channel were free AND content-blind AND **unbounded**, would random
> data net-compress without bound?

**Yes it would — so the channel is NOT unbounded, and the toy shows exactly
where it stops.** The free structural budget `E = −log2(q_bundle) = 9.36 bits`
buys a **finite** intercept: the knee `K = 2^E ≈ 657` passes.

- **Below K** the epoch is **~free in expectation** (`base ≈ 1`). This is an
  expectation statement, not a guarantee: `S_epoch = 1 + Binomial(T−1, q)`
  distinct epochs, mean `1 + (T−1)q`, which is *usually* 1 below K but
  occasionally forks (a wrong epoch parses). Those occasional forks are the
  variance of a probabilistic filter, **not** a leak — they are exactly the
  `(T−1)q < 1` expected wrong-survivors.
- **Past K** the per-bundle residual is

  ```
  log2(base) = log2(1 + (T−1)·q_bundle)  ──→  log2(T) − E   as T ≫ K
  ```

  which **grows without bound in T**. The bill reappears, paid in
  **stored-bits**: to deterministically select the true reading out of
  `S = base^R` survivors the header checksum must widen to
  `log2(S) = R·log2(base) ≈ R·(log2 T − E)` bits.

```
   T          base    log2(base)   log2(T)−E
   300        1.456    0.542        0.000     (below knee: ~free)
   655 (=K)   1.998    0.999        0.000     (knee: ~1 bit/bundle)
   1000       2.524    1.336        0.610
   4000       7.102    2.828        2.610
   1,000,000  1526.9  10.576       10.575     (slope == log2 T − E)
```

The free budget shifts the **intercept** (a bigger K than singles' 5.66), it
**never changes the slope** (exactly `P2-explosion-budget_exact.py` §6: "the
free budget shifts the intercept, never the slope"). No pigeonhole violation:
random data does not net-compress because the per-record birth bill
`log2(T) − E` is unavoidable past K.

## Currency

`structure (free ~E = 9.36 bits)` for the finite intercept; then `stored-bits`
for the slope. The explosion check is real and load-bearing — it gives bundles a
genuinely larger free reach than singles — but it is a **constant** discount on
a bill that still scales as `N·(log2 T − E)`.

## Verdict

**confirms-impossibility, mechanism (a).** The only un-refuted thread is now
closed at scale: arity-2 bundles are **not** a free unbounded birth-epoch
channel. They are the singles impossibility with a **larger but still finite**
free knee `K = 2^E`. Relaxing the uniform hash law (a non-uniform hash that
correlates a bundle's birth pass with its stored seed field) is the only place a
real channel could still hide; under the uniform law, there is none.
```
AVENUE:    Bundles (arity-2 survivor count at scale)
HYPOTHESIS: q_bundle lowers the base only (a); geometry does not pin (not b).
MECHANISM: real explosion check on the J3D1 Lotus grammar; both filters composed
           (affine-stride geometry G≈T content-blind, then length-pinned parse
           q_bundle); exact open/carry survivor count, real SHA, T up to 4000,
           R up to 4; epoch- vs branch-ambiguity reported separately.
RESULT:    sharp-impossibility / partial(reach K=2^E≈657 for arity-2)
EVIDENCE:  proven-by-construction + proven-by-math + measured —
           P2-bundle_survivor.py
CURRENCY:  structure (free E=9.36 bits) intercept; stored-bits slope (log2 T − E)
NEXT:      arity-k raises E~-log2(avalid(k,kB)/2^kB) and thus K, never the slope.
```
