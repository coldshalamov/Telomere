# Avenue A — Modular-orbit / affine-stride epochs for SINGLES

**Result: SHARP IMPOSSIBILITY (for the orbit channel) + a quantified reach
K ≈ 6 carried entirely by the explosion check, with the orbit contributing
exactly 0 bits.**

Toy: `model_analysis/birth_channel_research/A-modular-orbit_invariance.py`
(deterministic permutations + one tiny multiplicative field; no SHA
match-hunting — this is a counting/logic result, not a luck test).

---

## HYPOTHESIS (written before testing)

The affine-stride fingerprint gives *bundle* birth epochs because a bundle
spans ≥2 slots and the shuffle moves its children apart at a stride that
encodes how many passes have acted on it. A single (arity-1) has no span, so
no stride — but it *does* have a trajectory through the board. The hope:

> A prime-field shuffle `i → g·i mod p` (g a generator), or affine
> `i → a·i + b mod Q`, makes a single's birth pass `t` readable from its
> **orbit phase** at decode (e.g. discrete log of `current_pos / x`), with
> zero stored bits — and even if it doesn't pin `t` exactly, it might narrow
> the candidate births to ≤ 6 so the free explosion check (~2.5 bits) can
> finish the job.

**What I expected from the mechanics, before running anything.** I expected
this to FAIL, and to fail for one specific reason: a length-preserving single
occupies its original slot `x` for the *entire* run — it is a literal in that
slot before pass `t` and a record in that slot from pass `t` on. "Becoming a
record" is an in-place relabel, not a move. The shuffle acts on *positions*
identically whether the item is a literal or a record. So the single's
position at pass `j` is `σ^j(x)` for **all** `j`, with no dependence on `t`.
The orbit phase is therefore a function of `(x, number-of-passes-applied)`
only — and both of those are already derivable at decode (`x = σ^{-T}(final)`
self-presenting; `T` from the header-hash trial). A signal that is a function
of only already-known quantities carries **zero** new bits. I expected the
discrete-log reading to return `T`, not `t`, for exactly this reason.

This is the same structural fact the repo already half-concedes:
`v1_roundtrip_proof.py` keys singles by **original slot** `H(seed, slot)`
(lines ~104–111) and the decoder recovers `x = sig_pow(bwd, slot, T_try)`
with **no `k` anywhere** (lines ~165–170). That is the codebase saying singles
carry no birth pass. My contribution is proving the orbit cannot restore it.

---

## MECHANISM (precise construction tested)

- **Board:** fixed-size, `M` items (constant-N, the maintainer's PCTB fix —
  the board never grows, so no per-pass address tax; cf. `pctb_ledger.py`).
- **Shuffle (spec / Golden Config):** `σ(i) = (walk(5i mod P) + 1) mod M`,
  exact inverse `shift back, multiply by 5^{-1}, walk`. (`shuffle_rules_eval.py`
  confirms bijective + zero repeated neighbor pairs.)
- **Pure-field variant (best case for the dlog read):** `σ(i) = g·i mod p`,
  `g` a generator of `Z_p^*`. Position after `j` shuffles = `g^j · x mod p`.
- **Single birth:** at pass `t`, slot `x` flips from literal to a record
  `[arity-1 codeword][Lotus seed]`; salt is the self-presenting current
  position; the item keeps shuffling like everything else.
- **Proposed birth channel:** read `t` from the orbit phase of the single's
  final position — e.g. `t ?= dlog_g(final_pos · x^{-1})`.

---

## THE MATH (proven-by-math)

Let `σ` be the per-pass position permutation. A single born at pass `t` and
slot `x` sits at position

    p_j(x, t) = σ^j(x)      for every pass j = 0, 1, …, T,

**independent of `t`**, because the literal→record flip is in-place and `σ`
is applied to positions regardless of item type. Therefore the final position
is `f = σ^T(x)`, a function of `(x, T)` only.

For the multiplicative field, `f = g^T · x mod p`, so

    dlog_g(f · x^{-1} mod p) = T   (mod ord g),

which is the **total pass count**, already known from the header-hash trial —
never the per-record birth `t`. The affine map `i → a·i + b` has the same fate
(its orbit phase is again a function of the number of applications `T`, shared
by every item, not of any per-item birth).

