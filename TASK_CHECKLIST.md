# Telomere — Exhaustive Implementation Checklist (MVP to Production)

**Purpose**: This is the master task list. Every item is actionable, measurable, and traceable. Items are grouped by workstream. Check items off as completed. Add new items as discovered.

**Legend**:
- [ ] = Not started
- [x] = Done
- [!] = Blocked / needs decision
- [~] = In progress

**Current Date**: 2026-05-22  
**Target**: Full MVP (M4) with negative-delta proof + production readiness

---

## 0. Foundational Stabilization (M0)

### 0.1 Compilation & Build Health
- [ ] `cargo check` passes with zero errors (currently clean after stub)
- [ ] `cargo clippy -- -D warnings` passes with zero warnings
- [ ] `cargo fmt -- --check` passes
- [ ] All binaries in `src/bin/` compile (`seed_table`, `compressor`, `decompressor`, `hash_precompute`, etc.)
- [ ] GPU feature (`--features gpu`) compiles cleanly when OCL available
- [ ] No `unsafe` code outside `gpu` feature gate (enforce with `#![deny(unsafe_code)]`)
- [ ] `cargo deny check` passes (license, duplicate deps, vulnerabilities)
- [ ] `cargo test --no-run` succeeds for all test binaries

### 0.2 Hasher Abstraction (Critical Path)
- [ ] Replace stub `src/hasher.rs` with real implementation
- [ ] Implement `Blake3Expander` with real `expand_into` + `digest` + `prefix_matches`
- [ ] Implement `Sha256Expander` with real methods (software fallback)
- [ ] Implement `Sha256NiExpander` (x86 SHA-NI when available via `sha2` or `blake3`)
- [ ] Add `HasherKind` enum + `Config::get_expander()` factory
- [ ] Wire real expander into `compress.rs`, `seed_detect.rs`, `gpu_cpu.rs`, `tlmr.rs`
- [ ] Add unit tests for `expand_into` roundtrip (seed → hash → verify)
- [ ] Add constant-time comparison where possible for security
- [ ] Benchmark `expand_into` vs direct `blake3::hash` for 1–32 byte seeds

### 0.3 Lotus Canonicalization & (J, d) Decision
- [ ] Add `lotus` crate as dependency (or decide on vendored fork)
- [ ] Audit current `src/header.rs` Lotus 4-field vs canonical `(J, d)` model
- [ ] Create `docs/LOTUS_TUNING.md` with generated data
- [ ] Run matrix: `J ∈ {1,2,3}`, `d ∈ {1,2,3}` on Telomere value distributions (arity 1–6, len 0–255, payload 1–32 bytes)
- [ ] Measure average bits-per-value + worst-case overhead for each preset
- [ ] Justify final `(J, d)` choice with evidence (default to `LOTUS_J2D1` or better)
- [ ] Replace/augment `encode_lotus_*` / `decode_lotus_*` to use canonical Lotus
- [ ] Add `LOTUS_J2D1`, `LOTUS_J1D2`, `LOTUS_J3D1` re-exports or wrappers
- [ ] Update all call sites in `compress.rs` and `header.rs` tests
- [ ] Verify header self-delimiting + prefix-free property with new Lotus
- [ ] Add property test: encode → decode → original value for 10,000 random arities/lengths

### 0.4 Documentation & Planning Artifacts
- [ ] `RESEARCH_PLAN.md` committed and kept up to date (this file)
- [ ] `AGENTS.md` created with scoped conventions for future agents
- [ ] `docs/WHITEPAPER.md` updated with current Lotus 4-field + measured results
- [ ] `docs/BENCHMARKS.md` created (methodology only, no hand-written tables)
- [ ] `docs/RESULTS.md` + `docs/results.json` generated from code
- [ ] `scripts/reproduce_lotus_tuning.sh` committed
- [ ] `scripts/reproduce_delta_curves.sh` committed
- [ ] Update `README.md` with reproducible "hello world" + measured delta example
- [ ] Remove all stale references to `gloss`, `SigmaStep`, old header formats from comments

---

## 1. Generative Core (M1)

### 1.1 Seed Search & Matching
- [ ] Implement `find_seed_match` in `src/seed.rs` (real brute-force + hash loop)
- [ ] Deterministic seed enumeration: index → seed bytes (big-endian, length-ordered, 1..=max_seed_len)
- [ ] `index_to_seed` + `seed_to_index` bijection with roundtrip tests
- [ ] Support for truncated hash tables (24/32/40-bit prefixes)
- [ ] Prefix match optimization using `expander.prefix_matches`
- [ ] Early exit on first compressive match (header+seed < block span)
- [ ] Add `max_seed_len` config propagation to search
- [ ] Parallelize seed search with rayon (per-block or per-arity)
- [ ] Add seed search statistics (candidates tried, time per block, hit rate)
- [ ] Property test: for any block, if a seed matches, decode produces identical bytes

