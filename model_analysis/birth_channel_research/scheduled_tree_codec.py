#!/usr/bin/env python3
"""
Scheduled Tree Bundle (STB) candidate.

This mutation removes the open/carry birth problem by making the opening
schedule public:

* a slab is accepted only if it is a complete binary bundle tree;
* every internal node opens at its public tree depth;
* salts are fresh by (depth, position, seed);
* the decoder needs no per-record birth tags and no trial open/carry search;
* the price is reachability density: arbitrary data almost never fits, but a
  generated reachable class is fully charged-positive.

This is a constructive positive-control mode, not a natural-prevalence claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from math import log2
import sys


B = 8
CHECKSUM_BITS = 64
DOMAIN = b"TELOMERE-SCHEDULED-TREE-TOY"


@dataclass(frozen=True)
class Item:
    kind: str
    value: int


def lit(value: int) -> Item:
    return Item("L", value)


def rec(seed: int) -> Item:
    return Item("R", seed)


def seed_bits_for_depth(depth: int) -> int:
    """Depth-tiered seed width.

    Depth 1 records replace two literals, so they must stay under two literal
    items. Depth 3 roots replace two depth-2 records, so they can spend more
    seed bits while still being locally compressive.
    """
    if depth <= 2:
        return 15
    if depth == 3:
        return 22
    return 22


def seed_count_for_depth(depth: int) -> int:
    return 1 << seed_bits_for_depth(depth)


def item_bits(item: Item, depth: int = 1) -> str:
    if item.kind == "L":
        return "0" + format(item.value, f"0{B}b")
    if item.kind == "R":
        return "10" + format(item.value, f"0{seed_bits_for_depth(depth)}b")
    raise ValueError(item)


def parse_one(bits: str, offset: int, record_seed_bits: int) -> tuple[Item, int] | None:
    if offset >= len(bits):
        return None
    if bits[offset] == "0":
        end = offset + 1 + B
        if end > len(bits):
            return None
        return lit(int(bits[offset + 1:end], 2)), end
    if bits.startswith("10", offset):
        end = offset + 2 + record_seed_bits
        if end > len(bits):
            return None
        return rec(int(bits[offset + 2:end], 2)), end
    return None


def parse_prefix_items(bits: str, count: int = 2, record_seed_bits: int = 15) -> tuple[Item, ...] | None:
    offset = 0
    out: list[Item] = []
    for _ in range(count):
        parsed = parse_one(bits, offset, record_seed_bits)
        if parsed is None:
            return None
        item, offset = parsed
        out.append(item)
    return tuple(out)


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


def expansion_items(seed: int, depth: int, position: int) -> tuple[Item, ...] | None:
    bits = hash_bits("expand", seed, depth, position, n_bits=64)
    child_seed_bits = seed_bits_for_depth(max(1, depth - 1))
    return parse_prefix_items(bits, 2, child_seed_bits)


@lru_cache(maxsize=None)
def valid_seed(seed: int, depth: int, position: int) -> bool:
    expanded = expansion_items(seed, depth, position)
    if expanded is None:
        return False
    if depth == 1:
        return all(item.kind == "L" for item in expanded)
    if not all(item.kind == "R" for item in expanded):
        return False
    left, right = expanded
    return (
        valid_seed(left.value, depth - 1, position * 2)
        and valid_seed(right.value, depth - 1, position * 2 + 1)
    )


def find_root(depth: int, position: int = 0) -> int | None:
    for seed in range(seed_count_for_depth(depth)):
        if valid_seed(seed, depth, position):
            return seed
    return None


def decode_record(seed: int, depth: int, position: int) -> tuple[int, ...]:
    expanded = expansion_items(seed, depth, position)
    if expanded is None:
        raise RuntimeError("invalid expansion")
    if depth == 1:
        if not all(item.kind == "L" for item in expanded):
            raise RuntimeError("leaf depth expanded to non-literals")
        return tuple(item.value for item in expanded)
    if not all(item.kind == "R" for item in expanded):
        raise RuntimeError("internal depth expanded to non-records")
    left, right = expanded
    return (
        *decode_record(left.value, depth - 1, position * 2),
        *decode_record(right.value, depth - 1, position * 2 + 1),
    )


def checksum(values: tuple[int, ...]) -> str:
    data = bytes(values)
    return sha256(data).hexdigest()


@dataclass
class EncodedTree:
    mode: str
    depth: int
    root_seed: int | None
    raw_values: tuple[int, ...] | None
    original_checksum: str


def encode_tree(values: tuple[int, ...]) -> EncodedTree:
    if len(values) == 0 or len(values) & (len(values) - 1):
        return EncodedTree("raw", 0, None, values, checksum(values))
    depth = int(log2(len(values)))
    root = find_root(depth)
    if root is None:
        return EncodedTree("raw", depth, None, values, checksum(values))
    generated = decode_record(root, depth, 0)
    if generated != values:
        return EncodedTree("raw", depth, None, values, checksum(values))
    return EncodedTree("tree", depth, root, None, checksum(values))


def decode_tree(encoded: EncodedTree) -> tuple[int, ...]:
    if encoded.mode == "raw":
        if encoded.raw_values is None:
            raise RuntimeError("raw mode missing payload")
        values = encoded.raw_values
    elif encoded.mode == "tree":
        if encoded.root_seed is None:
            raise RuntimeError("tree mode missing root")
        values = decode_record(encoded.root_seed, encoded.depth, 0)
    else:
        raise RuntimeError(f"unknown mode {encoded.mode}")
    if checksum(values) != encoded.original_checksum:
        raise RuntimeError("checksum mismatch")
    return values


def generated_reachable_values(depth: int) -> tuple[int, ...]:
    root = find_root(depth)
    if root is None:
        raise RuntimeError(f"no reachable root at depth {depth}")
    return decode_record(root, depth, 0)


def charged_bits(encoded: EncodedTree) -> int:
    mode_bit = 1
    depth_bits = 6
    if encoded.mode == "tree":
        payload = 2 + seed_bits_for_depth(encoded.depth)
    else:
        if encoded.raw_values is None:
            raise RuntimeError("raw mode missing payload")
        payload = len(encoded.raw_values) * B
    return mode_bit + depth_bits + payload + CHECKSUM_BITS


def raw_bits(values: tuple[int, ...]) -> int:
    return len(values) * B


@dataclass
class EncodedForest:
    mode: str
    depth: int
    root_seeds: tuple[int, ...]
    raw_values: tuple[int, ...] | None
    original_checksum: str


def generated_forest_values(depth: int, roots: int) -> tuple[int, ...]:
    values: list[int] = []
    for position in range(roots):
        root = find_root(depth, position)
        if root is None:
            raise RuntimeError(f"no reachable root at depth {depth}, position {position}")
        values.extend(decode_record(root, depth, position))
    return tuple(values)


def encode_forest(values: tuple[int, ...], depth: int) -> EncodedForest:
    leaves_per_root = 1 << depth
    if len(values) == 0 or len(values) % leaves_per_root:
        return EncodedForest("raw", depth, (), values, checksum(values))
    roots: list[int] = []
    for position in range(len(values) // leaves_per_root):
        root = find_root(depth, position)
        if root is None:
            return EncodedForest("raw", depth, (), values, checksum(values))
        start = position * leaves_per_root
        end = start + leaves_per_root
        if decode_record(root, depth, position) != values[start:end]:
            return EncodedForest("raw", depth, (), values, checksum(values))
        roots.append(root)
    return EncodedForest("forest", depth, tuple(roots), None, checksum(values))


def decode_forest(encoded: EncodedForest) -> tuple[int, ...]:
    if encoded.mode == "raw":
        if encoded.raw_values is None:
            raise RuntimeError("raw forest missing payload")
        values = encoded.raw_values
    elif encoded.mode == "forest":
        values_list: list[int] = []
        for position, root in enumerate(encoded.root_seeds):
            values_list.extend(decode_record(root, encoded.depth, position))
        values = tuple(values_list)
    else:
        raise RuntimeError(f"unknown forest mode {encoded.mode}")
    if checksum(values) != encoded.original_checksum:
        raise RuntimeError("forest checksum mismatch")
    return values


def charged_forest_bits(encoded: EncodedForest) -> int:
    mode_bit = 1
    depth_bits = 6
    root_count_bits = 8
    if encoded.mode == "forest":
        payload = len(encoded.root_seeds) * (2 + seed_bits_for_depth(encoded.depth))
    else:
        if encoded.raw_values is None:
            raise RuntimeError("raw forest missing payload")
        payload = len(encoded.raw_values) * B
    return mode_bit + depth_bits + root_count_bits + payload + CHECKSUM_BITS


def run_depth(depth: int) -> None:
    values = generated_reachable_values(depth)
    encoded = encode_tree(values)
    decoded = decode_tree(encoded)
    assert decoded == values
    rb = raw_bits(values)
    cb = charged_bits(encoded)
    print(f"{depth:5d} {len(values):7d} {encoded.root_seed:9d} "
          f"{rb:9d} {cb:12d} {rb - cb:10d}")


def random_rejection_demo(depth: int = 6) -> None:
    # Deterministic non-generated input with a non-power-of-two length, so the
    # codec safely falls back to raw without spending search on a tree shape.
    values = tuple((i * 37 + 11) % 256 for i in range((1 << depth) - 1))
    encoded = encode_tree(values)
    decoded = decode_tree(encoded)
    assert decoded == values
    print()
    print("== random/fallback sanity ==")
    print(f"depth={depth} mode={encoded.mode} raw_bits={raw_bits(values)} "
          f"charged_bits={charged_bits(encoded)}")


def forest_demo(depth: int = 2, roots: int = 8) -> None:
    values = generated_forest_values(depth, roots)
    encoded = encode_forest(values, depth)
    decoded = decode_forest(encoded)
    assert decoded == values
    rb = raw_bits(values)
    cb = charged_forest_bits(encoded)
    print()
    print("== scheduled forest charged-positive control ==")
    print(f"depth={depth} roots={roots} leaves={len(values)} mode={encoded.mode}")
    print(f"raw_bits={rb} charged_bits={cb} net_bits={rb - cb}")
    print(f"root_seeds={encoded.root_seeds}")


def main() -> None:
    print("== scheduled tree bundle positive-control ==")
    print("depth  leaves root_seed seed_bits  raw_bits charged_bits  net_bits")
    for depth in range(1, 4):
        try:
            values = generated_reachable_values(depth)
            encoded = encode_tree(values)
            decoded = decode_tree(encoded)
            assert decoded == values
            rb = raw_bits(values)
            cb = charged_bits(encoded)
            print(f"{depth:5d} {len(values):7d} {encoded.root_seed:9d} "
                  f"{seed_bits_for_depth(depth):9d} {rb:9d} {cb:12d} {rb - cb:10d}")
        except RuntimeError as exc:
            print(f"{depth:5d} {'-':>7} {'-':>9} {'-':>9} {'-':>9} {'-':>12}  {exc}")
    forest_demo()
    if "--deep" in sys.argv:
        forest_demo(depth=3, roots=2)
    random_rejection_demo()
    print()
    print("Reading: the schedule removes birth/open metadata by construction.")
    print("The cost is reachability density: arbitrary data falls back to raw;")
    print("generated tree-reachable data is fully charged-positive once")
    print("raw_bits > mode+depth+seed+checksum.")


if __name__ == "__main__":
    main()
