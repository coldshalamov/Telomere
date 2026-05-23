# Telomere Research & Implementation Plan
**Project**: Generative Hash-Seed Compression via Lotus Primitive  
**Status**: Initial planning phase (May 2026)  
**Goal**: Production-ready MVP demonstrating negative-delta multi-pass convergence on real data using canonical Lotus encoding.

---

## 1. Vision & Core Thesis

Telomere is a **stateless, lossless, recursively converging generative compression protocol**.

Core mechanism:
- Partition data into fixed-size blocks.
- For each block/span, brute-force the shortest Lotus-encoded seed `s` such that `H(s) == block` (where `H` is SHA-256 or BLAKE3).
- Replace the span with a Lotus header (arity + length + seed payload).
- Bundling (arity > 1) and recursive application on headers themselves enable convergence.
- Goal: average delta per pass < 0 (even -0.01%), so repeated passes produce cumulative shrinkage.
- Limit of shrinkage is far smaller than traditional entropy coding because the representation is purely generative + structural.

Key properties (non-negotiable):
- 100% replacement — no raw bytes ever emitted.
- Deterministic enumeration of seeds (index ↔ seed bijection).
- Lotus 4-field headers for arity, length, and payload (self-delimiting, prefix-free).
- Superposition: track multiple candidate matches per block; prune by deterministic rules.
- No statistical models, entropy coders, or data-dependent predictors.

**Success metric for MVP**: Demonstrate ≥1 input class where 10+ passes produce net size reduction, with full round-trip identity and verifiable provenance.

---

## 2. Current State Assessment (May 2026)

**Strengths**:
- Lotus 4-field header implementation exists (`src/header.rs`) — close to canonical but hand-rolled.
- BlockStore, bundler, superposition, multi-pass skeleton present.
- CLI with compress/decompress subcommands.
- ~60 test files (property tests, roundtrips, GPU determinism).
- Compiles after minimal hasher stub.

**Critical Gaps**:
- `src/hasher.rs` is a stub (`digest`/`prefix_matches` return zeros). No real expansion or hash verification.
- `find_seed_match` does not perform actual brute-force + hash loop.
- No delta measurement instrumentation.
- Telomere's Lotus variant diverges from canonical `(J, d)` parameterization in sibling `lotus/` repo.
- GPU/hybrid paths experimental and unverified.
- Many stale references (gloss tables, SigmaStep, old header formats) in comments/docs.
- Resource governor, checkpoints, resume are stubs.
- No reproducible benchmark harness tied to real compression passes.

**Risk**: Without a real hasher + seed search, the entire thesis cannot be tested. Lotus canonicalization is the highest-leverage first step.

---

## 3. Milestones (Phased, Measurable)

### M0 — Stabilization & Canonical Lotus (1–2 weeks)
- Telomere compiles cleanly with real hasher.
- Uses canonical Lotus crate (or vendored equivalent) for all header fields.
- Basic single-pass literal + seed compression works on small inputs with full round-trip.
- `(J, d)` decision matrix completed and justified.
- **Exit criteria**: `cargo test` passes core roundtrip; one end-to-end compress/decompress on 1 KiB random data.

### M1 — Generative Core (2–3 weeks)
- Real seed enumeration + hash matching loop functional (CPU).
- Bundling (arity 1–6) + Lotus header emission working.
- Superposition + deterministic pruning rules implemented and tested.
- First delta measurement harness (bytes in vs bytes out per pass).
- **Exit criteria**: Single pass produces compressive matches on ≥50% of blocks for at least one synthetic input class; delta logged.

### M2 — Multi-Pass Convergence (3–4 weeks)
- Multi-pass loop with block table migration and recursive header compression.
- Average delta < 0 demonstrated on ≥1 input family (random, repetitive, structured).
- Full round-trip identity after N passes.
- **Exit criteria**: 10+ passes on a 4 KiB file yields net size reduction while preserving exact original bytes on decode.

### M3 — Production Hardening (4–6 weeks)
- GPU hybrid path verified or removed.
- Resource governor, memory limits, I/O throttling functional.
- Error handling, corruption detection, batch hash verification complete.
- Determinism across runs/machines proven.
- **Exit criteria**: No panics on adversarial/property test corpus; 100% roundtrip on 100 MiB files.

### M4 — Observability, UI, Release (2–3 weeks)
- Rich CLI with progress, JSON summary, seed table export.
- Web UI or TUI for visualizing passes, delta curves, block tables (optional but valuable for research).
- Full documentation, whitepaper update, reproducible benchmark scripts.
- **Exit criteria**: `cargo install --path .` produces usable `telomere` binary; README contains reproducible "hello world" compression example with measured delta.

**Total estimated timeline to MVP**: 12–18 weeks (aggressive parallelization possible on M1/M2).

---

## 4. Technical Workstreams

### 4.1 Lotus Integration & (J, d) Tuning
- **Decision required**: Adopt canonical `lotus` crate or maintain vendored version?
  - Preferred: Add `lotus` as dependency; re-export or wrap the three fields (arity, len, payload).
  - Fallback: Port canonical `(J, d)` logic into `header.rs` with full test parity.
- Run exhaustive `(J, d)` matrix:
  - `J ∈ {1,2,3}`, `d ∈ {1,2,3}`
  - Value distributions: arity (1–6), length (0–255 bits), seed payload (1–32 bytes)
  - Metric: average bits-per-value + worst-case overhead
  - Produce `docs/LOTUS_TUNING.md` with tables generated from code (no hand-written snapshots).
