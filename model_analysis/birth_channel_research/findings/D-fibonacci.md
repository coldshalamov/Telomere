# Avenue D — Fibonacci / Zeckendorf / Lucas bounded registers

**Researcher lane:** number-theoretic addressings where "how many times
shuffled since birth" leaves an additive/shift signature. Zeckendorf reps are
unique and shift-structured. Does a Fibonacci-stride shuffle make
pass-count-since-birth readable mod something, cheaply?

**Date:** 2026-06-13. Evidence classes labelled inline.

---

## 0. The question, restated in this lane's terms

The wall (THE_OPEN_QUESTION / BRIEF): a content-blind, deterministic,
sub-2-bit channel that conveys each record's BIRTH PASS at decode, for
**arity-1 singles** in particular. Singles are length-preserving (1->1) and
isolated (one slot, no span), so they have no stride to fingerprint the way a
bundle's k children do.

This lane's bet: maybe the *number-theoretic structure of the address itself*
carries the birth pass. Concretely:

- A Zeckendorf representation Z(n) = sum of non-consecutive Fibonacci numbers
  is unique. "Fibonacci shifts" act on Zeckendorf strings in a structured way
  (the Fibonacci/golden-ratio shift, Zeckendorf "left-shift" ~ multiply by
  phi). If a pass's shuffle were a Zeckendorf shift, then "number of shifts
  since birth" might be an additive register readable from the final address.

---

## 1. HYPOTHESIS (written BEFORE any test)

I expect this lane to return a **sharp impossibility for the free/unbounded
claim**, with reach not exceeding the already-known explosion check (~5-6
passes, ~2.5 free bits/record). My reasons, from the mechanics, before testing:

**(H1) Bijectivity gives a single exactly ONE equation, and one equation
cannot pin two unknowns.** A single keyed by position-at-birth sits, after the
remaining shuffles, at `p_final = sigma^(T-t)(p_birth)`. The decoder observes
ONE number `p_final`. The unknowns are TWO: the birth pass `t` and the birth
position `p_birth`. Because sigma is a bijection (required for reversibility),
for EVERY candidate `t in {1..T}` the decoder can compute a *distinct, legal*
`p_birth = sigma^(-(T-t))(p_final)`. No candidate t is ever positionally
excluded. The birth-pass signal is therefore not "smeared by further
shuffling" — **it was never in the position to begin with.** This is exactly
why bundles are solved (k children = k equations = pins t, the affine-stride
fingerprint) and singles are not. Fibonacci structure does not add equations
to a single: the digits of one Zeckendorf number are *one number*, not k
independent observations.

**(H2) The hash is blind to Zeckendorf structure.** CLAUDE.md states it: a
hash matches any output with equal probability regardless of structure.
`H(seed, Z(p))` is exactly as uniform as `H(seed, p)`. So whatever
"shift-structure" Zeckendorf reps have is invisible at the one point where it
would have to pay off — the salt fed to SHA. Zeckendorf can matter ONLY in the
decoder's position-unwinding arithmetic; and (H1) kills it there, because
unwinding is bijective regardless of how addresses are written.

**(H3) The only place a finite K could hide:** make wrong-`t` unwindings land
on *illegal* positions. That needs (a) a legal-birth **sublattice** — only
"Zeckendorf-special" slots may host a newborn single — plus (b) a shuffle
sigma whose phase relative to that sublattice is `t`-readable. I predict this
fails the counting gate: a free readable `birth-pass mod m` with m>=T would
make every single's fresh salt decodable -> unbounded compounding on RANDOM
data -> pigeonhole violation. So it cannot be free; the bill reappears as
either stored phase-reference bits (= the priced tag baseline) or match-supply
starvation (constraining births to the sublattice throws away lottery
tickets). I expect to NAME which, not escape it.

**Predicted result:** sharp-impossibility (free/unbounded), reach K bounded by
the explosion check (~5-6), currency = stored-bits OR match-supply depending
on which sub-construction. Fibonacci adds **nothing free** on top of the
explosion check.

**What would refute my hypothesis:** an orbit/phase structure of a *valid*
Fibonacci Telomere shuffle that yields a global phase homomorphism
`phi(sigma p) = phi(p) + 1 mod m` with m >= T, AND a birth-position reference
that is itself free (not content-dependent). I will test for exactly this
before committing.

---

## 2. THE MATH (proven-by-math, before any code)

### 2.1 The single's decode equation (one equation, two unknowns)

A single is born at pass `t` at some array position, keyed (per SPEC §1 and
`v1_roundtrip_proof.py` lines 102-112) by its **original slot** `x`. The
shuffle `sigma` is applied once per pass, so an item present from pass 0 sits,
after all `T` passes, at array position `p_final = sigma^T(x)`. The decoder
(line 167: `x = sig_pow(bwd, slot, T_try)`) recovers `x = sigma^{-T}(p_final)`.

Crucially: **the birth pass `t` never enters this equation.** A slot-keyed
single decodes with ZERO birth information — confirmed by T5 below
(planted single, real SHA, exact round trip, decode never references t0=7).

