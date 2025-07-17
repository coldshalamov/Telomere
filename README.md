# Telomere Compression

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

The `arity` field encodes both compression span and literal passthrough signals:

### Reserved Arity Values for Literal Passthrough

- `29` → one literal block  
- `30` → two literal blocks  
- `31` → three literal blocks  
- `32` → final tail (shorter than full block)

These literal codes are used in place of escape markers or raw bytes:

- The decoder reads the arity.
- If it is `29`–`31`, it copies that number of literal blocks directly.
- If it is `32`, it copies the remaining tail bytes (less than `block_size`).
- Otherwise, it uses `G(seed)` for normal reconstruction.

No additional marker bytes or prefix codes are ever emitted.

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

---

## Status

- ✅ Deterministic compression and literal passthrough format complete
- ✅ Round-trip identity supported
- 🔜 Seed-driven decoding (G-based) in development

## Telomere Protocol Compliance Notes

The compressed output contains only headers and deterministic seed references.
Any literal bytes are wrapped in a `Literal` header and expected to vanish as
multi-pass compression converges. Stopping early may leave such sections in the
stream, which is allowed but suboptimal. No entropy coding is applied at any
stage, adhering to the stateless design described in the whitepaper.
