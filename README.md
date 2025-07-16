# Telomere Compression

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three-byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
literal passthroughs, using reserved header codes—never as raw bytes.

Run `cargo run -- c <input> <output>` to compress a file or `cargo run -- d
<input> <output>` to decompress.

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

---

## Status

- ✅ Deterministic compression and literal passthrough format complete
- ✅ Round-trip identity supported
- 🔜 Seed-driven decoding (G-based) in development
