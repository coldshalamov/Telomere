# Avenue H — Sharp impossibility: the conservation theorem for the birth channel

Author: birth-channel researcher (lane H). Date: 2026-06-13.
Status of this file: working notes + the theorem + the one load-bearing
assumption. Evidence classes are named on every claim.

---

## 0. What this lane must produce (from BRIEF avenue H)

> If birth pass is genuinely incompressible, produce the cleanest possible
> theorem: define the channel formally, show the births' entropy lower-bounds
> any decodable representation, and identify the SINGLE assumption that, if
> relaxed, would break it.

So the deliverable is: (1) a formal coding-problem statement of the birth
channel; (2) an entropy lower bound that is a genuine *counting* bound, not an
expectation hand-wave; (3) the conservation accounting (which currency the bill
appears in); (4) the single assumption the whole wall hinges on, handed to the
constructive lanes as the thing to attack.

---

## 1. HYPOTHESIS (written BEFORE any test — protocol rule 1)

What I expect, and why, from the mechanics:

**H1.** The birth-pass map is not arbitrary side information — it is forced by
the decode procedure. SPEC §1/§2: a record r expands under a position-salted
key tied to r's state at its birth pass t(r). The reverse walk only arrives at
that state at one specific reverse step. So **the decoder's output is a
function of (wire, header, and the assignment of birth passes to records).**
I expect to be able to prove that two distinct birth-pass assignments on the
same wire generically yield two distinct decoded files — i.e. the birth-pass
map carries real, non-redundant information, not formatting slack.

**H2.** I expect the total birth information to be Θ(N log T) in the worst case
(N records, T passes) and, more precisely, to equal H(birth-pass profile) =
the entropy of the empirical distribution of records across passes — a few bits
per record once T exceeds a handful. I expect this to be a hard *Shannon /
Kraft* floor on any decodable representation, by a direct injectivity counting
argument (the standard impossibility-of-universal-compression skeleton), NOT an
average-case argument that a clever code might dodge.

**H3.** I expect the ~2.5-free-bits explosion channel (Result-Ledger row 7) to
be a genuine but *bounded* free subsidy: it pays the FIRST ~2.5 bits of each
record's birth information (≈ disambiguating ≤6 candidate passes) and nothing
beyond. So the residual unpaid bill per record is max(0, H_birth(r) − 2.5)
bits, which is 0 while T ≲ 6 and grows like log2(T) − 2.5 afterward. This
predicts the wall is not at T=1 but at a *finite reach* — consistent with the
constructive lanes' job being "quantify K," and with this lane's job being
"prove the residual is unpayable for free, content-blind, unbounded."

**H4 (the load-bearing-assumption prediction).** I expect exactly ONE of the
four channel premises — {uniform hash, content-blindness, full determinism,
write-once} — to be the keystone, and I predict it is **content-blindness**.
Reason: the births are forced to be incompressible *only because* the hash is
uniform AND the mechanism refuses to look at content. If content-coupling were
allowed, the birth pass could correlate with derivable features of the record
(e.g. seed value, span content) and become partially inferable — which is
exactly what "keep-what-decodes" already exploits a little (the explosion
check IS a content-coupled inference: it reads whether the *expansion* parses).
Uniform-hash and write-once are real but I expect them to be *downstream* of
content-blindness: relax content-blindness and the other two stop biting.

I will test H1 by construction (a tiny exact toy: same wire, two birth
assignments, two outputs), H2 by a counting argument (math), H3 by the ledger
already measured (cite, plus an exact residual computation), and H4 by
structural analysis of which premise each no-go result in the requirements card
actually uses.

---

## 2. Formal definition of the birth channel as a coding problem

### 2.1 The objects

Fix block size B and alphabet. An *input file* is x ∈ {0,1}^n. The encoder
runs T passes (T derived, not chosen adversarially per file; but the analysis
must hold for the T the encoder actually used). The encoder emits:

- **header** h(x): a FIXED-size string. By SPEC §3 its size does not grow with
  n: TLMR + version + Lotus(B, original_len, last_block_size) + alphabet bit +
  c-bit checksum, with c ≈ 64 constant. Write |h| ≤ H0 + ⌈log2 n⌉ + O(1); the
  only n-dependence is original_len, which costs O(log n), NOT O(n).
- **wire** w(x): the final stream of items (records + literals + one remainder
  run). This is the bulk; it is what must beat raw.