That is exactly why the slot-keyed single is *already decodable* — and exactly
why it is the WRONG channel for the wall: a slot-keyed single uses ONE dice
sequence per slot (`H(seed, x)`, no pass), so it **exhausts at D\*** (MATH_MODEL
§6: "birth-free and decodable forever, but one dice sequence per slot... a
bounded opening channel"). It is not fresh dice.

For FRESH dice (the sustained match rate of BRIEF piece 1) a single would have
to be keyed `H(seed, x, t)` — and then decode needs `t`. The observable is the
single number `p_final`. The unknowns are `(t, x)`. **One equation, two
unknowns.** Because `sigma` is a bijection (mandatory for reversibility), for
every candidate `t in {1..T}` the decoder gets a perfectly legal, distinct
`x_t = sigma^{-(T - t_offset)}(p_final)`. No candidate is positionally excluded.

> **Lemma (position-phase death).** For any bijection sigma and any single
> observed at `p_final`, the set of (birth-pass, birth-position) pairs
> consistent with `p_final` has exactly one element per candidate birth pass.
> Hence `p_final` carries **0 bits** of information about the birth pass.
> *Evidence: proven-by-math; confirmed by construction in T1 across
> M in {13,21,34}, g in {5,8}, T=40.*

This is the heart of the lane. Fibonacci adds nothing because the digits of
ONE Zeckendorf number are ONE number, not k independent observations. A
bundle's k children supply k equations (the affine-stride fingerprint, already
solved); a single supplies one. No re-addressing changes the count of
equations.

### 2.2 The hash is blind to the address's number theory

SPEC §0 / CLAUDE.md: a hash matches any output with equal probability
regardless of structure. `H(seed, Z(p))` is exactly as uniform as
`H(seed, p)`. So Zeckendorf's shift-structure is invisible at the salt — the
one place it would have to pay off. It can only live in the decoder's
position-unwinding arithmetic, and §2.1 shows unwinding is bijective regardless
of how addresses are written. *Evidence: proven-by-math (uniform-hash
assumption, MATH_MODEL §1).*

---

## 3. THE TESTS (artifact: `D-fibonacci_counting.py`, pure counting + 1 planted SHA round-trip)

### T1 — position-phase death (the core impossibility)
For M in {13,21,34}, g in {5,8}, T=40: every candidate birth pass t unwinds to
a legal, distinct birth position. **None is excluded.** Position carries 0 bits
about t, for every bijection. *proven-by-construction.*

### T2 — is the "Zeckendorf left-shift" even a valid Telomere shuffle?
The multiply-by-phi / Zeckendorf-index-shift map is **NOT a bijection mod M**
(measured: `bijection=False`, 1 fixed point, collisions at M=13,21,34). It
fails the shuffle gate outright (and the advisor's note: a pure additive stride
`i->i+F_k` keeps i,i+1 adjacent — no neighbor refresh). So the literal
"Fibonacci-stride shuffle" of the lane prompt is not even admissible. The valid
Fibonacci-flavored shuffle is multiplicative with a Fibonacci/Lucas generator g
(e.g. g=8 or g=13), tested in T3/T5. *measured.*

### T3 — orbit / phase homomorphism (the steelman for a finite K)
A valid multiplicative shuffle `i -> g*i mod P` walked decomposes into cycles.
A *global* additive phase `phi(sigma p)=phi(p)+1 mod m` exists only when one
cycle covers all movers; then m = that cycle length. Measured:
- M=21,g=5: cycles [1,20], global m=20.
- M=34,g=13 (Fibonacci g): cycles [1,33], global m=33.
- M=21,g=8: cycles [1,9,11] — coprime orbits, only partial (CRT) phase.

So a phase register of size m up to ~M *does* exist. **But it is a phase
RELATIVE TO A REFERENCE.** To read "passes since birth" you need
`phi(p_final) - phi(p_birth) mod m`. `phi(p_final)` is free (you see it). But
`phi(p_birth)` is the phase of the **birth position**, and a single is born
wherever an unmatched literal happened to sit — a content-uniform position.
**The reference `phi(p_birth)` is not free: it is `log2(m)` stored bits per
record, i.e. the priced-tag baseline** (THE_OPEN_QUESTION: "Global pass
counter: 16 bits total cannot carry per-record answers"; tags cost
>= log2(passes)). The phase exists; the reference doesn't come for free.
*measured + proven-by-math.*

### T4 — legal-birth sublattice (secondary route; CAVEAT: not a measurement)
Steelman: confine newborn singles to a Zeckendorf-special sublattice so wrong-t
unwindings land illegal and get excluded. The toy prints, for M=34,55,89, T=40,
a `bits_bought` vs `supply_bits_paid` comparison with paid > bought at every M.

