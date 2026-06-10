# Telomere Result Ledger

**Status: single source of truth for results.** Every major result, its
evidence class, and why it stands or fails. Where any other report disagrees
with this ledger, the other report is stale.

Evidence classes: `invalid` | `upper_bound` | `math_candidate` |
`wire_proven_candidate` | `implemented_codec_result`.

The single empirical assumption behind every `math_candidate` row is the
uniform hash law `P(match) = 2^-S` per (seed-tuple, content, position) trial.
Everything else is exact counting against canonical costs
(`model_analysis/proof_kernel/costs.py`, mirrored from
`src/bin/v1_cost_table.rs`; re-pin locally with
`cargo run --quiet --bin v1_cost_table`).

> **Correction notice 1 (accounting).** An earlier revision headlined a
> 0.908 %/pass "junction-density" primary. Instrumented cross-checks found
> two accounting bugs in the v-next kernel's run/grid bookkeeping (finding
> 5). Every `segments > 0` lane was re-evaluated; the family corrects to
> ~0.19–0.31 %/pass. φ=1 lanes were unaffected.
>
> **Correction notice 2 (decode dependency — maintainer review).** The
> claim that layer-masked expansion "needs no epoch inference" was wrong.
> In the evolving-stream model (the one every kernel prices — surviving
> entries carry forward free, which is correct for the wire), ANY
> pass-varying rule — masks, salts, per-layer alphabets, and the
> permutation refresh itself — requires per-record birth-epoch knowledge
> at decode. The strict layer-stack alternative decodes trivially but pays
> ~10:1 re-wrap carriage that no kernel charges (maintainer's original
> pricing, confirmed). My earlier two-layer "nested decode proof" stacked
> fully re-encoded layers — it paid carriage the kernel doesn't and dodged
> the hard case. Consequences: masked lanes demote to `upper_bound`;
> per-layer alphabet schedules demote to conditional; the affine-stride
> epoch-inference architecture (maintainer's handoff v2) is un-demoted and
> is now load-bearing for every refreshed lane. One new supporting lemma
> fell out: **arity-1 replacements preserve sequence length (1→1), so the
> permutation unwind needs only BUNDLE birth epochs** — exactly what the
> affine-stride fingerprint provides, and exactly why the v2 design salts
> bundles and leaves arity-1 unsalted. The v2 architecture is canonical.

## Headline table

| result | class | rate (10-pass min) | final/raw 11 / 50 / 100 / 200 / 500 | payback pass | kernel | decode dependency | why |
| --- | --- | ---: | --- | ---: | --- | --- | --- |
| **PRIMARY: constant single-cheap alphabet {sgl 2b, a2 3b} + J2D1 + permutation+swaps** | `math_candidate` | **+0.202%** | 1.207 / 1.079 / 0.935 / **0.742** / **0.478** | **76** | audited (`entry_state`) | bundle stride-inference induction (v2 obligation 1) + ~T/N escape ledger | 2-bit single pays for itself even charging a2 +1 forever; parse needs no epochs (one alphabet); arity-1 dice content-keyed |
| J2D1 + canonical alphabet (singles 3b) | `math_candidate` | +0.199% | 1.321 / 1.195 / 1.054 / 0.853 / 0.560 | 123 | audited | same as primary | J2 alone: rate up, wrap unchanged |
| audited BIT_LITERAL reference (J3, canonical, D96) | `math_candidate` | +0.1328% | 1.340 / 1.227 / 1.072 / 0.832 / 0.486 | 126 | audited | same as primary (the dependency was always there; previously unstated) | the conservative floor; deepest J3 lane |
| CONDITIONAL: pass-1-only 2-bit single (alphabet schedule) | conditional `math_candidate` | +0.309% (J2) / +0.159% (J3) | J2: 0.631@200, 0.382@500 | 53 / 81 | audited | **needs a singles-epoch channel — none known** (surviving pass-1 singles parse ambiguously at top level; singles have no stride) | the upside if a singles channel is ever found |
| UPPER BOUND: layer-masked expansion (fresh=1, zero metadata) | `upper_bound` | +0.397% (v-next kernel) | 0.817@200, 0.545@500 | 76 | v-next | **needs pass-varying dice keys for everything incl. arity-1 — no known zero-bit channel** (impossibility sketch: decode-derivable keys are frozen-attribute (no re-roll) or current-offset (deadlock/shift); pass-varying is neither) | the prize if a channel is found; law-validated as a LAW |
| affine shuffle + epoch salts (maintainer handoff v2) | **the canonical refresh architecture** | ≈ permutation rows above (strides price ~T/N escapes) | as primary | as primary | — | IS the epoch channel (obligation 1 = its induction proof) | un-demoted; the arity-1 length-preservation lemma completes its shape |
| φ<1 run-carriage lanes (corrected accounting) | `math_candidate` | +0.19–0.31% (v-next kernel) | ~0.85@200 | 104–155 | v-next | as primary | carriage cuts wrap at proportional rate cost |
| LITERAL_RUN ε-bloat bound (giant runs) | `math_candidate` | +0.0002% | 1.0026 p1 | 283 | v-next | as primary | attack-starved; "single-digit crossover" does not survive |
| FIXED-length runs (no Lotus length field) | sound negative | +0.24% | dominated | 130 | v-next | — | length field pays for itself; also: minting the codeword costs a split (see alphabet tax) |
| k=2 XOR (MitM) records | `wire_proven_candidate` (primitive) | configs +0.0225% | dominated | none | v-next | — | extra Lotus field dominates at small spans |
| position-ONLY salted expansion | `invalid` (as refresh) | 0 accepts from pass 3 | — | — | dice-validated | — | emission-replication deadlock |
| old uncharged rechunk-4 / charged rechunk variants | `invalid` | — / −24.7% / −1.67% | — | — | — | — | uncharged passthrough; flag tax; Kraft dominance |
| nested superposition | mechanism audit | +0.003–0.016 pp | — | — | both | — | subcritical |
| oracle rows | `upper_bound` | per artifact | — | — | — | — | never configs |

## Alphabet tax accounting (maintainer Q1)

Minting a codeword is never free in a Kraft-complete alphabet; every variant
below shows what was split and what it costs (audited kernel, J2D1, 500
passes, `audited_primary.json`):

| alphabet | what was split | per-record tax | wrap p1 | min %/pass | payback | @500 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| canonical {sgl 111=3b; a1,a2=2b} | — | — | 1.353 | 0.199 | 123 | 0.560 |
| **const single-cheap {sgl 00=2b; a1 01=2b; a2 100=3b}** | a2 loses its 2-bit slot | **+1 bit on every arity-2 record, forever** | **1.237** | **0.202** | **76** | **0.478** |
| fixed-run mint (3b FIX displacing a4/a5) | arity 4–5 dropped | high-arity channel lost | 1.23–1.28 | 0.21–0.25 | 111–141 | — |
| fixed-run mint (4b split of 111: FIX=1110, VAR=1111) | variable runs +1 bit | +1 bit/var-run header | similar | dominated by attackability loss either way | — | — |

Verdict: the 2-bit single wins **net of its tax** (the wrap saving of ~1
Mbit against ~a2-mass × 1 bit); the fixed-run mint loses regardless of how
the slot is funded, because the attackability loss dominates the header
saving.

## The corrected primary, in words

One constant alphabet for the whole file: single literal `00` (2 bits),
arity-1 `01`, arities 2–5 at 3 bits (a2 pays +1 vs canonical — charged in
the table above). J2D1 seed fields (per-FILE profile constant — no schedule,
no epoch issue), depth 29 ≈ the J2 cap. Permutation + neutral swaps refresh
(3 charged bits/pass), content-only expansion — dice need no pass key:
arity-1 freshness is content-change (cascade/swaps), multi-entry freshness
is new adjacency. Greedy; superposition delta 16 / cap 4.

Results (`audited_primary.json`, audited kernel — harness reproduces
`bit_literal_target.json` to five decimals): **+0.202 %/pass min** (avg
+0.247), wrap 1.237, **payback 76**, **0.742 @ 200**, **0.478 @ 500** —
better than the previous audited target on every axis.

Decode dependency (stated, not hidden): un-permuting the evolving stream
requires identifying which BUNDLES were born each pass. Arity-1 records are
length-preserving and need no epoch (lemma above). The affine-stride
fingerprint (v2 obligation 1) is the zero-bit channel; its induction proof
plus exact escape ledger (~T/N per bundle — structurally small, not
Kraft-mass) is the single load-bearing open proof of the program.

## Mechanism findings (cumulative, corrected)

1. **Layer-masked expansion** — unchanged: zero metadata, fresh = 1, shared
   tables; law-validated (sustained 0.13–0.18 %/pass toy-measured, no
   decay); decode-proven nested. The compute story of the whole program
   rides on this: build one table to D\*, every pass is lookups.
2. **Position-only salting dead** (emission-replication deadlock) —
   unchanged; the layer index in the mask is what breaks it.
3. **J2D1 ≈ 2× J3D1** at B=8 budgets (clean φ=1 comparison: 0.366 vs
   0.201). **Layer-indexed alphabet schedules are free and real**: the
   2-bit-single pass-1 alphabet cuts wrap bloat 1.369 → 1.245 and lifts the
   floor 0.366 → 0.397 with payback 130 → 76.
4. **Depth ceiling D\***: a record replacing an s-bit span can spend at most
   ~s bits on its seed field, so seeds past 2^(D\*) are never compressive —
   D=48 ≡ D=96 at B=8 in the sweep. Under masking, "when to stop searching"
   dissolves: the table is built once to D\*; compute converts to
   compression through passes, not depth. D\* falls as records shorten.
5. **Run/grid accounting corrections (this revision).** Two bugs found by
   instrumented cross-checks, both inflating `segments > 0` lanes:
   (a) the grid walk DP stepped by run *payload* length, crossing run
   header wire bits for free; (b) the apply step subtracted full covered
   wire from payload AND retired segments at the payload rate — a
   triple-dip. Hand-derived channel arithmetic now matches the kernel
   (0.124 vs 0.13 %/pass on the φ=0/S0=1M diagnostic). Corrected verdicts:
   run carriage lowers pass-1 bloat at roughly proportional rate cost;
   grid-mode arities are ~neutral at corrected pricing; the
   "junction-density" optimum was an artifact. This is the third
   accounting bug caught by the audit loop (after the walk-DP short-run
   laundering, also disclosed here, and it is why every number carries an
   evidence class.
6. **Fixed-length runs are a sound negative result**: deleting the Lotus
   length field (8–10 bits/run) starves whole-entry attackability — the
   length field pays for itself. Metadata audit otherwise: refresh 0,
   selector 0, superposition 0 (encoder-state), arity codewords
   irreducible (Kraft-complete), termination out-of-band (no in-band
   markers anywhere).
7. **Affine shuffle + epoch salts (handoff v2)**: modeled as a comparison
   lane — ties the masked lane to four decimals before its escape ledger
   and stride-test decode compute. Under the layer-stack decode, records
   never migrate between layers, so epoch *inference* is unnecessary:
   `mask(layer, offset)` is always known. Dominated; kept as fallback.
   Its open arity-1 problem is solved by masking.
8. **k=2 XOR / MitM** — unchanged: wire-proven, square-root search
   demonstrated, ~9× rate cost at B=8; superseded for compute by masking.

## Cost pinning status

Unchanged from the previous revision: golden vectors pass; J2D1 min 6 /
J3D1 min 7; caps 28/508; 127-vs-508 resolves to 508 on repo evidence;
**cargo unavailable in this sandbox — costs NOT newly Rust-validated**;
final wire pin needs the sibling `../lotus` crate. See
`cost_pin_report.json`.

## Reproduction

```powershell
python model_analysis/proof_kernel/vnext_search.py --stage rank
python model_analysis/proof_kernel/vnext_search.py --stage final
python model_analysis/proof_kernel/bit_literal_decode_proof.py
python model_analysis/proof_kernel/literal_run_decode_proof.py
python model_analysis/proof_kernel/position_salt_decode_proof.py
python model_analysis/proof_kernel/mitm_xor_decode_proof.py
python model_analysis/proof_kernel/freshness_law_validation.py
cargo run --quiet --bin v1_cost_table && python model_analysis/proof_kernel/cost_pin.py
```
