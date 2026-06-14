# Avenue G — Parity / sign channels (≤1 bit, derivable)

Lane owner: birth-channel research subagent.
Target: a ≤1-bit-per-record DERIVABLE signal (slot parity under an involution,
or a sign under a reflection) that, combined with the explosion check
(~2.5 free bits), extends reach by one more bit cheaply. Quantify exactly how
many derivable bits a reversible shuffle can leak per record without storing
anything, and whether they correlate with birth pass at all.

---

## HYPOTHESIS (written BEFORE any test)

**What I expect, and why, from the mechanics.**

The decoder, at the moment it considers a record sitting at final slot `s`, can
compute ANY deterministic function of:
- `s` (the final slot, free — it is reading the wire in order),
- `N`, `B`, the header,
- the public shuffle rule σ and its inverse,
- the trial pass count `T_try`.

A "parity / sign channel" would be: pick an involution or reflection ρ on the
board; the value `ρ`-parity of the record's slot is a 1-bit derivable label.
The question is whether that 1 bit can be made to **equal a bit of the record's
birth pass** without the encoder storing anything.

My prediction, from the conservation principle:

1. **A reversible shuffle leaks exactly ZERO bits about birth pass per record,
   for a single (arity-1) record.** Reason: the decoder already knows the final
   slot `s` for free (it is reading the wire). Any "derivable bit" it computes
   from `s` is a *deterministic function of `s`* — it carries information the
   decoder ALREADY HAS (the slot), not new information about `t`. A function of
   a known quantity is not a channel; its mutual information with the unknown
   (birth pass) is whatever correlation the encoder built in — and the encoder
   cannot build in correlation without either (a) moving the record to a slot
   chosen by `t` (which costs arrangement bits — PCTB position tax, the
   `wrap/carriage` currency), or (b) refusing to place records whose `t` does
   not match the slot's parity (which kills hit supply — the `match-supply`
   currency, geometric starvation).

2. **The slot itself already determines the single's birth pass via σ^−T — but
   only once T is known.** For singles the decoder uses `x = σ^−T(s)` (original
   slot, key-free). So the single's *salt* is recoverable without birth pass.
   But the SALT-REFRESH problem (the actual wall) needs the pass `t` to pick the
   pass-varying key `H(seed, t)`. The final slot `s` is a deterministic image of
   the original slot under σ^T — it tells you nothing about WHICH t, because
   every record, regardless of birth pass, ends up shuffled by the SAME number
   of remaining passes (T − t passes after birth, but then it sits, and the
   total applied to its final position is determined by T and where it was born;
   the decoder cannot separate "born early, shuffled more" from "born late,
   shuffled less" from the slot alone — that is exactly the open question in
   THE_OPEN_QUESTION.md, "one unshuffle short of home").

3. **Therefore a parity bit derived from the slot is REDUNDANT with the slot,
   not a new channel.** Expected information about birth pass: 0 bits. The
   correlation a parity channel could carry is bounded by H(birth pass | slot),
   and for the salted machine the slot does NOT pin the birth pass (that is the
   wall), so a function of the slot cannot pin it either. Data-processing
   inequality: I(t ; f(s)) ≤ I(t ; s), and I(t ; s) is the very quantity the
   wall says is ~0 for a content-blind uniform-hash engine.

4. **Where a parity bit CAN do real work: amplifying the explosion check by
   ruling out HALF the candidate passes — but only if the encoder PAYS for the
   correlation.** If the encoder only accepts a single at pass `t` when
   `parity(birth_slot) == bit(t)`, then at decode a derived parity rules out the
   passes of the wrong parity → the explosion check's 2.5 free bits now cover a
   denser candidate set. BUT this is exactly avenue E's LEAK: a parity gate on
   acceptance halves the per-pass acceptance probability → `match-supply`
   currency, ~2× supply loss per bit gained (the measured geometric-starvation
   penalty). Net reach gain after charging supply: I predict ≤ 0 or marginally
   negative — you buy 1 bit of disambiguation at the cost of 2× fewer matches,
   and a "win" worth ~2 bits cannot pay a 2× supply tax to save <1 pass of
   explosion-budget.

