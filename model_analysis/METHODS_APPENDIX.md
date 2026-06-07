# Methods Appendix — exact model behind the arity/headroom results and the arity→size curve

**Scope.** This document specifies, mechanically, the models that produced (a) the
headroom-distribution columns (arity 1/2/3, max headroom 5/11/17), (b) the
arity→size curve 145.833% → 125.000% → 111.667% → 106.667% → 101.750% → 100.958%
→ 100.121%, and (c) the multi-pass ledger and block×arity sweep. It argues
nothing. It contains definitions, formulas, parameters, code, raw tables, and the
assumptions the results are most sensitive to. Two discrepancies found during
this write-up are documented in §6.3 (they are disclosed, not hidden).

**Artifact inventory.** Four scripts in `model_analysis/`, all rerunnable:

| file | produced | type | recursion |
|---|---|---|---|
| `variability_test.py` | headroom columns, max-headroom 5/11/17 | live enumeration (blake2b) | one-pass, raw spans |
| `arity_floor.py` | the 145.833 → 100.121 curve | analytic (no hashing) | **one-pass** (see §7) |
| `breakeven_landscape.py` | seed-depth sweep (flat 112.5% column) | analytic | one-pass |
| `recurrence_model.py` | pass-by-pass ledger; B×A sweep | analytic | **recursive** (passes 2+ on current entries) |

---

## 1. Variable definitions

| symbol | meaning | values used |
|---|---|---|
| `b` | block size in **bits** | `variability_test`: 6 (chosen so search is exhaustive). All others: 16 / 24 / 32 / 40 (= 2/3/4/5 bytes); the quoted curve is `b = 24` |
| `A` | arity = number of contiguous units bundled into one seed record | 1–5 canonical; 10/16/50/64/100/1000 via the §1.1 extension |
| `S` | span size in bits, as a function of `A` | pass 1: `S = A·b` (raw content). Passes 2+: `S = A · (current mean entry length)` — concatenated **encoded entry bits**, not raw bytes |
| raw denominator | the divisor of every percentage | curve: the span's raw content `A·b` (equivalently `N·b` for a fully tiled file). Recurrence ledger/sweep: `raw = N·b`, `N = 1,000,000` blocks. Depth sweep: per-block `b` |
| initialized size | file size after the one-time literal wrap | `N·(b + 3)` if everything wraps (= 112.5% at b=24); pass 1 may replace runs instead (§3) |
| literal marker cost | `'111'` codeword, charged **once** at initialization, never re-charged | **3 bits** |
| arity header cost `ac(A)` | canonical Kraft alphabet | `1→'00'` 2 b, `2→'01'` 2 b, `3→'100'` 3 b, `4→'101'` 3 b, `5→'110'` 3 b |
| seed payload cost `p` | bit-length of the seed index `i` | `p = max(1, bitlen(i))` |
| J3D1 seed field | jumpstarter (3 b, fixed) + one length field `w = max(1, bitlen(p))` + payload `p` | `J3D1(p) = 3 + w + p` |
| total record cost | `R(A, i) = ac(A) + 3 + w + p` | e.g. arity 1, index 100: `2 + 3 + 3 + 7 = 15` bits |
| targets | what the seed expansion must equal | pass 1 / `variability_test` / curve: **raw spans**. `recurrence_model` passes 2+: **current recursive Telomere entries** (encoded bits, headers included) |

### 1.1 Arity-code extension beyond A=5 (assumption, flagged)

The canonical alphabet ends at 5. For A > 5 the curve and sweep used
`ab(A) = max(3, bitlen(A) + 1)` — a prefix-free-plausible extrapolation, **not
part of the spec**. Every A ≥ 10 value moves 1:1 with this choice (§10, item 3).
`arity_floor.py` applied `ab(A)` to *all* A including 1–5, which differs from the
canonical alphabet by 1 bit at A ∈ {1, 2, 5}; reconciled in §6.3.

---

## 2. What "equal depth for each bundle size" meant (`variability_test.py`)

