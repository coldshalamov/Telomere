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


⸻

TELOMERE PROTOCOL (2025, SWE 4-Field Edition)

⸻

Introduction

Telomere is a stateless, lossless, recursively converging compression protocol. No raw bytes are stored: every bit is replaced with an SWE-encoded header containing all regeneration instructions. For each block, we brute-force the shortest SWE-encoded seed (header + payload), using SHA256 to ensure that when decoded, the hash output reconstructs the data.
	•	Formal:
  G(s) = SHA-256(s) = h, where h is a deterministic representation of the original block (or recursively of headers).
	•	No entropy coding, fallback models, or statistical prediction.
All compression emerges from hash-verified regeneration, recursive bundling, and a superposed converging lattice.
	•	Only headers and seeds are kept—never raw data.

⸻

1. 📦 Core Design Elements

Block Partitioning
	•	Input is chunked into fixed-length blocks (typically 40 bits).
	•	Each block is a unit of compression, tracked in a canonical table.
	•	Bundling: Adjacent blocks may be grouped (arity >1), with max arity constrained by the SWE header (see below).
	•	No raw data in output—only SWE headers, arity, and seeds.

⸻

2. ✅ Stacked Block Table Model
	•	Each pass uses a stack of block tables (by size), not a monolithic hash table.
	•	After each pass, compressed/bundled blocks migrate to a new table according to their new effective length.
	•	Superposed blocks (fallbacks/candidates) are given canonical sub-labels (e.g., 168A, 168B).
	•	Hash lookups use prefix-truncated SHA256 (24, 32, 40 bits, etc.) for fast table lookup and low collision risk.

⸻

3. ✅ SWE 4-Field Header Format (2025: Fixed-Window System)
	•	Each header = 4 SWE fields:
	1.	Arity Field:
	•	SWE-encoded:
	•	00 = single block
	•	01 = 2-block
	•	100 = 3-block
	•	101 = 4-block
	•	110 = 5-block
	•	111 = literal passthrough (raw bits)
	2.	SWE Length Field:
	•	SWE-encoded, describes length of the payload (or next field if more deeply recursive in future).
	3.	SWE Payload Field:
	•	SWE-encoded value (the seed, or literal bits if arity=111).
	4.	[Reserved/Future Field or for deep recursion: can be ignored in MVP]
	•	Literal blocks always use arity=111, with a length SWE for the literal tail.
	•	Block headers are self-delimiting, prefix-free, and fully reconstructable by decoder.
	•	All info needed for deterministic decompression is contained within the header chain.

⸻

4. 🔁 Compression & Pass Logic
	•	Telomere is pass-based and converging:
	•	For each pass:
	•	For every block or span:
	•	Brute-force enumerate SWE-encoded seeds (shortest first), hash with SHA256, look for exact match.
	•	If found, replace block with SWE header (arity/length/payload).
	•	If not compressive, retain as superposed fallback (with canonical label: 168A, 168B, …).
	•	Bundling/spans: Try higher arities (grouping) for longer matches/greater gain.
	•	Final tail:
	•	If < block size left, encode as literal block with arity=111.
	•	No codeword boundaries are sacred: Every pass rechunks the bitstream, no external metadata.

⸻

5. ✅ Superposition: Fallback and Candidate Management
	•	All candidate matches per block are tracked, not just the best:
	•	If a replacement is found but not compressive, assign sub-label (168B, …).
	•	Prune longer candidates if delta >8 bits.
	•	If a candidate gets bundled, all non-bundled variants are pruned.
	•	Superposed blocks are always eligible for further compression in future passes.

⸻

6. 📈 Compression Condition
	•	Header bits + Seed bits < Raw span bits = accepted for compression.
	•	If not compressive, candidate is kept as fallback.
	•	All matches and fallbacks are lossless and retrievable for later passes.

⸻

7. 📦 Bundling and Recursion
	•	Bundles:
	•	Try grouping up to max SWE arity (usually ≤5, for encoding compactness).
	•	Bundling increases gain per header and enables recursion in future passes.
	•	All bundled and superposed candidates are pruned by deterministic rules.

⸻

8. 🔒 Determinism and Verifiability
	•	Protocol is fully deterministic, pass-based, and reproducible.
	•	All superpositions, fallbacks, and candidates are explicitly tracked (with labels).
	•	No external metadata required for verification: header/seed stream is sufficient.

⸻

9. 🚀 Implementation Steps (MVP, with SWE 4-Field)

9.1. File Partition
	•	Partition file into fixed 40-bit blocks.

9.2. Per-Pass Compression
	•	For each block/span:
	•	For all superposed candidates:
	•	Brute-force enumerate SWE-encoded seeds (shortest first).
	•	Hash with SHA256, check match.
	•	If compressive, record as main; if not, assign as fallback, label as 168B, 168C, etc.
	•	Apply deterministic pruning (delta>8bits, etc).
	•	Update block tables and migrate bundled blocks to next table.

9.3. Recurse
	•	Repeat above until no further compression.

9.4. Decompression
	•	For each header/seed, reconstruct original (by hashing or reading literal), following all superposition/pruning logic for block chain.

⸻

10. ✅ What’s Different From the SigmaStep Model
	•	No SigmaStep; all headers are encoded using SWE 4-field (arity, len, payload)
	•	No variable U/D walks; all fields are SWE
	•	Seed space toggle: Use 2 bits if you want to signal the starting length for seed search, as per your toggle mechanism.
	•	All other elements (block table stacking, superposition, pruning, bundling, recursion, 100% replacement, etc) are identical.
	•	Literal block marker is just arity=111 in SWE, not special marker.

⸻

11. ✅ Universal Block Replaceability (Seed Space Toggle)
	•	Every block can be replaced by a seed, compressive or not, thanks to:
	•	Optional 2-bit seed space toggle, indicating starting length for seed search (and encoding).
	•	Worst case: block is simply replaced by a canonical seed of equal length; overhead is minimal and bounded.
	•	No block is ever unmatchable.

⸻

12. ✅ Protocol Summary
	•	All compression is structural, superposed, recursive, and pass-driven.
	•	No raw data, fallback coders, or statistical entropy models are used—just brute-force, hash-driven, lattice compression.
	•	Superposition and recursive bundling ensure global convergence.
	•	Every pass is deterministic, and every block can be replaced on every pass.
	•	All information needed for decompression is encoded in SWE headers and canonical block tables—nothing else.

⸻

💡 MVP Implementation Notes for Codex
	•	Encode everything with SWE (arity/len/payload).
	•	Track block tables, superposed candidates, and apply deterministic pruning.
	•	For each block and arity, brute-force SWE seed search, check with SHA256.
	•	No need for SigmaStep logic anywhere; all self-delimiting codes are SWE.
	•	All block/seed structures are bit-for-bit roundtrippable and self-delimiting.

⸻


