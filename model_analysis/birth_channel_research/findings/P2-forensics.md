# P2 FORENSICS — does the repo's "multi-pass decode PROVEN, zero metadata" headline SCALE for bundles?

**Lane:** Phase-2 forensics (the hinge). Dissect how `v1_roundtrip_proof.py`
(the 36/36 proof) actually recovers BUNDLE birth epochs, and whether it scales.

**VERDICT (one line):** The headline is **honest about storage (zero birth-epoch
bits) but does NOT scale**. Bundle birth-epoch recovery is **not** a free
position fingerprint — the candidate-generation filter is **content-blind**
(provably: 321 distinct-content wires → identical candidate sets), so it cannot
pin the content-determined epoch; all epoch disambiguation falls on the fixed
256-bit header hash via a **DFS branching search** whose cost grows steeply and
multiplicatively in T (Lane B's `S=T^R`, measured: native `fork_budget=128`
blown ~54× by T=7). The 36/36 lives entirely inside Lane E's free region and
inside a hand-sized fork budget. **Confined to K≈5–6 passes; the bill is paid
in `compute`. Scoped impossibility: position structure cannot freely convey the
bundle epoch — the epoch is a content quantity.**

---

## Q1 — When an arity-k bundle collapses to ONE record, what happens to the other k−1 slots? TRACKED (stored bits) or STREAM SHRINKS (needs epochs)?

**Answer: the STREAM SHRINKS. Occupancy is never a stored field; it is implicit
in enumeration order. The decoder must therefore re-derive child placement, and
that derivation needs the birth epoch k (line 191).**

The state model is constant-N internally but the *wire* shrinks:

- The encoder's `arr` stays length N forever — `apply_shuffle` (lines 133–136)
  shuffles all N indices every pass; bundling never removes entries from `arr`.
  Coverage of the k−1 absorbed slots is positional, via the dict `cov`
  (line 87: `if any(x in cov for x in idxs): i += 1; continue`), **never an
  explicit stored field.** So there is no PCTB occupancy tax.

- But the **wire is shorter than N items**. Serialization (lines 122–130):
  ```python
  for r in records:
      slots = sorted(fpos[x] for x in r["children"])
      first[slots[0]] = r
      skip.update(slots[1:])          #  <-- the k-1 other slots emit NOTHING
  ...
  for p in range(N):
      if p in skip: continue          #  <-- skipped: wire shrinks by k-1 per bundle
      if p in first: bits += cw + seed
      else:          bits += "00" + literal
  ```
  An arity-k bundle emits **one** codeword+seed; the other k−1 slots emit
  nothing. The stream physically shrinks by k−1 per bundle.

- Because the stream shrank, the decoder cannot know where the k children
  belong without unwinding the permutation — and **unwinding requires k**.
  This is the load-bearing line (try_decode, line 191):
  ```python
  for j in range(a):
      x = sig_pow(bwd, q + j, k - 1)   # place child j at its ORIGINAL slot
  ```
  Placing children at their original slots = unwinding **k−1** shuffles =
  needs k. **So Q1's answer is the "stream-shrinks ⇒ needs birth epoch" branch.**
  The epoch is **derived by search** (next question), not stored. No stored bits.

**Currency for Q1:** stored bits = **ZERO** (genuinely; the headline is honest
on this narrow point). The cost is displaced into the *search* that derives k.

---

## Q2 — Real affine-stride FINGERPRINT (O(1) candidates) — or does 36/36 just live in Lane E's free region?

**Answer: NEITHER a clean O(1) fingerprint NOR the explosion check. It is an
exhaustive linear scan over all T candidate epochs + a geometric consistency
filter + the HEADER HASH as referee. The index arithmetic does NOT pin the
epoch; the checksum does the disambiguation. And yes, it also happens to live
deep inside Lane E's free region — but that is a *separate* fact.**

### (a) The mechanism is a scan, not a closed form (try_decode, lines 172–195)

