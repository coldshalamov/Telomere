# Telomere Research Plan

This file is no longer the format or architecture source of truth. Use:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/FORMAT.md](docs/FORMAT.md)
- [docs/RESEARCH_PROGRAM.md](docs/RESEARCH_PROGRAM.md)
- [docs/RESULTS.md](docs/RESULTS.md)
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)

## Current Research Decisions

- `.tlmr` v1 is one-layer-decodable only.
- `.tlmr` v2 is the experimental recursive format with explicit layer
  descriptors and index-free decompression.
- The active file header is the 40-byte rich v1 header, not the old 3-byte
  experimental header.
- Lotus preset 2 encodes canonical seed indices through the J3D2 tiered
  integer codec from the sibling crate at `../lotus/src/lib.rs`; arity-1
  records with seed index 0 fit in 8 bits.
- Arity `2` is valid.
- Literal marker is `0xFF`.
- GPU is research-only and currently uses deterministic CPU fallback semantics.
- Gloss tables and bloom pruning are removed from the active architecture.
- Random data is not expected to compress.
- Indexed and streaming v2 engines use exact generated-prefix matching, not
  digest-prefix matching of target blocks.

## Research Backlog

1. Measure whether a real OpenCL implementation can beat the CPU/rayon path.
2. Generate larger result artifacts from committed scripts before making any
   performance claims beyond the current small matrix.
3. Extend the current per-layer indexed/streaming telemetry into larger
   experiment artifacts with arity, span, and pass-count sweeps.
4. Broaden the planted-density, planted-offset, structured-data, and
   recursive-pass cases into parameter sweeps.
5. Explore whether an alternative candidate lattice beats the active flat
   verified-candidate plus weighted-interval selector enough to justify the
   added complexity.

All future research claims should be backed by generated artifacts, not
hand-written tables.
