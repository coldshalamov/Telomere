# Net-Compression Search — Compact Report

Companion to `docs/NET_MODEL.md` (proofs + exact equations). All costs are
code-anchored via `src/bin/v2_cost_probe.rs`. Model object: the **active V2
record format** (LiteralRun + seed-span records, ordered, decoded
sequentially). Reference file for every numeric row: **N = 1,000,000 bytes,
incompressible/natural, `max_seed_len = 1` (K=256), V2 fixed-span.**

---

## 1. Headline findings

1. **The per-block literal marker is a V1-only tax; V2 already fixed it.** V1
   pays ~1 byte per literal *block* (`1/B` of the file → 50% bloat at B=2). V2's
   `LiteralRun` pays one ~3–5 byte header per literal *run* — O(1) total. On 1
   MB incompressible data this drops bloat from **~12–50%** (V1, depending on B)
   to **~0.011%** (V2). This is the largest banked win, and it is already in the
   shipped V2 code.

2. **Net compression is governed by clusters, not single hits.** Inserting one
   isolated hit splits a literal run and adds a header, so the break-even is
   `k* = ⌈O_lit /(8B − S)⌉` *adjacent* hits. The old V1 break-even multipliers
   (824× / 3066× / 6144× in `CLAUDE.md`) were driven by the per-block literal
   tax and **do not apply to V2** — they are superseded by `k*`.

3. **The binding wall is the fragmentation-vs-rarity vise**, not overhead. For
   every feasible block size the profitable-cluster probability is pinned at
   ≈ 2⁻³² (K=256). Expected profitable cluster-bytes on 1 MB ≈ 0.

4. **Effective passes ≈ 1.** Re-searching unchanged bytes on a fixed grid finds
   nothing (repeated-search optimism); only rechunk is fresh, and it saturates
   at the ~1.2× aggregate-arity constant while every pass adds ~9 bytes of
   descriptor. 50/100/200 passes only bloat.

5. **No pure-format change reaches +0.3%/pass.** Format changes push the bloat
   floor toward zero and bank real clusters; they cannot create clustered
   density. The target needs a charged density **mechanism**.

---

## 2. Experiment table (ideas from the brief, modelled honestly)

`H` = header bytes, `O_lit` = literal-run header, `S` = seed-record bits,
`k*` = cluster break-even, `C` = bytes covered by profitable seed spans.
"Reaches +0.3%/eff-pass?" judges *true net* on natural data.

