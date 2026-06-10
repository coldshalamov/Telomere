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

## Headline table

| result | class | rate (10-pass min) | final/raw 11 / 50 / 100 / 200 / 500 | payback pass | selector | oracle? | literals charged | side info charged | decode proven | format | carrying assumption |
| --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| **v-next primary: grid_heavy φ=.5 S0=256k J2D1 layer-masked** | `math_candidate` | **+0.908%** | 1.386 / 1.096 / 0.958 / **0.810** / **0.541** | **81** | greedy | no (oracle bound +0.910%) | yes (runs+singles, headers exact) | zero metadata | primitives yes, full config no | v-next | uniform hash law; expectation-level recurrence |
| audited BIT_LITERAL target (block 8, D96, perm+swaps, vars 4) | `math_candidate` (primitive wire-proven) | +0.1328% | 1.340 / 1.227 / 1.072 / 0.832 / 0.486 | 126 (effective) | greedy | no (greedy at oracle bound) | yes (3-bit BIT_LITERAL) | 3 bits/pass | BIT_LITERAL yes (`bit_literal_decode_proof.py`) | v-next (needs BIT_LITERAL) | uniform hash law |
| canonical-v1 frontier (10-bit literal wrap, no new primitive) | `math_candidate` | +0.0430% | no crossover ≤ 500 | none | greedy | no | yes | 3 bits/pass | n/a (current wire format) | v1 | uniform hash law |
| LITERAL_RUN ε-bloat bound (S0=1024 giant runs) | `math_candidate` | +0.0002% | pass-1 1.0027; ~0.99 @500 | 293 | greedy | no | yes | zero | yes (`literal_run_decode_proof.py`) | v-next | junction-starved: proves the bloat end of the frontier, not a viable lane alone |
| layer-masked expansion (mechanism) | `wire_proven_candidate` (as primitive) | n/a (mechanism) | n/a | n/a | n/a | n/a | n/a | zero | yes (`position_salt_decode_proof.py`, nested) | v-next | fixed public mask schedule; law-validated with real SHA-256 dice |
| k=2 XOR (MitM) records | `wire_proven_candidate` (as primitive); `math_candidate` configs ~9× slower at B=8 | +0.0225% (B=8) | dominated | none ≤ 500 | greedy | no | yes | zero | yes (`mitm_xor_decode_proof.py`, salted + unsalted) | v-next | extra Lotus field (~+6-9 bits/record) dominates at small spans; amortizes only at spans ≥ ~60 bits |
| **position-ONLY salted expansion** | **`invalid` (as refresh)** | measured 0 accepts from pass 3 | n/a | n/a | n/a | n/a | n/a | zero | decode itself is sound; the REFRESH claim is dead | v-next | **deadlock**: pre-first-accept emission replicates the previous layer, so every (content, position) query repeats and re-misses |
| old uncharged rechunk-4 (0.53%/pass headline) | `invalid` (`failed_audit_uncharged_passthrough`) | n/a | n/a | n/a | n/a | n/a | **no** | no | no | — | verbatim chunks carried no charged record/chunk discriminator |
| charged rechunk, explicit flag | `invalid` (fails on cost) | −24.7%/pass | bloats | never | greedy | no | yes | yes | yes | v1 | 1 flag bit per element per pass exceeds all gain |
| charged rechunk, implicit selector (decode-by-replay) | `invalid` (fails on cost; Kraft-dominated) | −1.67%/pass | bloats | never | greedy | no | yes | yes (stuffing escapes) | replay decode defined | v1 | escape mass `Σ cnt·2^g·2^-S` > gain mass `Σ cnt·g·2^-S` for all g ≥ 1 — analytic, format-independent within this family |
| nested superposition | mechanism audit | +0.003 to +0.016 pp contribution | n/a | n/a | n/a | n/a | encoder-state only | zero wire | n/a (encoder-only; collapsed path serialized) | both | branching subcritical (~2^-7/generation); delta=8 cap=4 nesting=2 captures everything |
| oracle rows (any config) | `upper_bound` | labeled per row in `vnext_sweep.json` | — | — | oracle | yes | — | — | — | — | selection upper bound only, never a config |

## The v-next primary, in words

Configuration: block 8 bits; alphabet `grid_heavy` (entry arities 1–2 at
{2,2} bits, grid arities 3–4 at {3,3} bits, BIT_LITERAL single `110`,
LITERAL_RUN `111`); J2D1 seed fields (min record 6 bits, payload cap 28 →
depth 28); pass-1 exposure φ=0.5 of blocks as singles, the rest in
S0=262,144 literal runs (~15-bit average payload); layer-masked expansion
(zero metadata); greedy selection; superposition delta 16 / cap 4 (earned,
conservative discount).

Per `model_analysis/proof_kernel/vnext_best.json`: ten-effective-pass minimum
**+0.908%/pass** (average +0.991%), pass-1 ratio 1.531, raw payback at pass
**81**, final/raw **0.810 at 200** and **0.541 at 500**. Greedy sits at the
oracle bound (+0.910%). All headers charged in their emitting layer; refresh
metadata zero. Compute story (separate from size): shared unsalted prefix
table of 2^28 expansions built once; ~O(1) masked lookups per window.