**Predicted RESULT: refuted / sharp-impossibility for the free-and-unbounded
version; the only non-trivial residue is a quantified marginal reach that the
counting gate kills (supply currency).** A slot-derived parity bit is free but
content-blind-redundant with the slot (0 bits about birth pass); an
acceptance-gated parity bit is correlated with birth pass but paid in
match-supply at the avenue-E rate.

**Counting-gate pre-answer:** A free, content-blind parity bit that genuinely
conveyed 1 bit of birth pass per record would let random data net-compress
without bound (combine with explosion check → every record's birth pass for
~3.5 bits, but birth pass needs log2(T) bits and the WINS are only ~2 bits, so
even 3.5 free bits/record applied to T up to ~11 passes... must check the
arithmetic). The leak, if the channel were real, is that the parity bit is a
deterministic function of a slot the decoder already reads — so it conveys 0
NEW bits. No pigeonhole violation because there is no new information: it is the
slot, relabeled.

---

## Tests to run (to confirm or refute the above)

T1. **Exact counting / DPI argument** (proven-by-math): formalize
    I(t ; f(s)) ≤ I(t ; s) and compute I(t ; s) for the salted single under the
    uniform-hash law.

T2. **Toy measurement** (measured): build the actual shuffle σ = (5i mod P)+1,
    run records born at known passes, and measure the empirical mutual
    information between any slot-parity/sign function and the birth pass. If it
    is ~0, the free channel is refuted by construction.

T3. **Acceptance-gated variant** (measured + math): if a parity gate is imposed
    on acceptance, measure the supply loss and net the reach against avenue-E's
    2× penalty.

---

## THE EXACT RESULT (sharpened past the hypothesis — proven-by-math)

The hypothesis said "≈0 because the wall." The mechanics give something
**strictly stronger and exact: I(birth-pass ; any derivable slot-function) = 0,
identically, for arity-1 singles.** The wall is not invoked; this is proven from
the shuffle's own structure.

### The decoupling lemma (proven-by-math)

Setup, from SPEC §1 and `v1_roundtrip_proof.py` (encoder loop:
`arr = apply_shuffle(arr, fwd)` runs every pass for **every** item, matched or
not):

- A **single** (arity-1 record) is length-preserving, 1 item → 1 item. Once
  born it occupies exactly one slot and is permuted by the global shuffle σ on
  **every subsequent pass, identically to a literal**. There is no "frozen"
  state in V1: matched and unmatched items move the same way.
- Therefore a single whose original slot is `x` sits, after all `T` passes, at
  final slot

      s = σ^T(x).

  This depends on `x` and `T` **only**. The birth pass `t` does **not** appear:
  whether the item became a seed-record on pass 2 or pass 30, it was at slot `x`
  the whole time (a single never changes slot by being born — it replaces the
  literal in place) and got the same `T` applications of σ. (This is exactly the
  reason singles are key-free in the spec: original slot `x = σ^−T(s)`, no `k`.)

- **Birth pass is set by the lottery, not by position.** Under the uniform-hash
  law (MATH_MODEL §1), `P(match) = 2^−S` per (seed, key) trial, independent of
  position. Hit-*time* is therefore independent of slot: **t ⊥ x**.

- σ is a bijection on the board (`shuffle_rules_eval.py`: `mult_prime` +1 is an
  exact permutation), and the size schedule is decoder-derivable, so `s` is a
  bijective relabeling of `x` given public information. A bijection of `x`
  carries exactly the information `x` carries about `t`, which is none:

      I(t ; s) = I(t ; x) = 0   (since t ⊥ x).

- **Data-processing inequality.** For ANY deterministic, decoder-derivable
  function `f` of the slot (parity, reflection-sign, orbit-phase parity, residue
  mod anything, ...):

      I(t ; f(s)) ≤ I(t ; s) = 0   ⟹   I(t ; f(s)) = 0.

  Parity and sign are just two ≤1-bit projections of `s`; they are **subsumed**.
  The result is not "parity happens to give 0" — it is "the shuffle decouples
  position-evolution from birth-time, so **no** function of the final slot can
  carry **any** birth-pass bit, at any width."

**Evidence class: proven-by-math** (derivation above), **confirmed
proven-by-construction** by the toy below.

### The single hinge the impossibility rests on (avenue-H deliverable)

> **Assumption:** *a matched single's position evolves identically to a literal's
> — position evolution is independent of birth pass.*

