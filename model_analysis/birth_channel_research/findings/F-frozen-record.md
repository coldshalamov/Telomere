# Finding F — Frozen-record / two-speed boards

Lane: avenue F (BRIEF). "Once a record is born it stops moving (or moves on a
slower clock) while literals shuffle fast. Does freezing make birth POSITION
(hence salt) self-presenting AND birth PASS readable from the phase gap
between fast and slow clocks? Check reversibility very carefully."

Author pass: June 2026. Evidence is exact permutation logic + one planted
real-SHA single. No hash-hunting (no luck-dependent test anywhere).

Toys:
- `model_analysis/birth_channel_research/F-frozen-record_toy.py`
- `model_analysis/birth_channel_research/F-frozen-record_reversibility.py`

---

## HYPOTHESIS (written before the toys ran)

Split the lane into two halves, because they have opposite answers:

1. **Salt half** — a record frozen at its birth position has salt = its
   current (= final) position, which is self-presenting at decode. I expected
   this to be genuinely free, BUT to be nothing new: the standard V1 machine
   already self-presents *position* salts (SPEC §1, §4). Freezing does not add
   a new free channel here.

2. **Geometry half (the wall)** — to emit the original block order the decoder
   must recover each item's original slot = how many shuffles to reverse =
   birth pass. I expected freezing to *relocate* this requirement, not remove
   it. Specifically I predicted:
   - **Two-clock phase gives 0 free bits.** With records on σ_slow after birth
     and literals on σ_fast, `final = σ_slow^{T−t}(σ_fast^{t}(x0))`. Two
     unknowns (x0, t), one observation. For every candidate t∈[1..T] there is a
     legal x0 = σ_fast^{−t}(σ_slow^{−(T−t)}(final)); x0 ranges over all slots,
     so nothing prunes. Phase → T candidates, not a unique read.
   - **Reverse moving domain is occupancy-dependent.** On a fixed board the
     survivors shuffle over the *complement* of the frozen set. The frozen set
     as of pass t IS the birth schedule of everything born after t. So the
     reverse walk is self-presenting only for the FINAL pass; every earlier
     step needs future births. Zero-stored-state inversion would require
     reconstructing the schedule — exactly the missing quantity.
   - **Same-board two-speed isn't even a bijection.** σ_fast(literal-slots) and
     σ_slow(record-slots) collide; de-colliding needs occupancy-aware
     cycle-walk = the schedule again.

Predicted currency: STORED-BITS (write the schedule = tags, ≥ log2(T)/record,
net-negative past pass ~6) OR structure/compute (trial-reconstruct, capped at
the explosion-check ~2.5 bits ≈ 6 candidate passes). Phase = 0 free bits.

---

## MECHANISM (precise construction tested)

**Board.** Fixed size M (singles only, 1→1 length-preserving, so M is
constant — the regime the wall lives in per BRIEF "sustained arity-1 singles").

**Two clocks.** Both are exact prime-field permutations of the same board:
fast = `i → walk(5i mod P)+1 mod M`, slow = `i → walk(3i mod P) mod M`.

**Freeze rule (the lane's mechanism).** When a record is born at pass t it
keeps its board position forever (frozen). Only the *unfrozen* positions
participate in pass t's shuffle, restricted to the complement set (a genuine
sub-permutation, re-instantiated each pass for the current movable count).
Salt of a born record = its frozen position = self-presenting.

**Phase variant (CHECK 1).** Records, after birth, ride σ_slow on the full
board; literals ride σ_fast. The "phase gap" between the two clocks is the
proposed birth-pass channel.

**Same-board variant (CHECK 3).** Literals → σ_fast, records → σ_slow, both on
the SAME full board simultaneously.

---

## RESULTS (what the toys showed)

### CHECK 0 — salt half is free (sanity, real SHA, planted)
A record frozen at final position f has salt f; `H(seed|s{f})` regenerates its
content with no birth-pass input. Confirmed. **But this is the position salt
the standard machine already supplies; freezing adds nothing new.**
Evidence class: proven-by-construction (planted single, real SHA-256).

### CHECK 1 — two-clock phase gives 0 free bits
M=23, T=12. Planted true (x0=7, birth t=5) → final position 2. Inverting for
x0 at every candidate t:

```
t:  1   2   3   4   5   6   7   8   9  10  11  12
x0:14   0   1   9   7  21   3   9   4  14  18  20   (all legal slots)
```

All 12 candidate birth passes admit a valid origin slot. The phase pins
NOTHING. **Free bits from the two-clock gap = 0.**
Evidence class: proven-by-math / proven-by-construction (exact permutation
enumeration). Would-the-test-work check: pure permutation arithmetic, no luck
involved; the result is a counting identity, not a sampled estimate.

