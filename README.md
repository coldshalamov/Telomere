# Inchworm Compression

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
raw bytes with no special markers.

Run `cargo run -- c <input> <output>` to compress a file or `cargo run -- d
<input> <output>` to decompress.

## Seed and Hash Storage

Compression can optionally persist the seeds and SHA-256 hashes used for the
final output. Temporary candidates produced during the search are never written
to disk. When a seed is persisted, the library checks disk and memory
consumption before appending the new entry. If the file would exceed configured
limits or the system is low on memory, the operation aborts with an error.

The default table path is `hash_table.bin` and entries are encoded with
`bincode`.

## Format Notes

All files begin with an EVQL-encoded header describing the original
length and block size. Every subsequent region is preceded by a header
containing a seed index and an arity. The arity values `29`–`32` are
reserved for literal passthrough blocks:

* **29** - one literal block
* **30** - two literal blocks
* **31** - three literal blocks
* **32** - final tail shorter than one block

No additional marker bytes are used. Seed-driven decoding is not yet
implemented.
