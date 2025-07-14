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

The decompressor recognizes special 8‑bit codes for literal and terminal data:

* **29** – one literal block
* **30** – two literal blocks
* **31** – three literal blocks
* **32** – terminal tail of less than one block

These codes bypass the variable length header parser and are followed
immediately by the indicated bytes. Blocks outside this range continue
using the normal header scheme.
