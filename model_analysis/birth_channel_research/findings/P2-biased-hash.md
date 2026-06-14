# P2 — Keystone attack: biased/structured hash coupling birth-pass to the stored seed

Author: keystone-attack lane (P2). Date: 2026-06-13.
Toys (pure counting / exact enumeration, **no hashing, no luck** — BRIEF rules
2/3): `P2-biased-hash_coupling_ledger.py`, `P2-biased-hash_asymmetric_converse.py`.

---

## 0. The mandate

Lane H localized the single keystone of the birth-channel impossibility to the
**uniform hash law** — the one premise whose relaxation correlates birth pass
with something **already on the wire** (the stored seed field). This lane is the
attack on that keystone:

> Couple each record's birth pass to its STORED SEED via a biased/structured
> hash, so reading the seed at decode gives birth pass for free.

Two jobs, in order:
1. **Confirm or refute the lead's partition argument** (the 1:1 conservation
   claim): restrict pass `t` to accept only seeds in class `t` (a `1/T` fraction
   of the compressive seed set); reading the seed's class at decode gives birth
   pass free, but per-pass match supply drops by factor `T`, so over `T` passes
   you net the same matches as one unrestricted pass — the `log2(T)` birth bits
   paid exactly in match-supply currency.
2. **The one live question**: the compressive seed set is **non-uniform**
   (low-index / Lotus-cost bias; `E[win|hit] ≈ 2` bits). Does this non-uniformity
   permit a coupling conveying a birth-bit while losing **strictly less** supply
   than the bit gained (**sub-1x**, beating the 1:1 partition / the ~2× avenue-E
   rate)? Either exhibit a concrete sub-`log2(T)` coupling (push it through the
   counting gate) or **prove none exists** (partition is supply-optimal).

---

## 1. HYPOTHESIS (written before any test — protocol rule 1)

- **H-A (partition baseline = conservation anchor).** Free seed→pass decode
  REQUIRES the per-pass eligible seed sets `S_t` to be **disjoint** (the seed
  must determine the pass with no extra stored bits). Under the uniform hash law
  every eligible seed contributes the SAME `2^−W` hit-prob, so per-pass supply
  ∝ `|S_t|` (a COUNT), and disjointness forces `Σ_t |S_t| ≤ |S_all|`. Total
  supply over `T` passes ≤ one unrestricted pass ⇒ factor-`T` loss = `log2(T)`
  bits, paid in match-supply. I expected this to be **value-independent** (it
  falls out of count additivity; the value distribution never enters).

- **H-B (the live question: count-vs-value CO-LOCATION).** Sub-1x is possible
  ONLY if a class-decodable partition can preferentially KEEP high-value matches
  while SHEDDING low-value ones. Kraft: `#seeds(cost c) ∝ 2^c`, `win = W−c`. I
  expected the COUNT density (`∝2^c`) and VALUE density (`∝2^c·(W−c)`) to be
  dominated by the SAME region (near `c=W`, the numerous cheap-win seeds), with
  rare jackpots negligible in BOTH ⇒ **co-located** ⇒ no sub-1x.

- **H-C (entropy lever kills asymmetric exploit).** Bits conveyed by a partition
  = `H(f)` of the induced birth distribution `≤ log2(T)`, maximal only at
  EQUAL-supply classes. Exploiting non-uniformity needs an asymmetric partition,
  which concentrates births on few passes, dropping `H(f)` FASTER than it saves
  supply ⇒ optimum is the **uniform** partition at exactly 2×/bit.

- **H-D (soft-coupling converse).** A biased PROBABILISTIC (non-disjoint) hash
  is the obvious escape. I expected a rate-distortion converse: `I(seed;pass) ≤`
  supply-entropy-loss at `≥1:1` across the WHOLE family, not just hard
  partitions. Smoothing cannot beat the corner.

---

## 2. RESULTS

### 2.1 Sanity: the planted distribution is faithful

`E[win|hit]` over the planted Kraft cost set → **2.000 bits** (W=10→1.982,
W=13→1.997, W=16→2.000, W=20→2.000), reproducing MATH_MODEL §2 exactly. The
toy's seed economy is the real one.

### 2.2 STEP 1 (H-A) — CONFIRMED: partition baseline is exactly 1:1, value-independent

`P2-biased-hash_coupling_ledger.py` Step 1 (proven-by-math, exact counting):

