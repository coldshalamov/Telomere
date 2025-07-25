# Telomere Compression

![Coverage](https://github.com/OWNER/Inchworm/actions/workflows/coverage.yml/badge.svg?branch=main)

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three-byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
literal passthroughs, using reserved header codes—never as raw bytes.

Telomere exposes a simple command line interface built on top of these
primitives. Compression and decompression are invoked via subcommands –
`compress` (alias `c`) and `decompress` (alias `d`). Input and output paths may
be provided positionally or with the `--input`/`--output` flags. Additional
flags tweak runtime behaviour:

```text
USAGE:
    telomere compress [OPTIONS] [INPUT] [OUTPUT]
    telomere decompress [OPTIONS] [INPUT] [OUTPUT]

FLAGS:
    --block-size N   size of each compression block (default 3)
    --passes N       maximum compression passes (default 10)
    --status         print a short progress line for every block
    --json           emit a JSON summary after completion
    --dry-run        perform compression but skip writing the output file
```

## Usage Example

The following demonstrates a typical round‑trip using default settings:

```bash
# Compress a file
cargo run --release -- compress -i input.bin -o output.tlmr --block-size 4 --status

# Decompress back to the original bytes
cargo run --release -- decompress output.tlmr restored.bin
```

The `compress` and `decompress` subcommands are also available through the
top‑level `telomere` binary:

```bash
target/debug/telomere compress input.bin output.tlmr --block-size 3
target/debug/telomere decompress output.tlmr restored.bin
```

If an output path already exists, pass `--force` to overwrite it.  Use the
`--status` flag to print progress for each processed block, and `--json` to emit
a short summary after completion.

---

## Seed and Hash Storage

Compression can optionally persist the seeds and SHA‑256 hashes used for the
final output. Temporary candidates produced during the search are never written
to disk. When a seed is persisted, the library checks disk and memory
consumption before appending the new entry. If the file would exceed configured
limits or the system is low on memory, the operation aborts with an error.

The default table path is `hash_table.bin` and entries are stored as fixed
8-byte records. Precomputing 1-, 2-, and 3-byte seeds produces roughly 16.8
million entries (~135 MB).

---

## Format Notes

All files begin with an EVQL-encoded file header describing:

- The original input length
- The fixed block size

Every block after that is preceded by a standard compressed block header:

- **Seed index**
- **Arity**

The `seed index` is the ordinal position of a seed in the protocol's
deterministic enumeration. Seeds are ordered first by byte length
(`1..=max_seed_len`) and then lexicographically in big‑endian order.
Both encoder and decoder must implement the same mapping from index to
seed bytes for all time. Changing the enumeration would break backward
compatibility.

The `arity` field is encoded with a hybrid toggle + VQL scheme that is prefix
safe and keeps small spans compact.

### Arity Header Format

The header begins with a **1‑bit toggle**:

```
0 → arity = 1 (single literal block)
1 → arity continues in 2‑bit windows
```

When the first bit is `1`, the decoder reads successive 2‑bit windows.  Each
window follows VQL rules—`00`, `01`, and `10` carry payload values while `11`
signals continuation—except that the **first payload `00` is reserved**.  This
reserved pattern (`1 00`) encodes a literal block and terminates the header.
The numeric arity value `2` is therefore invalid and is never emitted.

The resulting codes are:

```
0           → arity = 1
1 00        → literal marker
1 01        → reserved
1 10        → arity = 3
1 11 00     → arity = 4
1 11 01     → arity = 5
1 11 10     → arity = 6
1 11 11 00  → arity = 7
...         → and so on
```

Each additional window contributes three more arity values.  Single block
literals therefore use `0`, while any multi‑block literal uses the reserved
`1 00` code.  No extra marker bytes or escape sequences are required.

### `.tlmr` File Layout

Telomere files are organized into small batches of up to three blocks.  Each
batch starts with a fixed three‑byte header followed by one or more standard
block headers and the associated data.  Conceptually this looks as follows:

```text
┌──────────────┬───────────────────────────────────┐
│ 3‑byte batch │ block header → block data → ...   │
│ header       │                                   │
└──────────────┴───────────────────────────────────┘
```

The outer file header (encoded with EVQL) still records the original length and
block size.  Batches merely group subsequent blocks together for streaming
purposes.

### Batch Header Format

The batch header packs a small amount of metadata into three bytes:

- **Bits 0‑3** – format version (currently `0`)
- **Bits 4‑7** – number of block headers that follow (1‑3)
- **Bits 8‑23** – truncated SHA‑256 of the batch output for quick sanity checks

Decoders verify the hash after reconstructing a batch to detect corruption.

---

## Telomere Protocol Compliance Notes

Telomere maintains a **stateless** design aside from the optional seed table.
The format never emits **raw data** directly; literal regions use reserved arity
codes as a **literal fallback** path. Every file header records the format
**version** and fixed **block size**. There is no entropy or statistical coding
involved—compression relies purely on search. The **literal header logic** is
intentionally simple, and recursive batching ensures eventual **convergence** of
nested segments as a recursive convergence goal.

### Protocol Invariants

- Headers always include a version and block size field.
- Decoders reject any raw payload that is not referenced by a header.
- Literal paths never exceed the configured block size.
- The truncated hash in each batch header must match the expanded output.
- Candidate pruning occurs after each pass and never during the insertion
  phase. Bundles are selected greedily without recursion within a pass and
  conflicting spans are dropped. Headers always alternate `arity` and `EVQL`
  bits and must self-terminate with a zero bit.

### Frequently Asked Questions

**Q: The decompressor reports `output hash mismatch`. What does this mean?**

A: The input file is likely corrupted or was produced with incompatible
parameters. Verify the block size and recompress the original data.

**Q: Why is compression so slow on large files?**

A: Telomere relies on exhaustive seed searches. Increase `--max-seed-len` only
when necessary and use the `--status` flag to monitor progress.

### Troubleshooting and Error Reference

Errors are grouped by subsystem. `Header` errors indicate malformed file
structures or invalid EVQL sequences. `SeedSearch` covers failures during seed
lookups and hash table access. `Bundling` errors originate in bundle selection
logic while `Superposition` errors surface when too many overlapping candidates
compete for the same block. Any I/O failure will surface as an `Io` error and
unexpected internal bugs are reported as `Internal`.

Most decoder issues stem from corrupted input. Verify the reported error type
and re-run the compressor to regenerate a fresh file if in doubt.

---

## Status

- ✅ Deterministic compression and literal passthrough format complete
- ✅ Round-trip identity supported
- 🔜 Seed-driven decoding (G-based) in development

## GPU Accelerated Matching and Block Tiling

The experimental hybrid pipeline splits the global block table into fixed-size
tiles that can be loaded into RAM or VRAM on demand. Each tile records the
global index of its first block so match logs can always refer to stable global
indices. When the GPU begins a pass it hashes seeds over the currently loaded
tile and reports only the compact match log back to the CPU. The CPU processes
shorter seeds in parallel and merges the results when both complete.  All block
tables are kept in sync after every pass so the next round starts from an
identical state.

### GPU feature flag

An experimental OpenCL backend accelerates seed matching on AMD hardware.
Enable it at compile time with:

```bash
cargo build --release --features gpu
```

The implementation targets OpenCL&nbsp;1.2 and works with both the standard
AMD driver and the ROCm stack. If no compatible device is detected at runtime
the compressor prints a single warning and transparently falls back to the CPU
matcher.
