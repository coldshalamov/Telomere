# Telomere R&D Roadmap — 30 / 60 / 90 days

Baseline: June 2026 proof-kernel revision. Primary target:
`grid_heavy_phi0.5_S262144_J2` (math_candidate, +0.908 %/pass min, payback
81, 0.541 @ 500, zero-metadata layer-masked refresh, shared-table compute).
Reference floor: audited BIT_LITERAL config (0.1328 %/pass, payback 126).

## 30 days — freeze the truth surface, finish the pins

| item | exit criterion | owner artifact |
| --- | --- | --- |
| Lotus wire pin | golden vectors vs `../lotus` crate match `cost_pin_report.json` for every tier boundary; 127-vs-508 closed in the crate's own arithmetic | `cost_pin.py` rerun with cargo |
| Rust cost re-pin | `cargo run --quiet --bin v1_cost_table` + `cost_pin.py` report `status: validated` | CI job |
| Long-horizon dice test | layer-masked lane sustains ≥ 0.8× its pass-2 rate over 50 toy passes (kills risk 5 or the primary) | `freshness_law_validation.py --passes 50 --runs 10` |
| Walk-DP stress | 2-bucket run-length mix changes leader rates < 2×; Monte-Carlo toy layer vs DP | new `walk_dp_validation.py` |
| Reviewer packet | a third party reproduces ledger numbers from the repro commands alone | `INVESTOR_RESEARCH_BRIEF.md` |

## 60 days — implement one model-equivalent pass for real

| item | exit criterion |
| --- | --- |
| v-next reference codec primitive set (BIT_LITERAL, LITERAL_RUN, layer-masked expansion; J2D1 profile) behind a profile flag in `src/` | `cargo test` round-trips mirroring the four toy decode proofs at the wire level; charged == wire asserted in Rust |
| Tiny end-to-end bit-layer demo | a real 1–16 MB file runs 10+ passes; measured pass ledger vs model rows within 2× (risk 3 gate) |
| Pass-cost benchmark | measured lookups/s and s/pass/MB on (a) one CPU core, (b) one consumer GPU; fills the implemented-throughput column of the compute table |
| Trajectory optimization in-kernel | per-pass (φ, S0 schedule, alphabet schedule) control search; target: payback < 60 modeled |

## 90 days — economics decision

| item | exit criterion |
| --- | --- |
| Post-compression pilot (product lane) | run the implemented passes on zstd/zip outputs + random/encrypted controls; measured rate vs the content-blind model on high-entropy bytes |
| Cost/TB estimate from measured throughput | $/TB to 1.0×, 0.84×, 0.60× on CPU / GPU / projected ASIC; compare against cold-storage $/TB-year |
| Investor demo | one reproducible end-to-end artifact: file in, N passes, decode-verified, ledger out |
| GPU/FPGA/ASIC go/no-go | decision memo: proceed to hardware path only if measured-throughput economics close within 10× of the ASIC projection (risk 9 kill condition) |

## Standing rules

Laptop runs validate laws and decode proofs only — never viability. Every
new number lands in `TELOMERE_RESULT_LEDGER.md` with an evidence class.
Oracle rows stay labeled. Any mechanism whose gain depends on source
structure is separated from the core content-blind claim.
