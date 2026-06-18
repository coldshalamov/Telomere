#!/usr/bin/env python3
"""H153 - cloud Q conservation.

H152 showed two different kinds of "superposition" value:

* visible value: choose one final stream y that decodes to an intermediate c,
  then c decodes to x;
* cloud value: sum the future description mass over all possible c values.

This kernel asks whether the cloud can be made honest by turning it into a
public arithmetic distribution Q over bottom strings. That is the only stateless
way to let the decoder use the whole cloud without receiving a rank/selector for
which branch of the cloud was chosen.

For each bottom word x:

    q_raw(x) = sum_c mass({ y : decode(y) = c }) where c decodes to x

with the same first-pass slack cap as H152. The normalized public distribution
is Q(x)=q_raw(x)/Z. Under uniform target words:

    E_U[-log2 Q(X)] = n + KL(U || Q) >= n

If q_raw has holes, the raw/Q mixture is also checked. The best honest mixture
should choose raw-only unless Q is exactly uniform or the source is non-uniform.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
H152_PATH = HERE / "H152-superposition_gap_ledger.py"
H152_SPEC = importlib.util.spec_from_file_location("h152_for_h153", H152_PATH)
if H152_SPEC is None or H152_SPEC.loader is None:
    raise RuntimeError(f"could not load {H152_PATH}")
h152 = importlib.util.module_from_spec(H152_SPEC)
sys.modules[H152_SPEC.name] = h152
H152_SPEC.loader.exec_module(h152)


@dataclass(frozen=True)
class CloudQRow:
    atoms: int
    max_arity: int
    depth_bits: int
    slack: int
    domain_size: int
    z_mass: float
    reachable_fraction: float
    raw_bits: float
    normalized_cross_entropy: float
    normalized_excess: float
    unnormalized_cross_entropy: float
    unnormalized_excess: float
    selected_cross_entropy: float
    selected_excess: float
    mean_cloud_gap: float
    best_alpha: float
    best_mixture_cross_entropy: float
    best_mixture_excess: float
    q_min: float
    q_max: float


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else float("inf")


def cross_entropy_for_mixture(q_values: list[float], alpha: float) -> float:
    domain = len(q_values)
    uniform = 1.0 / domain
    return -sum(
        math.log2((1.0 - alpha) * uniform + alpha * q)
        for q in q_values
    ) / domain


def word_cloud(
    kernel: h152.SuperpositionGapKernel,
    word: int,
    slack: int,
) -> tuple[float, float]:
    target_bits = h152.bits_for_word(word, kernel.atoms)
    budget = kernel.atoms + slack
    descriptions = kernel.bounded_descriptions_for(target_bits, budget)

    cloud_mass = 0.0
    best_weight = 0.0
    seen: set[str] = set()
    for description in descriptions:
        if description.bits in seen:
            continue
        seen.add(description.bits)
        future_total, future_best = kernel.future_mass_and_best(description.bits)
        if future_total > 0.0:
            cloud_mass += future_total
        best_weight = max(best_weight, future_best)
    return cloud_mass, best_weight


def row_for(
    atoms: int,
    max_arity: int,
    depth_bits: int,
    slack: int,
    seed: int,
) -> CloudQRow:
    kernel = h152.SuperpositionGapKernel(
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    domain = 1 << atoms
    raw_bits = float(atoms)
    cloud_values: list[float] = []
    selected_values: list[float] = []
    for word in range(domain):
        cloud, selected = word_cloud(kernel, word, slack)
        cloud_values.append(cloud)
        selected_values.append(selected)

    z_mass = sum(cloud_values)
    if z_mass <= 0.0:
        raise RuntimeError("zero cloud mass; raise D/slack or lower N")

    q_values = [value / z_mass for value in cloud_values]
    reachable = sum(1 for value in cloud_values if value > 0.0) / domain

    if any(value <= 0.0 for value in q_values):
        normalized_ce = float("inf")
        normalized_excess = float("inf")
    else:
        normalized_ce = -sum(math.log2(value) for value in q_values) / domain
        normalized_excess = normalized_ce - raw_bits

    if any(value <= 0.0 for value in cloud_values):
        unnormalized_ce = float("inf")
        unnormalized_excess = float("inf")
    else:
        unnormalized_ce = -sum(math.log2(value) for value in cloud_values) / domain
        unnormalized_excess = unnormalized_ce - raw_bits

    if any(value <= 0.0 for value in selected_values):
        selected_ce = float("inf")
        selected_excess = float("inf")
    else:
        selected_ce = -sum(math.log2(value) for value in selected_values) / domain
        selected_excess = selected_ce - raw_bits

    gaps = [
        math.log2(cloud / selected)
        for cloud, selected in zip(cloud_values, selected_values)
        if cloud > 0.0 and selected > 0.0
    ]

    best_alpha = 0.0
    best_ce = raw_bits
    # Fine enough to catch any real interior improvement; exact optimum should
    # be alpha=0 under uniform data unless Q is uniform.
    for index in range(0, 1001):
        alpha = index / 1000.0
        ce = cross_entropy_for_mixture(q_values, alpha)
        if ce < best_ce - 1e-12:
            best_ce = ce
            best_alpha = alpha

    positive_q = [value for value in q_values if value > 0.0]
    return CloudQRow(
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        slack=slack,
        domain_size=domain,
        z_mass=z_mass,
        reachable_fraction=reachable,
        raw_bits=raw_bits,
        normalized_cross_entropy=normalized_ce,
        normalized_excess=normalized_excess,
        unnormalized_cross_entropy=unnormalized_ce,
        unnormalized_excess=unnormalized_excess,
        selected_cross_entropy=selected_ce,
        selected_excess=selected_excess,
        mean_cloud_gap=finite_mean(gaps),
        best_alpha=best_alpha,
        best_mixture_cross_entropy=best_ce,
        best_mixture_excess=best_ce - raw_bits,
        q_min=min(positive_q) if positive_q else 0.0,
        q_max=max(q_values),
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[CloudQRow]) -> None:
    print("== cloud Q conservation ==")
    print("Q is the normalized two-pass cloud distribution over bottom words.")
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'s':>3} {'Z':>10} {'reach':>7} "
        f"{'Q CE':>9} {'Q excess':>9} {'rawCE':>9} {'selCE':>9} "
        f"{'gap':>8} {'alpha':>7} {'mixCE':>9} {'mixEx':>9} "
        f"{'qmin':>9} {'qmax':>9}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.slack:3d} {fmt(row.z_mass):>10} "
            f"{fmt(row.reachable_fraction):>7} "
            f"{fmt(row.normalized_cross_entropy):>9} "
            f"{fmt(row.normalized_excess):>9} "
            f"{fmt(row.unnormalized_cross_entropy):>9} "
            f"{fmt(row.selected_cross_entropy):>9} "
            f"{fmt(row.mean_cloud_gap):>8} "
            f"{fmt(row.best_alpha):>7} "
            f"{fmt(row.best_mixture_cross_entropy):>9} "
            f"{fmt(row.best_mixture_excess):>9} "
            f"{fmt(row.q_min):>9} {fmt(row.q_max):>9}"
        )
    print()


def print_reading(rows: list[CloudQRow]) -> None:
    print("== reading ==")
    best = min(rows, key=lambda row: row.normalized_excess)
    print(
        f"Best normalized Q row has excess {fmt(best.normalized_excess)} bits "
        f"over raw at N={best.atoms},K={best.max_arity},D={best.depth_bits},s={best.slack}."
    )
    print(
        "The H152 cloud gap is real local option mass, but once it is made "
        "into a public arithmetic distribution, uniform targets pay "
        "n + KL(U||Q). The raw/Q mixture chooses alpha=0 in these rows."
    )
    print(
        "Therefore the cloud can be honest only as a source-shaped/public-Q "
        "codec or as a paid rank stream; it is not a free stateless recursive "
        "compression channel for roughly-all uniform data."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument(
        "--config",
        action="append",
        help="N,K,D,slack row; may be repeated. Defaults to focused H152 rows.",
    )
    return parser.parse_args()


def parse_config(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("config must be N,K,D,slack")
    return parts[0], parts[1], parts[2], parts[3]


def main() -> None:
    args = parse_args()
    configs = (
        [parse_config(value) for value in args.config]
        if args.config
        else [
            (4, 4, 7, 12),
            (4, 4, 7, 20),
            (5, 5, 8, 10),
            (6, 5, 7, 18),
        ]
    )
    rows = [
        row_for(
            atoms=atoms,
            max_arity=max_arity,
            depth_bits=depth_bits,
            slack=slack,
            seed=args.seed,
        )
        for atoms, max_arity, depth_bits, slack in configs
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
