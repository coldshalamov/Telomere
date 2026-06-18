#!/usr/bin/env python3
"""Exact neutral-ecology toy kernel.

This is the small model proposed after H18:

    seed/genotype s --phi--> current phenotype x
                    --gamma--> future substrate y

The same stored seed can be read as both the witness for x and a latent
developmental choice that controls y. Under a uniform target over (x,y), this
only covers a tiny reachable set. Under an ecology-generated source where
(x,y) is produced by the public seed map, the seed is a compact stateless
description of the phenotype pair.

This kernel is not a universal-compression claim. It quantifies the exact
premise change: a public non-uniform developmental source.
"""

from __future__ import annotations

import argparse
import hashlib
import math
from dataclasses import dataclass


def hash_bits(label: str, value: int, width: int) -> int:
    if width <= 0:
        return 0
    digest = hashlib.blake2s(f"{label}:{value}".encode("ascii"), digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << width) - 1)


@dataclass(frozen=True)
class EcologyRow:
    seed_bits: int
    current_bits: int
    future_bits: int
    mode: str
    seeds: int
    current_values: int
    total_pairs: int
    reachable_pairs: int
    reachable_current: int
    uniform_pair_coverage: float
    uniform_current_coverage: float
    source_entropy_bits: float
    raw_pair_bits: int
    compressed_bits: int
    gain_per_pair: float
    entropy_deficit_bits: float
    neutral_bits_per_current: float


def build_pairs(seed_bits: int, current_bits: int, future_bits: int, mode: str) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    current_mask = (1 << current_bits) - 1
    future_mask = (1 << future_bits) - 1
    for seed in range(1 << seed_bits):
        if mode == "factor":
            current = seed & current_mask
            future = (seed >> current_bits) & future_mask
        elif mode == "hash":
            current = hash_bits("phi", seed, current_bits)
            future = hash_bits("gamma", seed, future_bits)
        elif mode == "pleiotropic":
            current = seed & current_mask
            regulator = seed >> current_bits
            future = hash_bits("reg", regulator, future_bits)
        else:
            raise ValueError(f"unknown mode: {mode}")
        pairs.add((current, future & future_mask))
    return pairs


def evaluate(seed_bits: int, current_bits: int, future_bits: int, mode: str) -> EcologyRow:
    pairs = build_pairs(seed_bits, current_bits, future_bits, mode)
    current_values = {current for current, _future in pairs}
    total_pairs = 1 << (current_bits + future_bits)
    reachable_pairs = len(pairs)
    reachable_current = len(current_values)
    raw_pair_bits = current_bits + future_bits
    compressed_bits = seed_bits
    # If collisions exist, the source entropy is at most log2(reachable_pairs).
    source_entropy = math.log2(reachable_pairs) if reachable_pairs else 0.0
    neutral = max(0.0, seed_bits - current_bits)
    return EcologyRow(
        seed_bits=seed_bits,
        current_bits=current_bits,
        future_bits=future_bits,
        mode=mode,
        seeds=1 << seed_bits,
        current_values=1 << current_bits,
        total_pairs=total_pairs,
        reachable_pairs=reachable_pairs,
        reachable_current=reachable_current,
        uniform_pair_coverage=reachable_pairs / total_pairs,
        uniform_current_coverage=reachable_current / (1 << current_bits),
        source_entropy_bits=source_entropy,
        raw_pair_bits=raw_pair_bits,
        compressed_bits=compressed_bits,
        gain_per_pair=raw_pair_bits - compressed_bits,
        entropy_deficit_bits=raw_pair_bits - source_entropy,
        neutral_bits_per_current=neutral,
    )


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value < 0.001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def render(rows: list[EcologyRow]) -> str:
    lines = [
        "# Neutral Ecology Tree Kernel",
        "",
        "A row stores one public seed/genotype. The decoder derives both the",
        "current phenotype and the future substrate from that seed. The same",
        "seed is therefore a witness now and a developmental choice later.",
        "",
        "| mode | seed bits W | current bits L | future bits G | reachable pairs | uniform pair coverage | source entropy | raw pair bits | stored bits | gain on ecology source | entropy deficit | neutral bits over current |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.seed_bits} | {row.current_bits} | {row.future_bits} | "
            f"{row.reachable_pairs} | {fmt_prob(row.uniform_pair_coverage)} | "
            f"{row.source_entropy_bits:.3f} | {row.raw_pair_bits} | "
            f"{row.compressed_bits} | {row.gain_per_pair:.3f} | "
            f"{row.entropy_deficit_bits:.3f} | {row.neutral_bits_per_current:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "The ecology source crosses whenever `L + G > W`, because the public",
            "seed map generated the phenotype pair. Uniform arbitrary pairs do",
            "not cross; they are covered only with probability about",
            "`reachable_pairs / 2^(L+G)`. The gain equals real entropy deficit,",
            "so this is a priced source-shaped/developmental lane, not a hidden",
            "all-data channel.",
            "",
            "The `pleiotropic` mode is the biology-shaped one: low seed bits name",
            "the current phenotype, while regulator bits choose a future substrate",
            "through a public map. Those regulator bits are neutral with respect",
            "to the current phenotype but meaningful for future unfolding.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-bits", type=int, nargs="+", default=[8, 10, 12])
    parser.add_argument("--current-bits", type=int, default=8)
    parser.add_argument("--future-bits", type=int, default=8)
    parser.add_argument("--modes", nargs="+", default=["factor", "hash", "pleiotropic"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        evaluate(seed_bits, args.current_bits, args.future_bits, mode)
        for seed_bits in args.seed_bits
        for mode in args.modes
    ]
    print(render(rows))


if __name__ == "__main__":
    main()
