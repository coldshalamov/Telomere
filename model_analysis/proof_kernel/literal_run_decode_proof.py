"""Toy wire-decode proof for the LITERAL_RUN primitive.

Proves at toy scale that a bit-aligned stream over the entry_singles_run
alphabet — entry arities 1..4, BIT_LITERAL singles (110), LITERAL_RUN (111)
with a charged Lotus length prefix — is prefix-free, self-delimiting, and
exactly round-trips with wire bits == charged bits.

Key property proven: the run is LENGTH-PREFIXED, not terminator-delimited.
The payload deliberately contains every codeword pattern (including 111 and
110) to demonstrate that no in-band marker is needed or consulted; a
terminator form could not decode (raw bits can contain any marker pattern).

Alphabet under test (Kraft-complete: 2*2^-2 + 4*2^-3 = 1):
    00   arity 1      01   arity 2
    100  arity 3      101  arity 4
    110  single literal: [110][block_bits raw]          (BIT_LITERAL)
    111  literal run:    [111][Lotus(bit_len)][payload]  (LITERAL_RUN)

Run: python literal_run_decode_proof.py
"""

from __future__ import annotations

import hashlib
import random

from costs import (
    j3d1_cost_for_seed_index,
    lotus_cost_for_value,
    lotus_width_for_value,
)
from bit_literal_decode_proof import j3d1_encode, j3d1_decode

BLOCK_BITS = 8
DEPTH = 4096
CODE = {1: "00", 2: "01", 3: "100", 4: "101"}
ARITY_BITS = {1: 2, 2: 2, 3: 3, 4: 3}
SINGLE = "110"
RUN = "111"


def expand(seed_index: int, nbits: int) -> str:
    digest = hashlib.sha256(seed_index.to_bytes(8, "big")).digest()
    return "".join(f"{b:08b}" for b in digest)[:nbits]


def lotus_encode_value(value: int) -> str:
    """Reference single-tier Lotus layout for a generic value >= 1."""

    pw = lotus_width_for_value(value)
    tw = lotus_width_for_value(pw)
    assert 1 <= tw <= 8
    return (
        format(tw - 1, "03b")
        + format(pw - ((1 << tw) - 2), f"0{tw}b")
        + format(value - ((1 << pw) - 2), f"0{pw}b")
    )


def lotus_decode_value(stream: str, pos: int) -> tuple[int, int]:
    tw = int(stream[pos : pos + 3], 2) + 1
    pos += 3
    pw = int(stream[pos : pos + tw], 2) + ((1 << tw) - 2)
    pos += tw
    value = int(stream[pos : pos + pw], 2) + ((1 << pw) - 2)
    pos += pw
    return value, pos


def encode(blocks: list[str], run_plan: list[tuple[int, int]]) -> tuple[str, dict]:
    """Encode: runs where planned (start, n_blocks), else seed search / single."""

    out = []
    charged = {"records": 0, "singles": 0, "runs": 0, "bits": 0}
    covered_by_run = {}
    for start, n in run_plan:
        for i in range(start, start + n):
            covered_by_run[i] = (start, n)
    i = 0
    while i < len(blocks):
        if i in covered_by_run and covered_by_run[i][0] == i:
            start, n = covered_by_run[i]
            payload = "".join(blocks[start : start + n])
            header = RUN + lotus_encode_value(len(payload))
            out.append(header + payload)
            charged["runs"] += 1
            charged["bits"] += len(RUN) + lotus_cost_for_value(len(payload)) + len(payload)
            i = start + n
            continue
        block = blocks[i]
        chosen = None
        for seed in range(DEPTH):
            cost = ARITY_BITS[1] + j3d1_cost_for_seed_index(seed)
            if cost >= len(SINGLE) + BLOCK_BITS:
                break
            if expand(seed, BLOCK_BITS) == block:
                chosen = seed
                break
        if chosen is not None:
            out.append(CODE[1] + j3d1_encode(chosen))
            charged["records"] += 1
            charged["bits"] += ARITY_BITS[1] + j3d1_cost_for_seed_index(chosen)
        else:
            out.append(SINGLE + block)
            charged["singles"] += 1
            charged["bits"] += len(SINGLE) + BLOCK_BITS
        i += 1
    return "".join(out), charged


def decode(stream: str, total_payload_bits: int) -> str:
    """Reconstruct the previous layer's bitstream; stop by out-of-band length."""

    out = []
    out_bits = 0
    pos = 0
    while out_bits < total_payload_bits:
        if stream[pos : pos + 2] == "00":
            seed, pos2 = j3d1_decode(stream, pos + 2)
            piece = expand(seed, BLOCK_BITS)
            pos = pos2
        elif stream[pos : pos + 3] == SINGLE:
            pos += 3
            piece = stream[pos : pos + BLOCK_BITS]
            pos += BLOCK_BITS
        elif stream[pos : pos + 3] == RUN:
            length, pos2 = lotus_decode_value(stream, pos + 3)
            pos = pos2
            piece = stream[pos : pos + length]
            pos += length
        else:
            raise AssertionError(f"unparseable codeword at bit {pos}")
        out.append(piece)
        out_bits += len(piece)
    assert pos == len(stream), "trailing bits — stream not self-delimiting"
    assert out_bits == total_payload_bits, "length mismatch"
    return "".join(out)


def main() -> None:
    rng = random.Random(20260610)
    blocks = [format(rng.randrange(256), "08b") for _ in range(3000)]

    # plant adversarial payloads: runs containing every codeword pattern
    blocks[100] = "11111111"
    blocks[101] = "11011100"
    blocks[102] = "00000000"

    run_plan = [(50, 200), (400, 64), (1000, 1024), (2500, 33)]  # 33: odd length
    stream, charged = encode(blocks, run_plan)
    decoded = decode(stream, total_payload_bits=len(blocks) * BLOCK_BITS)
    assert decoded == "".join(blocks), "round-trip mismatch"
    assert len(stream) == charged["bits"], (
        f"charged bits {charged['bits']} != wire bits {len(stream)}"
    )

    # tail case: total bits not a multiple of BLOCK_BITS (partial final block)
    tail_blocks = blocks[:97]
    tail_payload = "".join(tail_blocks)[:-3]  # 5-bit final fragment
    header = RUN + lotus_encode_value(len(tail_payload))
    tail_stream = header + tail_payload
    tail_decoded = decode(tail_stream, total_payload_bits=len(tail_payload))
    assert tail_decoded == tail_payload, "tail round-trip mismatch"

    ratio = len(stream) / (len(blocks) * BLOCK_BITS)
    print(
        f"OK: {len(blocks)} blocks, {charged['records']} seed records, "
        f"{charged['singles']} singles, {charged['runs']} literal runs; "
        f"{len(stream)} wire bits == charged bits; layer/raw = {ratio:.4f}; "
        f"adversarial in-payload codewords decoded; odd-length tail decoded; "
        f"self-delimiting"
    )


if __name__ == "__main__":
    main()
