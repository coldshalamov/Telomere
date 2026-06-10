"""Toy wire-decode proof for the BIT_LITERAL primitive (codec allowance #3).

Proves at toy scale that a bit-aligned record stream — canonical arity
codewords, J3D1 seed indices, and 3-bit marker-only literals with NO byte
pad — is prefix-free, self-delimiting, and exactly round-trips. The byte
pad in v1 literals is a memcpy convenience, not a decodability requirement;
this is the proof.

The J3D1 bit layout here is the proof kernel's reference layout
(jumpstarter 3 bits = tier width; tier field of width tw encodes the payload
width pw in [2^tw-2, 2^(tw+1)-3]; payload field of width pw encodes
seed_index+1 in [2^pw-2, 2^(pw+1)-3]). Its widths match
costs.j3d1_cost_for_seed_index exactly for every index tested. Pin against
the sibling lotus crate before claiming wire compatibility.

Run: python bit_literal_decode_proof.py
"""

from __future__ import annotations

import hashlib
import random

from costs import j3d1_cost_for_seed_index, payload_width_for_seed_index, lotus_width_for_value

BLOCK_BITS = 8
DEPTH = 4096  # toy seed universe
ARITY1 = "00"
LITERAL = "111"


def expand(seed_index: int, nbits: int) -> str:
    digest = hashlib.sha256(seed_index.to_bytes(8, "big")).digest()
    return "".join(f"{byte:08b}" for byte in digest)[:nbits]


def j3d1_encode(seed_index: int) -> str:
    value = seed_index + 1
    pw = payload_width_for_seed_index(seed_index)
    tw = lotus_width_for_value(pw)
    bits = f"{tw:03b}"
    bits += format(pw - ((1 << tw) - 2), f"0{tw}b")
    bits += format(value - ((1 << pw) - 2), f"0{pw}b")
    assert len(bits) == j3d1_cost_for_seed_index(seed_index), "width mismatch vs costs.py"
    return bits


def j3d1_decode(stream: str, pos: int) -> tuple[int, int]:
    tw = int(stream[pos : pos + 3], 2)
    pos += 3
    pw = int(stream[pos : pos + tw], 2) + ((1 << tw) - 2)
    pos += tw
    value = int(stream[pos : pos + pw], 2) + ((1 << pw) - 2)
    pos += pw
    return value - 1, pos


def encode(blocks: list[str]) -> tuple[str, int, int]:
    out = []
    seed_records = literals = 0
    for block in blocks:
        chosen = None
        for seed in range(DEPTH):
            cost = 2 + j3d1_cost_for_seed_index(seed)
            if cost >= 3 + BLOCK_BITS:
                break  # deeper seeds only cost more; literal is cheaper
            if expand(seed, BLOCK_BITS) == block:
                chosen = seed
                break
        if chosen is not None:
            out.append(ARITY1 + j3d1_encode(chosen))
            seed_records += 1
        else:
            out.append(LITERAL + block)  # NO pad: this is the primitive
            literals += 1
    return "".join(out), seed_records, literals


def decode(stream: str, block_count: int) -> list[str]:
    blocks = []
    pos = 0
    for _ in range(block_count):
        if stream[pos : pos + 2] == ARITY1:
            seed, pos = j3d1_decode(stream, pos + 2)
            blocks.append(expand(seed, BLOCK_BITS))
        elif stream[pos : pos + 3] == LITERAL:
            pos += 3
            blocks.append(stream[pos : pos + BLOCK_BITS])
            pos += BLOCK_BITS
        else:
            raise AssertionError(f"unparseable codeword at bit {pos}")
    assert pos == len(stream), "trailing bits — stream not self-delimiting"
    return blocks


def main() -> None:
    rng = random.Random(20260609)
    blocks = [format(rng.randrange(256), "08b") for _ in range(2000)]
    stream, seeds, lits = encode(blocks)
    decoded = decode(stream, len(blocks))
    assert decoded == blocks, "round-trip mismatch"
    expected_bits = seeds * 0 + lits * (3 + BLOCK_BITS)
    # add exact seed record bits
    expected_bits += sum(
        2 + j3d1_cost_for_seed_index(s)
        for b in blocks
        for s in [next((s for s in range(DEPTH)
                        if 2 + j3d1_cost_for_seed_index(s) < 3 + BLOCK_BITS
                        and expand(s, BLOCK_BITS) == b), None)]
        if s is not None
    )
    assert len(stream) == expected_bits, "charged bits != wire bits"
    print(
        f"OK: {len(blocks)} blocks, {seeds} seed records, {lits} bit-literals, "
        f"{len(stream)} wire bits == charged bits, exact round-trip, "
        f"self-delimiting with zero pad"
    )


if __name__ == "__main__":
    main()
