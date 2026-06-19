#!/usr/bin/env python3
"""H213 - recursive witness closure / upward-detour search.

H212 showed that choosing among already-valid witnesses is not a hidden selector
when the selected seed is stored.  The next stronger version is to search
*upward*: choose an intermediate witness record not because it is shortest now,
but because that exact record token is itself easy to regenerate on the next
pass.

This kernel enumerates a tiny two-pass grammar:

    pass2 seed -> pass1 record token -> original N-bit target

Every selected object is decoded from a stored seed or raw escape.  The kernel
also reports the hidden intermediate-length bill: if pass2 may generate several
record-token lengths, the decoder must know which length/class to request.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def hash_bits(label: bytes, bits: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << bits) - 1)


def width_base_index(width: int) -> int:
    if width == 1:
        return 0
    return costs.payload_width_count_le(width - 1)


def seed_indices(max_width: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for width in range(1, max_width + 1):
        base = width_base_index(width)
        for offset in range(costs.payload_width_count_exact(width)):
            out.append((base + offset, width))
    return out


@dataclass(frozen=True)
class Pass1Record:
    seed_index: int
    width: int
    target: int
    token_len: int
    token_value: int


@dataclass(frozen=True)
class Row:
    n_bits: int
    arity: int
    w1: int
    w2: int
    first_records: int
    token_classes: int
    class_bits: int
    final_token_hits: int
    targets: int
    one_pass_support: int
    two_pass_support: int
    two_pass_wins_oracle: int
    two_pass_wins_paid: int
    mean_raw: float
    mean_one_or_raw: float
    mean_two_oracle: float
    mean_two_paid: float
    delta_one: float
    delta_two_oracle: float
    delta_two_paid: float
    hidden_length_gain: float
    best_improvement_paid: int
    support_tax_upper: float


def pass1_records(*, n_bits: int, arity: int, w1: int) -> list[Pass1Record]:
    by_len_count: Counter[int] = Counter()
    tmp: list[tuple[int, int, int, int]] = []
    for seed_index, width in seed_indices(w1):
        cost = costs.record_cost_for_payload_width(arity, width)
        target = hash_bits(
            b"H213-pass1\0"
            + n_bits.to_bytes(2, "big")
            + arity.to_bytes(2, "big")
            + seed_index.to_bytes(8, "big"),
            n_bits,
        )
        ordinal = by_len_count[cost]
        by_len_count[cost] += 1
        tmp.append((seed_index, width, target, cost, ordinal))
    return [
        Pass1Record(
            seed_index=seed_index,
            width=width,
            target=target,
            token_len=token_len,
            token_value=ordinal,
        )
        for seed_index, width, target, token_len, ordinal in tmp
    ]


def final_token_costs(
    *,
    records: list[Pass1Record],
    arity: int,
    w2: int,
    class_bits: int,
) -> tuple[dict[tuple[int, int], int], int]:
    token_set = {(record.token_len, record.token_value) for record in records}
    token_lengths = sorted({record.token_len for record in records})
    best: dict[tuple[int, int], int] = {}
    hit_count = 0
    for seed_index, width in seed_indices(w2):
        final_cost = costs.record_cost_for_payload_width(arity, width) + class_bits
        for token_len in token_lengths:
            value = hash_bits(
                b"H213-pass2\0"
                + token_len.to_bytes(2, "big")
                + seed_index.to_bytes(8, "big"),
                token_len,
            )
            token = (token_len, value)
            if token not in token_set:
                continue
            hit_count += 1
            if final_cost < best.get(token, 10**18):
                best[token] = final_cost
    return best, hit_count


def run_row(*, n_bits: int, arity: int, w1: int, w2: int, raw_mode_bits: int) -> Row:
    records = pass1_records(n_bits=n_bits, arity=arity, w1=w1)
    target_count = 1 << n_bits
    raw_cost = n_bits + raw_mode_bits
    token_classes = len({record.token_len for record in records})
    class_bits = ceil_log2(token_classes)

    by_target: dict[int, list[Pass1Record]] = defaultdict(list)
    for record in records:
        by_target[record.target].append(record)

    final_oracle, final_oracle_hits = final_token_costs(
        records=records, arity=arity, w2=w2, class_bits=0
    )
    final_paid, final_paid_hits = final_token_costs(
        records=records, arity=arity, w2=w2, class_bits=class_bits
    )
    assert final_oracle_hits == final_paid_hits

    one_sum = 0.0
    two_oracle_sum = 0.0
    two_paid_sum = 0.0
    two_support = 0
    wins_oracle = 0
    wins_paid = 0
    best_improvement_paid = 0

    for target in range(target_count):
        candidates = by_target.get(target, [])
        best_one = min((record.token_len for record in candidates), default=10**18)
        one_or_raw = min(raw_cost, best_one)

        best_two_oracle = 10**18
        best_two_paid = 10**18
        for record in candidates:
            token = (record.token_len, record.token_value)
            if token in final_oracle:
                best_two_oracle = min(best_two_oracle, final_oracle[token])
            if token in final_paid:
                best_two_paid = min(best_two_paid, final_paid[token])

        if best_two_paid < 10**18:
            two_support += 1
        two_oracle = min(one_or_raw, best_two_oracle)
        two_paid = min(one_or_raw, best_two_paid)
        if two_oracle < one_or_raw:
            wins_oracle += 1
        if two_paid < one_or_raw:
            wins_paid += 1
            best_improvement_paid = max(best_improvement_paid, one_or_raw - two_paid)
        one_sum += one_or_raw
        two_oracle_sum += two_oracle
        two_paid_sum += two_paid

    mean_one = one_sum / target_count
    mean_oracle = two_oracle_sum / target_count
    mean_paid = two_paid_sum / target_count
    support_bits = math.log2(max(1, two_support))
    return Row(
        n_bits=n_bits,
        arity=arity,
        w1=w1,
        w2=w2,
        first_records=len(records),
        token_classes=token_classes,
        class_bits=class_bits,
        final_token_hits=final_oracle_hits,
        targets=target_count,
        one_pass_support=len(by_target),
        two_pass_support=two_support,
        two_pass_wins_oracle=wins_oracle,
        two_pass_wins_paid=wins_paid,
        mean_raw=float(raw_cost),
        mean_one_or_raw=mean_one,
        mean_two_oracle=mean_oracle,
        mean_two_paid=mean_paid,
        delta_one=mean_one - n_bits,
        delta_two_oracle=mean_oracle - n_bits,
        delta_two_paid=mean_paid - n_bits,
        hidden_length_gain=mean_paid - mean_oracle,
        best_improvement_paid=best_improvement_paid,
        support_tax_upper=n_bits - support_bits,
    )


def parse_int_list(text: str) -> list[int]:
    return [int(part) for part in text.split(",") if part]


def print_rows(args: argparse.Namespace) -> None:
    rows = [
        run_row(n_bits=n, arity=args.arity, w1=w1, w2=w2, raw_mode_bits=args.raw_mode_bits)
        for n in parse_int_list(args.n_bits)
        for w1 in parse_int_list(args.w1)
        for w2 in parse_int_list(args.w2)
    ]
    print("== H213 recursive witness closure / upward detour ==")
    print("pass2 seed -> pass1 record token -> original target; token length class is charged.")
    print(
        f"{'N':>3} {'A':>2} {'W1':>3} {'W2':>3} {'rec1':>5} {'cls':>3} "
        f"{'cBits':>5} {'tokHit':>6} {'sup1':>5} {'sup2':>5} "
        f"{'winO':>5} {'winP':>5} {'oneD':>9} {'twoO':>9} {'twoP':>9} "
        f"{'lenBill':>8} {'bestImp':>7} {'tax2':>8}"
    )
    for row in rows:
        print(
            f"{row.n_bits:3d} {row.arity:2d} {row.w1:3d} {row.w2:3d} "
            f"{row.first_records:5d} {row.token_classes:3d} {row.class_bits:5d} "
            f"{row.final_token_hits:6d} {row.one_pass_support:5d} {row.two_pass_support:5d} "
            f"{row.two_pass_wins_oracle:5d} {row.two_pass_wins_paid:5d} "
            f"{fmt(row.delta_one):>9} {fmt(row.delta_two_oracle):>9} "
            f"{fmt(row.delta_two_paid):>9} {fmt(row.hidden_length_gain):>8} "
            f"{row.best_improvement_paid:7d} {fmt(row.support_tax_upper):>8}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Recursive witness closure is a legal non-greedy search primitive:")
    print("the final seed names the intermediate record token, so no selector is")
    print("stored separately.  The apparent oracle gain from choosing variable")
    print("intermediate token lengths must still pay a length/arity/boundary class.")
    print("After raw fallback and class bits, the finite uniform mean remains")
    print("non-negative in these rows; wins are subset/reachable events unless")
    print("a future closure law beats its own support tax.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-bits", default="8,10,12")
    parser.add_argument("--arity", type=int, default=1)
    parser.add_argument("--w1", default="6,8")
    parser.add_argument("--w2", default="6,8")
    parser.add_argument("--raw-mode-bits", type=int, default=1)
    args = parser.parse_args()
    print_rows(args)
    print_theorem()


if __name__ == "__main__":
    main()
