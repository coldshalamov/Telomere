# Inchworm Compression

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
literals using a reserved fallback byte.

Run `cargo run -- c <input> <output>` to compress a file or `cargo run -- d
<input> <output>` to decompress.

## Arity Codes

The decompressor recognizes several reserved 8‑bit codes:

* **29** – reserved for one literal block (not currently emitted)
* **30** – reserved for two literal blocks (not currently emitted)
* **31** – reserved for three literal blocks (not currently emitted)
* **32** – terminal tail of less than one block

Only code `32` is produced by the encoder. It marks the final partial
block and is immediately followed by the remaining bytes. All other data
use standard headers.
