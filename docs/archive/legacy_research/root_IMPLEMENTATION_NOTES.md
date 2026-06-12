# Implementation Notes

Current implementation notes are intentionally short so they do not compete
with the canonical docs.

- `.tlmr` v1 uses the variable-length Lotus bit-stream header in `src/tlmr.rs`
  (5-byte raw `TLMR` magic + version prefix followed by a J3D2/J1D1 Lotus
  stream). The legacy 40-byte fixed v1 layout is no longer accepted.
- The writer emits one-layer-decodable payloads only.
- The decoder selects BLAKE3 or SHA-256 from header metadata.
- Config validation lives in `Config::validate`.
- Gloss, bloom, and broken fuzz targets have been removed.
- GPU is research-only and currently shares CPU matching semantics.

See `docs/ARCHITECTURE.md` and `docs/FORMAT.md` for details.
