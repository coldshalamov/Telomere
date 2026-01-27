# Telomere Production Hardening - Implementation Notes

## Completed
1. **Hasher Abstraction & BLAKE3 Migration (Day 1-2)**
   - Created `src/hasher.rs` with `SeedExpander` trait.
   - Implemented `Blake3Expander`, `Sha256Expander`.
   - Updated call sites in `lib.rs`, `compress.rs`, `seed.rs`, `tlmr.rs`, `seed_detect.rs`, `gpu_cpu.rs`.
   - Removed `sha_cache.rs` and `expand_seed` return functions (replaced with `expand_into`).

2. **CLI Hardening (Day 10 - Partial)**
   - Rewrote `src/main.rs` to use `clap` with subcommands `compress`/`decompress`.
   - Added mandated flags: `--seed-depth`, `--passes`, `--checkpoint-every`, `--memory-limit`, `--hasher`.
   - Removed `--status` and `--json`.
   - Integrated `tracing`.

3. **Dependencies**
   - Updated `Cargo.toml` with `blake3`, `tracing`, `tracing-subscriber`.

## Completed

1. **Test Suite Repairs (Day 2)**
   - Fixed `tests/` compilation failures.
   - Restored `SeedExpander` functionality.

2. **BlockStore Refactor (Day 3-4)**
   - Replaced `BlockTable` / `HashMap<usize, Vec<Block>>` with cache-friendly `BlockStore`.
   - `BlockStore` uses contiguous `Vec<u8>` arena and `BlockRef` indices.
   - Updated `src/block.rs`, `src/tile.rs`, `src/gpu_cpu.rs`, and tests.

3. **Resource Governor (Day 3-4)**
   - Added `memory_limit` to `Config`.
   - Wired logic in `src/main.rs` to parse memory limit (%, GB, MB).
   - Enforced memory limit in `compress_multi_pass` loop.

## Pending
1. **Functionality Stubs**:
   - `Checkpoints` are parsed in CLI but not implemented in logic.
   - `Resume` is a no-op.

## Next Steps
1. Fix test suite compilation (replace `expand_seed` usage).
2. Implement `BlockStore` arena allocation.
3. Wire up `ResourceGovernor`.