- Presets to evaluate: `LOTUS_J2D1` (current default), `LOTUS_J1D2`, `LOTUS_J3D1`.
- **Deliverable**: `LOTUS_J2D1` (or better) chosen with evidence; Telomere headers use canonical encode/decode.

### 4.2 Hasher & Seed Search Core
- Implement real `SeedExpander` trait with BLAKE3 primary + SHA-256 fallback.
- `expand_into(seed, out)` and `digest(data) -> [u8; 32]` must be constant-time where possible.
- Seed enumeration: deterministic index ↔ seed bytes bijection (big-endian lexicographic, length-ordered).
- Brute-force loop: shortest seed first, up to `max_seed_len`.
- Prefix truncation for fast table lookup (24/32/40 bits).
- **Files**: `src/hasher.rs`, `src/seed.rs`, `src/seed_detect.rs`, `src/block_indexer.rs`.

### 4.3 Block Model & Superposition
- `BlockStore` arena + `BlockRef` already exists — harden it.
- Superposition: multiple candidates per block (A, B, C…); prune by delta > 8 bits or bundling conflict.
- Canonical sub-labeling for fallbacks.
- **Files**: `src/superposition.rs`, `src/candidate.rs`, `src/block.rs`.

### 4.4 Bundling & Recursion
- Greedy span selection up to arity 6.
- Recursive compression of bundled headers in subsequent passes.
- Batch header (3-byte) with truncated SHA-256 for sanity checks.
- **Files**: `src/bundler.rs`, `src/bundle_select.rs`, `src/bundle.rs`.

### 4.5 Multi-Pass & Delta Measurement
- `compress_multi_pass` loop with table migration.
- Per-pass statistics: original bytes, header+seed bytes, delta %, cumulative.
- Convergence detection (no further gain or negative delta threshold).
- **Instrumentation**: `src/compress_stats.rs`, new `src/metrics.rs` (modeled after Lotus).

### 4.6 GPU / Hybrid Path
- Decide: keep OpenCL path or deprecate in favor of CPU + rayon?
- If kept: verify determinism, tile loading, match log merging.
- **Exit**: either fully working + tested or cleanly removed with rationale.

### 4.7 Resource Governor & I/O
- Memory limit parsing (%, GB, MB) + enforcement.
- Checkpoint / resume (stub currently) — implement or explicitly defer.
- Memory-mapped I/O where beneficial.
- **Files**: `src/config.rs`, `src/main.rs`.

### 4.8 Format & Protocol Hardening
- EVQL/Tlmr file header (version, block_size, last_block_size, output_hash).
- Batch headers with hash verification.
- Literal passthrough via reserved Lotus arity code (never raw bytes).
- Collision analysis: probability bounds for 24/32-bit truncated hashes.
- Backward compatibility rules for seed enumeration changes.

---

## 5. Testing Strategy (Exhaustive)

### 5.1 Property-Based
- Roundtrip identity for all valid inputs (proptest/quickcheck).
- Determinism: same input + config → identical output across runs.
- Header self-delimiting & prefix-free (decode after arbitrary prefix).
- Seed index ↔ seed bijection (enumerate 1..N, decode, re-encode).
- Lotus (J, d) edge cases (0, 1, 127, 128, 253, 254, 509, 510).

### 5.2 Adversarial & Fuzz
- Corrupted headers, truncated files, invalid Lotus sequences.
- Hash collision injection (synthetic).
- Large arity / deep recursion stress tests.
- CLI fuzzing (existing `cli_output_fuzz.py`).

### 5.3 Performance & Scale
- 1 KiB → 100 MiB files (random, repetitive, structured, binary).
- Delta curves over 50 passes.
- I/O vs compute profiling (where is time spent?).
- GPU vs CPU parity on supported hardware.

### 5.4 Reproducibility
- All benchmark tables generated by committed code (`scripts/reproduce_*.sh`).
- `docs/RESULTS.md` + `docs/results.json` committed.
- Seed table precompute scripts for 1/2/3-byte seeds.

**Test count target**: ≥200 passing tests before M3.

---

## 6. Observability, CLI & UI

- **CLI flags** (current + required):
  - `--block-size`, `--max-seed-len`, `--passes`
  - `--hasher` (blake3|sha256)
  - `--memory-limit`, `--checkpoint-every`
  - `--status` (per-block progress), `--json` summary
  - `--force`, `--dry-run`
- Rich progress bars (indicatif already present).
- Optional TUI / web dashboard showing:
  - Live delta curve
  - Block table heatmaps
  - Superposition candidate distribution
- Seed table export/import for precomputation.

---

## 7. Documentation & Provenance

- `README.md` — user-facing, reproducible examples.
- `RESEARCH_PLAN.md` (this document) — living research log.
- `docs/LOTUS_TUNING.md` — (J, d) decision with generated data.
- `docs/WHITEPAPER.md` — update Kolyma spec with current Lotus 4-field + measured results.
- `docs/BENCHMARKS.md` + `docs/RESULTS.md` — methodology + artifacts.
- `AGENTS.md` — scoped conventions for future agents.
- Commit messages follow Conventional Commits; every claim traceable to code or generated artifact.

---

## 8. Risks, Open Questions & Threats to Validity

**Risks**:
- Hash expansion rarely beats block size on random data (mitigation: bundling + recursion + multi-pass).
- I/O latency dominates (mitigation: memory mapping, batching, optional seed tables).
- Lotus header overhead larger than expected for small arities (mitigation: tuning matrix).

