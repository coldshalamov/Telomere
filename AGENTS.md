# Telomere — Agent Conventions

## Project overview
Telomere is a stateless lossless generative compression protocol. Each block is replaced
by a shorter seed whose hash expansion (BLAKE3 XOF or SHA-256) reproduces the original bytes.
Lotus 4-field headers encode (arity, seed) pairs in a self-delimiting bit stream.

## Architecture map

| Module | Purpose |
|--------|---------|
| `src/hasher.rs` | `SeedExpander` trait + Blake3/SHA256 implementations |
| `src/seed.rs` | `find_seed_match` — rayon-parallel brute-force seed search |
| `src/seed_index.rs` | Canonical index↔seed bijection (length-ordered, big-endian) |
| `src/header.rs` | Lotus 4-field header: encode/decode (arity 1-5, literal=0xFF) |
| `src/compress.rs` | Single-pass and multi-pass compression pipeline |
| `src/compress_stats.rs` | PassStats / RunSummary for per-pass delta measurement |
| `src/config.rs` | Runtime config: block_size, max_seed_len, hasher, memory_limit |
| `src/tlmr.rs` | 3-byte TlmrHeader (version, block_size, last_block_size, hash13) |
| `src/superposition.rs` | Multi-candidate tracking per block, pruned at pass boundary |
| `src/bundler.rs` | Greedy span bundling (arity 2-5) |
| `src/block.rs` | BlockStore arena + BlockRef metadata |
| `src/main.rs` | `telomere compress`/`decompress` CLI with --json, --seed-depth |
| `src/bin/compressor.rs` | Standalone `compressor` binary |
| `src/bin/decompressor.rs` | Standalone `decompressor` binary |

## Critical constraints

### Never change these without understanding implications
- **Seed enumeration order** — consensus critical: 1-byte seeds first (0..255), then 2-byte, etc.
  Changing this breaks all existing compressed files. Defined in `seed_index.rs`.
- **Lotus arity encoding** — arity 1-5 are valid; arity 2 is NOT reserved; literal marker is 0xFF.
  Defined in `header.rs::encode_lotus_arity_bits`.
- **TlmrHeader format** — 3 bytes, fixed layout (version 3b, block_size 4b, last_block_size 4b, hash 13b).
- **Hash choice** — BLAKE3 and SHA-256 use different seeds for the same block.
  The chosen hasher MUST be recorded in the file header for portability (not yet implemented).

### Performance rules for tests
- **Never use max_seed_len=3 in unit/integration tests** — 16M hash iterations per block ≈ 2s/block.
- Always use `fast_cfg(max_seed_len=1)` in tests for speed (256 seeds/block, microseconds).
- Reserve max_seed_len≥2 for slow/benchmark tests explicitly marked `#[ignore]`.

### Hasher semantics
- `Blake3Expander::expand_into(seed, out)` — BLAKE3 XOF: `hasher.finalize_xof().fill(out)`
- `Sha256Expander::expand_into(seed, out)` — plain SHA256(seed) for ≤32 bytes; counter mode for more
- `prefix_matches(seed, target, bits)` — expand to `(bits+7)/8` bytes, compare prefix
- `SeedExpander: Send + Sync` — required for rayon parallelism in `find_seed_match`

## Current state (2026-05-23)
- M0 + M1 complete: real hasher, 106 tests, rayon parallelism, zero warnings
- M2 in progress: PassStats/RunSummary/--json wired; convergence detection needs K=3 passes
- GPU path: marked #[ignore], unverified — see RESEARCH_PLAN.md section 4.6
- Negative delta: only achievable on structured/repetitive data, NOT random input

## Workflow conventions
- Tests: use `compress_multi_pass_with_config` not `compress()` (which forces max_seed_len=3)
- Test data: generate with `Blake3Expander.expand_into(seed, &mut buf)` so hasher is consistent
- Commits: Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`)
- No hand-written benchmark tables in docs — generate from code
- Dead code (gloss.rs, bloom.rs, swe.rs) tracked for section 7 cleanup — don't delete without plan
