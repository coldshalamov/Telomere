#!/usr/bin/env python3
"""H160 - seed-only closure transfer matrix.

H159 enumerated finite visible seed-record strings, then looked for edges
``y -> x`` where y decodes to another visible seed-record string x. H160 removes
the finite target-node conditioning: it counts source record streams directly
and runs the emitted target bits through a parser for the seed-record language.

Source side:
    y is a sequence of H96 seed records.

Target side:
    decode(y) emits the record.value bits of those source records.
    The emitted bitstream is accepted only if it is also parseable as a
    sequence of H96 visible record strings.

No filler, cloud, stop selector, rank channel, or raw repair is credited. This
is still an H96 toy-family closure test, not a production Lotus parser.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h160", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"cannot load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


ROOT_STATE = frozenset([0])


@dataclass(frozen=True)
class Trie:
    transitions: tuple[dict[str, int], ...]
    accepting: frozenset[int]
    duplicate_records: int
    accepting_with_children: int


@dataclass(frozen=True)
class MatrixRow:
    max_arity: int
    depth_bits: int
    cap_bits: int
    record_count: int
    trie_nodes: int
    duplicate_records: int
    accepting_with_children: int
    min_cost_minus_emit: int
    symbol_kraft: float
    total_paths: int
    alive_paths: int
    closed_paths: int
    closure_path_fraction: float
    total_mass: float
    alive_mass: float
    closed_mass: float
    closure_mass_fraction: float
    closure_tax_bits: float
    compressive_closed_paths: int
    compressive_mass: float
    compressive_tax_bits: float
    best_gain: int
    mean_closed_gain: float
    active_state_count: int
    max_active_width: int
    best_closed_src_len: int
    best_closed_src_fraction: float


def record_value_bits(record: h96.Record) -> str:
    return format(record.value, f"0{record.arity}b")


def flat_records(max_arity: int, depth_bits: int, seed: int) -> list[h96.Record]:
    by_value, _edge_weights, _edge_maxes = h96.build_record_family(
        block_bits=1,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    records: list[h96.Record] = []
    for arity in range(1, max_arity + 1):
        for bucket in by_value[arity]:
            records.extend(bucket)
    return sorted(records, key=lambda item: (len(item.bits), item.arity, item.rank, item.bits))


def build_trie(records: list[h96.Record]) -> Trie:
    transitions: list[dict[str, int]] = [dict()]
    accepting: set[int] = set()
    seen_records: set[str] = set()
    duplicates = 0
    for record in records:
        node = 0
        for bit in record.bits:
            nxt = transitions[node].get(bit)
            if nxt is None:
                nxt = len(transitions)
                transitions[node][bit] = nxt
                transitions.append({})
            node = nxt
        if record.bits in seen_records:
            duplicates += 1
        seen_records.add(record.bits)
        accepting.add(node)
    accepting_with_children = sum(1 for node in accepting if transitions[node])
    return Trie(
        transitions=tuple(transitions),
        accepting=frozenset(accepting),
        duplicate_records=duplicates,
        accepting_with_children=accepting_with_children,
    )


def feed_bit(trie: Trie, active: frozenset[int], bit: str) -> frozenset[int]:
    nxt: set[int] = set()
    for state in active:
        dest = trie.transitions[state].get(bit)
        if dest is None:
            continue
        nxt.add(dest)
        if dest in trie.accepting:
            nxt.add(0)
    return frozenset(nxt)


def feed_bits(trie: Trie, active: frozenset[int], bits: str) -> frozenset[int]:
    current = active
    for bit in bits:
        current = feed_bit(trie, current, bit)
        if not current:
            break
    return current


def safe_tax(part: float, whole: float) -> float:
    if part <= 0.0 or whole <= 0.0:
        return float("inf")
    return -math.log2(part / whole)


def source_total_counts(records: list[h96.Record], cap_bits: int) -> Counter[int]:
    counts: Counter[int] = Counter()
    counts[0] = 1
    for length in range(cap_bits + 1):
        base = counts[length]
        if base == 0:
            continue
        for record in records:
            nxt = length + len(record.bits)
            if 0 < nxt <= cap_bits:
                counts[nxt] += base
    counts.pop(0, None)
    return counts


def source_total_mass(records: list[h96.Record], cap_bits: int) -> tuple[int, float, Counter[int]]:
    counts = source_total_counts(records, cap_bits)
    total_paths = sum(counts.values())
    mass = sum(count * (2.0 ** -length) for length, count in counts.items())
    return total_paths, mass, counts


def row_for(max_arity: int, depth_bits: int, cap_bits: int, seed: int) -> MatrixRow:
    records = flat_records(max_arity, depth_bits, seed)
    trie = build_trie(records)
    total_paths, total_mass, total_by_len = source_total_mass(records, cap_bits)
    symbol_kraft = sum(2.0 ** (-len(record.bits)) for record in records)
    min_cost_minus_emit = min(len(record.bits) - record.arity for record in records)

    # DP over live target parser states. Values are path counts by
    # (source_len, target_len, active_state_set).
    initial = (0, 0, ROOT_STATE)
    queue: deque[tuple[int, int, frozenset[int]]] = deque([initial])
    states: dict[tuple[int, int, frozenset[int]], int] = {initial: 1}
    closed_by_src_len: Counter[int] = Counter()
    closed_gains: list[int] = []
    compressive_paths = 0
    compressive_mass = 0.0
    closed_paths = 0
    closed_mass = 0.0
    alive_paths = 0
    alive_mass = 0.0
    active_state_count = 0
    max_active_width = 1

    while queue:
        src_len, tgt_len, active = queue.popleft()
        count = states[(src_len, tgt_len, active)]
        if src_len > 0:
            alive_paths += count
            alive_mass += count * (2.0 ** -src_len)
            active_state_count += 1
            max_active_width = max(max_active_width, len(active))
            if 0 in active:
                gain = tgt_len - src_len
                closed_paths += count
                closed_mass += count * (2.0 ** -src_len)
                closed_by_src_len[src_len] += count
                closed_gains.extend([gain] * min(count, 10_000))
                if gain > 0:
                    compressive_paths += count
                    compressive_mass += count * (2.0 ** -src_len)
        for record in records:
            next_src_len = src_len + len(record.bits)
            if next_src_len > cap_bits:
                continue
            next_active = feed_bits(trie, active, record_value_bits(record))
            if not next_active:
                continue
            key = (next_src_len, tgt_len + record.arity, next_active)
            if key not in states:
                states[key] = 0
                queue.append(key)
            states[key] += count

    if closed_by_src_len:
        best_closed_src_len, best_closed_count = max(
            closed_by_src_len.items(),
            key=lambda item: (item[1] / total_by_len[item[0]], -item[0]),
        )
        best_closed_fraction = best_closed_count / total_by_len[best_closed_src_len]
    else:
        best_closed_src_len = 0
        best_closed_fraction = 0.0

    # If counts are huge, closed_gains is sampled for memory; best_gain is
    # computed conservatively from the structural per-record floor.
    best_gain = max(closed_gains) if closed_gains else 0
    mean_gain = mean(closed_gains) if closed_gains else float("-inf")

    return MatrixRow(
        max_arity=max_arity,
        depth_bits=depth_bits,
        cap_bits=cap_bits,
        record_count=len(records),
        trie_nodes=len(trie.transitions),
        duplicate_records=trie.duplicate_records,
        accepting_with_children=trie.accepting_with_children,
        min_cost_minus_emit=min_cost_minus_emit,
        symbol_kraft=symbol_kraft,
        total_paths=total_paths,
        alive_paths=alive_paths,
        closed_paths=closed_paths,
        closure_path_fraction=(closed_paths / total_paths if total_paths else 0.0),
        total_mass=total_mass,
        alive_mass=alive_mass,
        closed_mass=closed_mass,
        closure_mass_fraction=(closed_mass / total_mass if total_mass else 0.0),
        closure_tax_bits=safe_tax(closed_mass, total_mass),
        compressive_closed_paths=compressive_paths,
        compressive_mass=compressive_mass,
        compressive_tax_bits=safe_tax(compressive_mass, total_mass),
        best_gain=best_gain,
        mean_closed_gain=mean_gain,
        active_state_count=active_state_count,
        max_active_width=max_active_width,
        best_closed_src_len=best_closed_src_len,
        best_closed_src_fraction=best_closed_fraction,
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def compact_int(value: int) -> str:
    if value >= 1_000_000:
        return f"{value:.3e}"
    return str(value)


def print_rows(rows: list[MatrixRow]) -> None:
    print("== seed-only closure transfer matrix ==")
    print("Source streams are H96 records; emitted target bits must parse as H96 records.")
    print(
        f"{'K':>2} {'D':>2} {'cap':>3} {'recs':>5} {'trie':>5} "
        f"{'min(c-a)':>8} {'kraft':>8} {'tot':>9} {'alive':>9} "
        f"{'closed':>9} {'clFrac':>8} {'clTax':>8} {'cmp':>7} "
        f"{'cmpTax':>8} {'bestG':>6} {'meanG':>8} {'states':>7} "
        f"{'width':>5} {'bestL':>5} {'bestF':>8} {'dup':>4} {'pref':>4}"
    )
    for row in rows:
        print(
            f"{row.max_arity:2d} {row.depth_bits:2d} {row.cap_bits:3d} "
            f"{row.record_count:5d} {row.trie_nodes:5d} "
            f"{row.min_cost_minus_emit:8d} {fmt(row.symbol_kraft):>8} "
            f"{compact_int(row.total_paths):>9} {compact_int(row.alive_paths):>9} "
            f"{compact_int(row.closed_paths):>9} {fmt(row.closure_mass_fraction):>8} "
            f"{fmt(row.closure_tax_bits):>8} {compact_int(row.compressive_closed_paths):>7} "
            f"{fmt(row.compressive_tax_bits):>8} {row.best_gain:6d} "
            f"{fmt(row.mean_closed_gain):>8} {row.active_state_count:7d} "
            f"{row.max_active_width:5d} {row.best_closed_src_len:5d} "
            f"{fmt(row.best_closed_src_fraction):>8} {row.duplicate_records:4d} "
            f"{row.accepting_with_children:4d}"
        )
    print()


def print_reading(rows: list[MatrixRow]) -> None:
    print("== reading ==")
    best_closed = max(rows, key=lambda row: row.closure_mass_fraction)
    print(
        f"Best closure mass row: K={best_closed.max_arity},D={best_closed.depth_bits},"
        f"cap={best_closed.cap_bits}; closure fraction "
        f"{fmt(best_closed.closure_mass_fraction)}, tax "
        f"{fmt(best_closed.closure_tax_bits)} bits."
    )
    best_gain = max(rows, key=lambda row: row.best_gain)
    print(
        f"Best closed gain row: K={best_gain.max_arity},D={best_gain.depth_bits},"
        f"cap={best_gain.cap_bits}; best gain {best_gain.best_gain} bits."
    )
    print(
        "The structural column min(c-a) is the per-record visible cost minus "
        "emitted target bits. When it is positive for every source record, a "
        "source stream cannot be shorter than its emitted target bitstream in "
        "this H96 model; recurrent compression must therefore come from a "
        "different item-level grammar, not this bit-level surrogate."
    )
    if any(row.duplicate_records or row.accepting_with_children for row in rows):
        print(
            "The duplicate/pref columns are syntax stress markers for H96. They "
            "do not create credited compression; a production version needs an "
            "exact prefix-safe Lotus/item parser."
        )


def parse_job(raw: str) -> tuple[int, int, int]:
    parts = raw.split(",")
    if len(parts) != 3:
        raise ValueError("--job must be K,D,cap")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="append", default=[], help="K,D,cap")
    parser.add_argument("--seed", type=int, default=146146)
    args = parser.parse_args()

    jobs = [parse_job(item) for item in args.job] if args.job else [
        (2, 2, 24),
        (3, 3, 24),
        (4, 3, 28),
        (5, 3, 28),
    ]
    rows = [row_for(max_arity, depth_bits, cap_bits, args.seed) for max_arity, depth_bits, cap_bits in jobs]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