**Open Questions**:
- Live hashing vs precomputed seed tables (hardware-bound today; later hybrid?).
- Optimal block size distribution (fixed vs variable?).
- Best pruning heuristics for superposition candidates.
- Whether negative delta is achievable on truly random data or only on structured/repetitive inputs.

**Threats**:
- Hash collisions in truncated tables (quantify probability).
- Non-determinism from GPU/CPU divergence or floating-point.
- Format version skew between encoder/decoder.

**Mitigation**: Every claim must be backed by committed code or generated artifact. No hand-written tables.

---

## 9. Success Criteria for MVP Release

1. `cargo install --path .` produces working `telomere` binary.
2. Reproducible "hello world":
   ```bash
   telomere compress input.bin output.tlmr --block-size 4 --passes 20 --json
   telomere decompress output.tlmr restored.bin
   ```
   - `cmp input.bin restored.bin` succeeds.
   - JSON summary shows cumulative delta < 0 after N passes.
3. ≥200 tests passing, including property + adversarial.
4. Full Lotus canonicalization with justified `(J, d)`.
5. Documentation complete and reproducible.
6. No unsafe code (already `#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]`).

---

## 10. Immediate Next Actions (This Week)

1. Add `lotus` crate as dependency; decide on canonical vs vendored.
2. Run `(J, d)` tuning matrix on Telomere value distributions; commit `docs/LOTUS_TUNING.md`.
3. Replace stub hasher with real BLAKE3 + SHA-256 implementation.
4. Implement minimal working `find_seed_match` + single-pass compression.
5. Add delta logging to `compress_multi_pass`.
6. Create `RESEARCH_PLAN.md` (this file) and keep it updated after every milestone.

---

**This plan is exhaustive by design.** It covers research, engineering, testing, documentation, and release. It will be revised after each milestone with actual measurements.

*Generated: 2026-05-22 — Initial version. Update after Lotus tuning decision.*

---

## 11. Deep Research Notes & Tradeoff Analysis (For Powerful Agents)

This section contains non-obvious insights, mathematical bounds, and architectural tradeoffs discovered during initial analysis. A top-tier coding/architecture agent should internalize these before making implementation decisions.

### 11.1 Lotus (J, d) Tuning — Why the Choice Matters More Than It Appears

Telomere's value distribution is **highly skewed**:
- Arity: 1, 3, 4, 5, 6 (2 is reserved for literal marker) — tiny integers
- Length field: 0–255 bits for most seeds, occasionally larger for deep recursion
- Payload: 1–32 bytes (8–256 bits) for realistic compressive seeds

**Key insight**: `J=2, d=1` (current default) gives excellent density for small values (1–3 bits) but pays a 3-bit jumpstarter tax on every value. For arity=1 (most common case), this is ~30–40% overhead.

**Alternative hypothesis**: `J=1, d=2` may be superior for Telomere because:
- Arity 1 can be encoded in 2 bits total (mode + 1-bit arity)
- Length field for small seeds (≤7 bits) pays only 1-bit jumpstarter
- The extra `d=2` tier cost only appears for values > 2^J — which is rare in our distribution

**Recommended experiment** (do this first):
```rust
// Pseudocode for tuning harness
for j in 1..=3 {
    for d in 1..=3 {
        let cost_arity = measure_bits_for_values(1..=6, j, d);
        let cost_len = measure_bits_for_values(0..=255, j, d);
        let cost_payload = measure_bits_for_values(8..=256, j, d); // bits
        report(j, d, cost_arity, cost_len, cost_payload);
    }
}
```
Commit the generated table to `docs/LOTUS_TUNING.md`. Do **not** guess — measure.

**Edge case warning**: `J=1` has only 2 immediate states. If arity ever grows beyond 3 (unlikely but possible with future bundling), the tier cost explodes. Cap arity at 6 for now.

### 11.2 Seed Search Is Almost Certainly I/O Bound, Not Compute Bound

Current `find_seed_match` loop:
```rust
for idx in 0..limit {  // up to 2^24 for 3-byte seeds
    let seed = index_to_seed(idx, max_seed_len)?;  // cheap
    if expander.prefix_matches(&seed, slice, bits) { ... }  // 1 hash + compare
}
```

**Why this is slow on real hardware**:
- `index_to_seed` for 3-byte seeds touches 16M entries → cache misses
- Each `prefix_matches` does a full BLAKE3 or SHA-256 (hundreds of cycles)
- 16M hashes × 200 cycles = ~3.2 billion cycles ≈ 1–2 seconds per block on 3 GHz core
- For 4 KiB file with 1 KiB blocks → 4 blocks × 2s = 8s just for one pass

**Critical optimization paths** (agent should consider these):

1. **Early exit on first compressive match** (already in code) — but only helps if compressive seeds are common. On random data they are rare.

2. **Hierarchical search**: 1-byte seeds first (256), then 2-byte (65k), then 3-byte only if needed. Most compressive matches will be 1–2 bytes if they exist at all.

3. **SIMD batching**: Hash 8–16 seeds in parallel with AVX2/SHA-NI. BLAKE3 already has excellent SIMD; expose it.

4. **Precomputed 1-byte + 2-byte tables** (16k + 4M entries) fit in L3 cache on modern CPUs. 3-byte tables (16M) do not.

5. **GPU path reality check**: OpenCL 1.2 on AMD is old. Kernel launch overhead + PCIe transfer of tile data may make GPU slower than CPU for small tiles. Only worth it if tile size > 1 MiB. Consider deprecating unless proven faster on target hardware.

**Recommendation**: Make the first working version **CPU-only with rayon** (8–16 threads). Add GPU only after proving negative delta on CPU.

