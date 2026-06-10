"""Toy wire-decode proof for k-XOR (meet-in-the-middle) records, k=2,
including the salted-seed-#1 variant.

Claims proven at toy scale:
1. DECODE: a record [arity codeword][J3D1(s1)][J3D1(s2)] expanding to
   expand(s1) XOR expand(s2) is self-delimiting and stateless; round-trips
   exactly; wire bits == charged bits (two Lotus fields, both charged).
2. SEARCH: the encoder finds (s1, s2) pairs covering a 2H-bit-equivalent
   seed space in 2^H time + 2^H memory (table of s2 expansions, probe with
   s1), not 2^2H — the square-root property, demonstrated concretely.
3. SALT INTERACTION: salting only seed #1 (expand_pos(s1) XOR expand(s2))
   preserves the shared unsalted s2 table across positions while the salted
   side re-rolls with position — the resolution of the MitM/salt conflict.

Run: python mitm_xor_decode_proof.py
"""

from __future__ import annotations

import hashlib
import random

from costs import j3d1_cost_for_seed_index
from bit_literal_decode_proof import j3d1_encode, j3d1_decode

BLOCK_BITS = 16
HALF_DEPTH = 1024  # 2^10 each side -> 2^20 pair space at 2^10 memory
SINGLE = "111"
ARITY1 = "00"


def expand(seed_index: int, nbits: int) -> str:
    digest = hashlib.sha256(b"U" + seed_index.to_bytes(8, "big")).digest()
    return "".join(f"{b:08b}" for b in digest)[:nbits]


def expand_pos(seed_index: int, position: int, nbits: int) -> str:
    digest = hashlib.sha256(
        b"S" + position.to_bytes(8, "big") + seed_index.to_bytes(8, "big")
    ).digest()
    return "".join(f"{b:08b}" for b in digest)[:nbits]


def xor_bits(a: str, b: str) -> str:
    return "".join("1" if x != y else "0" for x, y in zip(a, b))


def build_table(nbits: int) -> dict[str, int]:
    """Shared unsalted s2 table: 2^H entries, built once."""

    table: dict[str, int] = {}
    for s2 in range(HALF_DEPTH):
        prefix = expand(s2, nbits)
        if prefix not in table:
            table[prefix] = s2
    return table


def mitm_search(target: str, position: int, table: dict[str, int], salted: bool):
    """Probe s1 side; lookup the complement in the shared s2 table."""

    probes = 0
    for s1 in range(HALF_DEPTH):
        left = expand_pos(s1, position, len(target)) if salted else expand(s1, len(target))
        probes += 1
        s2 = table.get(xor_bits(target, left))
        if s2 is not None:
            cost = 2 + j3d1_cost_for_seed_index(s1) + j3d1_cost_for_seed_index(s2)
            if cost < 3 + len(target):
                return s1, s2, probes
    return None, None, probes


def encode(blocks: list[str], table: dict[str, int], salted: bool):
    out = []
    records = singles = 0
    total_probes = 0
    pos_out = 0
    for block in blocks:
        s1, s2, probes = mitm_search(block, pos_out, table, salted)
        total_probes += probes
        if s1 is not None:
            out.append(ARITY1 + j3d1_encode(s1) + j3d1_encode(s2))
            records += 1
        else:
            out.append(SINGLE + block)
            singles += 1
        pos_out += BLOCK_BITS
    return "".join(out), records, singles, total_probes


def decode(stream: str, content_bits: int, salted: bool) -> str:
    out = []
    pos_out = 0
    pos = 0
    while pos_out < content_bits:
        if stream[pos : pos + 2] == ARITY1:
            s1, pos = j3d1_decode(stream, pos + 2)
            s2, pos = j3d1_decode(stream, pos)
            left = expand_pos(s1, pos_out, BLOCK_BITS) if salted else expand(s1, BLOCK_BITS)
            piece = xor_bits(left, expand(s2, BLOCK_BITS))
        elif stream[pos : pos + 3] == SINGLE:
            pos += 3
            piece = stream[pos : pos + BLOCK_BITS]
            pos += BLOCK_BITS
        else:
            raise AssertionError(f"unparseable codeword at bit {pos}")
        out.append(piece)
        pos_out += BLOCK_BITS
    assert pos == len(stream), "trailing bits — not self-delimiting"
    return "".join(out)


def main() -> None:
    rng = random.Random(20260610)
    blocks = [format(rng.randrange(1 << BLOCK_BITS), f"0{BLOCK_BITS}b") for _ in range(800)]
    table = build_table(BLOCK_BITS)

    for salted in (False, True):
        stream, records, singles, probes = encode(blocks, table, salted)
        back = decode(stream, len(blocks) * BLOCK_BITS, salted)
        assert back == "".join(blocks), f"round trip failed (salted={salted})"
        # charged == wire re-parse
        pos = 0
        charged = 0
        n = 0
        while n < len(blocks):
            if stream[pos : pos + 2] == ARITY1:
                s1, p2 = j3d1_decode(stream, pos + 2)
                s2, p3 = j3d1_decode(stream, p2)
                charged += 2 + j3d1_cost_for_seed_index(s1) + j3d1_cost_for_seed_index(s2)
                pos = p3
            else:
                charged += 3 + BLOCK_BITS
                pos += 3 + BLOCK_BITS
            n += 1
        assert charged == len(stream), f"charged {charged} != wire {len(stream)}"
        pair_space = HALF_DEPTH * HALF_DEPTH
        print(
            f"OK salted={salted!s:5s}: {records} k=2 records, {singles} singles; "
            f"{len(stream)} wire bits == charged; pair space 2^{pair_space.bit_length()-1} "
            f"searched with {probes} probes + {len(table)} table entries "
            f"(2^{(probes // len(blocks)).bit_length()} per window, not 2^20); "
            f"shared table reused across {'salted positions' if salted else 'windows'}"
        )


if __name__ == "__main__":
    main()
