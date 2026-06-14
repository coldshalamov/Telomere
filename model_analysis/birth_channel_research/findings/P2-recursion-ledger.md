# P2 — The recursion-ledger lane: layer-stacking economics at K free passes

Author: recursion-ledger researcher (lane P2). Date: 2026-06-13.
Toy: `model_analysis/birth_channel_research/P2-recursion-ledger.py`
(reuses the repo's accepted ledger `proof_kernel/golden_break_even.gain()`).

Addresses the user's actual goal — **recursive compression** — head-on with
numbers. Open question: MATH_MODEL_V1 §8 (Q2), GOLDEN_CONFIG §5/§7,
BRIEF "the legal recursion channel."

---

## AVENUE
Recursion / layer-stacking. Given MAX-FREE-REACH **K ≈ 5–6 passes per layer**
(birth channel free via the explosion check up to K, then it costs — lanes E/H),
quantify the economics of stacking layers: run K free passes, emit, then RE-RUN
the output as a fresh file (the legal recursion channel, SPEC §1).

## HYPOTHESIS (written before any test, from the mechanics)

Per layer: EARNINGS = coverage × E[win|hit] ≈ 2 bits; CARRIAGE = re-blocking
header + literal markers on the new blocking + any residual birth bill leaking
past K. At the content-blind base rate (p = 0.0039/window, ≈ 50× below the
threshold p\* ≈ 0.19), coverage over K ≈ 5.66 fresh draws is ~2%, so earnings
are ~0.04–0.05 bits/window while ~98% of windows stay literal and pay the
3-bit canonical marker. **Predict: per-layer net NEGATIVE** — the free birth
channel removes the log2(T) tax but NOT the wrap/carriage tax. **Predict
recursion does not rescue it**: content-blindness makes every layer identical
at the base rate, so the recursion's sign equals the single-layer sign (Q2
priced negative). **Predict the flip density = p\*** — the same density the
maintainer ruled content-aware.

## MECHANISM (precise construction)

- Golden Config: B = 8, canonical alphabet (literal marker = 3 bits), arity-2
  engine, E[win|hit] = 2.17 bits, p_base = 0.0039/window (all from
  GOLDEN_CONFIG §1/§3 and `golden_format_arithmetic.json`).
- **Per-layer ledger = the repo's own** `golden_break_even.gain()`, called at
  the base rate (density multiplier m = 1), with the per-pass birth charge `kb`
  forced to **0** within the layer (the explosion check pays birth free up to
  K — the entire premise of "K free passes"), and the pass count capped at the
  layer's fresh-draw budget. This keeps the accounting consistent with the
  maintainer's accepted numbers; we do NOT invent a fresh marker model.
- **Recursion** = treat the emitted stream as a new file (re-block, new N′,
  fresh coverage). Decode needs no epochs: the **layer boundary is the epoch,
  charged in carriage** (MATH_MODEL §8). This is the channel that resets the
  log2(T) birth tax to free each layer — at the price of per-layer carriage.

### The supply bracket (the one number that needs pinning — advisor #3)

K ≈ 5.66 is a **decode-disambiguation budget** (how many candidate birth passes
the explosion check resolves for free), NOT a match-supply count. Earnings
depend on fresh *match draws* per layer. Two honest readings bracket the truth:
- **(a) supply-rich** — each of the K passes gets a fresh shuffle + layer/pass
  salt (the deadlock of position-only salting,
  `freshness_law_validation.py:83`, is broken by the layer-index key, so dice
  DO refresh) ⇒ ~K ≈ 5.66 fresh draws/layer.
- **(b) supply-poor** — the maintainer's measured "effective passes ≈ 1"
  (MEMORY / net model) ⇒ ~1 fresh draw/layer.

The verdict (negative) holds in BOTH; (b) is simply more negative. We report
both rather than guess; the result's robustness is the point. Note that (b) is
also the *measured* end — "effective passes ≈ 1" is the maintainer's net-model
measurement — so the conservative bracket end is the empirical one, which only
strengthens "negative either way."

## RESULT — partial(reach below threshold), Q2 priced negative

`python P2-recursion-ledger.py` (exit 0), all numbers from the repo ledger:

### Q1 — Does K ≈ 5–6 free passes yield positive per-layer earnings at base rate? **NO.**

| supply / layer | coverage (ledger) | earn/bit | carriage/bit | **NET/bit** |
| --- | ---: | ---: | ---: | ---: |
| (a) ~K = 5.66 draws | 0.0446 | +0.0061 | 0.3583 | **−0.3522** |
| (b) ~1 draw         | 0.0077 | +0.0011 | 0.3721 | **−0.3711** |