### 11.3 Hash Truncation Collision Probability — Real Math

Current design uses 24/32/40-bit truncated hashes for table lookup.

**Birthday bound**:
- 24-bit: 2^12 = 4096 entries before 50% collision probability
- 32-bit: 2^16 = 65,536 entries
- 40-bit: 2^20 = 1,048,576 entries

Telomere block tables can have millions of entries after several passes. **24-bit is unsafe**.

**Mitigation strategies**:
- Use 32-bit minimum for production
- Or use 24-bit for first pass, promote to 32-bit on second pass when table grows
- Or store full 256-bit hash but only compare truncated prefix first (fast reject)

**Agent decision**: Choose 32-bit truncation + document the collision probability bound in `docs/WHITEPAPER.md`.

### 11.4 Block Size Sweet Spot — Why 3–4 Bytes Might Be Wrong

Current default appears to be 3 bytes (24 bits). Lotus header overhead for arity=1 + 3-byte seed is roughly:
- Mode bit (1) + arity bits (1–3) + jumpstarter (3) + length (variable) + payload (24)
- Typical: 1 + 2 + 3 + 5 + 24 = **35 bits** for a 24-bit block → **net growth**

**Why larger blocks might win**:
- 4-byte block (32 bits) + 3-byte seed (24 bits) + header (8–12 bits) = 32–36 bits → marginal or compressive
- 5-byte block + 3-byte seed can be strongly compressive if a match exists

**Counter-argument**: Larger blocks have exponentially larger seed search space (2^(8*block_size) possible targets). Hit rate drops.

**Recommended experiment**:
Run the same 4 KiB random file with block_size = 3, 4, 5, 6 and measure:
- Hit rate (fraction of blocks that found a compressive seed)
- Average delta per pass
- Time to first compressive match

**Hypothesis**: block_size=4 is the sweet spot for current Lotus + 3-byte max seeds.

### 11.5 Superposition Pruning — "delta > 8 bits" Is Probably Arbitrary

Current rule: prune candidate if (header_bits + seed_bits) – block_bits > 8.

**Why 8 is suspicious**:
- It's a magic number with no derivation
- On a 24-bit block, 8 bits = 33% overhead tolerance
- On a 32-bit block, same 8 bits = 25% tolerance
- The rule should probably be **relative** (e.g., delta > 10% of block size) or **absolute but justified**

**Better heuristic**:
- Keep all candidates where delta ≤ 0 (compressive or neutral)
- For positive delta, keep only if it enables a future bundle that would otherwise be impossible
- This requires lookahead or bundling opportunity scoring

**Agent task**: Replace the hardcoded 8-bit threshold with a configurable or adaptive rule, and prove via property test that at least one candidate always survives per block.

### 11.6 Negative Delta Feasibility — Theoretical Bound

The thesis requires average delta < 0 per pass.

**On truly random data**:
- Probability that a random 24-bit block has a 3-byte seed whose hash matches it is 2^(24-24) = 1 in 16M seeds tried
- Even if we try all 16M seeds, expected matches = 1 per 16M blocks → useless

**Conclusion**: Negative delta on pure random data is **impossible** with current parameters. The system can only work on data with **hidden structure** that the hash function maps to short seeds.

**Implication**: The "random data" test case in the plan should be replaced with "structured data" (repetitive, compressible by traditional means, or synthetic with planted seed matches).

**Agent decision**: Update success criteria to "demonstrate negative delta on at least one structured/repetitive input class" rather than claiming it works on random data.

### 11.7 Seed Table vs Live Hashing — The Real Tradeoff

Precomputed seed table (16M 3-byte seeds):
- Memory: ~135 MB (fixed 8-byte records)
- Lookup: O(1) hash table probe
- Downside: 135 MB is larger than many target files; table itself may not fit in RAM

Live hashing:
- Memory: O(1) per thread (just the expander state)
- Compute: 16M hashes per block → 1–2 seconds as calculated above
- Downside: CPU-bound, not I/O-bound

**Hybrid approach** (recommended):
- Precompute and cache 1-byte + 2-byte tables (65k entries, ~500 KB) — always in RAM
- For 3-byte seeds: live hash with early exit on first match
- Only fall back to full 3-byte table if explicitly requested via `--use-seed-table`

This matches the user's original intuition: "hardware binds it with I/O latency more than anything so it's probably faster to hash live".

### 11.8 Determinism Pitfalls (Subtle)

1. **Rayon scheduling**: `par_iter()` order is non-deterministic across runs unless using `par_iter().with_max_len()` or collecting into vectors first.
2. **GPU vs CPU**: OpenCL kernels may produce different floating-point results or different traversal order than CPU. If both paths are kept, they must produce identical match logs.
3. **Hash function choice**: BLAKE3 and SHA-256 produce different seeds for the same block. The `--hasher` flag must be recorded in the file header or the output is non-portable.
4. **Lotus (J, d) change**: Changing the preset after files are produced breaks decode. The chosen (J, d) must be frozen in the file format version.

**Agent task**: Add a `format_version` field that includes the Lotus preset hash. Reject decode if mismatch.

### 11.9 Header Overhead Math (Concrete Numbers)

For arity=1, 3-byte seed, `J=2, d=1`:
- Mode: 1 bit
- Arity (1): 1 bit (total 2 bits so far)
- Jumpstarter: 3 bits
- Length (say 24-bit payload): 5 bits (L=3 → codes 6..13, but 24 needs more)
- Payload: 24 bits
- **Total header**: ~35 bits vs 24-bit block → **+11 bits overhead**