| W | T | unrestricted supply | partition supply | loss× | loss bits | bits/bit |
|---|---|---|---|---|---|---|
| 13 | 2 | 16380 | 8190 | 2.0 | 1.000 | **1.000** |
| 13 | 8 | 65520 | 8190 | 8.0 | 3.000 | **1.000** |
| 13 | 64 | 524160 | 8190 | 64.0 | 6.000 | **1.000** |
| 16 | 64 | 4194176 | 65534 | 64.0 | 6.000 | **1.000** |

`loss_factor = T` exactly; `supply_loss_bits = log2(T) = bits_conveyed_max`;
**exactly 1.0 supply-bit per conveyed bit (2× per bit).** The value distribution
never enters the supply-count identity. **The lead's partition argument is
confirmed, rigorously.**

### 2.3 STEP 2 (H-B) — CONFIRMED: count and value are CO-LOCATED

Step 2 of the ledger, plus `P2-biased-hash_asymmetric_converse.py`:

- The per-ticket win distribution is **tightly concentrated**: `E[win]≈2.00`,
  `std≈1.41`, `CV = std/mean ≈ 0.70` (stable across W). There is almost no value
  spread to exploit.
- Mean cost under the COUNT measure = 11.00; under the VALUE measure = 10.02 —
  separation **< 1 bit**. Both densities sit on the numerous near-threshold
  (`c≈W`) seeds.
- **Jackpot trap, quantified.** Keeping the top-K highest-win classes:
  `value_kept ≈ supply(count)_kept` at every K (top-1: value 0.0015 vs supply
  0.0002; the value-greedy isolation of a high-win class buys ~0 supply). A
  high-value class has **6–7.5× the average win but ~0 supply share**, so it
  conveys **~0 bits**. You cannot sell value you can't supply.

### 2.4 STEP 3 (H-C) — CONFIRMED: uniform partition is the optimum

Step 3 of the ledger. For partitions with supply fractions `f`:
`supply_loss = log2(T)` always; `conveyed = H(f)`; ratio `= log2(T)/H(f) ≥ 1`,
equality only at uniform.

| W=13, T=8 | H(f) conveyed | supply-loss / conveyed |
|---|---|---|
| uniform | 3.000 | **1.000** (optimum) |
| skew(0.9) | 0.750 | 4.001 |
| value-greedy | 0.259 | 11.564 |

Every asymmetric split is strictly worse than 1.0. Asymmetry concentrates births
(low `H(f)`) but still pays the full `log2(T)` supply collapse.

### 2.5 STEP 4 (H-D) — CLOSED: the soft (biased, non-disjoint) escape, two ways

This step **caught and fixed two successive overclaims** (see §3); the airtight
result is in two cleanly-separated parts.

**4a — the exact 1:1 backbone (proven-by-construction): hard partition into k
equal groups** (`k | T`). Conveyed = supply_loss = `log2(k)` *exactly*; residual
(stored) = `log2(T/k)`; total = `log2(T)`. Verified for every k:

| k (T=8) | conveyed | supply_loss | residual_stored | total | loss/conv |
|---|---|---|---|---|---|
| 1 | 0.000 | 0.000 | 3.000 | **3.000** | — |
| 2 | 1.000 | 1.000 | 2.000 | **3.000** | **1.000** |
| 4 | 2.000 | 2.000 | 1.000 | **3.000** | **1.000** |
| 8 | 3.000 | 3.000 | 0.000 | **3.000** | **1.000** |

This is the clean 1:1 the lead's partition argument refers to: each conveyed
birth-bit costs exactly one bit of match-supply; the residual is stored-bits.

**4b — the soft escape closed by the COUNTING GATE (the converse), not by a
supply formula.** The information identity `I(L;t) + H(t|L) = log2(T)` is exact
(chain rule) for *every* coupling. The supply floor is **forced by pigeonhole**:
if any content-blind coupling conveyed `I` bits of pass-info at supply cost
`< I`, the encoder would obtain more effective fresh-pass supply than a full
unrestricted run for free ⇒ random data net-compresses ⇒ master gate violated.
Hence **`supply_cost ≥ I` for every coupling**, equality **achieved** at the
hard partition (4a); uniqueness of equality is not claimed. For the symmetric
biased channel `P(t|L)=(1−β)/T+β·1[t==L]`:

| β | I conveyed | H(t\|L) | supply_floor (≥I) | stored_resid | total (≥) |
|---|---|---|---|---|---|
| 0.0 | 0.000 | 3.000 | 0.000 | 3.000 | **3.000** |
| 0.5 | 0.783 | 2.217 | 0.783 | 2.217 | **3.000** |
| 0.8 | 1.840 | 1.160 | 1.840 | 1.160 | **3.000** |
| 1.0 | 3.000 | 0.000 | 3.000 | 0.000 | **3.000** |

