# ADR-0002: Keep GPU Acceleration Research-Only

## Status

Accepted

## Context

The whitepaper discusses GPU/ASIC-scale lookup as a plausible path for making
large seed searches practical. The current repository has a `gpu` feature, a
`GpuSeedMatcher` API, tiling helpers, and CPU/GPU parity tests. However, the
current enabled backend deliberately uses deterministic CPU matching semantics;
there is no trusted OpenCL/CUDA kernel-backed matcher in the production
compression path.

## Decision Drivers

- Do not trust acceleration output without CPU parity.
- Do not call a feature production-ready because it compiles.
- Keep the CPU streaming path as the correctness reference.
- Preserve a future hardware path if measured evidence justifies it.

## Decision

GPU remains research-only.

`--features gpu` must stay buildable, and GPU API tests must keep passing, but
the project must not describe GPU as production acceleration until a real
hardware backend has parity tests and benchmark evidence.

## Consequences

Positive:

- The current release surface remains honest.
- Future GPU work has a clear promotion gate.
- CPU streaming remains the canonical correctness path.

Negative:

- Telomere does not currently have production hardware acceleration.
- Whitepaper-scale throughput remains theoretical or external to this repo.

## Promotion Criteria

GPU can move toward production only after:

- a real OpenCL/CUDA/kernel-backed matcher exists
- CPU/GPU parity tests cover selected spans and decompressed output
- benchmarks show a speed or energy win over CPU streaming
- failure modes and CPU fallback behavior are documented
- generated reports update `docs/ACCELERATION.md` and
  `docs/RESEARCH_SCORECARD.md`

## References

- `docs/ACCELERATION.md`
- `docs/RESEARCH_SCORECARD.md`
- `tests/gpu_determinism.rs`
- `src/gpu_impl.rs`