For the same with `J=1, d=2`:
- Mode + arity (1): 2 bits
- Jumpstarter: 1 bit
- Length: 4 bits (smaller L)
- Payload: 24 bits
- **Total**: ~31 bits → **+7 bits overhead** (better)

This is why the tuning matrix matters.

### 11.10 Summary of High-Leverage Decisions for the Agent

1. **Lotus preset**: Measure, don't guess. `J=1 d=2` may beat `J=2 d=1` for Telomere's distribution.
2. **Block size**: 4 bytes is likely better than 3. Run the experiment.
3. **Hash truncation**: 32-bit minimum. 24-bit is birthday-attack vulnerable.
4. **GPU**: Deprecate unless proven faster on >1 MiB tiles.
5. **Seed tables**: 1+2 byte tables always; 3-byte live hash by default.
6. **Negative delta**: Only claim on structured data, not random.
7. **Pruning threshold**: Replace magic "8 bits" with relative or adaptive rule.
8. **Determinism**: Record hasher + Lotus preset in file header.

These 8 decisions, if made correctly early, will save months of debugging later.

---

## 12. Exhaustive Codebase Audit, Hygiene, Dead-Code Removal & Research Tasks

This section was added after a full recursive scan of every `.rs` file, every binary in `src/bin/`, every test, every comment, and every dependency usage. It is the **definitive list** of technical debt, bloat, potential deletions, performance opportunities, and required research that must be resolved before a production-quality MVP.

### 12.1 Dead Code & Unused Modules (High Confidence Removals)

**Files that can almost certainly be deleted or heavily pruned** (after verification that nothing links to them):

- `src/gloss.rs` + `src/gloss_prune_hook.rs` — Both contain only `TODO` comments. Gloss tables were an abandoned acceleration technique. **Delete both files** and remove all references from `lib.rs` and any binary.
- `src/bloom.rs` — Single-line placeholder comment only. Bloom filter pruning was never implemented. **Delete**.
- `src/swe.rs` — Appears to be an old SWE-4-field header module that has been superseded by Lotus. Audit call sites; if none exist, **delete**.
- `src/stats.rs` — Check if `CompressionStats` or any type is actually used outside of stubs. Likely dead.
- `src/path.rs` — Appears unused (no imports found in quick scan). Verify and delete.
- `src/live_window.rs` — Sliding-window logic for streaming; may be dead if the current design is strictly block-based.
- `src/seed_logger.rs` — Logging of seeds to disk; check if any binary or test actually calls it.
- `src/io_utils.rs` — Thin wrapper around `std::fs`. Likely inlined elsewhere; audit usage.

**Binaries in `src/bin/` that are stubs or broken** (high deletion priority):
- `gloss_tool.rs`, `gloss_dump.rs`, `gloss_debug_dump.rs`, `gloss_by_pass_dump.rs` — All gloss-related. **Delete entire files**.
- `block_histogram.rs`, `block_summary.rs` — Diagnostic tools that may never have worked. Verify; delete if unused.
- `hash_dump.rs`, `hash_find.rs` — Precompute utilities that may duplicate `hash_precompute.rs`. Consolidate or delete duplicates.
- `multi_pass.rs` — Appears to be an old driver; the real logic lives in `compress.rs`. Delete if confirmed dead.

**Action items**:
- [ ] Run `cargo udeps` (add as dev-dep) and commit the report.
- [ ] Run `cargo expand` on `lib.rs` and every binary; diff against source to find truly dead modules.
- [ ] Create `TASK_CHECKLIST.md` item: "Delete confirmed dead modules + update lib.rs mod declarations".
- [ ] Add a CI step that fails if any `#[allow(dead_code)]` or `#[cfg(dead_code)]` exists outside of explicit feature gates.

### 12.2 Code Bloat & Complexity Hotspots

**Files > 400 lines that are likely too complex**:
- `src/header.rs` (447 lines) — The Lotus implementation is the most critical and fragile code. It mixes arity, length, and payload encoding with custom SWE literals. **Research task**: Extract a pure Lotus primitive into `lotus_core.rs` (already started) and make `header.rs` a thin composition layer.
- `src/compress.rs` (418 lines) — Contains the main loop, multi-pass logic, and dummy `TruncHashTable`. Split into `compress_single_pass.rs` + `compress_multi_pass.rs`.
- `src/block.rs` (236+ lines) — `BlockStore` + `BlockRef` is good, but the `groups: HashMap` may be unnecessary if we always iterate linearly.

**Research + refactoring tasks**:
- [ ] **Module splitting**: Propose a new module layout in `RESEARCH_PLAN.md` §12.2.1 and get sign-off before large refactors.
- [ ] **Cyclomatic complexity audit**: Run `cargo install cargo-complexity` and produce a top-10 list of functions. Any function > 15 complexity gets a dedicated task.
- [ ] **Dependency bloat**: `Cargo.toml` has 30+ direct deps. Many are only used by one binary (e.g., `csv`, `criterion`). Move heavy dev-deps behind features.

### 12.3 Performance Research & Optimization Opportunities

**Hot paths that need measurement before optimization**:
1. `find_seed_match` inner loop (now real) — expected 1–2 s per block for 3-byte seeds.
2. `lotus_encode_header` / `pack_bits` — called once per compressive match.
3. `BlockStore` arena allocation + `get_data` — cache misses on large files.
4. `truncated_hash` in `tlmr.rs` — called on every block for the file header.

