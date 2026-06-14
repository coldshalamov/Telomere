# Avenue B — Trial-decode ambiguity is bounded ⇒ no channel needed?

**Lane.** Prove or refute a bound on the number of *self-consistent decodings*
(surviving readings) of a Telomere wire as a function of (N records, P passes).
If the count is polynomial / constant-per-record, deterministic decode is real
(Result-Ledger Q1) and the birth channel costs nothing in stored bits. If it is
exponential, decode is a search whose size grows with the file — which the
requirements card (THE_OPEN_QUESTION §"REQUIREMENTS CARD" item 3) forbids, and
the bill reappears in the **compute** currency.

This file is the empirical face of GOLDEN_CONFIG §5.2 / §7 item 2: *"each ~2-bit
win carries a real information bill at decode (settling which reading of the
stream is correct — multiple decodings are free to RUN but not free in the
accounting at scale)."*

---

## 1. HYPOTHESIS (written before any test)

I separate two quantities the decoder produces, because they pay in different
currencies:

- **S(N,P) = surviving full readings**: complete decodings that parse to N
  clean literals of the right total length and are otherwise structurally
  self-consistent, *before* the 64-bit header checksum is applied. This is the
  Q1 "self-consistent decodings" count.
- **W(N,P) = DFS work**: total partial readings (tree nodes) the keep-what-
  decodes search must touch to enumerate the survivors. This is the decode
  compute.

**What I expect, and why, from the mechanics:**

The ambiguity is born at one place only: *a single arity-a record on the wire
can be read two ways* — (i) "open it now" (it was born on the pass this reverse
step undoes) or (ii) "carry it" (it was born earlier, rides to a later reverse
step). The dispute in THE_OPEN_QUESTION is exactly this: a pass-2 record (home)
and a pass-1 survivor (one unshuffle from home) are byte-identical on the wire.
So at each reverse step, each record present is a *binary* open/carry choice.

Naively that is 2^(records) per step and 2^(records·P) over the run —
catastrophic. But three mechanical filters prune almost all of it:

1. **Structural pruning (free, content-blind).** A *wrong* open expands the
   seed against the wrong position-salt; the expansion is a uniform hash
   stream, so it parses to self-delimiting items only by luck and almost
   always leaves dangling garbage / wrong length / a record where a literal
   must be. This is the **explosion check** (BRIEF "free partial birth channel",
   ~2.5 bits/record measured). Each wrong open survives the structural parse
   with probability ≈ 2^-2.5 ≈ 0.18.

2. **Length pruning (free).** The final stream must be exactly N literals of
   B bits. An arity-a open changes the item count by +(a-1) relative to a carry.
   Over the whole reversal the produced length is pinned by the header, so
   readings whose opens don't sum to the right count die.

3. **Checksum referee (64 bits, FINITE, stored).** Among readings that survive
   1+2, the header's ~64-bit hash of the original keeps the true one. The
   checksum can distinguish at most ~2^64 candidates before a *collision* lets a
   wrong reading masquerade as right. This is a finite, file-size-independent
   resource.

**My prediction (mechanics-derived) — CORRECTED after advisor review.**

My first draft mislabelled the branching as *subcritical* (geometric ratio
0.18 → O(1) survivors). That is wrong, and it contradicted my own cited
evidence ("long runs lose to ambiguity growth", "good for tens of passes").
The correct accounting:

The **true reading always survives (prob 1).** Separately, for each record born
on some pass, the decoder may *also* try opening it on any of the other reverse
steps it is present for; each such *wrong* birth-pass open additionally survives
the explosion check with prob q ≈ 2^-2.5 ≈ 0.18. So the **per-record candidate
multiplicity** is

    m(P) = 1 + q·(window of alternative reverse steps) ≈ 1 + q·(P−1)   (upper)

— this is **> 1, i.e. supercritical**. The wrong lineages do not just decay
away: there are Θ(decision points) of them, each spawning more. Over R
*ambiguous* records (each choosing its open-step quasi-independently, pruned
only by the explosion + length checks), the count of self-consistent full
readings *before the checksum* is

    **E[S(R,P)] ≈ m(P)^R   — EXPONENTIAL in R, with base growing in P.**

