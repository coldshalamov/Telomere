#!/usr/bin/env python3
"""
Bounded bundle recursion candidate.

This is a serious toy codec, not a compression benchmark. It tests a finite
construction:

* fixed arity-2 bundle records;
* fresh SHA-256 dice keyed by (pass, position, seed);
* no per-record birth tags;
* reverse decode by public unshuffle plus open/carry DFS;
* side-channel accounting priced separately from the round trip.

The toy grammar is intentionally incomplete:

    literal: 0 + 4 payload bits      (5 bits)
    record : 10 + 5 seed bits        (7 bits)
    invalid prefix: 11

That makes wrong-salt bundle opens fail structurally sometimes, which is the
finite subsidy this construction relies on.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import gcd, log2
from random import Random
from typing import Iterable


B = 4
ARITY = 2
SEED_BITS = 5
SEED_COUNT = 1 << SEED_BITS
CHECKSUM_BITS_LEDGER = 64
DOMAIN = b"TELOMERE-BOUNDED-BUNDLE-TOY"


@dataclass(frozen=True, order=True)
class Item:
    kind: str
    value: int


def lit(value: int) -> Item:
    return Item("L", value)


def rec(seed: int) -> Item:
    return Item("R", seed)


def item_bits(item: Item) -> str:
    if item.kind == "L":
        return "0" + format(item.value, f"0{B}b")
    if item.kind == "R":
        return "10" + format(item.value, f"0{SEED_BITS}b")
    raise ValueError(item)


def stream_bits(items: Iterable[Item]) -> str:
    return "".join(item_bits(item) for item in items)


def parse_one(bits: str, offset: int) -> tuple[Item, int] | None:
    if offset >= len(bits):
        return None
    if bits[offset] == "0":
        end = offset + 1 + B
        if end > len(bits):
            return None
        return lit(int(bits[offset + 1:end], 2)), end
    if bits.startswith("10", offset):
        end = offset + 2 + SEED_BITS
        if end > len(bits):
            return None
        return rec(int(bits[offset + 2:end], 2)), end
    return None


def parse_prefix_items(bits: str, count: int) -> tuple[Item, ...] | None:
    out: list[Item] = []
    offset = 0
    for _ in range(count):
        parsed = parse_one(bits, offset)
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


def expansion_items(seed: int, pass_index: int, position: int) -> tuple[Item, ...] | None:
    # Enough bits to parse two records in the worst toy case.
    bits = hash_bits("expand", seed, pass_index, position, n_bits=64)
    return parse_prefix_items(bits, ARITY)


def choose_multiplier(size: int) -> int:
    for candidate in (5, 3, 7, 11, 13, 17):
        if gcd(candidate, size) == 1:
            return candidate
    return 1


def shuffle(items: tuple[Item, ...], pass_index: int) -> tuple[Item, ...]:
    size = len(items)
    if size <= 1:
        return items
    mult = choose_multiplier(size)
    shift = (2 * pass_index + 1) % size
    out: list[Item | None] = [None] * size
    for index, item in enumerate(items):
        out[(mult * index + shift) % size] = item
    return tuple(item for item in out if item is not None)


def unshuffle(items: tuple[Item, ...], pass_index: int) -> tuple[Item, ...]:
    size = len(items)
    if size <= 1:
        return items
    mult = choose_multiplier(size)
    shift = (2 * pass_index + 1) % size
    out: list[Item | None] = [None] * size
    for old_index in range(size):
        new_index = (mult * old_index + shift) % size
        out[old_index] = items[new_index]
    return tuple(item for item in out if item is not None)


@dataclass
class PassStat:
    pass_index: int
    before_len: int
    after_len: int
    windows: int
    draws: int
    matches: int


@dataclass
class Encoded:
    final_items: tuple[Item, ...]
    stats: list[PassStat]
    original_checksum: str
    original_count: int
    passes: int


def checksum(items: tuple[Item, ...]) -> str:
    # The toy uses a full checksum as a referee; the compression ledger below
    # charges the ambiguity cost instead of pretending this is free.
    return sha256(stream_bits(items).encode("ascii")).hexdigest()


def find_seed_for_span(span: tuple[Item, Item], pass_index: int, position: int) -> int | None:
    for seed in range(SEED_COUNT):
        if expansion_items(seed, pass_index, position) == span:
            if len(item_bits(rec(seed))) < len(stream_bits(span)):
                return seed
    return None


def encode(values: list[int], passes: int) -> Encoded:
    items = tuple(lit(value) for value in values)
    original = items
    stats: list[PassStat] = []
    for pass_index in range(1, passes + 1):
        before = items
        out: list[Item] = []
        index = 0
        matches = 0
        windows = max(0, len(before) - 1)
        draws = 0
        while index < len(before):
            if index + 1 < len(before):
                span = (before[index], before[index + 1])
                draws += SEED_COUNT
                packed_position = len(out)
                seed = find_seed_for_span(span, pass_index, packed_position)
                if seed is not None:
                    out.append(rec(seed))
                    matches += 1
                    index += 2
                    continue
            out.append(before[index])
            index += 1
        items = shuffle(tuple(out), pass_index)
        stats.append(PassStat(pass_index, len(before), len(out), windows, draws, matches))
    return Encoded(items, stats, checksum(original), len(original), passes)


def dense_first_pass_values(pair_count: int) -> list[int]:
    """Generate literal blocks whose pass-1 packed windows are reachable.

    This is a positive-control dense fixture. It proves the codec and ledger for
    a reachable class; it is not evidence of natural prevalence.
    """
    values: list[int] = []
    for packed_position in range(pair_count):
        for seed in range(SEED_COUNT):
            expanded = expansion_items(seed, 1, packed_position)
            if (
                expanded is not None
                and len(expanded) == 2
                and expanded[0].kind == "L"
                and expanded[1].kind == "L"
            ):
                values.extend([expanded[0].value, expanded[1].value])
                break
        else:
            raise RuntimeError(f"no dense pair seed for packed position {packed_position}")
    return values


def open_record(item: Item, pass_index: int, position: int) -> tuple[Item, ...] | None:
    if item.kind != "R":
        return None
    return expansion_items(item.value, pass_index, position)


def decode(encoded: Encoded, max_states: int = 200_000) -> tuple[Item, ...]:
    states: set[tuple[Item, ...]] = {encoded.final_items}
    max_seen = 1
    for pass_index in range(encoded.passes, 0, -1):
        next_states: set[tuple[Item, ...]] = set()
        for state in states:
            unshuffled = unshuffle(state, pass_index)

            def walk(position: int, acc: list[Item]) -> None:
                if len(next_states) > max_states:
                    return
                if len(acc) > encoded.original_count:
                    return
                if position == len(unshuffled):
                    next_states.add(tuple(acc))
                    return
                item = unshuffled[position]
                # Carry is always legal.
                acc.append(item)
                walk(position + 1, acc)
                acc.pop()
                # Open is legal only for records whose digest parses as two items.
                opened = open_record(item, pass_index, position)
                if opened is not None:
                    acc.extend(opened)
                    walk(position + 1, acc)
                    del acc[-len(opened):]

            walk(0, [])
        if len(next_states) > max_states:
            raise RuntimeError(f"decode state cap exceeded at pass {pass_index}")
        states = next_states
        max_seen = max(max_seen, len(states))

    winners = [
        state
        for state in states
        if len(state) == encoded.original_count
        and all(item.kind == "L" for item in state)
        and checksum(state) == encoded.original_checksum
    ]
    if len(winners) != 1:
        raise RuntimeError(f"expected one checksum winner, found {len(winners)}")
    decode.max_states_seen = max_seen  # type: ignore[attr-defined]
    decode.final_candidates = len(states)  # type: ignore[attr-defined]
    return winners[0]


def ambiguity_cost_per_record(passes: int, structural_bits: float) -> float:
    q = 2 ** (-structural_bits)
    return log2(1 + (passes - 1) * q)


def toy_ledger(encoded: Encoded) -> dict[str, float]:
    raw_bits = encoded.original_count * B
    payload_bits = len(stream_bits(encoded.final_items))
    records = sum(1 for item in encoded.final_items if item.kind == "R")
    total_matches = sum(stat.matches for stat in encoded.stats)
    # Estimate the structural filter directly from the toy prefix grammar by
    # enumerating all possible first 14 bits, enough for two toy records.
    valid = 0
    total = 1 << 14
    for value in range(total):
        bits = format(value, "014b")
        if parse_prefix_items(bits, ARITY) is not None:
            valid += 1
    structural_bits = -log2(valid / total)
    ambiguity_bits = records * ambiguity_cost_per_record(encoded.passes, structural_bits)
    header_bits = CHECKSUM_BITS_LEDGER + max(1, encoded.passes.bit_length())
    return {
        "raw_bits": raw_bits,
        "payload_bits": payload_bits,
        "records": records,
        "total_matches": total_matches,
        "structural_bits": structural_bits,
        "ambiguity_bits": ambiguity_bits,
        "header_bits": header_bits,
        "charged_bits": payload_bits + ambiguity_bits + header_bits,
        "asymptotic_bits": payload_bits + ambiguity_bits,
    }


def dense_regime_table() -> None:
    print("== asymptotic dense-regime ledger ==")
    print("Assume fixed arity-2 bundle records with 2.17-bit gross win/hit")
    print("and birth ambiguity cost c(P,E). Net is positive when density")
    print("covers literal carriage plus c(P,E).")
    print(f"{'passes':>7} {'E bits':>7} {'c(P,E)':>9} {'net/hit':>9}")
    for passes in (16, 64, 256, 1024):
        for e_bits in (9.36, 12.59, 18.20):
            cost = ambiguity_cost_per_record(passes, e_bits)
            print(f"{passes:7d} {e_bits:7.2f} {cost:9.3f} {2.17 - cost:9.3f}")
        print()


def print_encoded_report(title: str, values: list[int], passes: int) -> None:
    encoded = encode(values, passes)
    decoded = decode(encoded)
    assert decoded == tuple(lit(value) for value in values)

    ledger = toy_ledger(encoded)
    print(f"== {title} ==")
    print(f"blocks={len(values)} B={B} passes={passes} seed_count={SEED_COUNT}")
    print(f"round_trip=True max_decode_states={getattr(decode, 'max_states_seen')}")
    print(f"final_candidates_before_checksum={getattr(decode, 'final_candidates')}")
    print()
    print(f"{'pass':>4} {'before':>6} {'after':>5} {'windows':>7} "
          f"{'draws':>6} {'matches':>7}")
    for stat in encoded.stats:
        print(f"{stat.pass_index:4d} {stat.before_len:6d} {stat.after_len:5d} "
              f"{stat.windows:7d} {stat.draws:6d} {stat.matches:7d}")
    print()
    print("== toy accounting ==")
    for key in (
        "raw_bits",
        "payload_bits",
        "records",
        "total_matches",
        "structural_bits",
        "ambiguity_bits",
        "header_bits",
        "charged_bits",
        "asymptotic_bits",
    ):
        print(f"{key:>18}: {ledger[key]:.3f}")
    print(f"{'payload_delta':>18}: {ledger['raw_bits'] - ledger['payload_bits']:.3f}")
    print(f"{'charged_delta':>18}: {ledger['raw_bits'] - ledger['charged_bits']:.3f}")
    print(f"{'asymptotic_delta':>18}: {ledger['raw_bits'] - ledger['asymptotic_bits']:.3f}")
    margin = ledger["raw_bits"] - ledger["asymptotic_bits"]
    if margin > 0:
        print(f"{'header_break_even':>18}: {ledger['header_bits'] / margin:.3f} fixture-copies")
    print()


def run_demo(seed: int = 7, count: int = 24, passes: int = 6) -> None:
    rng = Random(seed)
    random_values = [rng.randrange(1 << B) for _ in range(count)]
    print_encoded_report("bounded bundle codec: random mechanics fixture",
                         random_values, passes)

    dense_values = dense_first_pass_values(pair_count=12)
    print_encoded_report("bounded bundle codec: generated dense fixture",
                         dense_values, passes=2)

    print("Dense fixture note: generated reachable data is a positive control")
    print("for the codec and payload ledger, not a natural-density claim.")
    print()
    dense_regime_table()


if __name__ == "__main__":
    run_demo()