Total cost `≥ log2(T)` for every coupling. The airtight statement is exactly
the floor: **`supply_cost ≥ I` for every coupling** (gate-forced), and equality
is **achieved** at the hard partition (4a, by construction). Whether some soft
coupling can also *achieve* equality is **not claimed** (minimum-supply-cost
distributions for a given mutual information are generically non-unique). I do
**not** ship a derived interior equality curve — the mechanism does not give one;
the converse floor `≥ I` is what holds, and it is all the no-sub-1x verdict needs.

---

## 3. Two overclaims Step 4 caught (honest record — both strengthen the result)

**Overclaim 1 (inverted supply, spurious sub-1x).** My first Step 4 supply
formula was `usable_free = S_all · 2^I`, giving `supply_loss = log2(T) − I`. This
printed **spurious sub-1x** (loss/conveyed 0.63 at β=0.8, 0.29 at β=0.9) —
exactly the false positive the master gate warns about. The kill was an
**internal consistency check**: at β=1 the biased channel IS the hard partition,
which Step 1 *proved* loses `log2(T)`; the buggy formula gave
`log2(T) − log2(T) = 0`. Two steps disagreeing at the one point they must agree =
proof the formula was wrong. Root cause: I inverted conveyed-vs-residual.
Conveying `I` free bits **partitions** seeds into `2^I` decodable groups, so the
per-pass eligible set **shrinks** (`supply_loss = I`), and the residual `H(t|L)`
is **not** free (it is stored-bits). This is counting-gate leak (a) realized: I
had let the residual leak out as "free," manufacturing a fake sub-1x.

**Overclaim 2 (a posited equality curve masquerading as proven).** The fix to
overclaim 1 gave `supply_loss = I` flat across all β, printed as "1:1 at every
bias, proven-by-math." But that `S_all/2^I` formula was *chosen* to hit the two
endpoints and be monotone — it is **not derived from the eligible-set geometry**.
**The airtight result is not any functional form** — it is the **hard-partition
exact 1:1** (§2.5, 4a, proven-by-construction) plus the **gate-forced converse
`supply_cost ≥ I`** (4b). The converse holds for the cleanest reason:
decodability forces `stored ≥ H(t|L)` (you cannot conjure the residual
ambiguity) and the gate forces `total ≥ log2(T)` (births are uniform-
incompressible), so `supply ≥ log2(T) − H(t|L) = I`, with no dependence on any
functional form. I dropped the fabricated curve.

What I do **not** claim: that equality is *unique* to the hard partition (4a
shows it is *achieved* there; minimum-supply distributions for a given mutual
information are generically non-unique, so a soft coupling might also achieve
it). The no-sub-1x verdict needs only `supply ≥ I`, which stands airtight.

---

## 4. WHY THIS IS NOT LANE E's VACUITY (required distinction)

Lane E refuted the period-P salt schedule as **informationally vacuous**: the
reverse-walk index already gives `t mod P` for free, so the schedule conveys
zero bits. The seed-coupling is **categorically different and NOT vacuous**: the
seed bits are **already stored on the wire**, so seed→pass is genuine
**double-duty reuse** of an existing field. The cost is therefore a **real
supply loss** (the seed set must be carved into decodable classes), not vacuity.
The seed field is the *only* free on-wire correlate of birth pass — which is
exactly why Lane H named it the keystone. This lane shows the double-duty reuse
is real but **conserved**: every bit of pass-info read from the seed is a bit of
match-supply spent carving the seed set.

---

## 5. COUNTING GATE (master gate, answered in writing)

**Q: If this biased-hash coupling were free + content-blind + unbounded, would
arbitrary random data net-compress without bound?** The coupling IS content-blind
(bias on seed VALUE, not on compressed content). So yes — a free unbounded
version would be a pigeonhole violation. **A: it is NOT free.** Each conveyed
birth-bit costs exactly one bit of match-supply (the per-pass eligible seed set
shrinks by `2^I`); the residual `log2(T) − I` bits are stored-bits. There is no
configuration of the bias — symmetric or maximally skewed to exploit the
seed-cost non-uniformity — for which `total_bill < log2(T)`. The two specific
leaks the gate warns about are both closed:
- **(a) explosion-check 2.5-bit bleed:** kept out of the coupling entirely; the
  coupling is 1:1 on its own bits. (The explosion subsidy is an *orthogonal*
  finite source, already counted in Lane E/H.)
