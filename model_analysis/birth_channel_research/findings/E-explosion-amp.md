# Lane E — Explosion-check amplification (MIND THE SUPPLY LEAK)

Researcher pass, June 2026. Findings + math + toys + currency accounting.
Toys (in `model_analysis/birth_channel_research/`):
`E-explosion-amp_supply_ledger.py`, `E-explosion-amp_reach.py`,
`E-explosion-amp_dfs_knee.py` (the measured branching knee).

**Headline:** the period-P salt schedule is REFUTED as an amplifier — it
conveys zero new information (the decoder already knows `t mod P` for free, see
below) and at best trades the free budget for match-supply. The native
explosion-check reach is a quantified **finite K ≈ 5–6 candidate open-steps
per record**, bounded not by a decode-correctness cliff but by trial-decode
**DFS branching (compute that scales with 2^bits)** once more than ~`1/q ≈ 5.66`
records are simultaneously ambiguous per reverse step. MEASURED below.

---

## HYPOTHESIS (written before any test, from the mechanics)

The free explosion check supplies ~2.5 bits/record (Result-Ledger row 7,
PLAIN_STATUS row 7, MEASURED): a wrong-salt trial-open fails to parse
("explodes") so at decode you can pick the right birth/open-step by
non-explosion. 2.5 bits distinguishes `2^2.5 ≈ 5.66` candidates for free.

The lane's premise: pair this with a **period-P salt schedule** (P=6) so the
salt-key depends only on `t mod P`. Then the explosion check covers the
residue `r = t mod P` (needs `log2 6 = 2.58` bits ≈ the 2.5 budget) and the
schedule "covers the quotient" `q = t // P`, extending reach past ~6 passes.

**What I expected before testing, from the mechanics:** the schedule is a
TRAP. A period-P salt schedule reuses the lottery every P passes. Combined
with the documented *position-only deadlock* (`freshness_law_validation.py`
lines 80–90: position-only salting gives zero accepts from pass 3 because the
emitted stream replicates the previous layer; a pass-DISTINCT key is required
to break the deadlock), a period-P key supplies only P distinct
deadlock-breaking keys. So match supply caps at ~P distinct draws/window. I
expected: gross reach unchanged, net reach strictly *worse* than the
explosion check used alone — the schedule pays the birth bill in the
`match-supply` currency and buys nothing the explosion check didn't already
have. I expected the honest deliverable to be the explosion-only reach, with
the schedule proven a pure loss.

---

## MECHANISM (precise construction)

- Board/shuffle/salt: Golden Config — B=8, canonical alphabet, arity-2 engine,
  shuffle `i→walk(5i mod P)+1 mod M`, **position salts** (self-presenting,
  free) as the base refresh.
- Birth-channel under test: the **explosion check** as the per-record
  open-step detector. On the reverse walk, at each step trial-open every
  still-encoded record; the right salt (right step) parses cleanly, a wrong
  salt yields a uniform digest that parses as valid self-delimiting items
  only with probability `q = 2^-E ≈ 0.177` (`E = 2.5` bits). The 64-bit
  header checksum is the global referee on complete readings
  (`robins_opening_rules.py` rule C = DFS-over-openings + checksum).
- The proposed amplifier: a **period-P pass-key** added to the salt,
  `H(seed, position, t mod P)`, so birth pass is ambiguous only up to its
  residue mod P, which the explosion check resolves.

---

## THE MATH

### (I) Explosion-only reach — the real free prize (no schedule)

The free budget `E ≈ 2.5` bits is a per-trial **false-non-explosion rate**
`q = 2^-E ≈ 0.177`. A record born on pass t becomes ambiguous if a WRONG
open-step also survives the explosion check. Over a window of `C` candidate
steps with `R_live` records simultaneously ambiguous, expected false
survivors (union bound, uniform-hash law, independent trials):

    E[false survivors] = R_live · (C − 1) · q .

