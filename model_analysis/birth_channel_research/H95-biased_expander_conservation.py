#!/usr/bin/env python3
"""H95 - biased expander conservation check.

H94 closed the easy "better witness code" route: once rank/record mass is
normalized, the optimistic K/D crossing disappears. The next honest biological
analogy is a native generator that is not uniform: seed expansions may prefer
future-fertile spans.

This kernel tests that idea in the smallest exact setting. It builds several
fixed public expander laws over the same paid V1 witness records:

* uniform: seed outputs are uniform over span values.
* fertile(theta): seed outputs are biased toward local spans that are easier to
  cover again under the uniform baseline.
* anti(theta): the same bias inverted.

For each law it sums the total whole-cover Kraft mass over every raw word.
If a biased generator is a real missing piece for arbitrary total-cover
recursion, it must increase honest mass, not merely move it onto different
strings. A fixed public source law may still compress matching non-uniform data,
but its KL/source-shape bill is priced separately.
"""

from __future__ import annotations

import bisect
import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import record_cost_for_payload_width  # noqa: E402
from total_cover_lotus_crossover import lotus_payload_width_from_rank  # noqa: E402

H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)


@dataclass(frozen=True)
class Law:
    name: str
    mode: str
    theta: float


@dataclass(frozen=True)
class LawRow:
    law: str
    z_total: float
    z_selected: float
    cover_mass_error: float
    q_entropy: float
    uniform_excess: float
    source_saving: float
    source_bill: float
    source_margin: float
    top25_mass: float
    future_lift: float


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


def span_value(word: int, start_atom: int, arity: int, block_bits: int, atoms: int) -> int:
    shift_atoms = atoms - (start_atom + arity)
    shift = shift_atoms * block_bits
    mask = (1 << (arity * block_bits)) - 1
    return (word >> shift) & mask


def rank_weights(max_arity: int, depth_bits: int) -> list[list[tuple[int, float]]]:
    rows: list[list[tuple[int, float]]] = [[]]
    for arity in range(1, max_arity + 1):
        arity_rows: list[tuple[int, float]] = []
        for rank in range(1, (1 << depth_bits) + 1):
            width = lotus_payload_width_from_rank(rank)
            cost = record_cost_for_payload_width(arity, width)
            arity_rows.append((rank, 2.0 ** (-cost)))
        rows.append(arity_rows)
    return rows


def choose_weighted(rng: random.Random, probabilities: list[float]) -> int:
    total = sum(probabilities)
    if total <= 0.0:
        raise ValueError("probability mass must be positive")
    cumulative: list[float] = []
    running = 0.0
    for probability in probabilities:
        running += probability / total
        cumulative.append(running)
    cumulative[-1] = 1.0
    return bisect.bisect_left(cumulative, rng.random())


def build_uniform_edges(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[list[float]], list[list[float]]]:
    rng = random.Random(seed)
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    weights_by_arity = rank_weights(max_arity, depth_bits)
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for _, weight in weights_by_arity[arity]:
            value = rng.randrange(value_count)
            weights[value] += weight
            maxes[value] = max(maxes[value], weight)
        total_weights.append(weights)
        max_weights.append(maxes)
    return total_weights, max_weights