**Equal relative coverage of the target space:** for span size `S = A·b`, exactly
`K_A = C · 2^S` seeds were enumerated, with `C = 4`, i.e. four times the number
of possible S-bit values, per arity:

| arity | S | seeds enumerated `K_A` |
|---|---|---|
| 1 | 6 | 256 |
| 2 | 12 | 16,384 |
| 3 | 18 | 1,048,576 |

So: **not** equal maximum seed bit-length, **not** equal absolute seed count,
**not** equal distance from any threshold. Equivalent statement: full enumeration
of all seeds of index bit-length ≤ S + 2 for each arity. Rationale for the
control: at equal *absolute* count, the smallest span would be covered ~2^12×
more densely than the largest and its headroom column would be inflated by
over-search rather than by any property of bundling. With `C = 4`, expected
fraction of targets hit is `1 − e^{−4} = 98.17%` for every arity (measured:
63/64, 4022/4096 = 98.2%, 257,335/262,144 = 98.2% — matches).

In the analytic artifacts (`arity_floor`, `breakeven_landscape`,
`recurrence_model`) depth is **unbounded**: search runs to the first match for
every span, however deep (option "full search up to and beyond the maximum
compressive seed length"). The expected first-match index for an S-bit target is
~`2^S` (P(found among the first `2^{S+k}` seeds) = `1 − exp(−2^k)`), so the
"compute required" column in §6 is `2^S = 2^{24A}` hash evaluations per span.

---

## 3. Exact acceptance conditions

| artifact | acceptance test |
|---|---|
| `variability_test.py` | none — it measures, it does not select. Every hit target's minimum-cost seed is recorded regardless of profitability |
| `arity_floor.py` (curve) | none — it prices full tiling at each A unconditionally (counterfactual floor; see §6.2 and §7) |
| `recurrence_model.py` pass 1 | replace a run of `A` raw blocks iff `R(A, i) < A·(b + 3)` (strictly smaller than the **wrapped-literal alternative**) and the hit is reliably available under full search (`P > 0.5`); otherwise blocks wrap once |
| `recurrence_model.py` passes 2+ | replace a window of `A` current entries iff `R(A, i) <` (sum of those entries' **current encoded bits**), strictly |

Literals: wrapped **once** at initialization (+3 bits each), never re-charged in
any later pass, in every artifact.

Equal-length matches: **rejected** everywhere (strict `<`). They are not counted
as wins and not stored as fallbacks; superposed-candidate retention is not
explicitly simulated (it is subsumed by the unbounded-search ceiling — flagged
as assumption 5, §10).

---

## 4. Exact headroom definition

In `variability_test.py`:

```
headroom(target) = S − max(1, bitlen(i_min))        [raw-index headroom]
```

where `i_min` is the lowest-index seed whose expansion's S-bit value equals the
target. **This is seed-name bits only** — it deliberately excludes the arity
code, jumpstarter, and length field, to isolate the distribution's shape from
the fixed framing constants. Full-record headroom = raw-index headroom −
`(ac(A) + 3 + w)`. So the columns answer "how much shorter than the span is the
shortest *index* that names it"; subtract framing to get net record profit.

Computed per arity (`b` = 6 for the measured rows; law rows are content-size–independent):

| arity | S | measured? | max possible headroom (= S − 1) | measured max |
|---|---|---|---|---|
| 1 | 6 | yes (exhaustive) | 5 | 5 |
| 2 | 12 | yes (exhaustive) | 11 | 11 |
| 3 | 18 | yes (exhaustive) | 17 | 17 |
| 5 | 30 (b=6) | no — `K = 4·2^30` exceeds the run budget | 29 | — (law: §5) |
| 100 | 2400 (b=24) | no — unenumerable | 2399 | — (law: §5) |
| 1000 | 24000 (b=24) | no — unenumerable | 23999 | — (law: §5) |

The ceiling `S − 1` exists because the cheapest possible name is index 0 at the
1-bit cost floor: `headroom ≤ S − 1`. In an exhaustive enumeration the value
expanded by seed 0 is itself among the targets, so the ceiling is attained
deterministically — that is why the measured maxima are exactly 5/11/17.

---

## 5. The distribution calculation

### 5.1 Measured (live enumeration — this artifact only)

- expander: `blake2b(i.to_bytes(6,'little'), digest_size=4)`, masked to the low
  `S` bits (`& ((1<<S)-1)`)
- seed cap: `K_A = 4·2^S` per arity (§2); enumeration `i = 0 … K_A−1`, no RNG,
  no sampling, no input files — the target space is enumerated, not drawn from
  a corpus
- per target: minimum `max(1, bitlen(i))` over all hitting seeds, via
  `np.minimum.at`
- sample size: every hit target (63 / 4,022 / 257,335)

### 5.2 Analytic law (no hashing)

Seeds of index bit-length ≤ `S − d` number `2^{S−d}`; each equals a *specific*
S-bit value with probability `2^{−S}`, independently. Hence

```
P(headroom ≥ d) = 1 − (1 − 2^{−S})^{2^{S−d}} ≈ 1 − exp(−2^{−d})
```

**independent of S** — the same curve for every arity and block size. Agreement
with the measured columns:

| d | law `1−e^{−2^{−d}}` | arity 1 (meas.) | arity 2 (meas.) | arity 3 (meas.) |
|---|---|---|---|---|
| 1 | 0.3935 | 0.4444 | 0.4010 | 0.4000 |
| 2 | 0.2212 | 0.2540 | 0.2268 | 0.2249 |
| 3 | 0.1175 | 0.1270 | 0.1191 | 0.1193 |
| 4 | 0.0606 | 0.0635 | 0.0619 | 0.0617 |
| 5 | 0.0308 | 0.0317 | 0.0311 | 0.0314 |
| 6 | 0.0155 | 0 (ceiling) | 0.0159 | 0.0158 |
| 8 | 0.0039 | — | 0.0040 | 0.0040 |
| 11 | 0.0005 | — | 0.0005 | 0.0005 |

(The arity-1 column sits slightly above the law at small `d`: 63-target universe
plus the `max(1,·)` cost floor; it is a finite-size effect of the smallest
configuration, visible only there.)

### 5.3 Why max grows with arity; why the mean does not (in this model)

- **Max:** expected maximum of `T` draws from `P(≥d) ≈ 2^{−d}` is ≈ `log2(T)`,
  and the structural ceiling is `S − 1`. Exhaustive coverage (`T ≈ 2^S`) pins
  the observed max at the ceiling, which grows linearly in `A`: 5 → 11 → 17.
- **Mean:** `E[headroom] = Σ_{d≥1} P(≥d) = Σ_{d≥1} (1 − e^{−2^{−d}}) = 0.8546`,
  a convergent sum whose terms halve. Raising the ceiling from 5 to 17 adds
  `Σ_{d=6..17} ≈ 0.031` — that is the entire mean contribution of the extended
  tail, which is why the measured means moved only ~0.92 → 0.86.
- Consistency check: `E[headroom | headroom ≥ 1] = 0.8546 / 0.3935 = 2.172`,
  matching the independently measured per-win savings constant **2.17** used in
  `recurrence_model.py` (`e_save`). The two artifacts agree through the law.

---

## 6. The arity→size curve, exactly

### 6.1 Formula

For block bits `b = 24`, content `c = A·b`:

```
w(A)      = max(1, bitlen(c))                       # J3D1 length field
framing(A)= ab(A) + 3 + w(A)                        # arity code + jumpstarter + length field
payload   = c                                       # bitlen of expected first matching index (§2)
record(A) = c + framing(A)
curve(A)  = 100 · record(A) / c  = 100 · (1 + framing(A)/c)
```

### 6.2 Per-value table (as published, `ab(A) = max(3, bitlen(A)+1)`)

| A | raw bits represented `c` | expected selected seed length | `ab` | `w` | `framing` | expected record bits | wrapper bits in this cell | final % | search depth required |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 24 | 24 | 3 | 5 | 11 | 35 | 0 | **145.833%** | ~2^24 |
| 2 | 48 | 48 | 3 | 6 | 12 | 60 | 0 | **125.000%** | ~2^48 |
| 5 | 120 | 120 | 4 | 7 | 14 | 134 | 0 | **111.667%** | ~2^120 |
| 10 | 240 | 240 | 5 | 8 | 16 | 256 | 0 | **106.667%** | ~2^240 |
| 50 | 1200 | 1200 | 7 | 11 | 21 | 1221 | 0 | **101.750%** | ~2^1200 |
| 100 | 2400 | 2400 | 8 | 12 | 23 | 2423 | 0 | **100.958%** | ~2^2400 |
| 1000 | 24000 | 24000 | 11 | 15 | 29 | 24029 | 0 | **100.121%** | ~2^24000 |

Wrapper bits are 0 in tiled cells (a tiled run carries no literal markers); the
wrap-only alternative is `(24+3)/24 = 112.500%` and is what the strict encoder
actually does whenever tiling fails the §3 bar.

### 6.3 Two discrepancies found while writing this appendix (disclosed)

**(i) Arity-code convention.** `arity_floor.py` charged `ab(A) = max(3,
bitlen(A)+1)` uniformly; the canonical alphabet is 1 bit cheaper at A ∈ {1, 2}
(2 b) and at A = 5 (3 b). **(ii) First-match credit.** The curve sets payload =
`c` exactly; the law in §5.2 says the first match is shorter than typical by
`E[headroom] = 0.855` bits on average, which the curve does not credit.
Corrected columns:

| A | as published | canonical alphabet | canonical + 0.855-bit first-match credit |
|---|---|---|---|
| 1 | 145.833% | 141.667% | 138.106% |
| 2 | 125.000% | 122.917% | 121.136% |
| 5 | 111.667% | 110.833% | 110.121% |
| 10 | 106.667% | 106.667% | 106.311% |
| 50 | 101.750% | 101.750% | 101.679% |
| 100 | 100.958% | 100.958% | 100.923% |
| 1000 | 100.121% | 100.121% | 100.117% |

Every correction lowers the values; none changes their ordering or sign relative
to 100%. (`recurrence_model.py` already used canonical codes — its pass-1 value
110.833% at b=24/A=5 equals the corrected column, which is the cross-check.)

**Strict-bar note (b = 24, canonical codes):** under §3's pass-1 rule, tiling is
*accepted* only at A = 5 (record 133 < bar 135); A = 1–4 fail (34>27, 59>54,
85>81, 109>108) and would wrap instead. The A ∈ {1, 2} curve points are
therefore *counterfactual* tiling prices, not encoder outcomes.

---

## 7. One-pass vs. recursive — explicit status

**The 145.833 → 100.121 curve is not a full recursive Telomere model; it is an
arity-scaling one-pass model.** It prices a single tiling pass at each arity
under unbounded search. It is not presented as proving or disproving the
recursive design.

Recursion was modeled separately, in `recurrence_model.py`:

- passes 2+ operate on the **current entry landscape**, not raw bytes;
- **"a block is a block is a block" applies:** a bundled seed record becomes one
  atomic entry for all later passes (`A` entries merge to 1);
- later-pass spans are **concatenations of encoded entries** (headers included);
- **deterministic shuffles modeled:** zero stream bits, decoder-known; effect
  modeled as fresh disjoint `A`-windows every pass (`starts = n/A` per arity,
  re-drawn each pass); with reshuffle off, repeated adjacencies contribute no
  new trials after their first pass;
- **superposition:** *not* simulated as explicit retained-candidate state.
  Modeled as the unbounded-search ceiling — every span that has a qualifying
  seed under §3 is found. Retained noncompressive exact matches participating in
  later bundles are therefore covered only insofar as the ceiling covers them
  (assumption 5, §10);
- entry lengths are homogenized to the current mean (`avg = bits/n`) for the
  per-pass probability evaluation (assumption 5, §10).

---

## 8. Raw output tables

### 8.1 Headroom distribution — §5.2 table above (measured + law)

### 8.2 Seed-depth sweep (`breakeven_landscape.py`; b = 24, arity 1, framing gap 10, marker 3, e_save 2)

| depth k (seed bits) | seeds = 2^k | P(any match) | P(record < span) | net size |
|---|---|---|---|---|
| 10 | 2^10 | 0.0001 | 0.000122 | 112.5% |
| 14 | 2^14 | 0.0020 | 0.001951 | 112.5% |
| 20 | 2^20 | 0.1175 | 0.001951 | 112.5% |
| 30 | 2^30 | 1.0000 | 0.001951 | 112.5% |
| 100 | 2^100 | 1.0000 | 0.001951 | 112.5% |
| 1000 | 2^1000 | 1.0000 | 0.001951 | 112.5% |
| 100000 | 2^100000 | 1.0000 | 0.001951 | 112.5% |

(`net = 1 + ((1−P)·3 − P·2)/24`; the P(record<span) column saturates at depth
`k = S − gap = 14` because deeper seeds carry longer payloads.)

### 8.3 Pass-by-pass ledger (`recurrence_model.py`; b = 24, A ≤ 5, reshuffle on, N = 10^6)

| pass | action | % of raw | expected hits | bits saved |
|---|---|---|---|---|
| 1 | tile arity 5 | 110.833% | — | — |
| 2 | reshuffle | 110.833% | 32.2 | 70 |
| 3 | reshuffle | 110.832% | 64.0 | 139 |
| 4 | reshuffle | 110.832% | 63.3 | 137 |
| 6 | reshuffle | 110.831% | 61.8 | 134 |
| 8 | reshuffle | 110.830% | 60.5 | 131 |
| 10 | reshuffle | 110.829% | 59.2 | 129 |
| 12 | reshuffle | 110.828% | 58.1 | 126 |

### 8.4 Converged block×arity sweep (`recurrence_model.py`, 12 passes, % of raw)

| B \ A-cap | 1 | 2 | 5 | 16 | 64 |
|---|---|---|---|---|---|
| 2 B | 118.603% | 118.409% | 116.241% | 106.667% | 101.984% |
| 3 B | 112.451% | 112.386% | 110.828% | 104.687% | 101.389% |
| 4 B | 109.338% | 109.290% | 108.748% | 103.542% | 101.042% |
| 5 B | 107.485% | 107.466% | 107.000% | 102.969% | 100.873% |

### 8.5 All constants

| constant | value | where |
|---|---|---|
| literal marker | 3 bits, once | all |
| jumpstarter | 3 bits, fixed | all |
| arity codes ≤ 5 | 2/2/3/3/3 bits | canonical; `recurrence_model` |
| arity codes, extension | `max(3, bitlen(A)+1)` | `arity_floor` (all A), sweeps A > 5 |
| `e_save` (per accepted win) | 2.17 bits (= law's 2.172) | `recurrence_model` |
| `E[headroom]` | 0.8546 bits | law; §6.3 credit |
| N (blocks) | 1,000,000 | `recurrence_model` |
| C (coverage) | 4× target space | `variability_test` |
| expander | blake2b, 4-byte digest, low-S mask | `variability_test` only |
| passes | 12 | `recurrence_model` |
| pass-1 reliability gate | P > 0.5 | `recurrence_model` |

---

## 9. Code

Load-bearing functions, verbatim:

```python
def ac(A):                      # arity codeword bits
    if A <= 2: return 2         # '00', '01'
    if A <= 5: return 3         # '100', '101', '110'   ('111' = literal)
    return max(3, A.bit_length() + 1)        # EXTENSION (assumption 3)

def j3d1(p):                    # seed-index field: jumpstarter + length + payload
    p = max(1, p); w = max(1, p.bit_length())
    return 3 + w + p

def record(A, content_bits):    # expected record: first match ~ index 2^content
    return ac(A) + j3d1(content_bits)

def curve(A, b=24):             # §6 curve
    c = A * b
    return 100.0 * (c + (ac(A) + 3 + max(1, c.bit_length()))) / c

def p_headroom_ge(d):           # §5 law, content-size independent
    return 1 - math.exp(-2.0 ** (-d))

def p_compressive(A, S, bar):   # P(some seed's record < bar) for an S-bit span
    best = -1; p = 1
    while p <= S + 2:
        if ac(A) + 3 + max(1, p.bit_length()) + p < bar: best = p; p += 1
        else: break
    if best < 0: return 0.0
    return 1.0 if best >= S else 1 - math.exp(-(2.0 ** (best - S)))
```

`variability_test.py` measurement core (per arity, S = A·6, K = 4·2^S):

```python
pref[i] = blake2b(i.to_bytes(6,'little'), digest_size=4) & ((1 << S) - 1)
cost[i] = max(1, bitlen(i))
minc    = per-target minimum of cost over hitting seeds   # np.minimum.at
headroom = S - minc        # over the ~98.2% of targets hit
```

`recurrence_model.py` pass recurrence (pseudocode):

```
pass 1: per block, cheapest legal form = min( b+3 ,  min over A of record(A, A·b)/A
                                              s.t. record < A·(b+3) and P>0.5 )
state  = (n entries, total bits)
pass t: avg = bits/n
        for A in 1..cap:  S = A·avg
            hits  = (n/A) · p_compressive(A, S, bar=S)      # strict, no re-wrap
            saved += hits · 2.17 ;  merged += hits · (A−1)
        bits -= saved ; n -= merged ; repeat (reshuffle ⇒ windows re-drawn)
```

Rerun everything:

```
python3 model_analysis/variability_test.py
python3 model_analysis/arity_floor.py
python3 model_analysis/breakeven_landscape.py
python3 model_analysis/recurrence_model.py
```

The verification snippet that regenerated every number in §5–§6 of this
appendix (including the corrected columns) is reproducible from §9's functions;
all values matched at the printed precision.

---

## 10. Top 5 assumptions that would most alter the results if changed

1. **The uniform match law.** Every probability here descends from
   `P(expansion of seed i prefix-equals a given S-bit value) = 2^{−S}`,
   independent across seeds. Any systematic deviation of the expander from this
   law re-derives every column (§5, §8.2, §8.3).

2. **Later-pass spans obey the same law.** `recurrence_model.py` assigns
   concatenated-entry spans in passes 2+ the *same* `2^{−S}` law as pass-1 raw
   spans — i.e., it assumes the records chosen in earlier passes do not make
   later targets systematically easier for the same expander to hit. If chosen
   entries' encoded bits were biased toward the expander's own short-seed
   outputs, the pass-2+ hit columns in §8.3 rise above what is shown. This is
   the single assumption the recursive conclusion leans on hardest.

3. **The arity-code extension beyond A = 5.** `ab(A) = max(3, bitlen(A)+1)` is
   an extrapolation, not the spec. Every §6 value at A ≥ 10 — including
   100.958% and 100.121% — moves 1:1 in `framing(A)` with this choice; a
   cheaper wide-arity alphabet lowers the whole tail of the curve, a costlier
   one raises it. (The A ≤ 5 one-bit convention difference is already
   reconciled in §6.3.)

4. **Payload = bit-length of the first match, expected ≈ S bits.** The model
   takes the lowest-index match (shortest-first search) and prices its index at
   `S` bits, crediting the 0.855-bit expected first-match saving only in the
   §6.3 corrected column. Any selection rule or expander property that lands
   shorter indices *more often than* `P(≥d) = 1 − e^{−2^{−d}}` allows would
   shorten expected records below `c + framing − 0.855` and change §6 and §8
   directly.

5. **Selection and state simplifications in the recursive model.** Greedy
   disjoint windows (`n/A` starts per arity), entry lengths homogenized to the
   mean, reshuffle as freshly re-drawn windows at zero stream bits, and
   superposition represented by the unbounded-search ceiling rather than as
   explicit retained-candidate states that may complete into later bundles. Any
   of these, made richer, changes the hits/saved columns of §8.3; the ceiling
   substitution (superposition) is the largest structural simplification of the
   four.

*End of appendix.*