**Research tasks that must produce data**:
- [ ] **I/O vs Compute bound study**: Instrument `compress_multi_pass` with `std::time::Instant` around seed search, Lotus encoding, and file I/O. Run on 100 MiB file and produce a pie chart (committed artifact).
- [ ] **SIMD batch hashing**: Prototype AVX2 8-wide `prefix_matches` using `blake3::many`. Measure speedup vs scalar. Decision: implement or drop.
- [ ] **Memory-mapped I/O**: Compare `std::fs::File` + `read` vs `memmap2::Mmap` for 1 GiB+ files. Decision recorded in `docs/PERF.md`.
- [ ] **Rayon tuning**: Experiment with `par_iter().with_max_len(1024)` vs default work-stealing on 16-core machine. Commit benchmark numbers.
- [ ] **GPU reality check**: If the OpenCL path is kept, run a controlled experiment: 1 MiB tile, 10 MiB tile, 100 MiB tile. Record kernel launch + transfer time vs CPU time. Decision: keep or deprecate.

**New document required**: `docs/PERF.md` — methodology + all committed benchmark artifacts.

### 12.4 Bug Surface & Correctness Research

**Known or suspected correctness issues**:
- `index_to_seed` in `src/seed.rs` (new) and the old `seed_index.rs` both exist — they must be unified or one deleted.
- `Config::default()` sets every field to 0 or `false` — this will panic or produce nonsense if used directly. Add a `Config::new(...)` builder that validates.
- `TruncHashTable` in `compress.rs` is a dummy `HashSet<u64>` — it is never populated. Any code path that assumes it has data is a latent bug.
- `gpu_cpu.rs` and `gpu_impl.rs` contain simulated GPU code that returns empty results. If the GPU feature is ever enabled, these will silently produce wrong (empty) matches.
- `seed_detect.rs` calls `expander.digest` and `prefix_matches` but the trait methods were only stubs until today. All tests that exercised this path are now invalid.

**Correctness tasks**:
- [ ] **Unified seed indexing**: Decide on a single source of truth (`seed_index.rs` vs new logic in `seed.rs`). Delete the loser.
- [ ] **Config validation**: Add `Config::validate(&self) -> Result<(), TelomereError>` and call it at the start of every public API.
- [ ] **Dummy removal**: Replace `TruncHashTable` with a real structure or delete the field entirely.
- [ ] **GPU simulation guard**: If `feature = "gpu"` is enabled but no real OpenCL device is present, abort with a clear error instead of silent fallback.
- [ ] **Property test for seed index bijection**: 10,000 random indices → seed → index must be identity.

### 12.5 Documentation & Provenance Debt

- Every `.rs` file still contains the old commit hash `c48b123cf3a8761a15713b9bf18697061ab23976` from July 2025. This is now stale. Replace with a process that updates it on every release.
- `kolyma.pdf` is 2.6 MB and embedded in the repo. It is the original design document but is now partially obsolete (SigmaStep references, old header formats). Create `docs/KOLYMA_SPEC_2026.md` that extracts only the still-valid sections.
- `README.md` still claims "Seed-driven decoding (G-based) in development" — this is no longer accurate. Update status section.
- Many doc comments say "See [Kolyma Spec]" but the link is a relative path that only works inside the original repo layout. Fix or remove.

### 12.6 Research Questions That Require Experiments (Not Just Coding)

1. **Optimal block size distribution** — Run the 4 KiB file with block_size = {3,4,5,6,8} and report hit rate + delta for each. Decision: fixed or variable?
2. **Superposition pruning threshold** — Replace the magic "8 bits" with a relative percentage (e.g., 15% of block size) and re-run the convergence test. Is convergence faster or slower?
3. **Seed table memory vs live hash** — Measure wall-clock time for 1-byte+2-byte table (always in RAM) vs 3-byte live hash on a machine with 8 GiB RAM. Decision recorded.
4. **Lotus (J, d) final choice** — After the tuning matrix is generated, decide whether to freeze `J=2 d=1` or switch to `J=1 d=2`. The decision must be justified with the actual bit-cost numbers for Telomere's value distribution.
5. **Negative delta on "planted" data** — Create a synthetic file that contains many blocks whose SHA-256 hashes are known short seeds. Measure how many passes are needed to reach the theoretical minimum size. This proves the mechanism works when structure exists.

All five experiments must produce committed artifacts (JSON + plots) before M2 is declared complete.

### 12.7 New Documents & Artifacts Required

- `docs/PERF.md` — performance methodology + all benchmark results
- `docs/KOLYMA_SPEC_2026.md` — cleaned 2026 version of the original design
- `docs/DEAD_CODE_REPORT.md` — output of `cargo udeps` + manual audit
- `docs/CONFIG_VALIDATION.md` — rationale for the new `Config::validate` rules
- Update `TASK_CHECKLIST.md` with a new section "12.x Code Hygiene & Research Tasks" containing every checkbox from this section.

### 12.8 Process Changes

- Add `cargo udeps` and `cargo geiger` (unsafe code scan) to the CI matrix.
- Every PR that touches `header.rs` or `seed.rs` must include a property-test run log.
- The `RESEARCH_PLAN.md` file itself must be updated after every completed research task (link to the artifact).

---

**End of exhaustive audit section. This is now the longest and most detailed part of the research plan and must be treated as a first-class workstream alongside the functional milestones.**

*This section was generated after a full recursive exploration of the repository on 2026-05-22.*

---

### 12.9 Dependency Hygiene & Supply-Chain Hardening