### 1.2 Bundling & Arity Handling
- [ ] Implement `bundle_one_layer` with arity 1–6 (skip 2 per current literal marker rule)
- [ ] Greedy span selection: longest compressive match first
- [ ] Bundle header emission via Lotus arity field
- [ ] Conflict resolution when overlapping bundles compete
- [ ] Update `bundle_select.rs` with deterministic tie-breaking
- [ ] Test: arity=1 (single), arity=3–6 (multi-block) roundtrips
- [ ] Test: literal marker (reserved arity code) never emits raw bytes

### 1.3 Superposition & Candidate Management
- [ ] Implement `SuperpositionManager` with sub-labeling (A, B, C…)
- [ ] Pruning rule: drop candidates where delta > 8 bits
- [ ] Pruning rule: drop non-bundled variants when a bundle wins
- [ ] Canonical label assignment for fallbacks
- [ ] Superposed blocks remain eligible for future passes
- [ ] Add visualization hook for candidate distribution per block
- [ ] Property test: after pruning, at least one candidate always remains per block

### 1.4 BlockStore & Memory Model
- [ ] Harden `BlockStore` arena allocation (contiguous `Vec<u8>`)
- [ ] `BlockRef` index safety (no dangling references after migration)
- [ ] Implement `split_into_blocks` with last-block handling
- [ ] Add `print_table_summary` for debugging
- [ ] Memory limit enforcement inside `compress_multi_pass`
- [ ] Add `BlockStatus::Compressed | Superposed | Literal` tracking
- [ ] Test: 100 MiB file does not exceed configured memory limit

### 1.5 Single-Pass Compression Loop
- [ ] Wire `compress_with_config` to use real seed search + Lotus headers
- [ ] Literal passthrough path (reserved Lotus code + raw block bytes)
- [ ] Output hash (truncated) written to TlmrHeader
- [ ] Batch header (3-byte) with SHA-256 sanity check
- [ ] End-to-end roundtrip on 1 KiB random data
- [ ] End-to-end roundtrip on 1 KiB repetitive data
- [ ] End-to-end roundtrip on 1 KiB structured data (JSON, binary, text)
- [ ] Delta logging: bytes_in, bytes_out, delta %, cumulative

---

## 2. Multi-Pass Convergence (M2)

### 2.1 Multi-Pass Engine
- [ ] Implement `compress_multi_pass` with table migration
- [ ] After each pass, migrate compressed/bundled blocks to new table by new size
- [ ] Recursive header compression (headers from pass N become data for pass N+1)
- [ ] Convergence detection: stop when delta ≥ 0 for K consecutive passes
- [ ] Configurable `--passes` (default 149, but early exit on convergence)
- [ ] Checkpoint every N minutes (resume from last good pass)
- [ ] Resume logic: load checkpoint, continue from that pass number

### 2.2 Delta Measurement & Instrumentation
- [ ] Per-pass `CompressionStats` struct (original, header+seed, delta, time)
- [ ] Cumulative delta tracking across all passes
- [ ] Export stats to JSON (`--json`)
- [ ] Generate `docs/RESULTS.md` + `docs/results.json` from real runs
- [ ] Add `scripts/size_check.sh` and `scripts/perf_check.sh` to CI
- [ ] Plot delta curve (bytes vs pass) for at least 3 input classes
- [ ] Prove negative average delta on ≥1 input family (random / repetitive / structured)

### 2.3 Recursive Header Compression
- [ ] Verify that Lotus headers themselves can be re-compressed in later passes
- [ ] Measure header compression gain separately from data gain
- [ ] Test deep recursion (5+ nesting levels) without stack overflow
- [ ] Add max-recursion-depth guard

---

## 3. Production Hardening (M3)

### 3.1 Error Handling & Safety
- [ ] All `TelomereError` variants have clear messages and recovery guidance
- [ ] Header corruption detection (batch hash mismatch, Lotus decode errors)
- [ ] Output hash mismatch on decompress → clear error + suggestion to re-compress
- [ ] I/O errors wrapped with context (path, offset, operation)
- [ ] Memory limit exceeded → graceful abort with current progress saved
- [ ] Add `decoder_safety.rs` tests for malformed input
- [ ] Fuzz header decoder with `cargo fuzz` (existing fuzz/ directory)

