#!/usr/bin/env python3
"""H158 - keep-what-decodes referee scaling.

SPEC_V1 makes trial decoding normative: reverse a shuffle, try openings, and
keep the reading that decodes and passes the fixed checksum. The tiny proof
artifacts show correctness on small cases, but they do not report how many
readings survive before the checksum.

This kernel instruments the existing Robin proof model without doing a broad
compression test. It counts:

* DFS subset choices tried by keep-what-decodes;
* all-literal terminal readings before checksum;
* checksum winners;
* log2(pre-checksum readings), the minimum referee bits needed before safety.

The purpose is narrow: test whether "checksum as referee" is a bounded
constant or a growing information channel in the stateless opening rule.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
ROBIN_PATH = MODEL_ROOT / "proof_kernel" / "robins_opening_rules.py"
ROBIN_SPEC = importlib.util.spec_from_file_location("robins_for_h158", ROBIN_PATH)
if ROBIN_SPEC is None or ROBIN_SPEC.loader is None:
    raise RuntimeError(f"cannot load {ROBIN_PATH}")
robins = importlib.util.module_from_spec(ROBIN_SPEC)
sys.modules[ROBIN_SPEC.name] = robins
ROBIN_SPEC.loader.exec_module(robins)


@dataclass(frozen=True)
class TrialRow:
    blocks: int
    passes: int
    rep: int
    final_items: int
    final_records: int
    dfs_nodes: int
    max_depth_records: int
    prechecksum_paths: int
    checksum_winner_paths: int
    prechecksum_outputs: int
    checksum_winner_outputs: int
    log2_prechecksum_outputs: float
    checksum_bits_with_32_safety: float
    capped: bool


def item_key(items: list[tuple[str]]) -> tuple[str, ...]:
    return tuple(item[0] for item in items)


def all_literal_payload(items: list[tuple[str]]) -> str | None:
    if any(robins.is_rec(item) for item in items):
        return None
    return "".join(item[0][1:] for item in items)


def count_readings(
    items: list[tuple[str]],
    passes: int,
    target_hash: str,
    *,
    node_cap: int,
) -> tuple[int, int, int, int, int, int, bool]:
    """Return nodes, max recs, path/output prechecksum counts, winners, capped."""

    nodes = 0
    max_recs = 0
    capped = False
    memo: dict[tuple[int, tuple[str, ...]], tuple[int, int, frozenset[str], frozenset[str]]] = {}

    def rec(current: list[tuple[str]], t: int) -> tuple[int, int, frozenset[str], frozenset[str]]:
        nonlocal nodes, max_recs, capped
        if nodes >= node_cap:
            capped = True
            return (0, 0, frozenset(), frozenset())
        key = (t, item_key(current))
        if key in memo:
            return memo[key]
        if t == 0:
            payload = all_literal_payload(current)
            if payload is None:
                memo[key] = (0, 0, frozenset(), frozenset())
                return (0, 0, frozenset(), frozenset())
            pre = 1
            win = 1 if hashlib.sha256(payload.encode()).hexdigest() == target_hash else 0
            pre_outputs = frozenset([payload])
            win_outputs = pre_outputs if win else frozenset()
            memo[key] = (pre, win, pre_outputs, win_outputs)
            return (pre, win, pre_outputs, win_outputs)

        unshuffled = robins.shuffle(current, inv=True)
        rec_positions = [pos for pos, item in enumerate(unshuffled) if robins.is_rec(item)]
        max_recs = max(max_recs, len(rec_positions))
        pre_total = 0
        win_total = 0
        pre_outputs: set[str] = set()
        win_outputs: set[str] = set()

        # Try all subsets. This is exactly the information channel the checksum
        # must referee; no heuristic ordering is credited.
        for size in range(len(rec_positions) + 1):
            for subset_tuple in itertools.combinations(rec_positions, size):
                nodes += 1
                if nodes >= node_cap:
                    capped = True
                    memo[key] = (
                        pre_total,
                        win_total,
                        frozenset(pre_outputs),
                        frozenset(win_outputs),
                    )
                    return (
                        pre_total,
                        win_total,
                        frozenset(pre_outputs),
                        frozenset(win_outputs),
                    )
                subset = set(subset_tuple)
                out: list[tuple[str]] = []
                for pos, item in enumerate(unshuffled):
                    if pos in subset:
                        out.extend(robins.open_rec(item, pos))
                    else:
                        out.append(item)
                pre, win, pre_set, win_set = rec(out, t - 1)
                pre_total += pre
                win_total += win
                pre_outputs.update(pre_set)
                win_outputs.update(win_set)

        memo[key] = (
            pre_total,
            win_total,
            frozenset(pre_outputs),
            frozenset(win_outputs),
        )
        return (
            pre_total,
            win_total,
            frozenset(pre_outputs),
            frozenset(win_outputs),
        )

    pre_paths, win_paths, pre_outputs, win_outputs = rec(items, passes)
    return (
        nodes,
        max_recs,
        pre_paths,
        win_paths,
        len(pre_outputs),
        len(win_outputs),
        capped,
    )


def run_trial(blocks: int, passes: int, rep: int, budget: int, node_cap: int) -> TrialRow:
    rng = random.Random(158_000 + blocks * 10_000 + passes * 101 + rep)
    block_bits = ["".join(rng.choice("01") for _ in range(8)) for _ in range(blocks)]
    target_hash = hashlib.sha256("".join(block_bits).encode()).hexdigest()
    encoded = robins.encode(block_bits, passes, budget=budget, rng=rng)
    parsed = robins.parse("".join(item[0] for item in encoded))
    nodes, max_recs, pre_paths, win_paths, pre_outputs, win_outputs, capped = count_readings(
        [tuple(item) for item in parsed],
        passes,
        target_hash,
        node_cap=node_cap,
    )
    log_pre_outputs = math.log2(pre_outputs) if pre_outputs > 0 else float("-inf")
    return TrialRow(
        blocks=blocks,
        passes=passes,
        rep=rep,
        final_items=len(parsed),
        final_records=sum(1 for item in parsed if robins.is_rec(item)),
        dfs_nodes=nodes,
        max_depth_records=max_recs,
        prechecksum_paths=pre_paths,
        checksum_winner_paths=win_paths,
        prechecksum_outputs=pre_outputs,
        checksum_winner_outputs=win_outputs,
        log2_prechecksum_outputs=log_pre_outputs,
        checksum_bits_with_32_safety=(
            log_pre_outputs + 32.0 if pre_outputs > 0 else float("inf")
        ),
        capped=capped,
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[TrialRow]) -> None:
    print("== keep-what-decodes referee scaling ==")
    print("Robin proof model; counts all-literal readings before checksum.")
    print(
        f"{'N':>2} {'T':>2} {'rep':>3} {'items':>5} {'recs':>4} "
        f"{'nodes':>8} {'maxR':>4} {'paths':>8} {'pwin':>5} "
        f"{'outs':>6} {'owin':>5} {'log2out':>9} {'chk+32':>9} {'cap':>4}"
    )
    for row in rows:
        print(
            f"{row.blocks:2d} {row.passes:2d} {row.rep:3d} "
            f"{row.final_items:5d} {row.final_records:4d} "
            f"{row.dfs_nodes:8d} {row.max_depth_records:4d} "
            f"{row.prechecksum_paths:8d} {row.checksum_winner_paths:5d} "
            f"{row.prechecksum_outputs:6d} {row.checksum_winner_outputs:5d} "
            f"{fmt(row.log2_prechecksum_outputs):>9} "
            f"{fmt(row.checksum_bits_with_32_safety):>9} "
            f"{str(row.capped):>4}"
        )
    print()


def print_reading(rows: list[TrialRow]) -> None:
    print("== reading ==")
    finite = [row for row in rows if row.prechecksum_outputs > 0]
    if not finite:
        print("No terminal all-literal readings in these capped rows.")
        return
    worst = max(finite, key=lambda row: row.log2_prechecksum_outputs)
    print(
        f"Worst measured row: N={worst.blocks},T={worst.passes},rep={worst.rep}; "
        f"unique pre-checksum outputs={worst.prechecksum_outputs}, "
        f"log2={fmt(worst.log2_prechecksum_outputs)}."
    )
    print(
        "A fixed 64-bit checksum can referee these tiny rows, but the bill is "
        "log2(unique pre-checksum outputs) plus safety. If this grows with record "
        "count or pass count, the checksum is a finite referee, not a free "
        "unbounded opening channel."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=12000)
    parser.add_argument("--node-cap", type=int, default=1_000_000)
    parser.add_argument("--rep", type=int, default=2)
    parser.add_argument("--blocks", type=int, action="append", default=[])
    parser.add_argument("--passes", type=int, action="append", default=[])
    args = parser.parse_args()

    block_values = args.blocks or [4, 6]
    pass_values = args.passes or [2, 3, 4]
    rows = [
        run_trial(blocks, passes, rep, args.budget, args.node_cap)
        for blocks in block_values
        for passes in pass_values
        for rep in range(args.rep)
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