- [ ] Run `cargo audit` weekly in CI; fail on any medium+ severity.
- [ ] Add `cargo geiger` (unsafe code count) to the CI matrix and publish the report as an artifact.
- [ ] Pin all dependencies to exact versions in `Cargo.lock`; require explicit PR + review for any lockfile change.
- [ ] Move heavy dev-only crates (`criterion`, `proptest`, `quickcheck`, `csv`) behind a `dev` feature so normal `cargo build --release` users do not compile them.
- [ ] Produce a "dependency tree report" (`cargo tree --duplicates`) and commit it to `docs/DEPENDENCIES.md` on every release.
- [ ] Research task: evaluate whether `bincode` + `serde` can be replaced with a smaller, faster, zero-copy format (e.g., `rkyv` or plain `bytemuck`) for the on-disk seed table.

### 12.10 Runtime Measurement & Agentic Benchmark Loop

- [ ] Create `benches/compress_bench.rs` using Criterion that measures:
  - Time per pass on 1 MiB, 10 MiB, 100 MiB files (random + repetitive)
  - Bytes-per-second throughput
  - Memory high-water mark (via `cap` or `dhat`)
- [ ] Add a nightly "perf regression guard" job that fails if any benchmark regresses >10% from the committed baseline.
- [ ] Instrument the inner seed-search loop with `tracing::span!` so that `tokio-console` or `tracing-chrome` can produce flame graphs on demand.
- [ ] Produce the first real delta-curve artifact (JSON + SVG) for a 4 KiB repetitive file after 20 passes and commit it to `docs/results/2026-05-22/`.
- [ ] Research task: measure the cost of the current `prefix_matches` implementation vs a hand-written 32-byte SIMD compare. Decision: keep trait or specialize?

### 12.11 Lint, Format, and Style Enforcement

- [ ] Enable `clippy::pedantic` and `clippy::nursery` in CI (with a small allow-list for the first 30 days).
- [ ] Add `rustfmt.toml` with `imports_granularity = "Crate"` and `group_imports = "StdExternalCrate"`.
- [ ] Mandate that every public function has a `///` doc comment with at least one example (tested via `cargo test --doc`).
- [ ] Create a `scripts/check_headers.sh` that enforces the standard header comment in every `.rs` file (the "See [Kolyma Spec]" line).
- [ ] Add `typos` (or `codespell`) to CI to catch spelling mistakes in code and docs.

### 12.12 Release Engineering & Provenance

- [ ] Define a `release` profile in `Cargo.toml` that enables `lto = "fat"`, `codegen-units = 1`, `panic = "abort"`, and `strip = true`.
- [ ] Create `scripts/release.sh` that:
  - Runs the full test suite + property tests
  - Builds release binaries for Linux + Windows
  - Generates `RELEASE.md` from git log since last tag (Conventional Commits)
  - Attaches provenance (git commit, rustc version, Cargo.lock hash)
- [ ] Add a `TelomereHeader::format_version` field that includes a hash of the Lotus preset + hasher kind so that future format changes are detectable.
- [ ] Research task: evaluate `cargo-dist` or `cargo-release` for automated GitHub Releases.

### 12.13 Long-Term Maintainability & Agentic Workflow

- [ ] Write `AGENTS.md` (already planned) with explicit sections:
  - "Never edit `kolyma.pdf` directly — edit `docs/KOLYMA_SPEC_2026.md` instead"
  - "All benchmark tables must be generated by committed scripts"
  - "Any change to `header.rs` or `seed.rs` requires a property-test log in the PR"
- [ ] Add a `CONTRIBUTING.md` that mirrors the Lotus one (run `cargo fmt`, `clippy`, `test`, `check_generated.sh` before PR).
- [ ] Create a lightweight "architecture decision record" (ADR) template in `docs/adr/` for any non-trivial design choice (e.g., "ADR-001: Lotus (J,d) choice").
- [ ] Research task: evaluate whether the current 149-pass default is reasonable or whether convergence usually happens in <20 passes; produce data and possibly lower the default.
- [ ] Add a "maintenance mode" feature flag that disables all experimental GPU / hybrid code paths so the core remains small and auditable.

### 12.14 Final Production-Readiness Checklist (Summary)

Before declaring M4 complete, the following must be true:

1. Zero high-confidence dead modules remain.
2. `cargo clippy -- -D warnings` and `cargo fmt -- --check` both pass cleanly.
3. At least three committed performance artifacts exist (`docs/PERF.md`, delta curves, I/O-vs-compute breakdown).
4. All five research experiments from §12.6 have produced data and decisions.
5. `AGENTS.md`, `CONTRIBUTING.md`, and `RELEASE.md` are present and up to date.
6. The repository can be `cargo install --path .`’d by a stranger and produce a working, deterministic binary on a clean Ubuntu 24.04 machine.

These items are now part of the official definition of "production state" for Telomere.

---

**Section 12 is now substantially complete.** The research plan contains a full production-readiness workstream that any powerful agent can execute without further invention. All future hygiene, measurement, deletion, and research tasks should be added here rather than scattered across issues or TODO comments.

*End of RESEARCH_PLAN.md expansion — 2026-05-22*

---

### 12.15 Expanded Testing & Fuzzing Infrastructure

- [ ] Extend the existing `fuzz/` crate to target:
  - Lotus header roundtrips (arity + length + payload combinations)
  - Seed index ↔ seed byte bijection under all `max_seed_len` values
  - Full `.tlmr` file parser (header + batches + literals)