```python
# bundle: infer (k, j0) by the T-candidate index-arithmetic test
cands = []
for k in range(1, T_try + 1):              # <-- LINEAR SCAN over ALL epochs 1..T
    shifts = T_try - k + 1
    p0 = sig_pow(bwd, slot, shifts)
    for j0 in range(a):
        q = p0 - j0
        if q < 0 or q + a > N: continue
        F = [sig_pow(fwd, q + j, shifts) for j in range(a)]
        if min(F) != slot: continue        # geometric consistency filter
        if any((f != slot) and (f in filled) for f in F): continue
        if any(f < slot and f != slot for f in F): continue
        cands.append((k, q, F))
if len(cands) > 1: forks += len(cands) - 1 # <-- MORE THAN ONE survives => fork
...
for (k, q, F) in cands:
    exp = H_bits(f"{seed}|p{k}", a * B)     # try each survivor; the only true
    ...                                     # arbiter is sha256==want_hash (decode())
```

There is **no closed-form stride read-out**. The decoder tries every epoch and
keeps whatever survives a geometric filter; ties are forked and ultimately
settled by `sha256(out)==want_hash` in `decode()` (lines 203–205).

### (b★) THE SHARP IMPOSSIBILITY — the candidate set is CONTENT-BLIND, so a position filter provably cannot pin the (content-determined) epoch

The candidate-generation loop (lines 173–183) reads **only** `sig_pow`,
`filled`, `N`, `a` — **zero block content**. Content enters decode in exactly
two later places: the expansion `H_bits(f"{seed}|p{k}",...)` and the final
`sha256==want_hash`. Therefore the surviving-candidate set `{(k,q,F)}` is a
function of **geometry alone**, while the birth epoch is a **content** quantity
(which pass a span matches depends on the span's bits vs the per-pass salt
`p{t}`). A position-only function cannot read a content quantity.

**Measured proof (`probe_content_blind.py`):** 321 DISTINCT-content wires that
share one wire structure (`R3 R1 R3 R1 R2 R2 R1 R2 R1`, N=16, T=5) produce
**byte-identical candidate sets**. And the filter barely narrows the epoch:

```
bundle@slot0 a=3:  5 candidates, epochs k in {1,2,3,4,5}   <- ALL 5 epochs survive
bundle@slot2 a=3: 13 candidates, epochs k in {1,2,3,4,5}
bundle@slot4 a=2: 10 candidates, epochs k in {1,2,3,4,5}
bundle@slot5 a=2:  6 candidates, epochs k in {1,2,3,4,5}
bundle@slot7 a=2:  4 candidates, epochs k in {1,3,4}
```

For most bundles **every** epoch 1..T survives the geometric filter — position
contributes *no* epoch information; 100% of epoch disambiguation is dumped on
the 256-bit header hash. This directly kills the brief's named bundle escape
hatch ("a k-slot span gives k position observations vs 2 unknowns"): **more
*position* observations still cannot determine a *content* quantity**, which is
why forks keep growing with T even at fixed arity k=2,3. (The identical fork
counts in Q3's table across different files — 3388,3388,3388; 6874×3 — are the
same content-blindness showing up as deterministic search cost.)

### (b) Corroborating test — shrink `fork_budget`. If a position fingerprint pinned (k,j0), budget=2 would suffice. It does not.

`forensics_scale_probe.py`, three phases (N=16, real SHA throughout):

| fork_budget | T=2 | T=3 | T=4 | T=5 | T=6 |
|------------:|:---:|:---:|:---:|:---:|:---:|
| 128 (native)| OK  | OK  | OK  | OK/FAIL | FAIL |
| 10          | OK  | OK  | **FAIL** | FAIL | FAIL |
| **2**       | **FAIL** | **FAIL** | FAIL | FAIL | FAIL |

**`fork_budget=2` FAILS even at T=2.** A genuine O(1) `(k,j0)` fingerprint
leaves `len(cands)==1` at every bundle → `forks` stays 0 → a budget of 2 is
plenty. It doesn't. This corroborates (b★): the index arithmetic leaves
*multiple* candidate `(k,j0)` per bundle, and the 256-bit header hash does the
disambiguation. (`fork` counts conflate epoch k and offset j0; the content-blind
test in (b★) is the cleaner statement that the *epoch* specifically is unpinned.)

### (c) Lane E free-region check — N·c_mean for the proof's ACTUAL N, T

