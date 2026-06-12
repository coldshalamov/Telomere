# Telomere V1 — Implementation Map (code goes here when built)

The actual V1 codec is NOT yet built. This file marks the slots. Build
against `docs/SPEC_V1.md` ONLY. The legacy Rust in `src/` implements an
OLD wire format — reference scaffolding, do not extend.

| module | responsibility | spec section |
| --- | --- | --- |
| `header` | TLMR magic, Lotus-coded fields, checksum | SPEC §3 |
| `lotus` | J3D1 self-delimiting integers (pin against `cost_pin_report.json`) | SPEC §3 |
| `expander` | seed+position-salt -> long digest (SHA-256 stream) | SPEC §1, §2 |
| `search` | hash-from-zero frontier search, match table, greedy accept | SPEC §1, §5 |
| `shuffle` | i -> 5i mod P, cycle-walked, + exact inverse | SPEC §1 |
| `encoder` | pass loop: search -> replace-in-place -> shuffle; halt on empty probe; REMAINDER RUN emit | SPEC §1, §3 |
| `decoder` | stateless reverse: trial decode ("multiple decodings"), checksum referee, in-place expansion, wrapper strip | SPEC §2, §4 |

Acceptance for every module: charged bits == wire bits; round trip
exact; ZERO stored metadata beyond SPEC §3's header. The toy reference
behaviors live in `model_analysis/proof_kernel/` (see SPEC §8).