**Capacity argument (the counting gate, formalised).** The orbit phase is a
deterministic function `Φ(x, T)`. The decoder already holds `x` (self-present)
and `T` (header). Mutual information between the birth pass `t` and a quantity
that is a deterministic function of variables the decoder already has is
`I(t ; Φ(x,T) | x, T) = 0`. The orbit is **not a channel** — it has zero
capacity for `t`. Equivalently: the births are i.i.d. uniform hash outcomes
(`MATH_MODEL §1`); the orbit map is fixed and content-blind, so it cannot be
correlated with which uniform draw landed when. There is nothing for it to read.

---

## TOY OUTPUT

`A-modular-orbit_invariance.py`, five parts, all pass.

**Evidence-class honesty note.** The load-bearing proof is the **math above**
(capacity = 0) and **part 2** (a genuine construction: real modular arithmetic
+ discrete log). Parts 1 and 3 are *illustrations* of the proven-by-math fact,
made non-tautological by part 0 (a falsifiability guard) — they are NOT
independent proofs. Earlier drafts overstated them; corrected here.

0. **FALSIFIABILITY GUARD** (two-speed rule, M=53, T=10): under a *t-dependent*
   move rule (records hop twice, literals once) the single's own trajectory
   genuinely **diverges** by birth `t`. This proves part 1 is a real
   construction — the spec's single-speed rule makes it `t`-invariant, a
   two-speed rule would break it. **proven-by-construction.**
1. **INVARIANCE** (spec shuffle, M=53, T=40): the item is given a payload whose
   *type* flips literal→record at birth `t`, and the move function is handed
   each item's type (so a two-speed rule would diverge — see part 0). For every
   slot `x` and every birth `t ∈ 1..40` the trajectory is byte-identical
   (mismatches = 0). **proven-by-construction** that the spec is single-speed;
   *illustrates* the proven-by-math invariance.
2. **DISCRETE-LOG READS T, NOT t** (mult field p=53, g=2, T=11):
   `dlog(final · x⁻¹) = 11 = T` for births `t ∈ {1, 5, 11}` alike; `x` is
   recovered exactly. The orbit observable conveys **0 birth bits**. This is
   the substantive construction. **proven-by-construction + proven-by-math.**
3. **NO DISCRIMINATOR** (spec shuffle, M=53, T=40): the birth salt the decoder
   needs is `σ^{t-1}(x)`, and these candidate salts are genuinely **distinct**
   across `t` (40 distinct values — so the wrong `t` expands against the wrong
   salt and yields wrong bytes, exactly the dispute in THE_OPEN_QUESTION). But
   the only orbit-observable, `f = σ^T(x)`, is `t`-free, so it supplies a
   **0-bit discriminator** among those `log2(T) ≈ 6` candidates. *Illustrates*
   the proven-by-math capacity result.
4. **HINGE** (counterfactual freeze, M=53, T=12): IF the single were frozen
   until birth then moved for `T−t` passes, final position WOULD be distinct
   across all 12 births — so phase *would* carry `t`. This is the boundary of
   the impossibility, and it is **avenue F, not lane A** (see below).
   **proven-by-construction** (separation) + **proven-by-math** (its costs).

---

## CURRENCY ACCOUNTING

The avenue's central claim was "free in stored-bits." The honest finding:

| component | currency | bits |
| --- | --- | --- |
| orbit phase signal for birth `t` | (no currency — empty channel) | **0 conveyed** |
| disambiguating birth across passes | `structure (free ~2.5 bits)` | ≈ 2.5 bits/record (explosion check), standalone |
| net birth-bill payment by the orbit | none — the bill is **not paid here** | 0 |

The orbit is free and content-blind but has **zero capacity** for birth pass.
The precise statement: the decoder must choose among `T` candidate birth salts
`σ^{t-1}(x)`, which are genuinely **distinct** (wrong choice → wrong bytes);
the only orbit-observable, `f = σ^T(x)`, collapses to `(x, T)` and so provides
**no free discriminator** among them. Lane A neither pays the birth bill nor
leaks: it does nothing for the problem. The working part of deep decode that
survives is the **explosion check's ~2.5-bit structure budget**, which
disambiguates ~5–6 candidate passes on its own. Reach **K ≈ 6**, with the orbit
contributing **0**. To go past K you must spend a real currency: `stored-bits`
(priced ≥ log2 T ≈ 2 bits, net negative past pass ~6) or `match-supply` (the
avenue-E period-schedule trap: geometric starvation, ~2× supply loss per bit).

---

## COUNTING-GATE ANSWER (mandatory)

