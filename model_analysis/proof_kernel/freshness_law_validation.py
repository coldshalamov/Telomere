"""Laptop-scale validation of the freshness law (toy enumeration, allowed use).

Question under test: does the per-pass match rate collapse without a refresh
operator and sustain with the pass-indexed permutation, as the kernel's
recurrence predicts?

This simulator uses REAL dice: SHA-256 expansions, exact canonical record
costs, strict ``record < span`` acceptance, deterministic seed search, and
greedy non-overlapping replacement on actual bit strings. Staleness is not
modeled here — it EMERGES, because identical window content at identical
depth deterministically yields the identical search result.

Scale is deliberately tiny (small spans, shallow depth) so hits are
observable on a laptop. This validates the probability LAW, not viability;
viability lives in the kernel at datacenter depths.

Run: python freshness_law_validation.py [--runs 5] [--passes 10]
"""

from __future__ import annotations

import argparse
import hashlib
import random

from costs import (
    ARITY_BITS,
    LITERAL_MARKER_BITS,
    j3d1_cost_for_seed_index,
    lotus_width_for_value,
    payload_width_for_seed_index,
)

BLOCK_BITS = 8
DEPTH_BITS = 14  # 16384-seed toy universe
DEPTH = 1 << DEPTH_BITS
ARITY_CODE = {1: "00", 2: "01", 3: "100"}
LITERAL = "111"
MAX_SPAN = 40
ARITY_CAP = 3


def j3d1_encode(seed_index: int) -> str:
    value = seed_index + 1
    pw = payload_width_for_seed_index(seed_index)
    tw = lotus_width_for_value(pw)
    return (
        f"{tw:03b}"
        + format(pw - ((1 << tw) - 2), f"0{tw}b")
        + format(value - ((1 << pw) - 2), f"0{pw}b")
    )


class ToyUniverse:
    """One salted hash universe with lazy first-S-bits match tables."""

    def __init__(self, salt: int):
        self.expansions: list[str] = []
        for seed in range(DEPTH):
            digest = hashlib.sha256(salt.to_bytes(4, "big") + seed.to_bytes(8, "big")).digest()
            self.expansions.append("".join(f"{b:08b}" for b in digest)[:MAX_SPAN])
        self.tables: dict[int, dict[str, int]] = {}

    def best_seed(self, content: str) -> int | None:
        span = len(content)
        table = self.tables.get(span)
        if table is None:
            table = {}
            # ascending index => first occurrence is the cheapest record
            for seed in range(DEPTH):
                prefix = self.expansions[seed][:span]
                if prefix not in table:
                    table[prefix] = seed
            self.tables[span] = table
        return table.get(content)


def run_sim(salt: int, passes: int, permute: bool, entry_count: int) -> list[dict]:
    rng = random.Random(salt * 7919 + 17)
    universe = ToyUniverse(salt)
    # Raw blocks (uniform random bytes — content-blind regime).
    entries = [format(rng.randrange(256), f"0{BLOCK_BITS}b") for _ in range(entry_count)]
    raw_layer = True
    rows = []
    for pass_i in range(1, passes + 1):
        if permute and not raw_layer:
            order = list(range(len(entries)))
            random.Random(pass_i).shuffle(order)  # pass-indexed, content-independent
            entries = [entries[i] for i in order]
        bits_before = sum(len(e) for e in entries) + (
            0 if not raw_layer else 0
        )
        accepted = 0
        gain_bits = 0
        out: list[str] = []
        i = 0
        while i < len(entries):
            best = None  # (gain, arity, record_bits)
            for arity in range(min(ARITY_CAP, len(entries) - i), 0, -1):
                content = "".join(entries[i : i + arity])
                span = len(content)
                if span > MAX_SPAN:
                    continue
                seed = universe.best_seed(content)
                if seed is None:
                    continue
                cost = ARITY_BITS[arity] + j3d1_cost_for_seed_index(seed)
                if cost < span:  # strict
                    gain = span - cost
                    if best is None or gain > best[0]:
                        best = (gain, arity, ARITY_CODE[arity] + j3d1_encode(seed))
            if best is not None:
                gain, arity, record = best
                out.append(record)
                accepted += 1
                gain_bits += gain
                i += arity
            else:
                if raw_layer:
                    out.append(LITERAL + entries[i])  # BIT_LITERAL wrap, charged
                else:
                    out.append(entries[i])  # already a charged record
                i += 1
        entries = out
        raw_layer = False
        bits_after = sum(len(e) for e in entries)
        # metadata: 3 bits/pass for the permutation rule selector
        metadata = 3 if permute else 0
        rows.append(
            {
                "pass": pass_i,
                "accepted": accepted,
                "gain_bits": gain_bits,
                "bits_after": bits_after + metadata,
                "net_pct": 100.0 * (bits_before - bits_after - metadata) / bits_before,
            }
        )
    return rows


def kernel_prediction(passes: int, refresh_name: str, entry_count: int) -> list[float]:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from entry_state import run_scheduled_profile
    from refresh_model import by_name
    from superposition_model import SuperpositionConfig

    _f, rows = run_scheduled_profile(
        entry_count,
        BLOCK_BITS,
        ARITY_CAP,
        (DEPTH_BITS,),
        passes,
        "left_to_right",
        SuperpositionConfig(0, 1, False, False),
        by_name(refresh_name),
        LITERAL_MARKER_BITS,
        None,
        "records_only",
    )
    return [row.net_delta_pct_current for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--passes", type=int, default=10)
    parser.add_argument("--entries", type=int, default=20000)
    args = parser.parse_args()

    print(f"toy universe: depth 2^{DEPTH_BITS}, blocks {BLOCK_BITS} bits, "
          f"{args.entries} blocks, arity cap {ARITY_CAP}, {args.runs} salted runs")
    for permute, label, refresh in (
        (False, "NO REFRESH", "no_refresh"),
        (True, "PERMUTATION REFRESH", "deterministic_entry_permutation"),
    ):
        acc = [[] for _ in range(args.passes)]
        net = [[] for _ in range(args.passes)]
        for salt in range(args.runs):
            for row in run_sim(salt, args.passes, permute, args.entries):
                acc[row["pass"] - 1].append(row["accepted"])
                net[row["pass"] - 1].append(row["net_pct"])
        pred = kernel_prediction(args.passes, refresh, args.entries)
        print(f"\n=== {label} (simulated mean over {args.runs} runs vs kernel prediction) ===")
        print("pass | sim accepted | sim net %  | kernel net %")
        for i in range(args.passes):
            mean_acc = sum(acc[i]) / len(acc[i])
            mean_net = sum(net[i]) / len(net[i])
            print(f"{i+1:4d} | {mean_acc:12.1f} | {mean_net:+9.4f}% | {pred[i]:+9.4f}%")


if __name__ == "__main__":
    main()