**The decode is ALWAYS correct (checksum-refereed); the cost of false
survivors is COMPUTE, not correctness.** The maintainer's decoder
(`robins_opening_rules.py` rule C) is a DFS over which records to open at each
reverse step, with the 64-bit header checksum as the global referee on
complete readings. A wrong-step opening that survives the explosion check does
NOT corrupt the output — it adds a DFS branch the checksum later kills. So the
right reading of `E[false survivors] = R_live·(C−1)·q` is **the DFS branching
factor**, not a determinism cliff. (This corrects an earlier framing of mine
that called it a sub-1-pass correctness collapse; the checksum is always the
referee, so the bill is compute.)

The **knee** is at `R_live ≈ 1/q = 2^E ≈ 5.66` records simultaneously
ambiguous per reverse step:

- `R_live ≲ 6`: each step's `(C−1)·q·R_live ≲ 1` ⟹ the DFS is ~linear (≈ one
  open/skip choice that survives per step) ⟹ **free + deterministic, the
  proven regime** (12/12, 36/36, all at small N and T ≤ 5).
- `R_live ≳ 6`: the explosion check fails to kill `> 1` branch per step ⟹ the
  DFS must enumerate up to `2^R_live` open/skip subsets per step before the
  checksum referees ⟹ the leak is **`compute that scales with 2^bits`** (the
  named currency, THE_OPEN_QUESTION card item 4; the Q1 trial-decode bill,
  GOLDEN_CONFIG §5/§7). GOLDEN §5 prices exactly this as "free to RUN but not
  free in the accounting at scale."