Per-layer net is **negative in both readings**. The earnings (coverage × win,
~0.006 bits/bit even in the rich case) are swamped by the literal carriage on
the ~98% of windows that stay unclaimed. **The free birth channel removes the
log2(T) tax; it does not remove the wrap/carriage tax — and the wrap/carriage
tax is what sinks the layer.** (On the two coverage numbers: X = 0.0446 counts
*claimed blocks* — an arity-2 accept claims a = 2 blocks, so X ≈ 2× the accept
count — while the bare single-window coverage 1−(1−p)^5.66 = 0.0219 is the
accept fraction. The ledger uses the *accept* rate `p(1−X)^a` for earnings
(`save`) and `(1−X)·marker` for carriage; both appear correctly in the same
ledger, no double-count, and both readings give negative net.)

### Q2 — Does recursion change the verdict? **NO — it reduces to the single-layer sign.**

The decisive argument is a **theorem, not a simulation** (advisor #2):

> **Content-blindness ⇒ layer L's input (= layer L−1's output) carries the
> same base rate p = 0.0039** (a content-blind machine's output on
> random-looking data is itself random-looking). ⇒ per-layer net is
> **layer-invariant**. ⇒ recursion's sign = a single layer's sign. The
> geometric sum collapses: one layer ≤ 0 ⇒ every layer ≤ 0 ⇒ recursion is
> strictly **non-positive**, bounded by raw + ε. **Compounding only switches
> on when a single layer is already net-positive — i.e. above p\*.**

This is **Q2 priced negative, proven-by-math**, the §7b corollary instantiated.
No multi-layer sim is needed; the sum collapses to the sign.