### 3.2 Resource Governor
- [ ] Parse `--memory-limit` ("80%", "4GB", "512MB")
- [ ] Enforce limit inside `compress_multi_pass` loop
- [ ] Add `sysinfo` memory pressure detection (already in deps)
- [ ] Throttle seed search when memory > 90% of limit
- [ ] Test: 10 GiB file on 4 GiB RAM machine does not OOM

### 3.3 GPU / Hybrid Path Decision
- [ ] Option A: Fully verify OpenCL path (determinism, tile loading, match log merge)
- [ ] Option B: Deprecate GPU feature with rationale in `RESEARCH_PLAN.md`
- [ ] If kept: add `gpu_determinism.rs` test that CPU and GPU produce identical match logs
- [ ] If kept: document ROCm + AMD driver requirements
- [ ] Remove all dead GPU code if Option B chosen

### 3.4 Determinism & Reproducibility
- [ ] Same input + config → bit-identical output on same machine
- [ ] Same input + config → bit-identical output across machines (CI + dev)
- [ ] Seed enumeration order is consensus-critical and frozen
- [ ] Add `compress_determinism.rs` test (run 5 times, compare outputs)
- [ ] Add `compress_roundtrip_random.rs` with 1000 random seeds

### 3.5 Large File & Scale Testing
- [ ] 100 MiB random file roundtrip in < 10 min on reference hardware
- [ ] 1 GiB file processes without OOM under 8 GiB RAM limit
- [ ] Add `large_file_perf.rs` benchmark
- [ ] Profile with `perf` / `samply` to find I/O vs compute hotspots
- [ ] Document "expected time per GiB" in README

---

## 4. CLI, Observability & UX (M4)

### 4.1 CLI Completeness
- [ ] All documented flags work (`--seed-depth`, `--passes`, `--hasher`, `--memory-limit`, `--verify`, `--resume`)
- [ ] `--status` (per-block progress) implemented or removed from docs
- [ ] `--json` summary includes: passes, final size, delta curve, time, hasher
- [ ] `--dry-run` performs all work except final write
- [ ] `--force` overwrites existing output
- [ ] Subcommand aliases (`c`, `d`) documented
- [ ] Help text accurate and complete
- [ ] Version string includes git commit + Lotus version

### 4.2 Progress & Diagnostics
- [ ] Indicatif progress bars for passes and blocks
- [ ] Per-block status line when `--status` given
- [ ] Warning when GPU requested but unavailable (fallback to CPU)
- [ ] Seed table size warning when `--seed-depth` high
- [ ] Add `tracing` spans for major phases (seed search, bundling, migration)

### 4.3 Seed Table & Precomputation
- [ ] `hash_precompute` binary generates 1/2/3-byte seed tables
- [ ] `seed_table` binary loads/saves `hash_table.bin`
- [ ] Table format documented (fixed 8-byte records)
- [ ] ~16.8 M entries (~135 MB) for 3-byte seeds confirmed
- [ ] Disk/memory limit check before appending new entries
- [ ] Optional: live hashing vs table lookup toggle

### 4.4 Optional TUI / Visualization (Stretch)
- [ ] TUI showing live delta curve (using `ratatui` or `cursive`)
- [ ] Block table heatmap (compressed vs literal density)
- [ ] Superposition candidate distribution pie chart
- [ ] Web dashboard (optional, using `axum` + `askama`)

---

## 5. Testing — Exhaustive Suite

### 5.1 Property-Based Tests
- [ ] `roundtrip.rs` — 10,000 random inputs, all sizes, all configs
- [ ] `property_matrix.rs` — cross product of block_size × max_seed_len × passes
- [ ] `property_launch.rs` — launch many quickcheck tests in parallel
- [ ] `adversarial_prop.rs` — adversarial inputs (all zeros, all 0xFF, repeating patterns)
- [ ] Header self-delimiting property test (decode after random prefix)
- [ ] Lotus (J, d) encode/decode roundtrip for edge values (0, 1, 127, 128, 253, 254, 509, 510)

### 5.2 Integration & Roundtrip
- [ ] `full_roundtrip_audit.rs` — end-to-end on 10 different file types
- [ ] `compress_multi_pass.rs` — 50-pass convergence test
- [ ] `decompress_validation.rs` — corrupted input rejection
- [ ] `decoder_safety.rs` — malformed Lotus sequences, truncated files
- [ ] `compress_bounds.rs` — max file size, max passes, max seed len