The relevant N is the number of records carrying birth ambiguity = **bundles**
(singles are k-free: keyed by `s|s{x}` = original slot, lines 109 & 166, no k).
With q = 2^−2.5 = 0.177, c_mean(T) = log2(1+(T−1)q):

- 36/36 regime per-file worst case: **N_bund=5, T=5 → N·c_mean = 3.86 bits ≪ 64.**
  Every 36/36 file is **deep in the free region** — births are essentially free
  there. So the 36/36 *also* lives in Lane E's free region, confirming the
  brief's framing. (This is independent of, and consistent with, the fork
  finding: free region ≠ free decode mechanism — see Q3.)

**Conclusion Q2:** no real fingerprint. The bundle epoch is recovered by
**search + checksum**, and the 36/36 only works because (i) it is in the free
region and (ii) the native fork budget happens to be big enough at T≤5.

**Currency for Q2:** `compute` (DFS refereed by the fixed header hash) — NOT
`structure(free 2.5 bits)` and NOT `stored bits`.

---

## Q3 — Does decode do SEARCH that grows with N or T? Measured & bounded.

**Answer: YES, and it grows multiplicatively (~2× per pass). This is Lane B's
`S=T^R` survivor explosion reappearing for bundles.**

`decode()` loops `T_try = 1..T_max` (line 200). For each, `try_decode` is a DFS
that **forks on every bundle with >1 surviving candidate** (line 184), capped at
`fork_budget=128` (line 185: `if forks > fork_budget: return`). Hitting the cap
makes a branch return early; if the correct epoch is on a pruned branch, decode
returns **None** (silent failure).

### Measured forks at the CORRECT epoch (real SHA, `probe_none_fast.py`, budget=20000)

| N  | T=2 | T=3 | T=4 | T=5 | T=6 | T=7 |
|---:|:---:|:---:|:---:|:----:|:----:|:----:|
| 10 |  9  |  25 |  90 |  99  |  92  | —    |
| 16 |  15 |  88 | 157 | 171  | **3388** | **6874** |
| 20 |  ~7 | 142 | 178–546 | 181 | **5165–5892** | — |

- Growth N=16: T=4→157, T=5→171, **T=6→3388 (×19.8)**, **T=7→6874 (×2.03)**.
  Growth is steep and multiplicative (the `k` loop adds a factor per pass; j0 is
  bounded by arity). It is irregular, not a clean ×2: the encoder ceiling
  saturates *effective* passes near 5, so the jump lands once deep epochs first
  appear (T=5→6). Headline: native `fork_budget=128` blown **~54×** by T=7.
- **The native `fork_budget=128` is blown by ~54× at T=7** (6874/128). Every
  None case from Phase A (N=16 T=6,7; N=20 T=4,6,7) was confirmed
  **BUDGET-KILLED, not structural**: each recovers exactly (`out==orig`,
  `T_found==T`) at `fork_budget=20000`. So decode is *correct but exponentially
  expensive*, and the fixed budget is a hard wall at K≈5–6.
- (The T_found < T "FAIL" rows at the native budget — e.g. N=10 T=7→3 — are a
  **benign** second effect: the encoder's `accepts_per_pass=2` + `max_seed=9000`
  exhausts matches by ~4–5 effective passes, so the wire is *bit-identical*
  to a lower-T wire — `probe_t8_anomaly.py`: `wire_equal=True` in 100% of cases.
  This is the ENCODER ceiling, why the toy never stressed the DECODER ceiling.)

**Two independent ceilings, do not conflate:**
1. **Encoder ceiling** (`accepts_per_pass=2`, `max_seed=9000`): effective passes
   cap at ~4–5; nominal T beyond that produces identical wire. This is why the
   36/36 toy never generated a deep-epoch bundle to stress the decoder.
2. **Decoder ceiling** (DFS fork explosion vs fixed `fork_budget=128`): the
   real "does it scale?" wall. Forks grow ~2×/pass; budget 128 dies at T≈6.

---

## COUNTING GATE

