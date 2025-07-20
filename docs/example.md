# Telomere Worked Example

This example walks through a tiny round‑trip using literal blocks only. It does
not rely on seed based compression so the numbers are easy to verify by hand.

## Input

```
00 01 02 03 04 05 06 07 08
```

We use a block size of `3` which splits the input into three blocks:

| Block | Global Index | Bytes       |
|------:|-------------:|-------------|
| 0     | 0‒2          | `00 01 02` |
| 1     | 3‒5          | `03 04 05` |
| 2     | 6‒8          | `06 07 08` |

## File Header

The file header stores the block size, final block length and a truncated
13‑bit SHA‑256 of the decompressed output. For this input the truncated hash is
`0x549`, producing the following three byte header:

```
04 45 49
```

## Block Headers

Every block is encoded with the three‑bit literal marker `100`. Packing the bits
for all three blocks yields the two header bytes `92 00`.

## Final Stream

Putting the pieces together results in the following `.tlmr` file:

```
04 45 49 92 00 00 01 02 03 04 05 06 07 08
```

## Decompression Steps

1. Read the 3‑byte file header: version = 0, block size = 3, last block size = 3
   and output hash = `0x549`.
2. Decode the block headers `92 00` into three literal markers.
3. Copy the next three bytes for each block to the output buffer.
4. Verify the truncated SHA‑256 hash matches and emit the nine bytes above.

The output exactly matches the original input bytes.