**Q: If this mechanism were free + content-blind, would arbitrary random data
net-compress without bound?**

**A: No — and crucially, NOT because a finite resource throttles a real
channel, but because the orbit is not a channel at all.** The orbit phase is a
deterministic function `Φ(x, T)` of quantities the decoder already holds
(`x` self-presenting, `T` from the header). It therefore carries **zero bits**
about birth pass `t`: the candidate birth salts `σ^{t-1}(x)` differ across `t`,
but the only observable `f = σ^T(x)` is `t`-free, so it cannot discriminate
among them. There is no leak to localise because nothing is conveyed: random
data does not net-compress under it because it conveys none of the
`Σ_records log2 T` birth bits that compounding would require. The finite
resource that bounds the *working* part of deep decode (the explosion check)
is `structure (free ~2.5 bits)`, capping reach at **K ≈ 6** — and the orbit
does not extend that cap by even one bit.

**The single hinge assumption** (avenue-H discipline): the impossibility rests
on **(single length-preservation) AND (every item moves every pass)**. Relax
*either* and trajectory becomes birth-dependent:
- **Freeze-until-birth** (the only relaxation that helps): the single does not
  move until born, then moves for `T−t` passes, so `f = σ^{T−t}(x)` and the
  phase encodes `t`. **But** (toy part 4) this (i) is **avenue F**
  (frozen/two-speed boards), not the modular-orbit idea; (ii) **breaks
  freshness** (proven) — frozen literals get no new neighbors, so their match
  supply never refreshes, destroying the property the channel was meant to buy;
  and (iii) appears **circular** (conjecture) — to apply the correct reverse
  shuffle per pass the decoder must already know, for each item, whether it was
  frozen (literal) or live (record) at that pass, i.e. its birth pass, the very
  unknown; whether keep-what-decodes can trial past this is unproven. The birth
  bill reappears in `match-supply` (proven) + possibly `compute/circularity`
  (conjectured), not free.

So the orbit channel for singles is a clean **sharp impossibility**: zero
capacity, content-blind, by deterministic-function-of-known-inputs.

---

## EVIDENCE CLASSES

The headline impossibility is **proven-by-math** (capacity = 0:
`I(t ; Φ(x,T) | x, T) = 0`). The constructions support it; only part 2 is an
independent construction.

- Orbit phase = function of (x, T) only, so 0 birth bits: **proven-by-math**
  (the capacity argument; `f = σ^T(x)`).
- Discrete log recovers T not t: **proven-by-construction + proven-by-math**
  (toy part 2; real modular arithmetic + dlog → T).
- Trajectory invariance across birth labels: **proven-by-construction** that
  the spec is single-speed (toy part 1, made non-tautological by the part-0
  falsifiability guard which shows a two-speed rule diverges); *illustrates*
  the proven-by-math invariance — NOT an independent proof.
- Candidate birth salts distinct but orbit gives 0-bit discriminator:
  **proven-by-construction** (toy part 3, 40 distinct salts) *illustrating*
  **proven-by-math** (capacity = 0).
- Freeze-hinge boundary: **proven-by-construction** (toy part 4, phase
  separation across births). Its costs split by class:
  - *freshness loss* (frozen literals get no new neighbors → match supply does
    not refresh): **proven-by-math** (direct consequence of the shuffle def).
  - *decode circularity* (decoder needs birth pass to pick the reverse shuffle):
    **conjecture** — I suspect keep-what-decodes cannot escape it cheaply, but
    there is no proof the trial-decode space necessarily explodes.
- Reach K ≈ 6 = the explosion check's standalone budget: **measured** upstream
  (Result-Ledger row 7 / PLAIN_STATUS, ~2.5 bits/record); the orbit's
  contribution of 0 is this finding.

---

## NEXT (single most promising sub-idea)

Lane A is closed for singles by the invariance theorem; the orbit cannot be
revived without freezing, which is avenue F. The most promising *adjacent*
sub-idea is **avenue F done carefully**: a two-speed board where records move
on a slower clock than literals, engineered so the fast/slow *gap* is itself
self-presenting at the reverse step — but this must first defeat the
circularity surfaced here (the decoder needs record-vs-literal status to pick
the clock, before it has opened the record). If that circularity cannot be
broken (I suspect it cannot, by the same content-blindness argument), then
F collapses into the same impossibility and the standing answer is: **birth
pass for singles is conveyable only by paying stored-bits or match-supply;
the only free source is the explosion check, K ≈ 6.**