def local_fertility_profiles(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> list[list[float]]:
    base_edges, base_maxes = build_uniform_edges(block_bits, max_arity, depth_bits, seed)
    profiles: list[list[float]] = [[]]
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        values: list[float] = []
        for value in range(value_count):
            total, _ = _h74.dp_mass_for_word(
                value,
                arity,
                block_bits,
                min(max_arity, arity),
                base_edges,
                base_maxes,
            )
            values.append(total)
        profiles.append(values)
    return profiles


def probabilities_for_law(profile: list[float], law: Law) -> list[float]:
    if law.mode == "uniform":
        return [1.0] * len(profile)
    positive = [value for value in profile if value > 0.0]
    floor = (min(positive) if positive else 1.0) * 1e-6
    if law.mode == "fertile":
        return [(value + floor) ** law.theta for value in profile]
    if law.mode == "anti":
        return [(value + floor) ** (-law.theta) for value in profile]
    raise ValueError(law.mode)


def build_biased_edges(
    law: Law,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
    profiles: list[list[float]],
) -> tuple[list[list[float]], list[list[float]]]:
    rng = random.Random(seed)
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    weights_by_arity = rank_weights(max_arity, depth_bits)
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        probabilities = probabilities_for_law(profiles[arity], law)
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for _, weight in weights_by_arity[arity]:
            value = choose_weighted(rng, probabilities)
            weights[value] += weight
            maxes[value] = max(maxes[value], weight)
        total_weights.append(weights)
        max_weights.append(maxes)
    return total_weights, max_weights


def cover_mass_from_record_weights(max_arity: int, atoms: int, depth_bits: int) -> float:
    weights_by_arity = rank_weights(max_arity, depth_bits)
    arity_masses = [0.0] + [sum(weight for _, weight in rows) for rows in weights_by_arity[1:]]
    dp = [0.0] * (atoms + 1)
    dp[0] = 1.0
    for end in range(1, atoms + 1):
        dp[end] = sum(dp[end - arity] * arity_masses[arity] for arity in range(1, min(max_arity, end) + 1))
    return dp[atoms]


def domain_masses(
    block_bits: int,
    atoms: int,
    max_arity: int,
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
) -> tuple[list[float], list[float]]:
    q_raw: list[float] = []
    best_raw: list[float] = []
    for word in range(1 << (block_bits * atoms)):
        total, best = _h74.dp_mass_for_word(word, atoms, block_bits, max_arity, edge_weights, edge_maxes)
        q_raw.append(total)
        best_raw.append(best)
    return q_raw, best_raw


def row_for_law(
    law: Law,
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
    profiles: list[list[float]],
    expected_cover_mass: float,
    future_values: list[float],
    top25: set[int],
    uniform_future: float,
) -> LawRow:
    edges, maxes = build_biased_edges(law, block_bits, max_arity, depth_bits, seed, profiles)
    q_raw, best_raw = domain_masses(block_bits, atoms, max_arity, edges, maxes)
    z_total = sum(q_raw)
    z_selected = sum(best_raw)
    if z_total <= 0.0:
        raise RuntimeError(f"{law.name} has zero total mass")
    q = [value / z_total for value in q_raw]
    raw_bits = block_bits * atoms
    q_entropy = entropy(q)
    if any(value == 0.0 for value in q):
        uniform_excess = float("inf")
    else:
        uniform_excess = -sum(math.log2(value) for value in q) / len(q) - raw_bits
    source_saving = raw_bits + math.log2(z_total) - q_entropy
    source_bill = raw_bits - q_entropy
    source_margin = source_saving - source_bill
    return LawRow(
        law=law.name,
        z_total=z_total,
        z_selected=z_selected,
        cover_mass_error=z_total - expected_cover_mass,
        q_entropy=q_entropy,
        uniform_excess=uniform_excess,
        source_saving=source_saving,
        source_bill=source_bill,
        source_margin=source_margin,
        top25_mass=sum(q[index] for index in top25),
        future_lift=expectation(q, future_values) - uniform_future,
    )


def baseline_future_values(
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[float], set[int], float]:
    edges, maxes = build_uniform_edges(block_bits, max_arity, depth_bits, seed)
    _, best_raw = domain_masses(block_bits, atoms, max_arity, edges, maxes)
    raw_bits = block_bits * atoms
    values = [raw_bits + math.log2(value) if value > 0.0 else -raw_bits for value in best_raw]
    top_count = max(1, len(values) // 4)
    top25 = set(sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:top_count])
    uniform_future = sum(values) / len(values)
    return values, top25, uniform_future


def run_sweep() -> list[LawRow]:
    block_bits = 1
    atoms = 12
    max_arity = 5
    depth_bits = 8
    profiles = local_fertility_profiles(block_bits, max_arity, depth_bits, seed=95000)
    expected_cover_mass = cover_mass_from_record_weights(max_arity, atoms, depth_bits)
    future_values, top25, uniform_future = baseline_future_values(
        block_bits,
        atoms,
        max_arity,
        depth_bits,
        seed=95100,
    )
    laws = [
        Law("uniform", "uniform", 0.0),
        Law("fertile theta=0.5", "fertile", 0.5),
        Law("fertile theta=1.0", "fertile", 1.0),
        Law("fertile theta=2.0", "fertile", 2.0),
        Law("anti theta=1.0", "anti", 1.0),
    ]
    return [
        row_for_law(
            law,
            block_bits,
            atoms,
            max_arity,
            depth_bits,
            seed=95200 + index,
            profiles=profiles,
            expected_cover_mass=expected_cover_mass,
            future_values=future_values,
            top25=top25,
            uniform_future=uniform_future,
        )
        for index, law in enumerate(laws)
    ]


def print_rows(rows: list[LawRow]) -> None:
    print("== biased expander conservation ==")
    print("B=1,N=12,K=5,D=8 with exact V1 arities. Laws are fixed public maps.")
    print(
        f"{'law':<18} {'log2 Z':>9} {'sel log2Z':>10} {'Z error':>10} "
        f"{'H(Q)':>8} {'U excess':>9} {'src save':>9} {'src bill':>9} "
        f"{'margin':>9} {'top25':>8} {'future':>8}"
    )
    for row in rows:
        print(
            f"{row.law:<18} {math.log2(row.z_total):9.6f} "
            f"{math.log2(row.z_selected) if row.z_selected > 0 else float('-inf'):10.6f} "
            f"{row.cover_mass_error:10.3e} {row.q_entropy:8.4f} "
            f"{row.uniform_excess:9.6f} {row.source_saving:9.6f} "
            f"{row.source_bill:9.6f} {row.source_margin:9.6f} "
            f"{row.top25_mass:8.4f} {row.future_lift:8.4f}"
        )
    print()


def print_reading(rows: list[LawRow]) -> None:
    log2_values = {round(math.log2(row.z_total), 12) for row in rows}
    print("== reading ==")
    print(
        "Biased seed expansion can move Q mass toward future-fertile strings: "
        "the top25/future columns change. But total whole-cover Kraft mass is "
        f"conserved across these fixed maps (distinct log2 Z values={len(log2_values)} "
        "after rounding)."
    )
    print(
        "For a matching non-uniform source P=Q, any apparent source-shaped win "
        "must be compared with the source-shape bill raw_bits-H(Q); the recursive "
        "margin is exactly log2 Z. In this paid V1 toy both source_saving and "
        "log2 Z are negative. For uniform inputs, U excess is non-negative, so "
        "the honest raw/Q mixture would choose raw."
    )
    print(
        "Therefore a biology-like biased native generator is useful only if the "
        "system already has a real public source/developmental law to spend. It "
        "does not by itself create the missing arbitrary-content total-cover "
        "compression channel."
    )


def main() -> None:
    rows = run_sweep()
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
