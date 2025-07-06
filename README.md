# Inchworm Compression

Demonstration of the generative compression scheme described in the project
documentation. The encoder brute‑forces short seeds whose SHA‑256 output
reconstructs one or more adjacent blocks. Matches replace those blocks with the
seed and a three byte header. Compressed regions may themselves contain nested
compressed units, enabling recursive compaction. Unmatched blocks are emitted as
literals using a reserved fallback byte.

Run `cargo run -- c <input> <output>` to compress a file or `cargo run -- d
<input> <output>` to decompress.
