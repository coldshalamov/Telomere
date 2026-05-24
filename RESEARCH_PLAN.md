# Telomere Research Plan

This file is no longer the format or architecture source of truth. Use:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/FORMAT.md](docs/FORMAT.md)
- [docs/RESULTS.md](docs/RESULTS.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)

## Current Research Decisions

- `.tlmr` v1 is one-layer-decodable only.
- The active file header is the 40-byte rich v1 header, not the old 3-byte
  experimental header.
- Lotus preset 1 is the concrete 4-field codec in `src/header.rs`.
- Arity `2` is valid.
- Literal marker is `0xFF`.
- Seed payloads in `.tlmr` v1 must be byte-aligned.
- GPU is research-only and currently uses deterministic CPU fallback semantics.
- Gloss tables and bloom pruning are removed from the active architecture.
- Random data is not expected to compress.

## Research Backlog

1. Measure whether a real OpenCL implementation can beat the CPU/rayon path.
2. Decide whether recursive multi-pass belongs in `.tlmr` v2.
3. If recursive multi-pass returns, design layer metadata and recursive decode
   before writing nested outputs.
4. Generate larger result artifacts from committed scripts before making any
   performance claims.
5. Evaluate whether research hash-table tools should be consolidated or removed.

All future research claims should be backed by generated artifacts, not
hand-written tables.