This **unifies what I first split into two models**: there is one mechanism
(checksum-refereed DFS); below the knee it is linear/free, above it it branches
and the cost is compute. The information-theoretic statement `C ≤ 2^E` per
record (each record's birth pass placed within ~5.66 candidate steps) and the
branching statement are the same fact: 5.66 is both `2^E` and `1/q`.

**MEASURED** (`E-explosion-amp_dfs_knee.py`, real SHA-256, maintainer's exact
rule C, node counter vs max live-records-per-step):

| max live records/step | cases | mean DFS nodes | max nodes |
| ---: | ---: | ---: | ---: |
| 2 | 16 | 4.6 | 5 |
| 3 | 15 | 55.9 | 117 |
| 4 | 5 | 153.4 | 319 |

Every single run decoded correctly (OK) — confirming decode stays correct;
the node count climbs ~12× from 2→3 and ~3× again from 3→4 live records, i.e.
super-linear growth as the live count rises toward the predicted ~5.66 knee.
The leak is compute, exactly as the reach model predicts.

### (II) Period-P salt schedule — REFUTED as an amplifier

**The decisive argument is informational vacuity, not supply (rock-solid).**
The decoder reverses pass by pass, so at every reverse step it knows the
*absolute* pass index it is undoing — and therefore knows `t mod P` for free,
for any P. A period-P salt schedule's residue `r = t mod P` is thus DERIVABLE,
conveys **zero new information**, and cannot narrow the candidate open-step set
by even one bit beyond what the reverse-walk index already gives. The
explosion check distinguishes ~5.66 candidate steps directly, with or without
a schedule. So the schedule is informationally vacuous: it amplifies nothing.
**Lane E's premise — "schedule covers the quotient, explosion covers the
residue" — is refuted: the quotient and residue are both already free from the
reverse-walk index; the explosion check's job is the *which-records-open-here*
ambiguity, which the schedule does not touch.**

**Supply cost (illustrative — the trap if you ignore the above and make salts
periodic anyway).** If, contrary to SPEC §1 (where position salts refresh by
the shuffle), one made the refresh key itself period-P, a window would see at
most ~P distinct dice draws, and coverage would saturate at the P-draw
ceiling:

    cov_periodic(T, P) = 1 − (1−p)^min(T,P) ,   p = 0.0039 (GOLDEN base).

| schedule | log2 P (label bits) | distinct draws | cov ceiling | cov / cov_fresh@1024 |
| --- | ---: | ---: | ---: | ---: |
| P=5 (residue free: P ≤ 2^E) | 2.32 | 5 | 0.01935 | 1.97% |
| P=6 | 2.58 | 6 | 0.02317 | 2.36% |
| P=16 | 4.00 | 16 | 0.06061 | 6.17% |
| P=64 | 6.00 | 64 | 0.22127 | 22.5% |

Fresh dice climb to coverage 1.0 by T≈1024; the schedule is stuck at ≤22%.
The "geometric starvation ~2× per bit" law (PLAIN_STATUS row 9): each
doubling of P (one extra label bit) only ~doubles distinct draws, but the
fresh ceiling needs ~1024 draws — so each bit of schedule label buys ~2× draws
against a 1024-draw target, i.e. you pay ~2× supply per bit of birth
disambiguation, exactly the measured starvation rate.

**Net ledger** (`E-explosion-amp_supply_ledger.py`, part 3) — net bits per
window, config A = explosion-only/no-schedule (fresh dice), config B = period-P:

| T | A: net (fresh) | B P=6 | B P=16 | B P=64 |
| ---: | ---: | ---: | ---: | ---: |
| 64 | 0.480 | 0.048 | 0.041 | −0.294 |
| 1024 | 2.130 | 0.048 | 0.041 | −0.294 |
| 4096 | 2.170 | 0.048 | 0.041 | −0.294 |

Every B column ≤ A at every T. Even setting the informational-vacuity kill
aside, the schedule is a pure loss: residue-free only for P ≤ 5 (caps supply
at 5 draws), buys NO disambiguation the explosion check didn't already supply
directly, and pays the relabeling in capped match supply. The optimum of the
explosion-bits-vs-supply-loss trade is therefore **P = 1 (no schedule).**

---

## THE OPTIMIZED K (the honest deliverable)

The trade the lane asked me to optimize — explosion-bits vs supply-loss — has
its optimum at **P = 1 (no schedule)**: any P > 1 spends supply (or, more
fundamentally, is informationally vacuous) for a relabeling the reverse-walk
index + explosion check already provide free. So the deliverable K is the
NATIVE explosion-check reach:

- **MAX-FREE-REACH K (stored-bits-free AND compute-free, deterministic):**
  **K ≈ 5–6 candidate open-steps placement per record** (`2^E = 5.66`), valid
  while **≲ 6 records are simultaneously ambiguous per reverse step**
  (`R_live ≲ 1/q ≈ 5.66`). In that regime the checksum-refereed DFS is linear
  and decode is free + deterministic — matching SPEC's proven 12/12 and 36/36
  (small N, T ≤ 5). MEASURED: DFS node count ≈ 4.6 at live=2.
- **Next bottleneck at K+1 (i.e. `R_live > ~6`):** decode stays CORRECT but the
  trial-decode DFS branches — the leak reappears as **`compute that scales with
  2^bits`** (super-linear node growth, MEASURED: 4.6 → 55.9 → 153 nodes as
  live goes 2 → 3 → 4). This is the open Q1 trial-decode bill.
- **Period-P schedule adds 0 to K** (informationally vacuous) and, if forced,
  subtracts from net via match-supply. **Refuted as an amplifier.**

---

## CURRENCY ACCOUNTING (where the birth bill reappears)

| mechanism | currency | bits |
| --- | --- | --- |
| explosion check (the free source) | `structure-free` | +2.5 bits/record = ~5.66 candidate steps placed per record; FINITE, cannot grow with T |
| **next bottleneck: trial-decode DFS above the knee** | **`compute` (scales 2^bits)** | once `R_live ≳ 1/q ≈ 5.66` per step, the DFS branches (MEASURED 4.6→55.9→153 nodes for live 2→3→4); decode stays correct, the bill is compute |
| period-P salt schedule (this lane's proposed amplifier) | `match-supply` (and moot) | informationally vacuous (`t mod P` is free from the reverse-walk index); if forced anyway, caps draws at P, ~2× supply lost per label bit |

**Primary currency for lane E: `structure-free` → `compute`.** The free
explosion budget is finite (~2.5 bits/record, ~5.66 candidate steps); pushing
past it does not corrupt decode but pays in exponential trial-decode `compute`.
`match-supply` is only the (vacuous) schedule's trap, not the lane's real bill.

---

## COUNTING GATE (the master gate, answered in writing)

**Q: If the explosion check were free + content-blind + UNBOUNDED, would
arbitrary random data net-compress without bound?** Yes — that would be a
pigeonhole violation (it would convey every record's birth pass for free,
unbounded, on random data). **So it must NOT be unbounded, and it isn't:**

The free budget `E ≈ 2.5 bits` is **FINITE** because the hash is
content-blind. A wrong-salt expansion is a uniform digest; it parses as valid
self-delimiting items (survives the explosion check) with probability
`q = 2^-E`, *not* zero. The check is a filter with a fixed pass-rate, not an
oracle. The finite resource that bounds it is the **`structure-free`
currency**: ~2.5 bits/record of distinguishing power (~5.66 candidate steps)
that cannot grow with T. Pushing past it does NOT corrupt decode (the checksum
referees), but the trial-decode DFS branches once `R_live ≳ 1/q ≈ 5.66` per
step, so the bill reappears as **`compute that scales with 2^bits`** (MEASURED,
`E-explosion-amp_dfs_knee.py`). The only ways past it: stored bits (`tags`,
≥ log2(passes), net-negative past pass 6), `compute` (exponential DFS), or
`match-supply` (the vacuous period-P schedule). The leak is plugged in one of
these currencies in every case. **No free, content-blind, unbounded channel
exists here** — the explosion check is exactly the FINITE structure source the
brief names, and the period-P schedule does not amplify it (it is
informationally vacuous: the reverse-walk index already supplies `t mod P`).

---

## EVIDENCE CLASSES

- **Period-P schedule is informationally vacuous** (decoder knows `t mod P`
  from the reverse-walk index): **proven-by-math** (the reverse walk undoes
  passes in known order; SPEC §4). This is the decisive refutation.
- Period-P (if forced) caps supply at P draws, coverage = 1−(1−p)^min(T,P):
  **proven-by-math**, but flagged **illustrative** — it rests on a replay
  assumption that does NOT hold in the shuffled architecture (position salts
  refresh per SPEC §1); included to show even the supply trade loses.
  Toy: `E-explosion-amp_supply_ledger.py`.
- Native explosion reach `K ≈ 5.66` candidate steps/record, with the knee at
  `R_live ≈ 1/q ≈ 5.66`: **proven-by-math** (`E = 2.5` measured → `q = 2^-E`;
  union bound = DFS branching factor) AND **measured**
  (`E-explosion-amp_dfs_knee.py`: real SHA-256, maintainer's rule C, node
  count 4.6 → 55.9 → 153 for live 2 → 3 → 4, every run decoding correctly).
- The leak above the knee is `compute ∝ 2^bits`, NOT a correctness cliff:
  **measured** (every DFS run OK; node count super-linear) + consistent with
  `robins_opening_rules.py` (rule C = checksum-refereed DFS) and GOLDEN §5/§7.
- The `q = 2^-E` identification (false-non-explosion rate) is a **conjecture**
  in its exact constant; 2.5 is measured (row 7), per-step independence is an
  idealization of the real parse/checksum filter.

## NEXT (single most promising sub-idea)

Push `E-explosion-amp_dfs_knee.py` to larger N/T (with a search-capped rule C)
to pin the branching-knee location precisely against the predicted `1/q ≈
5.66`, and fit the above-knee growth exponent — confirming whether the DFS
worst case is the full `2^R_live` or a tamer base. That fixes the exact
compute-currency cost of pushing lane E past K ≈ 6 (the open Q1, GOLDEN §7
agenda item 2).

---
---

# ROUND 2 (deeper) — the ambiguity ledger CORRECTS the currency to STORED-BITS

*June 2026, second pass on lane E. Toy: `E-explosion-amp_ambiguity_ledger.py`
(the discriminating test). This round supersedes BOTH the round-1 "compute"
attribution AND the "K ≈ 6 passes free" headline: the leak is **stored-bits**
(compute was a toy-scale symptom), and the honest reach is a **joint (N,T)
ceiling `N·c_mean(T) ≤ 64`** — NOT a free pass count. As N → ∞ the free
pass-reach collapses to T = 1; no T ≥ 2 is free at unbounded N. This is a
**sharp impossibility**. The "5.66 passes free" folklore is refuted by the model
itself (`c_mean(5.66) = 0.87 b/rec ≠ 0`).*

## What was wrong with round 1's instrument (verified, not asserted)

Round 1's `E-explosion-amp_dfs_knee.py` measured DFS node growth (4.6 → 55.9 →
153 as live-records rose 2 → 3 → 4) and attributed the leak to `compute`. **That
toy did not actually contain the explosion check.** With `SEED_BITS = 14`,
`robins_opening_rules.open_rec` parses ANY 64-bit digest into exactly `a` valid
9/16-bit items — a wrong open NEVER "explodes". Verified empirically:

    open_rec called 2000× on (random seed, arbitrary salt): explosions = 0
    => the explosion check is ABSENT (every digest parses) in this toy.

So the only pruning in round 1 was the **terminal 64-bit checksum** plus the
"no records left at t=0" gate. The node-count rose with the live-record count
for the trivial combinatorial reason that there are more open/skip subsets, and
its proximity to `1/q ≈ 5.66` was a **coincidence**, not a measurement of the
q-filter. Pushing that toy bigger would keep producing compute curves that LOOK
like they confirm the story while measuring nothing about the real ceiling.
(The explosion check IS real in the full B=8 Lotus architecture — wrong salts
fail to parse / miscount arity / leave dangling garbage, the measured ~2.5
bits — but the simplified fixed-width toy doesn't capture it. The faithful
instrument is a clean model with `q = 2^-E` as an explicit parameter.)

## The real ledger (proven-by-math) — supersedes "checksum always referees"

The checksum is a **fixed k = 64 bits for the whole file**, NOT a per-record
oracle. The honest per-record accounting:

| quantity | per record | scaling |
| --- | --- | --- |
| free: explosion check | `E ≈ 2.5` bits | FINITE, content-blind |
| free: global checksum | `k/N` bits | → 0 as N → ∞ |
| **required: birth pass** | `log2(T)` bits | grows with depth |

A *reading* of the file picks, for each record, which reverse step to open it
at. The true reading opens each at its birth step; a wrong step survives the
explosion check with prob `q = 2^-E`. The records are independent, so the
expected number of explosion-surviving COMPLETE readings is

    E[S(N,T)] = [ 1 + (T-1)·q ]^N ,   log2 E[S] = N · c_mean(T),
    c_mean(T) = log2(1 + (T-1)·q)  bits/record.

The k-bit checksum pins the unique true reading among the survivors only while
`E[S] < 2^k`, i.e. **`N · c_mean(T) ≤ k`**. Past that, multiple readings pass
every free check — decode is **genuinely ambiguous**, and the fix is stored
bits (`c_mean(T)` per record, the tags baseline).

### The honest reach is a JOINT (N,T) ceiling, NOT a free pass count K

`c_mean(T) = log2(1 + (T−1)q) > 0` for **every** T ≥ 2 — there is residual
ambiguity at every depth past one pass. So:

    free unique decode  ⟺  N · c_mean(T) ≤ k (= 64).

| T | c_mean(T) b/rec | N*(T) = 64/c_mean (max free-decodable records) |
| ---: | ---: | ---: |
| 2 | 0.235 | 272 |
| 4 | 0.614 | 104 |
| 8 | 1.162 | 55 |
| 64 | 3.601 | 18 |
| 1024 | 7.507 | 8.5 |

As N → ∞, `c_mean(T) ≤ 64/N → 0`; since `c_mean(T) > 0` for all T ≥ 2, the free
pass-reach collapses to **T = 1**. **No T ≥ 2 is free at unbounded N** — a
**sharp impossibility** with a finite *joint* reach, not a flat pass count.

**The folklore "K = 2^E ≈ 5.66 passes free" is REFUTED by this very model.**
`c_mean(5.66) = log2(1 + 4.66·0.177) = 0.867 bits/record ≠ 0`: a 5.66-candidate
window leaves `1 + (2^E−1)q = 1.82` survivors per record, not 1. The "2.5 bits
distinguishes 5.66 candidates" intuition is a *single-record* statement; across
N records the ambiguity multiplies (`(1+(T−1)q)^N`) and the fixed 64-bit
checksum cannot referee it. The 12/12 and 36/36 proofs survive because they live
deep inside the free region (small N: e.g. N=12, T=5 → `N·c_mean = 9.3 ≪ 64`).

`log2 T − E` is only the **large-T asymptote** of `c_mean` and a strict
**lower bound** (`c_mean(T) > log2 T − E` always); using it as "the residual"
under-states the bill and over-states reach. The exact residual is `c_mean`.

## The discriminating test (MEASURED — `E-explosion-amp_ambiguity_ledger.py`)

Clean Monte-Carlo, `q = 2^-2.5 ≈ 0.1768` an explicit parameter (NOT
luck-hashing): per record draw `Binomial(T-1, q)` surviving wrong steps, count
complete readings.

**Part B — log2 S is MULTIPLICATIVE in N** (the information-explosion
signature, NOT a fixed compute multiplier). Measured `mean(log2 S)` matches
`N · c_typ(T)` to < 1% across N ∈ {4..256}, T ∈ {2..8}, where `c_typ(T) =
E[log2 m]` (the typical/median constant; `c_typ < c_mean` by Jensen — the mean
E[S] is inflated by rare high-survivor draws, and it is `c_mean` that governs
the checksum cliff). Sample (T=8): measured 4.08, 8.38, 16.04, 32.15, 63.97,
129.78, 258.20 vs predicted `N·c_typ` 4.03, 8.06, 16.11, 32.23, 64.46, 128.91,
257.83 for N = 4,8,16,32,64,128,256. Multiplicative, exact.

**Part C — the checksum CLIFF, observed at toy N by shrinking k.** For a k-bit
checksum, P(some wrong reading sneaks through) rises from ~0 to ~1 as N crosses
`N* = k / c_mean(T)`:

| T | c_mean | k=8: N* / measured P at N≈N* | k=16: N* | k=24: N* |
| ---: | ---: | --- | ---: | ---: |
| 4 | 0.614 | 13.0 / P(13)=0.37→P(19)=0.76 | 26.1 | 39.1 |
| 8 | 1.162 | 6.9 / P(6)=0.29→P(10)=0.85 | 13.8 | 20.7 |

The cliff MOVES with k exactly as `k/c(T)` predicts. With a small checksum
(k=8) it sits at toy N — **proving the ambiguity is an information ceiling the
64-bit checksum merely POSTPONES to N ≈ 64/c(T)**, not a compute knob. Above
the cliff, unique decode demands `c(T)` extra STORED bits per record.

## Currency — CORRECTED

| mechanism | currency | bits |
| --- | --- | --- |
| explosion check (free source) | `structure-free` | `+E ≈ 2.5` b/rec, FINITE |
| global checksum (free source) | `structure-free` (global) | `k` bits total → `k/N → 0` b/rec |
| **leak past the joint ceiling `N·c_mean(T) ≤ k`** | **`stored-bits`** | `c_mean(T) = log2(1+(T−1)q)` b/rec (→ `log2 T − E` for large T); compute was the toy-scale SYMPTOM |
| period-P schedule (round 1) | `match-supply` (and moot) | informationally vacuous; refuted |

**Primary currency for lane E: `structure-free` (finite 2.5 b/rec + global
checksum → 0/rec) → `stored-bits` (`c_mean(T)` per record) past the joint
ceiling `N·c_mean(T) ≤ 64`.** This corrects round 1, which named `compute`;
compute is what you SEE at toy N (the DFS branches), but the underlying
conserved quantity is information: at scale the 64-bit checksum cannot referee
`(1+(T-1)q)^N` readings, and the deficit is paid in stored tag bits — exactly
MATH_MODEL §7b ("the file hash is 64 bits, not records × log2 T") instantiated
for the explosion channel.

## COUNTING GATE — answered sharply

**Q: explosion check free + content-blind + unbounded ⇒ random data
net-compresses without bound?** That is a pigeonhole violation. **A: it is NOT
unbounded.** Free budget = `E = 2.5` bits/record (FINITE; content-blind, so a
wrong-salt digest survives the parse with the SAME fixed rate `q = 2^-E` — a
filter, not an oracle) + a GLOBAL `k`-bit checksum that amortizes to `k/N → 0`
per record. The requirement is `log2(T)` bits/record. Free unique decode needs
the surviving-reading information to fit the checksum: **`N · c_mean(T) ≤ k`**,
with `c_mean(T) = log2(1+(T−1)q) > 0` for all T ≥ 2. This is a **joint (N,T)
ceiling**, not a free pass count: for any fixed T ≥ 2 decode fails past
`N*(T) = k/c_mean(T)` records, and as N → ∞ the free pass-reach → **T = 1**. No
T ≥ 2 is free at unbounded N. The residual `c_mean(T)` is uncovered by anything
free and must be paid in **stored bits** (tags). **Sharp impossibility** — no
free, content-blind, unbounded channel exists; the reach is a finite *joint*
(N,T) region, and the leak's currency is **stored-bits**.

## EVIDENCE CLASSES (round 2)

- The reach `K = 2^E ≈ 5.66` and the ledger `c(T) = log2(1+(T-1)q)`:
  **proven-by-math** (independence + counting + the uniform-hash law).
- `log2 S` multiplicative in N (= `N·c_typ`, < 1% error): **measured**
  (`E-explosion-amp_ambiguity_ledger.py` part B, q-explicit MC).
- The checksum cliff at `N* = k/c_mean(T)`, moving with k:
  **measured** (part C, k ∈ {8,16,24}, T ∈ {4,8}).
- Round 1's DFS toy lacks the explosion check (every digest parses, 0
  explosions in 2000 draws): **measured** — so its compute curve was a
  combinatorial artifact, the currency correction stands.
- The `q = 2^-E` identification remains a **conjecture** in its exact constant
  (2.5 is the measured row-7 budget; per-step independence is an idealization).

## NEXT (round 2)

The stored-bits floor `c_mean(T) = log2(1+(T−1)q)` is the price of decoding past
the joint ceiling `N·c_mean(T) ≤ 64`. The one remaining free lever the gate did
not close: whether `E` itself can be raised above 2.5 by a RICHER
self-delimiting record grammar (more parse constraints per record ⇒ lower
`q = 2^−E` ⇒ smaller `c_mean(T)` ⇒ a larger free (N,T) region). Raising E
shrinks `c_mean` but never to 0 for T ≥ 2, so it widens the finite joint region
without removing the impossibility — and E is bounded by the record's own bit
length (a record of `r` bits cannot supply more than `r` bits of
parse-constraint; smallest record is 7 bits, SPEC §3). Quantify the max E
achievable per record at B=8 / J3D1 Lotus from the format arithmetic
(`golden_format_arithmetic.json`), giving the widest achievable free region.
(Lane G's ≤1-bit parity channel is the orthogonal additive lever — it adds a
fixed `+1` to the free budget; lane E's is this `q`-lowering one.)
