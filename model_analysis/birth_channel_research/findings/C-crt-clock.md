# Avenue C — CRT / residue clocks on a fixed board

Researcher lane: "CRT / residue clocks on a fixed board." Result:
**SHARP IMPOSSIBILITY** (the capacity gate fails by construction), with the
strongest CRT-specific escape (frozen-coordinate stamp) tested and refuted.

Toys (toy scale, exact arithmetic, no luck-dependent hashing — the claim is a
counting/logic claim so no SHA draws are needed):
- `model_analysis/birth_channel_research/C-crt-clock_odometer.py`
- `model_analysis/birth_channel_research/C-crt-clock_frozen_coord.py`

---

## HYPOTHESIS (written before any test)

**Setup.** Board size `Q = ∏ p_i` (distinct primes). By CRT a slot `s ∈ [0,Q)`
is identified with its residue vector `(s mod p_1, …, s mod p_m)`. A "residue
clock" makes a pass **advance one odometer coordinate** (or, more generally,
apply a fixed affine bijection `s → a·s + b mod Q`, `gcd(a,Q)=1`). The hope:
the value of a clock coordinate, **read from a record's final position**, tells
the decoder how many passes elapsed since the record was born — i.e. a
per-record birth-pass register, *derived from position, not stored*.

**What I expected, and why, from the mechanics.** I expected this to **fail the
mandatory capacity check and collapse into PCTB**, for two reasons predicted
before running:

1. A residue clock is a **deterministic public permutation**. Anything a public
   rule computes is identical for every record that lands at the same final
   slot — so the coordinate read at slot `f` is a function of `f`, **not** of
   the record's birth pass `k`. (`H1` below.)
2. A *fixed* board holds only `log2(Q)` distinguishable positions total, hence
   `log2(Q)` bits of positional information across **all** slots. The birth
   register needs `N·log2(T)` bits (N records, T passes). `N·log2(T) > log2(Q)`
   essentially always. To fit, `Q` must grow per pass — which is exactly the
   PCTB move the brief already priced as a 22× bloat. (`H2` below.)

I also flagged one genuinely tempting CRT-specific escape worth *testing* rather
than dismissing — **freeze one coordinate at birth and stamp `k` into it** — and
predicted it would relocate, not remove, the `N·log2(T)` bits (into a
content-dependent placement list = stored bits = PCTB restricted to that
coordinate).

---

## MECHANISM (precise constructions tested)

### Construction 1 — the uniform odometer (the literal "clock advances a pass")
Board `Q = ∏ p_i`. Per pass: `s → (s+1) mod Q` (by CRT this increments every
residue coordinate by 1; the simplest, cleanest "advance the clock"). Reversible,
public. A record born at pass `k` at original slot `x` ends at
`f = (x + (T−k)) mod Q`. The decoder sees only `f`.

### Construction 2 — the multiplicative / affine clock
`s → a·s + b mod Q`, `gcd(a,Q)=1`, `a` of high multiplicative order. Still a
deterministic public bijection. Born at `k`, original slot `x` ⇒ final
`f = a^{T−k}·x + (…)`. Decoder sees only `f`.

### Construction 3 — the frozen-coordinate stamp (avenue C × avenue F, the real escape)
Factor `Q = p_clock · Q_rest` with `p_clock ≥ T`. Designate `r_clock ∈ Z_{p_clock}`
as the birth register. **At birth (pass k): move the record to a free slot whose
`r_clock ≡ k`.** Thereafter the shuffle permutes only the `Q_rest` coordinates;
`r_clock` is **frozen**. At decode, read `r_clock` off the final slot ⇒ recover
`k mod p_clock` ⇒ the birth pass, apparently free.

---

## THE MATH / RESULTS

### Result 1 — the collision (H1 is FALSE). `C-crt-clock_odometer.py`, demo (A).
For a chosen final slot `f = 123` on board `Q=210` (primes 2,3,5,7), `T=64`:
for **every** birth pass `k ∈ 1..64` there is exactly one original slot
`x = f − (T−k) mod Q` that lands at `f`. The residue vector **at `f` is `f`'s
own — `(1,0,3,4)` — identical for all `k`.**

> distinct residue vectors at the final slot over all `k` = **1**.

So position at `f` carries **zero** bits about birth pass `k`. The affine clock
(Construction 2, demo (C)) gives the identical verdict: `f`'s residues/orbit
phase are properties of `f`, fixed across `k`; the original slot `x` silently
absorbs the difference. A public map carries 0 history bits.
*Evidence class: proven-by-construction (exact enumeration, no luck).*

### Result 2 — the capacity ledger (H2 is FALSE). `C-crt-clock_odometer.py`, demo (B).
A fixed board of `Q` slots distinguishes exactly `Q` positions. The **only**
positional channel for `N` records is *which `N` of `Q` cells are occupied*:
`log2 C(Q,N)` bits — and that list is the PCTB position tax, **stored, not free**.
Even granting it for free, against demand `N·log2(T)`:

| N | T | Q | birth demand `N·log2(T)` | `log2 C(Q,N)` | slack |
|---|---|---|---|---|---|
| 1000 | 64 | 1024 | 6000 | 161 | −5839 |
| 1000 | 64 | 4096 | 6000 | 3278 | −2722 |
| 4096 | 64 | 4096 | 24576 | 0 | −24576 |
| 1000 | 256 | 1000 | 8000 | 0 | −8000 |
| 1000 | 64 | 1,000,000 | 6000 | 11401 | +5401 |

The only row with positive slack is `Q = 10^6` for `N=1000` — i.e. the board
blown up ~1000× past `N`. But then the occupancy list is (a) underivable (the
match pattern is content-dependent) and (b) must be transmitted: that growing,
transmitted position list **IS PCTB** (`log2 C(Q_P, N_P)`, the 22× bloat at 64
passes, `pctb_ledger.py`). A fixed board cannot hold the register; a board grown
to hold it has rebuilt PCTB. *Evidence class: proven-by-math (exact `log2 C`).*

### Result 3 — the frozen-coordinate stamp pays the bill in stored bits. `C-crt-clock_frozen_coord.py`.

**The verdict rests on the irreducible core (assumption-free).** The decoder
must learn, per record, **which lane = which birth pass**. That map
`record → birth_pass` has entropy equal to the birth histogram's information. On
random data the births are uniform-hash dice outcomes, hence incompressible
(Shannon); for a ~uniform histogram over `T` passes the map carries exactly
`N·log2(T)` bits. A deterministic public shuffle supplies **0** of them (Result
1), and the file checksum is 64 bits, not `N·log2(T)`. So the lane assignment is
underivable content ⇒ **stored**. Freezing a coordinate to "remember `k`" only
relabels the slot; it does not create the bits that say which record carries
which label. *Evidence class: proven-by-math.*

**Illustration (the placement table, with soft modeling assumptions).** Give the
construction every benefit (uniform histogram `n_k = N/T`, one lane per pass
`p_clock = T`, lane size `Q/T`). The frozen lane *does* hand you `r_clock = k`;
but recovering **which slot within lane `k`** each record grabbed (a
content-dependent choice among the free slots) costs `∑_k log2 C(Q/T, N/T)`
stored bits:

| N | T | Q | placement bits | `N·log2(T)` | ratio |
|---|---|---|---|---|---|
| 1000 | 64 | 64000 | 7362 | 6000 | 1.23 |
| 1000 | 64 | 256000 | 9418 | 6000 | 1.57 |
| 4096 | 64 | 262144 | 30163 | 24576 | 1.23 |
| 1000 | 256 | 256000 | 9029 | 8000 | 1.13 |

The placement bill is **≥ the birth demand** at every setting. Shrink `Q` so
lanes are tight (`Q ≈ N`) and the bits stay `O(N·log2 T)` but you've just *moved*
the birth bits into the placement list; grow `Q` so lanes are loose and the
placement bits **grow** (more empty slots to choose among) — and the board grew
= PCTB. (This table assumes within-lane placement must be stored; the core
argument above does not need that assumption — even granting free within-lane
placement, the lane *assignment* itself is the irreducible `N·log2(T)`.)

---

## THE COUNTING GATE (mandatory)

**Question.** If the residue-clock channel were free + content-blind + unbounded,
would arbitrary random data net-compress without bound?

**Answer: YES — therefore the channel cannot be all three.** A residue clock is
content-blind (it never inspects bytes) and, on a fixed board, bounded
(`log2 Q` total). But it is **NOT free**. If it were, then on a uniformly random
`N·B`-bit file each accepted record's ~2-bit win would compound across `T`
passes with the birth register supplied at zero cost, net-compressing random
data without bound — mapping `2^{N·B}` inputs into fewer outputs, a pigeonhole
violation (Shannon: uniform-hash births are independent and incompressible).

**Where the leak is, in this avenue specifically.** The clock read-from-position
is a function of the final slot `f` alone. For a public permutation `π`,
`birth_pass` is **not** a function of `f`: given `f`, the pair `(k, x)` is
underdetermined — for each `k ∈ 1..T` there is exactly one `x = π^{−(T−k)}(f)`,
so `H(k | f)` can be as large as `log2(T)`. The clock conveys 0 of those bits.
To convey them you must **store** which `N` of `Q` cells are occupied
(content-dependent) — **stored-bits currency = PCTB**. The bill is conserved.

**Bonus leak (if you try the orbit phase as a salt schedule, avenue E flavor).**
A multiplicative clock `s → a·s mod Q` has order dividing the Carmichael
function `λ(Q) = lcm(p_i − 1)` (measured: 60 for both `Q=1155` and `Q=30030`).
The orbit phase **repeats** every `order` passes, so reusing the phase as a salt
schedule reuses the same lottery every `order` passes ⇒ the dice stop refreshing
⇒ **match-supply currency** leak (geometric starvation, Result-Ledger row 9).
So even the consolation use of CRT structure (a periodic salt schedule for the
explosion check) pays in match supply, exactly as the brief's avenue-E LEAK
WARNING predicts.

---

## CURRENCY ACCOUNTING