### CHECK 2 / Reversibility LAYER 1 — invertible WITH schedule
M=15, schedule {1:{3}, 2:{0,7}, 3:{5}, 4:{2}}. Forward frozen-board map is a
bijection on items (True); reverse replay (movable domains re-derived from the
supplied schedule) recovers the identity exactly — every original slot home
(True). **WITH the schedule, the frozen board is fully invertible.** This is
the direct analogue of THE_OPEN_QUESTION's 9/9 column: the machine works when
the schedule is supplied *from outside the wire*.
Evidence class: proven-by-construction.

### CHECK 2 / Reversibility LAYER 2 — schedule NOT wire-derivable
The decoder's only free anchor is the FINAL pass: its movable domain =
complement of the record positions, which are visible on the wire (records are
tagged). Confirmed it matches the true final-pass movable domain exactly. **But
the induction has no base case beyond pass T.** To reverse pass T−1 the decoder
must know pass (T−1)'s movable domain = complement of (frozen-as-of-T−1) =
final frozen MINUS the records born at pass T. Which final records were born at
T is unknown without the schedule. At this *first* reverse induction step
alone there are 2^R − 1 = 31 candidate "born-at-T" subsets (R=5 records).
**The schedule is not wire-derivable; reversibility holds only when it is
supplied = stored birth info.**
Evidence class: proven-by-construction (the free base case is real and was
verified; the induction failure at T−1 is exhibited concretely).

### CHECK 2b — geometry pins nothing; full birth entropy is missing
**Discriminating test (decode ONE fixed wire under every labeling).** Build a
real wire once (R=5 records with planted seeds at final positions 0,2,3,5,7,
real-SHA content; random literals elsewhere; 64-bit checksum of the true
original). Then decode that *same* fixed wire under all T^R = 4^5 = 1024
candidate birth-pass labelings. Each labeling implies a different freeze
schedule → different movable domains → a different inverse permutation → a
different reconstructed original from the identical wire. Measured:

| quantity | result |
| --- | --- |
| true labeling decodes wire to original (checksum matches) | **True** |
| structurally-valid decodes of the fixed wire | **1024** (geometry never blocks) |
| DISTINCT original files produced (rival readings) | **1017** |
| readings matching the 64-bit checksum | **exactly 1** (the true reading) |

This is falsifiable (it would fail if geometry constrained the labelings, or if
the wire decoded the same file under every labeling) and it does not — 1017
genuinely different files decode from one wire. Birth information the wire fails
to supply = log2(1017) ≈ 10 bits for 5 records = **2.00 bits/record** (= log2 T,
the tag baseline). **Only the non-scaling 64-bit checksum separates the true
reading; it cannot carry R·log2(T) at scale.** Freezing buys nothing back.
Evidence class: proven-by-construction (real fixed-wire decode under all
labelings; real SHA-256 content and checksum; 1 of 1024 passes the referee).

**Scale-free proof-by-math (why all T^R survive).** A record born at pass t
freezes at its then-current position forever, so its final position = its
position at pass t. Conversely, given any labeling (final-pos f → birth pass
t_f), set schedule[t] = {f : t_f = t}. Final positions are distinct, so each f
is named exactly once, at t_f, and stays movable for all passes < t_f (nothing
else freezes it). Each pass acts as a bijection on the movable set, so the
whole forward map is a bijection; its inverse assigns every record + literal a
distinct original slot. Thus every labeling yields a structurally valid,
reversible decode landing records exactly at the observed positions — differing
only in the recovered slot-permutation (a different output file), separable
only by the global header checksum. ∎ Decode ambiguity = T^R, no geometric
narrowing. Evidence class: proven-by-math.

**Avenue-B corollary (closes trial-decode from this side too).** The geometric
decode ambiguity is **T^R = exponential in R** (the record count, which grows
with the file). The 64-bit global header checksum can separate readings only
down to ~2^64 survivors, but it does not scale per-record: with R records the
candidate set is T^R and the per-record disambiguation the checksum supplies is
o(1) at scale. So trial-decode is **not** bounded here (refutes the optimistic
read of avenue B for the frozen-board mechanism); the only finite handle is the
explosion check's ~2.5 bits/record, capping reach at ~6 passes.

### CHECK 3 — same-board two-speed is not a bijection
M=23, 2000 random record-occupancy subsets: **99%** produce ≥1 image collision
(worst 8 collisions). Two speeds on one full board collide for almost all
occupancy sets. De-colliding requires occupancy-aware cycle-walk = re-deriving
the frozen set = the schedule again. Not free.
Evidence class: measured (exact collision count over sampled occupancy sets;
the near-certainty is structural — two independent permutations restricted to
complementary subsets generically overlap).

---

## COUNTING GATE

> If this mechanism were free + content-blind, would arbitrary random data
> net-compress without bound?

