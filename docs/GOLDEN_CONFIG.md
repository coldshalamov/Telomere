# Telomere — The Golden Config (parameter study and build target)

*June 2026. The full tuning study under the V1 architecture
(`SPEC_V1.md`): every tunable tried, dead ends catalogued, the working
configuration fixed. Exact arithmetic and real-draw simulation only —
no expectation-value shortcuts; jackpot tails carry ≤7% of win mass
everywhere (measured), so nothing below leans on improbable strikes.*

Artifacts: `golden_format_arithmetic.py` (exact counting), `golden_mc.py`
(real-draw coverage), `golden_break_even.py` (honest ledger + thresholds),
in `model_analysis/proof_kernel/`.

## 1. THE GOLDEN CONFIG

| parameter | value | decided by |
| --- | --- | --- |
| block size B | **8 bits** | exact gap table across B ∈ 4–32 |
| alphabet | **canonical** (a1 `00`, a2 `01`, lit `111`) | 2-bit arity-2 doubles engine hit rate (gap 8.02 vs 9.03) — the maintainer's original assignment |
| engine arity | **2**; arities 3–5 optional add-ons | smallest gap; 253 compressive seeds; E[win\|hit] = 2.17 bits exact |
| seed field | **J3D1 Lotus** (cap 508) | J2D1 falsified (ossification) |
| search depth | **compressive frontier only** (the 253 seeds) | depth ceiling D* — deeper is provably worthless |
| salting | **position salts**, self-presenting at decode (the reverse walk arrives at each pass's state with records at their match positions) | the zero-metadata freshness channel |
| passes per run | **16–64** | trial-decode ambiguity and diminishing coverage beyond |
| shuffle | `i → walk(5i mod P) + 1 mod M` (maintainer's +1 fix: every item moves every pass) | zero repeated neighbor pairs, exact inverse |
| recursion | re-run the machine on its own output | the legal recursion channel |

## 2. What "working" means — precisely

- **Decoding: always works.** Stateless, zero metadata beyond the fixed
  header. Proven by construction (36/36 multi-pass round trips).
- **Bounded loss: always.** No file ever grows past raw + 3 bits + header.
- **Compression: works on the dense class.** A file compresses when its
  windows hit the reachable expansion set often enough. At the Golden
  Config the threshold is **p\* ≈ 0.19 per pair-window** (about one
  window in five findable on the compressive frontier); at 2× threshold
  the file earns ~4.4% per run, compounding across re-runs.
- **Random data sits below threshold** (p ≈ 0.0039, ~50× short) — at
  every parameter setting, not just this one (§5). That is a counting
  law about pure chance, not a tuning failure: a machine that never
  loses more than ε on any file cannot net-win on almost all files.

**Maintainer's ruling (June 2026): the density lane is NOT Telomere.**
Any mechanism that lifts real data's density toward p\* works by
favoring structured data over random data — content-aware compression
by definition, which violates the content-blindness requirement
(SPEC_V1 §0). And no content-blind boost exists: raising every file's
hit rate equally would make almost all files compress, which counting
forbids. Consequence, stated plainly: **pure Telomere treats every file
identically, and identically means below threshold** — it compresses
essentially nothing and bloats essentially nothing (a fair coin that
charges a small commission, bounded at raw + ε). Files that clear p\*
by luck exist but are exponentially rare and content-blind-rare. The
density lane remains documented as a HYBRID departure for anyone who
chooses to leave the definition; it is not part of this program.

## 3. Threshold table (what each config demands of the data)

| config | p (random) | p\* (threshold) | multiple | best T | gain at 2×p\* |
| --- | --- | --- | --- | --- | --- |
| **B8/canonical/a2 (GOLDEN)** | 0.0039 | **0.193** | **50×** | 64 | +4.4%/run |
| B8/payback/a2 | 0.0019 | 0.145 | 76× | 32 | +4.2%/run |
| B16/canonical/a2 | 0.0020 | 0.226 | 116× | 64 | +2.3%/run |
| B8/canonical/a3 | 0.0010 | 0.172 | 176× | 128 | +8.6%/run |
| B16/payback/a1 (singles lane) | 0.0039 | ~0.48 (one-shot) | ~125× | 1 | marginal |

Golden Config minimizes the demanded multiple. Legacy flat-format
break-evens were 824×–6144×; V1 format work brought the demand to 50×.

## 4. What works (proven / measured)

- Stateless decode in the maintainer's exact architecture, by his rule
  ("the one that decodes is the answer"): **12/12**
  (`robins_opening_rules.py`); both fixed mechanical opening rules 0/12
  — trial decoding is the design, not a fallback. All constructions
  (in-place expansion, remainder run, derived pass count,
  self-presenting position salts): proven.
- E[win|hit] ≈ 2 bits at every scale and setting — exact counting;
  viability is purely a hit-density question, never a hit-size question.
- Content-blind convergence: with many blocks, all files of a given
  density compress alike (law of large numbers).
- Shuffle freshness: every pass offers every item a never-repeated
  neighbor (measured, hundreds of passes).
- Hardware at honest settings: ~64 frontier lookups per byte per run —
  minutes per TB at ASIC tier, hours on a workstation (lookup-bound).

## 5. Why no config compresses random data unaided (the honest core)

Two independent arguments, both in `golden_break_even.py` and
`MATH_MODEL_V1.md` §7b:

1. **Counting.** Worst-case loss is bounded at +ε by design; if almost
   all n-bit files also won Θ(n), the protocol would map 2^n inputs
   into fewer outputs — impossible. So typical random data cannot win.
2. **The explicit ledger.** Each ~2-bit win carries a real information
   bill at decode (settling which reading of the stream is correct —
   "multiple decodings" are free to RUN but not free in the accounting
   at scale). Charged at its lower bound, every (config, T) is slightly
   negative on random data: short runs lose to the literal wrap, long
   runs lose to ambiguity growth. Best case ≈ −16%. The sweep covered
   B ∈ 4–32, both alphabets, arities 1–5, all depths, T ∈ 2–4000.

Dense data clears the bill because wins outnumber it (§3). This is the
same conclusion the legacy corpus program reached empirically (11M+
spans, 0 selected), now derived from format arithmetic.

## 6. Dead ends, catalogued (do not revisit without new evidence)

| dead end | killed by |
| --- | --- |
| J2D1 seed field | 28-bit cap → grown records unreachable (MC-falsified) |
| unsalted operation | dice exhaust; stalls +13% above raw (MC) |
| pass-number salts | needs birth info; position salts replace them |
| stored birth tags / pass counts / length fields | metadata contract; all derivable |
| expectation-value kernels | fractional-hit fantasy; thrice corrected |
| B = 4 | wrap tax dominates (worst honest ledger) |
| arity-1 as engine | 1 compressive seed at B=8; one-shot at any B |
| T ≫ 64 grinding | ambiguity bill grows as log(T), wins don't |
| naive layer compounding at constant rate | pigeonhole (§5) |

## 7. The research agenda (in order)

1. (Removed by maintainer's ruling — density mechanisms are
   content-aware and therefore outside the Telomere definition; see §2.)
2. **Trial-decode scaling** (the §5 bill, measured): grow
   `robins_opening_rules.py` (the maintainer's decoder, already 12/12 at
   toy scale) in file size and pass count; measure decode search cost
   and surviving-reading count. This is the empirical face of §5.
3. **Reference codec** per `IMPLEMENTATION_MAP.md` once 1–2 move.