| sub-construction | currency the birth bill is paid in | bits |
|---|---|---|
| uniform / affine clock | **stored-bits** (the omitted birth bits become an underivable occupancy list) | `N·log2(T)` (e.g. 6000 bits at N=1000,T=64) |
| frozen-coordinate stamp | **stored-bits** (content-dependent placement list, = PCTB on the frozen coordinate) | `≥ N·log2(T)` (measured 1.13–1.57× of it) |
| orbit-phase salt schedule | **match-supply** (period `λ(Q)` lottery reuse) | ~2× supply loss per bit gained (avenue-E rate) |

In all cases the bill equals (or exceeds) the `N·log2(T)` birth information. The
residue structure relocates it; it never removes it.

---

## WHICH ARGUMENT IS LOAD-BEARING (hinge vs. support)

The **hinge** is Result 1 (the public-permutation argument), **not** the
capacity ledger. Result 1 holds for *any* `Q`, including an infinite board:
`f = π^{T−k}(x)`, so given only `f` every `k ∈ 1..T` is consistent with some
`x`, hence `H(k | f) = H(k)` — a public deterministic permutation carries **0**
birth bits, full stop. Capacity (Result 2) is the mandated *fixed-board* check
and is *defeatable by growing `Q`* (the `Q=10^6` row has positive slack) — so it
cannot be the kill on its own. Its role is the second half: it shows the
fixed-board version is *also* dead, and that **enlarging `Q` to fit the register
reconstructs PCTB** (an underivable, transmitted, growing occupancy list). So:
*impossibility = public permutation carries 0 birth bits (any board); capacity =
why the fixed board is also dead and why growing it = PCTB.*

### The mixed-radix odometer does not escape
The lane name stresses "odometer," so to preempt the obvious objection: a
multi-rate / mixed-radix odometer (a slow digit that ticks once per full cycle
of the fast digit) is **still a deterministic public permutation of the `Q`
slots**, so Result 1 subsumes it verbatim — its digit values at `f` are
functions of `f`, not of `k`. `s → s+1 mod Q` *is* the canonical odometer in the
CRT representation (it increments every coordinate at its own period `p_j`); the
general public-permutation argument covers any radix mixing.

## CONCLUSION

Avenue C is a **sharp impossibility**, and the assumption it hinges on is exactly
the master-gate assumption: *the shuffle is a deterministic public permutation.*
A public permutation makes the slot's clock coordinate a function of the slot,
not of the record's birth pass — so position carries 0 birth bits, **on a board
of any size**. The board's `log2(Q)` total capacity additionally cannot hold the
`N·log2(T)`-bit register; growing the board to fit reconstructs PCTB's stored,
growing position list (the priced 22× bloat). The single relaxation that *would* break the impossibility is the same
one everywhere in this project: **make the shuffle content-coupled or
history-dependent** (so position genuinely records birth) — but that is
content-awareness (forbidden by SPEC §0) and/or stored state (forbidden by the
metadata contract). Within the rules, the wall stands.

**Reach K from this avenue alone: K = 0** (no near-free birth bits delivered; the
clock supplies position phase, which the existing self-presenting position salt
already supplies for free — CRT adds nothing the spec doesn't already have).

**NEXT (most promising sub-idea):** abandon trying to *carry* birth bits in
residue structure; instead feed residue structure to **avenue E/G as a narrowing
prior** for the free ~2.5-bit explosion check — but ONLY a coordinate whose phase
does **not** repeat within the pass horizon (else the avenue-E match-supply leak
bites). Concretely: does a coprime-modulus schedule (CRT-distinct salt domains,
period `lcm(p_i)` not `lcm(p_i−1)`) let the 2.5 free bits disambiguate a
*disjoint* residue class per pass for `~m` extra passes before the supply loss
overtakes the gain? That is a quantified-reach question for the E lane, not a
free-channel claim — and it must be reported net of the supply loss, not gross.

---

### OUTPUT BLOCK (brief format)

```
AVENUE: C — CRT / residue clocks on a fixed board
HYPOTHESIS: a residue clock read from position would give birth pass free;
  expected to FAIL the capacity check and collapse into PCTB, because a public
  permutation carries 0 history bits and a fixed board holds only log2(Q) << N*log2(T).
MECHANISM: Q=prod(primes); pass = advance one residue coordinate (s->s+1 mod Q)
  or affine s->a*s+b mod Q; plus the frozen-coordinate stamp (freeze r_clock=k at birth).
RESULT: sharp-impossibility (reach K=0)
EVIDENCE: proven-by-construction + proven-by-math —
  C-crt-clock_odometer.py (collision: 1 residue vector per final slot over all k;
  capacity ledger log2 C(Q,N) << N*log2(T)); C-crt-clock_frozen_coord.py
  (placement bill >= N*log2(T)). No luck-dependent test: the claim is counting/logic,
  so exact enumeration is the right instrument, not SHA draws.
CURRENCY: stored-bits = N*log2(T) (uniform/affine clock and frozen stamp both);
  orbit-phase-as-schedule leaks in match-supply (period lambda(Q), ~2x loss/bit).
NEXT: hand residue structure to the E/G lane as a NON-repeating narrowing prior
  for the 2.5 free bits, reported net of the avenue-E supply loss — not as a channel.
```