### 5.3 Fuzzing
- [ ] `cli_output_fuzz.py` extended to 10,000 iterations
- [ ] `cargo fuzz` on header decoder (existing `fuzz/` crate)
- [ ] Fuzz Lotus arity/length fields
- [ ] Fuzz seed index ↔ seed mapping

### 5.4 Performance & Scale
- [ ] `large_file_perf.rs` — 100 MiB timing
- [ ] `gpu_tiling.rs` / `gpu_determinism.rs` (if GPU kept)
- [ ] Criterion benchmarks for seed search, Lotus encode, hash expansion
- [ ] Memory usage test under tight limits

### 5.5 CI / Automation
- [ ] GitHub Actions: test (all features), clippy, fmt, deny, fuzz (limited)
- [ ] GitHub Actions: property tests (quickcheck + proptest)
- [ ] GitHub Actions: reproducible build check (`cargo build --release` twice, diff)
- [ ] `scripts/check_generated.sh` ensures no hand-written benchmark tables

---

## 6. Documentation & Release

### 6.1 User Documentation
- [ ] `README.md` — user guide with 3 reproducible examples + measured delta
- [ ] `RELEASE.md` — changelog, migration notes, known issues
- [ ] `docs/API.md` — public API surface (minimal)
- [ ] Man page or `--help` rendered to `docs/CLI.md`
- [ ] Tutorial: "How to prove negative delta on your own data"

### 6.2 Research Documentation
- [ ] `RESEARCH_PLAN.md` updated after every milestone
- [ ] `docs/LOTUS_TUNING.md` with generated tables
- [ ] `docs/WHITEPAPER.md` (Kolyma spec) updated with Lotus 4-field + results
- [ ] `docs/BENCHMARKS.md` — methodology
- [ ] `docs/RESULTS.md` + `docs/results.json` committed
- [ ] `CITATION.bib` added for academic use

### 6.3 Release Artifacts
- [ ] `cargo install --path .` produces working binary
- [ ] GitHub Release with binary for Linux x86_64 + Windows
- [ ] crates.io publish (optional, after stabilization)
- [ ] Docker image (optional)

---

## 7. Stale / Dead Code Cleanup

- [ ] Remove or fully implement `gloss.rs` + `gloss_prune_hook.rs` (currently TODO stubs)
- [ ] Remove or implement `bloom.rs` (currently placeholder)
- [ ] Decide fate of `swe.rs` (old SWE 4-field?) vs Lotus
- [ ] Clean `src/bin/` — many binaries are stubs or broken (`gloss_tool`, `gloss_dump`, etc.)
- [ ] Remove dead `sigma_step`, old header format comments everywhere
- [ ] Audit `src/types.rs`, `src/path.rs`, `src/live_window.rs`, `src/stats.rs` for usage
- [ ] Delete unused `repetitive.txt` or promote to test fixture
- [ ] Clean `error.log` from repo (add to `.gitignore` if not already)

---

## 8. Performance & Optimization (Post-MVP)

- [ ] Profile seed search hot loop (where is time spent?)
- [ ] SIMD for hash prefix matching (AVX2 / NEON)
- [ ] Memory-mapped I/O for large files (`memmap2` already in deps)
- [ ] Optional seed table on disk with LRU cache
- [ ] rayon work-stealing tuning for multi-core
- [ ] GPU path (if kept) — kernel optimization, coalesced memory access
- [ ] Add `criterion` HTML reports to CI artifacts

---

## 9. Security & Correctness

- [ ] Constant-time hash comparison for security-sensitive paths
- [ ] No secret-dependent branches in seed search (if used for crypto)
- [ ] Document collision probability for 24/32-bit truncated hashes
- [ ] Add `deny.toml` rules for known-vulnerable crate versions
- [ ] `cargo audit` in CI
- [ ] FIPS 140-3 consideration for SHA-256 path (optional)

---

## 10. Future Research Questions (Post-MVP)

- [ ] Live hashing vs precomputed tables — I/O vs CPU trade-off measurement
- [ ] Variable block size (entropy-guided) vs fixed
- [ ] Learned seed ordering (ML) vs deterministic lexicographic
- [ ] Combine with traditional entropy coding as final stage
- [ ] Negative delta on truly random data — theoretical bound
- [ ] Hardware acceleration (FPGA / ASIC) for seed search

---

**End of Checklist**

This list currently contains **~140 actionable items**. It will grow as we discover new issues during implementation. Every item above is designed to be checkable by a human or future agent.

**Next immediate actions (this week)**:
1. Lotus crate integration + tuning matrix
2. Real hasher implementation
3. Minimal working `find_seed_match`
4. First delta measurement on a 4 KiB file

Update this checklist after every completed item and every new discovery.
