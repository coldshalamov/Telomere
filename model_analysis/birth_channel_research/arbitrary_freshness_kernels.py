#!/usr/bin/env python3
"""
Arbitrary-content freshness kernels.

This file is for the reopened bar: generated/reachable fixtures are not
success. The question is whether a content-blind mechanism can keep usable
match supply across recursive passes while decoding statelessly and without an
explicit birth-pass channel.

The kernels below test three families:

1. decoder-known nonces carried in visible record bits;
2. target refresh with a fixed, unsalted seed universe;
3. self-dating grammar bits that make wrong openings fail structurally.

Every toy either round-trips exactly or is only an entropy counter. Positive
controls are labeled as such; random/unshaped supply is priced separately.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
from math import ceil, expm1, lgamma, log, log1p, log2
from pathlib import Path
from random import Random
from statistics import mean
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS as J3D1_MAX_PAYLOAD_WIDTH_BITS,
    j3d1_cost_for_payload_width,
    lotus_width_for_value,
)


DOMAIN = b"TELOMERE-ARBITRARY-FRESHNESS-TOY"


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


# ---------------------------------------------------------------------------
# Family 1: decoder-known nonces.


@dataclass(frozen=True)
class NonceRecord:
    nonce: int
    seed: int
    nonce_bits: int
    seed_bits: int
    span_bits: int


def expand_nonce_record(nonce: int, seed: int, span_bits: int) -> str:
    return hash_bits("visible-nonce", nonce, seed, n_bits=span_bits)


def build_nonce_book(nonce_bits: int, seed_bits: int, span_bits: int) -> dict[str, NonceRecord]:
    book: dict[str, NonceRecord] = {}
    for nonce in range(1 << nonce_bits):
        for seed in range(1 << seed_bits):
            bits = expand_nonce_record(nonce, seed, span_bits)
            book.setdefault(bits, NonceRecord(nonce, seed, nonce_bits, seed_bits, span_bits))
    return book


def encode_nonce_span(
    target_bits: str,
    nonce_bits: int,
    seed_bits: int,
    book: dict[str, NonceRecord] | None = None,
) -> NonceRecord | str:
    span_bits = len(target_bits)
    record_bits = 2 + nonce_bits + seed_bits
    if record_bits >= span_bits:
        return target_bits
    if book is None:
        book = build_nonce_book(nonce_bits, seed_bits, span_bits)
    if target_bits in book:
        return book[target_bits]
    return target_bits


def decode_nonce_span(encoded: NonceRecord | str) -> str:
    if isinstance(encoded, str):
        return encoded
    return expand_nonce_record(encoded.nonce, encoded.seed, encoded.span_bits)


def decoder_known_nonce_demo() -> None:
    print("== family 1: decoder-known visible nonce ==")
    print("The nonce is known before expansion because it is stored in the")
    print("record. That is stateless, but the nonce bits are paid address bits.")
    print()
    span_bits = 16
    seed_bits = 10
    marker_bits = 2
    rng = Random(42)
    print(f"{'k nonce':>7} {'record':>7} {'gross':>7} {'hit p':>10} "
          f"{'E win/window':>13} {'random hits':>12}")
    for nonce_bits in range(0, 6):
        record_bits = marker_bits + seed_bits + nonce_bits
        gross = span_bits - record_bits
        hit_p = min(1.0, (1 << (seed_bits + nonce_bits)) / (1 << span_bits))
        expected = hit_p * max(gross, 0)
        book = build_nonce_book(nonce_bits, seed_bits, span_bits)
        hits = 0
        trials = 256
        for _ in range(trials):
            target = format(rng.getrandbits(span_bits), f"0{span_bits}b")
            encoded = encode_nonce_span(target, nonce_bits, seed_bits, book)
            assert decode_nonce_span(encoded) == target
            hits += int(isinstance(encoded, NonceRecord))
        print(f"{nonce_bits:7d} {record_bits:7d} {gross:7d} {hit_p:10.5f} "
              f"{expected:13.5f} {hits:5d}/{trials:<6d}")
    print()
    print("Reading: visible nonces can refresh dice and decode cleanly, but")
    print("only by widening the stored address. This is a paid seed-depth")
    print("tradeoff, not a free birth/freshness channel.")
    print()


# ---------------------------------------------------------------------------
# Family 2: target refresh without salt refresh.


CHURN_B = 4
CHURN_SEED_BITS = 5
CHURN_SEED_COUNT = 1 << CHURN_SEED_BITS


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
        return "0" + format(item.value, f"0{CHURN_B}b")
    if item.kind == "R":
        return "10" + format(item.value, f"0{CHURN_SEED_BITS}b")
    raise ValueError(item)


def span_bits(span: tuple[Item, ...]) -> str:
    return "".join(item_bits(item) for item in span)


def parse_one(bits: str, offset: int) -> tuple[Item, int] | None:
    if offset >= len(bits):
        return None
    if bits[offset] == "0":
        end = offset + 1 + CHURN_B
        if end > len(bits):
            return None
        return lit(int(bits[offset + 1:end], 2)), end
    if bits.startswith("10", offset):
        end = offset + 2 + CHURN_SEED_BITS
        if end > len(bits):
            return None
        return rec(int(bits[offset + 2:end], 2)), end
    return None


def parse_two_items(bits: str) -> tuple[Item, Item] | None:
    first = parse_one(bits, 0)
    if first is None:
        return None
    item0, offset = first
    second = parse_one(bits, offset)
    if second is None:
        return None
    item1, _ = second
    return item0, item1


def parse_items(bits: str, count: int) -> tuple[Item, ...] | None:
    out: list[Item] = []
    offset = 0
    for _ in range(count):
        parsed = parse_one(bits, offset)
        if parsed is None:
            return None
        item, offset = parsed
        out.append(item)
    return tuple(out)


def fixed_expansion(seed: int) -> tuple[Item, Item] | None:
    return parse_two_items(hash_bits("fixed-universe", seed, n_bits=64))


def build_fixed_universe() -> dict[tuple[Item, Item], int]:
    universe: dict[tuple[Item, Item], int] = {}
    for seed in range(CHURN_SEED_COUNT):
        expanded = fixed_expansion(seed)
        if expanded is not None and seed not in expanded:
            universe.setdefault(expanded, seed)
    return universe


FIXED_UNIVERSE = build_fixed_universe()


def lane_expansion_items(seed: int, lane: int) -> tuple[Item, ...] | None:
    return parse_items(hash_bits("public-lane-universe", lane, seed, n_bits=64), 2)


def find_lane_seed_for_span(span: tuple[Item, Item], lanes: int) -> int | None:
    for seed in range(CHURN_SEED_COUNT):
        for lane in range(lanes):
            if lane_expansion_items(seed, lane) == span:
                if len(item_bits(rec(seed))) < len(span_bits(span)):
                    return seed
    return None


def encode_public_lane_stream(values: tuple[int, ...], lanes: int, passes: int) -> tuple[Item, ...]:
    items = tuple(lit(value) for value in values)
    for _ in range(passes):
        out: list[Item] = []
        index = 0
        matches = 0
        while index < len(items):
            if index + 1 < len(items):
                span = (items[index], items[index + 1])
                seed = find_lane_seed_for_span(span, lanes)
                if seed is not None:
                    out.append(rec(seed))
                    matches += 1
                    index += 2
                    continue
            out.append(items[index])
            index += 1
        items = tuple(out)
        if matches == 0:
            break
    return items


def lane_decode_item_candidates(
    item: Item,
    lanes: int,
    stack: tuple[int, ...] = (),
    cap: int = 200_000,
) -> tuple[set[tuple[int, ...]], bool]:
    if item.kind == "L":
        return {(item.value,)}, False
    seed = item.value
    if seed in stack:
        return set(), False
    out: set[tuple[int, ...]] = set()
    capped = False
    for lane in range(lanes):
        expanded = lane_expansion_items(seed, lane)
        if expanded is None:
            continue
        left, left_cap = lane_decode_item_candidates(expanded[0], lanes, (*stack, seed), cap)
        right, right_cap = lane_decode_item_candidates(expanded[1], lanes, (*stack, seed), cap)
        capped = capped or left_cap or right_cap
        for lhs in left:
            for rhs in right:
                out.add((*lhs, *rhs))
                if len(out) >= cap:
                    return out, True
    return out, capped


def lane_decode_stream_candidates(
    items: tuple[Item, ...],
    lanes: int,
    cap: int = 200_000,
) -> tuple[set[tuple[int, ...]], bool]:
    states: set[tuple[int, ...]] = {()}
    capped = False
    for item in items:
        candidates, item_capped = lane_decode_item_candidates(item, lanes, cap=cap)
        capped = capped or item_capped
        next_states: set[tuple[int, ...]] = set()
        for prefix in states:
            for candidate in candidates:
                next_states.add((*prefix, *candidate))
                if len(next_states) >= cap:
                    return next_states, True
        states = next_states
    return states, capped


def public_lane_ensemble_demo() -> None:
    print("== family 1b: public nonce-lane ensemble without stored lane ==")
    print("The encoder tries K public lanes per seed. The record stores only")
    print("the seed, so the decoder must try all lanes and price surviving")
    print("readings. This avoids a birth-pass field but not ambiguity.")
    print()
    rng = Random(789)
    values = tuple(rng.randrange(1 << CHURN_B) for _ in range(24))
    print(f"{'lanes':>6} {'final items':>11} {'records':>8} {'payload bits':>12} "
          f"{'candidates':>12} {'ambig bits':>11} {'orig in set':>11} {'net vs raw':>12}")
    raw_payload_bits = len(values) * CHURN_B
    for lanes in [1, 2, 4, 8]:
        encoded = encode_public_lane_stream(values, lanes, passes=4)
        candidates, capped = lane_decode_stream_candidates(encoded, lanes)
        records = sum(1 for item in encoded if item.kind == "R")
        payload_bits = sum(len(item_bits(item)) for item in encoded)
        candidate_count = len(candidates)
        ambiguity_bits = log2(candidate_count) if candidate_count else 0.0
        original_present = values in candidates
        original_text = "unknown" if capped and not original_present else str(original_present)
        net_vs_raw = raw_payload_bits - payload_bits - ambiguity_bits
        suffix = "+" if capped else ""
        net_text = f"<={net_vs_raw:.3f}" if capped else f"{net_vs_raw:.3f}"
        print(f"{lanes:6d} {len(encoded):11d} {records:8d} {payload_bits:12d} "
              f"{str(candidate_count) + suffix:>12} {ambiguity_bits:11.3f} "
              f"{original_text:>11} {net_text:>12}")
    print()
    print("Reading: public lanes increase search supply without storing a")
    print("lane id, but the decoder's candidate set grows because wrong")
    print("lanes often parse. Stronger self-dating grammar is needed before")
    print("this can scale, and that grammar must not destroy hit supply.")
    print()


def context_key(items: tuple[Item, ...], position: int) -> tuple[str, int]:
    left = "BOUNDARY" if position == 0 else item_bits(items[position - 1])
    return left, position


def context_expansion_items(seed: int, left_ctx: str, packed_position: int) -> tuple[Item, ...] | None:
    return parse_items(hash_bits("context-left-position-universe", seed, left_ctx, packed_position, n_bits=64), 2)


def find_context_seed_for_span(span: tuple[Item, Item], left_ctx: str, packed_position: int) -> int | None:
    for seed in range(CHURN_SEED_COUNT):
        if context_expansion_items(seed, left_ctx, packed_position) == span:
            if len(item_bits(rec(seed))) < len(span_bits(span)):
                return seed
    return None


def shuffle_context_items(items: tuple[Item, ...], pass_index: int) -> tuple[Item, ...]:
    size = len(items)
    if size <= 1:
        return items
    shift = (2 * pass_index + 1) % size
    out: list[Item | None] = [None] * size
    for index, item in enumerate(items):
        out[(5 * index + shift) % size] = item
    if any(item is None for item in out):
        # Fallback for toy sizes where 5 is not coprime.
        return tuple(items[(index + shift) % size] for index in range(size))
    return tuple(item for item in out if item is not None)


def unshuffle_context_items(items: tuple[Item, ...], pass_index: int) -> tuple[Item, ...]:
    size = len(items)
    if size <= 1:
        return items
    shift = (2 * pass_index + 1) % size
    out: list[Item | None] = [None] * size
    seen: set[int] = set()
    for old_index in range(size):
        new_index = (5 * old_index + shift) % size
        if new_index in seen:
            return tuple(items[(index - shift) % size] for index in range(size))
        seen.add(new_index)
        out[old_index] = items[new_index]
    return tuple(item for item in out if item is not None)


@dataclass
class ContextStat:
    pass_index: int
    before_len: int
    after_len: int
    windows: int
    matches: int
    bit_delta: int


@dataclass
class ContextEncoded:
    final_items: tuple[Item, ...]
    stats: tuple[ContextStat, ...]
    original_values: tuple[int, ...]
    passes: int


def encode_context_salted(values: tuple[int, ...], passes: int) -> ContextEncoded:
    items = tuple(lit(value) for value in values)
    stats: list[ContextStat] = []
    for pass_index in range(1, passes + 1):
        before = items
        out: list[Item] = []
        index = 0
        matches = 0
        bit_delta = 0
        windows = max(0, len(before) - 1)
        while index < len(before):
            if index + 1 < len(before):
                span = (before[index], before[index + 1])
                left_ctx = "BOUNDARY" if not out else item_bits(out[-1])
                packed_position = len(out)
                seed = find_context_seed_for_span(span, left_ctx, packed_position)
                if seed is not None:
                    replacement = rec(seed)
                    out.append(replacement)
                    matches += 1
                    bit_delta += len(span_bits(span)) - len(item_bits(replacement))
                    index += 2
                    continue
            out.append(before[index])
            index += 1
        items = shuffle_context_items(tuple(out), pass_index)
        stats.append(ContextStat(pass_index, len(before), len(out), windows, matches, bit_delta))
        if matches == 0:
            break
    return ContextEncoded(items, tuple(stats), values, len(stats))


def decode_context_salted(encoded: ContextEncoded, max_states: int = 200_000) -> tuple[set[tuple[int, ...]], bool]:
    states: set[tuple[Item, ...]] = {encoded.final_items}
    capped = False
    for pass_index in range(encoded.passes, 0, -1):
        next_states: set[tuple[Item, ...]] = set()
        for state in states:
            unshuffled = unshuffle_context_items(state, pass_index)

            def walk(position: int, acc: list[Item]) -> None:
                nonlocal capped
                if capped:
                    return
                if len(acc) > len(encoded.original_values):
                    return
                if position == len(unshuffled):
                    next_states.add(tuple(acc))
                    if len(next_states) >= max_states:
                        capped = True
                    return
                item = unshuffled[position]
                acc.append(item)
                walk(position + 1, acc)
                acc.pop()
                if item.kind == "R":
                    left_ctx, packed_position = context_key(unshuffled, position)
                    opened = context_expansion_items(item.value, left_ctx, packed_position)
                    if opened is not None:
                        acc.extend(opened)
                        walk(position + 1, acc)
                        del acc[-len(opened):]

            walk(0, [])
            if capped:
                break
        states = next_states
        if capped:
            break
    decoded: set[tuple[int, ...]] = set()
    for state in states:
        if all(item.kind == "L" for item in state):
            decoded.add(tuple(item.value for item in state))
    return decoded, capped


def context_neighbor_nonce_demo(trials: int = 20, n_blocks: int = 20, passes: int = 5) -> None:
    print("== family 1c: decoder-known left-context/position nonce ==")
    print("The salt is the visible left neighbor plus packed output position")
    print("at the post-replacement state. Encoder and decoder both know it")
    print("before expansion; no nonce field is stored.")
    print()
    rng = Random(987)
    rows: dict[int, list[ContextStat]] = {p: [] for p in range(1, passes + 1)}
    candidate_counts: list[int] = []
    capped_count = 0
    present_count = 0
    payload_gain: list[float] = []
    charged_gain: list[float] = []
    for _ in range(trials):
        values = tuple(rng.randrange(1 << CHURN_B) for _ in range(n_blocks))
        encoded = encode_context_salted(values, passes)
        candidates, capped = decode_context_salted(encoded, max_states=50_000)
        present = values in candidates
        assert present or capped
        final_bits = sum(len(item_bits(item)) for item in encoded.final_items)
        raw_payload_bits = len(values) * CHURN_B
        count = len(candidates)
        ambiguity = log2(count) if count else 0.0
        payload_gain.append(raw_payload_bits - final_bits)
        charged_gain.append(raw_payload_bits - final_bits - ambiguity)
        candidate_counts.append(count)
        capped_count += int(capped)
        present_count += int(present)
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(f"round_trips_or_capped={present_count + capped_count}/{trials} "
          f"exact_present={present_count}/{trials} capped={capped_count}")
    print(f"{'pass':>4} {'avg windows':>12} {'avg matches':>12} "
          f"{'hit/window':>11} {'avg gain':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_windows = mean(stat.windows for stat in stats)
        avg_matches = mean(stat.matches for stat in stats)
        hit_rate = avg_matches / avg_windows if avg_windows else 0.0
        avg_gain = mean(stat.bit_delta for stat in stats)
        print(f"{pass_index:4d} {avg_windows:12.2f} {avg_matches:12.3f} "
              f"{hit_rate:11.5f} {avg_gain:10.3f}")
    print(f"mean candidate count before checksum={mean(candidate_counts):.2f}")
    print(f"mean payload gain vs original raw={mean(payload_gain):.3f} bits")
    print(f"mean lower-bound charged gain={mean(charged_gain):.3f} bits")
    print()
    print("Reading: neighbor context is a genuinely decoder-visible nonce")
    print("that changes as the stream changes. In this toy it refreshes first")
    print("pass supply but does not sustain later passes, and raw-payload")
    print("accounting plus surviving readings remain negative.")
    print()


def decodes_to_literals(item: Item, stack: tuple[int, ...] = ()) -> tuple[int, ...] | None:
    if item.kind == "L":
        return (item.value,)
    seed = item.value
    if seed in stack:
        return None
    expanded = fixed_expansion(seed)
    if expanded is None:
        return None
    out: list[int] = []
    for child in expanded:
        decoded = decodes_to_literals(child, (*stack, seed))
        if decoded is None:
            return None
        out.extend(decoded)
    return tuple(out)


def decode_fixed_stream(items: tuple[Item, ...]) -> tuple[int, ...]:
    out: list[int] = []
    for item in items:
        decoded = decodes_to_literals(item)
        if decoded is None:
            raise RuntimeError(f"undecodable item {item}")
        out.extend(decoded)
    return tuple(out)


@dataclass
class ChurnStat:
    pass_index: int
    before_len: int
    windows: int
    matches: int
    bit_delta: int


@dataclass
class ChurnEncoded:
    final_items: tuple[Item, ...]
    stats: tuple[ChurnStat, ...]


def encode_fixed_churn(values: tuple[int, ...], passes: int) -> ChurnEncoded:
    items = tuple(lit(value) for value in values)
    stats: list[ChurnStat] = []
    for pass_index in range(1, passes + 1):
        out: list[Item] = []
        index = 0
        matches = 0
        bit_delta = 0
        windows = max(0, len(items) - 1)
        while index < len(items):
            if index + 1 < len(items):
                target = (items[index], items[index + 1])
                seed = FIXED_UNIVERSE.get(target)
                if seed is not None:
                    replacement = rec(seed)
                    if decodes_to_literals(replacement) is not None:
                        replaced_bits = len(span_bits(target))
                        record_bits = len(item_bits(replacement))
                        if record_bits < replaced_bits:
                            out.append(replacement)
                            matches += 1
                            bit_delta += replaced_bits - record_bits
                            index += 2
                            continue
            out.append(items[index])
            index += 1
        items = tuple(out)
        stats.append(ChurnStat(pass_index, len(items), windows, matches, bit_delta))
        if matches == 0:
            break
    return ChurnEncoded(items, tuple(stats))


def target_refresh_demo(trials: int = 200, n_blocks: int = 96, passes: int = 12) -> None:
    print("== family 2: target refresh without salt refresh ==")
    print("Fixed seed expansions are used forever; no pass salt and no birth")
    print("metadata are needed. Decode recursively opens records in place.")
    print()
    rng = Random(123)
    rows: dict[int, list[ChurnStat]] = {p: [] for p in range(1, passes + 1)}
    final_wrapped_gain: list[int] = []
    final_payload_gain: list[int] = []
    completed = 0
    for _ in range(trials):
        values = tuple(rng.randrange(1 << CHURN_B) for _ in range(n_blocks))
        encoded = encode_fixed_churn(values, passes)
        decoded = decode_fixed_stream(encoded.final_items)
        assert decoded == values
        raw_payload_bits = len(values) * CHURN_B
        raw_wrapped_bits = len(values) * (1 + CHURN_B)
        final_bits = sum(len(item_bits(item)) for item in encoded.final_items)
        final_wrapped_gain.append(raw_wrapped_bits - final_bits)
        final_payload_gain.append(raw_payload_bits - final_bits)
        completed += 1
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(f"toy grammar: literal={1 + CHURN_B} bits record={2 + CHURN_SEED_BITS} bits")
    print(f"fixed valid two-item universe size={len(FIXED_UNIVERSE)} seeds={CHURN_SEED_COUNT}")
    print(f"round_trips={completed}/{trials}")
    print(f"{'pass':>4} {'avg windows':>12} {'avg matches':>12} "
          f"{'hit/window':>11} {'avg gain':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_windows = mean(stat.windows for stat in stats)
        avg_matches = mean(stat.matches for stat in stats)
        hit_rate = avg_matches / avg_windows if avg_windows else 0.0
        avg_gain = mean(stat.bit_delta for stat in stats)
        print(f"{pass_index:4d} {avg_windows:12.2f} {avg_matches:12.3f} "
              f"{hit_rate:11.5f} {avg_gain:10.3f}")
    print(f"mean final wrapped-bit gain={mean(final_wrapped_gain):.3f} bits")
    print(f"mean final original-payload gain={mean(final_payload_gain):.3f} bits")
    print()
    print("Reading: target churn gives a stateless fixed-universe codec, but")
    print("the later-pass supply is whatever new adjacent item tuples land in")
    print("the same finite expansion set. In this random toy it decays rather")
    print("than stabilizing into a maintained match rate.")
    print()


FLEX_B = 4
FLEX_SEED_BITS = 8
FLEX_SEED_COUNT = 1 << FLEX_SEED_BITS
FLEX_ARITIES = (2, 3, 4, 5)


@dataclass(frozen=True, order=True)
class FlexItem:
    kind: str
    value: int
    arity: int = 0


def flex_lit(value: int) -> FlexItem:
    return FlexItem("L", value)


def flex_rec(arity: int, seed: int) -> FlexItem:
    return FlexItem("R", seed, arity)


def flex_item_bits(item: FlexItem) -> str:
    if item.kind == "L":
        return "0" + format(item.value, f"0{FLEX_B}b")
    if item.kind == "R":
        return "10" + format(item.arity - 2, "02b") + format(item.value, f"0{FLEX_SEED_BITS}b")
    raise ValueError(item)


def flex_span_bits(span: tuple[FlexItem, ...]) -> str:
    return "".join(flex_item_bits(item) for item in span)


def flex_parse_one(bits: str, offset: int) -> tuple[FlexItem, int] | None:
    if offset >= len(bits):
        return None
    if bits[offset] == "0":
        end = offset + 1 + FLEX_B
        if end > len(bits):
            return None
        return flex_lit(int(bits[offset + 1:end], 2)), end
    if bits.startswith("10", offset):
        meta_end = offset + 4
        end = meta_end + FLEX_SEED_BITS
        if end > len(bits):
            return None
        arity = 2 + int(bits[offset + 2:meta_end], 2)
        return flex_rec(arity, int(bits[meta_end:end], 2)), end
    return None


def flex_parse_items(bits: str, count: int) -> tuple[FlexItem, ...] | None:
    out: list[FlexItem] = []
    offset = 0
    for _ in range(count):
        parsed = flex_parse_one(bits, offset)
        if parsed is None:
            return None
        item, offset = parsed
        out.append(item)
    return tuple(out)


def flex_expansion(arity: int, seed: int) -> tuple[FlexItem, ...] | None:
    return flex_parse_items(hash_bits("fixed-flex-universe", arity, seed, n_bits=160), arity)


def build_flex_universe() -> dict[int, dict[tuple[FlexItem, ...], int]]:
    by_arity: dict[int, dict[tuple[FlexItem, ...], int]] = {arity: {} for arity in FLEX_ARITIES}
    for arity in FLEX_ARITIES:
        for seed in range(FLEX_SEED_COUNT):
            expanded = flex_expansion(arity, seed)
            if expanded is None:
                continue
            if any(item.kind == "R" and item.value == seed and item.arity == arity for item in expanded):
                continue
            by_arity[arity].setdefault(expanded, seed)
    return by_arity


FLEX_UNIVERSE = build_flex_universe()


def flex_decodes_to_literals(item: FlexItem, stack: tuple[tuple[int, int], ...] = ()) -> tuple[int, ...] | None:
    if item.kind == "L":
        return (item.value,)
    key = (item.arity, item.value)
    if key in stack:
        return None
    expanded = flex_expansion(item.arity, item.value)
    if expanded is None:
        return None
    out: list[int] = []
    for child in expanded:
        decoded = flex_decodes_to_literals(child, (*stack, key))
        if decoded is None:
            return None
        out.extend(decoded)
    return tuple(out)


def flex_decode_stream(items: tuple[FlexItem, ...]) -> tuple[int, ...]:
    out: list[int] = []
    for item in items:
        decoded = flex_decodes_to_literals(item)
        if decoded is None:
            raise RuntimeError(f"undecodable flex item {item}")
        out.extend(decoded)
    return tuple(out)


@dataclass
class FlexChurnStat:
    pass_index: int
    before_len: int
    windows: int
    matches: int
    by_arity: tuple[int, int, int, int]
    bit_delta: int


@dataclass
class FlexChurnEncoded:
    final_items: tuple[FlexItem, ...]
    stats: tuple[FlexChurnStat, ...]


def encode_fixed_flex_churn(values: tuple[int, ...], passes: int) -> FlexChurnEncoded:
    items = tuple(flex_lit(value) for value in values)
    stats: list[FlexChurnStat] = []
    for pass_index in range(1, passes + 1):
        out: list[FlexItem] = []
        index = 0
        matches = 0
        by_arity = {arity: 0 for arity in FLEX_ARITIES}
        bit_delta = 0
        windows = sum(max(0, len(items) - arity + 1) for arity in FLEX_ARITIES)
        while index < len(items):
            accepted = False
            for arity in reversed(FLEX_ARITIES):
                if index + arity > len(items):
                    continue
                target = items[index:index + arity]
                seed = FLEX_UNIVERSE[arity].get(target)
                if seed is None:
                    continue
                replacement = flex_rec(arity, seed)
                if flex_decodes_to_literals(replacement) is None:
                    continue
                replaced_bits = len(flex_span_bits(target))
                record_bits = len(flex_item_bits(replacement))
                if record_bits < replaced_bits:
                    out.append(replacement)
                    matches += 1
                    by_arity[arity] += 1
                    bit_delta += replaced_bits - record_bits
                    index += arity
                    accepted = True
                    break
            if not accepted:
                out.append(items[index])
                index += 1
        items = tuple(out)
        stats.append(
            FlexChurnStat(
                pass_index,
                len(items),
                windows,
                matches,
                tuple(by_arity[arity] for arity in FLEX_ARITIES),
                bit_delta,
            )
        )
        if matches == 0:
            break
    return FlexChurnEncoded(items, tuple(stats))


def target_refresh_flex_demo(trials: int = 200, n_blocks: int = 96, passes: int = 12) -> None:
    print("== family 2b: fixed-universe target refresh with arity 2-5 ==")
    print("This mutation tests effective-length migration: once records exist,")
    print("later targets may be record/literal or record/record spans under the")
    print("same fixed seed universe. No pass salt or birth channel is used.")
    print()
    rng = Random(456)
    rows: dict[int, list[FlexChurnStat]] = {p: [] for p in range(1, passes + 1)}
    payload_gain: list[int] = []
    wrapped_gain: list[int] = []
    for _ in range(trials):
        values = tuple(rng.randrange(1 << FLEX_B) for _ in range(n_blocks))
        encoded = encode_fixed_flex_churn(values, passes)
        assert flex_decode_stream(encoded.final_items) == values
        raw_payload_bits = len(values) * FLEX_B
        raw_wrapped_bits = len(values) * (1 + FLEX_B)
        final_bits = sum(len(flex_item_bits(item)) for item in encoded.final_items)
        payload_gain.append(raw_payload_bits - final_bits)
        wrapped_gain.append(raw_wrapped_bits - final_bits)
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(f"toy grammar: literal={1 + FLEX_B} bits record={4 + FLEX_SEED_BITS} bits")
    print("valid fixed-universe spans by arity:",
          ", ".join(f"a{arity}={len(FLEX_UNIVERSE[arity])}" for arity in FLEX_ARITIES))
    print(f"{'pass':>4} {'avg windows':>12} {'avg matches':>12} {'hit/window':>11} "
          f"{'avg gain':>10} {'a2/a3/a4/a5':>17}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_windows = mean(stat.windows for stat in stats)
        avg_matches = mean(stat.matches for stat in stats)
        avg_by_arity = [mean(stat.by_arity[i] for stat in stats) for i in range(len(FLEX_ARITIES))]
        hit_rate = avg_matches / avg_windows if avg_windows else 0.0
        avg_gain = mean(stat.bit_delta for stat in stats)
        arity_text = "/".join(f"{value:.2f}" for value in avg_by_arity)
        print(f"{pass_index:4d} {avg_windows:12.2f} {avg_matches:12.3f} {hit_rate:11.5f} "
              f"{avg_gain:10.3f} {arity_text:>17}")
    print(f"mean final wrapped-bit gain={mean(wrapped_gain):.3f} bits")
    print(f"mean final original-payload gain={mean(payload_gain):.3f} bits")
    print()
    print("Reading: arity variation creates a few later record-containing")
    print("targets, but it still does not stabilize random/unshaped match")
    print("supply or beat original payload accounting in this finite model.")
    print()


# ---------------------------------------------------------------------------
# Family 2c: full-cover bundle lattice without pass/birth tags.

LATTICE_BLOCK_BITS = 3
LATTICE_BLOCKS = 72
LATTICE_MAX_ARITY = 6
LATTICE_BOOK_CACHE: dict[tuple[int, int, int, int], dict[int, dict[str, int]]] = {}


def lattice_expand(arity: int, seed: int) -> str:
    return hash_bits("full-cover-bundle-lattice", arity, seed,
                     n_bits=arity * LATTICE_BLOCK_BITS)


def build_lattice_books(
    block_bits: int,
    max_arity: int,
    arity_bits: int,
    net_save_per_record: int,
) -> dict[int, dict[str, int]]:
    key = (block_bits, max_arity, arity_bits, net_save_per_record)
    cached = LATTICE_BOOK_CACHE.get(key)
    if cached is not None:
        return cached

    gross_gap = arity_bits + net_save_per_record
    books: dict[int, dict[str, int]] = {}
    for arity in range(1, max_arity + 1):
        span_bits = arity * block_bits
        seed_bits = span_bits - gross_gap
        if seed_bits < 0:
            books[arity] = {}
            continue
        book: dict[str, int] = {}
        for seed in range(1 << seed_bits):
            book.setdefault(lattice_expand(arity, seed), seed)
        books[arity] = book
    LATTICE_BOOK_CACHE[key] = books
    return books


@dataclass(frozen=True)
class LatticeRecord:
    arity: int
    seed: int


@dataclass(frozen=True)
class LatticeCoverStat:
    net_save_per_record: int
    covered: bool
    records: int
    charged_bits: int
    raw_bits: int


def encode_full_cover_lattice(
    bits: str,
    net_save_per_record: int,
    max_arity: int = LATTICE_MAX_ARITY,
) -> tuple[tuple[LatticeRecord, ...] | None, LatticeCoverStat]:
    if len(bits) % LATTICE_BLOCK_BITS:
        raise ValueError("lattice input must align to toy blocks")
    blocks = len(bits) // LATTICE_BLOCK_BITS
    arity_bits = ceil(log2(max_arity))
    books = build_lattice_books(LATTICE_BLOCK_BITS, max_arity, arity_bits, net_save_per_record)

    best: list[float] = [float("inf")] * (blocks + 1)
    paths: list[tuple[LatticeRecord, ...] | None] = [None] * (blocks + 1)
    best[0] = 0.0
    paths[0] = ()
    for start in range(blocks):
        if paths[start] is None:
            continue
        for arity in range(1, max_arity + 1):
            end = start + arity
            if end > blocks:
                continue
            target = bits[start * LATTICE_BLOCK_BITS:end * LATTICE_BLOCK_BITS]
            seed = books[arity].get(target)
            if seed is None:
                continue
            edge_cost = arity * LATTICE_BLOCK_BITS - net_save_per_record
            candidate = best[start] + edge_cost
            if candidate < best[end]:
                best[end] = candidate
                paths[end] = (*paths[start], LatticeRecord(arity, seed))

    path = paths[blocks]
    raw_bits = len(bits)
    if path is None:
        return None, LatticeCoverStat(net_save_per_record, False, 0, raw_bits, raw_bits)
    charged_bits = int(best[blocks])
    return path, LatticeCoverStat(net_save_per_record, True, len(path), charged_bits, raw_bits)


def decode_full_cover_lattice(records: tuple[LatticeRecord, ...]) -> str:
    return "".join(lattice_expand(record.arity, record.seed) for record in records)


def expected_lattice_cover_count(blocks: int, max_arity: int, net_save_per_record: int) -> float:
    arity_bits = ceil(log2(max_arity))
    gross_gap = arity_bits + net_save_per_record
    if gross_gap < 0:
        return float("inf")
    hit_p = 2.0 ** (-gross_gap)
    expected = [0.0] * (blocks + 1)
    expected[0] = 1.0
    for total in range(1, blocks + 1):
        expected[total] = sum(expected[total - arity] * hit_p
                              for arity in range(1, min(max_arity, total) + 1))
    return expected[blocks]


def full_cover_bundle_lattice_demo(trials: int = 200) -> None:
    print("== family 2c: full-cover bundle lattice without pass tags ==")
    print("This mutation takes the user's all-block-replacement idea literally:")
    print("every output unit is a seed record, so the decoder never needs a")
    print("birth pass or open/carry bitmap. The encoder searches every interval")
    print("up to max arity and runs a shortest-path cover over exact seed hits.")
    print()
    rng = Random(424242)
    arity_bits = ceil(log2(LATTICE_MAX_ARITY))
    raw_bits = LATTICE_BLOCKS * LATTICE_BLOCK_BITS
    print(f"exact toy: block={LATTICE_BLOCK_BITS} bits blocks={LATTICE_BLOCKS} "
          f"max_arity={LATTICE_MAX_ARITY} arity_bits={arity_bits}")
    print("net/record is after paying the arity header. Negative rows are")
    print("intentional bloat rows: they ask how much overpayment is needed to")
    print("make a full all-record cover appear.")
    print(f"{'net/rec':>7} {'gross d':>7} {'cover%':>8} {'records':>9} "
          f"{'charged':>9} {'net bits':>9} {'E covers':>11}")
    for net_save in [-2, -1, 0, 1, 2, 3]:
        stats: list[LatticeCoverStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(raw_bits), f"0{raw_bits}b")
            records, stat = encode_full_cover_lattice(bits, net_save)
            if records is not None:
                assert decode_full_cover_lattice(records) == bits
            stats.append(stat)
        covered = [stat for stat in stats if stat.covered]
        cover_rate = len(covered) / trials
        avg_records = mean(stat.records for stat in covered) if covered else 0.0
        avg_charged = mean(stat.charged_bits for stat in covered) if covered else float("nan")
        avg_net = mean(stat.raw_bits - stat.charged_bits for stat in covered) if covered else float("nan")
        expected_covers = expected_lattice_cover_count(LATTICE_BLOCKS, LATTICE_MAX_ARITY, net_save)
        print(f"{net_save:7d} {arity_bits + net_save:7d} {cover_rate:8.3f} "
              f"{avg_records:9.3f} {avg_charged:9.3f} {avg_net:9.3f} "
              f"{expected_covers:11.3e}")
    print()
    print("Closed-form seed-depth tradeoff for 3-byte base blocks with one")
    print("3-byte seed table reused across longer bundles:")
    print(f"{'arity':>6} {'target bits':>11} {'hit/window':>13} "
          f"{'gross before hdr':>16}")
    base_bits = 24
    seed_bits = 24
    for arity in [1, 2, 3, 4, 5, 8, 16]:
        target_bits = arity * base_bits
        hit_p = 2.0 ** (seed_bits - target_bits)
        gross = target_bits - seed_bits
        print(f"{arity:6d} {target_bits:11d} {hit_p:13.3e} {gross:16d}")
    print()
    print("Reading: full replacement really removes the birth-pass channel,")
    print("but it replaces it with a full-cover tiling requirement. To save")
    print("s bits after the arity header, each candidate interval hits with")
    print("probability about 2^-(header+s). The expected number of profitable")
    print("complete covers is already tiny in the toy. Rows that can cover need")
    print("bloating records; rows that would compress do not produce a cover.")
    print("Longer bundles amortize headers, but their exact-match probability")
    print("falls by the same missing payload bits unless the stored seed grows")
    print("toward the full target length.")
    print()


# ---------------------------------------------------------------------------
# Family 2d: adaptive smallest-replacement full-cover lattice.

ADAPTIVE_BLOCK_BITS = 3
ADAPTIVE_BLOCKS = 48
ADAPTIVE_MAX_ARITY = 5
ADAPTIVE_EXTRA_SEED_BITS = 2
ADAPTIVE_BOOK_CACHE: dict[tuple[int, int, int], dict[int, dict[str, tuple[int, int]]]] = {}


def adaptive_lattice_expand(arity: int, seed_bits: int, seed: int) -> str:
    return hash_bits("adaptive-smallest-cover", arity, seed_bits, seed,
                     n_bits=arity * ADAPTIVE_BLOCK_BITS)


def build_adaptive_lattice_books(
    block_bits: int,
    max_arity: int,
    extra_seed_bits: int,
) -> dict[int, dict[str, tuple[int, int]]]:
    key = (block_bits, max_arity, extra_seed_bits)
    cached = ADAPTIVE_BOOK_CACHE.get(key)
    if cached is not None:
        return cached

    books: dict[int, dict[str, tuple[int, int]]] = {}
    for arity in range(1, max_arity + 1):
        max_seed_bits = arity * block_bits + extra_seed_bits
        book: dict[str, tuple[int, int]] = {}
        for seed_bits in range(max_seed_bits + 1):
            for seed in range(1 << seed_bits):
                out = adaptive_lattice_expand(arity, seed_bits, seed)
                current = book.get(out)
                if current is None or seed_bits < current[0]:
                    book[out] = (seed_bits, seed)
        books[arity] = book
    ADAPTIVE_BOOK_CACHE[key] = books
    return books


@dataclass(frozen=True)
class AdaptiveCoverRecord:
    arity: int
    seed_bits: int
    seed: int


@dataclass(frozen=True)
class AdaptiveCoverStat:
    charged_width_class: bool
    covered: bool
    records: int
    seed_bits: int
    arity_bits: int
    width_bits: int
    charged_bits: int
    raw_bits: int


def encode_adaptive_smallest_cover(
    bits: str,
    charge_width_class: bool,
) -> tuple[tuple[AdaptiveCoverRecord, ...] | None, AdaptiveCoverStat]:
    if len(bits) % ADAPTIVE_BLOCK_BITS:
        raise ValueError("adaptive lattice input must align to toy blocks")
    blocks = len(bits) // ADAPTIVE_BLOCK_BITS
    books = build_adaptive_lattice_books(
        ADAPTIVE_BLOCK_BITS,
        ADAPTIVE_MAX_ARITY,
        ADAPTIVE_EXTRA_SEED_BITS,
    )
    arity_bits_per_record = ceil(log2(ADAPTIVE_MAX_ARITY))
    max_seed_class = ADAPTIVE_MAX_ARITY * ADAPTIVE_BLOCK_BITS + ADAPTIVE_EXTRA_SEED_BITS
    width_bits_per_record = ceil(log2(max_seed_class + 1)) if charge_width_class else 0

    best: list[float] = [float("inf")] * (blocks + 1)
    paths: list[tuple[AdaptiveCoverRecord, ...] | None] = [None] * (blocks + 1)
    best[0] = 0.0
    paths[0] = ()
    for start in range(blocks):
        if paths[start] is None:
            continue
        for arity in range(1, ADAPTIVE_MAX_ARITY + 1):
            end = start + arity
            if end > blocks:
                continue
            target = bits[start * ADAPTIVE_BLOCK_BITS:end * ADAPTIVE_BLOCK_BITS]
            witness = books[arity].get(target)
            if witness is None:
                continue
            seed_bits, seed = witness
            edge_cost = arity_bits_per_record + width_bits_per_record + seed_bits
            candidate = best[start] + edge_cost
            if candidate < best[end]:
                best[end] = candidate
                paths[end] = (*paths[start], AdaptiveCoverRecord(arity, seed_bits, seed))

    raw_bits = len(bits)
    path = paths[blocks]
    if path is None:
        return None, AdaptiveCoverStat(
            charge_width_class,
            False,
            0,
            0,
            0,
            0,
            raw_bits,
            raw_bits,
        )
    record_count = len(path)
    seed_bit_total = sum(record.seed_bits for record in path)
    arity_bit_total = record_count * arity_bits_per_record
    width_bit_total = record_count * width_bits_per_record
    charged_bits = seed_bit_total + arity_bit_total + width_bit_total
    return path, AdaptiveCoverStat(
        charge_width_class,
        True,
        record_count,
        seed_bit_total,
        arity_bit_total,
        width_bit_total,
        charged_bits,
        raw_bits,
    )


def decode_adaptive_smallest_cover(records: tuple[AdaptiveCoverRecord, ...]) -> str:
    return "".join(adaptive_lattice_expand(record.arity, record.seed_bits, record.seed)
                   for record in records)


def min_seed_width_cdf(target_bits: int, seed_bits: int) -> float:
    draws = (1 << (seed_bits + 1)) - 1
    return -expm1(draws * log1p(-(2.0 ** -target_bits)))


def adaptive_smallest_cover_demo(trials: int = 200) -> None:
    print("== family 2d: adaptive smallest-replacement cover ==")
    print("This mutation lets every interval use the smallest seed width found")
    print("up to a bounded over-search limit, then chooses the cheapest full")
    print("all-record cover by dynamic programming. Bloating records are allowed")
    print("as bridge pieces, so bundles get a fair chance to beat bloating singles.")
    print()
    rng = Random(515151)
    raw_bits = ADAPTIVE_BLOCKS * ADAPTIVE_BLOCK_BITS
    arity_bits_per_record = ceil(log2(ADAPTIVE_MAX_ARITY))
    max_seed_class = ADAPTIVE_MAX_ARITY * ADAPTIVE_BLOCK_BITS + ADAPTIVE_EXTRA_SEED_BITS
    charged_width_bits = ceil(log2(max_seed_class + 1))
    print(f"exact toy: block={ADAPTIVE_BLOCK_BITS} bits blocks={ADAPTIVE_BLOCKS} "
          f"max_arity={ADAPTIVE_MAX_ARITY} arity_bits={arity_bits_per_record} "
          f"max_extra_seed={ADAPTIVE_EXTRA_SEED_BITS}")
    print(f"{'ledger':>13} {'cover%':>8} {'records':>9} {'seed':>9} "
          f"{'arity':>8} {'width':>8} {'charged':>9} {'net':>9}")
    for charge_width_class, label in [(False, "free-width"), (True, "width-paid")]:
        stats: list[AdaptiveCoverStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(raw_bits), f"0{raw_bits}b")
            records, stat = encode_adaptive_smallest_cover(bits, charge_width_class)
            if records is not None:
                assert decode_adaptive_smallest_cover(records) == bits
            stats.append(stat)
        covered = [stat for stat in stats if stat.covered]
        cover_rate = len(covered) / trials
        avg_records = mean(stat.records for stat in covered) if covered else 0.0
        avg_seed = mean(stat.seed_bits for stat in covered) if covered else 0.0
        avg_arity = mean(stat.arity_bits for stat in covered) if covered else 0.0
        avg_width = mean(stat.width_bits for stat in covered) if covered else 0.0
        avg_charged = mean(stat.charged_bits for stat in covered) if covered else float("nan")
        avg_net = mean(stat.raw_bits - stat.charged_bits for stat in covered) if covered else float("nan")
        print(f"{label:>13} {cover_rate:8.3f} {avg_records:9.3f} {avg_seed:9.3f} "
              f"{avg_arity:8.3f} {avg_width:8.3f} {avg_charged:9.3f} {avg_net:9.3f}")
    print()
    print("Closed-form smallest-seed CDF for a single L-bit target:")
    print(f"{'L bits':>7} {'seed bits':>9} {'Pr[min<=b]':>12} "
          f"{'free rec':>9} {'paid rec':>9}")
    for target_bits, seed_bits in [(24, 16), (24, 20), (24, 22), (24, 23),
                                   (24, 24), (48, 40), (120, 111)]:
        free_record = arity_bits_per_record + seed_bits
        paid_record = arity_bits_per_record + charged_width_bits + seed_bits
        print(f"{target_bits:7d} {seed_bits:9d} "
              f"{min_seed_width_cdf(target_bits, seed_bits):12.5f} "
              f"{free_record:9d} {paid_record:9d}")
    print()
    print("Reading: adaptive search does find all-record covers, and bundles")
    print("can reduce some bloating single choices. The invalid free-width")
    print("oracle is positive in this tiny exact toy, which confirms the")
    print("overlap-order-statistic effect. Once the decoder is told each")
    print("variable seed width, the same cover becomes strongly negative. The")
    print("search-depth coordinate has reappeared as seed address length plus")
    print("a seed-width class.")
    print()


# ---------------------------------------------------------------------------
# Family 2d2: recursive adaptive cover churn with no pass salt.

ADAPTIVE_RECURSIVE_PASSES = 6
ADAPTIVE_PAD_BITS_PER_LAYER = ceil(log2(ADAPTIVE_BLOCK_BITS))


@dataclass(frozen=True)
class AdaptiveRecursiveLayerStat:
    pass_index: int
    before_bits: int
    padded_bits: int
    after_bits: int
    records: int
    seed_bits: int
    arity_bits: int
    width_bits: int
    pad_bits: int
    compressive_records: int
    by_arity: tuple[int, ...]


@dataclass(frozen=True)
class AdaptiveRecursiveEncoded:
    final_bits: str
    pad_counts: tuple[int, ...]
    stats: tuple[AdaptiveRecursiveLayerStat, ...]
    original_bits: str


def adaptive_record_code_width_bits() -> int:
    max_seed_class = ADAPTIVE_MAX_ARITY * ADAPTIVE_BLOCK_BITS + ADAPTIVE_EXTRA_SEED_BITS
    return ceil(log2(max_seed_class + 1))


def adaptive_record_bits(record: AdaptiveCoverRecord) -> str:
    arity_bits = ceil(log2(ADAPTIVE_MAX_ARITY))
    width_bits = adaptive_record_code_width_bits()
    seed = "" if record.seed_bits == 0 else format(record.seed, f"0{record.seed_bits}b")
    return (
        format(record.arity - 1, f"0{arity_bits}b")
        + format(record.seed_bits, f"0{width_bits}b")
        + seed
    )


def serialize_adaptive_records(records: tuple[AdaptiveCoverRecord, ...]) -> str:
    return "".join(adaptive_record_bits(record) for record in records)


def parse_adaptive_record_stream(bits: str) -> tuple[AdaptiveCoverRecord, ...]:
    arity_bits = ceil(log2(ADAPTIVE_MAX_ARITY))
    width_bits = adaptive_record_code_width_bits()
    offset = 0
    records: list[AdaptiveCoverRecord] = []
    while offset < len(bits):
        header_end = offset + arity_bits + width_bits
        if header_end > len(bits):
            raise ValueError("truncated adaptive record header")
        arity = 1 + int(bits[offset:offset + arity_bits], 2)
        offset += arity_bits
        if arity < 1 or arity > ADAPTIVE_MAX_ARITY:
            raise ValueError("invalid adaptive arity")
        seed_bits = int(bits[offset:offset + width_bits], 2)
        offset += width_bits
        max_seed_bits = arity * ADAPTIVE_BLOCK_BITS + ADAPTIVE_EXTRA_SEED_BITS
        if seed_bits > max_seed_bits:
            raise ValueError("invalid adaptive seed width")
        seed_end = offset + seed_bits
        if seed_end > len(bits):
            raise ValueError("truncated adaptive seed")
        seed = int(bits[offset:seed_end], 2) if seed_bits else 0
        offset = seed_end
        records.append(AdaptiveCoverRecord(arity, seed_bits, seed))
    return tuple(records)


def encode_adaptive_recursive_cover(bits: str, passes: int) -> AdaptiveRecursiveEncoded:
    current = bits
    stats: list[AdaptiveRecursiveLayerStat] = []
    pad_counts: list[int] = []
    arity_bits = ceil(log2(ADAPTIVE_MAX_ARITY))
    width_bits = adaptive_record_code_width_bits()
    for pass_index in range(1, passes + 1):
        pad_count = (-len(current)) % ADAPTIVE_BLOCK_BITS
        target = current + ("0" * pad_count)
        records, stat = encode_adaptive_smallest_cover(target, charge_width_class=True)
        if records is None:
            break
        encoded_bits = serialize_adaptive_records(records)
        assert len(encoded_bits) == stat.charged_bits
        compressive_records = 0
        by_arity = [0] * ADAPTIVE_MAX_ARITY
        for record in records:
            raw_span = record.arity * ADAPTIVE_BLOCK_BITS
            code_len = arity_bits + width_bits + record.seed_bits
            if code_len < raw_span:
                compressive_records += 1
            by_arity[record.arity - 1] += 1
        pad_counts.append(pad_count)
        stats.append(
            AdaptiveRecursiveLayerStat(
                pass_index=pass_index,
                before_bits=len(current),
                padded_bits=len(target),
                after_bits=len(encoded_bits),
                records=len(records),
                seed_bits=stat.seed_bits,
                arity_bits=stat.arity_bits,
                width_bits=stat.width_bits,
                pad_bits=ADAPTIVE_PAD_BITS_PER_LAYER,
                compressive_records=compressive_records,
                by_arity=tuple(by_arity),
            )
        )
        current = encoded_bits
    return AdaptiveRecursiveEncoded(current, tuple(pad_counts), tuple(stats), bits)


def decode_adaptive_recursive_cover(encoded: AdaptiveRecursiveEncoded) -> str:
    current = encoded.final_bits
    for pad_count in reversed(encoded.pad_counts):
        records = parse_adaptive_record_stream(current)
        expanded = decode_adaptive_smallest_cover(records)
        if pad_count:
            if expanded[-pad_count:] != "0" * pad_count:
                raise ValueError("adaptive recursive pad mismatch")
            expanded = expanded[:-pad_count]
        current = expanded
    return current


def adaptive_recursive_cover_churn_demo(
    trials: int = 80,
    n_bits: int = ADAPTIVE_BLOCKS * ADAPTIVE_BLOCK_BITS,
    passes: int = ADAPTIVE_RECURSIVE_PASSES,
) -> None:
    print("== family 2d2: recursive adaptive cover churn without salt ==")
    print("Every pass covers the entire current bitstream with records from")
    print("the same fixed seed universe. There is no open/carry bitmap and no")
    print("birth-pass salt; target refresh comes only from serializing the")
    print("previous pass's record language. Alignment pad counts are charged")
    print("as an end-header field.")
    print()
    rng = Random(626262)
    rows: dict[int, list[AdaptiveRecursiveLayerStat]] = {
        pass_index: [] for pass_index in range(1, passes + 1)
    }
    final_bits: list[int] = []
    header_bits: list[int] = []
    completed = 0
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_adaptive_recursive_cover(bits, passes)
        assert decode_adaptive_recursive_cover(encoded) == bits
        completed += int(len(encoded.stats) == passes)
        final_bits.append(len(encoded.final_bits))
        header_bits.append(len(encoded.pad_counts) * ADAPTIVE_PAD_BITS_PER_LAYER + ceil(log2(passes + 1)))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(
        f"toy grammar: block={ADAPTIVE_BLOCK_BITS} maxA={ADAPTIVE_MAX_ARITY} "
        f"width_bits={adaptive_record_code_width_bits()} passes={passes} n_bits={n_bits}"
    )
    print(f"round_trips={trials}/{trials} completed_all_passes={completed}/{trials}")
    print(f"{'pass':>4} {'avg in':>8} {'avg pad':>7} {'avg out':>9} "
          f"{'ratio':>8} {'records':>8} {'cmp%':>8} {'a1/a2/a3/a4/a5':>18}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_in = mean(stat.before_bits for stat in stats)
        avg_padded = mean(stat.padded_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_records = mean(stat.records for stat in stats)
        avg_compressive = mean(
            stat.compressive_records / stat.records if stat.records else 0.0
            for stat in stats
        )
        avg_by_arity = [
            mean(stat.by_arity[index] for stat in stats)
            for index in range(ADAPTIVE_MAX_ARITY)
        ]
        arity_text = "/".join(f"{value:.1f}" for value in avg_by_arity)
        print(f"{pass_index:4d} {avg_in:8.2f} {avg_padded - avg_in:7.3f} "
              f"{avg_out:9.2f} {avg_out / avg_in:8.3f} {avg_records:8.2f} "
              f"{100.0 * avg_compressive:8.3f} {arity_text:>18}")
    avg_final = mean(final_bits)
    avg_header = mean(header_bits)
    print(f"mean final payload bits={avg_final:.3f}")
    print(f"mean charged end-header bits={avg_header:.3f}")
    print(f"mean total net vs original={n_bits - avg_final - avg_header:.3f} bits")
    print()
    print("Reading: this is the clean all-block-replaced version of target")
    print("churn. It decodes statelessly and needs no birth pass, but the")
    print("fixed record language is not a compression attractor. Each layer's")
    print("record stream is longer than its input, so target refresh amplifies")
    print("the one-pass width/address overhead instead of maintaining a")
    print("positive match rate.")
    print()


def elias_delta_length_from_log_rank(log_rank: float) -> int:
    floor_log = max(0, int(log_rank))
    return floor_log + 2 * int(log2(floor_log + 1)) + 1


def overlap_cover_gain_per_block(
    rng: Random,
    blocks: int,
    max_arity: int,
    block_bits: int,
    overhead_bits: float,
    rank_mode: str,
) -> float:
    best = [float("-inf")] * (blocks + 1)
    best[0] = 0.0
    for start in range(blocks):
        if best[start] == float("-inf"):
            continue
        for arity in range(1, max_arity + 1):
            end = start + arity
            if end > blocks:
                break
            target_bits = arity * block_bits
            exponential = rng.expovariate(1.0)
            log_rank = max(0.0, target_bits + log2(exponential))
            if rank_mode == "oracle-log-rank":
                rank_bits = log_rank
            elif rank_mode == "ideal-geometric":
                rank_bits = target_bits + (exponential / log(2))
            elif rank_mode == "delta-rank":
                rank_bits = elias_delta_length_from_log_rank(log_rank)
            else:
                raise ValueError(f"unknown rank mode {rank_mode}")
            gain = target_bits - overhead_bits - rank_bits
            candidate = best[start] + gain
            if candidate > best[end]:
                best[end] = candidate
    return best[blocks] / blocks


def estimate_overlap_gain(
    max_arity: int,
    overhead_bits: float,
    rank_mode: str,
    trials: int,
    blocks: int,
    block_bits: int,
) -> float:
    rng = Random(7000 + max_arity * 101 + int(overhead_bits * 1000) + len(rank_mode))
    return mean(
        overlap_cover_gain_per_block(
            rng,
            blocks,
            max_arity,
            block_bits,
            overhead_bits,
            rank_mode,
        )
        for _ in range(trials)
    )


def estimate_overlap_crossover(
    max_arity: int,
    rank_mode: str,
    trials: int,
    blocks: int,
    block_bits: int,
) -> float | None:
    if estimate_overlap_gain(max_arity, 0.0, rank_mode, trials, blocks, block_bits) <= 0.0:
        return None
    lo = 0.0
    hi = 8.0
    while estimate_overlap_gain(max_arity, hi, rank_mode, trials, blocks, block_bits) > 0.0:
        hi *= 2.0
        if hi > 64.0:
            return hi
    for _ in range(12):
        mid = (lo + hi) / 2.0
        if estimate_overlap_gain(max_arity, mid, rank_mode, trials, blocks, block_bits) > 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def overlap_option_crossover_demo(trials: int = 80, blocks: int = 600) -> None:
    print("== family 2e: overlapping-option seed-rank crossover ==")
    print("This is the user's 1+2+3+4+5 option model directly. For each")
    print("candidate interval, unlimited search gives a first matching seed")
    print("rank about Exp(1)*2^L for an L-bit target. A shortest-path cover")
    print("then chooses the best overlapping tiling. This is an optimistic")
    print("infinite-compute model: no interval is unavailable.")
    print()
    block_bits = 24
    print(f"asymptotic simulation: block={block_bits} bits, blocks={blocks}, trials={trials}")
    print(f"{'rank coding':>16} {'maxA':>5} {'opts/block':>10} "
          f"{'gain@h0':>9} {'gain@h3':>9} {'h crossover':>12}")
    for rank_mode in ["oracle-log-rank", "ideal-geometric", "delta-rank"]:
        for max_arity in [1, 2, 3, 5, 8]:
            options_per_block = max_arity * (max_arity + 1) // 2
            gain_h0 = estimate_overlap_gain(max_arity, 0.0, rank_mode, trials, blocks, block_bits)
            gain_h3 = estimate_overlap_gain(max_arity, 3.0, rank_mode, trials, blocks, block_bits)
            crossover = estimate_overlap_crossover(max_arity, rank_mode, trials // 2, blocks, block_bits)
            crossover_text = "none" if crossover is None else f"{crossover:12.3f}"
            print(f"{rank_mode:>16} {max_arity:5d} {options_per_block:10d} "
                  f"{gain_h0:9.3f} {gain_h3:9.3f} {crossover_text:>12}")
    print()
    print("Reading: the overlap intuition is real under an invalid oracle")
    print("ledger. With max arity 5, the 15 options per interior block push")
    print("the free log-rank crossover to roughly 4 overhead bits/record, so")
    print("a 3-bit header appears positive. But that ledger assumes the decoder")
    print("knows where the variable seed-rank field ends for free. Even an")
    print("ideal arithmetic code for the geometric first-hit rank distribution")
    print("stays negative; a universal self-delimiting integer code is worse.")
    print("The missing channel is not the 5-block target length; it is the")
    print("seed-rank witness length/terminator.")
    print()


def search_hit_probability(search_bits: float, target_bits: int) -> float:
    exponent = search_bits - target_bits
    if exponent > 12:
        return 1.0
    if exponent < -60:
        return 2.0 ** exponent
    return -expm1(-(2.0 ** exponent))


def finite_depth_cover_stats(
    max_arity: int,
    search_bits: float,
    trials: int,
    blocks: int,
    block_bits: int,
    overhead_bits: float,
) -> tuple[float, float, float, float, float, float, float]:
    rng = Random(9090 + max_arity * 17 + int(search_bits * 100))
    covered = 0
    oracle_gain = 0.0
    fixed_gain = 0.0
    selected_symbols: list[tuple[int, int]] = []
    lower_rank_bits = 0
    selected_records = 0
    for _ in range(trials):
        edge_log_rank: dict[tuple[int, int], tuple[float, int]] = {}
        for start in range(blocks):
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > blocks:
                    break
                target_bits = arity * block_bits
                exponential = rng.expovariate(1.0)
                log_rank = max(0.0, target_bits + log2(exponential))
                if log_rank <= search_bits:
                    edge_log_rank[(start, arity)] = (log_rank, max(0, int(log_rank)))

        best_oracle = [float("-inf")] * (blocks + 1)
        best_fixed = [float("-inf")] * (blocks + 1)
        previous: list[tuple[int, int] | None] = [None] * (blocks + 1)
        best_oracle[0] = 0.0
        best_fixed[0] = 0.0
        for start in range(blocks):
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > blocks:
                    break
                info = edge_log_rank.get((start, arity))
                if info is None:
                    continue
                target_bits = arity * block_bits
                log_rank, _ = info
                if best_oracle[start] != float("-inf"):
                    candidate = best_oracle[start] + target_bits - overhead_bits - log_rank
                    if candidate > best_oracle[end]:
                        best_oracle[end] = candidate
                        previous[end] = (start, arity)
                if best_fixed[start] != float("-inf"):
                    candidate = best_fixed[start] + target_bits - overhead_bits - search_bits
                    if candidate > best_fixed[end]:
                        best_fixed[end] = candidate

        if best_oracle[blocks] == float("-inf"):
            continue
        covered += 1
        oracle_gain += best_oracle[blocks]
        if best_fixed[blocks] != float("-inf"):
            fixed_gain += best_fixed[blocks]

        cursor = blocks
        while cursor > 0:
            prev = previous[cursor]
            if prev is None:
                raise RuntimeError("finite-depth oracle cover traceback failed")
            start, arity = prev
            _, log_bin = edge_log_rank[(start, arity)]
            selected_symbols.append((arity, log_bin))
            lower_rank_bits += log_bin
            selected_records += 1
            cursor = start

    raw_bits = trials * blocks * block_bits
    if not selected_symbols:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    symbol_counts = Counter(selected_symbols)
    total_symbols = len(selected_symbols)
    symbol_entropy = -sum(
        (count / total_symbols) * log2(count / total_symbols)
        for count in symbol_counts.values()
    )
    model_bits = total_symbols * symbol_entropy + lower_rank_bits
    lower_bound_gain = (covered * blocks * block_bits - model_bits) / (trials * blocks)
    marker_gain = (
        covered * blocks * block_bits
        - model_bits
        - selected_records * overhead_bits
    ) / (trials * blocks)
    return (
        covered / trials,
        oracle_gain / (trials * blocks),
        lower_bound_gain,
        marker_gain,
        fixed_gain / (trials * blocks),
        selected_records / (trials * blocks),
        symbol_entropy + (lower_rank_bits / total_symbols),
    )


def finite_search_depth_crossover_demo(trials: int = 80, blocks: int = 600) -> None:
    print("== family 2e2: finite-depth overlapping cover crossover ==")
    print("This is the same 15-option interval-cover model, but with a finite")
    print("global search depth. 'Search 15 bytes' means every interval may use")
    print("the first seed rank <= 120 bits; shorter intervals usually have")
    print("matches, while 5-block intervals hit with probability about 63.2%.")
    print("The DP chooses the cheapest full cover after seeing all intervals.")
    print()
    block_bits = 24
    max_arity = 5
    overhead_bits = 3.0
    target_bits = block_bits * max_arity
    print(
        f"finite search simulation: block={block_bits} bits, maxA={max_arity}, "
        f"opts/block=15, blocks={blocks}, trials={trials}, h={overhead_bits:g}"
    )
    print(
        f"{'search':>7} {'p(a4)':>8} {'p(a5)':>8} {'cover%':>8} {'oracle':>9} "
        f"{'sel LB':>9} {'sel+h':>9} {'fixedW':>9} {'rec/bl':>8} {'bits/rec':>9}"
    )
    for search_bits in [72, 80, 88, 92, 96, 104, 112, 116, 120, 122, 128]:
        cover, oracle_gain, lower_gain, marker_gain, fixed_gain, rec_per_block, bits_per_rec = (
            finite_depth_cover_stats(
                max_arity,
                float(search_bits),
                trials,
                blocks,
                block_bits,
                overhead_bits,
            )
        )
        p4 = search_hit_probability(float(search_bits), block_bits * 4)
        p5 = search_hit_probability(float(search_bits), target_bits)
        print(
            f"{search_bits:7d} {p4:8.5f} {p5:8.5f} {100.0 * cover:8.3f} "
            f"{oracle_gain:9.3f} {lower_gain:9.3f} {marker_gain:9.3f} "
            f"{fixed_gain:9.3f} {rec_per_block:8.3f} {bits_per_rec:9.3f}"
        )
    print()
    print("Reading: finite depth does produce the crossover under the free")
    print("log-rank oracle. In this scale, the crossing starts before 15")
    print("bytes: around 92-96 search bits, because 3-block intervals are")
    print("saturated and 4-block intervals begin to supply enough overlap.")
    print("The 120-bit/15-byte row is near the asymptotic 15-option gain.")
    print("But a fixed 120-bit field is parseable")
    print("and very negative, while the selected-rank lower bound still loses")
    print("after coding the exact witness rank. The point that crosses is the")
    print("unpaid witness-length oracle, not a stateless Telomere record.")
    print()


def finite_block_option_coupling_stats(
    max_arity: int,
    search_bits: float,
    trials: int,
    blocks: int,
    block_bits: int,
    overhead_bits: float,
) -> tuple[float, float, float, float, float, float, float, float]:
    """Measure the user's per-block best option against legal cover coupling."""
    rng = Random(9440 + max_arity * 23 + int(search_bits * 100))
    hit_options = 0
    positive_options = 0
    local_upper_gain = 0.0
    legal_oracle_gain = 0.0
    selected_symbols: list[tuple[int, int]] = []
    lower_rank_bits = 0
    selected_records = 0
    covered = 0
    for _ in range(trials):
        edge_log_rank: dict[tuple[int, int], tuple[float, int, float]] = {}
        local_best = [float("-inf")] * blocks
        for start in range(blocks):
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > blocks:
                    break
                target_bits = arity * block_bits
                exponential = rng.expovariate(1.0)
                log_rank = max(0.0, target_bits + log2(exponential))
                if log_rank > search_bits:
                    continue
                interval_gain = target_bits - overhead_bits - log_rank
                edge_log_rank[(start, arity)] = (
                    log_rank,
                    max(0, int(log_rank)),
                    interval_gain,
                )
                hit_options += arity
                if interval_gain > 0.0:
                    positive_options += arity
                per_block_gain = interval_gain / arity
                for block in range(start, end):
                    if per_block_gain > local_best[block]:
                        local_best[block] = per_block_gain

        # The local ledger lets every block pick its own cheapest containing
        # interval. It is an upper bound because neighboring choices can clash.
        local_upper_gain += sum(
            0.0 if gain == float("-inf") else gain
            for gain in local_best
        )

        best = [float("-inf")] * (blocks + 1)
        previous: list[tuple[int, int] | None] = [None] * (blocks + 1)
        best[0] = 0.0
        for start in range(blocks):
            if best[start] == float("-inf"):
                continue
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > blocks:
                    break
                info = edge_log_rank.get((start, arity))
                if info is None:
                    continue
                _, _, interval_gain = info
                candidate = best[start] + interval_gain
                if candidate > best[end]:
                    best[end] = candidate
                    previous[end] = (start, arity)

        if best[blocks] == float("-inf"):
            continue
        covered += 1
        legal_oracle_gain += best[blocks]
        cursor = blocks
        while cursor > 0:
            prev = previous[cursor]
            if prev is None:
                raise RuntimeError("finite block option traceback failed")
            start, arity = prev
            _, log_bin, _ = edge_log_rank[(start, arity)]
            selected_symbols.append((arity, log_bin))
            lower_rank_bits += log_bin
            selected_records += 1
            cursor = start

    denominator = trials * blocks
    if not selected_symbols:
        return (
            hit_options / denominator,
            positive_options / denominator,
            local_upper_gain / denominator,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
    symbol_counts = Counter(selected_symbols)
    total_symbols = len(selected_symbols)
    symbol_entropy = -sum(
        (count / total_symbols) * log2(count / total_symbols)
        for count in symbol_counts.values()
    )
    model_bits = total_symbols * symbol_entropy + lower_rank_bits
    lower_bound_gain = (covered * blocks * block_bits - model_bits) / denominator
    marker_gain = (
        covered * blocks * block_bits
        - model_bits
        - selected_records * overhead_bits
    ) / denominator
    return (
        hit_options / denominator,
        positive_options / denominator,
        local_upper_gain / denominator,
        legal_oracle_gain / denominator,
        lower_bound_gain,
        marker_gain,
        selected_records / denominator,
        covered / trials,
    )


def block_option_coupling_crossover_demo(trials: int = 80, blocks: int = 600) -> None:
    print("== family 2e3: block-local 15-option crossover and cover coupling ==")
    print("This is the block-centered version of the overlap idea. An interior")
    print("block has 1 single, 2 two-block intervals, 3 three-block intervals,")
    print("4 four-block intervals, and 5 five-block intervals containing it.")
    print("The local column lets each block independently choose its cheapest")
    print("containing interval. The legal column forces neighboring choices to")
    print("agree on one non-overlapping full cover, then prices the selected")
    print("rank witnesses.")
    print()
    block_bits = 24
    max_arity = 5
    overhead_bits = 3.0
    print(
        f"finite search simulation: block={block_bits} bits, maxA={max_arity}, "
        f"opts/block=15, blocks={blocks}, trials={trials}, h={overhead_bits:g}"
    )
    print(
        f"{'search':>7} {'hit opt':>8} {'pos opt':>8} {'local UB':>9} "
        f"{'legal':>9} {'sel LB':>9} {'sel+h':>9} {'rec/bl':>8} {'cover%':>8}"
    )
    for search_bits in [72, 80, 88, 92, 96, 104, 112, 116, 120, 122, 128]:
        (
            hit_options,
            positive_options,
            local_upper,
            legal_oracle,
            lower_gain,
            marker_gain,
            rec_per_block,
            cover,
        ) = finite_block_option_coupling_stats(
            max_arity,
            float(search_bits),
            trials,
            blocks,
            block_bits,
            overhead_bits,
        )
        print(
            f"{search_bits:7d} {hit_options:8.3f} {positive_options:8.3f} "
            f"{local_upper:9.3f} {legal_oracle:9.3f} {lower_gain:9.3f} "
            f"{marker_gain:9.3f} {rec_per_block:8.3f} {100.0 * cover:8.3f}"
        )
    print()
    print("Reading: the block-local best-of-15 intuition is valid as an")
    print("optimistic upper bound, and it crosses earlier than a 15-byte")
    print("full-bundle-only framing. The legal cover stays close enough to show")
    print("the overlap effect is real, not a mirage. But the positive columns")
    print("are exactly the columns where the decoder is being handed the chosen")
    print("rank boundary for free. Once the selected witness is encoded, the")
    print("same rows remain negative.")
    print()


def expected_containing_interval_counts(
    max_arity: int,
    search_bits: float,
    block_bits: int,
    overhead_bits: float,
) -> tuple[float, float]:
    """Closed-form interior-block option counts for the finite-depth model."""
    finite_options = 0.0
    positive_options = 0.0
    for arity in range(1, max_arity + 1):
        target_bits = arity * block_bits
        finite_options += arity * search_hit_probability(search_bits, target_bits)
        positive_threshold = min(search_bits, target_bits - overhead_bits)
        if positive_threshold >= 0.0:
            positive_options += arity * search_hit_probability(positive_threshold, target_bits)
    return finite_options, positive_options


def direct_15_option_crossover_demo(trials: int = 80, blocks: int = 600) -> None:
    print("== family 2e4: direct 15-option crossover calculation ==")
    print("This is the crossover question in the user's block-centered terms.")
    print("A 3-byte block has 15 containing intervals when max arity is 5:")
    print("one single, two pairs, three triples, four quads, and five quints.")
    print("For an N-bit search cap, an arity-a interval exists with probability")
    print("1-exp(-2^(N-24a)). A compressive oracle interval additionally needs")
    print("log2(rank) < 24a-h. The DP column is the legal non-overlapping cover.")
    print()
    block_bits = 24
    max_arity = 5
    overhead_bits = 3.0
    print(
        f"finite search calculation: block={block_bits} bits, maxA={max_arity}, "
        f"opts/block=15, blocks={blocks}, trials={trials}, h={overhead_bits:g}"
    )
    print(
        f"{'search':>7} {'E finite':>9} {'E pos':>8} {'local UB':>9} "
        f"{'DP oracle':>9} {'sel LB':>9} {'sel+h':>9} {'rec/bl':>8}"
    )
    for search_bits in [72, 88, 92, 96, 104, 116, 120, 122, 128]:
        expected_finite, expected_positive = expected_containing_interval_counts(
            max_arity,
            float(search_bits),
            block_bits,
            overhead_bits,
        )
        (
            _hit_options,
            _positive_options,
            local_upper,
            legal_oracle,
            lower_gain,
            marker_gain,
            rec_per_block,
            _cover,
        ) = finite_block_option_coupling_stats(
            max_arity,
            float(search_bits),
            trials,
            blocks,
            block_bits,
            overhead_bits,
        )
        print(
            f"{search_bits:7d} {expected_finite:9.3f} {expected_positive:8.3f} "
            f"{local_upper:9.3f} {legal_oracle:9.3f} {lower_gain:9.3f} "
            f"{marker_gain:9.3f} {rec_per_block:8.3f}"
        )
    print()
    print("Reading: this is the calculation the fixed-bundle argument misses.")
    print("At 120 search bits, an interior block expects about 13 finite")
    print("matching containing intervals and about 1.76 individually")
    print("compressive containing intervals. The legal cover is still positive")
    print("under the free log-rank oracle, so the best-of-overlaps crossover is")
    print("real. It is not yet a stateless codec, because the negative selected")
    print("rank lower-bound columns are the bill for telling the decoder which")
    print("exact seed witness was chosen.")
    print()


def selected_rank_entropy_stats(
    max_arity: int,
    trials: int,
    blocks: int,
    block_bits: int,
    overhead_bits: float,
) -> tuple[float, float, float, float, float]:
    rng = Random(8080 + max_arity)
    selected_symbols: list[tuple[int, int]] = []
    lower_rank_bits = 0
    selected_records = 0
    oracle_gain = 0.0
    raw_bits = trials * blocks * block_bits
    for _ in range(trials):
        edge_log_rank: dict[tuple[int, int], tuple[float, int]] = {}
        best = [float("-inf")] * (blocks + 1)
        previous: list[tuple[int, int] | None] = [None] * (blocks + 1)
        best[0] = 0.0
        for start in range(blocks):
            if best[start] == float("-inf"):
                continue
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > blocks:
                    break
                target_bits = arity * block_bits
                exponential = rng.expovariate(1.0)
                log_rank = max(0.0, target_bits + log2(exponential))
                log_bin = max(0, int(log_rank))
                edge_log_rank[(start, arity)] = (log_rank, log_bin)
                gain = target_bits - overhead_bits - log_rank
                candidate = best[start] + gain
                if candidate > best[end]:
                    best[end] = candidate
                    previous[end] = (start, arity)
        oracle_gain += best[blocks]
        cursor = blocks
        while cursor > 0:
            prev = previous[cursor]
            if prev is None:
                raise RuntimeError("oracle selected-rank DP did not cover")
            start, arity = prev
            _, log_bin = edge_log_rank[(start, arity)]
            selected_symbols.append((arity, log_bin))
            lower_rank_bits += log_bin
            selected_records += 1
            cursor = start

    symbol_counts = Counter(selected_symbols)
    total_symbols = len(selected_symbols)
    symbol_entropy = -sum(
        (count / total_symbols) * log2(count / total_symbols)
        for count in symbol_counts.values()
    )
    lower_bits_per_record = lower_rank_bits / total_symbols
    model_bits = total_symbols * symbol_entropy + lower_rank_bits
    lower_bound_gain = (raw_bits - model_bits) / (trials * blocks)
    marker_gain = (raw_bits - model_bits - selected_records * overhead_bits) / (trials * blocks)
    return (
        oracle_gain / (trials * blocks),
        lower_bound_gain,
        marker_gain,
        selected_records / (trials * blocks),
        symbol_entropy + lower_bits_per_record,
    )


def collective_selected_rank_entropy_demo(trials: int = 80, blocks: int = 600) -> None:
    print("== family 2f: collective selected-rank entropy coding ==")
    print("This mutation gives the overlap idea a stronger paid witness model.")
    print("The oracle DP first chooses the best tiling by log-rank cost. Then")
    print("we pretend a public arithmetic model codes the selected")
    print("(arity, floor(log2 rank)) symbols at their empirical entropy, and")
    print("only raw lower rank bits are emitted inside each bin.")
    print()
    block_bits = 24
    overhead_bits = 3.0
    print(f"asymptotic simulation: block={block_bits} bits, blocks={blocks}, trials={trials}")
    print(f"{'maxA':>5} {'opts/block':>10} {'oracle':>9} "
          f"{'entropy LB':>11} {'+marker':>9} {'rec/block':>9} {'bits/rec':>9}")
    for max_arity in [2, 3, 5, 8]:
        oracle_gain, lower_bound_gain, marker_gain, records_per_block, bits_per_record = (
            selected_rank_entropy_stats(
                max_arity,
                trials,
                blocks,
                block_bits,
                overhead_bits,
            )
        )
        options_per_block = max_arity * (max_arity + 1) // 2
        print(f"{max_arity:5d} {options_per_block:10d} {oracle_gain:9.3f} "
              f"{lower_bound_gain:11.3f} {marker_gain:9.3f} "
              f"{records_per_block:9.3f} {bits_per_record:9.3f}")
    print()
    print("Reading: coding the selected witnesses collectively helps compared")
    print("with a universal integer code, but the exact rank still needs lower")
    print("bits inside its log bucket. Even with the arity/log-rank symbols")
    print("entropy-coded by a public selected distribution, the lower-bound")
    print("ledger stays negative. The free oracle was spending fractional")
    print("rank-length information that is not a parseable code.")
    print()


def projected_recursive_lengths(
    start_bits: float,
    block_bits: int,
    gain_per_block: float,
    passes: int,
) -> list[float]:
    lengths: list[float] = []
    bits = start_bits
    for _ in range(passes):
        expected_blocks = bits / block_bits
        bits -= expected_blocks * gain_per_block
        lengths.append(bits)
    return lengths


def recursive_overlap_dynamics_demo(trials: int = 50, blocks: int = 600) -> None:
    print("== family 2f2: recursive full-cover overlap dynamics ==")
    print("This mutation takes the all-block replacement story literally over")
    print("many passes. Every pass uses a full interval cover, so there is no")
    print("open/carry bitmap and no birth-pass tag. Under the uniform hash law,")
    print("the reserialized target stream is still random, so target churn")
    print("repeats the same one-pass gain distribution unless a new visible")
    print("state variable is introduced.")
    print()
    block_bits = 24
    max_arity = 5
    overhead_bits = 3.0
    passes = 64
    start_bits = blocks * block_bits
    selected_stats = selected_rank_entropy_stats(
        max_arity,
        trials,
        blocks,
        block_bits,
        overhead_bits,
    )
    rows = [
        (
            "oracle-log-rank",
            estimate_overlap_gain(
                max_arity,
                overhead_bits,
                "oracle-log-rank",
                trials,
                blocks,
                block_bits,
            ),
            "invalid",
        ),
        (
            "ideal-geometric",
            estimate_overlap_gain(
                max_arity,
                overhead_bits,
                "ideal-geometric",
                trials,
                blocks,
                block_bits,
            ),
            "paid",
        ),
        (
            "delta-rank",
            estimate_overlap_gain(
                max_arity,
                overhead_bits,
                "delta-rank",
                trials,
                blocks,
                block_bits,
            ),
            "paid",
        ),
        ("selected-entropy-LB", selected_stats[1], "paid-lb"),
        ("selected+marker", selected_stats[2], "paid-lb"),
    ]
    print(f"projection: start={int(start_bits)} bits block={block_bits} "
          f"maxA={max_arity} overhead={overhead_bits:g} passes={passes}")
    print(f"{'model':>20} {'status':>8} {'gain/block':>11} {'factor':>9} "
          f"{'P half':>8} {'len@1':>10} {'len@8':>10} "
          f"{'len@32':>10} {'len@64':>10}")
    for label, gain_per_block, status in rows:
        factor = 1.0 - (gain_per_block / block_bits)
        if 0.0 < factor < 1.0:
            passes_to_half = log2(0.5) / log2(factor)
            half_text = f"{passes_to_half:8.1f}"
        else:
            half_text = f"{'never':>8}"
        lengths = projected_recursive_lengths(start_bits, block_bits, gain_per_block, passes)
        print(f"{label:>20} {status:>8} {gain_per_block:11.3f} {factor:9.5f} "
              f"{half_text} {lengths[0]:10.1f} {lengths[7]:10.1f} "
              f"{lengths[31]:10.1f} {lengths[63]:10.1f}")
    print()
    print("Reading: repeated target churn amplifies whatever the honest")
    print("one-pass ledger says. The free oracle would reach half size only")
    print("after many passes, but it is not statelessly parseable because the")
    print("selected seed-rank witness length is missing. The paid rows grow")
    print("or stay negative from pass 1 onward, so all-block recursion does")
    print("not by itself create a compression attractor for random targets.")
    print()


def half_pass_count(gain_per_block: float, block_bits: int) -> float | None:
    if gain_per_block <= 0.0 or gain_per_block >= block_bits:
        return None
    return log(0.5) / log(1.0 - (gain_per_block / block_bits))


def high_arity_recursive_cover_surface_demo(trials: int = 30, blocks: int = 300) -> None:
    print("== family 2f3: high-arity recursive full-cover surface ==")
    print("This extends the all-block replacement projection beyond arity 5.")
    print("Every pass is still a full interval cover, so birth/open tags are")
    print("irrelevant. The question is whether longer arity alone makes target")
    print("refresh stay compressive after the selected seed-rank witness is paid.")
    print()
    block_bits = 24
    overhead_bits = 3.0
    passes = 64
    print(f"asymptotic simulation: block={block_bits} bits blocks={blocks} "
          f"trials={trials} overhead={overhead_bits:g} projected_passes={passes}")
    print(f"{'maxA':>5} {'opts/bl':>8} {'oracle':>8} {'half p':>8} "
          f"{'sel LB':>8} {'sel x64':>8} {'+mark':>8} {'mark x64':>9} "
          f"{'rec/bl':>7} {'bits/rec':>9}")
    for max_arity in [5, 8, 12, 16, 24, 32, 48, 64]:
        oracle_gain, lower_bound_gain, marker_gain, records_per_block, bits_per_record = (
            selected_rank_entropy_stats(
                max_arity,
                trials,
                blocks,
                block_bits,
                overhead_bits,
            )
        )
        oracle_half = half_pass_count(oracle_gain, block_bits)
        oracle_half_text = "none" if oracle_half is None else f"{oracle_half:8.1f}"
        selected_ratio = projected_recursive_lengths(
            blocks * block_bits,
            block_bits,
            lower_bound_gain,
            passes,
        )[-1] / (blocks * block_bits)
        marker_ratio = projected_recursive_lengths(
            blocks * block_bits,
            block_bits,
            marker_gain,
            passes,
        )[-1] / (blocks * block_bits)
        options_per_block = max_arity * (max_arity + 1) // 2
        print(f"{max_arity:5d} {options_per_block:8d} {oracle_gain:8.3f} "
              f"{oracle_half_text:>8} {lower_bound_gain:8.3f} "
              f"{selected_ratio:8.3f} {marker_gain:8.3f} {marker_ratio:9.3f} "
              f"{records_per_block:7.3f} {bits_per_record:9.3f}")
    print()
    print("Reading: higher arity strengthens the free oracle and reduces the")
    print("number of records per block. It also biases selected witnesses toward")
    print("cheaper ranks. But the exact lower rank bits inside each selected")
    print("bucket remain a real codeword cost; the paid lower bound plateaus")
    print("below zero in this sweep. Target refresh over full covers keeps")
    print("working only in the unpaid witness oracle.")
    print()


def lotus_jd_cost_for_payload_width(payload_width: int, j_bits: int, tiers: int) -> int:
    """Exact Lotus JxDy bit length for a seed with the given payload width."""
    if payload_width < 1:
        raise ValueError("payload_width must be positive")
    if not 1 <= j_bits <= 8:
        raise ValueError("j_bits must be in 1..=8")
    if tiers < 1:
        raise ValueError("tiers must be positive")
    current_width = payload_width
    total_tier_width = 0
    for _ in range(tiers):
        tier_width = lotus_width_for_value(current_width)
        total_tier_width += tier_width
        current_width = tier_width
    if current_width == 0 or current_width > (1 << j_bits):
        raise ValueError("payload_width exceeds Lotus jumpstarter capacity")
    return j_bits + total_tier_width + payload_width


def sampled_first_hit_payload_width(rng: Random, target_bits: int) -> int:
    # First hit rank is geometric with p=2^-target_bits. The exponential race
    # approximation samples log2(rank) without enumerating astronomical seeds.
    return max(1, ceil(target_bits + log2(rng.expovariate(1.0))))


def extended_arity_bits(max_arity: int, arity: int) -> int:
    if max_arity <= 5:
        if arity <= 2:
            return 2
        return 3
    return ceil(log2(max_arity))


def exact_lotus_rank_cost(payload_width: int, profile: tuple[int, int]) -> float:
    j_bits, tiers = profile
    if profile == (3, 1):
        if payload_width > J3D1_MAX_PAYLOAD_WIDTH_BITS:
            return float("inf")
        return float(j3d1_cost_for_payload_width(payload_width))
    try:
        return float(lotus_jd_cost_for_payload_width(payload_width, j_bits, tiers))
    except ValueError:
        return float("inf")


def sample_exact_lotus_all_block_cover(
    block_bits: int,
    max_arity: int,
    blocks: int,
    rng: Random,
    profile: tuple[int, int],
) -> tuple[float, float, int]:
    dp = [float("inf")] * (blocks + 1)
    records = [0] * (blocks + 1)
    dp[0] = 0.0
    for index in range(blocks):
        prefix = dp[index]
        if prefix == float("inf"):
            continue
        for arity in range(1, min(max_arity, blocks - index) + 1):
            payload_width = sampled_first_hit_payload_width(rng, arity * block_bits)
            seed_bits = exact_lotus_rank_cost(payload_width, profile)
            if seed_bits == float("inf"):
                continue
            record_bits = extended_arity_bits(max_arity, arity) + seed_bits
            candidate = prefix + record_bits
            if candidate < dp[index + arity]:
                dp[index + arity] = candidate
                records[index + arity] = records[index] + 1
    if dp[blocks] == float("inf"):
        return float("-inf"), 0.0, 0
    net_bits = (blocks * block_bits) - dp[blocks]
    record_count = records[blocks]
    avg_arity = blocks / record_count if record_count else 0.0
    return net_bits / blocks, avg_arity, record_count


def all_block_exact_lotus_landscape_demo(
    trials: int = 12,
    blocks: int = 512,
) -> None:
    print("== family 2f4: all-block exact-Lotus high-arity landscape ==")
    print("This is the clarified target: every block is replaced, so open/carry")
    print("entropy is zero. No salt or shuffle is needed in this surface. The")
    print("only per-record costs are arity code bits plus the exact Lotus seed")
    print("rank witness. A>5 is a format extension using fixed arity bits.")
    print()
    profiles = [(3, 1), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3)]
    print(f"trials={trials} blocks={blocks} profiles="
          f"{','.join(f'J{j}D{d}' for j, d in profiles)}")
    print("Best exact-Lotus rows by block size:")
    for block_bits in [8, 12, 16, 24]:
        rows: list[tuple[float, float, int, int, tuple[int, int], str]] = []
        for max_arity in [5, 8, 16, 32, 64, 128, 256]:
            for profile in profiles:
                rng = Random(880000 + block_bits * 1000 + max_arity * 10 + len(profile))
                nets: list[float] = []
                arities: list[float] = []
                record_counts: list[int] = []
                for _ in range(trials):
                    net, avg_arity, record_count = sample_exact_lotus_all_block_cover(
                        block_bits,
                        max_arity,
                        blocks,
                        rng,
                        profile,
                    )
                    if net != float("-inf"):
                        nets.append(net)
                        arities.append(avg_arity)
                        record_counts.append(record_count)
                arity_cost = ceil(log2(max_arity)) if max_arity > 5 else -1
                arity_text = (
                    "v1"
                    if max_arity <= 5
                    else str(arity_cost)
                )
                if nets:
                    rows.append((
                        mean(nets),
                        mean(arities),
                        mean(record_counts),
                        max_arity,
                        profile,
                        arity_text,
                    ))
        print(f"b={block_bits}")
        print(f"{'net/block':>10} {'avg arity':>10} {'records':>9} "
              f"{'A':>5} {'aritybits':>9} {'profile':>7}")
        for net, avg_arity, record_count, max_arity, profile, arity_text in sorted(rows, reverse=True)[:12]:
            j_bits, tiers = profile
            print(f"{net:10.4f} {avg_arity:10.3f} {record_count:9.2f} "
                  f"{max_arity:5d} {arity_text:>9} {f'J{j_bits}D{tiers}':>7}")
        print()
    print("Reading: this exact-cost surface is the right one for the all-block")
    print("hypothesis. Current J3D1 record seeds are capped at 508 payload bits;")
    print("J3D2 is the natural Lotus extension for larger ranks. Positive rows")
    print("would not be sparse hit-map wins; they would be full-cover all-record")
    print("tilings. In the sampled rows above the best cases are still slightly")
    print("negative. The remaining caveat is that this samples rank witnesses")
    print("under the uniform hash law; a production proof needs an integer")
    print("cover-language proof and a concrete A>5 arity alphabet.")
    print()


def counter_entropy(counter: Counter[object]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    return -sum((count / total) * log2(count / total) for count in counter.values())


def sample_oracle_cover_width_symbols(
    block_bits: int,
    max_arity: int,
    blocks: int,
    trials: int,
    seed: int,
) -> tuple[float, float, float, float, float, float]:
    rng = Random(seed)
    arity_header = ceil(log2(max_arity)) if max_arity > 5 else 3
    arity_counts: Counter[int] = Counter()
    delta_counts: Counter[int] = Counter()
    arity_delta_counts: Counter[tuple[int, int]] = Counter()
    nets: list[float] = []
    record_rates: list[float] = []
    for _ in range(trials):
        dp = [float("inf")] * (blocks + 1)
        previous: list[tuple[int, int, int] | None] = [None] * (blocks + 1)
        dp[0] = 0.0
        for index in range(blocks):
            prefix = dp[index]
            if prefix == float("inf"):
                continue
            for arity in range(1, min(max_arity, blocks - index) + 1):
                payload_width = sampled_first_hit_payload_width(rng, arity * block_bits)
                cost = arity_header + payload_width
                candidate = prefix + cost
                if candidate < dp[index + arity]:
                    dp[index + arity] = candidate
                    previous[index + arity] = (index, arity, payload_width)
        if dp[blocks] == float("inf"):
            continue
        nets.append((blocks * block_bits - dp[blocks]) / blocks)
        cursor = blocks
        records = 0
        while cursor > 0:
            entry = previous[cursor]
            if entry is None:
                raise AssertionError("missing oracle predecessor")
            prior, arity, payload_width = entry
            delta = payload_width - (arity * block_bits)
            arity_counts[arity] += 1
            delta_counts[delta] += 1
            arity_delta_counts[(arity, delta)] += 1
            records += 1
            cursor = prior
        record_rates.append(records / blocks)
    conditional = 0.0
    total_records = sum(arity_counts.values())
    if total_records:
        for arity, count in arity_counts.items():
            local = Counter({
                delta: hits
                for (candidate_arity, delta), hits in arity_delta_counts.items()
                if candidate_arity == arity
            })
            conditional += (count / total_records) * counter_entropy(local)
    net_per_block = mean(nets) if nets else float("-inf")
    records_per_block = mean(record_rates) if record_rates else 0.0
    budget_per_record = net_per_block / records_per_block if records_per_block else float("-inf")
    return (
        net_per_block,
        records_per_block,
        counter_entropy(arity_counts),
        counter_entropy(delta_counts),
        conditional,
        budget_per_record,
    )


def selected_width_residual_entropy_demo(trials: int = 180, blocks: int = 256) -> None:
    print("== family 2f5: selected width residual entropy ==")
    print("This prices the proposed free-width cure for all-block replacement.")
    print("The oracle can choose each interval's first-hit payload width, but")
    print("the stateless decoder still needs to know the seed boundary. If")
    print("arity almost determines width, a public width-by-arity schedule might")
    print("be enough. The conditional entropy below is the minimum remaining")
    print("width channel after the arity is already visible.")
    print()
    print(f"trials={trials} blocks={blocks}")
    print(f"{'b':>4} {'A':>5} {'oracle':>9} {'rec/bl':>8} {'budget/rec':>10} "
          f"{'H(a)':>7} {'H(dw)':>7} {'H(dw|a)':>9}")
    for block_bits, max_arity in [(8, 5), (8, 8), (8, 16), (8, 32), (12, 16), (24, 64)]:
        net, record_rate, arity_h, width_h, residual_h, budget = (
            sample_oracle_cover_width_symbols(
                block_bits,
                max_arity,
                blocks,
                trials,
                991000 + block_bits * 1000 + max_arity,
            )
        )
        print(f"{block_bits:4d} {max_arity:5d} {net:9.3f} {record_rate:8.3f} "
              f"{budget:10.3f} {arity_h:7.3f} {width_h:7.3f} {residual_h:9.3f}")
    print()
    print("Reading: the oracle's whole gain per selected record is around one")
    print("bit in the best 8-bit rows, while the residual seed-width class")
    print("after arity remains about three bits. So arity does not secretly")
    print("carry the width channel; a real fix must derive width from a stronger")
    print("invariant or stop needing variable seed boundaries.")
    print()


def sample_public_saving_schedule_cover(
    block_bits: int,
    max_arity: int,
    gains: list[int],
    blocks: int,
    trials: int,
    seed: int,
) -> tuple[float, float, float]:
    arity_header = ceil(log2(max_arity)) if max_arity > 5 else 3
    hit_probabilities = [
        0.0,
        *[-expm1(-(2 ** (-arity_header - gain))) for gain in gains[1:]],
    ]
    rng = Random(seed)
    net_per_block: list[float] = []
    record_rates: list[float] = []
    covers = 0
    for _ in range(trials):
        dp = [float("-inf")] * (blocks + 1)
        records = [0] * (blocks + 1)
        dp[0] = 0.0
        for index in range(blocks):
            prefix = dp[index]
            if prefix == float("-inf"):
                continue
            for arity in range(1, min(max_arity, blocks - index) + 1):
                if rng.random() >= hit_probabilities[arity]:
                    continue
                candidate = prefix + gains[arity]
                if candidate > dp[index + arity]:
                    dp[index + arity] = candidate
                    records[index + arity] = records[index] + 1
        if dp[blocks] == float("-inf"):
            net_per_block.append(-float(block_bits))
            continue
        covers += 1
        net_per_block.append(dp[blocks] / blocks)
        record_rates.append(records[blocks] / blocks)
    return (
        mean(net_per_block),
        covers / trials,
        mean(record_rates) if record_rates else 0.0,
    )


def public_width_schedule_cover_demo(trials: int = 160, blocks: int = 384) -> None:
    print("== family 2f6: public width-schedule all-block cover ==")
    print("This removes the per-record seed-width field entirely. A public")
    print("schedule assigns each arity a fixed net saving g after arity bits;")
    print("negative g is controlled bloat. The decoder reads arity, then a")
    print("fixed seed width for that arity. No open/carry or width metadata is")
    print("charged per record.")
    print()
    print(f"trials={trials} blocks={blocks}")
    print(f"{'b':>4} {'A':>5} {'schedule':>18} {'net/bl':>9} "
          f"{'cover':>8} {'rec/bl':>8}")
    surfaces = [
        (8, 8),
        (8, 16),
        (8, 32),
        (12, 16),
        (24, 32),
    ]
    for block_bits, max_arity in surfaces:
        schedules: list[tuple[str, list[int]]] = [
            ("all -2", [0] + [-2] * max_arity),
            ("all -1", [0] + [-1] * max_arity),
            ("all 0", [0] + [0] * max_arity),
            ("top half +1", [0] + [
                1 if arity > max_arity // 2 else 0
                for arity in range(1, max_arity + 1)
            ]),
            ("log ramp", [0] + [
                max(-2, round(-2 + log2(arity)))
                for arity in range(1, max_arity + 1)
            ]),
        ]
        rows = []
        for label, gains in schedules:
            net, cover, record_rate = sample_public_saving_schedule_cover(
                block_bits,
                max_arity,
                gains,
                blocks,
                trials,
                772000 + block_bits * 1000 + max_arity * 10 + len(label),
            )
            rows.append((net, cover, record_rate, label))
        for net, cover, record_rate, label in sorted(rows, reverse=True)[:4]:
            print(f"{block_bits:4d} {max_arity:5d} {label:>18} "
                  f"{net:9.3f} {cover:8.3f} {record_rate:8.3f}")
    print()
    print("Reading: a public arity-to-width schedule is stateless and honest,")
    print("but it loses the order-statistic advantage. Bloating schedules cover")
    print("and stay slightly negative; non-bloating or positive schedules leave")
    print("holes. The missing piece is not merely a global width table.")
    print()


WHOLE_COVER_BITS = 3
WHOLE_COVER_BLOCKS = 6
COVER_OUTPUT_CACHE: dict[tuple[int, int, int], tuple[str, ...]] = {}


def whole_cover_expand(arity: int, rank_bits: int, rank: int) -> str:
    return hash_bits("whole-cover-ordinal-language", arity, rank_bits, rank,
                     n_bits=arity * WHOLE_COVER_BITS)


def whole_cover_descriptions(blocks: int, max_arity: int, rank_bits: int) -> int:
    counts = [0] * (blocks + 1)
    counts[0] = 1
    for total in range(1, blocks + 1):
        counts[total] = sum(
            counts[total - arity] * (1 << rank_bits)
            for arity in range(1, min(max_arity, total) + 1)
        )
    return counts[blocks]


def enumerate_whole_cover_outputs(blocks: int, max_arity: int, rank_bits: int) -> set[str]:
    outputs: set[str] = set()

    def walk(remaining: int, chunks: list[str]) -> None:
        if remaining == 0:
            outputs.add("".join(chunks))
            return
        for arity in range(1, min(max_arity, remaining) + 1):
            for rank in range(1 << rank_bits):
                chunks.append(whole_cover_expand(arity, rank_bits, rank))
                walk(remaining - arity, chunks)
                chunks.pop()

    walk(blocks, [])
    return outputs


def whole_cover_output_tuple(blocks: int, max_arity: int, rank_bits: int) -> tuple[str, ...]:
    key = (blocks, max_arity, rank_bits)
    cached = COVER_OUTPUT_CACHE.get(key)
    if cached is not None:
        return cached
    outputs = tuple(sorted(enumerate_whole_cover_outputs(blocks, max_arity, rank_bits)))
    COVER_OUTPUT_CACHE[key] = outputs
    return outputs


def whole_cover_ordinal_language_demo() -> None:
    print("== family 2g: whole-cover ordinal language bound ==")
    print("This mutation encodes the entire selected cover as one ordinal in a")
    print("public cover language, instead of coding per-record rank terminators.")
    print("The decoder maps the ordinal to a full arity/rank cover and expands")
    print("it. This is exact and stateless, but its coverage is only the number")
    print("of distinct generated outputs in that language.")
    print()
    raw_bits = WHOLE_COVER_BITS * WHOLE_COVER_BLOCKS
    raw_space = 1 << raw_bits
    print(f"exact toy: block={WHOLE_COVER_BITS} bits blocks={WHOLE_COVER_BLOCKS} raw_bits={raw_bits}")
    print(f"{'maxA':>5} {'rank':>5} {'log desc':>9} {'unique':>8} "
          f"{'cover%':>9} {'save/hit':>9} {'E save':>9}")
    for max_arity in [1, 2, 3]:
        for rank_bits in [0, 1, 2, 3]:
            descriptions = whole_cover_descriptions(WHOLE_COVER_BLOCKS, max_arity, rank_bits)
            outputs = enumerate_whole_cover_outputs(WHOLE_COVER_BLOCKS, max_arity, rank_bits)
            code_bits = log2(descriptions)
            coverage = len(outputs) / raw_space
            save_per_hit = raw_bits - code_bits
            expected_save = coverage * save_per_hit
            print(f"{max_arity:5d} {rank_bits:5d} {code_bits:9.3f} {len(outputs):8d} "
                  f"{coverage:9.5f} {save_per_hit:9.3f} {expected_save:9.5f}")
    print()
    print("Reading: a whole-cover ordinal removes local terminators, but it")
    print("becomes a normal generated codebook. Short ordinals cover only a")
    print("small fraction of arbitrary outputs; broad cover languages have")
    print("ordinal spaces whose log size rises toward the raw payload. This")
    print("does not rescue arbitrary/random average compression.")
    print()


def cover_referee(bits: str, referee_bits: int) -> str:
    if referee_bits == 0:
        return ""
    return hash_bits("whole-cover-referee-code", bits, n_bits=referee_bits)


def whole_cover_referee_code_demo(trials: int = 200) -> None:
    print("== family 2h: whole-cover referee-as-codeword ==")
    print("This mutation stores a checksum/referee of the generated cover output")
    print("instead of storing the cover ordinal. The decoder enumerates the")
    print("public cover language and keeps outputs with matching referee bits.")
    print()
    blocks = WHOLE_COVER_BLOCKS
    max_arity = 3
    rank_bits = 2
    raw_bits = WHOLE_COVER_BITS * blocks
    outputs = whole_cover_output_tuple(blocks, max_arity, rank_bits)
    coverage = len(outputs) / (1 << raw_bits)
    rng = Random(939393)
    print(f"exact toy: block={WHOLE_COVER_BITS} bits blocks={blocks} maxA={max_arity} "
          f"rank={rank_bits} unique_outputs={len(outputs)} coverage={coverage:.5f}")
    print(f"{'ref':>5} {'survivors':>10} {'uniq%':>8} {'save/hit':>9} "
          f"{'E save':>9} {'E save+tag':>11}")
    for referee_bits in [0, 4, 8, 10, 12, 14, 16, 18]:
        bucket_counts = Counter(cover_referee(output, referee_bits) for output in outputs)
        survivor_counts: list[int] = []
        unique = 0
        for _ in range(trials):
            target = outputs[rng.randrange(len(outputs))]
            target_ref = cover_referee(target, referee_bits)
            survivors = bucket_counts[target_ref]
            survivor_counts.append(survivors)
            unique += int(survivors == 1)
        save_per_hit = raw_bits - referee_bits
        expected_save = coverage * save_per_hit
        expected_save_with_tag = expected_save - 1.0
        print(f"{referee_bits:5d} {mean(survivor_counts):10.3f} {unique / trials:8.3f} "
              f"{save_per_hit:9.3f} {expected_save:9.5f} {expected_save_with_tag:11.5f}")
    print()
    print("Reading: a referee can replace the ordinal only by becoming the")
    print("codeword for the generated output. Short referees leave multiple")
    print("valid generated outputs; long referees approach raw length. Even")
    print("when reachable hits have a small expected save, arbitrary data needs")
    print("a fallback/mode channel, which overwhelms the tiny coverage in this")
    print("toy.")
    print()


def logsumexp2(values: Iterable[float]) -> float:
    values = tuple(values)
    if not values:
        return float("-inf")
    peak = max(values)
    if peak == float("-inf"):
        return peak
    return peak + log2(sum(2.0 ** (value - peak) for value in values))


def interval_cover_log_descriptions(
    blocks: int,
    min_arity: int,
    max_arity: int,
    seed_bits: float,
) -> float:
    log_counts = [float("-inf")] * (blocks + 1)
    log_counts[0] = 0.0
    for total in range(1, blocks + 1):
        log_counts[total] = logsumexp2(
            log_counts[total - arity] + seed_bits
            for arity in range(min_arity, max_arity + 1)
            if total - arity >= 0
        )
    return log_counts[blocks]


def log2_coverage_from_descriptions(log_descriptions: float, raw_bits: int) -> float:
    exponent = log_descriptions - raw_bits
    if exponent < -40.0:
        return exponent
    if exponent > 8.0:
        return 0.0
    return log2(-expm1(-(2.0 ** exponent)))


def probability_text_from_log2(log_probability: float) -> str:
    if log_probability > -20.0:
        return f"{2.0 ** log_probability:.5f}"
    return f"2^{log_probability:.1f}"


def global_referee_interval_language_demo() -> None:
    print("== family 2h2: global-referee interval-cover language ==")
    print("This mutation removes all local rank witnesses. The compressed")
    print("object stores only a global referee/checksum, while the decoder")
    print("enumerates the public interval-cover language and keeps generated")
    print("outputs with the matching referee. This tests whether the overlap")
    print("crossover can be kept while moving witness bits to one end note.")
    print()
    blocks = WHOLE_COVER_BLOCKS
    max_arity = 3
    rank_bits = 2
    raw_bits = WHOLE_COVER_BITS * blocks
    outputs = whole_cover_output_tuple(blocks, max_arity, rank_bits)
    half_referee = raw_bits // 2
    half_buckets = Counter(cover_referee(output, half_referee) for output in outputs)
    mean_half_survivors = mean(half_buckets[cover_referee(output, half_referee)] for output in outputs)
    print(f"exact toy: block={WHOLE_COVER_BITS} bits blocks={blocks} maxA={max_arity} "
          f"rank={rank_bits} raw={raw_bits} unique_outputs={len(outputs)}")
    print(f"half-size referee bits={half_referee} "
          f"mean survivors among reachable targets={mean_half_survivors:.3f} "
          f"unique cost~=log2(unique)={log2(len(outputs)):.3f}")
    print()

    asym_blocks = 600
    block_bits = 24
    asym_raw = asym_blocks * block_bits
    half_bits = asym_raw / 2.0
    print(f"asymptotic counter: block={block_bits} bits blocks={asym_blocks} "
          f"raw={asym_raw} half_ref={half_bits:.0f}")
    print(f"{'arity':>7} {'seed':>6} {'logD/bl':>9} {'coverage':>12} "
          f"{'unique bits':>12} {'hit save':>9} {'surv@half':>11}")
    rows = [
        (1, 5, 24),
        (2, 5, 48),
        (3, 5, 72),
        (5, 5, 48),
        (5, 5, 72),
        (5, 5, 96),
        (5, 5, 112),
        (5, 5, 120),
    ]
    for min_arity, max_arity, seed_bits in rows:
        log_descriptions = interval_cover_log_descriptions(
            asym_blocks,
            min_arity,
            max_arity,
            float(seed_bits),
        )
        log_coverage = log2_coverage_from_descriptions(log_descriptions, asym_raw)
        log_unique_outputs = asym_raw + log_coverage
        hit_save = asym_raw - log_unique_outputs
        log_survivors_half = log_unique_outputs - half_bits
        arity_text = f"{min_arity}-{max_arity}" if min_arity != max_arity else str(min_arity)
        print(f"{arity_text:>7} {seed_bits:6d} {log_descriptions / asym_blocks:9.3f} "
              f"{probability_text_from_log2(log_coverage):>12} "
              f"{log_unique_outputs:12.1f} {hit_save:9.1f} "
              f"2^{log_survivors_half:.1f}")
    print()
    print("Reading: a global referee can replace local witnesses only by")
    print("becoming a codeword for the generated output set. When the language")
    print("is broad enough to cover a meaningful fraction of random inputs,")
    print("a half-size referee leaves about 2^(raw/2) survivors. When the")
    print("language is narrow enough for a half-size referee to be unique,")
    print("coverage is exponentially tiny. End-state/referee entropy is the")
    print("same witness channel in global form.")
    print()


def canonical_minimum_cover_derivation_demo() -> None:
    print("== family 2h3: canonical-minimum cover derivation ==")
    print("This mutation gives the overlap language its strongest public")
    print("tie-breaker: for every reachable output, the encoder and decoder")
    print("agree that the canonical witness is the minimum cover description.")
    print("Canonicalization deduplicates multiple descriptions of the same")
    print("output, but the compressed stream still has to identify which")
    print("canonical output is meant.")
    print()
    raw_bits = WHOLE_COVER_BITS * WHOLE_COVER_BLOCKS
    raw_space = 1 << raw_bits
    half_capacity = 1 << (raw_bits // 2)
    print(f"exact toy: block={WHOLE_COVER_BITS} bits blocks={WHOLE_COVER_BLOCKS} "
          f"raw={raw_bits} half_code={raw_bits // 2} bits")
    print(f"{'maxA':>5} {'rank':>5} {'log desc':>9} {'log uniq':>9} "
          f"{'dedup':>8} {'cover%':>9} {'best half%':>10} {'bits all':>9}")
    for max_arity in [1, 2, 3]:
        for rank_bits in [0, 1, 2, 3]:
            descriptions = whole_cover_descriptions(WHOLE_COVER_BLOCKS, max_arity, rank_bits)
            unique_outputs = len(enumerate_whole_cover_outputs(
                WHOLE_COVER_BLOCKS,
                max_arity,
                rank_bits,
            ))
            log_descriptions = log2(descriptions)
            log_unique = log2(unique_outputs)
            coverage = unique_outputs / raw_space
            best_half_coverage = min(unique_outputs, half_capacity) / raw_space
            print(f"{max_arity:5d} {rank_bits:5d} {log_descriptions:9.3f} "
                  f"{log_unique:9.3f} {log_descriptions - log_unique:8.3f} "
                  f"{coverage:9.5f} {best_half_coverage:10.5f} {log_unique:9.3f}")
    print()

    asym_blocks = 600
    block_bits = 24
    asym_raw = asym_blocks * block_bits
    half_bits = asym_raw / 2.0
    print(f"asymptotic canonical bound: block={block_bits} bits blocks={asym_blocks} "
          f"raw={asym_raw} half_code={half_bits:.0f} bits")
    print(f"{'arity':>7} {'seed':>6} {'logD/bl':>9} {'uniq bits':>10} "
          f"{'full cov':>12} {'best half cov':>14} {'bits all':>9}")
    for min_arity, max_arity, seed_bits in [
        (1, 5, 24),
        (2, 5, 48),
        (3, 5, 72),
        (5, 5, 48),
        (5, 5, 72),
        (5, 5, 96),
        (5, 5, 120),
    ]:
        log_descriptions = interval_cover_log_descriptions(
            asym_blocks,
            min_arity,
            max_arity,
            float(seed_bits),
        )
        log_full_coverage = log2_coverage_from_descriptions(log_descriptions, asym_raw)
        log_unique_outputs = asym_raw + log_full_coverage
        log_best_half_coverage = min(half_bits, log_unique_outputs) - asym_raw
        arity_text = f"{min_arity}-{max_arity}" if min_arity != max_arity else str(min_arity)
        print(f"{arity_text:>7} {seed_bits:6d} {log_descriptions / asym_blocks:9.3f} "
              f"{log_unique_outputs:10.1f} "
              f"{probability_text_from_log2(log_full_coverage):>12} "
              f"{probability_text_from_log2(log_best_half_coverage):>14} "
              f"{log_unique_outputs:9.1f}")
    print()
    print("Reading: a public minimum-cover rule is useful only for removing")
    print("duplicate descriptions. It cannot select one of the remaining")
    print("canonical outputs without code bits. At half-size, even the best")
    print("possible canonical subset covers at most 2^(-raw/2) of arbitrary")
    print("random inputs when the language is broad; when the language is")
    print("narrow, its own coverage is even smaller. Derivation is not a free")
    print("replacement for the witness channel.")
    print()


def fixed_width_cover_gain_per_block(
    rng: Random,
    rank_bits: int,
    blocks: int,
    max_arity: int,
    block_bits: int,
    overhead_bits: float,
) -> tuple[bool, float]:
    best = [float("-inf")] * (blocks + 1)
    best[0] = 0.0
    for start in range(blocks):
        if best[start] == float("-inf"):
            continue
        for arity in range(1, max_arity + 1):
            end = start + arity
            if end > blocks:
                break
            target_bits = arity * block_bits
            threshold = 2.0 ** (rank_bits - target_bits) if rank_bits - target_bits > -64 else 0.0
            hit_probability = 1.0 if threshold > 40.0 else -expm1(-threshold)
            if rng.random() > hit_probability:
                continue
            gain = target_bits - rank_bits - overhead_bits
            candidate = best[start] + gain
            if candidate > best[end]:
                best[end] = candidate
    if best[blocks] == float("-inf"):
        return False, 0.0
    return True, best[blocks] / blocks


def global_fixed_depth_cover_demo(trials: int = 120, blocks: int = 480) -> None:
    print("== family 2i: global fixed-depth rank cover ==")
    print("This mutation makes the seed-rank width decoder-known once in a")
    print("root/header schedule. Every record rank is fixed-width, so no")
    print("per-record seed-width terminator is needed. Raw fallback is treated")
    print("optimistically as zero gain when a full all-record cover is missing.")
    print()
    rng = Random(626262)
    block_bits = 24
    max_arity = 5
    overhead_bits = 3.0
    print(f"asymptotic simulation: block={block_bits} bits max_arity={max_arity} "
          f"blocks={blocks} trials={trials} overhead={overhead_bits:g}")
    print(f"{'rank bits':>9} {'cover%':>8} {'gain/covered':>13} {'E gain/block':>13}")
    for rank_bits in [24, 28, 32, 40, 48, 52, 56, 72, 96, 100, 120]:
        gains: list[float] = []
        covered_gains: list[float] = []
        covers = 0
        for _ in range(trials):
            covered, gain = fixed_width_cover_gain_per_block(
                rng,
                rank_bits,
                blocks,
                max_arity,
                block_bits,
                overhead_bits,
            )
            covers += int(covered)
            gains.append(gain if covered else 0.0)
            if covered:
                covered_gains.append(gain)
        cover_rate = covers / trials
        avg_covered = mean(covered_gains) if covered_gains else 0.0
        print(f"{rank_bits:9d} {cover_rate:8.3f} {avg_covered:13.3f} {mean(gains):13.3f}")
    print()
    print("Reading: a global fixed width is stateless and parseable, but it")
    print("removes the order-statistic benefit of lucky early ranks. Low widths")
    print("cover with bloating short records; high widths make long bundles")
    print("available but charge that same width to every selected record. In")
    print("this optimistic raw-fallback ledger, no tested global depth crosses")
    print("positive.")
    print()


HOMOPHONIC_VALUE_BITS = 4
HOMOPHONIC_SEED_BITS = 6


def homophonic_codeword(value: int, synonym: int, synonym_bits: int) -> str:
    return f"{value:0{HOMOPHONIC_VALUE_BITS}b}{synonym:0{synonym_bits}b}"


def homophonic_expand_pair_seed(seed: int, synonym_bits: int) -> str:
    span_bits = 2 * (HOMOPHONIC_VALUE_BITS + synonym_bits)
    return hash_bits("homophonic-literal-pair", synonym_bits, seed, n_bits=span_bits)


def homophonic_pair_values(surface_bits: str, synonym_bits: int) -> tuple[int, int]:
    width = HOMOPHONIC_VALUE_BITS + synonym_bits
    if len(surface_bits) != 2 * width:
        raise ValueError("wrong homophonic pair width")
    first = int(surface_bits[:HOMOPHONIC_VALUE_BITS], 2)
    second = int(surface_bits[width:width + HOMOPHONIC_VALUE_BITS], 2)
    return first, second


def build_homophonic_pair_book(synonym_bits: int) -> dict[tuple[int, int], int]:
    book: dict[tuple[int, int], int] = {}
    for seed in range(1 << HOMOPHONIC_SEED_BITS):
        surface = homophonic_expand_pair_seed(seed, synonym_bits)
        book.setdefault(homophonic_pair_values(surface, synonym_bits), seed)
    return book


@dataclass(frozen=True)
class HomophonicEncoded:
    synonym_bits: int
    pairs: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: tuple[int, ...]
    tail: tuple[int, ...]


@dataclass(frozen=True)
class HomophonicStat:
    synonym_bits: int
    pairs: int
    hits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def encode_homophonic_pairs(values: tuple[int, ...], synonym_bits: int) -> tuple[HomophonicEncoded, HomophonicStat]:
    book = build_homophonic_pair_book(synonym_bits)
    pairs = len(values) // 2
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[int] = []
    for pair_index in range(pairs):
        pair = (values[2 * pair_index], values[2 * pair_index + 1])
        seed = book.get(pair)
        if seed is None:
            hits.append(False)
            literals.extend(pair)
        else:
            hits.append(True)
            seeds.append(seed)
    tail = values[2 * pairs:]
    literal_bits = len(literals) * (HOMOPHONIC_VALUE_BITS + synonym_bits)
    tail_bits = len(tail) * HOMOPHONIC_VALUE_BITS
    seed_bits = len(seeds) * HOMOPHONIC_SEED_BITS
    bitmap_bits = log2_choose(pairs, len(seeds))
    count_bits = count_class_bits(pairs + 1)
    charged_bits = literal_bits + tail_bits + seed_bits + bitmap_bits + count_bits
    return (
        HomophonicEncoded(
            synonym_bits,
            pairs,
            tuple(hits),
            tuple(seeds),
            tuple(literals),
            tuple(tail),
        ),
        HomophonicStat(
            synonym_bits,
            pairs,
            len(seeds),
            literal_bits + tail_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_homophonic_pairs(encoded: HomophonicEncoded) -> tuple[int, ...]:
    out: list[int] = []
    seed_index = 0
    literal_index = 0
    for hit in encoded.hits:
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            surface = homophonic_expand_pair_seed(seed, encoded.synonym_bits)
            out.extend(homophonic_pair_values(surface, encoded.synonym_bits))
        else:
            out.extend(encoded.literals[literal_index:literal_index + 2])
            literal_index += 2
    if seed_index != len(encoded.seeds):
        raise ValueError("unused homophonic seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused homophonic literals")
    out.extend(encoded.tail)
    return tuple(out)


def homophonic_literal_recode_demo(trials: int = 200, blocks: int = 128) -> None:
    print("== family 2j: homophonic literal recoding ==")
    print("This mutation gives each literal payload block multiple reversible")
    print("surface encodings. The encoder may choose synonym bits so a seed")
    print("expansion matches the surface, while the decoder strips synonyms")
    print("back to the same payload.")
    print()
    rng = Random(747474)
    raw_bits = blocks * HOMOPHONIC_VALUE_BITS
    print(f"exact toy: value_bits={HOMOPHONIC_VALUE_BITS} blocks={blocks} "
          f"pair_seed={HOMOPHONIC_SEED_BITS}")
    print(f"{'syn':>4} {'hits':>8} {'hit/pair':>9} {'literal':>9} "
          f"{'seed':>7} {'bitmap':>8} {'charged':>9} {'net':>9} {'p formula':>10}")
    for synonym_bits in [0, 1, 2, 3, 4]:
        stats: list[HomophonicStat] = []
        for _ in range(trials):
            values = tuple(rng.randrange(1 << HOMOPHONIC_VALUE_BITS) for _ in range(blocks))
            encoded, stat = encode_homophonic_pairs(values, synonym_bits)
            assert decode_homophonic_pairs(encoded) == values
            stats.append(stat)
        avg_hits = mean(stat.hits for stat in stats)
        avg_pairs = mean(stat.pairs for stat in stats)
        avg_literal = mean(stat.literal_bits for stat in stats)
        avg_seed = mean(stat.seed_bits for stat in stats)
        avg_bitmap = mean(stat.bitmap_bits + stat.count_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        payload_pair_space = 1 << (2 * HOMOPHONIC_VALUE_BITS)
        hit_formula = 1.0 - ((1.0 - (1.0 / payload_pair_space)) ** (1 << HOMOPHONIC_SEED_BITS))
        print(f"{synonym_bits:4d} {avg_hits:8.3f} {avg_hits / avg_pairs:9.5f} "
              f"{avg_literal:9.3f} {avg_seed:7.3f} {avg_bitmap:8.3f} "
              f"{avg_charged:9.3f} {raw_bits - avg_charged:9.3f} {hit_formula:10.5f}")
    print()
    print("Reading: homophonic synonyms are decoder-visible and give the")
    print("encoder many surface choices, but for uniform hashes those choices")
    print("cancel against the extra surface bits. The probability that some")
    print("seed projects to a payload pair is independent of synonym width,")
    print("while missed literals get longer. The synonym freedom is stored")
    print("surface entropy, not a free target-refresh channel.")
    print()


GLOBAL_TRANSFORM_L = 12
GLOBAL_TRANSFORM_SEED_BITS = 8
GLOBAL_TRANSFORM_CHOICES = (1, 2, 4, 16, 64, 256)


def global_transform_expand_seed(seed: int) -> int:
    return int(hash_bits("global-transform-seed", seed, n_bits=GLOBAL_TRANSFORM_L), 2)


GLOBAL_TRANSFORM_BOOK = {
    global_transform_expand_seed(seed): seed for seed in range(1 << GLOBAL_TRANSFORM_SEED_BITS)
}


def global_transform_mask(transform: int, slot: int) -> int:
    return int(hash_bits("global-transform-mask", transform, slot, n_bits=GLOBAL_TRANSFORM_L), 2)


@dataclass(frozen=True)
class GlobalTransformEncoded:
    length: int
    transform: int
    slots: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: tuple[int, ...]
    tail: str


@dataclass(frozen=True)
class GlobalTransformStat:
    transforms: int
    slots: int
    hits: int
    hit_rate: float
    bitmap_bits: float
    transform_bits: float
    charged_bits: float


def global_transform_chunk(bits: str, slot: int, transform: int) -> int:
    raw = int(bits[slot * GLOBAL_TRANSFORM_L:(slot + 1) * GLOBAL_TRANSFORM_L], 2)
    return raw ^ global_transform_mask(transform, slot)


def encode_for_global_transform(
    bits: str,
    transform: int,
    transform_count: int,
    masks: tuple[tuple[int, ...], ...] | None = None,
) -> tuple[GlobalTransformEncoded, GlobalTransformStat]:
    slots = len(bits) // GLOBAL_TRANSFORM_L
    tail = bits[slots * GLOBAL_TRANSFORM_L:]
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[int] = []
    for slot in range(slots):
        raw = int(bits[slot * GLOBAL_TRANSFORM_L:(slot + 1) * GLOBAL_TRANSFORM_L], 2)
        mask = masks[transform][slot] if masks is not None else global_transform_mask(transform, slot)
        transformed = raw ^ mask
        seed = GLOBAL_TRANSFORM_BOOK.get(transformed)
        if seed is None:
            hits.append(False)
            literals.append(transformed)
        else:
            hits.append(True)
            seeds.append(seed)
    hit_count = sum(hits)
    literal_bits = len(literals) * GLOBAL_TRANSFORM_L + len(tail)
    seed_bits = len(seeds) * GLOBAL_TRANSFORM_SEED_BITS
    bitmap_bits = log2_choose(slots, hit_count)
    count_bits = count_class_bits(slots + 1)
    transform_bits = log2(transform_count) if transform_count > 1 else 0.0
    charged_bits = literal_bits + seed_bits + bitmap_bits + count_bits + transform_bits
    return (
        GlobalTransformEncoded(
            len(bits), transform, slots, tuple(hits), tuple(seeds), tuple(literals), tail,
        ),
        GlobalTransformStat(
            transform_count,
            slots,
            hit_count,
            hit_count / slots if slots else 0.0,
            bitmap_bits + count_bits,
            transform_bits,
            charged_bits,
        ),
    )


def encode_best_global_transform(
    bits: str,
    transform_count: int,
    masks: tuple[tuple[int, ...], ...] | None = None,
) -> tuple[GlobalTransformEncoded, GlobalTransformStat]:
    best: tuple[GlobalTransformEncoded, GlobalTransformStat] | None = None
    for transform in range(transform_count):
        candidate = encode_for_global_transform(bits, transform, transform_count, masks)
        if best is None or candidate[1].charged_bits < best[1].charged_bits:
            best = candidate
    assert best is not None
    return best


def decode_global_transform(encoded: GlobalTransformEncoded) -> str:
    out: list[str] = []
    seed_index = 0
    literal_index = 0
    for slot, hit in enumerate(encoded.hits):
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            transformed = global_transform_expand_seed(seed)
        else:
            transformed = encoded.literals[literal_index]
            literal_index += 1
        raw = transformed ^ global_transform_mask(encoded.transform, slot)
        out.append(format(raw, f"0{GLOBAL_TRANSFORM_L}b"))
    if seed_index != len(encoded.seeds):
        raise ValueError("unused global-transform seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused global-transform literals")
    out.append(encoded.tail)
    return "".join(out)


def kl_bernoulli(q: float, p: float) -> float:
    if q <= 0.0:
        return -log2(1.0 - p)
    if q >= 1.0:
        return -log2(p)
    return q * log2(q / p) + (1.0 - q) * log2((1.0 - q) / (1.0 - p))


def global_transform_layer_demo(trials: int = 200, n_bits: int = 3072) -> None:
    print("== family 2k: global public transform selection ==")
    print("A whole layer may choose one public reversible transform, store that")
    print("transform index once, then encode scheduled slots under the fixed")
    print("seed universe. This is the optimistic target-refresh version: no")
    print("per-window transform coordinate is stored.")
    print()
    rng = Random(224466)
    print(f"toy grammar: span={GLOBAL_TRANSFORM_L} seed={GLOBAL_TRANSFORM_SEED_BITS} "
          f"gross/hit={GLOBAL_TRANSFORM_L - GLOBAL_TRANSFORM_SEED_BITS} "
          f"unique seed images={len(GLOBAL_TRANSFORM_BOOK)}")
    print(f"{'K':>5} {'hits':>8} {'hit/slot':>10} {'bitmap':>10} "
          f"{'K bits':>8} {'charged':>10} {'net':>10}")
    slots = n_bits // GLOBAL_TRANSFORM_L
    max_transforms = max(GLOBAL_TRANSFORM_CHOICES)
    masks = tuple(
        tuple(global_transform_mask(transform, slot) for slot in range(slots))
        for transform in range(max_transforms)
    )
    for transform_count in GLOBAL_TRANSFORM_CHOICES:
        stats: list[GlobalTransformStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_best_global_transform(bits, transform_count, masks)
            assert decode_global_transform(encoded) == bits
            stats.append(stat)
        avg_hits = mean(stat.hits for stat in stats)
        avg_slots = mean(stat.slots for stat in stats)
        avg_hit_rate = mean(stat.hit_rate for stat in stats)
        avg_bitmap = mean(stat.bitmap_bits for stat in stats)
        avg_transform_bits = mean(stat.transform_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        print(f"{transform_count:5d} {avg_hits:8.3f} {avg_hit_rate:10.5f} "
              f"{avg_bitmap:10.3f} {avg_transform_bits:8.3f} "
              f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
    print()
    print("Large-deviation ledger for an ideal best-of-K global transform:")
    print(f"{'q hit':>8} {'D(q||p)':>11} {'q*d-H(q)':>11} {'net incl K':>11}")
    p = len(GLOBAL_TRANSFORM_BOOK) / (1 << GLOBAL_TRANSFORM_L)
    d = GLOBAL_TRANSFORM_L - GLOBAL_TRANSFORM_SEED_BITS
    for q in [p, 0.08, 0.10, 0.125, 0.16, 0.20, 0.25]:
        if q < p:
            continue
        transform_cost = kl_bernoulli(q, p)
        slot_net_before_transform = q * d - binary_entropy(q)
        net = slot_net_before_transform - transform_cost
        print(f"{q:8.5f} {transform_cost:11.5f} {slot_net_before_transform:11.5f} "
              f"{net:11.5f}")
    print()
    print("Reading: choosing the best public layer transform can raise hit")
    print("density while storing only one transform index. But under uniform")
    print("chunks the index cost is the large-deviation price of seeing that")
    print("many hits. After the hit bitmap is also priced, the best-of-K")
    print("advantage remains negative. Per-window transform choice would add")
    print("a larger coordinate bill.")
    print()


RECHUNK_L = 14
RECHUNK_SEED_BITS = 10
RECHUNK_RECORD_BITS = 1 + RECHUNK_SEED_BITS
RECHUNK_LITERAL_BITS = 2


def expand_rechunk_seed(seed: int) -> str:
    return hash_bits("whole-layer-rechunk-fixed-universe", seed, n_bits=RECHUNK_L)


def build_rechunk_book() -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << RECHUNK_SEED_BITS):
        book.setdefault(expand_rechunk_seed(seed), seed)
    return book


RECHUNK_BOOK = build_rechunk_book()


@dataclass
class RechunkLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    windows: int
    matches: int


@dataclass
class RechunkEncoded:
    final_bits: str
    stats: tuple[RechunkLayerStat, ...]
    original_bits: str


def encode_rechunk_layer(bits: str, pass_index: int) -> tuple[str, RechunkLayerStat]:
    out: list[str] = []
    index = 0
    matches = 0
    windows = max(0, len(bits) - RECHUNK_L + 1)
    while index < len(bits):
        if index + RECHUNK_L <= len(bits):
            seed = RECHUNK_BOOK.get(bits[index:index + RECHUNK_L])
            if seed is not None:
                out.append("1" + format(seed, f"0{RECHUNK_SEED_BITS}b"))
                matches += 1
                index += RECHUNK_L
                continue
        out.append("0" + bits[index])
        index += 1
    encoded = "".join(out)
    return encoded, RechunkLayerStat(pass_index, len(bits), len(encoded), windows, matches)


def decode_rechunk_layer(bits: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(bits):
        tag = bits[index]
        if tag == "0":
            if index + 2 > len(bits):
                raise ValueError("truncated literal")
            out.append(bits[index + 1])
            index += 2
        elif tag == "1":
            end = index + RECHUNK_RECORD_BITS
            if end > len(bits):
                raise ValueError("truncated record")
            seed = int(bits[index + 1:end], 2)
            out.append(expand_rechunk_seed(seed))
            index = end
        else:
            raise ValueError(f"invalid tag {tag!r}")
    return "".join(out)


def encode_rechunk_layers(bits: str, passes: int) -> RechunkEncoded:
    current = bits
    stats: list[RechunkLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_rechunk_layer(current, pass_index)
        stats.append(stat)
        if stat.matches == 0:
            break
    return RechunkEncoded(current, tuple(stats), bits)


def decode_rechunk_layers(encoded: RechunkEncoded) -> str:
    current = encoded.final_bits
    for _ in reversed(encoded.stats):
        current = decode_rechunk_layer(current)
    return current


def rechunk_superposition_demo(trials: int = 200, n_bits: int = 192, passes: int = 6) -> None:
    print("== family 2l: whole-layer rechunk / superposition target refresh ==")
    print("This toy gives target-refresh a clean stateless codec: each pass")
    print("encodes the entire current bitstream with a fixed unsalted universe,")
    print("a known layer count, literal tokens, and records. Greedy matching")
    print("checks every bit position, so selected boundaries are visible in")
    print("the token stream rather than stored as a sidecar.")
    print()
    rng = Random(2468)
    rows: dict[int, list[RechunkLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_delta: list[int] = []
    best_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_rechunk_layers(bits, passes)
        assert decode_rechunk_layers(encoded) == bits
        final_delta.append(len(bits) - len(encoded.final_bits))
        best_delta.append(max(len(bits) - stat.after_bits for stat in encoded.stats))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    unique_outputs = len(RECHUNK_BOOK)
    hit_p = unique_outputs / (1 << RECHUNK_L)
    gross = RECHUNK_L - RECHUNK_RECORD_BITS
    print(f"toy grammar: literal={RECHUNK_LITERAL_BITS} bits "
          f"record={RECHUNK_RECORD_BITS} bits span={RECHUNK_L} bits")
    print(f"fixed universe: unique outputs={unique_outputs} hit_p/window={hit_p:.5f} "
          f"gross per record={gross} bits")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in bits':>12} {'avg out bits':>13} "
          f"{'avg windows':>12} {'avg matches':>12} {'hit/window':>11} "
          f"{'delta vs in':>12} {'delta vs orig':>13}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_windows = mean(stat.windows for stat in stats)
        avg_matches = mean(stat.matches for stat in stats)
        hit_rate = avg_matches / avg_windows if avg_windows else 0.0
        delta_in = avg_in - avg_out
        delta_orig = n_bits - avg_out
        print(f"{pass_index:4d} {avg_in:12.2f} {avg_out:13.2f} "
              f"{avg_windows:12.2f} {avg_matches:12.3f} {hit_rate:11.5f} "
              f"{delta_in:12.3f} {delta_orig:13.3f}")
    print(f"mean final delta vs original={mean(final_delta):.3f} bits")
    print(f"mean best intermediate delta vs original={mean(best_delta):.3f} bits")
    print()
    print("Reading: all-position rechunking removes the explicit window")
    print("coordinate by putting boundaries in the token stream, but literals")
    print("then carry the non-hit regions. The fixed unsalted universe finds")
    print("some first-layer matches, yet whole-layer recursion bloats random")
    print("inputs instead of maintaining net compression.")
    print()


ADAPTIVE_LENGTH_OPTIONS = (10, 12, 14)
ADAPTIVE_LENGTH_SEED_BITS = 8
ADAPTIVE_LENGTH_CHOICE_BITS = ceil(log2(len(ADAPTIVE_LENGTH_OPTIONS)))


def adaptive_length_expand(span_bits: int, seed: int) -> str:
    return hash_bits("adaptive-length-fixed-universe", span_bits, seed, n_bits=span_bits)


@lru_cache(maxsize=None)
def adaptive_length_book(span_bits: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << ADAPTIVE_LENGTH_SEED_BITS):
        book.setdefault(adaptive_length_expand(span_bits, seed), seed)
    return book


@dataclass
class AdaptiveLengthLayerStat:
    pass_index: int
    span_bits: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    tail_bits: int
    tight_charged_bits: float


@dataclass
class AdaptiveLengthEncoded:
    final_bits: str
    stats: tuple[AdaptiveLengthLayerStat, ...]
    original_bits: str


def encode_adaptive_length_layer_for_span(
    bits: str,
    pass_index: int,
    span_bits: int,
) -> tuple[str, AdaptiveLengthLayerStat]:
    shuffled = apply_bit_permutation(bits, pass_index)
    chunks = len(shuffled) // span_bits
    tail = shuffled[chunks * span_bits:]
    book = adaptive_length_book(span_bits)
    out: list[str] = []
    hits = 0
    literal_chunks: list[str] = []
    for index in range(chunks):
        chunk = shuffled[index * span_bits:(index + 1) * span_bits]
        seed = book.get(chunk)
        if seed is None:
            out.append("0" + chunk)
            literal_chunks.append(chunk)
        else:
            out.append("1" + format(seed, f"0{ADAPTIVE_LENGTH_SEED_BITS}b"))
            hits += 1
    if tail:
        out.append(tail)
    bitmap_bits = log2_choose(chunks, hits)
    count_bits = count_class_bits(chunks + 1)
    tight_charged = (
        (chunks - hits) * span_bits
        + hits * ADAPTIVE_LENGTH_SEED_BITS
        + len(tail)
        + bitmap_bits
        + count_bits
        + ADAPTIVE_LENGTH_CHOICE_BITS
    )
    encoded = "".join(out)
    return encoded, AdaptiveLengthLayerStat(
        pass_index,
        span_bits,
        len(bits),
        len(encoded) + ADAPTIVE_LENGTH_CHOICE_BITS,
        chunks,
        hits,
        len(tail),
        tight_charged,
    )


def decode_adaptive_length_layer(bits: str, stat: AdaptiveLengthLayerStat) -> str:
    chunks: list[str] = []
    offset = 0
    for _ in range(stat.chunks):
        if offset >= len(bits):
            raise ValueError("truncated adaptive-length layer")
        tag = bits[offset]
        if tag == "0":
            end = offset + 1 + stat.span_bits
            if end > len(bits):
                raise ValueError("truncated adaptive-length literal")
            chunk = bits[offset + 1:end]
            offset = end
        elif tag == "1":
            end = offset + 1 + ADAPTIVE_LENGTH_SEED_BITS
            if end > len(bits):
                raise ValueError("truncated adaptive-length record")
            seed = int(bits[offset + 1:end], 2)
            chunk = adaptive_length_expand(stat.span_bits, seed)
            offset = end
        else:
            raise ValueError(f"invalid adaptive-length tag {tag!r}")
        chunks.append(chunk)
    tail = bits[offset:]
    shuffled = "".join(chunks) + tail
    if len(shuffled) != stat.before_bits:
        raise ValueError("adaptive-length decoded length mismatch")
    return invert_bit_permutation(shuffled, stat.pass_index)


def encode_adaptive_length_layers(bits: str, passes: int) -> AdaptiveLengthEncoded:
    current = bits
    stats: list[AdaptiveLengthLayerStat] = []
    for pass_index in range(1, passes + 1):
        candidates = [
            encode_adaptive_length_layer_for_span(current, pass_index, span_bits)
            for span_bits in ADAPTIVE_LENGTH_OPTIONS
        ]
        encoded, stat = min(candidates, key=lambda item: item[1].tight_charged_bits)
        stats.append(stat)
        current = encoded
    return AdaptiveLengthEncoded(current, tuple(stats), bits)


def decode_adaptive_length_layers(encoded: AdaptiveLengthEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_adaptive_length_layer(current, stat)
    return current


def adaptive_length_target_refresh_demo(trials: int = 80, n_bits: int = 512, passes: int = 5) -> None:
    print("== family 2l2: adaptive-length target refresh ==")
    print("This mutation lets each layer choose the best public chunk length")
    print("from a small set, while using the same fixed unsalted seed universe.")
    print("The layer stores only the chosen length index; open/carry is priced")
    print("with the hit bitmap/count in the tight ledger.")
    print()
    rng = Random(848484)
    rows: dict[int, list[AdaptiveLengthLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_visible_delta: list[int] = []
    best_visible_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_adaptive_length_layers(bits, passes)
        assert decode_adaptive_length_layers(encoded) == bits
        final_visible_delta.append(n_bits - len(encoded.final_bits))
        best_visible_delta.append(max(n_bits - stat.after_bits for stat in encoded.stats))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(f"toy grammar: spans={ADAPTIVE_LENGTH_OPTIONS} seed={ADAPTIVE_LENGTH_SEED_BITS} "
          f"choice_bits={ADAPTIVE_LENGTH_CHOICE_BITS}")
    print(f"{'pass':>4} {'avg in':>9} {'span mode':>10} {'hits/ch':>9} "
          f"{'visible net':>11} {'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        span_counts = Counter(stat.span_bits for stat in stats)
        mode_span, _ = span_counts.most_common(1)[0]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        avg_chunks = mean(stat.chunks for stat in stats)
        visible_net = avg_in - mean(stat.after_bits for stat in stats)
        tight_net = avg_in - mean(stat.tight_charged_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:9.2f} {mode_span:10d} "
              f"{avg_hits / avg_chunks if avg_chunks else 0.0:9.5f} "
              f"{visible_net:11.3f} {tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_visible_delta):.3f} bits")
    print(f"mean best visible intermediate delta vs original={mean(best_visible_delta):.3f} bits")
    print()
    print("Closed-form per-slot tight ledger for selectable lengths:")
    print(f"{'span':>5} {'p':>9} {'gross':>7} {'H(p)':>9} {'net/slot':>10}")
    for span_bits in ADAPTIVE_LENGTH_OPTIONS:
        p = 2.0 ** (ADAPTIVE_LENGTH_SEED_BITS - span_bits)
        gross = span_bits - ADAPTIVE_LENGTH_SEED_BITS
        entropy = binary_entropy(p)
        print(f"{span_bits:5d} {p:9.5f} {gross:7d} {entropy:9.5f} {p * gross - entropy:10.5f}")
    print()
    print("Reading: public length choice refreshes boundaries and target")
    print("populations, and it is cheap when stored once per layer. But each")
    print("fixed-length option still obeys p*d-H(p)<0 under uniform chunks.")
    print("The adaptive layer just chooses the least-bad negative option, so")
    print("recursive target churn amplifies bloat rather than creating an")
    print("arbitrary-content compression attractor.")
    print()


@dataclass
class ShuffleLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    tail_bits: int
    sparse_charged_bits: float


@dataclass
class ShuffleRefreshEncoded:
    final_bits: str
    stats: tuple[ShuffleLayerStat, ...]
    original_bits: str


def public_bit_permutation(length: int, pass_index: int) -> list[int]:
    perm = list(range(length))
    rng = Random(88000 + pass_index * 1009 + length * 17)
    rng.shuffle(perm)
    return perm


def apply_bit_permutation(bits: str, pass_index: int) -> str:
    perm = public_bit_permutation(len(bits), pass_index)
    return "".join(bits[index] for index in perm)


def invert_bit_permutation(bits: str, pass_index: int) -> str:
    perm = public_bit_permutation(len(bits), pass_index)
    out = ["0"] * len(bits)
    for shuffled_index, original_index in enumerate(perm):
        out[original_index] = bits[shuffled_index]
    return "".join(out)


def public_bit_permutation_choice(length: int, pass_index: int, choice: int) -> list[int]:
    perm = list(range(length))
    rng = Random(991000 + pass_index * 1009 + length * 17 + choice * 65537)
    rng.shuffle(perm)
    return perm


def apply_bit_permutation_choice(bits: str, pass_index: int, choice: int) -> str:
    perm = public_bit_permutation_choice(len(bits), pass_index, choice)
    return "".join(bits[index] for index in perm)


def invert_bit_permutation_choice(bits: str, pass_index: int, choice: int) -> str:
    perm = public_bit_permutation_choice(len(bits), pass_index, choice)
    out = ["0"] * len(bits)
    for shuffled_index, original_index in enumerate(perm):
        out[original_index] = bits[shuffled_index]
    return "".join(out)


def encode_shuffled_chunk_layer(bits: str, pass_index: int) -> tuple[str, ShuffleLayerStat]:
    shuffled = apply_bit_permutation(bits, pass_index)
    chunks = len(shuffled) // RECHUNK_L
    tail_bits = len(shuffled) - (chunks * RECHUNK_L)
    out: list[str] = []
    hits = 0
    for chunk_index in range(chunks):
        start = chunk_index * RECHUNK_L
        chunk = shuffled[start:start + RECHUNK_L]
        seed = RECHUNK_BOOK.get(chunk)
        if seed is None:
            out.append("0" + chunk)
            continue
        out.append("1" + format(seed, f"0{RECHUNK_SEED_BITS}b"))
        hits += 1
    if tail_bits:
        out.append(shuffled[-tail_bits:])
    encoded = "".join(out)
    bitmap_bits = log2_choose(chunks, hits)
    count_bits = count_class_bits(chunks + 1)
    sparse_charged = (
        (chunks - hits) * RECHUNK_L
        + hits * RECHUNK_SEED_BITS
        + bitmap_bits
        + count_bits
        + tail_bits
    )
    return encoded, ShuffleLayerStat(
        pass_index,
        len(bits),
        len(encoded),
        chunks,
        hits,
        tail_bits,
        sparse_charged,
    )


def decode_shuffled_chunk_layer(bits: str, stat: ShuffleLayerStat) -> str:
    chunks: list[str] = []
    offset = 0
    for _ in range(stat.chunks):
        if offset >= len(bits):
            raise ValueError("truncated shuffled layer")
        tag = bits[offset]
        if tag == "0":
            end = offset + 1 + RECHUNK_L
            if end > len(bits):
                raise ValueError("truncated shuffled literal chunk")
            chunks.append(bits[offset + 1:end])
            offset = end
        elif tag == "1":
            end = offset + RECHUNK_RECORD_BITS
            if end > len(bits):
                raise ValueError("truncated shuffled record")
            seed = int(bits[offset + 1:end], 2)
            chunks.append(expand_rechunk_seed(seed))
            offset = end
        else:
            raise ValueError(f"invalid shuffled tag {tag!r}")
    tail = bits[offset:offset + stat.tail_bits]
    if len(tail) != stat.tail_bits:
        raise ValueError("truncated shuffled tail")
    if offset + stat.tail_bits != len(bits):
        raise ValueError("extra bits after shuffled layer")
    shuffled = "".join(chunks) + tail
    if len(shuffled) != stat.before_bits:
        raise ValueError("decoded shuffled length mismatch")
    return invert_bit_permutation(shuffled, stat.pass_index)


def encode_shuffle_refresh_layers(bits: str, passes: int) -> ShuffleRefreshEncoded:
    current = bits
    stats: list[ShuffleLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_shuffled_chunk_layer(current, pass_index)
        stats.append(stat)
    return ShuffleRefreshEncoded(current, tuple(stats), bits)


def decode_shuffle_refresh_layers(encoded: ShuffleRefreshEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_shuffled_chunk_layer(current, stat)
    return current


def public_shuffle_refresh_demo(trials: int = 200, n_bits: int = 512, passes: int = 8) -> None:
    print("== family 2l2: public-shuffle scheduled target refresh ==")
    print("Before each fixed-universe chunk pass, a public bit permutation")
    print("changes which bits become neighbors. Decode reverses each layer by")
    print("parsing scheduled chunk tokens, expanding records, and applying the")
    print("public inverse permutation. No pass-varying salt or birth tag is used.")
    print()
    rng = Random(424242)
    rows: dict[int, list[ShuffleLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_visible_delta: list[int] = []
    best_visible_delta: list[int] = []
    final_sparse_delta: list[float] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_shuffle_refresh_layers(bits, passes)
        assert decode_shuffle_refresh_layers(encoded) == bits
        final_visible_delta.append(n_bits - len(encoded.final_bits))
        best_visible_delta.append(max(n_bits - stat.after_bits for stat in encoded.stats))
        final_sparse_delta.append(
            encoded.stats[-1].before_bits - encoded.stats[-1].sparse_charged_bits
        )
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    unique_outputs = len(RECHUNK_BOOK)
    hit_p = unique_outputs / (1 << RECHUNK_L)
    gross = RECHUNK_L - RECHUNK_SEED_BITS
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"literal-token={1 + RECHUNK_L} record={RECHUNK_RECORD_BITS}")
    print(f"fixed universe: unique outputs={unique_outputs} hit_p/chunk={hit_p:.5f} "
          f"gross seed saving={gross} bits")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in bits':>12} {'avg out bits':>13} "
          f"{'chunks':>9} {'hits':>9} {'hit/chunk':>10} "
          f"{'vis delta':>10} {'sparse net':>11}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_chunks = mean(stat.chunks for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        hit_rate = avg_hits / avg_chunks if avg_chunks else 0.0
        visible_delta = avg_in - avg_out
        sparse_net = avg_in - mean(stat.sparse_charged_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:12.2f} {avg_out:13.2f} "
              f"{avg_chunks:9.2f} {avg_hits:9.3f} {hit_rate:10.5f} "
              f"{visible_delta:10.3f} {sparse_net:11.3f}")
    print(f"mean final visible delta vs original={mean(final_visible_delta):.3f} bits")
    print(f"mean best visible intermediate delta vs original={mean(best_visible_delta):.3f} bits")
    print(f"mean last-layer sparse scheduled delta vs that layer input={mean(final_sparse_delta):.3f} bits")
    print()
    print("Reading: public shuffling does maintain fresh adjacency samples;")
    print("hit/chunk stays near the fixed-universe rate instead of decaying.")
    print("But the visible chunk tokens bloat every pass, and even the tighter")
    print("scheduled bitmap ledger is negative because it pays the open/carry")
    print("bitmap. Public adjacency refresh is real target churn, not a hidden")
    print("birth channel, but it is still not net compression for random input.")
    print()


LEFT_CONTEXT_SENTINEL = "0" * RECHUNK_L
LEFT_CONTEXT_SEED_BITS = 9
LEFT_CONTEXT_RECORD_BITS = 1 + LEFT_CONTEXT_SEED_BITS


def left_context_expand(previous_chunk: str, seed: int) -> str:
    return hash_bits("decoded-left-context-neighbor", previous_chunk, seed, n_bits=RECHUNK_L)


@lru_cache(maxsize=32768)
def left_context_book(previous_chunk: str) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << LEFT_CONTEXT_SEED_BITS):
        book.setdefault(left_context_expand(previous_chunk, seed), seed)
    return book


def left_context_lookup(previous_chunk: str, target: str) -> int | None:
    return left_context_book(previous_chunk).get(target)


@dataclass
class LeftContextLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    distinct_contexts: int
    tight_charged_bits: float


@dataclass
class LeftContextEncoded:
    final_bits: str
    stats: tuple[LeftContextLayerStat, ...]
    original_bits: str


def encode_left_context_layer(bits: str, pass_index: int) -> tuple[str, LeftContextLayerStat]:
    shuffled = apply_bit_permutation(bits, pass_index)
    chunks = len(shuffled) // RECHUNK_L
    tail = shuffled[chunks * RECHUNK_L:]
    previous = LEFT_CONTEXT_SENTINEL
    contexts: set[str] = set()
    out: list[str] = []
    hits: list[bool] = []
    seeds: list[int] = []
    literal_chunks: list[str] = []
    for chunk_index in range(chunks):
        contexts.add(previous)
        chunk = shuffled[chunk_index * RECHUNK_L:(chunk_index + 1) * RECHUNK_L]
        seed = left_context_lookup(previous, chunk)
        if seed is None:
            out.append("0" + chunk)
            hits.append(False)
            literal_chunks.append(chunk)
        else:
            out.append("1" + format(seed, f"0{LEFT_CONTEXT_SEED_BITS}b"))
            hits.append(True)
            seeds.append(seed)
        previous = chunk
    if tail:
        out.append(tail)
    hit_count = len(seeds)
    bitmap_bits = log2_choose(chunks, hit_count)
    count_bits = count_class_bits(chunks + 1)
    tight_charged = (
        (chunks - hit_count) * RECHUNK_L
        + hit_count * LEFT_CONTEXT_SEED_BITS
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, LeftContextLayerStat(
        pass_index,
        len(bits),
        len(encoded),
        chunks,
        hit_count,
        len(contexts),
        tight_charged,
    )


def decode_left_context_layer(bits: str, stat: LeftContextLayerStat) -> str:
    previous = LEFT_CONTEXT_SENTINEL
    chunks: list[str] = []
    offset = 0
    for _ in range(stat.chunks):
        if offset >= len(bits):
            raise ValueError("truncated left-context layer")
        tag = bits[offset]
        if tag == "0":
            end = offset + 1 + RECHUNK_L
            if end > len(bits):
                raise ValueError("truncated left-context literal")
            chunk = bits[offset + 1:end]
            offset = end
        elif tag == "1":
            end = offset + LEFT_CONTEXT_RECORD_BITS
            if end > len(bits):
                raise ValueError("truncated left-context record")
            seed = int(bits[offset + 1:end], 2)
            chunk = left_context_expand(previous, seed)
            offset = end
        else:
            raise ValueError(f"invalid left-context tag {tag!r}")
        chunks.append(chunk)
        previous = chunk
    tail = bits[offset:]
    shuffled = "".join(chunks) + tail
    if len(shuffled) != stat.before_bits:
        raise ValueError("left-context decoded length mismatch")
    return invert_bit_permutation(shuffled, stat.pass_index)


def encode_left_context_layers(bits: str, passes: int) -> LeftContextEncoded:
    current = bits
    stats: list[LeftContextLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_left_context_layer(current, pass_index)
        stats.append(stat)
    return LeftContextEncoded(current, tuple(stats), bits)


def decode_left_context_layers(encoded: LeftContextEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_left_context_layer(current, stat)
    return current


def decoded_left_context_nonce_demo(trials: int = 60, n_bits: int = 512, passes: int = 4) -> None:
    print("== family 1m/2l4: decoded-left-context nonce refresh ==")
    print("Each scheduled chunk is salted by the previous decoded chunk in")
    print("the public-shuffled chunk order. The encoder knows that neighbor")
    print("while matching, and the decoder knows it before opening the next")
    print("chunk. This tests stable neighbor identity as a birth-free nonce.")
    print()
    rng = Random(626262)
    rows: dict[int, list[LeftContextLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_delta: list[int] = []
    best_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_left_context_layers(bits, passes)
        assert decode_left_context_layers(encoded) == bits
        final_delta.append(n_bits - len(encoded.final_bits))
        best_delta.append(max(n_bits - stat.after_bits for stat in encoded.stats))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    hit_p = (1 << LEFT_CONTEXT_SEED_BITS) / (1 << RECHUNK_L)
    print(f"toy grammar: span={RECHUNK_L} left_seed={LEFT_CONTEXT_SEED_BITS} "
          f"literal-token={1 + RECHUNK_L} "
          f"record={LEFT_CONTEXT_RECORD_BITS} "
          f"hit_p/context={hit_p:.5f}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in bits':>12} {'avg out bits':>13} "
          f"{'chunks':>9} {'hits':>9} {'hit/chunk':>10} "
          f"{'contexts':>9} {'vis net':>9} {'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_chunks = mean(stat.chunks for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        avg_contexts = mean(stat.distinct_contexts for stat in stats)
        visible_net = avg_in - avg_out
        tight_net = avg_in - mean(stat.tight_charged_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:12.2f} {avg_out:13.2f} "
              f"{avg_chunks:9.2f} {avg_hits:9.3f} {avg_hits / avg_chunks:10.5f} "
              f"{avg_contexts:9.2f} {visible_net:9.3f} {tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_delta):.3f} bits")
    print(f"mean best visible intermediate delta vs original={mean(best_delta):.3f} bits")
    print()
    print("Reading: the previous decoded chunk is a genuine decoder-known")
    print("nonce and remains stable under replacements, unlike a future/right")
    print("neighbor. Public shuffling keeps contexts fresh across passes. But")
    print("only one context is active at each chunk, so arbitrary hit supply is")
    print("not multiplied; the open/carry bitmap still dominates the tight")
    print("ledger and visible tokens bloat the stream.")
    print()


CONTEXT_LANE_TOTAL_SEED_BITS = 10


def context_lane_value(previous_chunk: str, pass_index: int, chunk_index: int, lane_bits: int) -> int:
    if lane_bits == 0:
        return 0
    return int(
        hash_bits(
            "context-lane-value",
            previous_chunk,
            pass_index,
            chunk_index,
            n_bits=lane_bits,
        ),
        2,
    )


def context_lane_expand(
    previous_chunk: str,
    pass_index: int,
    chunk_index: int,
    lane_bits: int,
    local_seed: int,
) -> str:
    local_seed_bits = CONTEXT_LANE_TOTAL_SEED_BITS - lane_bits
    lane = context_lane_value(previous_chunk, pass_index, chunk_index, lane_bits)
    full_seed = (lane << local_seed_bits) | local_seed
    return hash_bits(
        "context-lane-child",
        previous_chunk,
        pass_index,
        chunk_index,
        lane_bits,
        full_seed,
        n_bits=RECHUNK_L,
    )


@lru_cache(maxsize=32768)
def context_lane_book(
    previous_chunk: str,
    pass_index: int,
    chunk_index: int,
    lane_bits: int,
) -> dict[str, int]:
    local_seed_bits = CONTEXT_LANE_TOTAL_SEED_BITS - lane_bits
    book: dict[str, int] = {}
    for local_seed in range(1 << local_seed_bits):
        book.setdefault(
            context_lane_expand(previous_chunk, pass_index, chunk_index, lane_bits, local_seed),
            local_seed,
        )
    return book


def context_lane_lookup(
    previous_chunk: str,
    pass_index: int,
    chunk_index: int,
    lane_bits: int,
    target: str,
) -> int | None:
    return context_lane_book(previous_chunk, pass_index, chunk_index, lane_bits).get(target)


@dataclass
class ContextLaneLayerStat:
    pass_index: int
    lane_bits: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    distinct_contexts: int
    tight_charged_bits: float


@dataclass
class ContextLaneEncoded:
    final_bits: str
    stats: tuple[ContextLaneLayerStat, ...]
    original_bits: str


def encode_context_lane_layer(
    bits: str,
    pass_index: int,
    lane_bits: int,
) -> tuple[str, ContextLaneLayerStat]:
    local_seed_bits = CONTEXT_LANE_TOTAL_SEED_BITS - lane_bits
    shuffled = apply_bit_permutation(bits, pass_index)
    chunks = len(shuffled) // RECHUNK_L
    tail = shuffled[chunks * RECHUNK_L:]
    previous = LEFT_CONTEXT_SENTINEL
    contexts: set[str] = set()
    out: list[str] = []
    hits: list[bool] = []
    seeds: list[int] = []
    for chunk_index in range(chunks):
        contexts.add(previous)
        chunk = shuffled[chunk_index * RECHUNK_L:(chunk_index + 1) * RECHUNK_L]
        seed = context_lane_lookup(previous, pass_index, chunk_index, lane_bits, chunk)
        if seed is None:
            out.append("0" + chunk)
            hits.append(False)
        else:
            seed_bits = "" if local_seed_bits == 0 else format(seed, f"0{local_seed_bits}b")
            out.append("1" + seed_bits)
            hits.append(True)
            seeds.append(seed)
        previous = chunk
    if tail:
        out.append(tail)
    hit_count = len(seeds)
    bitmap_bits = log2_choose(chunks, hit_count)
    count_bits = count_class_bits(chunks + 1)
    tight_charged = (
        (chunks - hit_count) * RECHUNK_L
        + hit_count * local_seed_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, ContextLaneLayerStat(
        pass_index,
        lane_bits,
        len(bits),
        len(encoded),
        chunks,
        hit_count,
        len(contexts),
        tight_charged,
    )


def decode_context_lane_layer(bits: str, stat: ContextLaneLayerStat) -> str:
    local_seed_bits = CONTEXT_LANE_TOTAL_SEED_BITS - stat.lane_bits
    previous = LEFT_CONTEXT_SENTINEL
    chunks: list[str] = []
    offset = 0
    for chunk_index in range(stat.chunks):
        if offset >= len(bits):
            raise ValueError("truncated context-lane layer")
        tag = bits[offset]
        if tag == "0":
            end = offset + 1 + RECHUNK_L
            if end > len(bits):
                raise ValueError("truncated context-lane literal")
            chunk = bits[offset + 1:end]
            offset = end
        elif tag == "1":
            end = offset + 1 + local_seed_bits
            if end > len(bits):
                raise ValueError("truncated context-lane record")
            seed_bits = bits[offset + 1:end]
            local_seed = int(seed_bits, 2) if seed_bits else 0
            chunk = context_lane_expand(
                previous,
                stat.pass_index,
                chunk_index,
                stat.lane_bits,
                local_seed,
            )
            offset = end
        else:
            raise ValueError(f"invalid context-lane tag {tag!r}")
        chunks.append(chunk)
        previous = chunk
    tail = bits[offset:]
    shuffled = "".join(chunks) + tail
    if len(shuffled) != stat.before_bits:
        raise ValueError("context-lane decoded length mismatch")
    return invert_bit_permutation(shuffled, stat.pass_index)


def encode_context_lane_layers(bits: str, passes: int, lane_bits: int) -> ContextLaneEncoded:
    current = bits
    stats: list[ContextLaneLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_context_lane_layer(current, pass_index, lane_bits)
        stats.append(stat)
    return ContextLaneEncoded(current, tuple(stats), bits)


def decode_context_lane_layers(encoded: ContextLaneEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_context_lane_layer(current, stat)
    return current


def context_lane_validity_demo(trials: int = 12, n_bits: int = 256, passes: int = 3) -> None:
    print("== family 1n/3e: context-lane validity grammar ==")
    print("A causal left-neighbor context derives lane bits before opening the")
    print("current chunk. The record stores only the local seed bits inside")
    print("that lane, so the lane is decoder-visible and wrong lanes are")
    print("structurally excluded. This combines context salt with seed-class")
    print("validity and prices the reduced seed supply plus hit map.")
    print()
    rng = Random(737373)
    print(f"toy grammar: span={RECHUNK_L} total_seed={CONTEXT_LANE_TOTAL_SEED_BITS} "
          f"passes={passes} n_bits={n_bits}")
    print(f"{'lane':>4} {'local':>5} {'hit p':>9} {'round':>7} "
          f"{'hit/ch':>9} {'contexts':>9} {'vis final':>10} "
          f"{'tight last':>10} {'closed net':>11}")
    for lane_bits in [0, 2, 4, 6, 8, 10]:
        local_seed_bits = CONTEXT_LANE_TOTAL_SEED_BITS - lane_bits
        pass_rows: dict[int, list[ContextLaneLayerStat]] = {p: [] for p in range(1, passes + 1)}
        final_visible_delta: list[int] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded = encode_context_lane_layers(bits, passes, lane_bits)
            assert decode_context_lane_layers(encoded) == bits
            final_visible_delta.append(n_bits - len(encoded.final_bits))
            for stat in encoded.stats:
                pass_rows[stat.pass_index].append(stat)
        last_stats = pass_rows[passes]
        avg_chunks = mean(stat.chunks for stat in last_stats)
        avg_hits = mean(stat.hits for stat in last_stats)
        hit_rate = avg_hits / avg_chunks if avg_chunks else 0.0
        avg_contexts = mean(stat.distinct_contexts for stat in last_stats)
        tight_last = mean(stat.before_bits - stat.tight_charged_bits for stat in last_stats)
        p = 2.0 ** (local_seed_bits - RECHUNK_L)
        gap = RECHUNK_L - local_seed_bits
        closed_net = p * gap - binary_entropy(p)
        print(f"{lane_bits:4d} {local_seed_bits:5d} {p:9.5f} "
              f"{trials:3d}/{trials:<3d} {hit_rate:9.5f} "
              f"{avg_contexts:9.2f} {mean(final_visible_delta):10.3f} "
              f"{tight_last:10.3f} {closed_net:11.5f}")
    print()
    print("Reading: the context lane is genuinely known before expansion,")
    print("and public shuffling makes those contexts change across passes.")
    print("But only one lane is active for a given chunk. Each lane bit removed")
    print("from the stored seed halves the eligible seed supply; the closed")
    print("uniform ledger remains p*d-H(p)<0, and the exact multi-pass toy")
    print("round-trips while bloating under both visible and tight accounting.")
    print()


CHECKERBOARD_SEED_BITS = 9


def checkerboard_expand(
    left_chunk: str,
    right_chunk: str,
    pass_index: int,
    seed_bits: int,
    seed: int,
) -> str:
    return hash_bits(
        "checkerboard-two-neighbor-context",
        left_chunk,
        right_chunk,
        pass_index % 2,
        seed_bits,
        seed,
        n_bits=RECHUNK_L,
    )


@lru_cache(maxsize=32768)
def checkerboard_book(
    left_chunk: str,
    right_chunk: str,
    pass_index: int,
    seed_bits: int,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        book.setdefault(
            checkerboard_expand(left_chunk, right_chunk, pass_index, seed_bits, seed),
            seed,
        )
    return book


def checkerboard_lookup(
    left_chunk: str,
    right_chunk: str,
    pass_index: int,
    seed_bits: int,
    target: str,
) -> int | None:
    return checkerboard_book(left_chunk, right_chunk, pass_index, seed_bits).get(target)


@dataclass
class CheckerboardContextLayerStat:
    pass_index: int
    seed_bits: int
    before_bits: int
    after_bits: int
    chunks: int
    active_slots: int
    guard_slots: int
    hits: int
    distinct_contexts: int
    tail_bits: int
    tight_charged_bits: float


@dataclass
class CheckerboardContextEncoded:
    final_bits: str
    stats: tuple[CheckerboardContextLayerStat, ...]
    original_bits: str


def checkerboard_neighbors(chunks: list[str], chunk_index: int) -> tuple[str, str]:
    left = chunks[chunk_index - 1] if chunk_index > 0 else LEFT_CONTEXT_SENTINEL
    right = chunks[chunk_index + 1] if chunk_index + 1 < len(chunks) else LEFT_CONTEXT_SENTINEL
    return left, right


def encode_checkerboard_context_layer(
    bits: str,
    pass_index: int,
    seed_bits: int = CHECKERBOARD_SEED_BITS,
) -> tuple[str, CheckerboardContextLayerStat]:
    shuffled = apply_bit_permutation(bits, pass_index)
    chunk_count = len(shuffled) // RECHUNK_L
    tail = shuffled[chunk_count * RECHUNK_L:]
    chunks = [
        shuffled[index * RECHUNK_L:(index + 1) * RECHUNK_L]
        for index in range(chunk_count)
    ]
    phase = pass_index % 2
    out: list[str] = []
    contexts: set[tuple[str, str]] = set()
    active_slots = 0
    hits = 0
    for chunk_index, chunk in enumerate(chunks):
        if chunk_index % 2 != phase:
            out.append(chunk)
            continue
        active_slots += 1
        left, right = checkerboard_neighbors(chunks, chunk_index)
        contexts.add((left, right))
        seed = checkerboard_lookup(left, right, pass_index, seed_bits, chunk)
        if seed is None:
            out.append("0" + chunk)
        else:
            out.append("1" + format(seed, f"0{seed_bits}b"))
            hits += 1
    if tail:
        out.append(tail)
    guard_slots = chunk_count - active_slots
    bitmap_bits = log2_choose(active_slots, hits)
    count_bits = count_class_bits(active_slots + 1)
    tight_charged = (
        guard_slots * RECHUNK_L
        + (active_slots - hits) * RECHUNK_L
        + hits * seed_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, CheckerboardContextLayerStat(
        pass_index,
        seed_bits,
        len(bits),
        len(encoded),
        chunk_count,
        active_slots,
        guard_slots,
        hits,
        len(contexts),
        len(tail),
        tight_charged,
    )


def decode_checkerboard_context_layer(bits: str, stat: CheckerboardContextLayerStat) -> str:
    phase = stat.pass_index % 2
    chunks: list[str | None] = [None] * stat.chunks
    record_seeds: dict[int, int] = {}
    offset = 0
    for chunk_index in range(stat.chunks):
        if chunk_index % 2 != phase:
            end = offset + RECHUNK_L
            if end > len(bits):
                raise ValueError("truncated checkerboard guard")
            chunks[chunk_index] = bits[offset:end]
            offset = end
            continue
        if offset >= len(bits):
            raise ValueError("truncated checkerboard active slot")
        tag = bits[offset]
        if tag == "0":
            end = offset + 1 + RECHUNK_L
            if end > len(bits):
                raise ValueError("truncated checkerboard active literal")
            chunks[chunk_index] = bits[offset + 1:end]
            offset = end
        elif tag == "1":
            end = offset + 1 + stat.seed_bits
            if end > len(bits):
                raise ValueError("truncated checkerboard active record")
            record_seeds[chunk_index] = int(bits[offset + 1:end], 2)
            offset = end
        else:
            raise ValueError(f"invalid checkerboard tag {tag!r}")
    tail = bits[offset:offset + stat.tail_bits]
    if len(tail) != stat.tail_bits:
        raise ValueError("truncated checkerboard tail")
    if offset + stat.tail_bits != len(bits):
        raise ValueError("extra bits after checkerboard layer")
    for chunk_index, seed in record_seeds.items():
        left = chunks[chunk_index - 1] if chunk_index > 0 else LEFT_CONTEXT_SENTINEL
        right = chunks[chunk_index + 1] if chunk_index + 1 < stat.chunks else LEFT_CONTEXT_SENTINEL
        if left is None or right is None:
            raise ValueError("checkerboard record neighbor was not decoded first")
        chunks[chunk_index] = checkerboard_expand(
            left,
            right,
            stat.pass_index,
            stat.seed_bits,
            seed,
        )
    if any(chunk is None for chunk in chunks):
        raise ValueError("checkerboard unresolved chunk")
    shuffled = "".join(chunk for chunk in chunks if chunk is not None) + tail
    if len(shuffled) != stat.before_bits:
        raise ValueError("checkerboard decoded length mismatch")
    return invert_bit_permutation(shuffled, stat.pass_index)


def encode_checkerboard_context_layers(
    bits: str,
    passes: int,
    seed_bits: int = CHECKERBOARD_SEED_BITS,
) -> CheckerboardContextEncoded:
    current = bits
    stats: list[CheckerboardContextLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_checkerboard_context_layer(current, pass_index, seed_bits)
        stats.append(stat)
    return CheckerboardContextEncoded(current, tuple(stats), bits)


def decode_checkerboard_context_layers(encoded: CheckerboardContextEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_checkerboard_context_layer(current, stat)
    return current


def checkerboard_two_neighbor_context_demo(
    trials: int = 20,
    n_bits: int = 256,
    passes: int = 4,
    seed_bits: int = CHECKERBOARD_SEED_BITS,
) -> None:
    print("== family 1o: checkerboard two-neighbor context nonce ==")
    print("A public checkerboard schedule carries one parity of chunks as")
    print("literal guards and attempts records only in the opposite parity.")
    print("Each active slot is salted by both adjacent guard chunks, so the")
    print("decoder knows the left and right nonce values before expanding the")
    print("active record. The phase alternates by public pass index.")
    print()
    rng = Random(828282)
    rows: dict[int, list[CheckerboardContextLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_visible_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_checkerboard_context_layers(bits, passes, seed_bits)
        assert decode_checkerboard_context_layers(encoded) == bits
        final_visible_delta.append(n_bits - len(encoded.final_bits))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    hit_p = 2.0 ** (seed_bits - RECHUNK_L)
    active_closed = hit_p * (RECHUNK_L - seed_bits) - binary_entropy(hit_p)
    all_slot_closed = 0.5 * active_closed
    print(f"toy grammar: span={RECHUNK_L} seed={seed_bits} passes={passes} n_bits={n_bits}")
    print(f"active hit_p/context={hit_p:.5f} active closed net={active_closed:.5f} "
          f"all-slot closed net={all_slot_closed:.5f}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in':>8} {'avg out':>9} {'active':>8} "
          f"{'guards':>8} {'hits':>8} {'hit/act':>9} {'contexts':>9} "
          f"{'vis net':>9} {'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_active = mean(stat.active_slots for stat in stats)
        avg_guards = mean(stat.guard_slots for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        avg_contexts = mean(stat.distinct_contexts for stat in stats)
        visible_net = avg_in - avg_out
        tight_net = avg_in - mean(stat.tight_charged_bits for stat in stats)
        hit_rate = avg_hits / avg_active if avg_active else 0.0
        print(f"{pass_index:4d} {avg_in:8.2f} {avg_out:9.2f} "
              f"{avg_active:8.2f} {avg_guards:8.2f} {avg_hits:8.3f} "
              f"{hit_rate:9.5f} {avg_contexts:9.2f} {visible_net:9.3f} "
              f"{tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_visible_delta):.3f} bits")
    print()
    print("seed-width closed surface, active slots only:")
    print(f"{'seed':>5} {'hit_p':>10} {'gap':>5} {'active net':>11} {'all-slot':>10}")
    for candidate_seed_bits in [6, 7, 8, 9, 10, 11]:
        p = 2.0 ** (candidate_seed_bits - RECHUNK_L)
        gap = RECHUNK_L - candidate_seed_bits
        active_net = p * gap - binary_entropy(p)
        print(f"{candidate_seed_bits:5d} {p:10.5f} {gap:5d} "
              f"{active_net:11.5f} {0.5 * active_net:10.5f}")
    print()
    print("Reading: two-sided guard context fixes the old right-neighbor")
    print("instability: both neighbors are known before expansion, and the")
    print("nonce changes under public shuffle and alternating parity. But the")
    print("price is that half the slots are forced raw guards. For the active")
    print("half, there is still only one decoder-known context per slot. The")
    print("closed uniform ledger remains p*d-H(p)<0, and the exact round-trip")
    print("bloats under visible tags and under the tight active-bitmap ledger.")
    print()


def one_runs(bitmap: tuple[int, ...]) -> int:
    runs = 0
    previous = 0
    for bit in bitmap:
        if bit and not previous:
            runs += 1
        previous = bit
    return runs


def log2_one_run_bitmaps(n_bits: int, ones: int, runs: int) -> float:
    if ones == 0:
        return 0.0 if runs == 0 else float("inf")
    if runs < 1 or runs > ones or runs > n_bits - ones + 1:
        return float("inf")
    return log2_choose(ones - 1, runs - 1) + log2_choose(n_bits - ones + 1, runs)


def bitmap_lower_bound_bits(bitmap: tuple[int, ...]) -> float:
    slots = len(bitmap)
    hits = sum(bitmap)
    run_count = one_runs(bitmap)
    enumerative = count_class_bits(slots + 1) + log2_choose(slots, hits)
    if hits == 0:
        run_coded = count_class_bits(slots + 1)
    else:
        run_coded = (
            count_class_bits(slots + 1)
            + count_class_bits(hits + 1)
            + log2_one_run_bitmaps(slots, hits, run_count)
        )
    return min(enumerative, run_coded)


@dataclass
class SelectedShuffleLayer:
    pass_index: int
    before_bits: int
    choice: int
    choice_count: int
    chunks: int
    tail: str
    bitmap: tuple[int, ...]
    seeds: tuple[int, ...]
    literal_chunks: tuple[str, ...]
    visible_bits: str
    charged_bits: float
    bitmap_bits: float


def evaluate_public_shuffle_choice(
    bits: str,
    pass_index: int,
    choice: int,
    choice_count: int,
) -> SelectedShuffleLayer:
    shuffled = apply_bit_permutation_choice(bits, pass_index, choice)
    chunks = len(shuffled) // RECHUNK_L
    tail = shuffled[chunks * RECHUNK_L:]
    bitmap: list[int] = []
    seeds: list[int] = []
    literals: list[str] = []
    visible_parts: list[str] = []
    for chunk_index in range(chunks):
        start = chunk_index * RECHUNK_L
        chunk = shuffled[start:start + RECHUNK_L]
        seed = RECHUNK_BOOK.get(chunk)
        if seed is None:
            bitmap.append(0)
            literals.append(chunk)
            visible_parts.append("0" + chunk)
            continue
        bitmap.append(1)
        seeds.append(seed)
        visible_parts.append("1" + format(seed, f"0{RECHUNK_SEED_BITS}b"))
    if tail:
        visible_parts.append(tail)
    bitmap_tuple = tuple(bitmap)
    bitmap_bits = bitmap_lower_bound_bits(bitmap_tuple)
    hits = sum(bitmap_tuple)
    charged = (
        (chunks - hits) * RECHUNK_L
        + hits * RECHUNK_SEED_BITS
        + len(tail)
        + bitmap_bits
        + log2(choice_count)
    )
    return SelectedShuffleLayer(
        pass_index,
        len(bits),
        choice,
        choice_count,
        chunks,
        tail,
        bitmap_tuple,
        tuple(seeds),
        tuple(literals),
        "".join(visible_parts),
        charged,
        bitmap_bits,
    )


def select_public_shuffle_layer(bits: str, pass_index: int, choice_count: int) -> SelectedShuffleLayer:
    choices = [
        evaluate_public_shuffle_choice(bits, pass_index, choice, choice_count)
        for choice in range(choice_count)
    ]
    return max(choices, key=lambda layer: layer.before_bits - layer.charged_bits)


def decode_selected_shuffle_layer(layer: SelectedShuffleLayer) -> str:
    chunks: list[str] = []
    seed_index = 0
    literal_index = 0
    for bit in layer.bitmap:
        if bit:
            seed = layer.seeds[seed_index]
            seed_index += 1
            chunks.append(expand_rechunk_seed(seed))
        else:
            chunks.append(layer.literal_chunks[literal_index])
            literal_index += 1
    if seed_index != len(layer.seeds) or literal_index != len(layer.literal_chunks):
        raise ValueError("unused selected-shuffle fields")
    shuffled = "".join(chunks) + layer.tail
    if len(shuffled) != layer.before_bits:
        raise ValueError("selected-shuffle length mismatch")
    return invert_bit_permutation_choice(shuffled, layer.pass_index, layer.choice)


def selected_public_shuffle_hitmap_demo(
    trials: int = 120,
    n_bits: int = 512,
    passes: int = 4,
) -> None:
    print("== family 2l3: selected public-shuffle hitmap shaping ==")
    print("This mutation lets the encoder try K public shuffles and choose the")
    print("one with the best lower-bound hitmap ledger. The decoder receives")
    print("the shuffle index once for the layer, then decodes a bitmap plus")
    print("seeds/literals. The bitmap is priced optimistically as the cheaper")
    print("of count+enumerative coding or count+one-run coding.")
    print()
    rng = Random(515151)
    choice_counts = (1, 4, 16, 64)
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"gross seed saving={RECHUNK_L - RECHUNK_SEED_BITS} bits "
          f"input={n_bits} passes={passes} trials={trials}")
    print(f"{'K':>4} {'pass':>4} {'hits':>9} {'hit/chunk':>10} "
          f"{'runs':>8} {'bitmap':>9} {'K bits':>7} "
          f"{'tight net':>10} {'visible net':>11}")
    for choice_count in choice_counts:
        rows: dict[int, list[SelectedShuffleLayer]] = {p: [] for p in range(1, passes + 1)}
        for _ in range(trials):
            current = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            for pass_index in range(1, passes + 1):
                layer = select_public_shuffle_layer(current, pass_index, choice_count)
                assert decode_selected_shuffle_layer(layer) == current
                rows[pass_index].append(layer)
                current = layer.visible_bits
        for pass_index in range(1, passes + 1):
            layers = rows[pass_index]
            avg_hits = mean(sum(layer.bitmap) for layer in layers)
            avg_chunks = mean(layer.chunks for layer in layers)
            hit_rate = avg_hits / avg_chunks if avg_chunks else 0.0
            avg_runs = mean(one_runs(layer.bitmap) for layer in layers)
            avg_bitmap = mean(layer.bitmap_bits for layer in layers)
            tight_net = mean(layer.before_bits - layer.charged_bits for layer in layers)
            visible_net = mean(layer.before_bits - len(layer.visible_bits) for layer in layers)
            print(f"{choice_count:4d} {pass_index:4d} {avg_hits:9.3f} {hit_rate:10.5f} "
                  f"{avg_runs:8.3f} {avg_bitmap:9.3f} {log2(choice_count):7.3f} "
                  f"{tight_net:10.3f} {visible_net:11.3f}")
    print()
    print("Reading: choosing among public shuffles does improve the selected")
    print("hit map a little, but the improvement is paid by the shuffle index")
    print("and the remaining bitmap entropy. Even with a favorable run-code")
    print("lower bound, the tight ledger stays negative on random inputs.")
    print("The channel bought nicer coordinates; it did not make open/carry")
    print("derivable for free.")
    print()


STATE_RECHUNK_STATE_BITS = 4
STATE_RECHUNK_STATE_COUNT = 1 << STATE_RECHUNK_STATE_BITS


def step_token_state(state: int, token_bits: str, state_bits: int = STATE_RECHUNK_STATE_BITS) -> int:
    mask = (1 << state_bits) - 1
    mixed = state
    for bit in token_bits:
        mixed = ((mixed * 5) ^ (3 if bit == "1" else 1)) & mask
    return mixed


def expand_state_rechunk_seed(state: int, seed: int) -> str:
    return hash_bits("prefix-state-rechunk-universe", state, seed, n_bits=RECHUNK_L)


def build_state_rechunk_books() -> dict[int, dict[str, int]]:
    books: dict[int, dict[str, int]] = {}
    for state in range(STATE_RECHUNK_STATE_COUNT):
        book: dict[str, int] = {}
        for seed in range(1 << RECHUNK_SEED_BITS):
            book.setdefault(expand_state_rechunk_seed(state, seed), seed)
        books[state] = book
    return books


STATE_RECHUNK_BOOKS = build_state_rechunk_books()


@dataclass
class StateRechunkLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    windows: int
    matches: int
    distinct_states: int


@dataclass
class StateRechunkEncoded:
    final_bits: str
    stats: tuple[StateRechunkLayerStat, ...]
    original_bits: str


def encode_state_rechunk_layer(bits: str, pass_index: int) -> tuple[str, StateRechunkLayerStat]:
    out: list[str] = []
    index = 0
    state = 0
    seen_states: set[int] = set()
    matches = 0
    windows = max(0, len(bits) - RECHUNK_L + 1)
    while index < len(bits):
        seen_states.add(state)
        if index + RECHUNK_L <= len(bits):
            seed = STATE_RECHUNK_BOOKS[state].get(bits[index:index + RECHUNK_L])
            if seed is not None:
                token = "1" + format(seed, f"0{RECHUNK_SEED_BITS}b")
                out.append(token)
                state = step_token_state(state, token)
                matches += 1
                index += RECHUNK_L
                continue
        token = "0" + bits[index]
        out.append(token)
        state = step_token_state(state, token)
        index += 1
    encoded = "".join(out)
    return encoded, StateRechunkLayerStat(
        pass_index,
        len(bits),
        len(encoded),
        windows,
        matches,
        len(seen_states),
    )


def decode_state_rechunk_layer(bits: str) -> str:
    out: list[str] = []
    index = 0
    state = 0
    while index < len(bits):
        tag = bits[index]
        if tag == "0":
            if index + 2 > len(bits):
                raise ValueError("truncated state literal")
            token = bits[index:index + 2]
            out.append(bits[index + 1])
            state = step_token_state(state, token)
            index += 2
        elif tag == "1":
            end = index + RECHUNK_RECORD_BITS
            if end > len(bits):
                raise ValueError("truncated state record")
            token = bits[index:end]
            seed = int(bits[index + 1:end], 2)
            out.append(expand_state_rechunk_seed(state, seed))
            state = step_token_state(state, token)
            index = end
        else:
            raise ValueError(f"invalid tag {tag!r}")
    return "".join(out)


def encode_state_rechunk_layers(bits: str, passes: int) -> StateRechunkEncoded:
    current = bits
    stats: list[StateRechunkLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_state_rechunk_layer(current, pass_index)
        stats.append(stat)
        if stat.matches == 0:
            break
    return StateRechunkEncoded(current, tuple(stats), bits)


def decode_state_rechunk_layers(encoded: StateRechunkEncoded) -> str:
    current = encoded.final_bits
    for _ in reversed(encoded.stats):
        current = decode_state_rechunk_layer(current)
    return current


def prefix_state_nonce_demo(trials: int = 200, n_bits: int = 192, passes: int = 6) -> None:
    print("== family 1e/2m: prefix-parse-state nonce layer ==")
    print("Each record expansion is salted by the decoder's current prefix")
    print("token state. Encoder and decoder both know that state before the")
    print("record opens; no nonce field or birth tag is stored.")
    print()
    rng = Random(97531)
    rows: dict[int, list[StateRechunkLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_delta: list[int] = []
    best_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_state_rechunk_layers(bits, passes)
        assert decode_state_rechunk_layers(encoded) == bits
        final_delta.append(len(bits) - len(encoded.final_bits))
        best_delta.append(max(len(bits) - stat.after_bits for stat in encoded.stats))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    avg_unique = mean(len(book) for book in STATE_RECHUNK_BOOKS.values())
    hit_p = avg_unique / (1 << RECHUNK_L)
    print(f"toy grammar: state_bits={STATE_RECHUNK_STATE_BITS} "
          f"literal={RECHUNK_LITERAL_BITS} bits record={RECHUNK_RECORD_BITS} bits "
          f"span={RECHUNK_L} bits")
    print(f"mean unique outputs/state={avg_unique:.1f} hit_p/state-window={hit_p:.5f}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in bits':>12} {'avg out bits':>13} "
          f"{'avg windows':>12} {'avg matches':>12} {'hit/window':>11} "
          f"{'states':>8} {'delta vs orig':>13}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_windows = mean(stat.windows for stat in stats)
        avg_matches = mean(stat.matches for stat in stats)
        avg_states = mean(stat.distinct_states for stat in stats)
        hit_rate = avg_matches / avg_windows if avg_windows else 0.0
        delta_orig = n_bits - avg_out
        print(f"{pass_index:4d} {avg_in:12.2f} {avg_out:13.2f} "
              f"{avg_windows:12.2f} {avg_matches:12.3f} {hit_rate:11.5f} "
              f"{avg_states:8.2f} {delta_orig:13.3f}")
    print(f"mean final delta vs original={mean(final_delta):.3f} bits")
    print(f"mean best intermediate delta vs original={mean(best_delta):.3f} bits")
    print()
    print("Reading: prefix parse state is a real decoder-known nonce and it")
    print("does refresh which seed outputs are tried at different token states.")
    print("It does not multiply coverage at a given position: only one state is")
    print("active there. The visible-token format still pays literal carriage,")
    print("so random/unshaped inputs bloat rather than maintain compression.")
    print()


@dataclass
class SparsePrefixMatch:
    position: int
    seed: int


@dataclass
class SparsePrefixEncoded:
    length: int
    matches: tuple[SparsePrefixMatch, ...]
    literals: str


@dataclass
class SparsePrefixStat:
    length: int
    windows: int
    matches: int
    literal_bits: int
    seed_bits: int
    optimistic_map_bits: float
    count_bits: float
    charged_bits: float


def nonoverlap_interval_map_bits(length: int, span: int, count: int) -> float:
    if count == 0:
        return 0.0
    return log2_choose(length - (span - 1) * count, count)


def count_class_bits(classes: int) -> float:
    if classes <= 1:
        return 0.0
    return log2(classes)


def encode_sparse_prefix_state(bits: str) -> tuple[SparsePrefixEncoded, SparsePrefixStat]:
    state = 0
    index = 0
    literals: list[str] = []
    matches: list[SparsePrefixMatch] = []
    windows = max(0, len(bits) - RECHUNK_L + 1)
    while index < len(bits):
        if index + RECHUNK_L <= len(bits):
            seed = STATE_RECHUNK_BOOKS[state].get(bits[index:index + RECHUNK_L])
            if seed is not None:
                span = bits[index:index + RECHUNK_L]
                matches.append(SparsePrefixMatch(index, seed))
                state = step_token_state(state, span)
                index += RECHUNK_L
                continue
        literals.append(bits[index])
        state = step_token_state(state, bits[index])
        index += 1
    map_bits = nonoverlap_interval_map_bits(len(bits), RECHUNK_L, len(matches))
    seed_bits = len(matches) * RECHUNK_SEED_BITS
    literal_bits = len(literals)
    max_matches = len(bits) // RECHUNK_L
    count_bits = count_class_bits(max_matches + 1)
    charged_bits = literal_bits + seed_bits + map_bits + count_bits
    return (
        SparsePrefixEncoded(len(bits), tuple(matches), "".join(literals)),
        SparsePrefixStat(
            len(bits),
            windows,
            len(matches),
            literal_bits,
            seed_bits,
            map_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_sparse_prefix_state(encoded: SparsePrefixEncoded) -> str:
    by_position = {match.position: match.seed for match in encoded.matches}
    out: list[str] = []
    state = 0
    literal_index = 0
    position = 0
    while position < encoded.length:
        seed = by_position.get(position)
        if seed is not None:
            span = expand_state_rechunk_seed(state, seed)
            out.append(span)
            state = step_token_state(state, span)
            position += RECHUNK_L
            continue
        if literal_index >= len(encoded.literals):
            raise ValueError("sparse literal stream exhausted")
        bit = encoded.literals[literal_index]
        literal_index += 1
        out.append(bit)
        state = step_token_state(state, bit)
        position += 1
    if literal_index != len(encoded.literals):
        raise ValueError("unused sparse literals")
    return "".join(out)


def sparse_prefix_state_accounting_demo(trials: int = 200, n_bits: int = 512) -> None:
    print("== family 1f: sparse-map prefix-state accounting ==")
    print("This removes the prefix-token literal overhead from the previous")
    print("state-nonce layer. The layer stores only miss bits, record seeds,")
    print("and an optimistic enumerative map of non-overlapping record spans.")
    print("The map is priced as log2 C(n-(L-1)m, m), plus log2(max_m+1)")
    print("for the match-count class.")
    print()
    rng = Random(86420)
    stats: list[SparsePrefixStat] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded, stat = encode_sparse_prefix_state(bits)
        assert decode_sparse_prefix_state(encoded) == bits
        stats.append(stat)
    avg_matches = mean(stat.matches for stat in stats)
    avg_windows = mean(stat.windows for stat in stats)
    avg_literal_bits = mean(stat.literal_bits for stat in stats)
    avg_seed_bits = mean(stat.seed_bits for stat in stats)
    avg_map_bits = mean(stat.optimistic_map_bits for stat in stats)
    avg_count_bits = mean(stat.count_bits for stat in stats)
    avg_charged = mean(stat.charged_bits for stat in stats)
    avg_gross = mean(stat.matches * (RECHUNK_L - RECHUNK_SEED_BITS) for stat in stats)
    hit_rate = avg_matches / avg_windows if avg_windows else 0.0
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"gross/match={RECHUNK_L - RECHUNK_SEED_BITS} state_bits={STATE_RECHUNK_STATE_BITS}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'n bits':>7} {'matches':>9} {'hit/window':>11} {'literals':>10} "
          f"{'seed bits':>10} {'map bits':>10} {'count':>8} "
          f"{'charged':>10} {'net':>10}")
    print(f"{n_bits:7d} {avg_matches:9.3f} {hit_rate:11.5f} {avg_literal_bits:10.3f} "
          f"{avg_seed_bits:10.3f} {avg_map_bits:10.3f} "
          f"{avg_count_bits:8.3f} {avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
    print(f"mean gross seed-span saving before map={avg_gross:.3f} bits")
    print(f"mean optimistic map+count cost={avg_map_bits + avg_count_bits:.3f} bits")
    print()
    print("Reading: sparse-map accounting removes the bad literal-token")
    print("format and keeps exact stateless decode. The selected-hit map then")
    print("costs about the same order as the seed-span savings. This is the")
    print("same conservation law as window multiplicity, now tested on the")
    print("maintained prefix-state match process itself.")
    print()


@dataclass
class ScheduledSlotEncoded:
    length: int
    slots: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass
class ScheduledSlotStat:
    length: int
    slots: int
    hits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def encode_scheduled_slots(bits: str) -> tuple[ScheduledSlotEncoded, ScheduledSlotStat]:
    slots = len(bits) // RECHUNK_L
    tail = bits[slots * RECHUNK_L:]
    state = 0
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        start = slot * RECHUNK_L
        chunk = bits[start:start + RECHUNK_L]
        seed = STATE_RECHUNK_BOOKS[state].get(chunk)
        if seed is not None:
            hits.append(True)
            seeds.append(seed)
        else:
            hits.append(False)
            literals.append(chunk)
        state = step_token_state(state, chunk)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    bitmap_bits = log2_choose(slots, len(seeds))
    count_bits = count_class_bits(slots + 1)
    charged_bits = literal_bits + seed_bits + bitmap_bits + count_bits
    return (
        ScheduledSlotEncoded(len(bits), slots, tuple(hits), tuple(seeds), "".join(literals), tail),
        ScheduledSlotStat(len(bits), slots, len(seeds), literal_bits, seed_bits, bitmap_bits,
                          count_bits, charged_bits),
    )


def decode_scheduled_slots(encoded: ScheduledSlotEncoded) -> str:
    state = 0
    seed_index = 0
    literal_index = 0
    out: list[str] = []
    for hit in encoded.hits:
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            chunk = expand_state_rechunk_seed(state, seed)
        else:
            chunk = encoded.literals[literal_index:literal_index + RECHUNK_L]
            if len(chunk) != RECHUNK_L:
                raise ValueError("scheduled literal stream exhausted")
            literal_index += RECHUNK_L
        out.append(chunk)
        state = step_token_state(state, chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused scheduled seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused scheduled literals")
    out.append(encoded.tail)
    return "".join(out)


def binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * log2(p)) - ((1.0 - p) * log2(1.0 - p))


def scheduled_slot_bitmap_demo(trials: int = 200, n_bits: int = 512) -> None:
    print("== family 1g: scheduled-slot bitmap accounting ==")
    print("This removes the sparse selected-span map by using public fixed")
    print("non-overlapping slots. The only open/carry channel is the hit")
    print("bitmap, priced optimistically as log2 C(slots, hits) plus")
    print("log2(slots+1) for the hit-count class.")
    print()
    rng = Random(112233)
    stats: list[ScheduledSlotStat] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded, stat = encode_scheduled_slots(bits)
        assert decode_scheduled_slots(encoded) == bits
        stats.append(stat)
    avg_hits = mean(stat.hits for stat in stats)
    avg_slots = mean(stat.slots for stat in stats)
    avg_literal_bits = mean(stat.literal_bits for stat in stats)
    avg_seed_bits = mean(stat.seed_bits for stat in stats)
    avg_bitmap_bits = mean(stat.bitmap_bits for stat in stats)
    avg_count_bits = mean(stat.count_bits for stat in stats)
    avg_charged = mean(stat.charged_bits for stat in stats)
    hit_rate = avg_hits / avg_slots if avg_slots else 0.0
    print(f"toy grammar: slot_span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"gross/hit={RECHUNK_L - RECHUNK_SEED_BITS} state_bits={STATE_RECHUNK_STATE_BITS}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'n bits':>7} {'slots':>7} {'hits':>8} {'hit/slot':>10} "
          f"{'literals':>10} {'seed bits':>10} {'bitmap':>10} "
          f"{'count':>8} {'charged':>10} {'net':>10}")
    print(f"{n_bits:7d} {avg_slots:7.2f} {avg_hits:8.3f} {hit_rate:10.5f} "
          f"{avg_literal_bits:10.3f} {avg_seed_bits:10.3f} "
          f"{avg_bitmap_bits:10.3f} {avg_count_bits:8.3f} "
          f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
    print()
    print("Closed-form scheduled-slot expectation under the uniform hash law:")
    print(f"{'gap d=L-r':>9} {'p=2^-d':>11} {'save p*d':>11} "
          f"{'H(p)':>11} {'net/slot':>11}")
    for gap in [1, 2, 3, 4, 6, 8, 12, 16]:
        p = 2 ** (-gap)
        save = p * gap
        entropy = binary_entropy(p)
        print(f"{gap:9d} {p:11.5f} {save:11.5f} "
              f"{entropy:11.5f} {save - entropy:11.5f}")
    print()
    print("Reading: public scheduling removes the position map, but the hit")
    print("bitmap becomes the open/carry channel. With random independent hits,")
    print("the bitmap entropy is larger than the expected seed-span savings")
    print("for every positive gap in the sweep.")
    print()


@dataclass(frozen=True)
class PhaseSlotLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    phase: int
    phase_bits: int
    slots: int
    hits: int
    prefix_bits: int
    tail_bits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    tight_bits: float


@dataclass(frozen=True)
class PhaseSlotEncoded:
    final_bits: str
    stats: tuple[PhaseSlotLayerStat, ...]
    original_bits: str


def encode_phase_slot_layer_for_phase(
    bits: str,
    pass_index: int,
    phase: int,
) -> tuple[str, PhaseSlotLayerStat]:
    phase_bits = ceil(log2(RECHUNK_L))
    if phase < 0 or phase >= RECHUNK_L or phase > len(bits):
        raise ValueError("invalid phase-selected slot phase")
    prefix = bits[:phase]
    body = bits[phase:]
    slots = len(body) // RECHUNK_L
    tail = body[slots * RECHUNK_L:]
    state = step_token_state(0, prefix)
    out: list[str] = [format(phase, f"0{phase_bits}b"), prefix]
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        start = phase + slot * RECHUNK_L
        chunk = bits[start:start + RECHUNK_L]
        seed = STATE_RECHUNK_BOOKS[state].get(chunk)
        if seed is not None:
            out.append("1" + format(seed, f"0{RECHUNK_SEED_BITS}b"))
            hits.append(True)
            seeds.append(seed)
        else:
            out.append("0" + chunk)
            hits.append(False)
            literals.append(chunk)
        state = step_token_state(state, chunk)
    out.append(tail)
    literal_bits = len(prefix) + sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    bitmap_bits = log2_choose(slots, len(seeds))
    count_bits = count_class_bits(slots + 1)
    tight_bits = phase_bits + literal_bits + seed_bits + bitmap_bits + count_bits
    encoded = "".join(out)
    return (
        encoded,
        PhaseSlotLayerStat(
            pass_index,
            len(bits),
            len(encoded),
            phase,
            phase_bits,
            slots,
            len(seeds),
            len(prefix),
            len(tail),
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            tight_bits,
        ),
    )


def encode_phase_slot_layer(bits: str, pass_index: int) -> tuple[str, PhaseSlotLayerStat]:
    max_phase = min(RECHUNK_L - 1, len(bits))
    candidates = [
        encode_phase_slot_layer_for_phase(bits, pass_index, phase)
        for phase in range(max_phase + 1)
    ]
    return min(
        candidates,
        key=lambda item: (item[1].tight_bits, item[1].after_bits, item[1].phase),
    )


def decode_phase_slot_layer(encoded: str, stat: PhaseSlotLayerStat) -> str:
    offset = 0
    if len(encoded) < stat.phase_bits:
        raise ValueError("truncated phase-selected phase")
    phase = int(encoded[offset:offset + stat.phase_bits], 2)
    if phase != stat.phase:
        raise ValueError("wrong phase-selected phase")
    offset += stat.phase_bits
    prefix = encoded[offset:offset + stat.prefix_bits]
    if len(prefix) != stat.prefix_bits:
        raise ValueError("truncated phase-selected prefix")
    offset += stat.prefix_bits
    state = step_token_state(0, prefix)
    out: list[str] = [prefix]
    for _ in range(stat.slots):
        if offset >= len(encoded):
            raise ValueError("truncated phase-selected slot tag")
        tag = encoded[offset]
        offset += 1
        if tag == "1":
            end = offset + RECHUNK_SEED_BITS
            if end > len(encoded):
                raise ValueError("truncated phase-selected seed")
            seed = int(encoded[offset:end], 2)
            offset = end
            chunk = expand_state_rechunk_seed(state, seed)
        elif tag == "0":
            end = offset + RECHUNK_L
            if end > len(encoded):
                raise ValueError("truncated phase-selected literal")
            chunk = encoded[offset:end]
            offset = end
        else:
            raise ValueError("invalid phase-selected slot tag")
        out.append(chunk)
        state = step_token_state(state, chunk)
    tail = encoded[offset:offset + stat.tail_bits]
    if len(tail) != stat.tail_bits:
        raise ValueError("truncated phase-selected tail")
    offset += stat.tail_bits
    if offset != len(encoded):
        raise ValueError("extra bits after phase-selected layer")
    out.append(tail)
    decoded = "".join(out)
    if len(decoded) != stat.before_bits:
        raise ValueError("phase-selected decoded length mismatch")
    return decoded


def encode_phase_slot_layers(bits: str, passes: int) -> PhaseSlotEncoded:
    current = bits
    stats: list[PhaseSlotLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_phase_slot_layer(current, pass_index)
        stats.append(stat)
    return PhaseSlotEncoded(current, tuple(stats), bits)


def decode_phase_slot_layers(encoded: PhaseSlotEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_phase_slot_layer(current, stat)
    return current


def try_decode_phase_slot_without_phase(
    body: str,
    before_bits: int,
    phase: int,
) -> str | None:
    if phase < 0 or phase >= RECHUNK_L or phase > before_bits:
        return None
    offset = 0
    prefix = body[offset:offset + phase]
    if len(prefix) != phase:
        return None
    offset += phase
    state = step_token_state(0, prefix)
    out: list[str] = [prefix]
    remaining = before_bits - phase
    slots = remaining // RECHUNK_L
    tail_bits = remaining - slots * RECHUNK_L
    for _ in range(slots):
        if offset >= len(body):
            return None
        tag = body[offset]
        offset += 1
        if tag == "1":
            end = offset + RECHUNK_SEED_BITS
            if end > len(body):
                return None
            seed = int(body[offset:end], 2)
            offset = end
            chunk = expand_state_rechunk_seed(state, seed)
        elif tag == "0":
            end = offset + RECHUNK_L
            if end > len(body):
                return None
            chunk = body[offset:end]
            offset = end
        else:
            return None
        out.append(chunk)
        state = step_token_state(state, chunk)
    tail = body[offset:offset + tail_bits]
    if len(tail) != tail_bits:
        return None
    offset += tail_bits
    if offset != len(body):
        return None
    decoded = "".join(out + [tail])
    if len(decoded) != before_bits:
        return None
    return decoded


def phase_slot_omitted_phase_candidates(
    encoded: str,
    stat: PhaseSlotLayerStat,
) -> tuple[int, bool]:
    body = encoded[stat.phase_bits:]
    candidates = {
        decoded
        for phase in range(min(RECHUNK_L - 1, stat.before_bits) + 1)
        for decoded in [try_decode_phase_slot_without_phase(body, stat.before_bits, phase)]
        if decoded is not None
    }
    original = decode_phase_slot_layer(encoded, stat)
    return len(candidates), original in candidates


def phase_selected_slot_refresh_demo(
    trials: int = 160,
    n_bits: int = 512,
    passes: int = 5,
    ambiguity_trials: int = 80,
    ambiguity_bits: int = 84,
) -> None:
    print("== family 1g2/2s: phase-selected scheduled slots ==")
    print("The encoder chooses one public slot phase for the whole layer and")
    print("stores that phase once. The phase changes which windows are tested,")
    print("while the hit bitmap/count still carries open vs carry.")
    print()
    rng = Random(121212)
    rows: dict[int, list[PhaseSlotLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_visible_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_phase_slot_layers(bits, passes)
        assert decode_phase_slot_layers(encoded) == bits
        final_visible_delta.append(len(bits) - len(encoded.final_bits))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)

    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"phase_bits={ceil(log2(RECHUNK_L))} passes={passes} n_bits={n_bits}")
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in':>9} {'avg out':>9} {'phase':>7} "
          f"{'slots':>7} {'hits':>7} {'hit/slot':>9} {'vis net':>9} "
          f"{'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        if not stats:
            continue
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_slots = mean(stat.slots for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        hit_rate = avg_hits / avg_slots if avg_slots else 0.0
        avg_phase = mean(stat.phase for stat in stats)
        visible_net = mean(stat.before_bits - stat.after_bits for stat in stats)
        tight_net = mean(stat.before_bits - stat.tight_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:9.2f} {avg_out:9.2f} {avg_phase:7.2f} "
              f"{avg_slots:7.2f} {avg_hits:7.3f} {hit_rate:9.5f} "
              f"{visible_net:9.3f} {tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_visible_delta):.3f} bits")

    ambiguity_counts: list[int] = []
    ambiguity_bits_list: list[float] = []
    present = 0
    for _ in range(ambiguity_trials):
        bits = format(rng.getrandbits(ambiguity_bits), f"0{ambiguity_bits}b")
        encoded_bits, stat = encode_phase_slot_layer(bits, 1)
        count, original_present = phase_slot_omitted_phase_candidates(encoded_bits, stat)
        ambiguity_counts.append(count)
        ambiguity_bits_list.append(log2(count) if count else 0.0)
        present += int(original_present)
    print()
    print("Omitted-phase ambiguity on small one-layer encodings:")
    print(f"layers={ambiguity_trials} before_bits={ambiguity_bits} "
          f"avg_candidates={mean(ambiguity_counts):.3f} "
          f"avg_log2={mean(ambiguity_bits_list):.3f} present={present}/{ambiguity_trials}")
    print()
    print("Reading: selecting the best phase does refresh target coordinates")
    print("and raises hit density versus one fixed scheduled alignment. The")
    print("phase itself is cheap but not free, and the bitmap/count bill remains")
    print("larger than the seed-span savings. Omitting the phase only converts")
    print("that field into finite trial-decode ambiguity.")
    print()


ROLL_LANE_L = 12
ROLL_LANE_SEED_BITS = 8


def expand_rolling_lane_seed(state: int, lane: int, seed: int) -> str:
    return hash_bits("rolling-state-lane-ensemble", state, lane, seed, n_bits=ROLL_LANE_L)


@lru_cache(maxsize=16)
def rolling_lane_books(lanes: int) -> tuple[dict[str, tuple[int, int]], ...]:
    books: list[dict[str, tuple[int, int]]] = []
    for state in range(STATE_RECHUNK_STATE_COUNT):
        book: dict[str, tuple[int, int]] = {}
        for lane in range(lanes):
            for seed in range(1 << ROLL_LANE_SEED_BITS):
                book.setdefault(expand_rolling_lane_seed(state, lane, seed), (lane, seed))
        books.append(book)
    return tuple(books)


@dataclass(frozen=True)
class RollingLaneEncoded:
    length: int
    lanes: int
    slots: int
    hits: tuple[bool, ...]
    chosen_lanes: tuple[int, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class RollingLaneStat:
    lanes: int
    slots: int
    hits: int
    unique_outputs_per_state: float
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    lane_bits: int
    free_lane_bits: float
    stored_lane_bits: float
    ambiguity_lower_bits: float


def encode_rolling_lane_layer(bits: str, lanes: int) -> tuple[RollingLaneEncoded, RollingLaneStat]:
    books = rolling_lane_books(lanes)
    slots = len(bits) // ROLL_LANE_L
    tail = bits[slots * ROLL_LANE_L:]
    state = 0
    hits: list[bool] = []
    chosen_lanes: list[int] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        start = slot * ROLL_LANE_L
        chunk = bits[start:start + ROLL_LANE_L]
        witness = books[state].get(chunk)
        if witness is None:
            hits.append(False)
            literals.append(chunk)
        else:
            lane, seed = witness
            hits.append(True)
            chosen_lanes.append(lane)
            seeds.append(seed)
        state = step_token_state(state, chunk)
    hit_count = len(seeds)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = hit_count * ROLL_LANE_SEED_BITS
    bitmap_bits = log2_choose(slots, hit_count)
    count_bits = count_class_bits(slots + 1)
    lane_bits_per_hit = 0 if lanes <= 1 else ceil(log2(lanes))
    lane_bits = hit_count * lane_bits_per_hit
    free_lane_bits = literal_bits + seed_bits + bitmap_bits + count_bits
    stored_lane_bits = free_lane_bits + lane_bits
    ambiguity_lower_bits = free_lane_bits + hit_count * log2(lanes)
    unique_outputs = mean(len(book) for book in books)
    return (
        RollingLaneEncoded(
            len(bits),
            lanes,
            slots,
            tuple(hits),
            tuple(chosen_lanes),
            tuple(seeds),
            "".join(literals),
            tail,
        ),
        RollingLaneStat(
            lanes,
            slots,
            hit_count,
            unique_outputs,
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            lane_bits,
            free_lane_bits,
            stored_lane_bits,
            ambiguity_lower_bits,
        ),
    )


def decode_rolling_lane_layer(encoded: RollingLaneEncoded) -> str:
    state = 0
    seed_index = 0
    lane_index = 0
    literal_index = 0
    out: list[str] = []
    for hit in encoded.hits:
        if hit:
            seed = encoded.seeds[seed_index]
            lane = encoded.chosen_lanes[lane_index]
            seed_index += 1
            lane_index += 1
            chunk = expand_rolling_lane_seed(state, lane, seed)
        else:
            chunk = encoded.literals[literal_index:literal_index + ROLL_LANE_L]
            if len(chunk) != ROLL_LANE_L:
                raise ValueError("rolling-lane literal stream exhausted")
            literal_index += ROLL_LANE_L
        out.append(chunk)
        state = step_token_state(state, chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused rolling-lane seeds")
    if lane_index != len(encoded.chosen_lanes):
        raise ValueError("unused rolling-lane lanes")
    if literal_index != len(encoded.literals):
        raise ValueError("unused rolling-lane literals")
    out.append(encoded.tail)
    return "".join(out)


def rolling_lane_candidate_count(
    encoded: RollingLaneEncoded,
    cap: int = 200_000,
) -> tuple[int, bool, bool]:
    candidates: set[tuple[int, str]] = {(0, "")}
    capped = False
    seed_index = 0
    literal_index = 0
    for hit in encoded.hits:
        next_candidates: set[tuple[int, str]] = set()
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            for state, prefix in candidates:
                for lane in range(encoded.lanes):
                    chunk = expand_rolling_lane_seed(state, lane, seed)
                    next_candidates.add((step_token_state(state, chunk), prefix + chunk))
                    if len(next_candidates) >= cap:
                        capped = True
                        break
                if capped:
                    break
        else:
            chunk = encoded.literals[literal_index:literal_index + ROLL_LANE_L]
            literal_index += ROLL_LANE_L
            for state, prefix in candidates:
                next_candidates.add((step_token_state(state, chunk), prefix + chunk))
        candidates = next_candidates
        if capped:
            break
    if not capped:
        candidates = {(state, prefix + encoded.tail) for state, prefix in candidates}
    original = decode_rolling_lane_layer(encoded)
    original_present = any(bits == original for _, bits in candidates)
    return len(candidates), capped, original_present


def rolling_state_lane_ensemble_demo(
    trials: int = 160,
    n_bits: int = 480,
    ambiguity_trials: int = 40,
    ambiguity_bits: int = 72,
) -> None:
    print("== family 1q: rolling-state public lane ensemble ==")
    print("The decoder-known rolling state selects a state-specific seed")
    print("universe. This mutation adds K public lanes per state but does not")
    print("store the lane in the free ledger. Stored-lane and ambiguity ledgers")
    print("price the missing lane selector.")
    print()
    rng = Random(646464)
    print(f"toy grammar: span={ROLL_LANE_L} seed={ROLL_LANE_SEED_BITS} "
          f"state_bits={STATE_RECHUNK_STATE_BITS} n_bits={n_bits}")
    print(f"{'K':>3} {'uniq/state':>10} {'hit/slot':>9} {'free net':>10} "
          f"{'stored net':>11} {'ambig LB':>10} {'lane bits':>10}")
    for lanes in [1, 2, 4, 8]:
        stats: list[RollingLaneStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_rolling_lane_layer(bits, lanes)
            assert decode_rolling_lane_layer(encoded) == bits
            stats.append(stat)
        avg_slots = mean(stat.slots for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        avg_unique = mean(stat.unique_outputs_per_state for stat in stats)
        hit_rate = avg_hits / avg_slots if avg_slots else 0.0
        free_net = n_bits - mean(stat.free_lane_bits for stat in stats)
        stored_net = n_bits - mean(stat.stored_lane_bits for stat in stats)
        ambiguity_net = n_bits - mean(stat.ambiguity_lower_bits for stat in stats)
        avg_lane_bits = mean(stat.lane_bits for stat in stats)
        print(f"{lanes:3d} {avg_unique:10.1f} {hit_rate:9.5f} {free_net:10.3f} "
              f"{stored_net:11.3f} {ambiguity_net:10.3f} {avg_lane_bits:10.3f}")

    print()
    print("Exact omitted-lane ambiguity on smaller layers:")
    print(f"{'K':>3} {'hits':>8} {'candidates':>11} {'ambig':>9} "
          f"{'present':>8} {'ambig net':>11}")
    for lanes in [2, 4, 8]:
        counts: list[int] = []
        hits: list[int] = []
        present = 0
        capped = 0
        ambig_nets: list[float] = []
        for _ in range(ambiguity_trials):
            bits = format(rng.getrandbits(ambiguity_bits), f"0{ambiguity_bits}b")
            encoded, stat = encode_rolling_lane_layer(bits, lanes)
            count, was_capped, original_present = rolling_lane_candidate_count(encoded)
            counts.append(count)
            hits.append(stat.hits)
            present += int(original_present)
            capped += int(was_capped)
            ambiguity = log2(count) if count else 0.0
            ambig_nets.append(ambiguity_bits - stat.free_lane_bits - ambiguity)
        suffix = "+" if capped else ""
        print(f"{lanes:3d} {mean(hits):8.3f} {mean(counts):11.2f}{suffix:1s} "
              f"{mean(log2(count) if count else 0.0 for count in counts):9.3f} "
              f"{present:3d}/{ambiguity_trials:<4d} {mean(ambig_nets):11.3f}")

    print()
    print("Closed-form lane expectation, ignoring collisions:")
    print(f"{'K':>3} {'p~K2^-d':>10} {'free':>10} {'stored/amb':>12}")
    gap = ROLL_LANE_L - ROLL_LANE_SEED_BITS
    base_p = 2.0 ** (-gap)
    for lanes in [1, 2, 4, 8, 16]:
        p = min(1.0, lanes * base_p)
        entropy = binary_entropy(p)
        free = p * gap - entropy
        stored = p * (gap - log2(lanes)) - entropy
        print(f"{lanes:3d} {p:10.5f} {free:10.5f} {stored:12.5f}")
    print()
    print("Reading: K lanes are real fresh dice because the rolling state is")
    print("known before expansion. The tempting positive rows are precisely the")
    print("rows where the lane selector is free. Once the lane is stored, or an")
    print("end checksum/referee must distinguish K lane readings per hit, the")
    print("gain flips negative under the uniform hash law.")
    print()


def lane_sequence_entropy_bits(lanes: tuple[int, ...], lane_count: int) -> tuple[float, float, float]:
    """Return histogram, assignment, and total enumerative bits for lane labels."""
    if not lanes:
        return 0.0, 0.0, 0.0
    counts = Counter(lanes)
    hist_bits = log2_choose(len(lanes) + lane_count - 1, lane_count - 1)
    assignment_bits = log2_factorial(len(lanes)) - sum(
        log2_factorial(counts.get(lane, 0)) for lane in range(lane_count)
    )
    return hist_bits, assignment_bits, hist_bits + assignment_bits


def rolling_lane_collective_selector_demo(trials: int = 160, n_bits: int = 480) -> None:
    print("== family 1q3: collective rolling-lane selector entropy ==")
    print("This re-prices the positive rolling-lane row without assuming a")
    print("fixed lane header per record. The encoder stores lane counts plus")
    print("an enumerative assignment of selected lanes to hit records. The")
    print("count-only ledger is shown as an invalid histogram-only oracle.")
    print()
    rng = Random(686868)
    print(f"toy grammar: span={ROLL_LANE_L} seed={ROLL_LANE_SEED_BITS} n_bits={n_bits}")
    print(f"{'K':>3} {'hits':>8} {'free':>9} {'hist':>8} {'assign':>9} "
          f"{'count net':>10} {'enum net':>10} {'fixed net':>10}")
    for lanes in [2, 4, 8]:
        hits: list[int] = []
        free_nets: list[float] = []
        hist_bits: list[float] = []
        assignment_bits: list[float] = []
        count_only_nets: list[float] = []
        enum_nets: list[float] = []
        fixed_nets: list[float] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_rolling_lane_layer(bits, lanes)
            assert decode_rolling_lane_layer(encoded) == bits
            hist, assignment, total = lane_sequence_entropy_bits(encoded.chosen_lanes, lanes)
            hits.append(stat.hits)
            free_nets.append(n_bits - stat.free_lane_bits)
            hist_bits.append(hist)
            assignment_bits.append(assignment)
            count_only_nets.append(n_bits - stat.free_lane_bits - hist)
            enum_nets.append(n_bits - stat.free_lane_bits - total)
            fixed_nets.append(n_bits - stat.stored_lane_bits)
        print(f"{lanes:3d} {mean(hits):8.3f} {mean(free_nets):9.3f} "
              f"{mean(hist_bits):8.3f} {mean(assignment_bits):9.3f} "
              f"{mean(count_only_nets):10.3f} {mean(enum_nets):10.3f} "
              f"{mean(fixed_nets):10.3f}")

    print()
    print("Reading: collective coding is cheaper than fixed ceil(log K) lane")
    print("headers when selected lanes are slightly skewed, but the assignment")
    print("of lane labels to ordered hit records is still the selector channel.")
    print("Count histograms alone can look positive; histogram plus assignment")
    print("flips the free-lane rows negative again.")
    print()


def partition_lane_for_seed(seed: int, lanes: int) -> int:
    return 0 if lanes <= 1 else seed % lanes


def expand_partition_lane_seed(state: int, lanes: int, seed: int) -> str:
    lane = partition_lane_for_seed(seed, lanes)
    return hash_bits("rolling-state-partition-lane", state, lanes, lane, seed, n_bits=ROLL_LANE_L)


@lru_cache(maxsize=16)
def partition_lane_books(lanes: int) -> tuple[dict[str, int], ...]:
    books: list[dict[str, int]] = []
    for state in range(STATE_RECHUNK_STATE_COUNT):
        book: dict[str, int] = {}
        for seed in range(1 << ROLL_LANE_SEED_BITS):
            book.setdefault(expand_partition_lane_seed(state, lanes, seed), seed)
        books.append(book)
    return tuple(books)


def output_lane(bits: str, lanes: int) -> int:
    if lanes <= 1:
        return 0
    lane_bits = ceil(log2(lanes))
    return int(hash_bits("rolling-output-derived-lane", bits, n_bits=lane_bits), 2) % lanes


def expand_output_lane_seed(state: int, lane: int, seed: int) -> str:
    return hash_bits("rolling-state-output-lane", state, lane, seed, n_bits=ROLL_LANE_L)


def output_consistent_chunks(state: int, lanes: int, seed: int) -> tuple[str, ...]:
    chunks: list[str] = []
    for lane in range(lanes):
        chunk = expand_output_lane_seed(state, lane, seed)
        if output_lane(chunk, lanes) == lane:
            chunks.append(chunk)
    return tuple(chunks)


@lru_cache(maxsize=16)
def output_consistent_lane_books(lanes: int) -> tuple[dict[str, int], ...]:
    books: list[dict[str, int]] = []
    for state in range(STATE_RECHUNK_STATE_COUNT):
        book: dict[str, int] = {}
        for seed in range(1 << ROLL_LANE_SEED_BITS):
            for chunk in output_consistent_chunks(state, lanes, seed):
                book.setdefault(chunk, seed)
        books.append(book)
    return tuple(books)


@dataclass(frozen=True)
class DerivableLaneEncoded:
    length: int
    lanes: int
    mode: str
    slots: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class DerivableLaneStat:
    lanes: int
    mode: str
    slots: int
    hits: int
    unique_outputs_per_state: float
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def encode_derivable_lane_layer(
    bits: str,
    lanes: int,
    mode: str,
) -> tuple[DerivableLaneEncoded, DerivableLaneStat]:
    if mode == "seed-partition":
        books = partition_lane_books(lanes)
    elif mode == "output-consistent":
        books = output_consistent_lane_books(lanes)
    else:
        raise ValueError(f"unknown derivable lane mode {mode!r}")
    slots = len(bits) // ROLL_LANE_L
    tail = bits[slots * ROLL_LANE_L:]
    state = 0
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        start = slot * ROLL_LANE_L
        chunk = bits[start:start + ROLL_LANE_L]
        seed = books[state].get(chunk)
        if seed is None:
            hits.append(False)
            literals.append(chunk)
        else:
            hits.append(True)
            seeds.append(seed)
        state = step_token_state(state, chunk)
    hit_count = len(seeds)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = hit_count * ROLL_LANE_SEED_BITS
    bitmap_bits = log2_choose(slots, hit_count)
    count_bits = count_class_bits(slots + 1)
    charged_bits = literal_bits + seed_bits + bitmap_bits + count_bits
    unique_outputs = mean(len(book) for book in books)
    return (
        DerivableLaneEncoded(len(bits), lanes, mode, slots, tuple(hits), tuple(seeds), "".join(literals), tail),
        DerivableLaneStat(
            lanes,
            mode,
            slots,
            hit_count,
            unique_outputs,
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_seed_partition_lane_layer(encoded: DerivableLaneEncoded) -> str:
    if encoded.mode != "seed-partition":
        raise ValueError("deterministic lane decode requires seed-partition mode")
    state = 0
    seed_index = 0
    literal_index = 0
    out: list[str] = []
    for hit in encoded.hits:
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            chunk = expand_partition_lane_seed(state, encoded.lanes, seed)
        else:
            chunk = encoded.literals[literal_index:literal_index + ROLL_LANE_L]
            if len(chunk) != ROLL_LANE_L:
                raise ValueError("seed-partition literal stream exhausted")
            literal_index += ROLL_LANE_L
        out.append(chunk)
        state = step_token_state(state, chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused seed-partition seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused seed-partition literals")
    out.append(encoded.tail)
    return "".join(out)


def output_consistent_lane_candidates(
    encoded: DerivableLaneEncoded,
    cap: int = 200_000,
) -> tuple[set[str], bool]:
    if encoded.mode != "output-consistent":
        raise ValueError("candidate lane decode requires output-consistent mode")
    candidates: set[tuple[int, str]] = {(0, "")}
    seed_index = 0
    literal_index = 0
    capped = False
    for hit in encoded.hits:
        next_candidates: set[tuple[int, str]] = set()
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            for state, prefix in candidates:
                for chunk in output_consistent_chunks(state, encoded.lanes, seed):
                    next_candidates.add((step_token_state(state, chunk), prefix + chunk))
                    if len(next_candidates) >= cap:
                        capped = True
                        break
                if capped:
                    break
        else:
            chunk = encoded.literals[literal_index:literal_index + ROLL_LANE_L]
            if len(chunk) != ROLL_LANE_L:
                raise ValueError("output-consistent literal stream exhausted")
            literal_index += ROLL_LANE_L
            for state, prefix in candidates:
                next_candidates.add((step_token_state(state, chunk), prefix + chunk))
        candidates = next_candidates
        if capped:
            break
    if capped:
        return {bits for _, bits in candidates}, True
    return {prefix + encoded.tail for _, prefix in candidates}, False


def derivable_lane_variants_demo(
    trials: int = 160,
    n_bits: int = 480,
    ambiguity_trials: int = 80,
    ambiguity_bits: int = 120,
) -> None:
    print("== family 1q2: derivable rolling-lane selectors ==")
    print("This mutates the positive free-lane result by making the lane")
    print("decoder-derivable. In seed-partition mode, the stored seed names")
    print("one public lane. In output-consistent mode, the expanded output must")
    print("hash back to its lane, so the decoder can trial lanes without a")
    print("stored lane id.")
    print()
    rng = Random(676767)
    print(f"toy grammar: span={ROLL_LANE_L} seed={ROLL_LANE_SEED_BITS} n_bits={n_bits}")
    print(f"{'mode':>18} {'K':>3} {'uniq/state':>10} {'hit/slot':>9} "
          f"{'charged':>10} {'net':>10}")
    for mode in ["seed-partition", "output-consistent"]:
        for lanes in [1, 2, 4, 8]:
            stats: list[DerivableLaneStat] = []
            for _ in range(trials):
                bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
                encoded, stat = encode_derivable_lane_layer(bits, lanes, mode)
                if mode == "seed-partition":
                    assert decode_seed_partition_lane_layer(encoded) == bits
                else:
                    # The full ambiguity set is measured below on smaller layers.
                    assert bits in output_consistent_lane_candidates(encoded, cap=1_000_000)[0]
                stats.append(stat)
            avg_slots = mean(stat.slots for stat in stats)
            avg_hits = mean(stat.hits for stat in stats)
            hit_rate = avg_hits / avg_slots if avg_slots else 0.0
            avg_unique = mean(stat.unique_outputs_per_state for stat in stats)
            avg_charged = mean(stat.charged_bits for stat in stats)
            print(f"{mode:>18} {lanes:3d} {avg_unique:10.1f} {hit_rate:9.5f} "
                  f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
        print()

    print("Output-consistent omitted-lane ambiguity on smaller layers:")
    print(f"{'K':>3} {'hits':>8} {'candidates':>11} {'ambig':>9} "
          f"{'present':>8} {'charged net':>12}")
    for lanes in [2, 4, 8]:
        counts: list[int] = []
        hits: list[int] = []
        present = 0
        capped = 0
        nets: list[float] = []
        for _ in range(ambiguity_trials):
            bits = format(rng.getrandbits(ambiguity_bits), f"0{ambiguity_bits}b")
            encoded, stat = encode_derivable_lane_layer(bits, lanes, "output-consistent")
            candidates, was_capped = output_consistent_lane_candidates(encoded)
            counts.append(len(candidates))
            hits.append(stat.hits)
            present += int(bits in candidates)
            capped += int(was_capped)
            ambiguity = log2(len(candidates)) if candidates else 0.0
            nets.append(ambiguity_bits - stat.charged_bits - ambiguity)
        suffix = "+" if capped else ""
        print(f"{lanes:3d} {mean(hits):8.3f} {mean(counts):11.2f}{suffix:1s} "
              f"{mean(log2(count) if count else 0.0 for count in counts):9.3f} "
              f"{present:3d}/{ambiguity_trials:<4d} {mean(nets):12.3f}")

    print()
    print("Closed-form expectation:")
    print(f"{'mode':>18} {'K':>3} {'p':>10} {'net/slot':>11}")
    gap = ROLL_LANE_L - ROLL_LANE_SEED_BITS
    p = 2.0 ** (-gap)
    for lanes in [1, 2, 4, 8, 16]:
        print(f"{'seed-partition':>18} {lanes:3d} {p:10.5f} "
              f"{p * gap - binary_entropy(p):11.5f}")
    for lanes in [1, 2, 4, 8, 16]:
        # K lanes each survive the output-lane check with probability 1/K.
        print(f"{'output-consistent':>18} {lanes:3d} {p:10.5f} "
              f"{p * gap - binary_entropy(p):11.5f}")
    print()
    print("Reading: deriving the lane removes the stored lane field, but it")
    print("also removes the K-fold coverage that made the free-lane ledger")
    print("positive. Seed partitioning gives one lane per seed; output")
    print("consistency gives roughly one self-consistent lane per seed. The")
    print("remaining hit bitmap/count and occasional candidate ambiguity keep")
    print("the uniform ledger negative.")
    print()


@dataclass(frozen=True)
class ParentSummaryEncoded:
    length: int
    summary_bits: int
    group_size: int
    groups: int
    summaries: tuple[int, ...]
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class ParentSummaryStat:
    summary_bits: int
    group_size: int
    groups: int
    slots: int
    hits: int
    parent_bits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def parent_summary_value(group_bits: str, summary_bits: int) -> int:
    if summary_bits == 0:
        return 0
    return int(hash_bits("parent-summary-value", group_bits, n_bits=summary_bits), 2)


@lru_cache(maxsize=16384)
def parent_summary_book(summary_bits: int, summary: int, local_slot: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << RECHUNK_SEED_BITS):
        out = hash_bits(
            "parent-summary-child",
            summary_bits,
            summary,
            local_slot,
            seed,
            n_bits=RECHUNK_L,
        )
        book.setdefault(out, seed)
    return book


def parent_summary_expand(summary_bits: int, summary: int, local_slot: int, seed: int) -> str:
    return hash_bits(
        "parent-summary-child",
        summary_bits,
        summary,
        local_slot,
        seed,
        n_bits=RECHUNK_L,
    )


def encode_parent_summary_slots(
    bits: str,
    group_size: int,
    summary_bits: int,
) -> tuple[ParentSummaryEncoded, ParentSummaryStat]:
    group_bits_len = group_size * RECHUNK_L
    groups = len(bits) // group_bits_len
    tail = bits[groups * group_bits_len:]
    summaries: list[int] = []
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for group in range(groups):
        group_start = group * group_bits_len
        raw_group = bits[group_start:group_start + group_bits_len]
        summary = parent_summary_value(raw_group, summary_bits)
        summaries.append(summary)
        for local_slot in range(group_size):
            start = group_start + local_slot * RECHUNK_L
            chunk = bits[start:start + RECHUNK_L]
            seed = parent_summary_book(summary_bits, summary, local_slot).get(chunk)
            if seed is None:
                hits.append(False)
                literals.append(chunk)
            else:
                hits.append(True)
                seeds.append(seed)
    slots = groups * group_size
    parent_bits = groups * summary_bits
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    bitmap_bits = log2_choose(slots, len(seeds))
    count_bits = count_class_bits(slots + 1)
    charged_bits = parent_bits + literal_bits + seed_bits + bitmap_bits + count_bits
    return (
        ParentSummaryEncoded(
            len(bits),
            summary_bits,
            group_size,
            groups,
            tuple(summaries),
            tuple(hits),
            tuple(seeds),
            "".join(literals),
            tail,
        ),
        ParentSummaryStat(
            summary_bits,
            group_size,
            groups,
            slots,
            len(seeds),
            parent_bits,
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_parent_summary_slots(encoded: ParentSummaryEncoded) -> str:
    seed_index = 0
    literal_index = 0
    hit_index = 0
    out: list[str] = []
    for group, summary in enumerate(encoded.summaries):
        group_chunks: list[str] = []
        for local_slot in range(encoded.group_size):
            hit = encoded.hits[hit_index]
            hit_index += 1
            if hit:
                seed = encoded.seeds[seed_index]
                seed_index += 1
                chunk = parent_summary_expand(encoded.summary_bits, summary, local_slot, seed)
            else:
                chunk = encoded.literals[literal_index:literal_index + RECHUNK_L]
                if len(chunk) != RECHUNK_L:
                    raise ValueError("parent-summary literal stream exhausted")
                literal_index += RECHUNK_L
            group_chunks.append(chunk)
        group_bits = "".join(group_chunks)
        if parent_summary_value(group_bits, encoded.summary_bits) != summary:
            raise ValueError(f"parent summary mismatch in group {group}")
        out.append(group_bits)
    if hit_index != len(encoded.hits):
        raise ValueError("unused parent-summary hit bits")
    if seed_index != len(encoded.seeds):
        raise ValueError("unused parent-summary seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused parent-summary literals")
    out.append(encoded.tail)
    return "".join(out)


def parent_summary_nonce_demo(trials: int = 80, n_bits: int = 1024) -> None:
    print("== family 1g2: parent-summary nonce amortization ==")
    print("A public group stores a small parent summary before its children.")
    print("Every child expansion is salted by that parent state and local slot,")
    print("so the decoder knows the salt before opening child records. The")
    print("parent summary is verified after children decode and is charged once")
    print("per group.")
    print()
    rng = Random(747474)
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} n_bits={n_bits}")
    print(f"{'summary':>7} {'g slots':>7} {'groups':>7} {'hits':>8} "
          f"{'hit/slot':>10} {'parent':>8} {'bitmap':>10} "
          f"{'charged':>10} {'net':>10}")
    for summary_bits in [0, 2, 4, 6]:
        for group_size in [2, 4, 8, 16]:
            stats: list[ParentSummaryStat] = []
            for _ in range(trials):
                bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
                encoded, stat = encode_parent_summary_slots(bits, group_size, summary_bits)
                assert decode_parent_summary_slots(encoded) == bits
                stats.append(stat)
            avg_groups = mean(stat.groups for stat in stats)
            avg_hits = mean(stat.hits for stat in stats)
            avg_slots = mean(stat.slots for stat in stats)
            avg_parent = mean(stat.parent_bits for stat in stats)
            avg_bitmap = mean(stat.bitmap_bits + stat.count_bits for stat in stats)
            avg_charged = mean(stat.charged_bits for stat in stats)
            print(f"{summary_bits:7d} {group_size:7d} {avg_groups:7.1f} "
                  f"{avg_hits:8.3f} {avg_hits / avg_slots:10.5f} "
                  f"{avg_parent:8.1f} {avg_bitmap:10.3f} "
                  f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
        print()
    print("Closed-form parent-summary expectation:")
    print(f"{'summary':>7} {'g slots':>7} {'parent/g':>10} {'p':>10} "
          f"{'save/slot':>10} {'H(p)':>10} {'net/slot':>10}")
    p = 2 ** (RECHUNK_SEED_BITS - RECHUNK_L)
    save = p * (RECHUNK_L - RECHUNK_SEED_BITS)
    entropy = binary_entropy(p)
    for summary_bits in [0, 2, 4, 6]:
        for group_size in [2, 4, 8, 16]:
            parent_per_slot = summary_bits / group_size
            print(f"{summary_bits:7d} {group_size:7d} {parent_per_slot:10.3f} "
                  f"{p:10.5f} {save:10.5f} {entropy:10.5f} "
                  f"{save - entropy - parent_per_slot:10.5f}")
        print()
    print("Reading: parent state is a real decoder-known salt and can be")
    print("verified after child decode. But each child still has only one")
    print("active parent state. The summary bits are metadata, not extra")
    print("coverage, so amortizing them over a group only makes the already")
    print("negative bitmap ledger more negative.")
    print()


EDGE_TOTAL_SEED_BITS = RECHUNK_SEED_BITS


@dataclass(frozen=True)
class ScheduledEdgeEncoded:
    length: int
    pass_index: int
    edge_bits: int
    slots: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class ScheduledEdgeStat:
    edge_bits: int
    pass_index: int
    slots: int
    hits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def scheduled_edge_class(pass_index: int, slot: int, edge_bits: int) -> int:
    if edge_bits == 0:
        return 0
    return int(hash_bits("scheduled-edge-class", pass_index, slot, n_bits=edge_bits), 2)


def scheduled_edge_expand(pass_index: int, slot: int, edge_bits: int, local_seed: int) -> str:
    edge_class = scheduled_edge_class(pass_index, slot, edge_bits)
    return hash_bits("scheduled-edge-expand", pass_index, slot, edge_bits, edge_class,
                     local_seed, n_bits=RECHUNK_L)


def build_scheduled_edge_books(pass_index: int, edge_bits: int, slots: int) -> tuple[dict[str, int], ...]:
    local_seed_bits = EDGE_TOTAL_SEED_BITS - edge_bits
    if local_seed_bits < 0:
        raise ValueError("edge bits exceed total seed bits")
    books: list[dict[str, int]] = []
    for slot in range(slots):
        book: dict[str, int] = {}
        for local_seed in range(1 << local_seed_bits):
            book.setdefault(scheduled_edge_expand(pass_index, slot, edge_bits, local_seed), local_seed)
        books.append(book)
    return tuple(books)


def encode_scheduled_edges(
    bits: str,
    pass_index: int,
    edge_bits: int,
    books: tuple[dict[str, int], ...],
) -> tuple[ScheduledEdgeEncoded, ScheduledEdgeStat]:
    local_seed_bits = EDGE_TOTAL_SEED_BITS - edge_bits
    slots = len(bits) // RECHUNK_L
    tail = bits[slots * RECHUNK_L:]
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        chunk = bits[slot * RECHUNK_L:(slot + 1) * RECHUNK_L]
        seed = books[slot].get(chunk)
        if seed is None:
            hits.append(False)
            literals.append(chunk)
        else:
            hits.append(True)
            seeds.append(seed)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * local_seed_bits
    bitmap_bits = log2_choose(slots, len(seeds))
    count_bits = count_class_bits(slots + 1)
    charged_bits = literal_bits + seed_bits + bitmap_bits + count_bits
    return (
        ScheduledEdgeEncoded(
            len(bits), pass_index, edge_bits, slots, tuple(hits), tuple(seeds), "".join(literals), tail,
        ),
        ScheduledEdgeStat(
            edge_bits,
            pass_index,
            slots,
            len(seeds),
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_scheduled_edges(encoded: ScheduledEdgeEncoded) -> str:
    seed_index = 0
    literal_index = 0
    out: list[str] = []
    for slot, hit in enumerate(encoded.hits):
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            chunk = scheduled_edge_expand(encoded.pass_index, slot, encoded.edge_bits, seed)
        else:
            chunk = encoded.literals[literal_index:literal_index + RECHUNK_L]
            if len(chunk) != RECHUNK_L:
                raise ValueError("scheduled-edge literal stream exhausted")
            literal_index += RECHUNK_L
        out.append(chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused scheduled-edge seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused scheduled-edge literals")
    out.append(encoded.tail)
    return "".join(out)


def scheduled_edge_exclusion_demo(trials: int = 80, n_bits: int = 1024, passes: int = 3) -> None:
    print("== family 1j: scheduled-edge exclusion rules ==")
    print("A public (pass, slot) edge class is used as a decoder-known salt.")
    print("The stored seed omits those class bits, so the schedule can refresh")
    print("dice without a per-record class field. The cost is fewer eligible")
    print("seeds in each scheduled slot plus the usual hit bitmap.")
    print()
    rng = Random(606060)
    slots = n_bits // RECHUNK_L
    print(f"toy grammar: span={RECHUNK_L} total_seed={EDGE_TOTAL_SEED_BITS} slots={slots}")
    print(f"{'edge':>5} {'local':>5} {'pass':>4} {'hits':>8} {'hit/slot':>10} "
          f"{'bitmap':>10} {'count':>8} {'charged':>10} {'net':>10}")
    for edge_bits in [0, 1, 2, 3, 4]:
        local_seed_bits = EDGE_TOTAL_SEED_BITS - edge_bits
        books_by_pass = {
            pass_index: build_scheduled_edge_books(pass_index, edge_bits, slots)
            for pass_index in range(1, passes + 1)
        }
        for pass_index in range(1, passes + 1):
            stats: list[ScheduledEdgeStat] = []
            for _ in range(trials):
                bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
                encoded, stat = encode_scheduled_edges(
                    bits, pass_index, edge_bits, books_by_pass[pass_index],
                )
                assert decode_scheduled_edges(encoded) == bits
                stats.append(stat)
            avg_hits = mean(stat.hits for stat in stats)
            avg_slots = mean(stat.slots for stat in stats)
            avg_bitmap = mean(stat.bitmap_bits for stat in stats)
            avg_count = mean(stat.count_bits for stat in stats)
            avg_charged = mean(stat.charged_bits for stat in stats)
            print(f"{edge_bits:5d} {local_seed_bits:5d} {pass_index:4d} "
                  f"{avg_hits:8.3f} {avg_hits / avg_slots:10.5f} "
                  f"{avg_bitmap:10.3f} {avg_count:8.3f} "
                  f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
        print()
    print("Closed-form scheduled-edge expectation:")
    print(f"{'edge':>5} {'local':>5} {'p':>11} {'gross':>7} {'H(p)':>11} {'net/slot':>11}")
    for edge_bits in [0, 1, 2, 3, 4, 6, 8]:
        local_seed_bits = EDGE_TOTAL_SEED_BITS - edge_bits
        p = 2 ** (local_seed_bits - RECHUNK_L)
        gross = RECHUNK_L - local_seed_bits
        entropy = binary_entropy(p)
        print(f"{edge_bits:5d} {local_seed_bits:5d} {p:11.5e} "
              f"{gross:7d} {entropy:11.5e} {p * gross - entropy:11.5e}")
    print()
    print("Reading: the public schedule does give fresh decoder-known salts")
    print("across passes and slots. But every omitted class bit removes half")
    print("the eligible seed supply. With the open/carry bitmap priced, the")
    print("uniform ledger remains negative; the schedule is a valid salt, not")
    print("a compression subsidy.")
    print()


VARIABLE_CLASS_OPTIONS = (
    (10,),
    (9, 10),
    (8, 9, 10),
    (6, 8, 10),
    (4, 6, 8, 10),
)


@dataclass(frozen=True)
class VariableSeedClassEncoded:
    length: int
    pass_index: int
    seed_bits_options: tuple[int, ...]
    class_bits: int
    slots: int
    hits: tuple[bool, ...]
    classes: tuple[int, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class VariableSeedClassStat:
    seed_bits_options: tuple[int, ...]
    pass_index: int
    class_bits: int
    slots: int
    hits: int
    literal_bits: int
    record_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def variable_seed_class_expand(pass_index: int, class_id: int, seed_bits: int, seed: int) -> str:
    return hash_bits("variable-seed-length-class", pass_index, class_id, seed_bits, seed, n_bits=RECHUNK_L)


def variable_seed_class_books(
    pass_index: int,
    seed_bits_options: tuple[int, ...],
) -> tuple[dict[str, int], ...]:
    books: list[dict[str, int]] = []
    for class_id, seed_bits in enumerate(seed_bits_options):
        book: dict[str, int] = {}
        for seed in range(1 << seed_bits):
            book.setdefault(variable_seed_class_expand(pass_index, class_id, seed_bits, seed), seed)
        books.append(book)
    return tuple(books)


def fixed_class_bits(class_count: int) -> int:
    if class_count <= 1:
        return 0
    return ceil(log2(class_count))


def encode_variable_seed_classes(
    bits: str,
    pass_index: int,
    seed_bits_options: tuple[int, ...],
    books: tuple[dict[str, int], ...],
) -> tuple[VariableSeedClassEncoded, VariableSeedClassStat]:
    class_bits = fixed_class_bits(len(seed_bits_options))
    slots = len(bits) // RECHUNK_L
    tail = bits[slots * RECHUNK_L:]
    # Shorter records are tried first. Longer classes are useful only when
    # shorter seed-length universes miss the slot.
    class_order = sorted(range(len(seed_bits_options)),
                         key=lambda class_id: (class_bits + seed_bits_options[class_id], class_id))
    hits: list[bool] = []
    classes: list[int] = []
    seeds: list[int] = []
    literals: list[str] = []
    for slot in range(slots):
        chunk = bits[slot * RECHUNK_L:(slot + 1) * RECHUNK_L]
        accepted: tuple[int, int] | None = None
        for class_id in class_order:
            seed = books[class_id].get(chunk)
            if seed is not None:
                accepted = (class_id, seed)
                break
        if accepted is None:
            hits.append(False)
            literals.append(chunk)
        else:
            class_id, seed = accepted
            hits.append(True)
            classes.append(class_id)
            seeds.append(seed)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    record_bits = sum(class_bits + seed_bits_options[class_id] for class_id in classes)
    bitmap_bits = log2_choose(slots, len(seeds))
    count_bits = count_class_bits(slots + 1)
    charged_bits = literal_bits + record_bits + bitmap_bits + count_bits
    return (
        VariableSeedClassEncoded(
            len(bits),
            pass_index,
            seed_bits_options,
            class_bits,
            slots,
            tuple(hits),
            tuple(classes),
            tuple(seeds),
            "".join(literals),
            tail,
        ),
        VariableSeedClassStat(
            seed_bits_options,
            pass_index,
            class_bits,
            slots,
            len(seeds),
            literal_bits,
            record_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_variable_seed_classes(encoded: VariableSeedClassEncoded) -> str:
    class_index = 0
    seed_index = 0
    literal_index = 0
    out: list[str] = []
    for hit in encoded.hits:
        if hit:
            class_id = encoded.classes[class_index]
            class_index += 1
            seed = encoded.seeds[seed_index]
            seed_index += 1
            seed_bits = encoded.seed_bits_options[class_id]
            chunk = variable_seed_class_expand(encoded.pass_index, class_id, seed_bits, seed)
        else:
            chunk = encoded.literals[literal_index:literal_index + RECHUNK_L]
            if len(chunk) != RECHUNK_L:
                raise ValueError("variable-class literal stream exhausted")
            literal_index += RECHUNK_L
        out.append(chunk)
    if class_index != len(encoded.classes):
        raise ValueError("unused variable-class ids")
    if seed_index != len(encoded.seeds):
        raise ValueError("unused variable-class seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused variable-class literals")
    out.append(encoded.tail)
    return "".join(out)


def variable_seed_class_expected(seed_bits_options: tuple[int, ...]) -> tuple[float, float, float, float]:
    class_bits = fixed_class_bits(len(seed_bits_options))
    ordered = sorted(seed_bits_options, key=lambda seed_bits: (class_bits + seed_bits, seed_bits))
    miss_probability = 1.0
    expected_gross = 0.0
    p_any = 0.0
    for seed_bits in ordered:
        p_class = 2 ** (seed_bits - RECHUNK_L)
        hit_here = miss_probability * p_class
        p_any += hit_here
        expected_gross += hit_here * (RECHUNK_L - class_bits - seed_bits)
        miss_probability *= (1.0 - p_class)
    entropy = binary_entropy(p_any)
    return p_any, expected_gross, entropy, expected_gross - entropy


def variable_seed_length_class_demo(trials: int = 80, n_bits: int = 1024, passes: int = 3) -> None:
    print("== family 1k: seed-length class as decoder-known nonce ==")
    print("The record class chooses a seed length and is known before expansion,")
    print("so it can salt the hash output. Hits store a fixed-width class id")
    print("plus the seed; misses are carried through a scheduled hit bitmap.")
    print()
    rng = Random(515151)
    print(f"toy grammar: span={RECHUNK_L} slots={n_bits // RECHUNK_L}")
    print(f"{'classes':>13} {'cbits':>5} {'pass':>4} {'hits':>8} {'hit/slot':>10} "
          f"{'record':>10} {'bitmap':>10} {'charged':>10} {'net':>10}")
    for seed_bits_options in VARIABLE_CLASS_OPTIONS:
        books_by_pass = {
            pass_index: variable_seed_class_books(pass_index, seed_bits_options)
            for pass_index in range(1, passes + 1)
        }
        label = "/".join(str(seed_bits) for seed_bits in seed_bits_options)
        for pass_index in range(1, passes + 1):
            stats: list[VariableSeedClassStat] = []
            for _ in range(trials):
                bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
                encoded, stat = encode_variable_seed_classes(
                    bits, pass_index, seed_bits_options, books_by_pass[pass_index],
                )
                assert decode_variable_seed_classes(encoded) == bits
                stats.append(stat)
            avg_hits = mean(stat.hits for stat in stats)
            avg_slots = mean(stat.slots for stat in stats)
            avg_record = mean(stat.record_bits for stat in stats)
            avg_bitmap = mean(stat.bitmap_bits + stat.count_bits for stat in stats)
            avg_charged = mean(stat.charged_bits for stat in stats)
            print(f"{label:>13} {fixed_class_bits(len(seed_bits_options)):5d} {pass_index:4d} "
                  f"{avg_hits:8.3f} {avg_hits / avg_slots:10.5f} "
                  f"{avg_record:10.3f} {avg_bitmap:10.3f} "
                  f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
        print()
    print("Closed-form variable-class expectation under independent hash outputs:")
    print(f"{'classes':>13} {'p any':>11} {'E gross':>11} {'H(p)':>11} {'net/slot':>11}")
    for seed_bits_options in VARIABLE_CLASS_OPTIONS:
        p_any, expected_gross, entropy, net = variable_seed_class_expected(seed_bits_options)
        label = "/".join(str(seed_bits) for seed_bits in seed_bits_options)
        print(f"{label:>13} {p_any:11.5e} {expected_gross:11.5e} "
              f"{entropy:11.5e} {net:11.5e}")
    print()
    print("Reading: seed length is genuinely decoder-known before expansion,")
    print("and multiple seed classes raise hit probability. The class id and")
    print("longer seed addresses are paid inside each hit, while the bitmap")
    print("still carries open/carry. Under the uniform law the extra classes")
    print("do not overcome their own class/address and bitmap entropy.")
    print()


def seed_prefix_nonce_expand(
    pass_index: int,
    prefix_bits: int,
    total_seed_bits: int,
    prefix: int,
    suffix: int,
) -> str:
    return hash_bits(
        "seed-prefix-nonce-split",
        pass_index,
        prefix_bits,
        total_seed_bits,
        prefix,
        suffix,
        n_bits=RECHUNK_L,
    )


def fixed_width_bits(value: int, width: int) -> str:
    if width == 0:
        return ""
    return format(value, f"0{width}b")


@lru_cache(maxsize=512)
def seed_prefix_nonce_book(
    pass_index: int,
    prefix_bits: int,
    total_seed_bits: int,
) -> dict[str, tuple[int, int]]:
    suffix_bits = total_seed_bits - prefix_bits
    if suffix_bits < 0:
        raise ValueError("prefix bits exceed total seed bits")
    book: dict[str, tuple[int, int]] = {}
    for prefix in range(1 << prefix_bits):
        for suffix in range(1 << suffix_bits):
            book.setdefault(
                seed_prefix_nonce_expand(
                    pass_index,
                    prefix_bits,
                    total_seed_bits,
                    prefix,
                    suffix,
                ),
                (prefix, suffix),
            )
    return book


@lru_cache(maxsize=4096)
def seed_prefix_omitted_choices(
    pass_index: int,
    prefix_bits: int,
    total_seed_bits: int,
    suffix: int,
) -> int:
    outputs = {
        seed_prefix_nonce_expand(
            pass_index,
            prefix_bits,
            total_seed_bits,
            prefix,
            suffix,
        )
        for prefix in range(1 << prefix_bits)
    }
    return len(outputs)


@dataclass(frozen=True)
class SeedPrefixNonceLayerStat:
    pass_index: int
    prefix_bits: int
    suffix_bits: int
    before_bits: int
    after_bits: int
    slots: int
    hits: int
    literal_bits: int
    bitmap_bits: float
    count_bits: float
    tight_bits: float
    fantasy_bits: float
    omitted_prefix_ambiguity: float


@dataclass(frozen=True)
class SeedPrefixNonceEncoded:
    final_bits: str
    stats: tuple[SeedPrefixNonceLayerStat, ...]
    original_bits: str
    total_seed_bits: int


def encode_seed_prefix_nonce_layer(
    bits: str,
    pass_index: int,
    prefix_bits: int,
    total_seed_bits: int,
) -> tuple[str, SeedPrefixNonceLayerStat]:
    suffix_bits = total_seed_bits - prefix_bits
    if suffix_bits < 0:
        raise ValueError("prefix bits exceed total seed bits")
    slots = len(bits) // RECHUNK_L
    tail = bits[slots * RECHUNK_L:]
    book = seed_prefix_nonce_book(pass_index, prefix_bits, total_seed_bits)
    out: list[str] = []
    hits = 0
    literals: list[str] = []
    omitted_ambiguity = 0.0
    for slot in range(slots):
        chunk = bits[slot * RECHUNK_L:(slot + 1) * RECHUNK_L]
        witness = book.get(chunk)
        if witness is None:
            out.append("0" + chunk)
            literals.append(chunk)
            continue
        prefix, suffix = witness
        out.append(
            "1"
            + fixed_width_bits(prefix, prefix_bits)
            + fixed_width_bits(suffix, suffix_bits)
        )
        hits += 1
        choices = seed_prefix_omitted_choices(
            pass_index,
            prefix_bits,
            total_seed_bits,
            suffix,
        )
        omitted_ambiguity += log2(choices) if choices else 0.0
    out.append(tail)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    bitmap_bits = log2_choose(slots, hits)
    count_bits = count_class_bits(slots + 1)
    tight_bits = literal_bits + hits * total_seed_bits + bitmap_bits + count_bits
    fantasy_bits = literal_bits + hits * suffix_bits + bitmap_bits + count_bits
    encoded = "".join(out)
    return (
        encoded,
        SeedPrefixNonceLayerStat(
            pass_index,
            prefix_bits,
            suffix_bits,
            len(bits),
            len(encoded),
            slots,
            hits,
            literal_bits,
            bitmap_bits,
            count_bits,
            tight_bits,
            fantasy_bits,
            omitted_ambiguity,
        ),
    )


def decode_seed_prefix_nonce_layer(
    encoded: str,
    stat: SeedPrefixNonceLayerStat,
    total_seed_bits: int,
) -> str:
    offset = 0
    chunks: list[str] = []
    for _ in range(stat.slots):
        if offset >= len(encoded):
            raise ValueError("truncated seed-prefix tag")
        tag = encoded[offset]
        offset += 1
        if tag == "0":
            end = offset + RECHUNK_L
            if end > len(encoded):
                raise ValueError("truncated seed-prefix literal")
            chunks.append(encoded[offset:end])
            offset = end
        elif tag == "1":
            prefix_end = offset + stat.prefix_bits
            suffix_end = prefix_end + stat.suffix_bits
            if suffix_end > len(encoded):
                raise ValueError("truncated seed-prefix record")
            prefix_bits_value = encoded[offset:prefix_end]
            suffix_bits_value = encoded[prefix_end:suffix_end]
            prefix = int(prefix_bits_value, 2) if prefix_bits_value else 0
            suffix = int(suffix_bits_value, 2) if suffix_bits_value else 0
            chunks.append(
                seed_prefix_nonce_expand(
                    stat.pass_index,
                    stat.prefix_bits,
                    total_seed_bits,
                    prefix,
                    suffix,
                )
            )
            offset = suffix_end
        else:
            raise ValueError(f"invalid seed-prefix tag {tag!r}")
    tail = encoded[offset:]
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("seed-prefix decoded length mismatch")
    return decoded


def encode_seed_prefix_nonce_layers(
    bits: str,
    passes: int,
    prefix_bits: int,
    total_seed_bits: int,
) -> SeedPrefixNonceEncoded:
    current = bits
    stats: list[SeedPrefixNonceLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_seed_prefix_nonce_layer(
            current,
            pass_index,
            prefix_bits,
            total_seed_bits,
        )
        stats.append(stat)
    return SeedPrefixNonceEncoded(current, tuple(stats), bits, total_seed_bits)


def decode_seed_prefix_nonce_layers(encoded: SeedPrefixNonceEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_seed_prefix_nonce_layer(current, stat, encoded.total_seed_bits)
    return current


def seed_prefix_nonce_split_demo(
    trials: int = 120,
    n_bits: int = 512,
    passes: int = 4,
    total_seed_bits: int = RECHUNK_SEED_BITS,
) -> None:
    print("== family 1k2: visible seed-prefix nonce split ==")
    print("The high bits of a fixed-width seed field are read before expansion")
    print("and used as a public nonce. No separate class field is added. The")
    print("charged ledger stores prefix+suffix; the fantasy ledger stores only")
    print("the suffix and pays omitted-prefix ambiguity separately.")
    print()
    rng = Random(616161)
    print(f"toy grammar: span={RECHUNK_L} total_seed={total_seed_bits} "
          f"passes={passes} n_bits={n_bits}")
    print(f"{'prefix':>6} {'suffix':>6} {'hit1':>8} {'hitN':>8} "
          f"{'visible':>9} {'tight':>9} {'fantasy':>9} "
          f"{'fant+amb':>10} {'amb/hit':>8}")
    for prefix_bits in [0, 2, 4, 6, 8]:
        if prefix_bits > total_seed_bits:
            continue
        stats_by_pass: dict[int, list[SeedPrefixNonceLayerStat]] = {
            pass_index: [] for pass_index in range(1, passes + 1)
        }
        final_visible: list[int] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded = encode_seed_prefix_nonce_layers(
                bits,
                passes,
                prefix_bits,
                total_seed_bits,
            )
            assert decode_seed_prefix_nonce_layers(encoded) == bits
            final_visible.append(n_bits - len(encoded.final_bits))
            for stat in encoded.stats:
                stats_by_pass[stat.pass_index].append(stat)
        all_stats = [stat for stats in stats_by_pass.values() for stat in stats]
        first_stats = stats_by_pass[1]
        last_stats = stats_by_pass[passes]
        first_hit_rate = (
            mean(stat.hits for stat in first_stats) / mean(stat.slots for stat in first_stats)
        )
        last_hit_rate = (
            mean(stat.hits for stat in last_stats) / mean(stat.slots for stat in last_stats)
        )
        avg_tight = mean(stat.before_bits - stat.tight_bits for stat in all_stats)
        avg_fantasy = mean(stat.before_bits - stat.fantasy_bits for stat in all_stats)
        avg_fantasy_amb = mean(
            stat.before_bits - stat.fantasy_bits - stat.omitted_prefix_ambiguity
            for stat in all_stats
        )
        hits_total = sum(stat.hits for stat in all_stats)
        amb_total = sum(stat.omitted_prefix_ambiguity for stat in all_stats)
        amb_per_hit = amb_total / hits_total if hits_total else 0.0
        print(f"{prefix_bits:6d} {total_seed_bits - prefix_bits:6d} "
              f"{first_hit_rate:8.5f} {last_hit_rate:8.5f} "
              f"{mean(final_visible):9.3f} {avg_tight:9.3f} "
              f"{avg_fantasy:9.3f} {avg_fantasy_amb:10.3f} "
              f"{amb_per_hit:8.3f}")
    p = 1.0 - ((1.0 - (2.0 ** -RECHUNK_L)) ** (1 << total_seed_bits))
    charged = p * (RECHUNK_L - total_seed_bits) - binary_entropy(p)
    print()
    print("Closed form, ignoring collisions:")
    print(f"hit_p={p:.5f} charged_net/slot={charged:.5f}")
    for prefix_bits in [0, 2, 4, 6, 8]:
        if prefix_bits > total_seed_bits:
            continue
        suffix_bits = total_seed_bits - prefix_bits
        fantasy = p * (RECHUNK_L - suffix_bits) - binary_entropy(p)
        fantasy_amb = p * (RECHUNK_L - suffix_bits - prefix_bits) - binary_entropy(p)
        print(f"prefix={prefix_bits:2d} suffix={suffix_bits:2d} "
              f"fantasy={fantasy:.5f} fantasy+amb={fantasy_amb:.5f}")
    print()
    print("Reading: seed-prefix bits are genuinely decoder-known before the")
    print("hash expands, but they are already part of the seed address. Splitting")
    print("a fixed seed field into nonce+suffix keeps total hit supply roughly")
    print("constant. If the prefix is omitted, the same bits return as candidate")
    print("ambiguity. Visible seed prefixes are not a free freshness channel.")
    print()


ARITY_HEADER_BASE_BITS = 4
ARITY_HEADER_SEED_BITS = 7
ARITY_HEADER_OPTIONS = (1, 2, 3, 4)


def arity_header_bits() -> int:
    return ceil(log2(len(ARITY_HEADER_OPTIONS)))


def arity_header_expand(arity: int, seed: int) -> str:
    return hash_bits(
        "arity-header-known-nonce",
        arity,
        seed,
        n_bits=arity * ARITY_HEADER_BASE_BITS,
    )


@lru_cache(maxsize=16)
def arity_header_books(seed_bits: int = ARITY_HEADER_SEED_BITS) -> tuple[tuple[int, dict[str, int]], ...]:
    books: list[tuple[int, dict[str, int]]] = []
    for arity in ARITY_HEADER_OPTIONS:
        book: dict[str, int] = {}
        for seed in range(1 << seed_bits):
            book.setdefault(arity_header_expand(arity, seed), seed)
        books.append((arity, book))
    return tuple(books)


def arity_count_vector_count(blocks: int, arities: tuple[int, ...] = ARITY_HEADER_OPTIONS) -> int:
    count = 0

    def walk(index: int, remaining: int) -> None:
        nonlocal count
        if index == len(arities):
            count += 1  # remaining blocks are literals
            return
        arity = arities[index]
        for arity_count in range((remaining // arity) + 1):
            walk(index + 1, remaining - (arity_count * arity))

    walk(0, blocks)
    return count


def arity_parse_map_bits(blocks: int, counts_by_arity: Counter[int]) -> float:
    literal_blocks = blocks - sum(arity * count for arity, count in counts_by_arity.items())
    if literal_blocks < 0:
        return float("inf")
    token_count = literal_blocks + sum(counts_by_arity.values())
    log_multinomial = log2_factorial(token_count) - log2_factorial(literal_blocks)
    for count in counts_by_arity.values():
        log_multinomial -= log2_factorial(count)
    count_bits = log2(arity_count_vector_count(blocks))
    return count_bits + log_multinomial


@dataclass
class ArityHeaderLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    blocks: int
    tail_bits: int
    hits_by_arity: tuple[int, ...]
    visible_charged_bits: int
    tight_charged_bits: float


@dataclass
class ArityHeaderEncoded:
    final_bits: str
    stats: tuple[ArityHeaderLayerStat, ...]
    original_bits: str


def choose_arity_header_record(
    bits: str,
    block_index: int,
    blocks: int,
    books: tuple[tuple[int, dict[str, int]], ...],
) -> tuple[int, int, int] | None:
    header_bits = arity_header_bits()
    best: tuple[int, int, int] | None = None
    best_gain = 0
    for arity, book in books:
        if block_index + arity > blocks:
            continue
        start = block_index * ARITY_HEADER_BASE_BITS
        end = (block_index + arity) * ARITY_HEADER_BASE_BITS
        target = bits[start:end]
        seed = book.get(target)
        if seed is None:
            continue
        record_bits = 1 + header_bits + ARITY_HEADER_SEED_BITS
        gain = (arity * ARITY_HEADER_BASE_BITS) - record_bits
        if gain > best_gain:
            best_gain = gain
            best = (arity, seed, gain)
    return best


def encode_arity_header_layer(bits: str, pass_index: int) -> tuple[str, ArityHeaderLayerStat]:
    books = arity_header_books()
    blocks = len(bits) // ARITY_HEADER_BASE_BITS
    tail = bits[blocks * ARITY_HEADER_BASE_BITS:]
    header_bits = arity_header_bits()
    out: list[str] = []
    counts: Counter[int] = Counter()
    block_index = 0
    while block_index < blocks:
        chosen = choose_arity_header_record(bits, block_index, blocks, books)
        if chosen is None:
            start = block_index * ARITY_HEADER_BASE_BITS
            out.append("0" + bits[start:start + ARITY_HEADER_BASE_BITS])
            block_index += 1
            continue
        arity, seed, _ = chosen
        class_id = ARITY_HEADER_OPTIONS.index(arity)
        out.append(
            "1"
            + format(class_id, f"0{header_bits}b")
            + format(seed, f"0{ARITY_HEADER_SEED_BITS}b")
        )
        counts[arity] += 1
        block_index += arity
    if tail:
        out.append(tail)
    encoded = "".join(out)
    literal_blocks = blocks - sum(arity * count for arity, count in counts.items())
    tight_charged = (
        literal_blocks * ARITY_HEADER_BASE_BITS
        + sum(counts.values()) * ARITY_HEADER_SEED_BITS
        + arity_parse_map_bits(blocks, counts)
        + len(tail)
    )
    return encoded, ArityHeaderLayerStat(
        pass_index,
        len(bits),
        len(encoded),
        blocks,
        len(tail),
        tuple(counts[arity] for arity in ARITY_HEADER_OPTIONS),
        len(encoded),
        tight_charged,
    )


def decode_arity_header_layer(encoded: str, stat: ArityHeaderLayerStat) -> str:
    header_bits = arity_header_bits()
    chunks: list[str] = []
    blocks_out = 0
    offset = 0
    while blocks_out < stat.blocks:
        if offset >= len(encoded):
            raise ValueError("truncated arity-header layer")
        tag = encoded[offset]
        if tag == "0":
            end = offset + 1 + ARITY_HEADER_BASE_BITS
            if end > len(encoded):
                raise ValueError("truncated arity-header literal")
            chunks.append(encoded[offset + 1:end])
            blocks_out += 1
            offset = end
        elif tag == "1":
            meta_end = offset + 1 + header_bits
            end = meta_end + ARITY_HEADER_SEED_BITS
            if end > len(encoded):
                raise ValueError("truncated arity-header record")
            class_id = int(encoded[offset + 1:meta_end], 2)
            if class_id >= len(ARITY_HEADER_OPTIONS):
                raise ValueError("invalid arity class")
            arity = ARITY_HEADER_OPTIONS[class_id]
            seed = int(encoded[meta_end:end], 2)
            chunks.append(arity_header_expand(arity, seed))
            blocks_out += arity
            offset = end
        else:
            raise ValueError(f"invalid arity-header tag {tag!r}")
    if blocks_out != stat.blocks:
        raise ValueError("arity-header record overshot layer length")
    tail = encoded[offset:offset + stat.tail_bits]
    if len(tail) != stat.tail_bits:
        raise ValueError("truncated arity-header tail")
    if offset + stat.tail_bits != len(encoded):
        raise ValueError("extra bits after arity-header layer")
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("arity-header decoded length mismatch")
    return decoded


def encode_arity_header_layers(bits: str, passes: int) -> ArityHeaderEncoded:
    current = bits
    stats: list[ArityHeaderLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_arity_header_layer(current, pass_index)
        stats.append(stat)
    return ArityHeaderEncoded(current, tuple(stats), bits)


def decode_arity_header_layers(encoded: ArityHeaderEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_arity_header_layer(current, stat)
    return current


def arity_header_nonce_demo(trials: int = 120, n_bits: int = 256, passes: int = 4) -> None:
    print("== family 1q/2m: arity-header-known nonce surface ==")
    print("The arity header is parsed before seed expansion, so arity can salt")
    print("the hash output without a birth tag. This toy greedily chooses any")
    print("compressive arity-3/4 record, carries misses as literal base blocks,")
    print("then reserializes the token stream for the next fixed-universe pass.")
    print()
    rng = Random(949494)
    rows: dict[int, list[ArityHeaderLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_arity_header_layers(bits, passes)
        assert decode_arity_header_layers(encoded) == bits
        final_delta.append(n_bits - len(encoded.final_bits))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(
        f"toy grammar: base={ARITY_HEADER_BASE_BITS} seed={ARITY_HEADER_SEED_BITS} "
        f"arity_bits={arity_header_bits()} arities={ARITY_HEADER_OPTIONS} "
        f"passes={passes} n_bits={n_bits}"
    )
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in':>8} {'avg out':>9} {'a3':>7} {'a4':>7} "
          f"{'vis net':>9} {'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_a3 = mean(stat.hits_by_arity[2] for stat in stats)
        avg_a4 = mean(stat.hits_by_arity[3] for stat in stats)
        visible_net = avg_in - avg_out
        tight_net = avg_in - mean(stat.tight_charged_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:8.2f} {avg_out:9.2f} "
              f"{avg_a3:7.3f} {avg_a4:7.3f} {visible_net:9.3f} {tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_delta):.3f} bits")
    print()
    print("closed scheduled-window surface, one public arity class at a time:")
    print(f"{'arity':>5} {'target':>7} {'p':>10} {'visible gap':>12} "
          f"{'mapless E':>11} {'H(p)':>10} {'net/slot':>10}")
    for arity in ARITY_HEADER_OPTIONS:
        target = arity * ARITY_HEADER_BASE_BITS
        p = min(1.0, 2.0 ** (ARITY_HEADER_SEED_BITS - target))
        visible_gap = target - (1 + arity_header_bits() + ARITY_HEADER_SEED_BITS)
        mapless = p * max(0, visible_gap)
        entropy = binary_entropy(p)
        print(f"{arity:5d} {target:7d} {p:10.5f} {visible_gap:12d} "
              f"{mapless:11.5f} {entropy:10.5f} {mapless - entropy:10.5f}")
    print()
    print("Reading: arity is a real parser-known nonce and target refresh")
    print("keeps finding fresh records over passes. The visible codec bloats")
    print("because misses carry literal tags; the tight ledger still pays the")
    print("non-overlapping parse/arity map. The arity header buys extra dice")
    print("only by being part of the paid record/parse description.")
    print()


GEOMETRY_BASE_BITS = 4
GEOMETRY_GROUP_CHUNKS = 4
GEOMETRY_SEED_BITS = 4
GEOMETRY_SHAPES: tuple[tuple[tuple[str, int], ...], ...] = (
    (("L", 1), ("L", 1), ("L", 1), ("L", 1)),
    (("R", 4),),
    (("R", 3), ("L", 1)),
    (("L", 1), ("R", 3)),
    (("R", 2), ("R", 2)),
    (("R", 2), ("L", 1), ("L", 1)),
    (("L", 1), ("R", 2), ("L", 1)),
    (("L", 1), ("L", 1), ("R", 2)),
)


def geometry_mode_bits() -> int:
    return ceil(log2(len(GEOMETRY_SHAPES)))


def geometry_record_count(shape: tuple[tuple[str, int], ...]) -> int:
    return sum(1 for kind, _ in shape if kind == "R")


def geometry_literal_chunks(shape: tuple[tuple[str, int], ...]) -> int:
    return sum(width for kind, width in shape if kind == "L")


def geometry_expand(shape_id: int, segment_index: int, arity: int, seed: int) -> str:
    return hash_bits(
        "bundle-geometry-known-nonce",
        shape_id,
        segment_index,
        arity,
        seed,
        n_bits=arity * GEOMETRY_BASE_BITS,
    )


@lru_cache(maxsize=4096)
def geometry_book(shape_id: int, segment_index: int, arity: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << GEOMETRY_SEED_BITS):
        book.setdefault(geometry_expand(shape_id, segment_index, arity, seed), seed)
    return book


def geometry_shape_encoded_bits(shape_id: int) -> int:
    shape = GEOMETRY_SHAPES[shape_id]
    return (
        geometry_mode_bits()
        + geometry_record_count(shape) * GEOMETRY_SEED_BITS
        + geometry_literal_chunks(shape) * GEOMETRY_BASE_BITS
    )


def encode_geometry_group(group_bits: str, shape_id: int) -> tuple[str, tuple[int, ...]] | None:
    shape = GEOMETRY_SHAPES[shape_id]
    cursor = 0
    out: list[str] = [format(shape_id, f"0{geometry_mode_bits()}b")]
    seeds: list[int] = []
    for segment_index, (kind, width) in enumerate(shape):
        span = width * GEOMETRY_BASE_BITS
        target = group_bits[cursor:cursor + span]
        if len(target) != span:
            return None
        if kind == "L":
            out.append(target)
        else:
            seed = geometry_book(shape_id, segment_index, width).get(target)
            if seed is None:
                return None
            out.append(format(seed, f"0{GEOMETRY_SEED_BITS}b"))
            seeds.append(seed)
        cursor += span
    if cursor != len(group_bits):
        return None
    return "".join(out), tuple(seeds)


def geometry_mode_count_vector_bits(groups: int, modes: int) -> float:
    return log2_choose(groups + modes - 1, modes - 1)


def geometry_mode_map_bits(mode_counts: Counter[int], groups: int) -> float:
    bits = geometry_mode_count_vector_bits(groups, len(GEOMETRY_SHAPES))
    bits += log2_factorial(groups)
    for count in mode_counts.values():
        bits -= log2_factorial(count)
    return bits


@dataclass
class BundleGeometryLayerStat:
    pass_index: int
    before_bits: int
    after_bits: int
    groups: int
    tail_bits: int
    modes: tuple[int, ...]
    records: int
    tight_charged_bits: float


@dataclass
class BundleGeometryEncoded:
    final_bits: str
    stats: tuple[BundleGeometryLayerStat, ...]
    original_bits: str


def encode_bundle_geometry_layer(bits: str, pass_index: int) -> tuple[str, BundleGeometryLayerStat]:
    group_bits_len = GEOMETRY_GROUP_CHUNKS * GEOMETRY_BASE_BITS
    groups = len(bits) // group_bits_len
    tail = bits[groups * group_bits_len:]
    out: list[str] = []
    mode_ids: list[int] = []
    record_count = 0
    for group in range(groups):
        group_start = group * group_bits_len
        group_bits = bits[group_start:group_start + group_bits_len]
        best_id = 0
        best_encoded, _ = encode_geometry_group(group_bits, 0) or ("", ())
        best_len = len(best_encoded)
        best_records = 0
        for shape_id in range(1, len(GEOMETRY_SHAPES)):
            candidate = encode_geometry_group(group_bits, shape_id)
            if candidate is None:
                continue
            encoded_group, seeds = candidate
            if len(encoded_group) < best_len:
                best_id = shape_id
                best_encoded = encoded_group
                best_len = len(encoded_group)
                best_records = len(seeds)
        out.append(best_encoded)
        mode_ids.append(best_id)
        record_count += best_records
    if tail:
        out.append(tail)
    mode_counts = Counter(mode_ids)
    literal_bits = 0
    seed_bits = 0
    for mode_id, count in mode_counts.items():
        shape = GEOMETRY_SHAPES[mode_id]
        literal_bits += count * geometry_literal_chunks(shape) * GEOMETRY_BASE_BITS
        seed_bits += count * geometry_record_count(shape) * GEOMETRY_SEED_BITS
    tight_charged = (
        literal_bits
        + seed_bits
        + geometry_mode_map_bits(mode_counts, groups)
        + len(tail)
    )
    encoded = "".join(out)
    return encoded, BundleGeometryLayerStat(
        pass_index,
        len(bits),
        len(encoded),
        groups,
        len(tail),
        tuple(mode_ids),
        record_count,
        tight_charged,
    )


def decode_bundle_geometry_layer(encoded: str, stat: BundleGeometryLayerStat) -> str:
    mode_bits = geometry_mode_bits()
    chunks: list[str] = []
    offset = 0
    for _ in range(stat.groups):
        if offset + mode_bits > len(encoded):
            raise ValueError("truncated bundle-geometry mode")
        shape_id = int(encoded[offset:offset + mode_bits], 2)
        offset += mode_bits
        if shape_id >= len(GEOMETRY_SHAPES):
            raise ValueError("invalid bundle-geometry mode")
        shape = GEOMETRY_SHAPES[shape_id]
        group_parts: list[str] = []
        for segment_index, (kind, width) in enumerate(shape):
            if kind == "L":
                span = width * GEOMETRY_BASE_BITS
                end = offset + span
                if end > len(encoded):
                    raise ValueError("truncated bundle-geometry literal")
                group_parts.append(encoded[offset:end])
                offset = end
            else:
                end = offset + GEOMETRY_SEED_BITS
                if end > len(encoded):
                    raise ValueError("truncated bundle-geometry seed")
                seed = int(encoded[offset:end], 2)
                group_parts.append(geometry_expand(shape_id, segment_index, width, seed))
                offset = end
        chunks.append("".join(group_parts))
    tail = encoded[offset:offset + stat.tail_bits]
    if len(tail) != stat.tail_bits:
        raise ValueError("truncated bundle-geometry tail")
    if offset + stat.tail_bits != len(encoded):
        raise ValueError("extra bits after bundle-geometry layer")
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("bundle-geometry decoded length mismatch")
    return decoded


def encode_bundle_geometry_layers(bits: str, passes: int) -> BundleGeometryEncoded:
    current = bits
    stats: list[BundleGeometryLayerStat] = []
    for pass_index in range(1, passes + 1):
        current, stat = encode_bundle_geometry_layer(current, pass_index)
        stats.append(stat)
    return BundleGeometryEncoded(current, tuple(stats), bits)


def decode_bundle_geometry_layers(encoded: BundleGeometryEncoded) -> str:
    current = encoded.final_bits
    for stat in reversed(encoded.stats):
        current = decode_bundle_geometry_layer(current, stat)
    return current


def bundle_geometry_partition_demo(trials: int = 160, n_bits: int = 512, passes: int = 4) -> None:
    print("== family 1r/2n: bundle-geometry partition selector ==")
    print("A group shape is decoded before child seeds, so the shape can salt")
    print("each bundle segment. The encoder chooses among raw, one large record,")
    print("two 2-block records, or one 2/3-block record plus literals. The")
    print("visible codec stores a mode per group; the tight ledger replaces")
    print("that with an enumerative mode map.")
    print()
    rng = Random(959595)
    rows: dict[int, list[BundleGeometryLayerStat]] = {p: [] for p in range(1, passes + 1)}
    final_delta: list[int] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded = encode_bundle_geometry_layers(bits, passes)
        assert decode_bundle_geometry_layers(encoded) == bits
        final_delta.append(n_bits - len(encoded.final_bits))
        for stat in encoded.stats:
            rows[stat.pass_index].append(stat)
    print(
        f"toy grammar: base={GEOMETRY_BASE_BITS} group={GEOMETRY_GROUP_CHUNKS} "
        f"seed={GEOMETRY_SEED_BITS} modes={len(GEOMETRY_SHAPES)} "
        f"passes={passes} n_bits={n_bits}"
    )
    print(f"round_trips={trials}/{trials}")
    print(f"{'pass':>4} {'avg in':>8} {'avg out':>9} {'groups':>8} "
          f"{'rec':>8} {'mode0%':>8} {'vis net':>9} {'tight net':>10}")
    for pass_index in range(1, passes + 1):
        stats = rows[pass_index]
        avg_in = mean(stat.before_bits for stat in stats)
        avg_out = mean(stat.after_bits for stat in stats)
        avg_groups = mean(stat.groups for stat in stats)
        avg_records = mean(stat.records for stat in stats)
        raw_fraction = mean(stat.modes.count(0) / stat.groups if stat.groups else 1.0 for stat in stats)
        visible_net = avg_in - avg_out
        tight_net = avg_in - mean(stat.tight_charged_bits for stat in stats)
        print(f"{pass_index:4d} {avg_in:8.2f} {avg_out:9.2f} {avg_groups:8.2f} "
              f"{avg_records:8.3f} {100.0 * raw_fraction:8.3f} "
              f"{visible_net:9.3f} {tight_net:10.3f}")
    print(f"mean final visible delta vs original={mean(final_delta):.3f} bits")
    print()
    print("closed shape surface, ignoring overlap between shapes:")
    print(f"{'mode':>4} {'shape':>12} {'q':>11} {'gap':>6} "
          f"{'q*gap':>11} {'H(q)':>10} {'net':>10}")
    total_q = 0.0
    total_gain = 0.0
    for shape_id, shape in enumerate(GEOMETRY_SHAPES):
        if shape_id == 0:
            continue
        q = 1.0
        for _, (kind, width) in enumerate(shape):
            if kind == "R":
                q *= 2.0 ** (GEOMETRY_SEED_BITS - (width * GEOMETRY_BASE_BITS))
        raw_bits = GEOMETRY_GROUP_CHUNKS * GEOMETRY_BASE_BITS
        encoded_bits = geometry_shape_encoded_bits(shape_id)
        gap = raw_bits - encoded_bits
        gain = q * max(0, gap)
        total_q += q
        total_gain += gain
        shape_text = "".join(f"{kind}{width}" for kind, width in shape)
        entropy = binary_entropy(min(q, 1.0))
        print(f"{shape_id:4d} {shape_text:>12} {q:11.5e} {gap:6d} "
              f"{gain:11.5e} {entropy:10.5e} {gain - entropy:10.5e}")
    union_entropy = binary_entropy(min(total_q, 1.0))
    print(f"{'all':>4} {'optimistic':>12} {total_q:11.5e} {'':>6} "
          f"{total_gain:11.5e} {union_entropy:10.5e} "
          f"{total_gain - union_entropy:10.5e}")
    print()
    print("Reading: bundle geometry is a real decoder-known nonce only after")
    print("the mode/shape is known. Trying several shapes raises the chance")
    print("that some group can use a record, but the selected geometry is the")
    print("open/carry map at group scale. The exact codec round-trips and")
    print("refreshes targets across passes, yet both visible mode bits and the")
    print("optimistic mode-map ledger remain negative.")
    print()


def category_entropy(probabilities: tuple[float, ...]) -> float:
    miss = max(0.0, 1.0 - sum(probabilities))
    total = 0.0
    for probability in (*probabilities, miss):
        if probability > 0.0:
            total -= probability * log2(probability)
    return total


def exact_count_assignment_entropy(slots: int, probabilities: tuple[float, ...]) -> tuple[float, float]:
    categories = len(probabilities) + 1
    probs = (*probabilities, max(0.0, 1.0 - sum(probabilities)))
    log_fact_slots = log2_factorial(slots)
    count_entropy = 0.0
    expected_assignment = 0.0
    for counts in compositions(slots, categories):
        if any(count and probs[index] <= 0.0 for index, count in enumerate(counts)):
            continue
        log_probability = log_fact_slots
        for count, probability in zip(counts, probs):
            log_probability -= log2_factorial(count)
            if count:
                log_probability += count * log2(probability)
        probability = 2.0 ** log_probability
        count_entropy -= probability * log_probability
        log_assignment = log_fact_slots - sum(log2_factorial(count) for count in counts)
        expected_assignment += probability * log_assignment
    return count_entropy, expected_assignment


def seed_value_count_separation_demo() -> None:
    print("== family 1k2: seed value/count separation ==")
    print("This mutation tries to spend rare high-value seed classes while")
    print("storing only a class histogram/counts. The decoder then knows how")
    print("many hits of each class exist, but not which slots get which class.")
    print("That missing assignment is survivor ambiguity or a bitmap.")
    print()
    slots = 32
    rows = [
        ("d4 feasible", ((2.0 ** -4, 4.0),)),
        ("d8 feasible", ((2.0 ** -8, 8.0),)),
        ("d4+d8+d12", ((2.0 ** -4, 4.0), (2.0 ** -8, 8.0), (2.0 ** -12, 12.0))),
        ("jackpot d16/p8", ((2.0 ** -8, 16.0),)),
        ("jackpot d24/p12", ((2.0 ** -12, 24.0),)),
        ("mixed fantasy", ((2.0 ** -4, 4.0), (2.0 ** -10, 18.0))),
    ]
    print(f"exact count/assignment entropy: slots={slots}")
    print(f"{'case':>16} {'feasible':>8} {'gross/sl':>9} {'Hcount/sl':>10} "
          f"{'assign/sl':>10} {'fullH/sl':>9} {'count net':>10} {'full net':>10}")
    for label, classes in rows:
        probabilities = tuple(probability for probability, _ in classes)
        savings = tuple(saving for _, saving in classes)
        feasible = all(probability <= 2.0 ** (-saving) + 1e-15
                       for probability, saving in classes)
        gross = sum(probability * saving for probability, saving in classes)
        count_entropy, expected_assignment = exact_count_assignment_entropy(slots, probabilities)
        full_entropy = category_entropy(probabilities)
        count_net = gross - count_entropy / slots
        full_net = gross - full_entropy
        print(f"{label:>16} {str(feasible):>8} {gross:9.5f} "
              f"{count_entropy / slots:10.5f} {expected_assignment / slots:10.5f} "
              f"{full_entropy:9.5f} {count_net:10.5f} {full_net:10.5f}")
    print()
    print("Reading: counts alone can make rare high-value classes look useful,")
    print("because histogram entropy is sublinear in the number of slots. But")
    print("the decoder still needs the class assignment to ordered slots. Once")
    print("assignment entropy is charged, feasible uniform classes lose. Rows")
    print("with positive full net require impossible jackpot density: a class")
    print("saving d bits cannot cover more than about 2^-d of arbitrary chunks")
    print("without extra codewords or side information.")
    print()


@dataclass
class GroupedScheduleEncoded:
    length: int
    group_size: int
    groups: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass
class GroupedScheduleStat:
    length: int
    group_size: int
    groups: int
    hits: int
    literal_bits: int
    seed_bits: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def encode_grouped_schedule(bits: str, group_size: int) -> tuple[GroupedScheduleEncoded, GroupedScheduleStat]:
    group_bits = group_size * RECHUNK_L
    groups = len(bits) // group_bits
    tail = bits[groups * group_bits:]
    state = 0
    hits: list[bool] = []
    seeds: list[int] = []
    literals: list[str] = []
    for group in range(groups):
        start = group * group_bits
        chunks = [bits[start + slot * RECHUNK_L:start + (slot + 1) * RECHUNK_L]
                  for slot in range(group_size)]
        probe_state = state
        group_seeds: list[int] = []
        all_hit = True
        for chunk in chunks:
            seed = STATE_RECHUNK_BOOKS[probe_state].get(chunk)
            if seed is None:
                all_hit = False
                break
            group_seeds.append(seed)
            probe_state = step_token_state(probe_state, chunk)
        if all_hit:
            hits.append(True)
            seeds.extend(group_seeds)
        else:
            hits.append(False)
            literals.extend(chunks)
        for chunk in chunks:
            state = step_token_state(state, chunk)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    bitmap_bits = log2_choose(groups, sum(hits))
    count_bits = count_class_bits(groups + 1)
    charged_bits = literal_bits + seed_bits + bitmap_bits + count_bits
    return (
        GroupedScheduleEncoded(
            len(bits),
            group_size,
            groups,
            tuple(hits),
            tuple(seeds),
            "".join(literals),
            tail,
        ),
        GroupedScheduleStat(
            len(bits),
            group_size,
            groups,
            sum(hits),
            literal_bits,
            seed_bits,
            bitmap_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_grouped_schedule(encoded: GroupedScheduleEncoded) -> str:
    state = 0
    seed_index = 0
    literal_index = 0
    out: list[str] = []
    for hit in encoded.hits:
        if hit:
            for _ in range(encoded.group_size):
                seed = encoded.seeds[seed_index]
                seed_index += 1
                chunk = expand_state_rechunk_seed(state, seed)
                out.append(chunk)
                state = step_token_state(state, chunk)
        else:
            for _ in range(encoded.group_size):
                chunk = encoded.literals[literal_index:literal_index + RECHUNK_L]
                if len(chunk) != RECHUNK_L:
                    raise ValueError("grouped literal stream exhausted")
                literal_index += RECHUNK_L
                out.append(chunk)
                state = step_token_state(state, chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused grouped seeds")
    if literal_index != len(encoded.literals):
        raise ValueError("unused grouped literals")
    out.append(encoded.tail)
    return "".join(out)


def grouped_schedule_bitmap_demo(trials: int = 200, n_bits: int = 4096) -> None:
    print("== family 1h: grouped scheduled-bundle bitmap accounting ==")
    print("This mutation tries to amortize the bitmap by accepting only complete")
    print("public groups of scheduled slots. A group is a record only when every")
    print("slot in that group has a prefix-state seed; otherwise the whole group")
    print("is carried literally. The group bitmap is still priced optimistically")
    print("with a count-class charge.")
    print()
    rng = Random(998877)
    print(f"{'g slots':>7} {'groups':>7} {'hits':>8} {'hit/group':>10} "
          f"{'bitmap':>10} {'count':>8} {'charged':>10} {'net':>10}")
    for group_size in [1, 2, 3, 4]:
        stats: list[GroupedScheduleStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_grouped_schedule(bits, group_size)
            assert decode_grouped_schedule(encoded) == bits
            stats.append(stat)
        avg_groups = mean(stat.groups for stat in stats)
        avg_hits = mean(stat.hits for stat in stats)
        hit_rate = avg_hits / avg_groups if avg_groups else 0.0
        avg_bitmap = mean(stat.bitmap_bits for stat in stats)
        avg_count = mean(stat.count_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        print(f"{group_size:7d} {avg_groups:7.1f} {avg_hits:8.3f} "
              f"{hit_rate:10.5f} {avg_bitmap:10.3f} {avg_count:8.3f} "
              f"{avg_charged:10.3f} {n_bits - avg_charged:10.3f}")
    print()
    print("Closed-form all-hit group expectation under the uniform hash law:")
    print(f"{'g slots':>7} {'q=p^g':>11} {'save/group':>12} "
          f"{'H(q)':>11} {'net/group':>11}")
    gap = RECHUNK_L - RECHUNK_SEED_BITS
    p = 2 ** (-gap)
    for group_size in [1, 2, 3, 4, 8]:
        q = p ** group_size
        save = q * group_size * gap
        entropy = binary_entropy(q)
        print(f"{group_size:7d} {q:11.5e} {save:12.5e} "
              f"{entropy:11.5e} {save - entropy:11.5e}")
    print()
    print("Reading: complete scheduled groups reduce bitmap frequency but")
    print("thin hit supply by the same exponent. The all-hit group entropy")
    print("remains larger than expected savings under uniform independent hits.")
    print()


@dataclass(frozen=True)
class BucketDirectoryEncoded:
    length: int
    group_size: int
    groups: int
    bucket_hits: tuple[bool, ...]
    local_indices: tuple[int, ...]
    seeds: tuple[int, ...]
    literals: str
    tail: str


@dataclass(frozen=True)
class BucketDirectoryStat:
    group_size: int
    groups: int
    bucket_hits: int
    records: int
    literal_bits: int
    seed_bits: int
    directory_bits: float
    index_bits: int
    count_bits: float
    charged_bits: float


def encode_bucket_directory(bits: str, group_size: int) -> tuple[BucketDirectoryEncoded, BucketDirectoryStat]:
    group_bits = group_size * RECHUNK_L
    groups = len(bits) // group_bits
    tail = bits[groups * group_bits:]
    bucket_hits: list[bool] = []
    local_indices: list[int] = []
    seeds: list[int] = []
    literals: list[str] = []
    for group in range(groups):
        base = group * group_bits
        chunks = [
            bits[base + slot * RECHUNK_L:base + (slot + 1) * RECHUNK_L]
            for slot in range(group_size)
        ]
        chosen: tuple[int, int] | None = None
        for local, chunk in enumerate(chunks):
            seed = RECHUNK_BOOK.get(chunk)
            if seed is not None:
                chosen = (local, seed)
                break
        if chosen is None:
            bucket_hits.append(False)
            literals.extend(chunks)
            continue
        local, seed = chosen
        bucket_hits.append(True)
        local_indices.append(local)
        seeds.append(seed)
        for index, chunk in enumerate(chunks):
            if index != local:
                literals.append(chunk)
    directory_bits = log2_choose(groups, sum(bucket_hits))
    count_bits = count_class_bits(groups + 1)
    index_bits = ceil(log2(group_size)) * len(local_indices)
    literal_bits = sum(len(chunk) for chunk in literals) + len(tail)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    charged_bits = literal_bits + seed_bits + directory_bits + count_bits + index_bits
    return (
        BucketDirectoryEncoded(
            len(bits),
            group_size,
            groups,
            tuple(bucket_hits),
            tuple(local_indices),
            tuple(seeds),
            "".join(literals),
            tail,
        ),
        BucketDirectoryStat(
            group_size,
            groups,
            sum(bucket_hits),
            len(seeds),
            literal_bits,
            seed_bits,
            directory_bits,
            index_bits,
            count_bits,
            charged_bits,
        ),
    )


def decode_bucket_directory(encoded: BucketDirectoryEncoded) -> str:
    local_index_cursor = 0
    seed_cursor = 0
    literal_cursor = 0
    out: list[str] = []
    for bucket_hit in encoded.bucket_hits:
        if bucket_hit:
            local = encoded.local_indices[local_index_cursor]
            local_index_cursor += 1
            seed = encoded.seeds[seed_cursor]
            seed_cursor += 1
            for slot in range(encoded.group_size):
                if slot == local:
                    out.append(expand_rechunk_seed(seed))
                else:
                    chunk = encoded.literals[literal_cursor:literal_cursor + RECHUNK_L]
                    if len(chunk) != RECHUNK_L:
                        raise ValueError("bucket-directory literal stream exhausted")
                    literal_cursor += RECHUNK_L
                    out.append(chunk)
        else:
            for _ in range(encoded.group_size):
                chunk = encoded.literals[literal_cursor:literal_cursor + RECHUNK_L]
                if len(chunk) != RECHUNK_L:
                    raise ValueError("bucket-directory raw bucket exhausted")
                literal_cursor += RECHUNK_L
                out.append(chunk)
    if local_index_cursor != len(encoded.local_indices):
        raise ValueError("unused bucket-directory local indices")
    if seed_cursor != len(encoded.seeds):
        raise ValueError("unused bucket-directory seeds")
    if literal_cursor != len(encoded.literals):
        raise ValueError("unused bucket-directory literals")
    out.append(encoded.tail)
    return "".join(out)


def bucket_directory_hitmap_demo(trials: int = 200, n_bits: int = 4096) -> None:
    print("== family 1h2: bucket-directory one-hit hit map ==")
    print("This mutation stores a public bucket directory instead of a per-slot")
    print("bitmap. Each non-empty bucket records at most one matching slot, with")
    print("a local index and seed; all other slots are literals. This is a")
    print("middle ground between per-slot bitmap and all-hit groups.")
    print()
    rng = Random(838383)
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"gross/hit={RECHUNK_L - RECHUNK_SEED_BITS}")
    print(f"{'g slots':>7} {'groups':>7} {'buckets':>8} {'hit/bkt':>9} "
          f"{'index':>8} {'dir+cnt':>10} {'charged':>10} {'net':>10}")
    for group_size in [2, 4, 8, 16]:
        stats: list[BucketDirectoryStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_bucket_directory(bits, group_size)
            assert decode_bucket_directory(encoded) == bits
            stats.append(stat)
        avg_groups = mean(stat.groups for stat in stats)
        avg_bucket_hits = mean(stat.bucket_hits for stat in stats)
        avg_index = mean(stat.index_bits for stat in stats)
        avg_dir_count = mean(stat.directory_bits + stat.count_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        print(f"{group_size:7d} {avg_groups:7.1f} {avg_bucket_hits:8.3f} "
              f"{avg_bucket_hits / avg_groups:9.5f} {avg_index:8.3f} "
              f"{avg_dir_count:10.3f} {avg_charged:10.3f} "
              f"{n_bits - avg_charged:10.3f}")
    print()
    print("Closed-form one-hit bucket expectation under uniform independent hits:")
    print(f"{'g slots':>7} {'q bucket':>10} {'E save':>10} {'H(q)':>10} "
          f"{'idx bits':>9} {'net/group':>11}")
    p = 2 ** (RECHUNK_SEED_BITS - RECHUNK_L)
    gap = RECHUNK_L - RECHUNK_SEED_BITS
    for group_size in [2, 4, 8, 16, 32]:
        q = 1.0 - ((1.0 - p) ** group_size)
        idx = ceil(log2(group_size))
        expected_save = q * max(0, gap - idx)
        entropy = binary_entropy(q)
        print(f"{group_size:7d} {q:10.5f} {expected_save:10.5f} "
              f"{entropy:10.5f} {idx:9d} {expected_save - entropy:11.5f}")
    print()
    print("Reading: bucket directories reduce bitmap resolution, but each")
    print("non-empty bucket needs a local coordinate and gives up additional")
    print("hits inside the bucket. The directory entropy plus local index")
    print("cost remains larger than the expected one-hit savings.")
    print()


@dataclass(frozen=True)
class AllOrRawBlockEncoded:
    length: int
    group_size: int
    groups: int
    modes: tuple[bool, ...]
    seeds: tuple[int, ...]
    raw_groups: str
    tail: str


@dataclass(frozen=True)
class AllOrRawBlockStat:
    group_size: int
    groups: int
    compressed_groups: int
    seed_bits: int
    raw_bits: int
    mode_bits: int
    charged_bits: int


def encode_all_or_raw_blocks(bits: str, group_size: int) -> tuple[AllOrRawBlockEncoded, AllOrRawBlockStat]:
    group_bits = group_size * RECHUNK_L
    groups = len(bits) // group_bits
    tail = bits[groups * group_bits:]
    state = 0
    modes: list[bool] = []
    seeds: list[int] = []
    raw_groups: list[str] = []
    for group in range(groups):
        start = group * group_bits
        chunks = [bits[start + slot * RECHUNK_L:start + (slot + 1) * RECHUNK_L]
                  for slot in range(group_size)]
        probe_state = state
        group_seeds: list[int] = []
        all_hit = True
        for chunk in chunks:
            seed = STATE_RECHUNK_BOOKS[probe_state].get(chunk)
            if seed is None:
                all_hit = False
                break
            group_seeds.append(seed)
            probe_state = step_token_state(probe_state, chunk)
        if all_hit:
            modes.append(True)
            seeds.extend(group_seeds)
        else:
            modes.append(False)
            raw_groups.extend(chunks)
        for chunk in chunks:
            state = step_token_state(state, chunk)
    seed_bits = len(seeds) * RECHUNK_SEED_BITS
    raw_bits = sum(len(chunk) for chunk in raw_groups) + len(tail)
    mode_bits = groups
    charged_bits = seed_bits + raw_bits + mode_bits
    return (
        AllOrRawBlockEncoded(
            len(bits), group_size, groups, tuple(modes), tuple(seeds), "".join(raw_groups), tail,
        ),
        AllOrRawBlockStat(group_size, groups, sum(modes), seed_bits, raw_bits, mode_bits, charged_bits),
    )


def decode_all_or_raw_blocks(encoded: AllOrRawBlockEncoded) -> str:
    state = 0
    seed_index = 0
    raw_index = 0
    out: list[str] = []
    for compressed in encoded.modes:
        if compressed:
            for _ in range(encoded.group_size):
                seed = encoded.seeds[seed_index]
                seed_index += 1
                chunk = expand_state_rechunk_seed(state, seed)
                out.append(chunk)
                state = step_token_state(state, chunk)
        else:
            for _ in range(encoded.group_size):
                chunk = encoded.raw_groups[raw_index:raw_index + RECHUNK_L]
                if len(chunk) != RECHUNK_L:
                    raise ValueError("all-or-raw group stream exhausted")
                raw_index += RECHUNK_L
                out.append(chunk)
                state = step_token_state(state, chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused all-or-raw seeds")
    if raw_index != len(encoded.raw_groups):
        raise ValueError("unused all-or-raw raw bits")
    out.append(encoded.tail)
    return "".join(out)


def all_or_raw_block_mode_demo(trials: int = 200, n_bits: int = 4096) -> None:
    print("== family 1l: bitmap-free all-or-raw block modes ==")
    print("This mutation removes mixed open/carry positions inside a block.")
    print("Each public block is either fully compressed, when every scheduled")
    print("slot has a seed, or carried raw. The only local side channel is one")
    print("raw/compressed mode bit per block.")
    print()
    rng = Random(818181)
    print(f"toy grammar: span={RECHUNK_L} seed={RECHUNK_SEED_BITS} "
          f"gross/hit={RECHUNK_L - RECHUNK_SEED_BITS}")
    print(f"{'g slots':>7} {'groups':>7} {'cmp grp':>8} {'hit/group':>10} "
          f"{'mode':>8} {'charged':>10} {'net':>10}")
    for group_size in [1, 2, 3, 4, 8, 16]:
        stats: list[AllOrRawBlockStat] = []
        for _ in range(trials):
            bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            encoded, stat = encode_all_or_raw_blocks(bits, group_size)
            assert decode_all_or_raw_blocks(encoded) == bits
            stats.append(stat)
        avg_groups = mean(stat.groups for stat in stats)
        avg_compressed = mean(stat.compressed_groups for stat in stats)
        hit_rate = avg_compressed / avg_groups if avg_groups else 0.0
        avg_mode = mean(stat.mode_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        print(f"{group_size:7d} {avg_groups:7.1f} {avg_compressed:8.3f} "
              f"{hit_rate:10.5f} {avg_mode:8.1f} {avg_charged:10.3f} "
              f"{n_bits - avg_charged:10.3f}")
    print()
    print("Closed-form all-or-raw expectation under uniform independent hits:")
    print(f"{'g slots':>7} {'q=p^g':>11} {'save/group':>12} {'net/group':>11} "
          f"{'whole-layer net @292':>20}")
    gap = RECHUNK_L - RECHUNK_SEED_BITS
    p = 2 ** (-gap)
    layer_slots = 4096 // RECHUNK_L
    for group_size in [1, 2, 3, 4, 8, 16, layer_slots]:
        q = p ** group_size
        save = q * group_size * gap
        net = save - 1.0
        whole = (p ** layer_slots) * layer_slots * gap - 1.0 if group_size == layer_slots else float("nan")
        whole_text = f"{whole:20.5e}" if group_size == layer_slots else f"{'':>20}"
        print(f"{group_size:7d} {q:11.5e} {save:12.5e} {net:11.5e} {whole_text}")
    print()
    print("Reading: all-or-raw blocks remove the per-slot bitmap, but the")
    print("mode bit is still an open/carry channel. Making blocks larger")
    print("reduces mode frequency only by requiring exponentially rarer all-hit")
    print("events. A whole-layer all-hit mode has essentially zero random hit")
    print("probability, so its single mode bit is just fallback overhead.")
    print()


HOLE_BASE_BITS = 4
HOLE_GROUP_CHUNKS = 4
HOLE_SEED_BITS = 10


@dataclass(frozen=True)
class HoleRunBundleEncoded:
    length: int
    groups: int
    modes: tuple[bool, ...]
    seeds: tuple[int, ...]
    raw_groups: str
    tail: str


@dataclass(frozen=True)
class HoleRunBundleStat:
    groups: int
    hits: int
    raw_bits: int
    seed_bits: int
    mode_bits: int
    cell_occupancy_bits: int
    charged_bits: int
    cell_board_bits: int
    tight_bits: float
    free_oracle_bits: int


def expand_hole_run_bundle(seed: int) -> str:
    return hash_bits(
        "hole-run-bundle",
        seed,
        n_bits=HOLE_GROUP_CHUNKS * HOLE_BASE_BITS,
    )


def build_hole_run_bundle_book() -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << HOLE_SEED_BITS):
        book.setdefault(expand_hole_run_bundle(seed), seed)
    return book


HOLE_RUN_BUNDLE_BOOK = build_hole_run_bundle_book()


def encode_hole_run_bundles(bits: str) -> tuple[HoleRunBundleEncoded, HoleRunBundleStat]:
    group_bits = HOLE_GROUP_CHUNKS * HOLE_BASE_BITS
    groups = len(bits) // group_bits
    tail = bits[groups * group_bits:]
    modes: list[bool] = []
    seeds: list[int] = []
    raw_groups: list[str] = []
    for group in range(groups):
        start = group * group_bits
        chunk = bits[start:start + group_bits]
        seed = HOLE_RUN_BUNDLE_BOOK.get(chunk)
        if seed is None:
            modes.append(False)
            raw_groups.append(chunk)
        else:
            modes.append(True)
            seeds.append(seed)
    hits = sum(modes)
    raw_bits = sum(len(chunk) for chunk in raw_groups) + len(tail)
    seed_bits = hits * HOLE_SEED_BITS
    mode_bits = groups
    cell_occupancy_bits = groups * HOLE_GROUP_CHUNKS
    charged_bits = raw_bits + seed_bits + mode_bits
    cell_board_bits = raw_bits + seed_bits + cell_occupancy_bits
    tight_bits = raw_bits + seed_bits + log2_choose(groups, hits) + ceil(log2(groups + 1))
    free_oracle_bits = raw_bits + seed_bits
    return (
        HoleRunBundleEncoded(
            len(bits), groups, tuple(modes), tuple(seeds), "".join(raw_groups), tail,
        ),
        HoleRunBundleStat(
            groups=groups,
            hits=hits,
            raw_bits=raw_bits,
            seed_bits=seed_bits,
            mode_bits=mode_bits,
            cell_occupancy_bits=cell_occupancy_bits,
            charged_bits=charged_bits,
            cell_board_bits=cell_board_bits,
            tight_bits=tight_bits,
            free_oracle_bits=free_oracle_bits,
        ),
    )


def decode_hole_run_bundles(encoded: HoleRunBundleEncoded) -> str:
    seed_index = 0
    raw_index = 0
    group_bits = HOLE_GROUP_CHUNKS * HOLE_BASE_BITS
    out: list[str] = []
    for is_bundle in encoded.modes:
        if is_bundle:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            out.append(expand_hole_run_bundle(seed))
        else:
            chunk = encoded.raw_groups[raw_index:raw_index + group_bits]
            if len(chunk) != group_bits:
                raise ValueError("hole-run raw stream exhausted")
            raw_index += group_bits
            out.append(chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused hole-run seeds")
    if raw_index != len(encoded.raw_groups):
        raise ValueError("unused hole-run raw groups")
    out.append(encoded.tail)
    decoded = "".join(out)
    if len(decoded) != encoded.length:
        raise ValueError("hole-run decoded length mismatch")
    return decoded


def hole_run_bundle_demo(trials: int = 120, n_bits: int = 4096) -> None:
    print("== family 1m: hole-run bundle occupancy ==")
    print("A 4-chunk bundle occupies the first cell and leaves three holes.")
    print("If those holes are visible, they tell the decoder open vs carry.")
    print("If the stream is packed, the omitted hole pattern is just the")
    print("bundle-mode bitmap and must be charged.")
    print()
    rng = Random(424242)
    stats: list[HoleRunBundleStat] = []
    for _ in range(trials):
        bits = format(rng.getrandbits(n_bits), f"0{n_bits}b")
        encoded, stat = encode_hole_run_bundles(bits)
        assert decode_hole_run_bundles(encoded) == bits
        stats.append(stat)
    avg_groups = mean(stat.groups for stat in stats)
    avg_hits = mean(stat.hits for stat in stats)
    avg_charged = mean(stat.charged_bits for stat in stats)
    avg_cell_board = mean(stat.cell_board_bits for stat in stats)
    avg_tight = mean(stat.tight_bits for stat in stats)
    avg_free = mean(stat.free_oracle_bits for stat in stats)
    print(
        f"toy grammar: base={HOLE_BASE_BITS} group={HOLE_GROUP_CHUNKS} "
        f"seed={HOLE_SEED_BITS} n_bits={n_bits}"
    )
    print(f"round_trips={trials}/{trials}")
    print(f"groups={avg_groups:.1f} hits={avg_hits:.3f} "
          f"hit/group={avg_hits / avg_groups:.5f}")
    print(f"{'ledger':>18} {'bits':>10} {'net':>10} {'note':>24}")
    rows = [
        ("free holes", avg_free, "invalid packed oracle"),
        ("1 mode/group", avg_charged, "exact visible codec"),
        ("cell occupancy", avg_cell_board, "explicit hole cells"),
        ("tight bitmap", avg_tight, "enumerative lower bound"),
    ]
    for label, cost, note in rows:
        print(f"{label:>18} {cost:10.3f} {n_bits - cost:10.3f} {note:>24}")
    print()
    group_bits = HOLE_GROUP_CHUNKS * HOLE_BASE_BITS
    p = 2 ** (HOLE_SEED_BITS - group_bits)
    gap = group_bits - HOLE_SEED_BITS
    entropy = binary_entropy(p)
    print("Closed-form group expectation under uniform independent hits:")
    print(f"p={p:.6f} gap={gap} p*gap={p * gap:.6f} "
          f"H(p)={entropy:.6f}")
    print(f"free oracle net/group={p * gap:.6f}")
    print(f"mode net/group={p * gap - 1.0:.6f}")
    print(f"cell-occupancy net/group={p * gap - HOLE_GROUP_CHUNKS:.6f}")
    print(f"tight bitmap net/group={p * gap - entropy:.6f}")
    print()
    print("Reading: holes can be a perfectly good mechanical open/carry")
    print("signal only when the hole pattern remains visible. Packing away")
    print("the holes removes the decoder observation; restoring it costs the")
    print("same mode-map entropy the holes were supposed to avoid.")
    print()


CHECKSUM_SPAN_BITS = 8
CHECKSUM_SEED_BITS = 4
CHECKSUM_SLOTS = 12


def checksum_slot_expand(slot: int, seed: int) -> str:
    return hash_bits("checksum-pruned-slot", slot, seed, n_bits=CHECKSUM_SPAN_BITS)


def build_checksum_slot_books() -> tuple[dict[str, int], ...]:
    books: list[dict[str, int]] = []
    for slot in range(CHECKSUM_SLOTS):
        book: dict[str, int] = {}
        for seed in range(1 << CHECKSUM_SEED_BITS):
            book.setdefault(checksum_slot_expand(slot, seed), seed)
        books.append(book)
    return tuple(books)


CHECKSUM_SLOT_BOOKS = build_checksum_slot_books()


def score_order(slots: int) -> tuple[int, ...]:
    return tuple(sorted(
        range(slots),
        key=lambda slot: (hash_bits("greedy-score-order", slots, slot, n_bits=24), slot),
    ))


@dataclass(frozen=True)
class ScoreOrderEncoded:
    slots: int
    seeds: tuple[int, ...]
    literals: tuple[str, ...]


@dataclass(frozen=True)
class ScoreOrderStat:
    hits: int
    survivors: int
    unique: bool
    bitmap_bits: float
    ambiguity_bits: float
    charged_bits: float


def greedy_score_hit_positions(chunks: list[str], order: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        slot
        for slot in order
        if chunks[slot] in CHECKSUM_SLOT_BOOKS[slot]
    )


def encode_score_order_block(bits: str) -> tuple[ScoreOrderEncoded, str]:
    if len(bits) != CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS:
        raise ValueError("score-order block has wrong length")
    chunks = [
        bits[slot * CHECKSUM_SPAN_BITS:(slot + 1) * CHECKSUM_SPAN_BITS]
        for slot in range(CHECKSUM_SLOTS)
    ]
    order = score_order(CHECKSUM_SLOTS)
    hit_positions = set(greedy_score_hit_positions(chunks, order))
    seeds: list[int] = []
    literals: list[str] = []
    map_bits = ["0"] * CHECKSUM_SLOTS
    for slot in order:
        chunk = chunks[slot]
        if slot in hit_positions:
            seeds.append(CHECKSUM_SLOT_BOOKS[slot][chunk])
            map_bits[slot] = "1"
        else:
            literals.append(chunk)
    return ScoreOrderEncoded(CHECKSUM_SLOTS, tuple(seeds), tuple(literals)), "".join(map_bits)


def decode_score_order_candidates(encoded: ScoreOrderEncoded) -> list[tuple[str, str]]:
    hit_count = len(encoded.seeds)
    order = score_order(encoded.slots)
    survivors: list[tuple[str, str]] = []
    for hit_positions in combinations(order, hit_count):
        hit_set = set(hit_positions)
        seed_index = 0
        literal_index = 0
        chunks = [""] * encoded.slots
        map_bits = ["0"] * encoded.slots
        for slot in order:
            if slot in hit_set:
                seed = encoded.seeds[seed_index]
                seed_index += 1
                chunks[slot] = checksum_slot_expand(slot, seed)
                map_bits[slot] = "1"
            else:
                chunks[slot] = encoded.literals[literal_index]
                literal_index += 1
        if tuple(slot for slot in order if slot in hit_set) != greedy_score_hit_positions(chunks, order):
            continue
        survivors.append(("".join(map_bits), "".join(chunks)))
    return survivors


def greedy_score_order_count_demo(trials: int = 400) -> None:
    print("== family 1n: greedy score-order count-only hit map ==")
    print("This mutation omits the bitmap and stores only the seed/literal")
    print("streams. A public slot order says every matchable chunk must be")
    print("opened as a record; carried literals are valid only when they are")
    print("not in that slot's seed image. The decoder enumerates count-matched")
    print("maps and rejects maps that violate this local greedy rule.")
    print()
    rng = Random(303030)
    stats: list[ScoreOrderStat] = []
    true_survived = 0
    raw_bits = CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS
    for _ in range(trials):
        bits = format(rng.getrandbits(raw_bits), f"0{raw_bits}b")
        encoded, true_map = encode_score_order_block(bits)
        survivors = decode_score_order_candidates(encoded)
        true_survived += any(candidate_bits == bits for _, candidate_bits in survivors)
        hits = len(encoded.seeds)
        bitmap_bits = log2_choose(encoded.slots, hits)
        ambiguity_bits = log2(len(survivors)) if survivors else float("inf")
        charged = (
            hits * CHECKSUM_SEED_BITS
            + (encoded.slots - hits) * CHECKSUM_SPAN_BITS
            + count_class_bits(encoded.slots + 1)
            + ambiguity_bits
        )
        stats.append(
            ScoreOrderStat(
                hits,
                len(survivors),
                len(survivors) == 1,
                bitmap_bits,
                ambiguity_bits,
                charged,
            )
        )
    avg_hits = mean(stat.hits for stat in stats)
    avg_survivors = mean(stat.survivors for stat in stats)
    unique_rate = mean(1.0 if stat.unique else 0.0 for stat in stats)
    avg_bitmap = mean(stat.bitmap_bits for stat in stats)
    avg_ambiguity = mean(stat.ambiguity_bits for stat in stats)
    avg_charged = mean(stat.charged_bits for stat in stats)
    print(f"toy grammar: slots={CHECKSUM_SLOTS} span={CHECKSUM_SPAN_BITS} "
          f"seed={CHECKSUM_SEED_BITS} raw={raw_bits} trials={trials}")
    print(f"round_trips={true_survived}/{trials}")
    print(f"avg hits={avg_hits:.3f} avg survivors={avg_survivors:.3f} "
          f"unique%={unique_rate:.3f}")
    print(f"avg bitmap bits avoided={avg_bitmap:.3f} "
          f"avg ambiguity bits={avg_ambiguity:.3f}")
    print(f"charged={avg_charged:.3f} net={raw_bits - avg_charged:.3f}")
    print()
    print("Reading: the local greedy rule prunes some maps, because a carried")
    print("literal that is seed-matchable would have been opened. But the")
    print("decoder still sees multiple valid seed/literal interleavings on")
    print("average. The omitted bitmap reappears as survivor ambiguity or a")
    print("referee checksum; count-only score order is not a free open/carry")
    print("channel.")
    print()


PREFIX_STOP_BLOCKS = 8
PREFIX_STOP_SLOTS = 6


def prefix_stop_order() -> tuple[int, ...]:
    return score_order(PREFIX_STOP_SLOTS)


def prefix_stop_block_encode(bits: str) -> tuple[str, int]:
    if len(bits) != PREFIX_STOP_SLOTS * CHECKSUM_SPAN_BITS:
        raise ValueError("prefix-stop block has wrong length")
    chunks = [
        bits[slot * CHECKSUM_SPAN_BITS:(slot + 1) * CHECKSUM_SPAN_BITS]
        for slot in range(PREFIX_STOP_SLOTS)
    ]
    order = prefix_stop_order()
    encoded: list[str] = []
    stop = 0
    while stop < PREFIX_STOP_SLOTS:
        slot = order[stop]
        seed = CHECKSUM_SLOT_BOOKS[slot].get(chunks[slot])
        if seed is None:
            break
        encoded.append(format(seed, f"0{CHECKSUM_SEED_BITS}b"))
        stop += 1
    for slot in order[stop:]:
        encoded.append(chunks[slot])
    return "".join(encoded), stop


def prefix_stop_parse_block(stream: str, offset: int, stop: int) -> tuple[str, int] | None:
    order = prefix_stop_order()
    chunks = [""] * PREFIX_STOP_SLOTS
    cursor = offset
    for index in range(stop):
        slot = order[index]
        end = cursor + CHECKSUM_SEED_BITS
        if end > len(stream):
            return None
        seed = int(stream[cursor:end], 2)
        chunks[slot] = checksum_slot_expand(slot, seed)
        cursor = end
    for slot in order[stop:]:
        end = cursor + CHECKSUM_SPAN_BITS
        if end > len(stream):
            return None
        chunks[slot] = stream[cursor:end]
        cursor = end
    if stop < PREFIX_STOP_SLOTS:
        first_literal_slot = order[stop]
        if chunks[first_literal_slot] in CHECKSUM_SLOT_BOOKS[first_literal_slot]:
            return None
    return "".join(chunks), cursor


def prefix_stop_encode_stream(bits: str) -> tuple[str, tuple[int, ...]]:
    raw_block_bits = PREFIX_STOP_SLOTS * CHECKSUM_SPAN_BITS
    if len(bits) % raw_block_bits != 0:
        raise ValueError("prefix-stop stream must have whole blocks")
    encoded: list[str] = []
    stops: list[int] = []
    for block in range(len(bits) // raw_block_bits):
        chunk = bits[block * raw_block_bits:(block + 1) * raw_block_bits]
        block_bits, stop = prefix_stop_block_encode(chunk)
        encoded.append(block_bits)
        stops.append(stop)
    return "".join(encoded), tuple(stops)


def prefix_stop_parse_with_stops(stream: str, stops: tuple[int, ...]) -> str | None:
    offset = 0
    out: list[str] = []
    for stop in stops:
        parsed = prefix_stop_parse_block(stream, offset, stop)
        if parsed is None:
            return None
        block_bits, offset = parsed
        out.append(block_bits)
    if offset != len(stream):
        return None
    return "".join(out)


def prefix_stop_survivor_count(stream: str, blocks: int) -> int:
    @lru_cache(maxsize=None)
    def count(block_index: int, offset: int) -> int:
        if block_index == blocks:
            return 1 if offset == len(stream) else 0
        total = 0
        for stop in range(PREFIX_STOP_SLOTS + 1):
            parsed = prefix_stop_parse_block(stream, offset, stop)
            if parsed is None:
                continue
            _, next_offset = parsed
            total += count(block_index + 1, next_offset)
        return total

    return count(0, 0)


def prefix_stop_countless_demo(trials: int = 120) -> None:
    print("== family 1o: prefix-stop count-free hit map ==")
    print("This mutation removes both the bitmap and per-block hit count in")
    print("a favorable fixed-block setting. In a public slot order, the encoder")
    print("opens consecutive matchable slots until the first miss, then carries")
    print("the rest raw. The compressed block length would reveal the stop count")
    print("only if block boundaries were free; concatenated blocks require the")
    print("decoder to infer all stop counts from the final bitstream.")
    print()
    rng = Random(404040)
    raw_block_bits = PREFIX_STOP_SLOTS * CHECKSUM_SPAN_BITS
    raw_bits = PREFIX_STOP_BLOCKS * raw_block_bits
    true_round_trips = 0
    free_savings: list[int] = []
    survivor_counts: list[int] = []
    ambiguity_nets: list[float] = []
    charged_nets: list[float] = []
    total_stops: list[int] = []
    length_class_bits = count_class_bits((PREFIX_STOP_BLOCKS * PREFIX_STOP_SLOTS) + 1)
    for _ in range(trials):
        bits = format(rng.getrandbits(raw_bits), f"0{raw_bits}b")
        encoded, stops = prefix_stop_encode_stream(bits)
        decoded = prefix_stop_parse_with_stops(encoded, stops)
        if decoded == bits:
            true_round_trips += 1
        survivors = prefix_stop_survivor_count(encoded, PREFIX_STOP_BLOCKS)
        free_save = raw_bits - len(encoded)
        ambiguity = log2(survivors) if survivors > 0 else float("inf")
        free_savings.append(free_save)
        survivor_counts.append(survivors)
        ambiguity_nets.append(free_save - ambiguity)
        charged_nets.append(free_save - ambiguity - length_class_bits)
        total_stops.append(sum(stops))
    print(f"toy grammar: blocks={PREFIX_STOP_BLOCKS} slots/block={PREFIX_STOP_SLOTS} "
          f"span={CHECKSUM_SPAN_BITS} seed={CHECKSUM_SEED_BITS} raw={raw_bits}")
    print(f"true_path_round_trips={true_round_trips}/{trials}")
    print(f"avg opened prefix slots={mean(total_stops):.3f} "
          f"avg free saving={mean(free_savings):.3f} bits")
    print(f"avg survivors={mean(survivor_counts):.3f} "
          f"avg ambiguity={mean(log2(count) for count in survivor_counts):.3f} bits")
    print(f"net after ambiguity={mean(ambiguity_nets):.3f} bits")
    print(f"length/count class={length_class_bits:.3f} bits "
          f"charged net={mean(charged_nets):.3f} bits")
    print()
    print("Reading: the prefix-stop rule removes an explicit count inside")
    print("an isolated block, but concatenated stateless decoding needs block")
    print("boundaries or stop counts. Inferring them from the bitstream leaves")
    print("multiple valid stop-count parses, and the total bit length is itself")
    print("a savings/count class. Once that recursive-layer length channel is")
    print("charged, the apparent finite gain disappears.")
    print()


@dataclass(frozen=True)
class ChecksumPrunedEncoded:
    slots: int
    checksum_bits: int
    seeds: tuple[int, ...]
    literals: tuple[str, ...]
    checksum: str


@dataclass(frozen=True)
class ChecksumPrunedStat:
    hits: int
    assignments: int
    checksum_bits: int
    survivors: int
    bitmap_bits: float
    count_bits: float
    charged_bits: float


def block_checksum(bits: str, checksum_bits: int) -> str:
    if checksum_bits == 0:
        return ""
    return hash_bits("checksum-pruned-block-referee", bits, n_bits=checksum_bits)


def encode_checksum_pruned_block(bits: str, checksum_bits: int) -> tuple[ChecksumPrunedEncoded, str]:
    if len(bits) != CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS:
        raise ValueError("checksum-pruned block has wrong length")
    seeds: list[int] = []
    literals: list[str] = []
    hit_chunks: list[bool] = []
    for slot in range(CHECKSUM_SLOTS):
        chunk = bits[slot * CHECKSUM_SPAN_BITS:(slot + 1) * CHECKSUM_SPAN_BITS]
        seed = CHECKSUM_SLOT_BOOKS[slot].get(chunk)
        if seed is None:
            hit_chunks.append(False)
            literals.append(chunk)
        else:
            hit_chunks.append(True)
            seeds.append(seed)
    return (
        ChecksumPrunedEncoded(
            CHECKSUM_SLOTS,
            checksum_bits,
            tuple(seeds),
            tuple(literals),
            block_checksum(bits, checksum_bits),
        ),
        "".join("1" if hit else "0" for hit in hit_chunks),
    )


def decode_checksum_pruned_candidates(encoded: ChecksumPrunedEncoded) -> list[tuple[str, str]]:
    hit_count = len(encoded.seeds)
    survivors: list[tuple[str, str]] = []
    for hit_positions in combinations(range(encoded.slots), hit_count):
        hit_set = set(hit_positions)
        seed_index = 0
        literal_index = 0
        chunks: list[str] = []
        map_bits: list[str] = []
        for slot in range(encoded.slots):
            if slot in hit_set:
                seed = encoded.seeds[seed_index]
                seed_index += 1
                chunks.append(checksum_slot_expand(slot, seed))
                map_bits.append("1")
            else:
                chunks.append(encoded.literals[literal_index])
                literal_index += 1
                map_bits.append("0")
        bits = "".join(chunks)
        if block_checksum(bits, encoded.checksum_bits) == encoded.checksum:
            survivors.append(("".join(map_bits), bits))
    return survivors


def checksum_pruned_hitmap_demo(trials: int = 200) -> None:
    print("== family 1m: checksum-pruned hit-map search ==")
    print("This mutation omits the hit bitmap. The decoder receives ordered")
    print("seed and literal streams, so the hit count is known from stream")
    print("lengths, then tries all C(slots,hits) hit-position assignments and")
    print("uses a block checksum to prune wrong maps.")
    print()
    rng = Random(929292)
    print(f"toy grammar: slots={CHECKSUM_SLOTS} span={CHECKSUM_SPAN_BITS} "
          f"seed={CHECKSUM_SEED_BITS}")
    print(f"{'chk':>4} {'hits':>8} {'assign':>9} {'survivors':>10} "
          f"{'uniq%':>8} {'bitmap':>9} {'charged':>9} {'net':>9}")
    for checksum_bits in [0, 2, 4, 6, 8, 10, 12]:
        stats: list[ChecksumPrunedStat] = []
        unique = 0
        for _ in range(trials):
            bits = format(rng.getrandbits(CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS),
                          f"0{CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS}b")
            encoded, true_map = encode_checksum_pruned_block(bits, checksum_bits)
            survivors = decode_checksum_pruned_candidates(encoded)
            assert any(candidate_bits == bits and map_bits == true_map
                       for map_bits, candidate_bits in survivors)
            if len(survivors) == 1:
                unique += 1
            hit_count = len(encoded.seeds)
            assignments = len(list(combinations(range(encoded.slots), hit_count)))
            bitmap_bits = log2_choose(encoded.slots, hit_count)
            count_bits = count_class_bits(encoded.slots + 1)
            literal_bits = len(encoded.literals) * CHECKSUM_SPAN_BITS
            seed_bits = hit_count * CHECKSUM_SEED_BITS
            charged_bits = literal_bits + seed_bits + count_bits + checksum_bits
            stats.append(ChecksumPrunedStat(
                hit_count,
                assignments,
                checksum_bits,
                len(survivors),
                bitmap_bits,
                count_bits,
                charged_bits,
            ))
        avg_hits = mean(stat.hits for stat in stats)
        avg_assign = mean(stat.assignments for stat in stats)
        avg_survivors = mean(stat.survivors for stat in stats)
        avg_bitmap = mean(stat.bitmap_bits for stat in stats)
        avg_charged = mean(stat.charged_bits for stat in stats)
        raw_bits = CHECKSUM_SLOTS * CHECKSUM_SPAN_BITS
        print(f"{checksum_bits:4d} {avg_hits:8.3f} {avg_assign:9.3f} "
              f"{avg_survivors:10.3f} {unique / trials:8.3f} "
              f"{avg_bitmap:9.3f} {avg_charged:9.3f} {raw_bits - avg_charged:9.3f}")
    print()
    print("Closed-form checksum pruning for fixed hit count:")
    print(f"{'hits':>5} {'maps':>8} {'log2 maps':>10} {'chk for ~1':>11}")
    for hit_count in range(0, CHECKSUM_SLOTS + 1):
        maps = len(list(combinations(range(CHECKSUM_SLOTS), hit_count)))
        map_bits = log2(maps) if maps else 0.0
        print(f"{hit_count:5d} {maps:8d} {map_bits:10.3f} {ceil(map_bits):11d}")
    print()
    print("Reading: checksum search is a real nonlocal coupling, but a checksum")
    print("wide enough to leave about one map survivor has the same width as")
    print("the enumerative hit map it replaces. Shorter checksums leave multiple")
    print("valid decodes; wider checksums overpay. The hit count itself is also")
    print("a channel unless the stream lengths already expose it and are charged.")
    print()


VALUE_CODE_L = 8
VALUE_CODE_SEED_BITS = 4
VALUE_CODE_STATE_BITS = 3
VALUE_CODE_STATE_COUNT = 1 << VALUE_CODE_STATE_BITS


@dataclass
class ValueCodeStateTable:
    short_len: int
    long_len: int
    seed_by_chunk: dict[int, int]
    code_by_chunk: dict[int, str]
    decode_trie: dict[str, object]


@dataclass
class ValueCodeLayerStat:
    input_bits: int
    output_bits: int
    chunks: int
    hits: int
    short_len: int
    mean_long_len: float


def build_canonical_prefix_codes(length_by_symbol: dict[int, int]) -> dict[int, str]:
    entries = sorted((length, symbol) for symbol, length in length_by_symbol.items())
    code = 0
    previous_length = 0
    codes: dict[int, str] = {}
    for length, symbol in entries:
        code <<= length - previous_length
        if code >= (1 << length):
            raise ValueError("prefix-code lengths exceed Kraft capacity")
        codes[symbol] = format(code, f"0{length}b")
        code += 1
        previous_length = length
    return codes


def add_to_decode_trie(trie: dict[str, object], code: str, symbol: int) -> None:
    node = trie
    for bit in code:
        child = node.setdefault(bit, {})
        if not isinstance(child, dict):
            raise ValueError("prefix collision while building decode trie")
        node = child
    if "symbol" in node or "0" in node or "1" in node:
        raise ValueError("prefix collision while building decode trie")
    node["symbol"] = symbol


def parse_decode_trie(trie: dict[str, object], bits: str, index: int) -> tuple[int, int]:
    node = trie
    cursor = index
    while cursor < len(bits):
        child = node.get(bits[cursor])
        if not isinstance(child, dict):
            break
        node = child
        cursor += 1
        symbol = node.get("symbol")
        if isinstance(symbol, int):
            return symbol, cursor
    raise ValueError("value-code stream does not match the prefix grammar")


def value_code_expand(state: int, seed: int, span_bits: int = VALUE_CODE_L) -> str:
    return hash_bits("tagless-value-code", state, seed, n_bits=span_bits)


def value_code_state_table(short_len: int, state: int) -> ValueCodeStateTable:
    seed_count = 1 << VALUE_CODE_SEED_BITS
    alphabet = 1 << VALUE_CODE_L
    seed_by_chunk: dict[int, int] = {}
    for seed in range(seed_count):
        chunk = int(value_code_expand(state, seed), 2)
        seed_by_chunk.setdefault(chunk, seed)
    short_count = len(seed_by_chunk)
    complement_count = alphabet - short_count
    remaining_kraft = 1.0 - short_count * (2 ** -short_len)
    if remaining_kraft <= 0.0:
        raise ValueError("short code class consumes the whole prefix tree")
    long_len = 0 if complement_count == 0 else ceil(log2(complement_count / remaining_kraft))
    length_by_symbol: dict[int, int] = {}
    for symbol in range(alphabet):
        length_by_symbol[symbol] = short_len if symbol in seed_by_chunk else long_len
    codes = build_canonical_prefix_codes(length_by_symbol)
    trie: dict[str, object] = {}
    for symbol, code in codes.items():
        add_to_decode_trie(trie, code, symbol)
    return ValueCodeStateTable(short_len, long_len, seed_by_chunk, codes, trie)


def build_value_code_tables(short_len: int) -> tuple[ValueCodeStateTable, ...]:
    return tuple(value_code_state_table(short_len, state)
                 for state in range(VALUE_CODE_STATE_COUNT))


def encode_value_code_layer(
    bits: str,
    short_len: int,
    tables: tuple[ValueCodeStateTable, ...],
) -> tuple[str, ValueCodeLayerStat]:
    state = 0
    out: list[str] = []
    hits = 0
    chunks = len(bits) // VALUE_CODE_L
    for chunk_index in range(chunks):
        chunk = bits[chunk_index * VALUE_CODE_L:(chunk_index + 1) * VALUE_CODE_L]
        symbol = int(chunk, 2)
        table = tables[state]
        if symbol in table.seed_by_chunk:
            hits += 1
        out.append(table.code_by_chunk[symbol])
        state = step_token_state(state, chunk, VALUE_CODE_STATE_BITS)
    tail = bits[chunks * VALUE_CODE_L:]
    out.append(tail)
    encoded = "".join(out)
    mean_long_len = mean(table.long_len for table in tables)
    return (
        encoded,
        ValueCodeLayerStat(len(bits), len(encoded), chunks, hits, short_len, mean_long_len),
    )


def decode_value_code_layer(
    encoded: str,
    output_length: int,
    tables: tuple[ValueCodeStateTable, ...],
) -> str:
    state = 0
    out: list[str] = []
    index = 0
    chunks = output_length // VALUE_CODE_L
    for _ in range(chunks):
        table = tables[state]
        symbol, index = parse_decode_trie(table.decode_trie, encoded, index)
        seed = table.seed_by_chunk.get(symbol)
        if seed is None:
            chunk = format(symbol, f"0{VALUE_CODE_L}b")
        else:
            chunk = value_code_expand(state, seed)
        out.append(chunk)
        state = step_token_state(state, chunk, VALUE_CODE_STATE_BITS)
    tail_len = output_length - chunks * VALUE_CODE_L
    tail = encoded[index:index + tail_len]
    if len(tail) != tail_len:
        raise ValueError("value-code tail exhausted")
    index += tail_len
    if index != len(encoded):
        raise ValueError("unused value-code suffix")
    out.append(tail)
    return "".join(out)


def value_code_expected_bits(span_bits: int, seed_bits: int, short_len: int) -> tuple[float, float, float]:
    hit_p = 2 ** (seed_bits - span_bits)
    remaining_kraft = 1.0 - 2 ** (seed_bits - short_len)
    if remaining_kraft <= 0.0:
        return hit_p, float("inf"), float("inf")
    complement = (1 << span_bits) - (1 << seed_bits)
    ideal_long = log2(complement / remaining_kraft)
    expected = hit_p * short_len + (1.0 - hit_p) * ideal_long
    return hit_p, ideal_long, expected


def tagless_value_code_demo(trials: int = 200, n_bits: int = 512, passes: int = 4) -> None:
    print("== family 1i: tagless value-code open/carry derivation ==")
    print("This mutation removes the hit bitmap. For each decoder-known state,")
    print("seed-image chunks get short prefix codewords and non-image chunks get")
    print("long complement codewords. Open vs carry is derived from the parsed")
    print("value class, not from a side bitmap. The price is Kraft space.")
    print()
    rng = Random(445566)
    print(f"exact toy: span={VALUE_CODE_L} seed={VALUE_CODE_SEED_BITS} "
          f"state_bits={VALUE_CODE_STATE_BITS}")
    print(f"{'short':>6} {'pass':>4} {'avg in':>9} {'avg out':>9} "
          f"{'hit/chunk':>10} {'long':>7} {'delta orig':>11}")
    for short_len in [VALUE_CODE_SEED_BITS + 1, VALUE_CODE_SEED_BITS + 2, VALUE_CODE_L]:
        tables = build_value_code_tables(short_len)
        final_delta: list[int] = []
        per_pass: list[list[ValueCodeLayerStat]] = [[] for _ in range(passes)]
        for _ in range(trials):
            original = format(rng.getrandbits(n_bits), f"0{n_bits}b")
            current = original
            lengths: list[int] = []
            for pass_index in range(passes):
                lengths.append(len(current))
                current, stat = encode_value_code_layer(current, short_len, tables)
                per_pass[pass_index].append(stat)
            decoded = current
            for output_length in reversed(lengths):
                decoded = decode_value_code_layer(decoded, output_length, tables)
            assert decoded == original
            final_delta.append(n_bits - len(current))
        for pass_index, stats in enumerate(per_pass, start=1):
            avg_in = mean(stat.input_bits for stat in stats)
            avg_out = mean(stat.output_bits for stat in stats)
            avg_hits = mean(stat.hits for stat in stats)
            avg_chunks = mean(stat.chunks for stat in stats)
            hit_rate = avg_hits / avg_chunks if avg_chunks else 0.0
            avg_long = mean(stat.mean_long_len for stat in stats)
            delta_orig = n_bits - avg_out
            print(f"{short_len:6d} {pass_index:4d} {avg_in:9.2f} {avg_out:9.2f} "
                  f"{hit_rate:10.5f} {avg_long:7.2f} {delta_orig:11.3f}")
        print(f"{'':6s} {'final':>4} {'':9s} {mean(n_bits - d for d in final_delta):9.2f} "
              f"{'':10s} {'':7s} {mean(final_delta):11.3f}")
    print()
    print("Ideal Kraft ledger for one uniform chunk, ignoring integer code")
    print("rounding and collisions:")
    print(f"{'L':>4} {'r':>4} {'short':>6} {'hit p':>10} "
          f"{'ideal long':>11} {'E bits':>9} {'E save':>9}")
    for span_bits, seed_bits in [(8, 4), (14, 10), (32, 16)]:
        for short_len in [seed_bits + 1, seed_bits + 2, span_bits]:
            hit_p, ideal_long, expected = value_code_expected_bits(span_bits, seed_bits, short_len)
            print(f"{span_bits:4d} {seed_bits:4d} {short_len:6d} {hit_p:10.5f} "
                  f"{ideal_long:11.5f} {expected:9.5f} {span_bits - expected:9.5f}")
    print()
    print("Reading: this gives the decoder a real stateless open/carry rule,")
    print("and the state can refresh which chunks are seed-image chunks. But")
    print("under uniform chunks, the prefix tree's Kraft conservation cancels")
    print("the short seed words with longer complement literals. The only")
    print("non-bloating setting is the no-compression point where short words")
    print("are as long as raw chunks.")
    print()


@dataclass(frozen=True)
class FiniteClassDesign:
    name: str
    span_bits: int
    classes: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class FiniteClassLedger:
    span_bits: int
    image_fraction: float
    kraft_used: float
    fallback_len: float
    expected_bits: float
    saving_bits: float
    valid: bool


def finite_class_local_ledger(span_bits: int, classes: tuple[tuple[int, int], ...]) -> FiniteClassLedger:
    """Optimistic uniform-source ledger for local seed-image/fallback grammars.

    Each class is (image_bits, code_bits), meaning 2^image_bits disjoint seed
    images get codewords of length code_bits. Non-image chunks get an ideal
    fallback code using all remaining Kraft mass. Hash collisions and fallback
    integer code lengths are ignored, so this is deliberately favorable.
    """
    alphabet = 1 << span_bits
    image_count = sum(1 << image_bits for image_bits, _ in classes)
    kraft_used = sum((1 << image_bits) * (2 ** (-code_bits))
                     for image_bits, code_bits in classes)
    if image_count > alphabet or kraft_used > 1.0:
        return FiniteClassLedger(span_bits, image_count / alphabet, kraft_used,
                                 float("nan"), float("inf"), float("-inf"), False)
    fallback_count = alphabet - image_count
    record_expectation = sum(((1 << image_bits) / alphabet) * code_bits
                             for image_bits, code_bits in classes)
    if fallback_count == 0:
        expected = record_expectation
        return FiniteClassLedger(span_bits, 1.0, kraft_used, 0.0,
                                 expected, span_bits - expected, True)
    remaining_kraft = 1.0 - kraft_used
    if remaining_kraft <= 0.0:
        return FiniteClassLedger(span_bits, image_count / alphabet, kraft_used,
                                 float("inf"), float("inf"), float("-inf"), False)
    fallback_len = log2(fallback_count / remaining_kraft)
    expected = record_expectation + (fallback_count / alphabet) * fallback_len
    return FiniteClassLedger(span_bits, image_count / alphabet, kraft_used,
                             fallback_len, expected, span_bits - expected, True)


def finite_class_design_label(classes: tuple[tuple[int, int], ...]) -> str:
    return "+".join(f"{image}/{code}" for image, code in classes)


def finite_class_kraft_bound_demo() -> None:
    print("== finite-class local grammar Kraft bound ==")
    print("This is a scoped impossibility check for local per-slot grammars:")
    print("decoder-known classes, seed lengths, lanes, or salts produce seed")
    print("image codewords, and all other chunks use an ideal fallback language.")
    print("If open/carry is local and no bitmap/side map is stored, these")
    print("codewords form a prefix code over the uniform chunk alphabet.")
    print()
    designs = [
        FiniteClassDesign("tagless r10 c11", 14, ((10, 11),)),
        FiniteClassDesign("tagless r10 c12", 14, ((10, 12),)),
        FiniteClassDesign("raw point r10 c14", 14, ((10, 14),)),
        FiniteClassDesign("seed length 9/10", 14, ((9, 10), (10, 11))),
        FiniteClassDesign("seed length 8/9/10", 14, ((8, 10), (9, 11), (10, 12))),
        FiniteClassDesign("mixed lanes 6/8/10", 14, ((6, 8), (8, 10), (10, 12))),
        FiniteClassDesign("visible nonce k2", 16, ((12, 14),)),
        FiniteClassDesign("visible nonce k4", 16, ((14, 16),)),
    ]
    print(f"{'design':>22} {'img frac':>10} {'Kraft':>10} {'fallback':>10} "
          f"{'E bits':>10} {'save':>10}")
    for design in designs:
        ledger = finite_class_local_ledger(design.span_bits, design.classes)
        print(f"{design.name:>22} {ledger.image_fraction:10.5f} "
              f"{ledger.kraft_used:10.5f} {ledger.fallback_len:10.5f} "
              f"{ledger.expected_bits:10.5f} {ledger.saving_bits:10.5f}")
    print()
    print("Best brute-force local designs with at least one short seed-image")
    print("class, under the same optimistic disjoint-image/ideal-fallback model:")
    candidates: list[tuple[float, tuple[tuple[int, int], ...], FiniteClassLedger]] = []
    base_classes = [(image_bits, code_bits)
                    for image_bits in range(2, 13)
                    for code_bits in range(image_bits + 1, 15)]
    for first_index, first in enumerate(base_classes):
        for second_index in range(first_index, len(base_classes)):
            for third_index in range(second_index, len(base_classes)):
                classes = tuple(sorted((first, base_classes[second_index], base_classes[third_index])))
                if all(code_bits >= 14 for _, code_bits in classes):
                    continue
                ledger = finite_class_local_ledger(14, classes)
                if ledger.valid:
                    candidates.append((ledger.saving_bits, classes, ledger))
    print(f"{'classes image/code':>26} {'img frac':>10} {'Kraft':>10} "
          f"{'E bits':>10} {'save':>10}")
    for saving, classes, ledger in sorted(candidates, key=lambda item: item[0], reverse=True)[:8]:
        print(f"{finite_class_design_label(classes):>26} {ledger.image_fraction:10.5f} "
              f"{ledger.kraft_used:10.5f} {ledger.expected_bits:10.5f} {saving:10.5f}")
    print()
    print("Reading: this does not rule out nonlocal side information, shaped")
    print("sources, generated reachable sets, or finite bundle parse subsidies.")
    print("It does rule out a broad class of local parser-known nonce tricks:")
    print("when arbitrary chunks are uniform and fallback is lossless, the")
    print("seed-image/fallback prefix code cannot have expected length below")
    print("the raw chunk width. Any apparent win needs a bitmap, distributional")
    print("restriction, arrangement channel, or nonlocal coupling to pay for it.")
    print()


# ---------------------------------------------------------------------------
# Family 3: self-dating grammar / wrong-pass explosion.


BBL_E_BITS_BY_ARITY = {
    2: 9.36,
    3: 12.59,
    4: 14.97,
    5: 18.20,
}


def bbl_ambiguity_cost(arity: int, passes: int) -> float:
    e_bits = BBL_E_BITS_BY_ARITY[arity]
    return log2(1.0 + (passes - 1) * (2.0 ** -e_bits))


def bbl_random_bundle_density_surface_demo() -> None:
    print("== family 3d: BBL random-density ambiguity surface ==")
    print("This separates two ledgers for length-pinned bundles. In a dense")
    print("selected-bundle regime, BBL pays only the wrong-pass ambiguity")
    print("c_a(P). For arbitrary/random scheduled windows, the decoder must")
    print("also learn which rare windows hit; the hit-map entropy is the")
    print("open/carry channel.")
    print()
    block_bits = 24
    header_bits = 3
    passes_list = [64, 1_000_000, 1_000_000_000]
    print(f"sparse uniform windows: block={block_bits} bits header={header_bits} bits")
    print(f"{'a':>2} {'P':>10} {'c_a(P)':>8} {'best d':>7} {'hit p':>11} "
          f"{'no-map E':>10} {'map net/hit':>12} {'map E':>11}")
    for arity in [2, 3, 4, 5]:
        for passes in passes_list:
            ambiguity = bbl_ambiguity_cost(arity, passes)
            best: tuple[float, int, float, float, float] | None = None
            for gap in range(max(1, int(ambiguity) + 1), 81):
                hit_p = 2.0 ** -(gap + header_bits)
                no_map_expected = hit_p * (gap - ambiguity)
                map_cost_per_hit = binary_entropy(hit_p) / hit_p
                map_net_per_hit = gap - ambiguity - map_cost_per_hit
                map_expected = hit_p * map_net_per_hit
                if best is None or no_map_expected > best[0]:
                    best = (no_map_expected, gap, hit_p, map_net_per_hit, map_expected)
            assert best is not None
            no_map_expected, gap, hit_p, map_net_per_hit, map_expected = best
            print(f"{arity:2d} {passes:10d} {ambiguity:8.3f} {gap:7d} "
                  f"{hit_p:11.3e} {no_map_expected:10.3e} "
                  f"{map_net_per_hit:12.3f} {map_expected:11.3e}")
        print()

    print("dense half-layer requirement if every public group could be selected:")
    print(f"{'a':>2} {'P':>10} {'c_a(P)':>8} {'gap for 50%':>12} "
          f"{'uniform hit p':>14} {'random groups':>13}")
    for arity in [2, 3, 4, 5]:
        for passes in [64, 1_000_000]:
            ambiguity = bbl_ambiguity_cost(arity, passes)
            required_gap = ceil(ambiguity + (arity * block_bits / 2.0))
            hit_p = 2.0 ** -(required_gap + header_bits)
            print(f"{arity:2d} {passes:10d} {ambiguity:8.3f} {required_gap:12d} "
                  f"{hit_p:14.3e} {hit_p:13.3e}")
        print()
    print("Reading: high arity really does make birth/open ambiguity nearly")
    print("free over large finite pass windows. That is BBL's valid ledge.")
    print("For arbitrary random windows, though, the same rare-hit map costs")
    print("more than the selected savings: per-hit map entropy is about")
    print("log2(1/p)+1/ln(2), which exceeds the gross gap by the header plus")
    print("ambiguity. To get a 50% layer from dense bundles, random data would")
    print("need an exponentially unlikely density of large-gap hits.")
    print()


def grammar_item_survival_probability(residue_bits: int, record_bias: bool = True) -> float:
    """Probability that random bits parse as one locally valid item.

    Literal item: prefix 0 plus residue check.
    Record item: prefix 10 plus residue check when record_bias=True.
    Prefix 11 is invalid. The residue check models a local checksum/residue
    that true items carry and wrong expansions satisfy by chance.
    """
    residue = 2 ** (-residue_bits)
    literal = 0.5 * residue
    record = 0.25 * residue if record_bias else 0.0
    return literal + record


def self_dating_grammar_sweep() -> None:
    print("== family 3: self-dating grammar / wrong-pass explosion ==")
    print("Residue bits make wrong openings fail, but true targets must carry")
    print("those bits too, so arbitrary match supply shrinks at the same time.")
    print()
    base_b = 8
    seed_bits = 13
    marker_bits = 2
    passes = 1_000_000
    print(f"{'arity':>5} {'res':>4} {'span':>6} {'gross':>7} {'hit p':>11} "
          f"{'ambig':>8} {'E net/window':>13}")
    best: tuple[float, int, int] | None = None
    for arity in range(2, 6):
        for residue_bits in range(0, 13, 2):
            item_bits_with_residue = 1 + base_b + residue_bits
            span = arity * item_bits_with_residue
            record = marker_bits + seed_bits
            gross = span - record
            hit_p = min(1.0, (1 << seed_bits) / (2 ** span))
            q_item = grammar_item_survival_probability(residue_bits)
            q_wrong = q_item ** arity
            ambiguity = log2(1 + (passes - 1) * q_wrong)
            net_per_window = hit_p * max(0.0, gross - ambiguity)
            if best is None or net_per_window > best[0]:
                best = (net_per_window, arity, residue_bits)
            print(f"{arity:5d} {residue_bits:4d} {span:6d} {gross:7d} "
                  f"{hit_p:11.3e} {ambiguity:8.3f} {net_per_window:13.3e}")
        print()
    assert best is not None
    print(f"best toy expected net/window={best[0]:.3e} at arity={best[1]} residue={best[2]}")
    print()
    print("Reading: self-dating grammar can push wrong-pass ambiguity down by")
    print("construction. The same residue bits lengthen the target language,")
    print("so arbitrary content supplies fewer exact hits. This is a promising")
    print("finite ambiguity lever, but not yet an arbitrary-content density")
    print("solution.")
    print()


def residue_checksum(data_bits: str, pass_index: int, residue_bits: int) -> str:
    if residue_bits == 0:
        return ""
    return hash_bits("residue-valid-bundle-check", pass_index, data_bits, n_bits=residue_bits)


def residue_is_valid(chunk: str, data_bits: int, pass_index: int, residue_bits: int) -> bool:
    data = chunk[:data_bits]
    residue = chunk[data_bits:data_bits + residue_bits]
    if len(data) != data_bits or len(residue) != residue_bits:
        return False
    return residue == residue_checksum(data, pass_index, residue_bits)


def residue_raw_filter_expand(seed: int, pass_index: int, span_bits: int) -> str:
    return hash_bits("residue-raw-filter-expand", pass_index, seed, n_bits=span_bits)


def residue_constrained_expand(
    seed: int,
    pass_index: int,
    data_bits: int,
    residue_bits: int,
) -> str:
    data = hash_bits("residue-constrained-data", pass_index, seed, n_bits=data_bits)
    return data + residue_checksum(data, pass_index, residue_bits)


def residue_syndrome_expand(
    seed: int,
    pass_index: int,
    data_bits: int,
    residue_bits: int,
    syndrome: str,
) -> str:
    data = hash_bits("residue-syndrome-data", pass_index, seed, n_bits=data_bits)
    expected = residue_checksum(data, pass_index, residue_bits)
    repaired = "".join("1" if a != b else "0" for a, b in zip(expected, syndrome))
    return data + repaired


@lru_cache(maxsize=4096)
def residue_raw_filter_book(
    pass_index: int,
    seed_bits: int,
    data_bits: int,
    residue_bits: int,
) -> dict[str, int]:
    span_bits = data_bits + residue_bits
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        chunk = residue_raw_filter_expand(seed, pass_index, span_bits)
        if residue_is_valid(chunk, data_bits, pass_index, residue_bits):
            book.setdefault(chunk, seed)
    return book


@lru_cache(maxsize=4096)
def residue_constrained_book(
    pass_index: int,
    seed_bits: int,
    data_bits: int,
    residue_bits: int,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        book.setdefault(
            residue_constrained_expand(seed, pass_index, data_bits, residue_bits),
            seed,
        )
    return book


@lru_cache(maxsize=4096)
def residue_syndrome_data_book(
    pass_index: int,
    seed_bits: int,
    data_bits: int,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        data = hash_bits("residue-syndrome-data", pass_index, seed, n_bits=data_bits)
        book.setdefault(data, seed)
    return book


@dataclass
class ResidueTrilemmaLayerStat:
    mode: str
    pass_index: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    valid_targets: int
    record_bits: int
    tight_charged_bits: float
    wrong_survival: float


def encode_residue_trilemma_layer(
    bits: str,
    mode: str,
    pass_index: int,
    seed_bits: int,
    data_bits: int,
    residue_bits: int,
) -> tuple[str, ResidueTrilemmaLayerStat]:
    span_bits = data_bits + residue_bits
    chunks = len(bits) // span_bits
    tail = bits[chunks * span_bits:]
    out: list[str] = []
    hits = 0
    valid_targets = 0
    wrong_survival_trials = 512
    wrong_survivors = 0
    rng = Random(990000 + len(mode) * 101 + residue_bits * 17 + pass_index)
    for chunk_index in range(chunks):
        chunk = bits[chunk_index * span_bits:(chunk_index + 1) * span_bits]
        valid_targets += int(residue_is_valid(chunk, data_bits, pass_index, residue_bits))
        if mode == "raw-filter":
            seed = residue_raw_filter_book(
                pass_index, seed_bits, data_bits, residue_bits,
            ).get(chunk)
            if seed is None:
                out.append("0" + chunk)
            else:
                out.append("1" + format(seed, f"0{seed_bits}b"))
                hits += 1
        elif mode == "constrained":
            seed = residue_constrained_book(
                pass_index, seed_bits, data_bits, residue_bits,
            ).get(chunk)
            if seed is None:
                out.append("0" + chunk)
            else:
                out.append("1" + format(seed, f"0{seed_bits}b"))
                hits += 1
        elif mode == "syndrome":
            data = chunk[:data_bits]
            seed = residue_syndrome_data_book(pass_index, seed_bits, data_bits).get(data)
            if seed is None:
                out.append("0" + chunk)
            else:
                expected = residue_checksum(data, pass_index, residue_bits)
                residue = chunk[data_bits:data_bits + residue_bits]
                syndrome = "".join("1" if a != b else "0" for a, b in zip(expected, residue))
                out.append("1" + format(seed, f"0{seed_bits}b") + syndrome)
                hits += 1
        else:
            raise ValueError(f"unknown residue trilemma mode {mode!r}")

    if tail:
        out.append(tail)

    wrong_pass = pass_index + 1
    for _ in range(wrong_survival_trials):
        seed = rng.randrange(1 << seed_bits)
        if mode == "raw-filter":
            wrong = residue_raw_filter_expand(seed, wrong_pass, span_bits)
            wrong_survivors += int(residue_is_valid(wrong, data_bits, wrong_pass, residue_bits))
        elif mode == "constrained":
            wrong = residue_constrained_expand(seed, wrong_pass, data_bits, residue_bits)
            wrong_survivors += int(residue_is_valid(wrong, data_bits, wrong_pass, residue_bits))
        else:
            syndrome_value = rng.randrange(1 << residue_bits) if residue_bits else 0
            syndrome = "" if residue_bits == 0 else format(syndrome_value, f"0{residue_bits}b")
            wrong = residue_syndrome_expand(
                seed,
                wrong_pass,
                data_bits,
                residue_bits,
                syndrome,
            )
            # The syndrome is part of the record's repair language. A separate
            # validity check would reject true arbitrary targets too.
            wrong_survivors += int(len(wrong) == span_bits)

    bitmap_bits = log2_choose(chunks, hits)
    count_bits = count_class_bits(chunks + 1)
    per_record_bits = seed_bits if mode != "syndrome" else seed_bits + residue_bits
    tight_charged = (
        (chunks - hits) * span_bits
        + hits * per_record_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, ResidueTrilemmaLayerStat(
        mode,
        pass_index,
        len(bits),
        len(encoded),
        chunks,
        hits,
        valid_targets,
        per_record_bits,
        tight_charged,
        wrong_survivors / wrong_survival_trials,
    )


def decode_residue_trilemma_layer(
    encoded: str,
    stat: ResidueTrilemmaLayerStat,
    seed_bits: int,
    data_bits: int,
    residue_bits: int,
) -> str:
    span_bits = data_bits + residue_bits
    chunks: list[str] = []
    offset = 0
    for _ in range(stat.chunks):
        tag = encoded[offset]
        if tag == "0":
            end = offset + 1 + span_bits
            if end > len(encoded):
                raise ValueError("truncated residue literal")
            chunks.append(encoded[offset + 1:end])
            offset = end
        elif tag == "1":
            if stat.mode == "syndrome":
                end = offset + 1 + seed_bits + residue_bits
                if end > len(encoded):
                    raise ValueError("truncated residue syndrome record")
                seed = int(encoded[offset + 1:offset + 1 + seed_bits], 2)
                syndrome = encoded[offset + 1 + seed_bits:end]
                chunks.append(
                    residue_syndrome_expand(
                        seed,
                        stat.pass_index,
                        data_bits,
                        residue_bits,
                        syndrome,
                    )
                )
            else:
                end = offset + 1 + seed_bits
                if end > len(encoded):
                    raise ValueError("truncated residue record")
                seed = int(encoded[offset + 1:end], 2)
                if stat.mode == "raw-filter":
                    chunks.append(
                        residue_raw_filter_expand(
                            seed,
                            stat.pass_index,
                            span_bits,
                        )
                    )
                elif stat.mode == "constrained":
                    chunks.append(
                        residue_constrained_expand(
                            seed,
                            stat.pass_index,
                            data_bits,
                            residue_bits,
                        )
                    )
                else:
                    raise ValueError(f"unknown residue trilemma mode {stat.mode!r}")
            offset = end
        else:
            raise ValueError(f"invalid residue tag {tag!r}")
    tail = encoded[offset:]
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("residue decoded length mismatch")
    return decoded


def residue_syndrome_trilemma_demo(
    trials: int = 80,
    chunks: int = 64,
    data_bits: int = 8,
    seed_bits: int = 6,
    pass_window: int = 1_000_000,
) -> None:
    print("== family 3f: residue validity / syndrome trilemma ==")
    print("Residue-valid bundle grammars have three distinct ledgers. Filtering")
    print("random hash outputs gives wrong-pass pruning but arbitrary targets")
    print("must already satisfy the residue. Constraining the expander to valid")
    print("strings keeps outputs valid but wrong-pass openings also stay valid.")
    print("Storing a syndrome repairs arbitrary targets, but the syndrome is a")
    print("paid record field and removes the structural wrong-pass failure.")
    print()
    rng = Random(929292)
    print(
        f"toy codec: data={data_bits} seed={seed_bits} chunks={chunks} "
        f"trials={trials} pass_window={pass_window}"
    )
    print(
        f"{'res':>3} {'mode':>12} {'valid%':>8} {'hit/ch':>8} "
        f"{'wrong q':>9} {'ambig':>8} {'vis net':>9} "
        f"{'tight':>9} {'closed':>9}"
    )
    for residue_bits in [0, 2, 4, 6]:
        span_bits = data_bits + residue_bits
        for mode in ["raw-filter", "constrained", "syndrome"]:
            stats: list[ResidueTrilemmaLayerStat] = []
            for trial in range(trials):
                bits = format(rng.getrandbits(chunks * span_bits), f"0{chunks * span_bits}b")
                encoded, stat = encode_residue_trilemma_layer(
                    bits,
                    mode,
                    pass_index=trial + 1,
                    seed_bits=seed_bits,
                    data_bits=data_bits,
                    residue_bits=residue_bits,
                )
                assert decode_residue_trilemma_layer(
                    encoded,
                    stat,
                    seed_bits,
                    data_bits,
                    residue_bits,
                ) == bits
                stats.append(stat)
            avg_hits = mean(stat.hits for stat in stats)
            avg_valid = mean(stat.valid_targets for stat in stats)
            hit_rate = avg_hits / chunks
            valid_rate = avg_valid / chunks
            wrong_q = mean(stat.wrong_survival for stat in stats)
            ambiguity = log2(1 + (pass_window - 1) * max(wrong_q, 1e-12))
            visible_net = mean(stat.before_bits - stat.after_bits for stat in stats)
            tight_net = mean(stat.before_bits - stat.tight_charged_bits for stat in stats)
            if mode == "raw-filter":
                closed_hit = (2.0 ** -residue_bits) * (2.0 ** (seed_bits - span_bits))
                closed_record = seed_bits
            elif mode == "constrained":
                closed_hit = (2.0 ** -residue_bits) * min(1.0, 2.0 ** (seed_bits - data_bits))
                closed_record = seed_bits
            else:
                closed_hit = min(1.0, 2.0 ** (seed_bits - data_bits))
                closed_record = seed_bits + residue_bits
            closed_gap = span_bits - closed_record - ambiguity
            closed = closed_hit * closed_gap - binary_entropy(min(max(closed_hit, 0.0), 1.0))
            print(
                f"{residue_bits:3d} {mode:>12} {100.0 * valid_rate:8.3f} "
                f"{hit_rate:8.4f} {wrong_q:9.5f} {ambiguity:8.3f} "
                f"{visible_net:9.3f} {tight_net:9.3f} {closed:9.3f}"
            )
        print()
    print("Reading: residue bits can be used in only one place. If they prune")
    print("wrong passes, they also thin arbitrary true targets. If the expander")
    print("or a syndrome makes arbitrary targets reachable again, wrong-pass")
    print("survival rises to one or the residue bits are paid in the record.")
    print("The trilemma has no winning row under uniform scheduled chunks.")
    print()


def oob_check_payload(pass_index: int, seed: int, data_bits: int) -> str:
    return hash_bits("out-of-band-check-payload", pass_index, seed, n_bits=data_bits)


def oob_fixed_check(seed: int, check_bits: int) -> str:
    return hash_bits("out-of-band-check-fixed", seed, n_bits=check_bits)


def oob_expected_check(pass_index: int, data: str, check_bits: int) -> str:
    return hash_bits("out-of-band-check-expected", pass_index, data, n_bits=check_bits)


def xor_bits(left: str, right: str) -> str:
    return "".join("1" if a != b else "0" for a, b in zip(left, right))


@lru_cache(maxsize=4096)
def oob_check_book(
    mode: str,
    pass_index: int,
    seed_bits: int,
    data_bits: int,
    check_bits: int,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        data = oob_check_payload(pass_index, seed, data_bits)
        if mode == "fixed-filter":
            if oob_fixed_check(seed, check_bits) != oob_expected_check(pass_index, data, check_bits):
                continue
        book.setdefault(data, seed)
    return book


@dataclass(frozen=True)
class OutOfBandCheckStat:
    mode: str
    check_bits: int
    chunks: int
    hits: int
    after_bits: int
    tight_bits: float
    tight_with_ambiguity: float
    wrong_q: float


@dataclass(frozen=True)
class OutOfBandCheckEncoded:
    mode: str
    pass_index: int
    chunks: int
    hits: tuple[bool, ...]
    seeds: tuple[int, ...]
    syndromes: tuple[str, ...]
    literals: str
    check_bits: int


def oob_check_wrong_survival(
    mode: str,
    true_pass: int,
    wrong_pass: int,
    seed: int,
    syndrome: str,
    data_bits: int,
    check_bits: int,
) -> bool:
    if mode == "self-consistent":
        return True
    data = oob_check_payload(wrong_pass, seed, data_bits)
    expected = oob_expected_check(wrong_pass, data, check_bits)
    if mode == "fixed-filter":
        return oob_fixed_check(seed, check_bits) == expected
    if mode == "syndrome-validated":
        repaired = xor_bits(oob_fixed_check(seed, check_bits), syndrome)
        return repaired == expected
    raise ValueError(f"unknown out-of-band check mode {mode!r}")


def encode_oob_check_layer(
    bits: str,
    mode: str,
    pass_index: int,
    seed_bits: int,
    data_bits: int,
    check_bits: int,
    pass_window: int,
) -> tuple[OutOfBandCheckEncoded, OutOfBandCheckStat]:
    chunks = len(bits) // data_bits
    tail = bits[chunks * data_bits:]
    hits: list[bool] = []
    seeds: list[int] = []
    syndromes: list[str] = []
    literals: list[str] = []
    out_bits = 0
    wrong_trials = 0
    wrong_survivors = 0
    book = oob_check_book(mode, pass_index, seed_bits, data_bits, check_bits)
    for chunk_index in range(chunks):
        chunk = bits[chunk_index * data_bits:(chunk_index + 1) * data_bits]
        seed = book.get(chunk)
        if seed is None:
            hits.append(False)
            literals.append(chunk)
            out_bits += 1 + data_bits
            continue
        hits.append(True)
        seeds.append(seed)
        syndrome = ""
        if mode == "syndrome-validated":
            syndrome = xor_bits(
                oob_fixed_check(seed, check_bits),
                oob_expected_check(pass_index, chunk, check_bits),
            )
            syndromes.append(syndrome)
        out_bits += 1 + seed_bits + len(syndrome)
        for delta in range(1, min(pass_window, 64)):
            wrong_trials += 1
            wrong_survivors += int(
                oob_check_wrong_survival(
                    mode,
                    pass_index,
                    pass_index + delta,
                    seed,
                    syndrome,
                    data_bits,
                    check_bits,
                )
            )
    out_bits += len(tail)
    hit_count = len(seeds)
    wrong_q = (wrong_survivors / wrong_trials) if wrong_trials else (
        1.0 if mode == "self-consistent" else 2.0 ** (-check_bits)
    )
    ambiguity_per_hit = log2(1 + (pass_window - 1) * max(wrong_q, 1e-12))
    bitmap_bits = log2_choose(chunks, hit_count)
    count_bits = count_class_bits(chunks + 1)
    syndrome_bits = hit_count * check_bits if mode == "syndrome-validated" else 0
    tight_bits = (
        (chunks - hit_count) * data_bits
        + hit_count * seed_bits
        + syndrome_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    tight_with_ambiguity = tight_bits + hit_count * ambiguity_per_hit
    return (
        OutOfBandCheckEncoded(
            mode,
            pass_index,
            chunks,
            tuple(hits),
            tuple(seeds),
            tuple(syndromes),
            "".join(literals),
            check_bits,
        ),
        OutOfBandCheckStat(
            mode,
            check_bits,
            chunks,
            hit_count,
            out_bits,
            tight_bits,
            tight_with_ambiguity,
            wrong_q,
        ),
    )


def decode_oob_check_layer(
    encoded: OutOfBandCheckEncoded,
    seed_bits: int,
    data_bits: int,
) -> str:
    out: list[str] = []
    seed_index = 0
    syndrome_index = 0
    literal_index = 0
    for hit in encoded.hits:
        if hit:
            seed = encoded.seeds[seed_index]
            seed_index += 1
            data = oob_check_payload(encoded.pass_index, seed, data_bits)
            if encoded.mode == "fixed-filter":
                if oob_fixed_check(seed, encoded.check_bits) != oob_expected_check(
                    encoded.pass_index, data, encoded.check_bits,
                ):
                    raise ValueError("out-of-band fixed check failed")
            elif encoded.mode == "syndrome-validated":
                syndrome = encoded.syndromes[syndrome_index]
                syndrome_index += 1
                repaired = xor_bits(oob_fixed_check(seed, encoded.check_bits), syndrome)
                if repaired != oob_expected_check(encoded.pass_index, data, encoded.check_bits):
                    raise ValueError("out-of-band syndrome check failed")
            out.append(data)
        else:
            chunk = encoded.literals[literal_index:literal_index + data_bits]
            if len(chunk) != data_bits:
                raise ValueError("out-of-band literal stream exhausted")
            literal_index += data_bits
            out.append(chunk)
    if seed_index != len(encoded.seeds):
        raise ValueError("unused out-of-band seeds")
    if syndrome_index != len(encoded.syndromes):
        raise ValueError("unused out-of-band syndromes")
    if literal_index != len(encoded.literals):
        raise ValueError("unused out-of-band literals")
    return "".join(out)


def out_of_band_check_trilemma_demo(
    trials: int = 80,
    chunks: int = 192,
    data_bits: int = 14,
    seed_bits: int = 10,
    pass_window: int = 64,
) -> None:
    print("== family 3h: out-of-band check-bit trilemma ==")
    print("Check bits are generated inside the record but are not decoded")
    print("payload. Self-consistent checks preserve hit supply but reject no")
    print("wrong passes. Fixed checks reject wrong passes but thin the true seed")
    print("book. Syndrome-validated checks preserve arbitrary payload reach but")
    print("store the check repair bits in the record.")
    print()
    rng = Random(313131)
    print(f"toy grammar: data={data_bits} seed={seed_bits} chunks={chunks} "
          f"trials={trials} pass_window={pass_window}")
    print(f"{'chk':>4} {'mode':>20} {'hit/ch':>8} {'wrong q':>9} "
          f"{'amb/hit':>8} {'visible':>9} {'tight':>9} "
          f"{'tight+amb':>10} {'closed':>9}")
    for check_bits in [0, 2, 4, 6, 8]:
        for mode in ["self-consistent", "fixed-filter", "syndrome-validated"]:
            stats: list[OutOfBandCheckStat] = []
            for trial in range(trials):
                bits = format(rng.getrandbits(chunks * data_bits), f"0{chunks * data_bits}b")
                encoded, stat = encode_oob_check_layer(
                    bits,
                    mode,
                    pass_index=1,
                    seed_bits=seed_bits,
                    data_bits=data_bits,
                    check_bits=check_bits,
                    pass_window=pass_window,
                )
                assert decode_oob_check_layer(encoded, seed_bits, data_bits) == bits
                stats.append(stat)
            hit_rate = mean(stat.hits for stat in stats) / chunks
            wrong_q = mean(stat.wrong_q for stat in stats)
            amb = log2(1 + (pass_window - 1) * max(wrong_q, 1e-12))
            visible_net = mean((chunks * data_bits) - stat.after_bits for stat in stats)
            tight_net = mean((chunks * data_bits) - stat.tight_bits for stat in stats)
            tight_amb_net = mean((chunks * data_bits) - stat.tight_with_ambiguity for stat in stats)
            if mode == "fixed-filter":
                p = min(1.0, 2.0 ** (seed_bits - data_bits - check_bits))
                record_bits = seed_bits
                q = 2.0 ** (-check_bits)
            elif mode == "syndrome-validated":
                p = min(1.0, 2.0 ** (seed_bits - data_bits))
                record_bits = seed_bits + check_bits
                q = 2.0 ** (-check_bits)
            else:
                p = min(1.0, 2.0 ** (seed_bits - data_bits))
                record_bits = seed_bits
                q = 1.0
            closed_amb = log2(1 + (pass_window - 1) * q)
            closed = p * (data_bits - record_bits - closed_amb) - binary_entropy(p)
            print(f"{check_bits:4d} {mode:>20} {hit_rate:8.4f} {wrong_q:9.5f} "
                  f"{amb:8.3f} {visible_net:9.3f} {tight_net:9.3f} "
                  f"{tight_amb_net:10.3f} {closed:9.3f}")
        print()
    print("Paid check+ambiguity lower bound per hit:")
    print(f"{'chk':>4} {'chk+log(1+(P-1)2^-chk)':>28} {'log2(P)':>9}")
    for check_bits in [0, 2, 4, 6, 8, 10, 12]:
        paid = check_bits + log2(1 + (pass_window - 1) * (2.0 ** -check_bits))
        print(f"{check_bits:4d} {paid:28.3f} {log2(pass_window):9.3f}")
    print()
    print("Reading: out-of-band checks are useful for finite wrong-pass pruning")
    print("only when their bits are either paid as a syndrome or paid as seed")
    print("supply loss. The combined check-plus-ambiguity bill is never below")
    print("the pass label in this independent model; it just moves the channel.")
    print()


GUARDED_DATA_BITS = 4
GUARDED_SEED_BITS = 8
GUARDED_PASSES = 1_000_000


@dataclass(frozen=True)
class GuardedBundleLayerStat:
    mode: str
    arity: int
    guard_bits: int
    before_bits: int
    after_bits: int
    windows: int
    hits: int
    valid_targets: int
    record_bits: int
    tight_bits: float
    wrong_q: float
    ambiguity_bits: float


def guarded_item_check(data: str, pass_index: int, arity: int, child_index: int, guard_bits: int) -> str:
    if guard_bits == 0:
        return ""
    return hash_bits(
        "guarded-bundle-item-check",
        pass_index,
        arity,
        child_index,
        data,
        n_bits=guard_bits,
    )


def guarded_split_items(chunk: str, arity: int, guard_bits: int) -> tuple[tuple[str, str], ...]:
    item_bits = GUARDED_DATA_BITS + guard_bits
    if len(chunk) != arity * item_bits:
        raise ValueError("guarded chunk has wrong length")
    items: list[tuple[str, str]] = []
    for child_index in range(arity):
        start = child_index * item_bits
        data = chunk[start:start + GUARDED_DATA_BITS]
        guard = chunk[start + GUARDED_DATA_BITS:start + item_bits]
        items.append((data, guard))
    return tuple(items)


def guarded_is_valid(chunk: str, pass_index: int, arity: int, guard_bits: int) -> bool:
    for child_index, (data, guard) in enumerate(guarded_split_items(chunk, arity, guard_bits)):
        if guard != guarded_item_check(data, pass_index, arity, child_index, guard_bits):
            return False
    return True


def guarded_raw_filter_expand(pass_index: int, arity: int, guard_bits: int, seed: int) -> str:
    span_bits = arity * (GUARDED_DATA_BITS + guard_bits)
    return hash_bits("guarded-bundle-raw-filter", pass_index, arity, guard_bits, seed, n_bits=span_bits)


def guarded_data_expand(pass_index: int, arity: int, seed: int) -> str:
    return hash_bits("guarded-bundle-data", pass_index, arity, seed, n_bits=arity * GUARDED_DATA_BITS)


def guarded_constrained_expand(pass_index: int, arity: int, guard_bits: int, seed: int) -> str:
    data_stream = guarded_data_expand(pass_index, arity, seed)
    chunks: list[str] = []
    for child_index in range(arity):
        data = data_stream[child_index * GUARDED_DATA_BITS:(child_index + 1) * GUARDED_DATA_BITS]
        chunks.append(data + guarded_item_check(data, pass_index, arity, child_index, guard_bits))
    return "".join(chunks)


def guarded_syndrome_expand(
    pass_index: int,
    arity: int,
    guard_bits: int,
    seed: int,
    syndrome: str,
) -> str:
    data_stream = guarded_data_expand(pass_index, arity, seed)
    chunks: list[str] = []
    offset = 0
    for child_index in range(arity):
        data = data_stream[child_index * GUARDED_DATA_BITS:(child_index + 1) * GUARDED_DATA_BITS]
        expected = guarded_item_check(data, pass_index, arity, child_index, guard_bits)
        repair = syndrome[offset:offset + guard_bits]
        if len(repair) != guard_bits:
            raise ValueError("truncated guarded syndrome")
        guard = "".join("1" if a != b else "0" for a, b in zip(expected, repair))
        chunks.append(data + guard)
        offset += guard_bits
    return "".join(chunks)


@lru_cache(maxsize=4096)
def guarded_raw_filter_book(pass_index: int, arity: int, guard_bits: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << GUARDED_SEED_BITS):
        chunk = guarded_raw_filter_expand(pass_index, arity, guard_bits, seed)
        if guarded_is_valid(chunk, pass_index, arity, guard_bits):
            book.setdefault(chunk, seed)
    return book


@lru_cache(maxsize=4096)
def guarded_constrained_book(pass_index: int, arity: int, guard_bits: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << GUARDED_SEED_BITS):
        book.setdefault(guarded_constrained_expand(pass_index, arity, guard_bits, seed), seed)
    return book


@lru_cache(maxsize=4096)
def guarded_data_book(pass_index: int, arity: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << GUARDED_SEED_BITS):
        book.setdefault(guarded_data_expand(pass_index, arity, seed), seed)
    return book


def encode_guarded_bundle_layer(
    bits: str,
    mode: str,
    pass_index: int,
    arity: int,
    guard_bits: int,
) -> tuple[str, GuardedBundleLayerStat]:
    span_bits = arity * (GUARDED_DATA_BITS + guard_bits)
    windows = len(bits) // span_bits
    tail = bits[windows * span_bits:]
    out: list[str] = []
    hits = 0
    valid_targets = 0
    record_bits = 1 + GUARDED_SEED_BITS
    if mode == "syndrome":
        record_bits += arity * guard_bits
    raw_literal_bits = 0
    for window in range(windows):
        chunk = bits[window * span_bits:(window + 1) * span_bits]
        valid_targets += int(guarded_is_valid(chunk, pass_index, arity, guard_bits))
        if mode == "raw-filter":
            seed = guarded_raw_filter_book(pass_index, arity, guard_bits).get(chunk)
            if seed is not None:
                out.append("1" + format(seed, f"0{GUARDED_SEED_BITS}b"))
                hits += 1
                continue
        elif mode == "constrained":
            seed = guarded_constrained_book(pass_index, arity, guard_bits).get(chunk)
            if seed is not None:
                out.append("1" + format(seed, f"0{GUARDED_SEED_BITS}b"))
                hits += 1
                continue
        elif mode == "syndrome":
            data = "".join(data for data, _ in guarded_split_items(chunk, arity, guard_bits))
            seed = guarded_data_book(pass_index, arity).get(data)
            if seed is not None:
                expected_items = guarded_split_items(
                    guarded_constrained_expand(pass_index, arity, guard_bits, seed),
                    arity,
                    guard_bits,
                )
                target_items = guarded_split_items(chunk, arity, guard_bits)
                syndrome_bits: list[str] = []
                for (_, expected_guard), (_, target_guard) in zip(expected_items, target_items):
                    syndrome_bits.append(
                        "".join("1" if a != b else "0" for a, b in zip(expected_guard, target_guard))
                    )
                out.append("1" + format(seed, f"0{GUARDED_SEED_BITS}b") + "".join(syndrome_bits))
                hits += 1
                continue
        else:
            raise ValueError(f"unknown guarded bundle mode {mode!r}")
        out.append("0" + chunk)
        raw_literal_bits += span_bits

    if mode == "raw-filter":
        wrong_q = 2.0 ** (-(arity * guard_bits))
    elif mode in {"constrained", "syndrome"}:
        wrong_q = 1.0
    else:
        raise ValueError(f"unknown guarded bundle mode {mode!r}")
    ambiguity = log2(1.0 + (GUARDED_PASSES - 1) * wrong_q)
    tight_bits = (
        raw_literal_bits
        + hits * (record_bits - 1)
        + len(tail)
        + log2_choose(windows, hits)
        + ceil(log2(windows + 1))
    )
    return (
        "".join(out),
        GuardedBundleLayerStat(
            mode=mode,
            arity=arity,
            guard_bits=guard_bits,
            before_bits=len(bits),
            after_bits=sum(len(part) for part in out),
            windows=windows,
            hits=hits,
            valid_targets=valid_targets,
            record_bits=record_bits,
            tight_bits=tight_bits,
            wrong_q=wrong_q,
            ambiguity_bits=ambiguity,
        ),
    )


def decode_guarded_bundle_layer(
    encoded: str,
    stat: GuardedBundleLayerStat,
    pass_index: int,
) -> str:
    span_bits = stat.arity * (GUARDED_DATA_BITS + stat.guard_bits)
    offset = 0
    out: list[str] = []
    for _ in range(stat.windows):
        tag = encoded[offset]
        if tag == "0":
            end = offset + 1 + span_bits
            if end > len(encoded):
                raise ValueError("truncated guarded literal")
            out.append(encoded[offset + 1:end])
            offset = end
        elif tag == "1":
            end = offset + stat.record_bits
            if end > len(encoded):
                raise ValueError("truncated guarded record")
            seed = int(encoded[offset + 1:offset + 1 + GUARDED_SEED_BITS], 2)
            if stat.mode == "raw-filter":
                out.append(guarded_raw_filter_expand(pass_index, stat.arity, stat.guard_bits, seed))
            elif stat.mode == "constrained":
                out.append(guarded_constrained_expand(pass_index, stat.arity, stat.guard_bits, seed))
            elif stat.mode == "syndrome":
                syndrome = encoded[offset + 1 + GUARDED_SEED_BITS:end]
                out.append(guarded_syndrome_expand(pass_index, stat.arity, stat.guard_bits, seed, syndrome))
            else:
                raise ValueError(f"unknown guarded bundle mode {stat.mode!r}")
            offset = end
        else:
            raise ValueError(f"invalid guarded tag {tag!r}")
    out.append(encoded[offset:])
    decoded = "".join(out)
    if len(decoded) != stat.before_bits:
        raise ValueError("guarded decoded length mismatch")
    return decoded


def guarded_multi_arity_trilemma_demo(trials: int = 80, windows: int = 256) -> None:
    print("== family 3g: guarded multi-arity bundle trilemma ==")
    print("This mutation gives wrong-pass explosion the larger arities BBL")
    print("wants, but keeps the arbitrary-target accounting visible. Guard bits")
    print("may filter raw hash outputs, be baked into constrained outputs, or")
    print("be repaired by a stored syndrome.")
    print()
    rng = Random(737373)
    print(
        f"toy grammar: data={GUARDED_DATA_BITS} seed={GUARDED_SEED_BITS} "
        f"P={GUARDED_PASSES} windows={windows}"
    )
    print(f"{'mode':>12} {'a':>2} {'g':>2} {'valid%':>8} {'hit/w':>9} "
          f"{'wrong q':>9} {'ambig':>8} {'visible':>9} {'tight':>9} {'closed':>9}")
    for guard_bits in [0, 2, 4]:
        for arity in [2, 3, 4, 5]:
            span_bits = arity * (GUARDED_DATA_BITS + guard_bits)
            for mode in ["raw-filter", "constrained", "syndrome"]:
                stats: list[GuardedBundleLayerStat] = []
                for _ in range(trials):
                    bits = format(rng.getrandbits(windows * span_bits), f"0{windows * span_bits}b")
                    encoded, stat = encode_guarded_bundle_layer(bits, mode, 1, arity, guard_bits)
                    assert decode_guarded_bundle_layer(encoded, stat, 1) == bits
                    stats.append(stat)
                avg_valid = mean(stat.valid_targets / stat.windows if stat.windows else 0.0 for stat in stats)
                avg_hit = mean(stat.hits / stat.windows if stat.windows else 0.0 for stat in stats)
                avg_visible = mean(stat.before_bits - stat.after_bits for stat in stats)
                avg_tight = mean(stat.before_bits - stat.tight_bits for stat in stats)
                ambiguity = stats[0].ambiguity_bits
                if mode == "raw-filter":
                    closed_hit = 2.0 ** (GUARDED_SEED_BITS - span_bits - arity * guard_bits)
                    closed_record = GUARDED_SEED_BITS
                    closed_wrong = 2.0 ** (-(arity * guard_bits))
                elif mode == "constrained":
                    closed_hit = (2.0 ** (-(arity * guard_bits))) * min(
                        1.0, 2.0 ** (GUARDED_SEED_BITS - arity * GUARDED_DATA_BITS)
                    )
                    closed_record = GUARDED_SEED_BITS
                    closed_wrong = 1.0
                else:
                    closed_hit = min(1.0, 2.0 ** (GUARDED_SEED_BITS - arity * GUARDED_DATA_BITS))
                    closed_record = GUARDED_SEED_BITS + arity * guard_bits
                    closed_wrong = 1.0
                closed_ambiguity = log2(1.0 + (GUARDED_PASSES - 1) * closed_wrong)
                closed_gross = span_bits - closed_record
                closed_net = closed_hit * max(0.0, closed_gross - closed_ambiguity)
                print(f"{mode:>12} {arity:2d} {guard_bits:2d} {100.0 * avg_valid:8.3f} "
                      f"{avg_hit:9.5f} {stats[0].wrong_q:9.3e} {ambiguity:8.3f} "
                      f"{avg_visible:9.3f} {avg_tight:9.3f} {closed_net:9.3e}")
            print()
        print()
    print("Reading: larger guarded bundles can make wrong-pass survival tiny")
    print("only in the raw-filter ledger, where arbitrary targets must already")
    print("carry all guard bits and true-hit supply collapses. Constraining the")
    print("expander or storing syndromes restores reachability but makes wrong")
    print("passes structurally plausible or pays the guard bits in each record.")
    print()


def derived_validity_sweep() -> None:
    print("== family 3b: derived validity from existing seed classes ==")
    print("Here validity is not stored as extra residue bits. Instead, the")
    print("decoder-visible seed class must match a public context residue.")
    print("That lowers wrong-pass survival, but it removes the same fraction")
    print("of eligible seeds from arbitrary search.")
    print()
    base_b = 8
    seed_bits = 13
    marker_bits = 2
    passes = 1_000_000
    print(f"{'arity':>5} {'class':>5} {'span':>6} {'gross':>7} {'hit p':>11} "
          f"{'ambig':>8} {'E net/window':>13}")
    best: tuple[float, int, int] | None = None
    for arity in range(2, 6):
        span = arity * base_b
        record = marker_bits + seed_bits
        gross = span - record
        for class_bits in range(0, 13, 2):
            usable_seeds = max(1, 1 << max(seed_bits - class_bits, 0))
            hit_p = min(1.0, usable_seeds / (2 ** span))
            wrong_survival = 2 ** (-class_bits * arity)
            ambiguity = log2(1 + (passes - 1) * wrong_survival)
            net_per_window = hit_p * max(0.0, gross - ambiguity)
            if best is None or net_per_window > best[0]:
                best = (net_per_window, arity, class_bits)
            print(f"{arity:5d} {class_bits:5d} {span:6d} {gross:7d} "
                  f"{hit_p:11.3e} {ambiguity:8.3f} {net_per_window:13.3e}")
        print()
    assert best is not None
    print(f"best toy expected net/window={best[0]:.3e} at arity={best[1]} class={best[2]}")
    print()
    print("Reading: deriving the validity check from visible seed classes")
    print("avoids extra record bits, but the same information reappears as")
    print("match-supply loss. It is a useful pricing lens for checksum")
    print("residue, lane-constrained codewords, and neighbor-state classes.")
    print()


def nested_referee_node_count(arity: int, depth: int) -> int:
    if depth <= 0:
        return 0
    return (arity ** depth - 1) // (arity - 1)


def nested_referee_check(
    arity: int,
    depth: int,
    path: tuple[int, ...],
    body: str,
    check_bits: int,
) -> str:
    return hash_bits("nested-referee-check", arity, depth, path, body, n_bits=check_bits)


def nested_referee_encode_node(
    payload: str,
    index: int,
    arity: int,
    depth: int,
    leaf_bits: int,
    check_bits: int,
    path: tuple[int, ...],
) -> tuple[str, int]:
    if depth == 0:
        end = index + leaf_bits
        leaf = payload[index:end]
        if len(leaf) != leaf_bits:
            raise ValueError("nested referee payload exhausted")
        return leaf, end
    children: list[str] = []
    cursor = index
    for child in range(arity):
        child_stream, cursor = nested_referee_encode_node(
            payload, cursor, arity, depth - 1, leaf_bits, check_bits, path + (child,),
        )
        children.append(child_stream)
    body = "".join(children)
    return body + nested_referee_check(arity, depth, path, body, check_bits), cursor


def nested_referee_encode(
    payload: str,
    arity: int,
    depth: int,
    leaf_bits: int,
    check_bits: int,
) -> str:
    stream, cursor = nested_referee_encode_node(payload, 0, arity, depth, leaf_bits, check_bits, ())
    if cursor != len(payload):
        raise ValueError("unused nested referee payload bits")
    return stream


def nested_referee_decode_node(
    stream: str,
    index: int,
    arity: int,
    depth: int,
    leaf_bits: int,
    check_bits: int,
    path: tuple[int, ...],
) -> tuple[str, int]:
    if depth == 0:
        end = index + leaf_bits
        leaf = stream[index:end]
        if len(leaf) != leaf_bits:
            raise ValueError("nested referee leaf exhausted")
        return leaf, end
    body_start = index
    payload_parts: list[str] = []
    cursor = index
    for child in range(arity):
        child_payload, cursor = nested_referee_decode_node(
            stream, cursor, arity, depth - 1, leaf_bits, check_bits, path + (child,),
        )
        payload_parts.append(child_payload)
    body = stream[body_start:cursor]
    end = cursor + check_bits
    check = stream[cursor:end]
    if len(check) != check_bits:
        raise ValueError("nested referee check exhausted")
    if check != nested_referee_check(arity, depth, path, body, check_bits):
        raise ValueError("nested referee check mismatch")
    return "".join(payload_parts), end


def nested_referee_decode(
    stream: str,
    arity: int,
    depth: int,
    leaf_bits: int,
    check_bits: int,
) -> str:
    payload, cursor = nested_referee_decode_node(stream, 0, arity, depth, leaf_bits, check_bits, ())
    if cursor != len(stream):
        raise ValueError("unused nested referee stream bits")
    return payload


@dataclass(frozen=True)
class NestedRefereeLedgerRow:
    arity: int
    depth: int
    check_bits: int
    payload_bits: int
    referee_nodes: int
    check_total: int
    ambiguity_bits: float
    fantasy_net: float
    stored_net: float
    derived_net: float


def nested_referee_ledger_rows() -> list[NestedRefereeLedgerRow]:
    leaf_bits = 8
    seed_bits = 18
    record_bits = seed_bits + 2
    passes = 1_000_000
    rows: list[NestedRefereeLedgerRow] = []
    for arity in range(2, 6):
        for depth in range(1, 5):
            payload_bits = (arity ** depth) * leaf_bits
            gross_original = payload_bits - record_bits
            if gross_original <= 0:
                continue
            nodes = nested_referee_node_count(arity, depth)
            for check_bits in [0, 1, 2, 4, 6, 8]:
                check_total = check_bits * nodes
                wrong_survival = 2 ** (-check_total) if check_total else 1.0
                ambiguity = log2(1 + (passes - 1) * wrong_survival)
                margin = max(0.0, gross_original - ambiguity)
                fantasy_hit = min(1.0, 2 ** (seed_bits - payload_bits))
                charged_hit = min(1.0, 2 ** (seed_bits - payload_bits - check_total))
                rows.append(NestedRefereeLedgerRow(
                    arity,
                    depth,
                    check_bits,
                    payload_bits,
                    nodes,
                    check_total,
                    ambiguity,
                    fantasy_hit * margin,
                    charged_hit * margin,
                    charged_hit * margin,
                ))
    return rows


def nested_referee_wrong_pass_demo(trials: int = 5_000) -> None:
    print("== family 3c: nested referee wrong-pass grammar ==")
    print("Recursive referee checks make wrong openings fail at internal nodes.")
    print("The exact wrapper below round-trips arbitrary payload bits and then")
    print("tests random wrong streams against the same public grammar. The")
    print("ledger separates a fantasy free-validity row from charged rows where")
    print("the referee information is stored in the target or derived from seed")
    print("classes.")
    print()
    arity = 3
    depth = 2
    leaf_bits = 4
    check_bits = 2
    leaves = arity ** depth
    nodes = nested_referee_node_count(arity, depth)
    payload_bits = leaves * leaf_bits
    stream_bits = payload_bits + nodes * check_bits
    rng = Random(737373)
    round_trips = 0
    wrong_survivors = 0
    for _ in range(trials):
        payload = format(rng.getrandbits(payload_bits), f"0{payload_bits}b")
        stream = nested_referee_encode(payload, arity, depth, leaf_bits, check_bits)
        if nested_referee_decode(stream, arity, depth, leaf_bits, check_bits) == payload:
            round_trips += 1
        wrong = format(rng.getrandbits(stream_bits), f"0{stream_bits}b")
        try:
            nested_referee_decode(wrong, arity, depth, leaf_bits, check_bits)
            wrong_survivors += 1
        except ValueError:
            pass
    expected_survivors = trials * (2 ** (-(nodes * check_bits)))
    print(f"exact wrapper: arity={arity} depth={depth} leaves={leaves} "
          f"payload={payload_bits} check_total={nodes * check_bits} stream={stream_bits}")
    print(f"round_trips={round_trips}/{trials}")
    print(f"wrong_survivors={wrong_survivors}/{trials} "
          f"expected~{expected_survivors:.2f}")
    print()
    rows = nested_referee_ledger_rows()
    print("Top rows if referee validity were free for true targets:")
    print(f"{'a':>2} {'d':>2} {'chk':>3} {'payload':>7} {'nodes':>5} "
          f"{'ambig':>8} {'fantasy':>11} {'stored':>11} {'derived':>11}")
    for row in sorted(rows, key=lambda item: item.fantasy_net, reverse=True)[:8]:
        print(f"{row.arity:2d} {row.depth:2d} {row.check_bits:3d} "
              f"{row.payload_bits:7d} {row.referee_nodes:5d} "
              f"{row.ambiguity_bits:8.3f} {row.fantasy_net:11.3e} "
              f"{row.stored_net:11.3e} {row.derived_net:11.3e}")
    print()
    print("Best charged rows after storing checks or deriving them from seed class:")
    print(f"{'a':>2} {'d':>2} {'chk':>3} {'payload':>7} {'nodes':>5} "
          f"{'ambig':>8} {'charged':>11}")
    for row in sorted(rows, key=lambda item: max(item.stored_net, item.derived_net),
                      reverse=True)[:8]:
        print(f"{row.arity:2d} {row.depth:2d} {row.check_bits:3d} "
              f"{row.payload_bits:7d} {row.referee_nodes:5d} "
              f"{row.ambiguity_bits:8.3f} "
              f"{max(row.stored_net, row.derived_net):11.3e}")
    print()
    print("Reading: nested checks do make wrong-pass parses die quickly. The")
    print("moment the referee bits are paid, either as target/wrapper bits or")
    print("as seed-class restrictions, the nested advantage collapses. The best")
    print("charged rows are shallow; deeper nesting mainly creates a larger")
    print("validity channel to pay.")
    print()


def output_nonce(bits: str, nonce_bits: int) -> int:
    if nonce_bits == 0:
        return 0
    digest = hash_bits("nonce-of-output", bits, n_bits=nonce_bits)
    return int(digest, 2)


def self_consistent_output(seed: int, nonce: int, span_bits_count: int) -> str:
    return hash_bits("self-consistent-output-nonce", seed, nonce, n_bits=span_bits_count)


def self_consistent_candidates(seed: int, nonce_bits: int, span_bits_count: int) -> set[str]:
    out: set[str] = set()
    for nonce in range(1 << nonce_bits):
        bits = self_consistent_output(seed, nonce, span_bits_count)
        if output_nonce(bits, nonce_bits) == nonce:
            out.add(bits)
    return out


def self_consistent_book(nonce_bits: int, seed_bits: int, span_bits_count: int) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        for bits in self_consistent_candidates(seed, nonce_bits, span_bits_count):
            book.setdefault(bits, seed)
    return book


def self_consistent_output_nonce_demo() -> None:
    print("== family 1d: self-consistent output-derived nonce ==")
    print("The nonce is not stored. It is computed from the expanded output,")
    print("and the decoder tries nonce values, keeping only outputs whose")
    print("own nonce agrees. This is stateless, but each target determines")
    print("one nonce, so supply should not multiply by the nonce count.")
    print()
    span_bits_count = 16
    seed_bits = 10
    marker_bits = 2
    rng = Random(1357)
    print(f"{'nonce':>6} {'book':>6} {'record':>7} {'gross':>7} {'hit p':>10} "
          f"{'hits':>10} {'mean cand':>10} {'E net/window':>13}")
    for nonce_bits in range(0, 7):
        book = self_consistent_book(nonce_bits, seed_bits, span_bits_count)
        record_bits = marker_bits + seed_bits
        gross = span_bits_count - record_bits
        hit_p = len(book) / (1 << span_bits_count)
        hits = 0
        candidate_counts: list[int] = []
        trials = 256
        for _ in range(trials):
            target = format(rng.getrandbits(span_bits_count), f"0{span_bits_count}b")
            seed = book.get(target)
            if seed is None:
                continue
            candidates = self_consistent_candidates(seed, nonce_bits, span_bits_count)
            assert target in candidates
            hits += 1
            candidate_counts.append(len(candidates))
        mean_candidates = mean(candidate_counts) if candidate_counts else 0.0
        ambiguity = log2(mean_candidates) if mean_candidates > 0 else 0.0
        net = hit_p * max(0.0, gross - ambiguity)
        print(f"{nonce_bits:6d} {len(book):6d} {record_bits:7d} {gross:7d} "
              f"{hit_p:10.5f} {hits:4d}/{trials:<5d} {mean_candidates:10.3f} {net:13.5f}")
    print()
    print("Reading: output-derived nonces are decodable without a stored")
    print("nonce, but they do not create extra arbitrary target coverage.")
    print("They select roughly one self-consistent output per seed, plus a")
    print("small ambiguity tail, so freshness is paid as compute rather")
    print("than new match supply.")
    print()


def log2_factorial(n: int) -> float:
    return lgamma(n + 1) / log(2)


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k))


def compositions(total: int, parts: int) -> Iterable[tuple[int, ...]]:
    if parts == 1:
        yield (total,)
        return
    for head in range(total + 1):
        for tail in compositions(total - head, parts - 1):
            yield (head, *tail)


def histogram_entropy_and_assignment(records: int, passes: int) -> tuple[float, float]:
    total_label_bits = records * log2(passes)
    hist_entropy = 0.0
    expected_assignment = 0.0
    log_fact_records = log2_factorial(records)
    for counts in compositions(records, passes):
        log_multinomial = log_fact_records - sum(log2_factorial(count) for count in counts)
        log_prob = log_multinomial - total_label_bits
        probability = 2 ** log_prob
        hist_entropy -= probability * log_prob
        expected_assignment += probability * log_multinomial
    return hist_entropy, expected_assignment


# ---------------------------------------------------------------------------
# Family 4: biology-inspired public interpreters.


DEVELOPMENTAL_CELL_BITS = 24
DEVELOPMENTAL_RULE_BITS = 8
DEVELOPMENTAL_INIT_BITS = 8
DEVELOPMENTAL_STEPS = 12


def developmental_expand(
    program: int,
    cells: int = DEVELOPMENTAL_CELL_BITS,
    steps: int = DEVELOPMENTAL_STEPS,
    init_bits: int = DEVELOPMENTAL_INIT_BITS,
) -> str:
    """Tiny public "developmental" interpreter: elementary CA from a genome."""
    init_mask = (1 << init_bits) - 1
    rule = program >> init_bits
    init = program & init_mask
    zygote = hash_bits("developmental-zygote", rule, init, cells, n_bits=cells)
    state = [int(bit) for bit in zygote]
    for _ in range(steps):
        next_state: list[int] = []
        for index in range(cells):
            left = state[(index - 1) % cells]
            center = state[index]
            right = state[(index + 1) % cells]
            neighborhood = (left << 2) | (center << 1) | right
            next_state.append((rule >> neighborhood) & 1)
        state = next_state
    return "".join(str(bit) for bit in state)


@lru_cache(maxsize=16)
def developmental_book(
    cells: int = DEVELOPMENTAL_CELL_BITS,
    steps: int = DEVELOPMENTAL_STEPS,
    rule_bits: int = DEVELOPMENTAL_RULE_BITS,
    init_bits: int = DEVELOPMENTAL_INIT_BITS,
) -> dict[str, int]:
    book: dict[str, int] = {}
    program_bits = rule_bits + init_bits
    for program in range(1 << program_bits):
        book.setdefault(developmental_expand(program, cells, steps, init_bits), program)
    return book


@dataclass
class DevelopmentalEncoded:
    original_bits: str
    final_bits: str
    cells: int
    steps: int
    program_bits: int
    chunks: int
    tail: str
    bitmap: tuple[int, ...]
    programs: tuple[int, ...]
    literals: tuple[str, ...]
    visible_bits: str
    tight_bits: float
    all_generated_bits: float | None


def encode_developmental_interpreter(
    bits: str,
    cells: int = DEVELOPMENTAL_CELL_BITS,
    steps: int = DEVELOPMENTAL_STEPS,
    rule_bits: int = DEVELOPMENTAL_RULE_BITS,
    init_bits: int = DEVELOPMENTAL_INIT_BITS,
) -> DevelopmentalEncoded:
    book = developmental_book(cells, steps, rule_bits, init_bits)
    program_bits = rule_bits + init_bits
    chunks = len(bits) // cells
    tail = bits[chunks * cells:]
    bitmap: list[int] = []
    programs: list[int] = []
    literals: list[str] = []
    visible_parts: list[str] = []
    for chunk_index in range(chunks):
        chunk = bits[chunk_index * cells:(chunk_index + 1) * cells]
        program = book.get(chunk)
        if program is None:
            bitmap.append(0)
            literals.append(chunk)
            visible_parts.append("0" + chunk)
        else:
            bitmap.append(1)
            programs.append(program)
            visible_parts.append("1" + fixed_width_bits(program, program_bits))
    visible_bits = "".join(visible_parts) + tail
    hits = sum(bitmap)
    tight_bits = (
        count_class_bits(chunks + 1)
        + log2_choose(chunks, hits)
        + hits * program_bits
        + (chunks - hits) * cells
        + len(tail)
    )
    all_generated_bits = None
    if hits == chunks:
        all_generated_bits = chunks * program_bits + len(tail)
    return DevelopmentalEncoded(
        original_bits=bits,
        final_bits=visible_bits,
        cells=cells,
        steps=steps,
        program_bits=program_bits,
        chunks=chunks,
        tail=tail,
        bitmap=tuple(bitmap),
        programs=tuple(programs),
        literals=tuple(literals),
        visible_bits=visible_bits,
        tight_bits=tight_bits,
        all_generated_bits=all_generated_bits,
    )


def decode_developmental_interpreter(encoded: DevelopmentalEncoded) -> str:
    program_index = 0
    literal_index = 0
    chunks: list[str] = []
    for flag in encoded.bitmap:
        if flag:
            program = encoded.programs[program_index]
            program_index += 1
            chunks.append(developmental_expand(program, encoded.cells, encoded.steps))
        else:
            chunks.append(encoded.literals[literal_index])
            literal_index += 1
    if program_index != len(encoded.programs) or literal_index != len(encoded.literals):
        raise ValueError("developmental stream has unused payload")
    return "".join(chunks) + encoded.tail


def developmental_generated_bits(
    rng: Random,
    chunks: int,
    rule_bits: int = DEVELOPMENTAL_RULE_BITS,
    init_bits: int = DEVELOPMENTAL_INIT_BITS,
) -> str:
    program_bits = rule_bits + init_bits
    return "".join(
        developmental_expand(rng.randrange(1 << program_bits))
        for _ in range(chunks)
    )


def biological_developmental_interpreter_demo(
    trials: int = 120,
    chunks: int = 128,
    cells: int = DEVELOPMENTAL_CELL_BITS,
    steps: int = DEVELOPMENTAL_STEPS,
    rule_bits: int = DEVELOPMENTAL_RULE_BITS,
    init_bits: int = DEVELOPMENTAL_INIT_BITS,
) -> None:
    print("== family 4a: biological developmental interpreter ==")
    print("Biology suggests a different missing piece: a compact genome is")
    print("interpreted by a large public machine (cellular chemistry, folding")
    print("physics, regulatory state). This toy replaces a blind hash universe")
    print("with a public developmental interpreter and prices what changes.")
    print()
    book = developmental_book(cells, steps, rule_bits, init_bits)
    program_bits = rule_bits + init_bits
    output_space_bits = cells
    coverage = len(book) / (1 << output_space_bits)
    rng = Random(424242)
    random_rows: list[DevelopmentalEncoded] = []
    shaped_rows: list[DevelopmentalEncoded] = []
    for _ in range(trials):
        random_bits = fixed_width_bits(rng.getrandbits(chunks * cells), chunks * cells)
        random_encoded = encode_developmental_interpreter(
            random_bits, cells, steps, rule_bits, init_bits
        )
        assert decode_developmental_interpreter(random_encoded) == random_bits
        random_rows.append(random_encoded)
        shaped_bits = developmental_generated_bits(rng, chunks, rule_bits, init_bits)
        shaped_encoded = encode_developmental_interpreter(
            shaped_bits, cells, steps, rule_bits, init_bits
        )
        assert decode_developmental_interpreter(shaped_encoded) == shaped_bits
        shaped_rows.append(shaped_encoded)

    def summarize(rows: list[DevelopmentalEncoded]) -> tuple[float, float, float, float | None]:
        raw_bits = mean(len(row.original_bits) for row in rows)
        hit_rate = mean(sum(row.bitmap) / row.chunks for row in rows)
        visible_net = mean(len(row.original_bits) - len(row.visible_bits) for row in rows)
        tight_net = mean(len(row.original_bits) - row.tight_bits for row in rows)
        all_generated = [
            len(row.original_bits) - row.all_generated_bits
            for row in rows
            if row.all_generated_bits is not None
        ]
        all_generated_net = mean(all_generated) if len(all_generated) == len(rows) else None
        return raw_bits, hit_rate, visible_net, tight_net, all_generated_net

    print(f"toy interpreter: rule={rule_bits} bits init={init_bits} bits "
          f"program={program_bits} bits cells={cells} steps={steps}")
    print(f"unique reachable outputs={len(book)} of 2^{output_space_bits} "
          f"(coverage={coverage:.6f}, max={2 ** (program_bits - output_space_bits):.6f})")
    print()
    print(f"{'source':>10} {'raw':>8} {'hit/ch':>8} {'visible':>10} "
          f"{'tight':>10} {'all-gen':>10}")
    for label, rows in [("generated", shaped_rows), ("uniform", random_rows)]:
        raw_bits, hit_rate, visible_net, tight_net, all_generated_net = summarize(rows)
        all_generated_text = (
            f"{all_generated_net:10.3f}" if all_generated_net is not None else f"{'n/a':>10}"
        )
        print(f"{label:>10} {raw_bits:8.1f} {hit_rate:8.5f} "
              f"{visible_net:10.3f} {tight_net:10.3f} {all_generated_text}")
    print()
    print("Interpreter/config accounting:")
    print(f"- Generated file mode saves {cells - program_bits} bits/chunk before")
    print("  fixed/root metadata because open-vs-carry is an invariant.")
    print("- Mixed arbitrary mode must store a map; sparse hits do not pay for it.")
    for interpreter_bits in [0, 256, 4096, 1_048_576]:
        if interpreter_bits == 0:
            print("- Public inherited interpreter: 0 extra bits.")
            continue
        chunk_win = cells - program_bits
        break_even = ceil(interpreter_bits / chunk_win) if chunk_win > 0 else float("inf")
        print(f"- Private interpreter/config {interpreter_bits} bits needs "
              f"{break_even} generated chunks just to amortize it.")
    print()
    print("Scale gate:")
    for phenotype_bits in [24, 64, 128, 1024]:
        reachable_fraction_log = min(0, program_bits - phenotype_bits)
        print(f"- {program_bits}-bit genome to {phenotype_bits}-bit phenotype: "
              f"reachable fraction <= 2^{reachable_fraction_log}.")
    print()
    print("Reading: this is the biology-shaped positive path. It is stateless")
    print("and compressive when the target is already in the interpreter's")
    print("reachable language, exactly like a genome unfolding through public")
    print("cellular machinery. It does not make uniform arbitrary targets dense;")
    print("for those, the interpreter is a source-family/preset channel that")
    print("must be public, inherited, or paid and amortized.")
    print()


CASCADE_ROOT_BITS = 12
CASCADE_LEAF_BITS = 8


@lru_cache(maxsize=131072)
def recursive_cascade_expand(
    root: int,
    depth: int,
    path: int = 1,
    root_bits: int = CASCADE_ROOT_BITS,
    leaf_bits: int = CASCADE_LEAF_BITS,
) -> str:
    if depth == 0:
        return hash_bits("bio-cascade-leaf", root, path, n_bits=leaf_bits)
    child_bits = hash_bits(
        "bio-cascade-children",
        root,
        depth,
        path,
        n_bits=2 * root_bits,
    )
    left = int(child_bits[:root_bits], 2)
    right = int(child_bits[root_bits:], 2)
    return (
        recursive_cascade_expand(left, depth - 1, path * 2, root_bits, leaf_bits)
        + recursive_cascade_expand(right, depth - 1, path * 2 + 1, root_bits, leaf_bits)
    )


@lru_cache(maxsize=32)
def recursive_cascade_book(
    depth: int,
    root_bits: int = CASCADE_ROOT_BITS,
    leaf_bits: int = CASCADE_LEAF_BITS,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for root in range(1 << root_bits):
        book.setdefault(recursive_cascade_expand(root, depth, 1, root_bits, leaf_bits), root)
    return book


@dataclass
class RecursiveCascadeEncoded:
    original_bits: str
    final_bits: str
    depth: int
    root_bits: int
    leaf_bits: int
    phenotype_bits: int
    chunks: int
    tail: str
    bitmap: tuple[int, ...]
    roots: tuple[int, ...]
    literals: tuple[str, ...]
    visible_bits: str
    tight_bits: float
    all_generated_bits: float | None


def encode_recursive_cascade(
    bits: str,
    depth: int,
    root_bits: int = CASCADE_ROOT_BITS,
    leaf_bits: int = CASCADE_LEAF_BITS,
) -> RecursiveCascadeEncoded:
    phenotype_bits = (1 << depth) * leaf_bits
    book = recursive_cascade_book(depth, root_bits, leaf_bits)
    chunks = len(bits) // phenotype_bits
    tail = bits[chunks * phenotype_bits:]
    bitmap: list[int] = []
    roots: list[int] = []
    literals: list[str] = []
    visible_parts: list[str] = []
    for chunk_index in range(chunks):
        chunk = bits[chunk_index * phenotype_bits:(chunk_index + 1) * phenotype_bits]
        root = book.get(chunk)
        if root is None:
            bitmap.append(0)
            literals.append(chunk)
            visible_parts.append("0" + chunk)
        else:
            bitmap.append(1)
            roots.append(root)
            visible_parts.append("1" + fixed_width_bits(root, root_bits))
    visible_bits = "".join(visible_parts) + tail
    hits = sum(bitmap)
    tight_bits = (
        count_class_bits(chunks + 1)
        + log2_choose(chunks, hits)
        + hits * root_bits
        + (chunks - hits) * phenotype_bits
        + len(tail)
    )
    all_generated_bits = None
    if hits == chunks:
        all_generated_bits = chunks * root_bits + len(tail)
    return RecursiveCascadeEncoded(
        original_bits=bits,
        final_bits=visible_bits,
        depth=depth,
        root_bits=root_bits,
        leaf_bits=leaf_bits,
        phenotype_bits=phenotype_bits,
        chunks=chunks,
        tail=tail,
        bitmap=tuple(bitmap),
        roots=tuple(roots),
        literals=tuple(literals),
        visible_bits=visible_bits,
        tight_bits=tight_bits,
        all_generated_bits=all_generated_bits,
    )


def decode_recursive_cascade(encoded: RecursiveCascadeEncoded) -> str:
    root_index = 0
    literal_index = 0
    chunks: list[str] = []
    for flag in encoded.bitmap:
        if flag:
            root = encoded.roots[root_index]
            root_index += 1
            chunks.append(
                recursive_cascade_expand(
                    root,
                    encoded.depth,
                    1,
                    encoded.root_bits,
                    encoded.leaf_bits,
                )
            )
        else:
            chunks.append(encoded.literals[literal_index])
            literal_index += 1
    if root_index != len(encoded.roots) or literal_index != len(encoded.literals):
        raise ValueError("recursive cascade stream has unused payload")
    return "".join(chunks) + encoded.tail


def recursive_cascade_generated_bits(
    rng: Random,
    chunks: int,
    depth: int,
    root_bits: int = CASCADE_ROOT_BITS,
    leaf_bits: int = CASCADE_LEAF_BITS,
) -> str:
    return "".join(
        recursive_cascade_expand(rng.randrange(1 << root_bits), depth, 1, root_bits, leaf_bits)
        for _ in range(chunks)
    )


def recursive_biological_cascade_demo(
    trials: int = 80,
    chunks: int = 64,
    test_depth: int = 4,
    root_bits: int = CASCADE_ROOT_BITS,
    leaf_bits: int = CASCADE_LEAF_BITS,
) -> None:
    print("== family 4b: recursive biological unfold cascade ==")
    print("A root seed emits child regulatory seeds; child seeds emit more")
    print("children; only leaves become phenotype bits. Depth/path are public")
    print("developmental coordinates, so the decoder needs no birth-pass state.")
    print()
    rng = Random(777331)
    print(f"root={root_bits} bits leaf={leaf_bits} bits chunks={chunks} "
          f"test_depth={test_depth}")
    print(f"{'depth':>5} {'leaves':>7} {'out/root':>9} {'unique':>7} "
          f"{'log2 cov':>9} {'save/root':>10}")
    for depth in [0, 1, 2, 3, 4, 5, 6]:
        phenotype_bits = (1 << depth) * leaf_bits
        book = recursive_cascade_book(depth, root_bits, leaf_bits)
        log_coverage = log2(len(book)) - phenotype_bits
        save_per_root = phenotype_bits - root_bits
        print(f"{depth:5d} {1 << depth:7d} {phenotype_bits:9d} "
              f"{len(book):7d} {log_coverage:9.3f} {save_per_root:10d}")
    print()

    phenotype_bits = (1 << test_depth) * leaf_bits
    random_rows: list[RecursiveCascadeEncoded] = []
    generated_rows: list[RecursiveCascadeEncoded] = []
    for _ in range(trials):
        random_bits = fixed_width_bits(rng.getrandbits(chunks * phenotype_bits),
                                       chunks * phenotype_bits)
        random_encoded = encode_recursive_cascade(
            random_bits, test_depth, root_bits, leaf_bits
        )
        assert decode_recursive_cascade(random_encoded) == random_bits
        random_rows.append(random_encoded)

        generated_bits = recursive_cascade_generated_bits(
            rng, chunks, test_depth, root_bits, leaf_bits
        )
        generated_encoded = encode_recursive_cascade(
            generated_bits, test_depth, root_bits, leaf_bits
        )
        assert decode_recursive_cascade(generated_encoded) == generated_bits
        generated_rows.append(generated_encoded)

    def summarize(rows: list[RecursiveCascadeEncoded]) -> tuple[float, float, float, float | None]:
        hit_rate = mean(sum(row.bitmap) / row.chunks for row in rows)
        visible_net = mean(len(row.original_bits) - len(row.visible_bits) for row in rows)
        tight_net = mean(len(row.original_bits) - row.tight_bits for row in rows)
        all_generated = [
            len(row.original_bits) - row.all_generated_bits
            for row in rows
            if row.all_generated_bits is not None
        ]
        all_generated_net = mean(all_generated) if len(all_generated) == len(rows) else None
        return hit_rate, visible_net, tight_net, all_generated_net

    print(f"exact encode/decode at depth={test_depth}, phenotype={phenotype_bits} bits")
    print(f"{'source':>10} {'raw':>8} {'hit/ch':>8} {'visible':>10} "
          f"{'tight':>10} {'all-gen':>10}")
    for label, rows in [("generated", generated_rows), ("uniform", random_rows)]:
        hit_rate, visible_net, tight_net, all_generated_net = summarize(rows)
        all_generated_text = (
            f"{all_generated_net:10.3f}" if all_generated_net is not None else f"{'n/a':>10}"
        )
        raw_bits = mean(len(row.original_bits) for row in rows)
        print(f"{label:>10} {raw_bits:8.1f} {hit_rate:8.5f} "
              f"{visible_net:10.3f} {tight_net:10.3f} {all_generated_text}")
    print()
    print("Reading: recursion is the DNA-like multiplier. A single root address")
    print("can unfold exponentially many phenotype bits with stateless decode")
    print("because every internal open is scheduled by the public developmental")
    print("tree. But the reachable set under uniform targets is only about")
    print("2^(root_bits - phenotype_bits) per chunk. Recursion solves how to")
    print("unfold compact generated information; it does not by itself solve how")
    print("to make arbitrary files belong to that generated language.")
    print()


def neutral_synonym_payload(genotype: int, phenotype_bits: int) -> str:
    return hash_bits("neutral-synonym-payload", genotype, n_bits=phenotype_bits)


def neutral_next_pass_target(seed: int, target_bits: int) -> str:
    return hash_bits("neutral-next-pass-target", seed, n_bits=target_bits)


@lru_cache(maxsize=64)
def neutral_preimage_sets(genotype_bits: int, phenotype_bits: int) -> dict[str, tuple[int, ...]]:
    preimages: dict[str, list[int]] = {}
    for genotype in range(1 << genotype_bits):
        payload = neutral_synonym_payload(genotype, phenotype_bits)
        preimages.setdefault(payload, []).append(genotype)
    return {payload: tuple(values) for payload, values in preimages.items()}


@lru_cache(maxsize=64)
def neutral_next_compressible_set(target_bits: int, seed_bits: int) -> frozenset[str]:
    outputs = {
        neutral_next_pass_target(seed, target_bits)
        for seed in range(1 << seed_bits)
    }
    return frozenset(outputs)


def expected_log_poisson_nonzero(lam: float, cap: int = 256) -> float:
    if lam <= 0:
        return 0.0
    p0 = expm1(-lam) + 1.0
    nonzero = 1.0 - p0
    if nonzero <= 0:
        return 0.0
    probability = p0
    total = 0.0
    for count in range(1, cap + 1):
        probability *= lam / count
        total += probability * log2(count)
    return total / nonzero


def neutral_synonym_reservoir_demo(
    phenotype_bits: int = 12,
    next_saving_bits: int = 2,
) -> None:
    print("== family 4c: neutral synonymous seed reservoir ==")
    print("Biology's codon degeneracy suggests a non-obvious Telomere channel:")
    print("if one decoded payload has several same-cost seed preimages, the")
    print("encoder can choose the preimage that is friendliest to the next pass.")
    print("The decoder needs no extra metadata; the chosen seed is the record.")
    print()
    print(f"exact map: phenotype={phenotype_bits} bits, next pass saves "
          f"{next_saving_bits} bits when a chosen genotype is itself matchable")
    print(f"{'geno':>5} {'gap':>5} {'lambda':>8} {'cover':>8} "
          f"{'ElogM':>8} {'next base':>9} {'next syn':>9} "
          f"{'mixed net':>10} {'syn-bloat':>10}")
    for genotype_bits in [8, 9, 10, 11, 12, 13, 14, 15, 16]:
        preimages = neutral_preimage_sets(genotype_bits, phenotype_bits)
        coverage = len(preimages) / (1 << phenotype_bits)
        lam = 2 ** (genotype_bits - phenotype_bits)
        elogm = mean(log2(len(values)) for values in preimages.values())
        next_seed_bits = max(0, genotype_bits - next_saving_bits)
        next_set = neutral_next_compressible_set(genotype_bits, next_seed_bits)
        next_base = len(next_set) / (1 << genotype_bits)
        synonym_success = mean(
            1.0 if any(fixed_width_bits(value, genotype_bits) in next_set for value in values)
            else 0.0
            for values in preimages.values()
        )
        gap = phenotype_bits - genotype_bits
        mixed_net = (
            coverage * gap - binary_entropy(coverage)
            if 0.0 < coverage < 1.0
            else coverage * gap
        )
        synonym_minus_bloat = elogm + gap
        print(f"{genotype_bits:5d} {gap:5d} {lam:8.3f} {coverage:8.5f} "
              f"{elogm:8.3f} {next_base:9.5f} {synonym_success:9.5f} "
              f"{mixed_net:10.3f} {synonym_minus_bloat:10.3f}")
    print()
    print("Poisson preimage law for larger spans:")
    print(f"{'gap P-G':>8} {'lambda':>10} {'coverage':>10} "
          f"{'E logM|hit':>12}")
    for gap in [6, 4, 3, 2, 1, 0, -1, -2, -3, -4]:
        lam = 2 ** (-gap)
        coverage = 1.0 - expm1(-lam) - 1.0
        print(f"{gap:8d} {lam:10.5f} {coverage:10.5f} "
              f"{expected_log_poisson_nonzero(lam):12.5f}")
    print()
    print("Reading: neutral synonyms are the closest genetics-like salt channel.")
    print("They are real and stateless: choosing one valid seed among many can")
    print("raise next-pass matchability without recording a lane. But the amount")
    print("of free choice is exactly the preimage multiplicity. In compressive")
    print("rows, multiplicity is tiny; in high-multiplicity rows, the genotype is")
    print("longer than the phenotype and the choice entropy has been bought as")
    print("bloat. This may be useful as a controlled all-block replacement fuel,")
    print("but it is not a free arbitrary-content rate-maintenance channel by")
    print("itself.")
    print()


def sparse_map_zero_threshold(gross_saving: int) -> float:
    if gross_saving <= 0:
        return 1.0
    lo = 0.0
    hi = 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        value = mid * gross_saving - binary_entropy(mid)
        if value >= 0:
            hi = mid
        else:
            lo = mid
    return hi


def poisson_synonym_selected_hit(lambda_value: float, base_hit: float) -> float:
    nonzero = -expm1(-lambda_value)
    if nonzero <= 0:
        return 0.0
    all_miss = ((expm1(-lambda_value * base_hit) + 1.0)
                - (expm1(-lambda_value) + 1.0)) / nonzero
    return 1.0 - all_miss


def neutral_breakthrough_requirement_demo() -> None:
    print("== family 4d: neutral synonym breakthrough requirement ==")
    print("For a sparse mixed pass, the lower-bound ledger is p*d-H(p).")
    print("This surface asks how many same-payload seed synonyms would be")
    print("needed to raise next-pass hit probability to the non-negative")
    print("threshold, compared with the natural preimage multiplicity.")
    print()
    print(f"{'gap':>4} {'base p':>10} {'p*':>10} {'M req':>10} "
          f"{'bits req':>9} {'E M|hit':>9} {'ElogM':>9} {'p syn':>10}")
    for gap in range(1, 9):
        lambda_value = 2 ** (-gap)
        base_hit = -expm1(-lambda_value)
        threshold = sparse_map_zero_threshold(gap)
        m_required = log(1.0 - threshold) / log(1.0 - base_hit)
        bits_required = log2(m_required)
        nonzero = -expm1(-lambda_value)
        expected_m = lambda_value / nonzero
        expected_log_m = expected_log_poisson_nonzero(lambda_value)
        synonym_hit = poisson_synonym_selected_hit(lambda_value, base_hit)
        print(f"{gap:4d} {base_hit:10.5f} {threshold:10.5f} "
              f"{m_required:10.3f} {bits_required:9.3f} "
              f"{expected_m:9.3f} {expected_log_m:9.3f} {synonym_hit:10.5f}")
    print()
    print("Reading: synonyms move the rate in the right direction, but natural")
    print("multiplicity in the compressive rows is far below the threshold")
    print("needed to erase the sparse hit map. That does not kill the idea; it")
    print("says synonyms need an amplifier: all-block replacement, bundle")
    print("selection, recursive trees, or a neutral reservoir created by a")
    print("temporary controlled bloat that later gets spent.")
    print()


def neutral_bundle_amplifier_surface_demo(
    max_arity: int = 64,
    max_gross_saving: int = 96,
) -> None:
    print("== family 4e: neutral reservoir bundle amplifier ==")
    print("If each carried block has B neutral synonym bits, an arity-a bundle")
    print("has about 2^(aB) surface combinations. This prices the tempting")
    print("two-pass strategy: first buy a neutral reservoir, then spend it to")
    print("make later bundle matches denser without storing a lane map.")
    print()
    print(f"surface: arity<= {max_arity}, gross<= {max_gross_saving}, "
          "B in 0.1-bit steps up to 6.0")
    print()
    rows: list[tuple[float, float, int, int, float, float, float]] = []
    for reservoir_bits_tenths in range(0, 61):
        reservoir_bits = reservoir_bits_tenths / 10.0
        variants_per_block = 2 ** reservoir_bits
        for arity in range(1, max_arity + 1):
            variants = variants_per_block ** arity
            for gross_saving in range(1, max_gross_saving + 1):
                base_hit = -expm1(-(2 ** (-gross_saving)))
                amplified_hit = 1.0 - ((1.0 - base_hit) ** variants)
                sparse_bundle_net = amplified_hit * gross_saving - binary_entropy(amplified_hit)
                net_per_block = (sparse_bundle_net / arity) - reservoir_bits
                rows.append((
                    net_per_block,
                    reservoir_bits,
                    arity,
                    gross_saving,
                    base_hit,
                    amplified_hit,
                    sparse_bundle_net,
                ))
    nonzero = [row for row in rows if row[1] > 0]
    positive_bundle = [row for row in nonzero if row[6] > 0]
    best = sorted(positive_bundle, reverse=True)[:14]
    print("Best net rows with a positive bundle ledger:")
    print(f"{'net/block':>10} {'B':>5} {'arity':>5} {'gross':>6} "
          f"{'base p':>10} {'amp p':>10} {'bundle net':>11}")
    for net_per_block, reservoir_bits, arity, gross_saving, base_hit, amplified_hit, bundle_net in best:
        print(f"{net_per_block:10.4f} {reservoir_bits:5.2f} {arity:5d} "
              f"{gross_saving:6d} {base_hit:10.5f} {amplified_hit:10.5f} "
              f"{bundle_net:11.4f}")
    print()
    print("Best active rows with amplified hit probability at least 1%:")
    active = [row for row in positive_bundle if row[5] >= 0.01]
    for net_per_block, reservoir_bits, arity, gross_saving, base_hit, amplified_hit, bundle_net in sorted(active, reverse=True)[:10]:
        spent = reservoir_bits * arity
        recovered = bundle_net / spent if spent else 0.0
        print(f"B={reservoir_bits:.2f} a={arity} gross={gross_saving} "
              f"base={base_hit:.5f} amp={amplified_hit:.5f} "
              f"bundle={bundle_net:.4f} spent={spent:.3f} "
              f"return={recovered:.3f} net/block={net_per_block:.4f}")
    print()
    print("Best return ratio where the bundle ledger is positive:")
    for net_per_block, reservoir_bits, arity, gross_saving, base_hit, amplified_hit, bundle_net in sorted(
        positive_bundle,
        key=lambda row: row[6] / (row[1] * row[2]),
        reverse=True,
    )[:10]:
        spent = reservoir_bits * arity
        recovered = bundle_net / spent if spent else 0.0
        print(f"B={reservoir_bits:.2f} a={arity} gross={gross_saving} "
              f"amp={amplified_hit:.5f} bundle={bundle_net:.4f} "
              f"spent={spent:.3f} return={recovered:.3f} "
              f"net/block={net_per_block:.4f}")
    print()
    print("Reading: neutral choices do compound across bundles, which is the")
    print("right biological shape. But under the uniform random law, the best")
    print("two-pass exchange does not beat the reservoir bits it spends: the")
    print("top nonzero-reservoir rows remain slightly negative. This is still")
    print("useful because it identifies the missing amplifier precisely: a")
    print("finite structural subsidy, cheaper open maps, or unavoidable neutral")
    print("bloat from all-block replacement would only need to cover a small")
    print("residual, not an exponential gap.")
    print()


ORBIT_PHASE_SPAN_BITS = 14
ORBIT_PHASE_SEED_BITS = 9


def affine_orbit_coordinate(slot: int, phase: int, slots: int) -> int:
    if slots <= 0:
        return 0
    stride = 5 if slots % 5 else 7
    return (slot + (phase * stride)) % slots


def orbit_phase_expand(seed: int, coordinate: int, span_bits: int = ORBIT_PHASE_SPAN_BITS) -> str:
    return hash_bits("affine-orbit-coordinate-salt", coordinate, seed, n_bits=span_bits)


@lru_cache(maxsize=4096)
def orbit_phase_book(
    coordinate: int,
    seed_bits: int = ORBIT_PHASE_SEED_BITS,
    span_bits: int = ORBIT_PHASE_SPAN_BITS,
) -> dict[str, int]:
    book: dict[str, int] = {}
    for seed in range(1 << seed_bits):
        book.setdefault(orbit_phase_expand(seed, coordinate, span_bits), seed)
    return book


def orbit_phase_lookup(target: str, coordinate: int, seed_bits: int) -> int | None:
    return orbit_phase_book(coordinate, seed_bits, len(target)).get(target)


@dataclass
class OrbitPhaseLayerStat:
    mode: str
    passes: int
    before_bits: int
    after_bits: int
    chunks: int
    hits: int
    tight_charged_bits: float
    ambiguity_bits: float
    birth_entropy_bits: float


def birth_phase_entropy(phases: list[int], passes: int) -> float:
    if not phases:
        return 0.0
    counts = Counter(phases)
    total = len(phases)
    return -sum((count / total) * log2(count / total) for count in counts.values())


def encode_orbit_final_coordinate_layer(
    bits: str,
    passes: int,
    seed_bits: int = ORBIT_PHASE_SEED_BITS,
) -> tuple[str, OrbitPhaseLayerStat]:
    span_bits = ORBIT_PHASE_SPAN_BITS
    chunks = len(bits) // span_bits
    tail = bits[chunks * span_bits:]
    out: list[str] = []
    hits = 0
    for slot in range(chunks):
        chunk = bits[slot * span_bits:(slot + 1) * span_bits]
        coordinate = affine_orbit_coordinate(slot, passes, chunks)
        seed = orbit_phase_lookup(chunk, coordinate, seed_bits)
        if seed is None:
            out.append("0" + chunk)
        else:
            out.append("1" + format(seed, f"0{seed_bits}b"))
            hits += 1
    if tail:
        out.append(tail)
    bitmap_bits = log2_choose(chunks, hits)
    count_bits = count_class_bits(chunks + 1)
    tight_charged = (
        (chunks - hits) * span_bits
        + hits * seed_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, OrbitPhaseLayerStat(
        "final-coordinate",
        passes,
        len(bits),
        len(encoded),
        chunks,
        hits,
        tight_charged,
        0.0,
        0.0,
    )


def decode_orbit_final_coordinate_layer(
    encoded: str,
    stat: OrbitPhaseLayerStat,
    seed_bits: int = ORBIT_PHASE_SEED_BITS,
) -> str:
    span_bits = ORBIT_PHASE_SPAN_BITS
    chunks: list[str] = []
    offset = 0
    for slot in range(stat.chunks):
        if offset >= len(encoded):
            raise ValueError("truncated orbit-final layer")
        tag = encoded[offset]
        if tag == "0":
            end = offset + 1 + span_bits
            if end > len(encoded):
                raise ValueError("truncated orbit-final literal")
            chunks.append(encoded[offset + 1:end])
            offset = end
        elif tag == "1":
            end = offset + 1 + seed_bits
            if end > len(encoded):
                raise ValueError("truncated orbit-final record")
            seed = int(encoded[offset + 1:end], 2)
            coordinate = affine_orbit_coordinate(slot, stat.passes, stat.chunks)
            chunks.append(orbit_phase_expand(seed, coordinate, span_bits))
            offset = end
        else:
            raise ValueError(f"invalid orbit-final tag {tag!r}")
    tail = encoded[offset:]
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("orbit-final decoded length mismatch")
    return decoded


def encode_orbit_birth_coordinate_layer(
    bits: str,
    passes: int,
    seed_bits: int = ORBIT_PHASE_SEED_BITS,
) -> tuple[str, OrbitPhaseLayerStat]:
    span_bits = ORBIT_PHASE_SPAN_BITS
    chunks = len(bits) // span_bits
    tail = bits[chunks * span_bits:]
    birth_bits = ceil(log2(passes)) if passes > 1 else 0
    out: list[str] = []
    hit_phases: list[int] = []
    for slot in range(chunks):
        chunk = bits[slot * span_bits:(slot + 1) * span_bits]
        chosen: tuple[int, int] | None = None
        for phase in range(passes):
            coordinate = affine_orbit_coordinate(slot, phase, chunks)
            seed = orbit_phase_lookup(chunk, coordinate, seed_bits)
            if seed is not None:
                chosen = (phase, seed)
                break
        if chosen is None:
            out.append("0" + chunk)
        else:
            phase, seed = chosen
            phase_bits = "" if birth_bits == 0 else format(phase, f"0{birth_bits}b")
            out.append("1" + phase_bits + format(seed, f"0{seed_bits}b"))
            hit_phases.append(phase)
    if tail:
        out.append(tail)
    hits = len(hit_phases)
    bitmap_bits = log2_choose(chunks, hits)
    count_bits = count_class_bits(chunks + 1)
    fixed_birth_bits = hits * birth_bits
    entropy_birth_bits = hits * birth_phase_entropy(hit_phases, passes)
    tight_charged = (
        (chunks - hits) * span_bits
        + hits * seed_bits
        + fixed_birth_bits
        + len(tail)
        + bitmap_bits
        + count_bits
    )
    encoded = "".join(out)
    return encoded, OrbitPhaseLayerStat(
        "birth-coordinate",
        passes,
        len(bits),
        len(encoded),
        chunks,
        hits,
        tight_charged,
        fixed_birth_bits,
        entropy_birth_bits,
    )


def decode_orbit_birth_coordinate_layer(
    encoded: str,
    stat: OrbitPhaseLayerStat,
    seed_bits: int = ORBIT_PHASE_SEED_BITS,
) -> str:
    span_bits = ORBIT_PHASE_SPAN_BITS
    birth_bits = ceil(log2(stat.passes)) if stat.passes > 1 else 0
    chunks: list[str] = []
    offset = 0
    for slot in range(stat.chunks):
        if offset >= len(encoded):
            raise ValueError("truncated orbit-birth layer")
        tag = encoded[offset]
        if tag == "0":
            end = offset + 1 + span_bits
            if end > len(encoded):
                raise ValueError("truncated orbit-birth literal")
            chunks.append(encoded[offset + 1:end])
            offset = end
        elif tag == "1":
            end = offset + 1 + birth_bits + seed_bits
            if end > len(encoded):
                raise ValueError("truncated orbit-birth record")
            phase_bits = encoded[offset + 1:offset + 1 + birth_bits]
            phase = int(phase_bits, 2) if phase_bits else 0
            seed = int(encoded[offset + 1 + birth_bits:end], 2)
            if phase >= stat.passes:
                raise ValueError("invalid orbit-birth phase")
            coordinate = affine_orbit_coordinate(slot, phase, stat.chunks)
            chunks.append(orbit_phase_expand(seed, coordinate, span_bits))
            offset = end
        else:
            raise ValueError(f"invalid orbit-birth tag {tag!r}")
    tail = encoded[offset:]
    decoded = "".join(chunks) + tail
    if len(decoded) != stat.before_bits:
        raise ValueError("orbit-birth decoded length mismatch")
    return decoded


def orbit_phase_nonce_demo(trials: int = 120, chunks: int = 64) -> None:
    print("== family 1p: affine orbit phase / final-coordinate nonce ==")
    print("A fixed affine orbit makes every slot's final coordinate known to")
    print("the decoder. If salt uses that final coordinate, decode is stateless")
    print("but each slot gets only one dice roll. If salt uses the coordinate")
    print("at the record's birth phase, the encoder gets P rolls, but the")
    print("decoder needs the phase label or an equivalent referee.")
    print()
    rng = Random(939393)
    span_bits = ORBIT_PHASE_SPAN_BITS
    seed_bits = ORBIT_PHASE_SEED_BITS
    print(
        f"toy codec: span={span_bits} seed={seed_bits} chunks={chunks} trials={trials}"
    )
    print(
        f"{'P':>4} {'mode':>17} {'hit/ch':>8} {'vis net':>9} "
        f"{'tight':>9} {'birth/R':>9} {'ambig/R':>9} {'closed':>9}"
    )
    for passes in [1, 2, 4, 8, 16, 32]:
        for mode in ["final-coordinate", "birth-coordinate"]:
            stats: list[OrbitPhaseLayerStat] = []
            for _ in range(trials):
                bits = format(rng.getrandbits(chunks * span_bits), f"0{chunks * span_bits}b")
                if mode == "final-coordinate":
                    encoded, stat = encode_orbit_final_coordinate_layer(bits, passes, seed_bits)
                    assert decode_orbit_final_coordinate_layer(encoded, stat, seed_bits) == bits
                else:
                    encoded, stat = encode_orbit_birth_coordinate_layer(bits, passes, seed_bits)
                    assert decode_orbit_birth_coordinate_layer(encoded, stat, seed_bits) == bits
                stats.append(stat)
            avg_hits = mean(stat.hits for stat in stats)
            hit_rate = avg_hits / chunks
            visible_net = mean(stat.before_bits - stat.after_bits for stat in stats)
            tight_net = mean(stat.before_bits - stat.tight_charged_bits for stat in stats)
            if mode == "final-coordinate":
                birth_per_record = 0.0
                ambiguity_per_record = 0.0
                p_hit = 2.0 ** (seed_bits - span_bits)
                closed = p_hit * (span_bits - seed_bits) - binary_entropy(p_hit)
            else:
                birth_per_record = (
                    mean(stat.birth_entropy_bits / stat.hits for stat in stats if stat.hits)
                    if any(stat.hits for stat in stats)
                    else 0.0
                )
                ambiguity_per_record = log2(passes) if passes > 1 else 0.0
                p_one = 2.0 ** (seed_bits - span_bits)
                p_hit = 1.0 - ((1.0 - p_one) ** passes)
                closed = (
                    p_hit * (span_bits - seed_bits - ambiguity_per_record)
                    - binary_entropy(p_hit)
                )
            print(
                f"{passes:4d} {mode:>17} {hit_rate:8.4f} {visible_net:9.3f} "
                f"{tight_net:9.3f} {birth_per_record:9.3f} "
                f"{ambiguity_per_record:9.3f} {closed:9.3f}"
            )
        print()
    print("Reading: final-coordinate salts are genuinely decoder-known, but")
    print("they do not refresh dice across P candidate births; the hit rate")
    print("stays near the one-salt baseline. Birth-coordinate salts refresh")
    print("hit supply roughly by P, yet the selected phase has about log2(P)")
    print("bits of entropy per hit. Omitting that phase leaves the same amount")
    print("as trial-decode ambiguity. Orbit phase reads total motion, not birth.")
    print()


def final_board_entropy_gate() -> None:
    print("== final-position board / egg-carton entropy gate ==")
    print("Final occupied positions can be stored once, and R shrinkage lowers")
    print("the total note. The per-survivor birth-label entropy still has to")
    print("come from positions, ordering, a validity restriction, or metadata.")
    print()
    print("Optimistic lower bound if every survivor somehow gets a pass label")
    print("with no slot/order overhead:")
    print(f"{'P passes':>8} {'birth bits/R':>13} {'net after 2b/R':>16}")
    for passes in [2, 3, 4, 8, 16, 64]:
        birth_bits = log2(passes)
        print(f"{passes:8d} {birth_bits:13.3f} {2.0 - birth_bits:16.3f}")
    print()
    print("Universal lane board, unordered occupied cells, S=R cells/pass.")
    print("This is favorable to the board: it stores one final cell set and")
    print("has enough capacity for even the adversarial all-same-pass birth map.")
    print(f"{'R':>6} {'P':>5} {'Q=P*R':>10} {'cell bits/R':>12} "
          f"{'net after 2b/R':>16}")
    for records, passes in [(1, 64), (10, 64), (100, 64), (1000, 64),
                            (100, 2), (100, 3), (100, 4)]:
        cells = records * passes
        cell_bits_per = log2_choose(cells, records) / records
        print(f"{records:6d} {passes:5d} {cells:10d} {cell_bits_per:12.3f} "
              f"{2.0 - cell_bits_per:16.3f}")
    print()
    print("Value/count split for pass lanes. A cheap histogram is not enough;")
    print("the assignment of pass labels to the ordered survivor sequence carries")
    print("the remaining entropy. Histogram + assignment = R*log2(P).")
    print(f"{'R':>5} {'P':>5} {'H(hist)':>10} {'E(assign)':>12} "
          f"{'total/R':>10} {'RlogP/R':>10}")
    for records, passes in [(8, 4), (16, 4), (32, 4), (16, 8)]:
        hist_entropy, expected_assignment = histogram_entropy_and_assignment(records, passes)
        total = hist_entropy + expected_assignment
        print(f"{records:5d} {passes:5d} {hist_entropy:10.3f} "
              f"{expected_assignment:12.3f} {total / records:10.3f} "
              f"{log2(passes):10.3f}")
    print()
    print("Reading: shrinking R reduces the final note and the number of")
    print("matches in the same unit. For many passes, the per-survivor channel")
    print("is still at least log2(P) before practical board slots, ordering,")
    print("holes, or validity restrictions. Tight boards that store only counts")
    print("must pay the missing assignment entropy or reject most birth maps.")
    print()


@dataclass(frozen=True)
class GroupedFinalBoardEncoded:
    passes: int
    survivors: int
    positions: tuple[int, ...]


def encode_grouped_final_board(labels: tuple[int, ...], passes: int) -> GroupedFinalBoardEncoded:
    if passes <= 0:
        raise ValueError("passes must be positive")
    for label in labels:
        if label < 0 or label >= passes:
            raise ValueError("invalid final-board label")
    positions = tuple(index * passes + label for index, label in enumerate(labels))
    return GroupedFinalBoardEncoded(passes, len(labels), positions)


def decode_grouped_final_board(encoded: GroupedFinalBoardEncoded) -> tuple[int, ...]:
    labels = [-1] * encoded.survivors
    for position in encoded.positions:
        group, label = divmod(position, encoded.passes)
        if group < 0 or group >= encoded.survivors:
            raise ValueError("final-board position outside survivor groups")
        if labels[group] != -1:
            raise ValueError("duplicate final-board group")
        labels[group] = label
    if any(label < 0 for label in labels):
        raise ValueError("missing final-board group")
    return tuple(labels)


def shrinking_final_board_surface_demo(
    trials: int = 120,
    survivors: int = 64,
    original_blocks: int = 1024,
) -> None:
    print("== final-position board with shrinking survivor count ==")
    print("This exact toy encodes a birth/open label by placing each final")
    print("survivor in one of P cells inside its public survivor group. It is")
    print("the most favorable final-board form: group order is free from the")
    print("payload order, and the valid arrangement count is exactly P^R.")
    print()
    rng = Random(454545)
    print(f"exact grouped-board toy: survivors={survivors} trials={trials}")
    print(f"{'P':>5} {'round trips':>12} {'log2 V/R':>10} "
          f"{'net@2b/R':>10} {'Q/R':>7}")
    for passes in [2, 3, 4, 8, 16, 64]:
        ok = 0
        for _ in range(trials):
            labels = tuple(rng.randrange(passes) for _ in range(survivors))
            encoded = encode_grouped_final_board(labels, passes)
            ok += int(decode_grouped_final_board(encoded) == labels)
        bits_per_survivor = log2(passes)
        print(f"{passes:5d} {ok:5d}/{trials:<6d} {bits_per_survivor:10.3f} "
              f"{2.0 - bits_per_survivor:10.3f} {passes:7.1f}")

    print()
    print("Shrink surface for a 2-bit gross match win. R/M changes total")
    print("bits, not the per-survivor sign:")
    print(f"{'R/M':>7} {'P':>5} {'board/M':>10} {'gross/M':>10} "
          f"{'net/M':>10} {'note bits':>11}")
    for ratio in [1.0, 0.5, 0.25, 0.125]:
        records = max(1, round(original_blocks * ratio))
        for passes in [2, 4, 8, 64]:
            board_bits = records * log2(passes)
            gross_bits = records * 2.0
            print(f"{ratio:7.3f} {passes:5d} {board_bits / original_blocks:10.3f} "
                  f"{gross_bits / original_blocks:10.3f} "
                  f"{(gross_bits - board_bits) / original_blocks:10.3f} "
                  f"{board_bits:11.1f}")
        print()

    raw_block_bits = 24
    print("Gross win per survivor required for 50% compression of 3-byte")
    print("source blocks, after paying only the ideal grouped-board note:")
    print(f"{'R/M':>7} {'P':>5} {'board/R':>9} {'required g/R':>14}")
    for ratio in [1.0, 0.5, 0.25, 0.125]:
        for passes in [2, 4, 8, 64]:
            board_per = log2(passes)
            required_gross = board_per + raw_block_bits / (2.0 * ratio)
            print(f"{ratio:7.3f} {passes:5d} {board_per:9.3f} "
                  f"{required_gross:14.3f}")
        print()

    print("Unordered cell-board slack surface. This is less favorable than the")
    print("grouped board because extra cells add arrangement entropy:")
    print(f"{'R':>5} {'P':>5} {'Q/R':>7} {'log2C/R':>10} "
          f"{'vs logP':>9} {'net@2b/R':>10}")
    for records, passes in [(32, 4), (64, 4), (64, 8), (64, 64)]:
        for slack in [1.0, 1.5, 2.0, 4.0]:
            cells = ceil(records * passes * slack)
            cell_bits_per = log2_choose(cells, records) / records
            print(f"{records:5d} {passes:5d} {cells / records:7.2f} "
                  f"{cell_bits_per:10.3f} {cell_bits_per - log2(passes):9.3f} "
                  f"{2.0 - cell_bits_per:10.3f}")
        print()

    print("Reading: the grouped board proves the best possible shrinking-R")
    print("case exactly. It decodes statelessly and stores final positions once,")
    print("but those positions are the pass/open labels at R log2(P) bits. When")
    print("R shrinks, the note and the number of gross wins shrink together. For")
    print("a 50% target, smaller R actually requires larger gross savings per")
    print("survivor.")
    print()


def fifty_percent_counting_gate() -> None:
    print("== 50% arbitrary/random compression counting gate ==")
    print("A lossless code that maps every n-bit input to at most n/2 bits")
    print("has far fewer possible outputs than inputs. Any candidate claiming")
    print("50% on arbitrary random data must pay the missing bits as exceptions,")
    print("side information, a non-injective collision, or a distributional")
    print("restriction.")
    print()
    print(f"{'n raw':>7} {'<=n/2 outputs':>16} {'all inputs':>14} "
          f"{'cover fraction':>16} {'missing bits/input':>19}")
    for n_bits in [16, 32, 64, 128, 256]:
        max_outputs = (1 << (n_bits // 2 + 1)) - 1
        all_inputs = 1 << n_bits
        cover_fraction = max_outputs / all_inputs
        missing = -log2(cover_fraction)
        print(f"{n_bits:7d} {max_outputs:16.3e} {all_inputs:14.3e} "
              f"{cover_fraction:16.3e} {missing:19.3f}")
    print()
    print("Reading: unlimited compute can search more addresses, but it cannot")
    print("make an injective lossless map from all n-bit strings into <=n/2")
    print("bits. A Telomere candidate can still target a subset, a distribution,")
    print("or a paid side channel, but not unqualified 50% compression for all")
    print("arbitrary/random inputs.")
    print()


def short_code_count_and_mean(max_bits: int) -> tuple[int, float]:
    count = (1 << (max_bits + 1)) - 1
    if max_bits == 0:
        return count, 0.0
    weighted_bits = ((max_bits - 1) * (1 << (max_bits + 1))) + 2
    return count, weighted_bits / count


def exception_burden_gate() -> None:
    print("== exception-burden gate for partial random coverage ==")
    print("A subset compressor can map only a tiny fraction of n-bit inputs")
    print("to <=n/2 bits. Let every missed input fall back optimistically to")
    print("an n-bit exception, with no per-block tag. The average length still")
    print("stays essentially n unless the short-code fraction is enormous.")
    print()
    print(f"{'n':>5} {'c':>5} {'q max short':>13} {'q for 1b avg':>14} "
          f"{'q for half avg':>16} {'best avg len':>13} {'best save':>11} "
          f"{'raw+tag avg':>12}")
    for n_bits in [16, 32, 64, 128, 256]:
        c_bits = n_bits // 2
        short_count, avg_short_len = short_code_count_and_mean(c_bits)
        q_max = short_count / (1 << n_bits)

        # With raw n-bit exceptions, these are the required short fractions
        # for one bit of average saving and for half-size average length.
        q_for_one_bit = 1.0 / (n_bits - avg_short_len)
        q_for_half_avg = (n_bits - c_bits) / (n_bits - avg_short_len)

        best_save = q_max * (n_bits - avg_short_len)
        best_avg_len = n_bits - best_save
        raw_tag_avg = (n_bits + 1) - (q_max * (n_bits + 1 - avg_short_len))
        print(f"{n_bits:5d} {c_bits:5d} {q_max:13.3e} "
              f"{q_for_one_bit:14.3e} {q_for_half_avg:16.3e} "
              f"{best_avg_len:13.6f} {best_save:11.3e} "
              f"{raw_tag_avg:12.6f}")
    print()
    print("Reading: exceptions are not a loophole for arbitrary/random 50%.")
    print("The short-code population is exponentially too small. If misses")
    print("carry raw bytes, the best global average saving is negligible; if")
    print("misses need even a one-bit tag, the average bloats. Any stronger")
    print("exception scheme must identify an actually non-uniform source.")
    print()


def window_multiplicity_gate() -> None:
    print("== window/placement multiplicity gate ==")
    print("Trying many public windows, lanes, board slots, or instruction")
    print("positions can raise the chance that at least one trial matches.")
    print("But if the decoder cannot derive the selected coordinate before")
    print("opening, that coordinate is arrangement entropy or ambiguity.")
    print()
    print(f"{'L':>5} {'r':>5} {'W trials':>9} {'hit/chunk':>11} "
          f"{'coord bits':>11} {'free E':>10} {'priced E':>10}")
    cases = [
        (16, 12, [1, 2, 4, 8, 16, 32, 64]),
        (32, 16, [1, 256, 4096, 16384, 45426, 65536]),
    ]
    for l_bits, r_bits, windows_list in cases:
        gross = l_bits - r_bits
        p = 2 ** (r_bits - l_bits)
        for windows in windows_list:
            hit = 1.0 - ((1.0 - p) ** windows)
            coord_bits = log2(windows)
            free_expected = hit * gross
            priced_expected = hit * max(0.0, gross - coord_bits)
            print(f"{l_bits:5d} {r_bits:5d} {windows:9d} {hit:11.5f} "
                  f"{coord_bits:11.3f} {free_expected:10.3f} "
                  f"{priced_expected:10.3f}")
        print()
    print("Reading: multiplicity can buy coverage, but the coordinate grows")
    print("with the same order as the nominal saved bits. If the coordinate")
    print("is truly visible in the stream, charge the visible placement,")
    print("segmentation, holes, or carried leftovers instead; if it is not")
    print("visible, charge log2(W) or the equivalent survivor ambiguity.")
    print()


def salt_trilemma_and_compute_gate() -> None:
    print("== public salt / compute trilemma ==")
    print("Fresh public salts can be used three ways: store the selected salt,")
    print("try all salts at decode and pay ambiguity, or derive the salt from")
    print("the output itself. The first two pay log2(K); the third keeps only")
    print("about one valid salt per arbitrary target and does not multiply")
    print("coverage.")
    print()
    span_bits_count = 16
    seed_bits = 10
    record_bits = 12
    base_hit = (1 << seed_bits) / (1 << span_bits_count)
    gross = span_bits_count - record_bits
    print(f"{'K salts':>8} {'stored net/window':>18} {'try-all net/window':>20} "
          f"{'self-selected net':>18} {'free-reject fantasy':>20}")
    for salts in [1, 2, 4, 8, 16, 32, 64]:
        salt_bits = log2(salts)
        coverage = min(1.0, salts * base_hit)
        paid_net = coverage * max(0.0, gross - salt_bits)
        self_net = base_hit * gross
        fantasy = coverage * gross
        print(f"{salts:8d} {paid_net:18.5f} {paid_net:20.5f} "
              f"{self_net:18.5f} {fantasy:20.5f}")
    print()
    print("Reading: the attractive column is the impossible one: it assumes")
    print("wrong salts reject for free while true arbitrary targets are not")
    print("thinned and no salt is stored. The tested self-consistent nonce")
    print("landed on the self-selected column, not the fantasy column.")
    print()

    print("== repeated-compute coverage gate for random spans ==")
    print("For a span of L bits and an r-bit stored record, one fresh trial")
    print("hits with probability p=2^(r-L). To make half of random spans hit,")
    print("the required trial count carries about log2(T) ~= L-r bits of")
    print("implicit address. If those bits are not derivable for free, the")
    print("nominal 50% saving evaporates.")
    print()
    print(f"{'L':>5} {'r':>5} {'p':>12} {'T for 50%':>14} {'salt bits':>11} "
          f"{'eff record':>11} {'save/hit':>10} {'E save/span':>12}")
    for l_bits, r_bits in [(16, 8), (24, 12), (32, 16), (48, 24), (64, 32)]:
        p = 2 ** (r_bits - l_bits)
        trials = ceil(log(0.5) / log1p(-p))
        salt_bits = log2(trials)
        effective_record = r_bits + salt_bits
        save_per_hit = l_bits - effective_record
        expected_save = 0.5 * save_per_hit
        print(f"{l_bits:5d} {r_bits:5d} {p:12.3e} {trials:14.3e} "
              f"{salt_bits:11.3f} {effective_record:11.3f} "
              f"{save_per_hit:10.3f} {expected_save:12.3f}")
    print()
    print("Reading: unlimited compute can raise hit probability, but for")
    print("random spans the trial index has almost exactly the same bit width")
    print("as the nominal saving. A successful mechanism must make that trial")
    print("coordinate decoder-derivable without becoming ambiguity, stored")
    print("metadata, or target-language thinning. None tested so far does.")
    print()


def main() -> None:
    decoder_known_nonce_demo()
    public_lane_ensemble_demo()
    context_neighbor_nonce_demo()
    target_refresh_demo()
    target_refresh_flex_demo()
    full_cover_bundle_lattice_demo()
    adaptive_smallest_cover_demo()
    adaptive_recursive_cover_churn_demo()
    overlap_option_crossover_demo()
    finite_search_depth_crossover_demo()
    block_option_coupling_crossover_demo()
    direct_15_option_crossover_demo()
    collective_selected_rank_entropy_demo()
    recursive_overlap_dynamics_demo()
    high_arity_recursive_cover_surface_demo()
    all_block_exact_lotus_landscape_demo()
    selected_width_residual_entropy_demo()
    public_width_schedule_cover_demo()
    whole_cover_ordinal_language_demo()
    whole_cover_referee_code_demo()
    global_referee_interval_language_demo()
    canonical_minimum_cover_derivation_demo()
    global_fixed_depth_cover_demo()
    homophonic_literal_recode_demo()
    global_transform_layer_demo()
    rechunk_superposition_demo()
    adaptive_length_target_refresh_demo()
    public_shuffle_refresh_demo()
    decoded_left_context_nonce_demo()
    context_lane_validity_demo()
    checkerboard_two_neighbor_context_demo()
    selected_public_shuffle_hitmap_demo()
    prefix_state_nonce_demo()
    sparse_prefix_state_accounting_demo()
    scheduled_slot_bitmap_demo()
    phase_selected_slot_refresh_demo()
    rolling_state_lane_ensemble_demo()
    rolling_lane_collective_selector_demo()
    derivable_lane_variants_demo()
    parent_summary_nonce_demo()
    scheduled_edge_exclusion_demo()
    variable_seed_length_class_demo()
    seed_prefix_nonce_split_demo()
    arity_header_nonce_demo()
    bundle_geometry_partition_demo()
    seed_value_count_separation_demo()
    grouped_schedule_bitmap_demo()
    bucket_directory_hitmap_demo()
    all_or_raw_block_mode_demo()
    hole_run_bundle_demo()
    greedy_score_order_count_demo()
    prefix_stop_countless_demo()
    checksum_pruned_hitmap_demo()
    tagless_value_code_demo()
    finite_class_kraft_bound_demo()
    bbl_random_bundle_density_surface_demo()
    self_dating_grammar_sweep()
    residue_syndrome_trilemma_demo()
    out_of_band_check_trilemma_demo()
    guarded_multi_arity_trilemma_demo()
    derived_validity_sweep()
    nested_referee_wrong_pass_demo()
    biological_developmental_interpreter_demo()
    recursive_biological_cascade_demo()
    neutral_synonym_reservoir_demo()
    neutral_breakthrough_requirement_demo()
    neutral_bundle_amplifier_surface_demo()
    self_consistent_output_nonce_demo()
    orbit_phase_nonce_demo()
    final_board_entropy_gate()
    shrinking_final_board_surface_demo()
    fifty_percent_counting_gate()
    exception_burden_gate()
    window_multiplicity_gate()
    salt_trilemma_and_compute_gate()


if __name__ == "__main__":
    main()