**No** — and the reason is exhibited, not asserted. Freezing does NOT make the
birth pass free. The two-clock phase supplies 0 bits (CHECK 1); the reverse
geometry supplies the schedule for the final pass only and nothing earlier
(LAYER 2); the full N·log2(T) birth entropy remains missing (CHECK 2b, 1024/1024
labelings survive). So there is no free unbounded channel here to drive the
pigeonhole violation.

**Where the bill reappears (currency):** the birth schedule must be conveyed.
Two ways, both already-priced no-go's:
- **STORED-BITS:** write the schedule = per-record birth tags, ≥ log2(T) bits
  each (2 bits at T=4; grows with T). Net-negative past pass ~6 (THE_OPEN_QUESTION
  requirements card; GOLDEN_CONFIG §6 "stored birth tags").
- **STRUCTURE / COMPUTE:** trial-reconstruct the schedule at decode and keep
  what passes the checksum (the explosion check). Capped at the measured free
  budget ~2.5 bits/record ≈ 6 candidate passes (BRIEF settled-list / Result
  Ledger row 7). Freezing does not extend this cap — it does not narrow the
  candidate set at all (CHECK 1: all T candidates legal; CHECK 2b: all T^R
  labelings legal).

**Finite resource that bounds it:** the explosion check's ~2.5 free bits per
record. Freezing contributes 0 to it. So K(frozen-record) = K(explosion-check
alone) ≈ 6 passes — freezing adds no reach.

---

## RESULT

**refuted** (as a free birth-pass channel) — equivalently a **sharp
impossibility for the geometry half**, with one genuinely new structural
sub-result:

> **The final pass is a free base case, and the induction dies immediately at
> T−1.** On a frozen board the last shuffle's domain = complement of the
> wire-visible record positions, so pass T inverts with zero stored state. But
> pass T−1's domain = (final frozen) minus (records born at T), and "which
> records were born at T" is exactly one birth-pass bit per record. The
> occupancy-dependence of the moving domain converts the missing birth pass
> into a missing *permutation domain*, one reverse step in — it does not remove
> it. This localizes precisely WHERE freezing fails: not at salt, not at the
> final pass, but at the second-to-last reverse induction step, in the
> occupancy-dependence of the survivor shuffle.

The single assumption it hinges on (per avenue H discipline): the shuffle
restricted to the movable set is a *full* permutation of that set (every
unfrozen slot reachable). That is what makes all T^R labelings geometry-legal.
A shuffle that instead constrained reachability (e.g. coupled record positions
to birth pass) would leak content-awareness or re-introduce stored structure —
it is the same wall from the other side.

## CURRENCY

`stored-bits` (write the schedule = tags, ≥ log2(T) bits/record) OR
`structure (free ~2.5 bits)` capped at ~6 passes via the explosion check.
Phase channel = 0 free bits. Freezing adds **0** reach over the explosion
check that already exists.

## EVIDENCE SUMMARY

| claim | class |
| --- | --- |
| salt self-presents at frozen position | proven-by-construction (real SHA) |
| two-clock phase = 0 free bits | proven-by-math / construction |
| frozen board invertible WITH schedule | proven-by-construction |
| final pass is a free base case | proven-by-construction |
| induction dies at T−1 (schedule not wire-derivable) | proven-by-construction |
| all T^R labelings geometry-legal (no narrowing) | proven-by-construction (1024/1024 replays) + proven-by-math |
| trial-decode ambiguity = T^R, exponential (avenue B closed) | proven-by-math |
| same-board two-speed not a bijection | measured (99% collide) |

## NEXT (the one untested corner — now resolved, sharpening the impossibility)

Probed: does a *gradated* freeze (records thaw on a known public schedule —
unfreeze after a fixed public lag L) let the last L passes all be free base
cases instead of one? **Resolved: no — public thaw DESTROYS even the single
free base case.** With finite lag L, a wire-visible record participates in the
final pass's shuffle iff it was born at pass ≤ T−L. Whether each record is in
the final-pass movable pool therefore depends on its birth pass, so the
final-pass movable domain is no longer the simple complement of the record
positions — it carries 2^R ambiguity (R records). Full freeze (L=∞) is the
*only* policy with a free base case, and it has exactly one (the last pass).
A content-dependent thaw is just the tag baseline.

**Sharpened impossibility:** for ANY public freeze/thaw policy, at most ONE
reverse pass (the final one, under full freeze) is a free base case; the
induction never extends. The frozen-record lane's entire free contribution is
that single final-pass inversion, which conveys 0 birth-pass bits (the birth
pass of the record opened on the final reverse step is still unknown — only its
*position* is, and position salt was already free). Net reach added over the
explosion check: **0**.

Nothing further in this lane is worth a toy; it is closed.