**Honesty flag (caught in review):** the inequality
`bits_bought < bits_paid` reduces algebraically to `f < 1`
(`Tf < 1 + (T-1)f` for legal-fraction `f`), which is forced for ANY `f<1, T>1`.
It is NOT a measurement of supply economics and does NOT reproduce the
avenue-E "~2x per bit" mechanism — it merely restates that a sublattice has
`f<1`. I therefore do NOT lean on T4's numbers. It is recorded as intuition
that the sublattice route also fails; the airtight kill is the stored-bits
argument (§2.1 + §4), not this. *NOT measured — algebraically forced;
labelled as such.*

### T5 — mechanics sanity (real SHA, planted)
A planted slot-keyed single round-trips exactly under a Fibonacci-generator
shuffle (g=8): decoder recovers original slot 13 via `bwd^T`, salt matches,
block recovered exactly — **without ever using the birth pass**. Confirms the
slot-keyed single is decodable and k-free, and that Fibonacci-g is a valid
reversible shuffle — but this is the bounded one-shot channel, not fresh dice.
*proven-by-construction.*

---

## 4. THE COUNTING GATE (mandatory)

**Q: If a Fibonacci/Zeckendorf birth-pass channel were free + content-blind,
would arbitrary random data net-compress without bound?**

**A: Yes — therefore it has a leak, and there is no free channel here.** A free
readable birth pass would make every single's fresh salt `H(seed, x, t)`
decodable. Fresh dice + free decode for singles = unbounded compounding
(MATH_MODEL §6: fresh dice cross below original size and earn without bound).
On RANDOM data that is a pigeonhole violation (maps 2^n inputs to fewer
outputs). So the channel cannot be free. The bill is paid in **stored-bits**,
and the argument is airtight:

**The decoder already owns the single's ENTIRE position trajectory for free.**
By T5 it has `x = sigma^{-T}(p_final)`; it has `sigma`; it has `T`. So
`sigma^j(x)` for every `j` is free, and therefore EVERY position-derived
quantity is already in the decoder's hand for free: the orbit phase, the
Zeckendorf digits of every position the item ever occupied, the T3 phase
homomorphism value — all free.

**The birth pass `t` is logically independent of that entire trajectory.** `t`
is the index of a CONTENT event — the pass on which the lottery first hit this
slot. The position trajectory `(x, sigma(x), sigma^2(x), ...)` is *identical*
whether the slot was first matched at `t=3` or `t=30`. Two files differing only
in when a given slot's single was born have the SAME position trajectory and
DIFFERENT `t`. Hence **no function of position can carry `t`** — they are
independent variables. Conveying `t` costs its own entropy: `log2(T)` stored
bits per record. That is the priced-tag baseline (THE_OPEN_QUESTION: tags
>= log2(passes), net-negative past pass ~6). The metadata contract (SPEC §0)
forbids storing it; nothing derives it.

This makes T3's phase homomorphism a clean **red herring**, not a near-miss:
the phase is free, but `t` is independent of the phase, so the phase is
useless for reading `t`. The earlier "phi(p_birth) isn't free" framing
understated it — the truth is `t` isn't a position function at all.

*(Secondary route, the legal sublattice of T4, would pay in match-supply
instead — but its toy inequality is algebraically forced, §3-T4, so the
load-bearing kill is the stored-bits argument above.)*

**Where Fibonacci's reach actually sits:** Fibonacci adds NO free bits on top
of the explosion check. The free reach K of this lane = the explosion check's
own reach, ~5-6 passes (~2.5 bits/record), because the only content-blind free
discriminator available is non-explosion, and Zeckendorf structure does not
extend it (it cannot — §2.1 Lemma). So K ~= 5-6, unchanged.

---

## 5. RESULT

**sharp-impossibility (free / unbounded), reach K ~= 5-6 (explosion check
only; Fibonacci adds zero free bits).**

The single assumption it hinges on: **`sigma` is a bijection** (mandatory for
reversibility). Relax that — a non-injective "shuffle" that maps birth
positions of different passes to disjoint position-classes — and a single's
position WOULD carry birth-pass bits. But a non-bijection is not reversible, so
it breaks decode globally. Equivalently: the impossibility hinges on the same
bijectivity that the whole machine needs to run. This is the cleanest statement
of the singles wall in number-theoretic-addressing terms: **you cannot get k
equations from a 1->1 record by rewriting its single address, however clever
the number theory.**

| field | value |
|---|---|
| currency | stored-bits (primary, airtight); match-supply (secondary, sublattice route) |
| currency_bits | log2(T) ~= 5-6 stored bits/record for the birth-pass index directly (t is independent of the free position trajectory, so it is the index itself, not a phase reference) |
| evidence_class | proven-by-math (Lemma §2.1 + independence argument §4) + proven-by-construction (T1,T5); T2,T3 measured; T4 algebraically-forced, not relied on |

**NEXT:** The phase homomorphism in T3 is interesting *for bundles*, not
singles: a bundle already has k>=2 equations; could a Fibonacci-orbit phase
sharpen the affine-stride fingerprint's reach or reduce its fork count? That is
the one place Fibonacci structure might pay (more equations available), and it
sidesteps this lane's impossibility (which is specifically about the 1-equation
single). Worth a focused check against `v1_roundtrip_proof.py`'s fork counts.