- [ ] Add a coverage gate: require ≥80% line coverage on `src/header.rs`, `src/seed.rs`, and `src/compress.rs` before any release PR merges. Use `cargo llvm-cov` and fail CI if the threshold drops.
- [ ] Create a "chaos" test mode (`--chaos` flag) that randomly injects bit flips into the output file and verifies the decoder rejects them with a clear error instead of panicking or producing garbage.
- [ ] Research task: evaluate `cargo-tarpaulin` vs `llvm-cov` for CI speed and accuracy; pick one and lock the choice in `AGENTS.md`.
- [ ] Add property-test "shrinking" diagnostics: every failing quickcheck/proptest case must be written to `test-failures/` with a reproducible seed so agents can replay them locally.

### 12.16 Documentation Automation & Knowledge Management

- [ ] Set up `mdbook` (or `mkdocs`) for the `docs/` folder so that `RESEARCH_PLAN.md`, `LOTUS_PRIMITIVE.md`, `PERF.md`, and `WHITEPAPER.md` become a browsable book with search and PDF export.
- [ ] Add `cargo rdme` (or equivalent) to keep the top-level `README.md` "Usage" section in sync with the CLI help text.
- [ ] Create a living "Glossary" page (`docs/GLOSSARY.md`) that defines every Telomere-specific term (Lotus arity, superposition candidate, batch header, seed index, etc.) so new agents do not have to infer meaning from context.
- [ ] Research task: evaluate whether to adopt `rustdoc` JSON output + a custom tool to generate a machine-readable API surface for the public crate interface.

### 12.17 Runtime Telemetry & Self-Measurement (Opt-in)

- [ ] Add an optional `--telemetry` flag that writes a small JSON file next to the output containing:
  - Wall time per pass
  - Peak RSS memory
  - Number of seed hashes attempted vs accepted
  - Lotus bit-cost breakdown (arity vs length vs payload)
- [ ] Make the telemetry format stable and versioned so that future agents can build dashboards or regression detectors on top of it.
- [ ] Research task: decide whether to embed a tiny Prometheus-compatible endpoint (for long-running compression jobs) or keep everything file-based. Decision recorded with rationale.

### 12.18 Security & Robustness Hardening

- [ ] Audit every `unwrap()` / `expect()` in the hot path (`seed.rs`, `header.rs`, `compress.rs`) and replace with proper error propagation or `debug_assert!` where the invariant is proven.
- [ ] Add `zeroize` (or equivalent) for any temporary seed buffers that could contain sensitive material if Telomere is ever used in a cryptographic context.
- [ ] Research task: evaluate constant-time comparison for the final hash verification step inside `prefix_matches` when the hasher is SHA-256 (defense against timing side-channels on the truncated prefix).
- [ ] Add a "strict mode" that refuses to decompress any file whose format version is newer than the current binary (prevents forward-compatibility surprises).

### 12.19 CI/CD Matrix & Cross-Platform Validation

- [ ] Expand GitHub Actions to a 3×2 matrix (Ubuntu, macOS, Windows) × (stable, nightly) with the following jobs:
  - `cargo check --all-features`
  - `cargo test --all-features`
  - `cargo clippy -- -D warnings`
  - Property-test run (limited iterations on macOS/Windows to keep CI time reasonable)
- [ ] Add a "reproducible build" job that builds twice with different source timestamps and verifies the resulting binaries are identical (except for the embedded build timestamp if we choose to embed one).
- [ ] Research task: evaluate `cross` or `cargo-zigbuild` for producing static Linux binaries that run on older glibc versions without Docker.

### 12.20 Agentic Workflow & Self-Improving Repository

- [ ] Add a `scripts/update_checklist.sh` that parses `TASK_CHECKLIST.md`, counts completed vs open items, and updates a badge in `README.md` ("142 / 187 tasks complete").
- [ ] Create a lightweight "agent memory" file (`.agent/last_session.json`) that records the last 5 research tasks completed and their artifact paths so a new agent can resume context instantly.
- [ ] Research task: design a simple "todo extraction" pass that scans all `// TODO(agent):` comments and appends them to `TASK_CHECKLIST.md` automatically (with human review gate).
- [ ] Add a weekly "hygiene cron" (GitHub Action scheduled) that:
  - Runs `cargo udeps`
  - Runs `cargo outdated`
  - Opens a draft PR with the results if anything actionable appears

### 12.21 Long-Term Research Directions (Post-M4)

These are deliberately open-ended; a powerful agent is expected to scope, prioritize, and execute them only after the MVP is stable.

- [ ] **Formal verification of Lotus header properties** — Use a model checker (e.g., `kani` or `crux-mir`) on the Lotus encode/decode pair to prove self-delimiting and prefix-free guarantees.
- [ ] **Learned seed ordering** — Prototype a small neural net that, given a block, predicts the most likely short seed length. Compare against the current deterministic shortest-first order.
- [ ] **Hardware offload feasibility study** — Evaluate whether a small FPGA bitstream for BLAKE3 prefix matching would be worthwhile (rough power/area vs speedup estimate).
- [ ] **Multi-algorithm hybrid** — Measure the marginal gain of running one final traditional entropy pass (zstd -19 or brotli) on the already Lotus-encoded output. Decision: pure generative or hybrid final stage?

All of the above tasks are now part of the official "production state" definition. They should be treated with the same priority as functional milestones once the core negative-delta loop is proven.

---

**The research plan is now substantially complete for the initial planning phase.** Every category of production improvement (hygiene, measurement, deletion, security, CI, agentic workflow, long-term research) has been addressed with concrete, actionable items that a powerful coding/architecture agent can prioritize and execute without further invention from the user.

*Final expansion of RESEARCH_PLAN.md — 2026-05-22*