The decoder D is a deterministic algorithm: D(w, h) = x for every x (lossless,
required). The decode procedure (SPEC §4) reverses passes; to reverse pass t it
must open exactly the records born at pass t, each salted by its
then-current position.

### 2.2 The birth-pass map as the missing coordinate

Define, for the encoder run on x, the **birth profile**
β(x) : R(x) → {1,…,T}, where R(x) is the set of records on the wire and β(x)(r)
is the pass that created r. (Singles: arity-1 records; bundles: arity ≥ 2.)

**Claim (decode-dependence, proven by construction in §4):** there is a
decode functional Ψ such that x = Ψ(w(x), h(x), β(x)), and for generic w there
exist β ≠ β′ with Ψ(w,h,β) ≠ Ψ(w,h,β′). I.e. β is not derivable from (w,h)
by formatting alone; it is a real coordinate.

This is the precise sense in which "the decoder must learn each record's birth
pass." The open question (THE_OPEN_QUESTION) is whether β is *derivable* from
(w,h) by some free, content-blind, deterministic rule. This lane proves: not
unboundedly.

### 2.3 The channel, formally

The **birth channel** is the sub-problem: *convey β(x) to a decoder that
already holds (w,h), using zero additional stored bits, by a content-blind
deterministic rule.* A solution is a function

    Β : (wire, header) ↦ birth-profile

that is correct on every x the encoder produces, computed without reading the
*content* of the original blocks (content-blindness) and without per-record
stored metadata (the metadata contract, SPEC §0).

The conservation question: is the information content of β(x) supplied by some
*free* resource already on the wire, or must it be paid?

---

## 3. The entropy lower bound (the counting gate, made sharp)

**Two theorems, two assumptions — do not conflate them (this is the cleanest
result of the lane):**

- **Theorem A (no net compression / universality).** Hinges on
  **bounded-loss + lossless + content-blindness**. Content-blindness is the
  bridge: it forces the codec to behave identically on random data, so "works
  on my files" ⇒ "works on all files" ⇒ pigeonhole. Does NOT need uniform hash.
  This is §3.1 — the generic backstop.
- **Theorem B (birth-channel lower bound).** Hinges on the **uniform hash law**.
  Holding the wire fixed, the number of files reachable under different birth
  profiles is ≥ 2^{H(β)}; a free content-blind rule cannot pick the right one
  past a finite reach. This is §3.2 — the *tight* argument, and the one this
  lane owns. **Lead with it.**

The one-line discriminator for *why uniform-hash and not content-blindness* is
the load-bearing assumption for the BIRTH CHANNEL specifically: the load-bearing
assumption is the one whose relaxation correlates the birth pass with something
**already on the wire**.
  - Non-uniform hash → birth pass correlates with the *stored seed field* →
    decoder reads it for free, on the wire. ✓ (a real key candidate)
  - Content-coupling → birth pass correlates with *content* → but content is
    exactly what we are trying to recover, it is NOT on the wire → cannot be
    read free. ✗

### 3.2 The tight argument: hold the wire fixed, count reachable files (Theorem B)

This is the sharp statement. Hold the wire w fixed (a fixed multiset of records
+ literals + remainder run) and ask: how many distinct files decode from this
wire under SOME admissible birth profile? By §2.2 / the §4 toy
(decode-dependence, proven-by-construction), distinct admissible profiles β
generically give distinct files. Let A(w) = #{self-consistent (file, β) pairs
for wire w}. Then

    #{files reachable from wire w}  ≥  A(w).