| # | Idea | Lever it moves | Modelled effect (B=2, K=256) | Reaches target? |
|---|---|---|---|---|
| 1 | LiteralRun vs per-block markers | `O_lit` | per-block 1 B/blk → per-run ~3 B/run; bloat 50% → 0.011% | **No** (anti-bloat only; can't beat literal floor) |
| 2 | Fixed-span layer (drop `Lotus(span−1)`) | `S` | `S_var→S_fix`: −10..11 bits/hit; k\* 6→… still ≥2 | No (lowers `k*`, density unchanged) |
| 3 | **[future] Minimal record** (1-bit flag + flat 8-bit index) | `S` | `S` 12→9 (best), avg 20→9; `k*` 6→4 @B=2 | No (lowers `k*`, density unchanged) |
| 4 | Better seed-index coding (flat vs Lotus) | `S` | −5.85 bits/record avg (13.85→8) for K=256 | No (helps `k*`, not `C`) |
| 5 | Larger first-pass block / smaller later grid | hit rarity vs `k*` | trades vise ends; product `h^{k*}` ≈ 2⁻³² invariant | No |
| 6 | Deterministic rechunk schedule | fresh trials | +~1.2× one-time on a **nonzero** base; ×0 on natural | No |
| 7 | Multi-seed / combiner record (all seeds charged) | `S` amortization | k seeds, 1 header: helps only if k adjacent hits exist | No (needs the cluster first) |
| 8 | **Seed-run / bundle record** (fully decodable) | `O_lit` per cluster | one header for a k-cluster → directly lowers `k*` toward 1 | Partial: removes fragmentation tax, still needs clusters |
| 9 | Fragmentation-aware selector (optimise emitted size) | prevents bloat | skip hits with `ΔEmitted ≥ 0`; fixes a real selector gap (§5) | No (anti-bloat; never < literal floor) |
| 10 | **[charged] Public preset / dictionary / transform** | **`C`** | raises *clustered* exact-hit density directly | **Only lane that can** — must be frozen & charged |

Reading: ideas 1–9 are all **denominator** moves (shrink overhead, lower `k*`).
Only idea **10** moves the **numerator** `C`. The brief's "selector that
optimises emitted size" (idea 9) and "seed-run/bundle" (idea 8) are the most
valuable *native* moves because they make the model honest and remove
fragmentation bloat — but they convert "isolated hits that bloat" into "no
worse than literal," not into net compression.

---

## 3. Exact 10-pass ledger (N = 1,000,000 B, B=2, K=256, V2 fixed-span)

Per-pass quantities from the §2 equations of `docs/NET_MODEL.md`.
`E[profitable clusters] = (N/B)·h^{k*} = 5·10⁵ · 2⁻³² ≈ 1.2·10⁻⁴` → **0 hits**,
so `C = 0` every pass on natural data.

| pass | input B | fresh? (audit) | hits (C) | literal O (B) | descriptor (B) | payload out B | file B | net % |
|---|---|---|---|---|---|---|---|---|
| 1 | 1,000,000 | **real** (first trial) | 0 | 79 | — | 1,000,079 | 1,000,110 | −0.0110 |
| 2 | 1,000,079 | repeated-search optimism | 0 | (re-wrap) | +9 | — | **STOP** | — |
| 3–10 | — | (encoder halted at pass 2) | — | — | — | — | — | — |

`src/streaming.rs:361` rejects pass 2 (`payload ≥ current`) and emits pass 1
only. **Code-honest final = 1,000,110 B at any pass count.**

**Measured (not modelled).** Running the real encoder
`compress_streaming_v2_with_telemetry(data, Sha256, max_seed_len=1,
max_span_len=16, block_size=2, max_arity=5, passes=10, hash_bits=13)` on a
1,000,000-byte incompressible buffer (`v2_cost_probe` end-to-end section)
reproduces the ledger exactly:

| quantity | ledger | encoder |
|---|---|---|
| final file bytes | 1,000,110 | **1,000,110** |
| final payload bytes | 1,000,079 | **1,000,079** |
| net | −0.0110% | **−0.0110%** |
| layers kept | 1 | **1** |
| selected hits | 0 | **0** |
| stop_reason | stops | **`non_compressive_layer`** |

With this multi-tier (variable-span) config the 2-byte record carries a
`Lotus(span−1)` field, costing ≥21 bits > the 16-bit span, so **no 2-byte hit
is profitable at all**; 4+ byte hits are profitable per-record but have
expected count ≈ 0.06 in 1 MB — so 0 are selected. That is the
fragmentation-vs-rarity vise observed directly in the encoder, not a model.

Counterfactual "forced" ledger (stop disabled, to show why passes can't help):
each pass re-wraps the prior payload (0 hits) for ≈ +79 B and adds +9 B
descriptor ⇒ **+88 B/pass**, monotone bloat.

| pass | forced file B (≈1,000,110 + 88·(k−1)) | net % |
|---|---|---|
| 1 | 1,000,110 | −0.011 |
| 2 | 1,000,198 | −0.020 |
| 5 | 1,000,462 | −0.046 |
| 10 | 1,000,902 | −0.090 |

---

## 4. Final/raw at 1 / 10 / 50 / 100 / 200 passes

| passes | **Natural data — code-honest** (encoder stops) | **Natural — forced** (no stop) | **Idealised mechanism** (§6) |
|---|---|---|---|
| | final/raw — net% | final/raw — net% | final/raw — net% |
| 1 | 1.000110 — −0.011% | 1.000110 — −0.011% | 0.997 — **+0.3%** |
| 10 | 1.000110 — −0.011% | 1.000902 — −0.090% | ~0.9964 — +0.36% (1.2× rechunk, saturates) |
| 50 | 1.000110 — −0.011% | 1.004422 — −0.44% | ~0.9964 — +0.36% (no further compounding) |
| 100 | 1.000110 — −0.011% | 1.008822 — −0.88% | ~0.9964 — +0.36% |
| 200 | 1.000110 — −0.011% | 1.017622 — −1.76% | ~0.9964 — +0.36% |

- **Natural data**: Telomere V2 is pigeonhole-honest — it bloats by a flat
  ~0.011% and refuses to bloat further. It never net-compresses incompressible
  data; no pass count changes that.
- **Idealised**: even *with* a mechanism that yields +0.3% in pass 1, passes do
  **not** stack — rechunk adds a one-time ~1.2× then flatlines. The realistic
  ceiling is **"+X% in ~1 effective pass,"** not `+X%·passes`.

---

## 5. A real selector gap found while modelling

`select_weighted_candidates` (`src/indexed.rs:766-833`) retains a candidate on
`encoded_bits < span_len·8` — **per-record** profitability that ignores the
`O_lit` header added when the hit splits a literal run. On data with sparse
hits (planted / dictionary corpora) it can therefore select an isolated hit
that **net-bloats** the layer, and pass 1 is emitted even when it bloats
(`POWER_MODEL.md`; no pass-1 guard). The fragmentation-aware fix is idea #9:
charge `O_lit` to interior hits and accept a cluster only when
`k·(8B − S) > O_lit`. This is a concrete, native, anti-bloat improvement; it
does not create compression.

---

## 6. Best current candidate

**Single-pass, fragmentation-aware, minimal-overhead V2.** Concretely:

- **fixed-span layer** (`V2_TIER_POLICY_FIXED_SEED_SPAN`, already in code) —
  drops the per-record `Lotus(span−1)` field;
- **LiteralRun coalescing** (already in code) — O(1) literal overhead;
- **fragmentation-aware selection** (idea #9, ~small patch) — never emit a
  layer that bloats; accept clusters only when `k·(8B−S) > O_lit`;
- **[future / optional] minimal record** — 1-bit flag instead of the 6-bit
  Lotus tag, and a flat `⌈log₂K⌉`-bit seed index instead of Lotus (−5.85
  bits/record at K=256). Lowers `S` from ~12 (best) / ~20 (avg) to **9**, and
  `k*` from 6 to **4** at B=2.

What this candidate delivers, stated without inflation:

- **Guaranteed near-zero bloat** on incompressible data (≈ container + O(1)
  run headers ≈ 0.01% on 1 MB) — the honest pigeonhole result.
- **Every genuine cluster banked** at the lowest `k*` the format allows.
- **It does not reach +0.3% net on natural data**, because that needs ~0.7% of
  file bytes to fall in net-profitable *clusters* (threshold below), and raw
  search supplies ≈ 0.

### Clustered-density threshold (what a mechanism must hit)

From `NetSave ≈ C·[8 − S/B − O_lit/(B·k̄)] − 8H` (minimal record, B=2, large
`k̄`): coefficient ≈ **3.5 bits per covered byte**. So:

| target true-net | required covered fraction `C/N` (clusters) |
|---|---|
| +0.3% | ≈ **0.69%** of file bytes in net-profitable clusters |
| +0.7% (stretch) | ≈ **1.6%** of file bytes in net-profitable clusters |

This is the concrete bar for idea #10. The brief's stretch of +0.7%/pass is
**not** reachable by format work; it is reachable **only** if a frozen,
charged, held-out mechanism (public preset, reversible transform, dictionary,
or schema-native table) supplies ≳1.6% clustered exact-hit coverage with cheap
decode. `CLAUDE.md`'s open question and the `VIABILITY.md` level-45
schema-native probe are exactly that lane — and are where to push next.

---

## 7. Reproduce and scope

```powershell
cargo run --bin v2_cost_probe        # record/Lotus/container costs + 1 MB end-to-end run
```
The probe prints both the ground-truth cost primitives and the **end-to-end**
real-encoder run whose numbers populate §3. Cross-checks: the §3 ledger is now
**measured** by the encoder (table above), `POWER_MODEL.md`'s pass-1 row
(≈1,000,111 B) agrees, and the closed-form `L(v)` in `docs/NET_MODEL.md` matches
`lotus_encoded_bit_len` for every sampled value (probe section 1).

**Scope caveats.** (1) Every numeric row uses **block_size = 2**, the
worst-case-economics reference; the model's conclusions (the `k*` formula, the
`h^{k*}` vise, the ~0.011% bloat, "effective passes ≈ 1") hold for any B, but
the *specific* byte counts are illustrative-at-B=2. The default `compressor`
CLI emits **V1** via `compress_multi_pass`, and its configured `block_size` was
not separately audited here — the ledger is the V2 streaming path at B=2, not
"what the default CLI does." (2) `src/bin/v2_cost_probe.rs` is committed
alongside this report (mirroring the existing `src/bin/v1_cost_table.rs`); keep
or remove it deliberately.