If the bundle-epoch channel were free + content-blind + unbounded, random data
would net-compress without bound (births are uniform hash outcomes,
incompressible by Shannon) — a pigeonhole violation. **Where is the leak?** It
is NOT a stored field (epoch storage is genuinely 0 bits). The leak is that
**a *fixed* 256-bit referee can disambiguate only a bounded survivor set, and a
*fixed* fork budget caps the search.** As N bundles and T passes grow, the
survivor count is multiplicative (~T^bundles) — exactly Lane B's "the checksum
must grow to N·log2(T)," here wearing a **compute** hat. The channel is free
only while `forks ≪ budget` AND `survivors ≪ what 256 bits can pin`. That is a
**finite K**, not ∞.

---

## OUTPUT BLOCK

```
AVENUE: P2-forensics (bundle birth-epoch decode mechanism)
HYPOTHESIS: the affine-stride "fingerprint" is really checksum-refereed search,
  not an O(1) read-out; 36/36 lives in Lane E's free region and a hand-sized
  fork budget; it will not scale past ~6 passes for bundles.
MECHANISM: encode shrinks the wire (skip slots[1:]); decode re-derives child
  placement via sig_pow(bwd, q+j, k-1) which NEEDS k; k is found by a linear
  scan over 1..T_try + geometric filter, ties forked, settled by sha256 header.
RESULT: sharp-impossibility SCOPED to the position-fingerprint claim
  ("affine-stride position structure cannot freely convey the content-determined
  bundle epoch") / partial(reach K≈5–6 passes, paid in compute). NOT a claim
  that no bundle epoch channel can exist (see NEXT).
EVIDENCE:
  - proven-by-math (counting gate + code inspection), backed measured:
    candidate set is content-blind (lines 173-183 read geometry only); 321
    distinct-content wires -> byte-identical candidate sets, every epoch 1..T
    survives the geometric filter for most bundles; probe_content_blind.py.
  - proven-by-construction: fork_budget=2 fails even at T=2 (no O(1) (k,j0)
    fingerprint); forensics_scale_probe.py.
  - measured: forks@correct epoch grow ×2/pass (N=16: 171→3388→6874 for T=5,6,7),
    native budget=128 blown ×54 at T=7; probe_none_fast.py.
  - measured: all native-budget None cases are budget-killed not structural
    (recover exactly at budget=20000); probe_none_fast.py.
  - proven-by-construction: benign encoder ceiling — wire_equal=True at lower
    effective T in 100% of high-T files; probe_t8_anomaly.py.
  - proven-by-math: 36/36 per-file N·c_mean = 3.86 bits ≪ 64 (deep free region).
  would-the-test-work: yes — these are counting/logic tests with real SHA, not
    luck-dependent match hunts; matches are planted by the encoder's own search.
CURRENCY: compute. Birth-epoch stored bits = 0. The bill is a DFS refereed by a
  fixed 256-bit hash, branching ~T^bundles; same wall as Lane B's growing
  checksum, displaced into compute. Bounded reach K≈5–6 at the native budget.
NEXT: quantify the exact fork-growth exponent per bundle vs (gap, arity) to
  pin K(budget) closed-form; and test whether a per-bundle stride read-out
  (true O(1), making forks==0) is constructible — if it is, the channel moves
  from compute to free, but the fork=2 result says the CURRENT code is not it.
```

### Bottom line for the Phase-2 hinge

The repo's "multi-pass decode PROVEN, zero metadata" headline is **true as a
storage statement and false as a scaling statement.** For bundles it does **not**
scale past ~6 passes: the birth epoch is recovered by an **exponentially growing
checksum-refereed search**, not a free arithmetic fingerprint. It is **confined
to Lane E's free region** by two independent ceilings (encoder match-exhaustion
at ~5 effective passes; decoder fork-budget at ~6 passes). **The single
keystone** that would change the verdict is a genuine per-bundle O(1)
epoch read-out (forks≡0) — which the current code provably does NOT have
(fork_budget=2 fails at T=2).

---

### Artifacts (all in `model_analysis/birth_channel_research/`)
- `probe_content_blind.py` — proves candidate set is content-blind (321
  distinct-content wires → identical candidate sets). THE sharp impossibility.
- `forensics_scale_probe.py` — extends T,N; varies fork_budget (Phases A/B/C).
- `probe_t8_anomaly.py` — proves the benign encoder ceiling (wire_equal).
- `probe_none_fast.py` — discriminates None cases; measures forks@correct epoch.