So the bound I will look for is NOT "S stays small"; it is the *opposite*:
S explodes, and the discriminating measurement is **log S vs R at fixed P**.
A positive linear slope = exponential = "no free channel"; the slope IS
log2 m(P), and m(P) is the one number worth pinning. (At small R even 1.9^R
looks deceptively linear — that is exactly why the test must vary R and fit the
log, not eyeball toy magnitudes.)

- **W(N,P) (DFS work)** tracks the surviving tree, so it is also **exponential**
  in R (super-polynomial), dominated by m(P)^R. The keep-what-decodes search is
  therefore a search *whose size grows with the file* — which the requirements
  card item 3 forbids for a stateless decoder.

- **Where the bill reappears (counting gate, named in advance):** to uniquely
  select the true reading among S = m(P)^R candidates, a referee needs
  **log2 S = R·log2 m(P) bits** of discrimination. The header checksum is that
  referee. So the deferred birth entropy resurfaces as **checksum width — stored
  bits, ~log2 m(P) per record** — which is exactly THE_OPEN_QUESTION's
  ~log2(passes)-per-record lower bound, arriving through the back door of trial
  decode. Equivalently, hold the checksum fixed at 64 bits and the bill becomes
  **exponential DFS compute**, and decode goes **genuinely ambiguous** (a false
  reading collides with the 64-bit checksum) once R·log2 m(P) ≳ 64, i.e. at a
  finite reach **R ≈ 64 / log2 m(P)**.

- **Net per match ≈ 2 − log2 m(P)** bits: crosses zero when m(P) ≈ 4, i.e. when
  q·(P−1) ≈ 3, i.e. **P ≈ 1 + 3/0.18 ≈ 18** — which would explain the documented
  "best T 16–64" sweet spot and the "T ≫ 64 grinding" dead end (GOLDEN_CONFIG
  §6) falling out of the *same* arithmetic.

**Pre-registered prediction to test:** log S(R,P) rises linearly in R; the slope
log2 m(P) climbs from ~1 (P=20) toward larger values as P grows. I will MEASURE
m(P) directly rather than assume q·(P−1) — the length and position constraints
may lower the effective base, and that effective base is the load-bearing
number.

---

## 2. SHARPENING — singles collapse the slope to an EXACT count S = T^R

Building the toy exposed that the explosion-check survival probability q is not
a single number: it is **q ≈ 0.18 for bundles but q = 1 for singles**, and the
singles case is the crux of this lane. Two facts:

- **For bundles (arity ≥ 2)**, the *real* J3D1 Lotus seed field is an
  *incomplete* code: many digests fail to parse to exactly `a` self-delimiting
  children (invalid seed, child-count mismatch, dangling tail). That incomplete
  code IS the ~2.5-bit explosion check (BRIEF row 7). A toy with a *complete*
  alphabet (every bitstring parses) measures q = 1 — but that is a toy artifact,
  not the bundle truth. (My first `measure_q` returned q=1 for exactly this
  reason; I do not use it for bundles.) Bundles also carry the affine-stride
  fingerprint (index-arithmetic), a strong content-blind filter — this is why
  `v1_roundtrip_proof.py` forks stay 15–171 at T≤5. **Bundles are a different
  lane (affine-stride); they are NOT the wall.**

- **For singles (arity 1)** q = 1 is *fundamental, not a toy artifact.* A single
  is length-preserving (1 item → 1 item) and expands to a structurally valid
  B-bit literal at *any* position-salt. So:
  * the explosion check cannot touch it — a wrong-salt open is exactly as
    structurally valid as the right one; it merely yields **different bytes**
    (this is verbatim the `robins_exact_spec.py` dispute: seed 6523 opened at
    position 0 vs its true position 4 — both "decode successfully", different
    bytes, 0/9 vs 9/9);
  * the length constraint cannot bite — 1→1 preserves the item count;
  * therefore the **only** decode freedom for a single is *which reverse walk it
    is opened on*. A single placed on the wire is present at all T walks;
    opening on walk j salts with its position-at-walk-j → a distinct,
    structurally valid reading.