This is the ONE thing to relax. It is precisely avenue F (frozen-record /
two-speed boards): if born singles stop moving (or move on a slower clock),
then `s` becomes a function of `t` (how long it has been frozen), so
`I(t ; s) > 0` and a slot-parity bit DOES carry birth information. But the
coupling that creates the correlation is exactly what must then be paid for in
**carriage** — a two-speed board needs the decoder to know the clock-gap, which
is the PCTB position-tax currency again (board must encode who froze when). So
the parity channel cannot be free AND informative simultaneously: free ⟺
decoupled ⟺ 0 bits; informative ⟺ coupled ⟺ paid in carriage. (Hand off the
coupled case to avenue F; it is out of lane G's "free derivable" scope.)

### Why "parity + explosion check extends reach by one bit" FAILS — head on

The lane premise was: parity adds one bit on top of the explosion check's
~2.5 free bits. It does not, for a precise reason:

- The **explosion check** extracts birth-pass information from **content
  structure** — does the wrong-salt expansion parse as self-delimiting items /
  pass the checksum (the `structure-free ~2.5 bits` currency). Its input is the
  *bytes*.
- **Slot parity** offers birth-pass information from **position**. Its input is
  the *slot*.
- Position carries **0** birth-pass bits (lemma above). So the combination adds
  **0**: reach stays at the explosion check's ~5–6 passes.

**The combine claim needs the CONDITIONAL quantity, not the marginal.** The lane
asks about `I(t ; parity(s) | explosion-check output)`. Marginal independence
`I(t ; parity(s)) = 0` does **not** by itself imply conditional independence
(canonical trap: A,B independent bits, C = A⊕B ⟹ I(A;B)=0 but I(A;B|C)=1). The
correct foundation is **joint independence**:

> **t ⊥ (x, content).** Under the uniform-hash law the per-trial match
> probability is 2^−gap regardless of BOTH position and target bytes, so the
> first-success pass is geometric with the *same* law for every block,
> independent of where it sits and what it contains.

The independence from *content* holds because the explosion check's information
comes from **decode-time parse-failure of wrong-salt expansions** — a property
of the seed→digest map at trial passes, NOT of the block's original bytes. There
is no back-channel coupling `t` to content. From `t ⊥ (x, content)`: parity is
`f(σ^−T(slot)) = f(x)`, a function of position only; conditioning on any function
`g(content)` (the explosion check's output) leaves `t ⊥ f(x) | g(content)`,
because `t` is independent of the joint `(x, content)`. So

      I(t ; parity(s) | explosion-check) = 0.

The explosion check reads the **seed-expansion coordinate**; parity reads the
**position coordinate**; position is decoupled from birth-time, so they do not
interact. No extension, and not even a cheapening of the existing check.

This does NOT contradict the working explosion check: that channel's birth-pass
information is content-/structure-derived (parse-failure at wrong salts), while
this lane is position-derived; position contributes 0 in the joint. No conflict.

### Toy confirmation (proven-by-construction)

`G-parity-sign_mi_check.py` — content-blind by construction (birth passes drawn
**independently** of slots, modeling t ⊥ x; coupling them would be content-
awareness, forbidden by SPEC §0). Real V1 shuffle σ = (walk(5i mod P)+1) mod M,
verified bijective. No SHA matches are needed or sought (this is a counting/MI
check, not a luck hunt — per protocol rule 2).

Output (two board sizes):

```
M=257, T=40, 20000 records
  I(t ; parity(s))      = 0.001021 bits
  I(t ; sign(s))        = 0.001587 bits
  I(t ; orbitParity(s)) = 0.001229 bits
  I(t ; full slot s)    = 0.413014 bits   <- finite-sample bias, not signal
  CONTROL I(indep t ; indep parity) = 0.001029 bits  (true MI=0 noise floor)
  CONTROL I(indep t ; indep slot)   = 0.415917 bits  (matches slot bias above)

M=521, T=80, 20000 records
  I(t ; parity(s))      = 0.003693 bits
  I(t ; sign(s))        = 0.002958 bits
  I(t ; orbitParity(s)) = 0.000000 bits
  I(t ; full slot s)    = 1.464733 bits
  CONTROL I(indep t ; indep slot) = 1.473389 bits  (matches)
```

The ≤1-bit channels equal the independent-draw noise floor exactly. The
full-slot estimate equals its CONTROL (independent t, independent slot) — i.e.
it is **pure plug-in-estimator bias**, not signal. The bias sweep proves it:

```
   n        I(t;parity)    I(t;slot)   analytic_bias(slot) = (M-1)(T-1)/(2 ln2 n)
   2000      0.012117      2.437163    3.600967
   8000      0.005530      1.015809    0.900242
  32000      0.001112      0.254836    0.225060
 128000      0.000258      0.057081    0.056265
```

Both estimates **fall like 1/n** and track the analytic Miller-Madow bias term.
A genuine channel's MI would hold constant as n grows; these collapse toward 0.
**Confirmed: true I(t ; slot-function) = 0, by construction.**

---

## CURRENCY ACCOUNTING (mandatory)

Two sub-cases, two currencies:

1. **Free derivable parity/sign (the lane as literally posed).**
   Currency: **structure-free**. Bits about birth pass per record: **0 bits**
   (proven exact). It is the slot relabeled — the decoder already has the slot
   for free; a function of it conveys nothing new. Cost 0, payload 0. No net
   change to reach.

2. **Acceptance-gated parity (the only way to MANUFACTURE correlation).**
   To make parity informative, the encoder accepts a single at pass `t` only
   when `parity(birth_slot) == bit(t)`. Now a derived parity rules out the
   wrong-parity passes at decode. Currency: **match-supply**. This is exactly
   avenue E's measured leak: a gate that lets the parity bit disambiguate also
   **halves the per-pass acceptance probability** → ~**2× supply loss per bit
   gained** (Result-Ledger row 9 / PLAIN_STATUS, geometric starvation; cited,
   not re-derived). The trade is: one gated bit **doubles** the disambiguation
   reach (1 bit = 2× candidate passes resolvable) but **halves** match supply.
   A win is worth ≈2 bits (E[win|hit], MATH_MODEL §2); halving supply forgoes
   ~half of all future ≈2-bit wins. Per avenue E's measured ~2×-supply-per-bit,
   the net is ≤ 0. The bill reappears in **match-supply**.

---

## COUNTING GATE (mandatory, in writing)

*If a free, content-blind parity bit genuinely conveyed 1 bit of birth pass per
record, would arbitrary random data net-compress without bound?*

It cannot convey 1 bit, so there is no violation — and the reason is the leak's
location: **the parity bit is a deterministic function of a slot the decoder
already reads off the wire for free.** A function of a known quantity is not a
channel; `I(t ; f(s)) = 0`. It conveys **0 new bits**, so it cannot map 2^n
inputs into fewer outputs. There is no pigeonhole violation because there is no
new information — the "channel" is the slot, relabeled.

The hypothetical "what if it did carry a bit" is foreclosed at the source:
position is decoupled from birth pass by the shuffle (decoupling lemma). The
only way to recouple is acceptance-gating, which is **not free** (match-supply,
case 2 above) and **not unbounded** (each gated bit halves supply, so reach is
finite and the net is ≤ 0). Either branch passes the gate cleanly: free ⟹ 0
bits ⟹ no compression; informative ⟹ paid in supply ⟹ net ≤ 0.

---

## RESULT

**sharp-impossibility** for the free-and-unbounded version of the lane, with the
exact hinge named (position evolution ⊥ birth pass), plus a **refuted**
acceptance-gated variant (collapses to avenue E, net ≤ 0).

- Free derivable parity/sign carries **exactly 0 bits** of birth pass
  (proven-by-math + proven-by-construction). Reach extension from this lane: 0.
- The explosion check's ~5–6 pass reach is **not** extended by any slot
  function; conditioning on parity does not even cheapen it.
- The only correlation-manufacturing route is acceptance-gating, which pays in
  match-supply at avenue E's measured ~2×/bit rate; net ≤ 0.

**NEXT (single most promising sub-idea):** hand the *coupled* case to **avenue F
(frozen / two-speed boards)** — that is the one assumption whose relaxation
makes `I(t ; s) > 0`. The open question there is whether the freeze-time clock
can be made decoder-derivable for **under** the carriage it costs (PCTB says no
for an expanding board; a *fixed* board with a bounded two-speed odometer —
avenue C/F hybrid — is the only un-refuted shape). Lane G itself is closed.

