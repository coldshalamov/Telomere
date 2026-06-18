#!/usr/bin/env python3
"""H69 - rank-width sampling bias calibration.

Older total-cover sweeps used an integer representative rank for 49..512 bit
spans, then computed Lotus payload width from that rounded rank. Because the
representative was rounded up to a power of two, it overcharged the high-span
payload width by about one bit.

The corrected path samples log2(rank) under the exponential-race law and
computes payload width directly from the log-rank.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import (
    lotus_payload_width_from_log_rank,
    lotus_payload_width_from_rank,
    sample_log2_first_rank,
)


def row(target_bits: int, trials: int, seed: int) -> tuple[float, float, float]:
    rng = random.Random(seed + target_bits * 1009)
    corrected: list[int] = []
    old_rounded: list[int] = []
    for _ in range(trials):
        log2_rank = sample_log2_first_rank(target_bits, rng)
        corrected.append(lotus_payload_width_from_log_rank(log2_rank))
        rounded_rank = 1 << max(0, math.ceil(log2_rank))
        old_rounded.append(lotus_payload_width_from_rank(rounded_rank))
    delta = [old - new for old, new in zip(old_rounded, corrected)]
    return mean(corrected), mean(old_rounded), mean(delta)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-bits", type=int, nargs="+", default=[49, 64, 96, 128, 192, 384, 512])
    parser.add_argument("--trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=6901)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("== rank-width sampling bias ==")
    print(f"{'target bits':>11} {'corrected width':>16} {'old rounded width':>18} {'old-new':>9}")
    for target_bits in args.target_bits:
        corrected, old, delta = row(target_bits, args.trials, args.seed)
        print(f"{target_bits:11d} {corrected:16.6f} {old:18.6f} {delta:9.6f}")
    print()
    print("Reading: the old 49..512-bit path rounded the rank up before widthing,")
    print("which costs about one payload bit/record. The corrected generator keeps")
    print("the exponential-race sample in log space for width calculation.")


if __name__ == "__main__":
    main()
