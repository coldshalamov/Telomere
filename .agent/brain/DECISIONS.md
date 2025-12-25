# Decisions

- **Header Format**: Adopted "Lotus 4-Field" header (`encode_lotus_header`) as the canonical format.
  - Rationale: The codebase contained a newer `header.rs` implementation that mismatched the `compress.rs` logic. I chose to update `compress.rs` to match the new `header.rs` rather than reverting.
  - Consequence: Obsolete tests relying on old header patterns (Sigma/Toggle) were removed.

- **Compression Logic**: Forced acceptance of the first compression pass even if it increases size (overhead).
  - Rationale: The output file MUST be a valid Telomere file (with header). Returning raw bytes is invalid.
  - Consequence: Small files or incompressible data will grow slightly (by header size), but will be valid format.

- **Config**: `main.rs` now explicitly passes the configuration object to the compression function.
  - Rationale: CLI arguments like `--max-seed-len` were being ignored by the wrapper function.
