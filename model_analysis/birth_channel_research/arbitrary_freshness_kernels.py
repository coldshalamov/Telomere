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

from dataclasses import dataclass
from hashlib import sha256
from math import log2
from random import Random
from statistics import mean


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
          f"{'candidates':>12} {'ambig bits':>11} {'orig in set':>11} {'net vs raw':>11}")
    raw_payload_bits = len(values) * CHURN_B
    for lanes in [1, 2, 4, 8]:
        encoded = encode_public_lane_stream(values, lanes, passes=4)
        candidates, capped = lane_decode_stream_candidates(encoded, lanes)
        records = sum(1 for item in encoded if item.kind == "R")
        payload_bits = sum(len(item_bits(item)) for item in encoded)
        candidate_count = len(candidates)
        ambiguity_bits = log2(candidate_count) if candidate_count else 0.0
        original_present = values in candidates
        net_vs_raw = raw_payload_bits - payload_bits - ambiguity_bits
        suffix = "+" if capped else ""
        print(f"{lanes:6d} {len(encoded):11d} {records:8d} {payload_bits:12d} "
              f"{str(candidate_count) + suffix:>12} {ambiguity_bits:11.3f} "
              f"{str(original_present):>11} {net_vs_raw:11.3f}")
    print()
    print("Reading: public lanes increase search supply without storing a")
    print("lane id, but the decoder's candidate set grows because wrong")
    print("lanes often parse. Stronger self-dating grammar is needed before")
    print("this can scale, and that grammar must not destroy hit supply.")
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
# Family 3: self-dating grammar / wrong-pass explosion.


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


def main() -> None:
    decoder_known_nonce_demo()
    public_lane_ensemble_demo()
    target_refresh_demo()
    target_refresh_flex_demo()
    self_dating_grammar_sweep()
    derived_validity_sweep()


if __name__ == "__main__":
    main()