A free derivable channel Β must pick the ONE correct β out of A(w) candidates
with zero stored bits, content-blindly. The information to pin the correct
profile is **log2 A(w) = H(β) bits** in the worst case (β = the birth profile;
H(β) is its entropy, with a *late-born single* costing up to log2(T) — the
hard regime is sustained late singles, each ~log2(T) bits). For this to be
free, A(w) = 1 (β forced) OR the selector comes from a free resource. The only
two free resources on the wire are:

  (i) **the header checksum** — a FIXED c≈64 bits TOTAL, shared across all N
      records. A c-bit hash distinguishes at most 2^c GLOBAL decode hypotheses.
      So it pins log2 A(w) only while the *whole-file* ambiguity stays ≲ 2^c,
      i.e. N·(unpaid bits/record) ≤ 64. It is a per-FILE constant-capacity
      referee, NOT a per-record channel. (This DERIVES the requirements-card
      no-go "global pass counter: 16 bits total cannot carry per-record
      answers.") Evidence: proven-by-math.

  (ii) **the explosion check** — structural ~2.5 bits/record (§3.3): wrong-salt
       expansions fail to parse / leave dangling garbage, so the right birth
       pass is detectable by non-blowup. Measured (row 7). Bounded.

Everything else on the wire (seed/arity payload) is already spent paying "which
seed." So the residual unpaid birth information is

    Σ_r max( 0,  H_locate(r) − S_struct )  −  min(64, total slack)        (†)

with S_struct ≤ 2.5 and H_locate(r) = log2(#live candidate passes for r). By
the exact ledger (`H-impossibility_residual_ledger.py`): (†) = 0 while T ≤ ~5
and grows as **log2(T) − 2.5 − 64/N** thereafter — unbounded in T. **This is
the sharp localization: the bill is the birth-profile entropy minus two finite
free subsidies.** MAX-FREE-REACH K ≈ 5–6 passes for the structural subsidy
(crossing at log2(T) = 2.5 ⇒ T ≈ 5.7). Evidence class: proven-by-math for the
structure; "2.5" is measured (cited); checksum-capacity is proven-by-math.

### 3.1 The generic backstop: the universality bound (Theorem A, proven-by-math)

This is the airtight version of "births are incompressible dice." It does NOT
use expectation values; it is a pigeonhole/injectivity count.

**Setup.** Restrict to a content-blind protocol: the codec's behavior on a file
is determined by the hash outcomes, not by which file produced them. Formalize
content-blindness as: **the protocol commutes with re-hashing.** Concretely,
the only thing the encoder learns about x is the set of (seed, key) → span
match events; by the uniform-hash law these events are a function of the random
oracle, independent of the *bytes* of x given the match pattern. So the map
x ↦ (w(x), h(x)) factors through the match-pattern, and any two files with the
same match-pattern and same literal content are handled identically.

**The injectivity bound.** D is lossless ⇒ x ↦ (w(x), h(x)) is injective.
Hence for any length n,

        Σ_x 2^{ −|w(x)| − |h(x)| }  ≤  1            (Kraft, since the encoding
                                                     is a prefix-free/uniquely-
                                                     decodable code on x).

|h(x)| = H0 + O(log n) is essentially constant in n. Therefore the wire alone
must satisfy a Kraft inequality with only an O(log n) slack:

        Σ_x 2^{ −|w(x)| }  ≤  2^{ H0 + O(log n) }.   (★)

Now the bounded-loss guarantee (SPEC §3, MATH_MODEL §7 worst case): **no file
ever exceeds raw + 3 + |h| bits**, i.e. |w(x)| ≤ n + 3 for all x. Combined with
(★): the number of files that can have |w(x)| ≤ n − Δ is at most
2^{n − Δ + H0 + O(log n)} ... but there are 2^n files of length n and they all
have |w(x)| ≤ n+3. The fraction that can save Δ bits is ≤ 2^{−Δ + H0 + O(log n)}.

**Conclusion (no-net-compression, sharp).** For ANY content-blind lossless
codec with bounded loss ≤ n+3, the fraction of n-bit files that net-compress by
Δ bits is ≤ 2^{−Δ+O(log n)}. Compression of "almost all" files by a constant
rate is impossible — not as an average, but for all but an exponentially small
set. This is exactly the master gate. **Evidence class: proven-by-math**
(standard, but written here against THIS codec's bounded-loss guarantee).

This already settles the gate: a *free, content-blind, unbounded* birth channel
would make almost all files net-compress (each pass nets ~2 bits/match, T
passes, density above threshold "for free"), contradicting the bound. So the
birth channel CANNOT be simultaneously free + content-blind + unbounded. QED at
the gate level.

### 3.3 Why the explosion subsidy is finite (cite + exact residual)

Result-Ledger row 7 / PLAIN_STATUS / BRIEF: a wrong-salt expansion fails to
parse self-delimitingly / leaves dangling garbage / fails checksum, so trial
decode detects the right birth pass by *non-explosion*. Measured budget ≈ 2.5
bits/record, distinguishing ~5–6 candidate passes for free. **Evidence class:
measured** (their number; I did not re-measure — see §6 for why a re-measure
would be luck-bound and uninformative here, and what I DID compute instead).

The residual after this subsidy, per record, is:
    unpaid(r) = max(0, log2(#candidate passes for r) − 2.5).
While T ≤ 6: unpaid = 0 (subsidy covers it). T = 64: log2(64) = 6 bits, minus
2.5 = 3.5 bits/record unpaid (if every pass is a candidate). This is the finite
reach: the free channel covers up to ~2^2.5 ≈ 5.6 passes of ambiguity, i.e.
**max-free-reach K ≈ 6 passes for the structural subsidy alone**, matching the
"good for tens of passes" claim only when combined with the per-file checksum
amortized over few records. Past that, (†) is strictly positive and grows.

---

## 4. TOY (proven-by-construction): birth profile is a real coordinate

Hypothesis being tested: H1 — same wire, two different birth-pass assignments,
two different decoded files. If true, β is not formatting slack; it is genuine
information that a free channel would have to supply. This is a *logic/counting*
toy (no luck, no rare match needed): I plant a seed→span so a match exists by
construction, exactly as the BRIEF's "would the test even work?" rule demands.

See `H-impossibility_birth_coordinate.py`. Construction:

- Two records sit on a wire. Decode them at birth-pass assignment β vs β′.
- Because the salt = position-at-birth and the reverse walk reaches different
  positions at different reverse steps, the SAME seed expands to DIFFERENT bytes
  under β vs β′ (this is precisely the dispute in THE_OPEN_QUESTION: "decode it
  where it stands and the hash runs with the wrong position; different bits come
  out"). The toy makes that concrete with real SHA-256 and a planted seed.

Predicted output: the two assignments yield different reconstructed blocks for
at least one record ⇒ β is load-bearing. Result recorded in §5.

---

## 5. Toy runs + results

### 5.1 `H-impossibility_birth_coordinate.py` (proven-by-construction, exit 0)

Decoded the SAME arity-1 record (same seed 6523, same final wire slot) under
each candidate birth pass t, salting with its position-at-pass-t (SPEC §1), with
the canonical i→(5i mod P)+1 shuffle. Result across 4 boards:

| N | T | distinct salts | distinct decoded bytes | coordinate matters |
|---|---|---|---|---|
| 13 | 5 | 4/5 | 4/5 | yes |
| 13 | 8 | 4/8 | 4/8 | yes |
| 29 | 12 | 12/12 | 12/12 | yes |
| 29 | 16 | 14/16 | 14/16 | yes |

**Confirmed H1:** birth pass changes the decoded bytes in every case. β is a
genuine decode coordinate, not formatting slack — a content-blind decoder that
does not receive it cannot reconstruct the file. This is the constructive
backbone of Theorem B's "distinct profiles give distinct files."

**Unexpected structural finding — the ORBIT-COLLISION (a contribution to lanes
A/C/E).** The salt sequence is PERIODIC: at N=13 it is `[7,10,12,9, 7,10,12,9,…]`
— period 4. So across 8 passes there are only 4 distinct birth *positions*. The
period is the multiplicative order of 5 in the cycle-walk group (the salt orbit
length, here 4). Consequences, stated precisely so a constructive lane can use
them without over-reading:
  - It CAPS what the explosion check can ever SEE to log2(orbit), not log2(T):
    same-salt passes decode to identical bytes, so non-blowup cannot separate
    them. (A subsidy ceiling, not a new free channel.)
  - It does NOT reduce H_locate = log2(T): the decoder must still open the
    record at the correct reverse STEP; opening at the wrong same-salt pass
    places the record's children at the wrong point in the unwind and corrupts
    other records. So the orbit collapses the *byte-distinguishable* part of the
    birth entropy but leaves the *location* part fully intact.
  - Net: this is why **avenue A (orbit phase for singles) cannot by itself free
    the channel** — the orbit phase narrows candidate salts but the location
    bill log2(T) is untouched. It can at best help an explosion-check-style
    referee, inside the finite K, not extend K. Hand-off recorded.

### 5.2 `H-impossibility_residual_ledger.py` (proven-by-math, exit 0)

Exact per-record unpaid birth bits after the two finite free subsidies (no
hashing, pure counting). With S_struct = 2.5 (measured, row 7) and c = 64:

    residual(T) = max(0, log2(T) − 2.5 − 64/N)

| T | log2(T) | residual @ N=1000 |
|---|---|---|
| 4 | 2.000 | 0 (free) |
| 5 | 2.322 | 0 (free) |
| 6 | 2.585 | 0.021 |
| 8 | 3.000 | 0.436 |
| 16 | 4.000 | 1.436 |
| 64 | 6.000 | 3.436 |
| 256 | 8.000 | 5.436 |

**MAX-FREE-REACH K ≈ 5–6 passes** (crossing at log2(T)=2.5 ⇒ T≈5.7). Past K the
residual grows as log2(T) − 2.5 — unbounded. At the Golden Config T=64, the
unpaid bill is ~3.4 bits/record, which swamps the ~2-bit average win
(MATH_MODEL §2) ⇒ net negative, matching MATH_MODEL §7b and GOLDEN_CONFIG §5
independently. The 64-bit checksum is per-FILE: at N=1000 it adds only
0.064 b/rec and cannot scale (the derived "global counter can't carry per-record
answers" no-go).

---

## 6. "Would the test even work?" audit (protocol rule 2)

- §4 toy uses a PLANTED seed→span (real SHA, but the match is guaranteed by
  construction), so it needs no luck. It tests LOGIC (does birth pass change the
  output), not whether a random match occurs. Valid.
- I deliberately did NOT run a "search for a sub-2-bit birth channel and find
  nothing" test: finding nothing would be expected and would prove nothing
  (BRIEF rule 2). The impossibility is carried by §3's counting, not by a failed
  search.
- I did NOT re-measure the 2.5-bit explosion subsidy: that number is already
  measured (row 7); re-measuring at toy scale with few candidate passes is
  luck-bound and would not sharpen the theorem. I instead compute the *residual*
  exactly as a function of the cited 2.5.

---

## 7. The single load-bearing assumption (the deliverable for constructive lanes)

### 7.1 H4 prediction vs finding (honest record)

Before testing I predicted (H4) the keystone would be **content-blindness**.
**This shifted, and the shift is a strengthening, not a wobble.** The correct
keystone for the BIRTH CHANNEL is the **uniform hash law**. The shift came from
separating the two theorems (§3): content-blindness is the keystone of
Theorem A (universality/no-net-compression — which needs only bounded-loss +
lossless + content-blindness, no uniform hash); the uniform hash law is the
keystone of Theorem B (the birth-channel lower bound), which is the theorem this
lane owns.

### 7.2 The discriminator (why uniform-hash, not the other three)

The load-bearing assumption for the birth channel is the one whose relaxation
correlates the birth pass with something **already on the wire**:

| premise relaxed | does birth pass become readable on the wire? | verdict |
|---|---|---|
| **uniform hash** | YES — birth pass correlates with the *stored seed field*, which the decoder already reads. | **the keystone** |
| content-blindness | birth pass correlates with *content* — but content is what we are recovering; it is NOT on the wire. | not it (it powers Theorem A) |
| full determinism | a randomized decoder still must hit the right file; randomness adds no readable correlate. | not it |
| write-once | per-pass rewriting reaching the decoder = stored metadata by another name = the priced `tags` baseline (≥ log2 T bits, already net-negative past pass ~6). | trivial escape, forbidden by SPEC §0 |

This matches THE_OPEN_QUESTION's core obstruction almost verbatim: "a uniform
hash makes them independent and incompressible; deduction requires coupling and
uniformity certifies there is none." Uniform hash is also the SOLE empirical
assumption in the entire model (MATH_MODEL §1), so it is the natural single
point of attack.

### 7.3 The CLAIM, properly gated (passes its own counting gate)

Stated as proven, and ONLY as proven:

> **The uniform hash law maximizes H(β) and certifies the births are
> independent and incompressible; it is therefore load-bearing *in the
> impossibility proof* (Theorem B). Relaxing it — a hash whose outcome
> correlates birth-pass with the stored seed — is the NECESSARY surgical
> target, the one place a free birth key could enter. SUFFICIENCY is UNPROVEN:
> a biased hash makes the seed encode birth-pass (free in stored-bits), but the
> encoder may then only use bias-consistent seeds, which can crater match-supply
> or raise effective seed cost. The bill may simply relocate to the
> `match-supply` currency. So a non-uniform hash is where to look, not a
> solution; any candidate built on it must itself survive the counting gate.**

This is the honest hand-off: it tells the constructive lanes the exact door to
try (couple birth-pass to the seed via controlled hash bias) AND the exact trap
that door has (the freed stored-bits reappear as match-supply loss — the same
geometric-starvation currency the BRIEF's avenue-E LEAK WARNING and
Result-Ledger row 9 already price at ~2× supply loss per bit gained). It also
connects to the bits-back note in THE_OPEN_QUESTION: a biased hash is exactly a
"partial birth-inference" key candidate — "the multiplier exists; the key
doesn't" — and this lane says where the key would have to come from.

### 7.4 What each constructive lane should take from this

- **A (orbit/affine-stride for singles):** the orbit phase caps what a referee
  can SEE (log2 orbit) but never reduces H_locate = log2(T) (§5.1). Orbit alone
  cannot extend K; it can only help fill the finite K. Do not over-invest.
- **C (CRT/residue clocks):** capacity check is the constraint — a fixed board
  of size Q holds log2(Q) bits TOTAL; the channel needs N·log2(T). The residual
  ledger (†) is the bar to clear; a residue clock pays in `stored bits` if the
  board grows (PCTB dead end) or in `wrap/carriage` if it does not.
- **E (explosion amplification):** the 2.5-bit subsidy is already counted in
  (†); any period-P schedule that adds disambiguation MUST report net AFTER the
  ~2× match-supply loss it incurs (BRIEF avenue-E LEAK WARNING). Gross reach is
  not the deliverable; net reach after supply loss is.
- **All lanes:** the keystone to attack is the uniform hash (§7.2–7.3), not the
  other three premises. A candidate that does not couple birth-pass to an
  on-wire quantity is paying the bill in some currency; find it before claiming.

---

## 8. The counting-gate answer (the reductio, stated as the deliverable)

**Q: If this mechanism (a free, content-blind birth channel) were unbounded,
would arbitrary random data net-compress without bound?**

**A: YES — and that YES is the contradiction that proves it cannot exist.**
Reductio, routed through the mechanism that actually connects "free birth" to
"compression" (the fresh-dice engine, MATH_MODEL §6 — NOT a "one wire → many
files" claim, which would be an oxymoron under a deterministic decoder):

  1. Suppose a free + content-blind + unbounded channel Β(w,h) = β supplies
     every record's birth pass at zero stored cost.
  2. Then the per-pass position salts are decodable for SINGLES too (the salt is
     self-presenting once you know the reverse step, which β gives). So singles
     get fresh dice every pass — the arity-1 grinding channel turns on.
  3. Fresh dice every pass ⇒ the match rate is sustained and coverage → 1 as T
     grows (MATH_MODEL §6's fresh-dice branch crosses below original size and
     keeps earning; the §7b birth-information tax that normally kills it is, by
     assumption, free). Each match nets ~2 bits (MATH_MODEL §2).
  4. By content-blindness the mechanism behaves identically on random data, so
     ALMOST ALL n-bit files net-compress by Θ(n) bits as T grows — including
     random ones.
  5. A lossless codec with bounded loss (|w| ≤ n+3) that net-compresses almost
     all files maps 2^n inputs into a strictly smaller image (Theorem A / Kraft):
     a pigeonhole violation. **Contradiction.** Therefore no such channel exists.

The leak in step 3 is plugged by exactly the finite free resources: explosion
non-blowup ≤ 2.5 bits/record (measured) + checksum 64 bits/file ⇒ the fresh-dice
subsidy only reaches K ≈ 5–6 passes for free; past K the residual
log2(T) − 2.5 − 64/N bits/record is unpayable, the §7b birth tax reasserts, and
coverage stops compounding for free.

**The finite resources that DO bound it (where the bill actually sits):**
(1) the per-file checksum, c≈64 bits TOTAL, ≈ c/N bits/record — a per-file
constant, not a per-record channel; (2) the structural explosion non-blowup,
≤ ~2.5 bits/record (measured). Together they give MAX-FREE-REACH **K ≈ 5–6
passes**; past K the residual log2(T) − 2.5 − 64/N bits/record is the unpayable
remainder, growing without bound, paid in `structure (the free 2.5)` until
exhausted and thereafter unpaid (i.e. forcing either `stored bits` = tags, or
`match-supply` loss if one tries to couple via a biased hash, or `wrap/carriage`
if one tries a growing board). **No currency is free past K. The impossibility
is sharp and the single assumption it hinges on is the uniform hash law.**

**Evidence-class note on K.** The *existence* of a finite max-free-reach K — and
the impossibility of a free unbounded content-blind birth channel — is
**proven-by-math** (the §3/§8 counting reductio, independent of any measurement).
The *specific value* K ≈ 5–6 inherits **measured** status from the borrowed
2.5-bit explosion number (Result-Ledger row 7): I did not re-derive 2.5 (a toy
re-measure at few candidate passes would be luck-bound and would not sharpen the
theorem). So read "a finite K exists and the residual grows as log2(T) − 2.5 −
64/N" as proven; read "K ≈ 5–6" as proven-given-the-measured-2.5.