Success bars (handoff): baseline ≥0.1% ✓, stretch ≥0.2% ✓, breakthrough
≥0.5% fully-charged non-oracle ✓, crossover ≤200 ✓, ≤0.84@200 ✓, ≤0.60@500 ✓.
**Crossover <50 not met** (best payback 81; the missing lever is pass-1
bloat ~1.53 — see the frontier chart; sub-50 needs ~1.15 bloat at ≥0.7%/pass,
which no swept config reaches yet).

## Mechanism findings of this run

1. **Layer-masked expansion** (`expand(seed) XOR mask(layer_index, offset)`)
   is the corrected, viable form of position salting: zero metadata (both
   mask inputs are decoder-known; the mask schedule is a fixed protocol
   constant — an explicitly allowed "fixed-profile phase schedule" refresh),
   fresh = 1 for every window every pass, and the seed table stays unsalted
   and shared. Law-validated with real SHA-256 dice
   (`freshness_law_validation.py`: sustained ~0.13–0.18%/pass measured at toy
   scale with no decay; permutation ~0.05–0.08%; kernel conservative).
   Decode-proven nested (`position_salt_decode_proof.py`).
2. **Position-only salting is dead** — the validator measured zero accepts
   from pass 3 and the cause is analytic (emission-replication deadlock).
   This is a new hard gate: *a refresh keyed only to emission state that
   reproduces itself on a no-accept pass refreshes nothing.*
3. **J2D1 roughly doubles** the sustained rate vs J3D1 at block-8 budgets
   (min record 6 vs 7; every budget count fattens). Depth cap 28 is not
   binding below arity-5 spans at B=8.
4. **LITERAL_RUN** delivers the ε-bloat end (pass-1 1.0027 measured in-model
   at S0=1024) but is junction-starved alone. Its real role is **junction
   density engineering**: the optimum exposes φ≈0.5–0.75 of mass as singles
   and fragments the rest into ~2-block runs (S0 ≈ N/4). Re-segmentation is
   the legal rechunk: boundaries are explicit charged headers.
5. **Grid-mode records** (expansion = exactly a·B bits at any bit offset,
   length decoder-known) price run-interior attack honestly via a walk DP
   (clean / dirty / interior classes; clipping a record mid-bits forces the
   remnant under a new charged header). An early revision laundered dirty
   mass as clean through short runs; fixed, numbers re-evaluated (leaders
   moved ~1.17 → ~1.01 %/pass).
6. **k=2 XOR records decode and search as claimed** (square-root pair-space
   demonstrated in the toy proof) but cost ~9× in rate at B=8 spans. With
   masked targets making k=1 table-shared, MitM is no longer needed for
   compute feasibility; it remains a niche option for spans ≥ ~60 bits.

## Cost pinning status

`cost_pin.py` / `cost_pin_report.json`: golden vectors for the reference
J3D1 layout (jumpstarter stores tier_width−1; boundary bug at payload width
≥254 fixed — widths unchanged) pass round-trip and width equality for all
tier boundaries and dense sweeps. J2D1 min record 6 bits / cap 28; J3D1 min
7 / cap 508. The 127-vs-508 payload-cap discrepancy resolves to **508** on
repo-internal evidence (`max_width_for_config(3,1)` in
`src/bin/v1_cost_table.rs`); a true 127 cap is inconsistent with the repo's
own cost arithmetic. **Cargo was unavailable in this sandbox: costs are NOT
newly Rust-validated** (`rust_probe: NOT_NEWLY_VALIDATED` in the report).
Re-pin locally: `cargo run --quiet --bin v1_cost_table && python
model_analysis/proof_kernel/cost_pin.py`. Final wire-layout pin against the
sibling `../lotus` crate remains open (crate not in this checkout).

## Reproduction

```powershell
# v-next sweep (two-stage; artifacts: vnext_sweep.json, vnext_best.json, vnext_top_profiles.csv)
python model_analysis/proof_kernel/vnext_search.py --stage rank
python model_analysis/proof_kernel/vnext_search.py --stage final

# decode proofs (wire bits == charged bits, exact round trips)
python model_analysis/proof_kernel/bit_literal_decode_proof.py
python model_analysis/proof_kernel/literal_run_decode_proof.py
python model_analysis/proof_kernel/position_salt_decode_proof.py
python model_analysis/proof_kernel/mitm_xor_decode_proof.py

# freshness law with real SHA-256 dice (law validation, not viability)
python model_analysis/proof_kernel/freshness_law_validation.py --runs 5 --passes 10

# cost pin
cargo run --quiet --bin v1_cost_table
python model_analysis/proof_kernel/cost_pin.py

# audited v1/BIT_LITERAL lane (unchanged reference kernel)
python model_analysis/proof_kernel/viability_search.py --write-artifacts
```