- **(b) jackpot value living in rare seeds:** §2.3 — a high-value class has ~0
  supply share and conveys ~0 bits; value and count are co-located, so "value
  preserved" is never real conveyed information.

---

## 6. ANSWER TO THE LIVE QUESTION

**No sub-`log2(T)` coupling exists. The seed-class partition is SUPPLY-OPTIMAL.**

The seed-set non-uniformity (low-index / Lotus-cost bias, `E[win|hit]≈2`) does
**not** permit a coupling that conveys a birth-bit for less than one bit of
match-supply. The reason is precise: the non-uniformity is in the **cost** axis
(`#seeds ∝ 2^c`), but **value and count are co-located** — the per-ticket win is
tightly concentrated (`CV≈0.7`, mean ≈2 bits), so there is no value spread for a
class-decodable partition to sort. Any attempt to isolate high-value (jackpot)
seeds isolates ~0 supply and conveys ~0 bits. The conserved law:

> **conveyed bits → match-supply at ≥ 1:1 (= 1:1, achieved at the hard
> partition); residual (log2T − conveyed) → stored-bits; total ≥ log2(T) for
> every coupling. ~2× supply per birth-bit. No sub-1x at any bias.**

Among *disjoint* partitions the uniform split is the optimum (Step 3: every
asymmetric disjoint split conveys fewer free bits per unit supply lost). For the
full soft/biased family the airtight statement is the gate floor `supply ≥ I`;
no coupling beats it, so none achieves sub-1x.

---

## 7. OUTPUT (BRIEF format)

```
AVENUE: P2 — biased/structured hash coupling birth-pass to the stored seed (the
        keystone relaxation: uniform hash law).
HYPOTHESIS: partition is 1:1 (confirm lead); non-uniformity (cost bias,
        E[win|hit]~2) might allow sub-1x by sorting value from count. Expected:
        co-location ⇒ no sub-1x; partition supply-optimal.
MECHANISM: restrict/bias pass t's accepted seeds to class t. Hard partition:
        disjoint classes, supply ∝ count, Σ|S_t| ≤ |S_all|. Soft: biased channel
        P(t|L)=(1−β)/T+β·1[t==L], decoder reads seed label L, learns I(L;t).
RESULT: sharp-impossibility (conserved) — the seed-class partition is
        supply-optimal; no sub-1x coupling exists.
EVIDENCE: proven-by-math (exact counting + rate-distortion converse), corroborated
        by exact-enumeration toys P2-biased-hash_coupling_ledger.py and
        P2-biased-hash_asymmetric_converse.py (no hashing, no luck; the planted
        Kraft set reproduces E[win|hit]=2.000). Would-the-test-work: pure
        counting, no rare-match dependence — valid by construction.
CURRENCY: match-supply, EXACTLY 1 supply-bit per conveyed birth-bit (2×/bit) for
        the conveyed part; the residual log2(T)−conveyed is stored-bits. Total
        log2(T), conserved at every bias level.
NEXT: the conserved law holds for the seed field as the on-wire correlate. The
        only un-attacked surface is whether a DIFFERENT on-wire field (arity tag,
        literal-marker positions) has a value/count DEcorrelation the seed lacks —
        but those fields carry less information than the seed and inherit the same
        co-location. The wall stands; bundles (arity≥2, q<1 real explosion check)
        remain the only structurally-distinct un-refuted thread.
```

## 8. Evidence classes

- Partition 1:1 conservation, value-independent (Step 1): **proven-by-math**.
- Count/value co-location, `CV≈0.7`, jackpot trap (Step 2 + asymmetric toy):
  **proven-by-math** (exact enumeration of the planted Kraft set).
- Uniform partition optimal among disjoint partitions (Step 3): **proven-by-math**.
- Hard partition into k equal groups is exact 1:1 (Step 4a): **proven-by-
  construction** (conveyed = supply_loss = log2(k) exactly, every k).
- Soft-coupling converse `supply_cost ≥ I`, total `≥ log2(T)` at all bias, with
  equality achieved at the hard partition (Step 4b): **proven-by-math** — the
  floor is forced by the master counting gate (`stored ≥ H(t|L)` from
  decodability + `total ≥ log2(T)` from uniform-incompressibility ⇒ `supply ≥ I`),
  independent of the channel's functional form. Uniqueness of equality is not
  claimed; the no-sub-1x verdict needs only `supply ≥ I`.
- The `2.5`-bit explosion subsidy is deliberately **excluded** (orthogonal,
  finite, content-blind; counted elsewhere) — the coupling is 1:1 on its own bits.
```
