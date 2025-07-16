# Inchworm Compression

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three-byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
literal passthroughs, using reserved header codes—never as raw bytes.

Telomere exposes a simple command line interface built on top of these
primitives.  The binary is invoked with a mode (`c` for compress or `d` for
decompress) followed by input and output file paths.  Additional flags tweak
runtime behaviour:

```
USAGE: telomere [c|d] <input> <output> [--block-size N] [--status] [--json] [--dry-run]

FLAGS:
    --block-size N   size of each compression block (default 3)
    --status         print a short progress line for every block
    --json           emit a JSON summary after completion
    --dry-run        perform compression but skip writing the output file
```

### Usage Example

The following demonstrates a typical round‑trip using default settings:

```
# Compress a file
cargo run --release -- c input.bin output.tlmr --block-size 4 --status

# Decompress back to the original bytes
cargo run --release -- d output.tlmr restored.bin
```

---

## Seed and Hash Storage

Compression can optionally persist the seeds and SHA‑256 hashes used for the
final output. Temporary candidates produced during the search are never written
to disk. When a seed is persisted, the library checks disk and memory
consumption before appending the new entry. If the file would exceed configured
limits or the system is low on memory, the operation aborts with an error.

The default table path is `hash_table.bin` and entries are encoded with
`bincode`.

---

## Format Notes

All files begin with an EVQL-encoded file header describing:

- The original input length
- The fixed block size

Every block after that is preceded by a standard compressed block header:
- **Seed index**
- **Arity**

The `arity` field encodes both compression span and literal passthrough signals:

### Reserved Arity Values for Literal Passthrough:

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

```
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

## Status

- ✅ Deterministic compression and literal passthrough format complete
- ✅ Round-trip identity supported
- 🔜 Seed-driven decoding (G-based) in development