Consequently the per-single multiplicity is not `1 + q·(P−1)`; it is **exactly
T**, and R independent singles give

    **S(R, T) = T^R   — EXACT, by construction. No explosion, no length**
    **pruning, checksum only.**  (evidence: proven-by-construction, below.)

This is the *stronger* (worse-for-the-design) result and the right one for the
wall. It collapses the "measure the slope" plan into an exact closed form:
log2 S = R·log2 T, slope = log2 T, m(P) ≡ T.

Sanity check against the existing artifact: T=2, R=1 ⇒ S=2. Those two readings
*are* `robins_exact_spec`'s "open on walk 1" (wrong for a pass-1 survivor) and
"open on walk 2" (right) — the exact 0/9 vs 9/9 split, checksum as referee.

---

## 3. TOY + RESULTS (proven-by-construction, real SHA-256)

Toy: `model_analysis/birth_channel_research/B-ambiguity-bound_survivor_count.py`.
Maintainer's exact architecture — in-place expansion, position salts (item's
current position at match time), +1-shifted bijective shuffle, keep-what-decodes
open/carry DFS. Singles are in the open/carry dispute (unlike v1_roundtrip_proof,
which slot-keys singles and dodges the birth-pass ambiguity). The DFS branches
open/carry on every record at every reverse walk and **counts every complete
reading that ends all-literal with the correct item count, BEFORE the checksum**.
R singles are planted one per early pass so each rides ~T walks. Real SHA-256 on
every open.

**Would-the-test-work check:** this test never needs a *lucky* match — the
plants create the true spine deterministically, and the quantity under test
(does a wrong-salt single-open stay structurally valid?) is content-blind and
true with probability 1, so no rare event is being waited on. The DFS is exact
enumeration, not sampling.

Confirmation at small T (S equals T^R exactly, node count polynomial):

    T=3 R=1 S=3   =3^1   nodes=10
    T=3 R=2 S=9   =3^2   nodes=30
    T=3 R=3 S=27  =3^3   nodes=100
    T=4 R=3 S=64  =4^3   nodes=225
    T=5 R=3 S=125 =5^3   nodes=441      (all match=True)

High-T runs (well past the wall — the BRIEF demands T ≫ tens). Every row is
integer-exact, S == T^R, real SHA-256, exact DFS enumeration:

    T = 20:  R=1 S=20      =20^1   nodes=231
             R=2 S=400     =20^2   nodes=3,311
             R=3 S=8,000   =20^3   nodes=53,361
    T = 50:  R=1 S=50      =50^1   nodes=1,326
             R=2 S=2,500   =50^2   nodes=45,526
             R=3 S=125,000 =50^3   nodes=1,758,276
    T = 100: R=1 S=100        =100^1  nodes=5,151
             R=2 S=10,000     =100^2  nodes=348,551
             R=3 S=1,000,000  =100^3  nodes=26,532,801

All nine rows: match = YES (S equals T^R to the integer). The DFS node count
itself grows like ~(T·R)-polynomial-per-leaf but the LEAF count — the
self-consistent readings the checksum must referee — is T^R, exponential in R.

The fit is not needed: S = T^R holds to the integer at every tested (R,T), so
the per-single multiplicity m(P) = T exactly. log2 S vs R is a straight line of
slope log2 T.

---

## 4. COUNTING GATE — closed (the deliverable)

**Gate question:** if keep-what-decodes were a free, content-blind, unbounded
birth channel, would arbitrary random data net-compress without bound?

**Answer: NO — and the leak is named precisely.** The survivor count is
S = T^R, exponential in the number of singles R. Deterministic decode means
*selecting the one true reading out of S*. By Shannon that selection requires a
referee with **log2 S = R·log2 T bits** of discrimination. The header checksum
IS that referee. Therefore:

- **Hold the checksum at its fixed 64 bits** ⇒ decode is genuinely deterministic
  only while `R·log2 T < 64`, i.e. **R ≲ 64 / log2 T** single-records
  (≈ 9.6 singles at T=100, ≈ 15 at T=20). Past that, a *wrong* reading collides
  with the 64-bit checksum and decode is **genuinely ambiguous** — there is no
  rule, free or otherwise, that picks the truth. This is exactly why 12/12 and
  36/36 pass: their R≲9, T≤5 give R·log2 T ≈ 20 ≪ 64 — they sit *below the
  collision floor*, which is NOT evidence of boundedness. Prediction (falsifiable):
  push R and T so R·log2 T > 64 and decode WILL admit a colliding false reading.

- **To scale to N singles on a real file**, the checksum must grow to
  ≈ N·log2 T bits — which is **exactly the birth bill**, log2(passes) per record,
  THE_OPEN_QUESTION's "unpayable remainder." The deferred birth entropy
  reappears, dollar-for-dollar, as stored referee bits.

- **Equivalently in compute:** at fixed checksum the keep-what-decodes search
  must enumerate/winnow T^R readings — a search **whose size grows
  exponentially with the file**, which the requirements card item 3 forbids for
  a stateless decoder.

So "trial-decode ambiguity is bounded ⇒ no channel needed" is **REFUTED for
singles.** The ambiguity is not bounded; it is T^R. The "no channel" is an
illusion that holds only below the checksum collision floor.

---

## 5. CURRENCY ACCOUNTING

The birth bill for singles is paid in **stored-bits (checksum width) ≡ compute
(search T^R)** — a strict equivalence, not a discount in either:

- **stored-bits:** log2 T per single = log2(passes) per record. At the Golden
  Config T∈{16..64}, that is **4 to 6 bits per single** of required referee
  width — and the average win is E[win|hit] ≈ 2 bits (MATH_MODEL §2). So
  **net per single = 2 − log2 T**, which is **≤ 0 for all T ≥ 4** and strongly
  negative across the whole Golden range.
- **compute:** the alternative to paying the bits is to brute-search T^R
  readings, i.e. compute that scales as 2^(R·log2 T) — the `compute that scales
  with 2^bits` currency named in the BRIEF.

**Max-free reach K for the singles grinding channel:** net/single = 2 − log2 T
> 0 only for **T ≤ 3**, marginal at T=3, so **K ≈ 3–4 passes.** This is the
honest finite reach: the free singles channel sustains compounding for only a
handful of passes before the birth bill on each new single exceeds its 2-bit
win. It is fully consistent with the repo's standing facts — "arity-1 is
one-shot" (GOLDEN_CONFIG §6), "singles are slot-keyed, epoch-free but one-shot"
(MATH_MODEL §6/§7b), and the "best T 16–64 / T≫64 grinding dead end": the engine
runs many passes because *bundles* (affine-stride, real channel) keep paying;
the *singles* free channel was spent by pass ~4.

---

## 6. EVIDENCE CLASSES (per claim)

- **S(R,T) = T^R for singles, exactly:** *proven-by-construction*
  (real SHA-256, exact DFS enumeration; toy confirms integer-exact at every
  tested (R,T) including T∈{20,50,100}). Also *proven-by-math*: a single is
  1→1 and structurally valid at every salt, so the only freedom is the open-walk
  ∈ {1..T}, independent across R singles ⇒ T^R.
- **q = 1 for singles (no explosion check):** *proven-by-math* (length-preserving
  + complete on one literal) and consistent with `robins_exact_spec.py`'s
  "different bytes, both decode" trace.
- **q ≈ 0.18 for bundles (explosion check is real there):** *measured* upstream
  (BRIEF row 7 / PLAIN_STATUS); not re-measured here — bundles are the
  affine-stride lane, out of scope for the wall.
- **Counting-gate closure (referee needs R·log2 T bits; net = 2−log2 T;
  K≈3–4):** *proven-by-math* from S=T^R + Shannon selection + E[win|hit]≈2.
- **Decode below the collision floor (12/12, 36/36) is not evidence of
  boundedness:** *proven-by-math* (R·log2 T ≈ 20 ≪ 64 in those harnesses).

---
