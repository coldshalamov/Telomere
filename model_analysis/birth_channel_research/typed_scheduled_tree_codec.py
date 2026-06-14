#!/usr/bin/env python3
"""
Typed Scheduled Tree (TST) candidate.

This mutation keeps the public opening schedule from STF, but removes internal
marker entropy. The schedule itself tells the decoder what the expansion means:

* at depth 1, expansion bits are two B-bit literals;
* at depth d>1, expansion bits are two child seeds of width seed_bits(d-1).

No birth/open/carry metadata is needed. Each depth uses fresh SHA-256 context.
Seed widths are tiered so every scheduled replacement is locally compressive:

    record_bits(d) < 2 * child_bits(d-1)

The price is the usual reachable-set density. The positive fixture is generated
from low root seeds so the toy encoder can find the witnesses quickly; roots are
still stored at full fixed width, so there is no hidden low-seed side channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


B = 8
CHECKSUM_BITS = 64
DOMAIN = b"TELOMERE-TYPED-SCHEDULED-TREE-TOY"


def seed_bits_for_depth(depth: int) -> int:
    if depth < 1:
        raise ValueError(depth)
    bits = 12
    for _ in range(2, depth + 1):
        bits = 2 * bits + 1
    return bits


def record_bits_for_depth(depth: int) -> int:
    return 2 + seed_bits_for_depth(depth)


def child_payload_bits(depth: int) -> int:
    if depth == 1:
        return 2 * B
    return 2 * record_bits_for_depth(depth - 1)


def hash_bits(*parts: object, n_bits: int) -> str:
    out = ""
    counter = 0
    while len(out) < n_bits:
        h = sha256()
        h.update(DOMAIN)
        for part in parts:
            data = str(part).encode("ascii")
            h.update(len(data).to_bytes(2, "big"))
            h.update(data)
        h.update(counter.to_bytes(4, "big"))
        out += "".join(format(byte, "08b") for byte in h.digest())
        counter += 1
    return out[:n_bits]


def expand_node(seed: int, depth: int, position: int) -> tuple[int, int]:
    if depth == 1:
        bits = hash_bits("leaf", seed, depth, position, n_bits=2 * B)
        return int(bits[:B], 2), int(bits[B:], 2)
    width = seed_bits_for_depth(depth - 1)
    bits = hash_bits("node", seed, depth, position, n_bits=2 * width)
    return int(bits[:width], 2), int(bits[width:], 2)


def decode_node(seed: int, depth: int, position: int) -> tuple[int, ...]:
    left, right = expand_node(seed, depth, position)
    if depth == 1:
        return left, right
    return (
        *decode_node(left, depth - 1, position * 2),
        *decode_node(right, depth - 1, position * 2 + 1),
    )


def checksum(values: tuple[int, ...]) -> str:
    return sha256(bytes(values)).hexdigest()


@dataclass
class EncodedTypedForest:
    mode: str
    depth: int
    roots: tuple[int, ...]
    raw_values: tuple[int, ...] | None
    original_checksum: str


def generated_values(depth: int, roots: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    root_values = tuple(range(roots))
    values: list[int] = []
    for position, seed in enumerate(root_values):
        values.extend(decode_node(seed, depth, position))
    return tuple(values), root_values


def encode(values: tuple[int, ...], depth: int, max_seed_search: int = 1024) -> EncodedTypedForest:
    leaves_per_root = 1 << depth
    if len(values) == 0 or len(values) % leaves_per_root:
        return EncodedTypedForest("raw", depth, (), values, checksum(values))
    roots: list[int] = []
    for position in range(len(values) // leaves_per_root):
        start = position * leaves_per_root
        end = start + leaves_per_root
        target = values[start:end]
        found = None
        for seed in range(max_seed_search):
            if decode_node(seed, depth, position) == target:
                found = seed
                break
        if found is None:
            return EncodedTypedForest("raw", depth, (), values, checksum(values))
        roots.append(found)
    return EncodedTypedForest("typed_tree", depth, tuple(roots), None, checksum(values))


def decode(encoded: EncodedTypedForest) -> tuple[int, ...]:
    if encoded.mode == "raw":
        if encoded.raw_values is None:
            raise RuntimeError("raw mode missing payload")
        values = encoded.raw_values
    elif encoded.mode == "typed_tree":
        out: list[int] = []
        for position, seed in enumerate(encoded.roots):
            out.extend(decode_node(seed, encoded.depth, position))
        values = tuple(out)
    else:
        raise RuntimeError(f"unknown mode {encoded.mode}")
    if checksum(values) != encoded.original_checksum:
        raise RuntimeError("checksum mismatch")
    return values


def raw_bits(values: tuple[int, ...]) -> int:
    return len(values) * B


def charged_bits(encoded: EncodedTypedForest) -> int:
    mode_bit = 1
    depth_bits = 6
    root_count_bits = 12
    if encoded.mode == "typed_tree":
        payload = len(encoded.roots) * record_bits_for_depth(encoded.depth)
    else:
        if encoded.raw_values is None:
            raise RuntimeError("raw mode missing payload")
        payload = len(encoded.raw_values) * B
    return mode_bit + depth_bits + root_count_bits + payload + CHECKSUM_BITS


def local_budget_table(max_depth: int = 7) -> None:
    print("== typed schedule local budgets ==")
    print("depth seed_bits record_bits child_payload local_margin raw/root")
    for depth in range(1, max_depth + 1):
        record = record_bits_for_depth(depth)
        child = child_payload_bits(depth)
        raw = (1 << depth) * B
        print(f"{depth:5d} {seed_bits_for_depth(depth):9d} {record:11d} "
              f"{child:13d} {child - record:12d} {raw:8d}")


def forest_demo(depth: int, roots: int) -> None:
    values, expected_roots = generated_values(depth, roots)
    encoded = encode(values, depth, max_seed_search=max(1024, roots + 1))
    decoded = decode(encoded)
    assert decoded == values
    rb = raw_bits(values)
    cb = charged_bits(encoded)
    print()
    print("== typed scheduled forest ==")
    print(f"depth={depth} roots={roots} leaves={len(values)} mode={encoded.mode}")
    print(f"expected_roots={expected_roots}")
    print(f"encoded_roots={encoded.roots}")
    print(f"raw_bits={rb} charged_bits={cb} net_bits={rb - cb}")


def random_fallback_demo(depth: int = 5) -> None:
    values = tuple((17 + 41 * i) % 256 for i in range((1 << depth) - 3))
    encoded = encode(values, depth)
    decoded = decode(encoded)
    assert decoded == values
    print()
    print("== typed schedule fallback sanity ==")
    print(f"depth={depth} mode={encoded.mode} raw_bits={raw_bits(values)} "
          f"charged_bits={charged_bits(encoded)}")


def main() -> None:
    local_budget_table()
    forest_demo(depth=4, roots=4)
    forest_demo(depth=6, roots=2)
    random_fallback_demo()
    print()
    print("Reading: TST has no open/carry channel because the tree schedule is")
    print("public. It is deep and fully charged-positive on generated reachable")
    print("forests; arbitrary inputs fall back to raw unless the encoder finds")
    print("a root seed witness.")


if __name__ == "__main__":
    main()