**Reconciliation with raw + ε (advisor #4) — no catastrophic bloat is claimed.**
The real codec applies a layer ONLY if it shrinks; a non-shrinking layer is a
no-op costing ~0 (one remainder-run marker). Under that *kept-if-shrinks* rule:

| supply / layer | per-layer net/bit | layers KEPT / 64 | size after 64 attempts |
| --- | ---: | ---: | ---: |
| (a) ~K draws | −0.3522 | **0** | 100.0000% of original |
| (b) ~1 draw  | −0.3711 | **0** | 100.0000% of original |

The honest verdict at base rate is **"net ≈ 0, zero layers kept, bounded by
raw + ε"** — NOT "bloats X%/layer." The −0.35 magnitude is the net of a layer
the codec would *refuse to apply*; it is never paid. Only the **sign** (halt
vs compound) and the **flip density** matter.

### Q3 — The exact density for net-positive recursive compounding. **It is p\*.**

| supply / layer | break-even multiplier | p_needed | vs base |
| --- | ---: | ---: | ---: |
| (a) ~K = 5.66 draws | **47.5×** | **0.185** | 48× |
| (b) ~1 draw         | 95.1× | 0.371 | 95× |

The repo solver `golden_break_even.py` independently prints B8/canonical/a2
break-even at **48× base = 0.187 ≈ p\* = 0.193**. Our free-birth, K-capped
layer lands at the **same 48× band** — and this is a **structural** agreement,
not a coincidence of canceling effects. Our break-even is birth-FREE at T = 6;
the solver's is birth-CHARGED at T = 64. They agree because both solve the
*same* condition — coverage × win = unclaimed × marker — whose break-even
density is ≈ T-invariant (the marker tax and the win are both per-window
constants; T only moves coverage, which saturates). That T-invariant flip
density **is** p\*. So we independently re-derive p\* as the recursion flip
density from a different (birth-free) starting point. So the density that would make recursive
compounding net-positive at K free passes **is p\*** — the very threshold the
maintainer ruled CONTENT-AWARE (GOLDEN_CONFIG §2: any mechanism lifting real
data's density toward p\* favors structured over random data, i.e. content-aware
by definition, violating SPEC §0 content-blindness).

**The whole result in one line:** recursion buys high *effective* T
(= layers × K) while resetting the log2(T) birth tax to free each layer — but
pays per-layer **wrap/carriage** instead; at the base rate that carriage ≥ the
birth tax it saves, so the wall does not move. **Same wall, different currency.**

## EVIDENCE
- Per-layer net negative at base rate, break-even at 48× = p\*:
  **proven-by-math / exact-counting** — `P2-recursion-ledger.py` reusing the
  repo ledger `golden_break_even.gain()`; cross-checked against the solver's
  printed 48× for B8/canonical/a2. No luck-hashing (the leak is a counting
  fact; a content-blind hash gives the same base rate on every layer).
- Layer-invariance ⇒ recursion sign = single-layer sign: **proven-by-math**
  (content-blindness + the §7b corollary).
- The supply count per layer (~K vs ~1): **bracketed** — (a) is the
  shuffle/salt-refresh reading, (b) is the measured "effective passes ≈ 1";
  the verdict is negative across the whole bracket, so the result does not
  depend on resolving it. Pinning the exact supply at high pass count is the
  one open measurement (NEXT).
- **Would-the-test-work check:** this is a counting/ledger test, not a
  match-hunt — no rare hash event is needed; the base rate p = 0.0039 is the
  measured GOLDEN random rate fed into the accepted format arithmetic.

## CURRENCY (where the birth bill reappears under recursion)

| mechanism | currency | bits |
| --- | --- | --- |
| K free passes within a layer (explosion check) | `structure-free` | birth pass free up to K ≈ 5.66; removes the per-record log2(T) tax *within* the layer |
| **the layer boundary / re-run (the recursion epoch)** | **`wrap/carriage`** | literal re-marking on the new blocking on ~98% unclaimed windows; this is what makes per-layer net negative. (The re-blocking *header* is O(1) per layer ⇒ 0 bits/bit at scale, so the toy charges it as 0 per-bit; it never bites because 0 layers are kept at base rate. Only the per-window literal re-marking is load-bearing.) |
| pushing density to p\* to flip the sign | `hit-density` (content-aware) | 48× the base rate = the threshold the maintainer ruled outside Telomere (GOLDEN §2) |

**Primary currency for lane P2: `wrap/carriage`.** Recursion's defining trade is
that it *converts* the unbounded-T birth tax (`stored-bits`, log2(T)/record,
which lanes E/H show is unpayable past K) into a *per-layer* wrap/carriage tax.
That conversion is legal and bounded (raw + ε) — but at the base rate the
carriage it incurs each layer is ≥ the birth tax it saves, so the net does not
turn positive. The bill is conserved; recursion only changes which currency
pays it.

## COUNTING GATE (the master gate, answered in writing)

**Q: If recursive layer-stacking at K free passes were free + content-blind +
unbounded, would arbitrary random data net-compress without bound?** That is a
pigeonhole violation. **A: it is NOT free — each layer charges wrap/carriage.**
A base-rate-positive unbounded recursion would compress almost all files by
Θ(layers) bits, mapping 2^n inputs into a strictly smaller image (Theorem A,
lane H §3.1). It does not happen because **every layer pays the re-blocking
carriage on its ~98% unclaimed windows** — the finite resource that bounds the
recursion. Self-gate run: no config nets > 0 at the base rate; gate **passed**
(a positive would have flagged a dropped carriage term). The flip requires
density p\*, which is content-aware and therefore outside the content-blind
program — exactly the wall, reached from the recursion side.

## NEXT (single most promising sub-idea)

Pin the per-layer fresh-draw supply at high pass count (the (a)/(b) bracket).
Measure, with the maintainer's shuffle + layer/pass salt over tens of passes
per layer, the actual distinct-draw count a window sees before the emitted
stream stops refreshing — i.e. confirm whether effective draws/layer is ~K
(shuffle keeps refreshing) or saturates toward ~1 (the measured "effective
passes ≈ 1"). The verdict is negative either way; this only sharpens the
*magnitude* of the gap and the exact break-even multiplier (47.5× vs 95×).

---

### OUTPUT-FORMAT block

```
AVENUE: P2 (recursion / layer-stacking ledger)
HYPOTHESIS: per-layer net negative at base rate; recursion = layer-invariant
  so reduces to single-layer sign; flip density = p*. (All confirmed.)
MECHANISM: re-run output as fresh file (SPEC §1); per-layer ledger = repo's
  golden_break_even.gain() at m=1, birth free within K, carriage charged.
RESULT: partial(reach: per-layer net<0 at base rate; Q2 priced negative) —
  recursion does NOT unlock compounding below p*; bounded raw+ε.
EVIDENCE: proven-by-math / exact-counting — P2-recursion-ledger.py + repo
  ledger cross-check (solver prints same 48x); counting test, no luck needed.
CURRENCY: wrap/carriage — recursion converts the unbounded log2(T) birth tax
  (stored-bits) into a per-layer re-blocking tax; at base rate carriage ≥ the
  tax saved, so net stays negative. Flip needs hit-density p* (content-aware).
NEXT: measure per-layer fresh-draw supply at high pass count (~K vs ~1 bracket).
```
