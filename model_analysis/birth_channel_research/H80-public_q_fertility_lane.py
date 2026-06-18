#!/usr/bin/env python3
"""H80 - exact public-Q fertility lane profiler.

H77 tested one exact class: top 10% by latent whole-cover score log2(Q/U).
H80 sweeps public class sizes on the same finite H74 domain and reports:

* value lift: E_U[score | F] - E_U[score]
* Q-source concentration: Q(F)
* target threshold c*
* recursive p_FF required when the outside/background rate is uniform f
* public lane loss for d-choice placement
* shuffled-class negative controls

This is not a compressor. It is a finite exact profiler for the only surviving
source/fertility lane: a predeclared public class law with uniform controls.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)
build_edge_weights = _h74.build_edge_weights
dp_mass_for_word = _h74.dp_mass_for_word


def lane_hit_fraction(fraction: float, choices: int) -> float:
    return 1.0 - (1.0 - fraction) ** choices


def lane_loss(fraction: float, choices: int) -> float:
    return -math.log2(lane_hit_fraction(fraction, choices))


def min_p_ff(c_star: float, p_of: float) -> float:
    if c_star <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


@dataclass(frozen=True)
class Domain:
    block_bits: int
    atoms: int
    max_arity: int
    depth_bits: int
    seed: int
    q: list[float]
    scores: list[float]

    @property
    def raw_bits(self) -> int:
        return self.block_bits * self.atoms

    @property
    def uniform_mean_score(self) -> float:
        return sum(self.scores) / len(self.scores)

    @property
    def q_mean_score(self) -> float:
        return sum(q_value * score for q_value, score in zip(self.q, self.scores))


@dataclass(frozen=True)
class Target:
    name: str
    bits_per_atom: float


TARGETS = [
    Target("zero", 0.0),
    Target("H59 scaled", 0.053411 / 384.0),
    Target("H58 scaled", 0.229195 / 384.0),
    Target("H7 scaled", 0.011929),
]


@dataclass(frozen=True)
class ClassRow:
    fraction: float
    count: int
    q_mass: float
    mu_f: float
    mu_o: float
    lift_over_uniform: float
    d16_lane_loss: float
    d64_lane_loss: float
    shuffled_lift_avg: float
    shuffled_lift_max: float


@dataclass(frozen=True)
class TargetRow:
    fraction: float
    target: str
    target_bits_per_word: float
    c_star: float
    q_mass: float
    q_source_crosses: bool
    p_ff_needed_uniform_bg: float
    d16_lane_loss: float
    d64_lane_loss: float
    verdict: str


def exact_domain(
    block_bits: int = 1,
    atoms: int = 12,
    max_arity: int = 6,
    depth_bits: int = 8,
    seed: int = 75,
) -> Domain:
    domain_size = 1 << (block_bits * atoms)
    edge_weights, edge_maxes = build_edge_weights(block_bits, max_arity, depth_bits, seed)
    q_raw = [
        dp_mass_for_word(word, atoms, block_bits, max_arity, edge_weights, edge_maxes)[0]
        for word in range(domain_size)
    ]
    z_mass = sum(q_raw)
    if z_mass <= 0.0:
        raise RuntimeError("zero Q mass")
    uniform_probability = 1.0 / domain_size
    q = [value / z_mass for value in q_raw]
    if any(value <= 0.0 for value in q):
        raise RuntimeError("H80 expects positive Q mass for every tiny-domain word")
    scores = [math.log2(value / uniform_probability) for value in q]
    return Domain(block_bits, atoms, max_arity, depth_bits, seed, q, scores)


def top_class_indices(scores: list[float], fraction: float) -> list[int]:
    count = max(1, round(fraction * len(scores)))
    return sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:count]


def bottom_class_indices(scores: list[float], fraction: float) -> list[int]:
    count = max(1, round(fraction * len(scores)))
    return sorted(range(len(scores)), key=lambda index: scores[index])[:count]


def positive_class_indices(scores: list[float]) -> list[int]:
    return [index for index, score in enumerate(scores) if score > 0.0]


def row_for_indices(domain: Domain, indices: list[int], shuffle_trials: int = 128) -> ClassRow:
    f_set = set(indices)
    count = len(indices)
    f = count / len(domain.scores)
    q_mass = sum(domain.q[index] for index in indices)
    mu_f = sum(domain.scores[index] for index in indices) / count
    outside = [index for index in range(len(domain.scores)) if index not in f_set]
    mu_o = sum(domain.scores[index] for index in outside) / len(outside)
    lift = mu_f - domain.uniform_mean_score

    rng = random.Random(80080 + count)
    shuffled_lifts: list[float] = []
    population = list(range(len(domain.scores)))
    for _ in range(shuffle_trials):
        sample = rng.sample(population, count)
        shuffled_mu = sum(domain.scores[index] for index in sample) / count
        shuffled_lifts.append(shuffled_mu - domain.uniform_mean_score)

    return ClassRow(
        fraction=f,
        count=count,
        q_mass=q_mass,
        mu_f=mu_f,
        mu_o=mu_o,
        lift_over_uniform=lift,
        d16_lane_loss=lane_loss(f, 16),
        d64_lane_loss=lane_loss(f, 64),
        shuffled_lift_avg=sum(shuffled_lifts) / len(shuffled_lifts),
        shuffled_lift_max=max(shuffled_lifts),
    )


def class_row(domain: Domain, fraction: float, shuffle_trials: int = 128) -> ClassRow:
    return row_for_indices(domain, top_class_indices(domain.scores, fraction), shuffle_trials)


def target_rows(domain: Domain, classes: list[ClassRow]) -> list[TargetRow]:
    rows: list[TargetRow] = []
    for cls in classes:
        for target in TARGETS:
            target_word = target.bits_per_atom * domain.atoms
            if cls.mu_f == cls.mu_o:
                c_star = math.inf
            else:
                c_star = (target_word - cls.mu_o) / (cls.mu_f - cls.mu_o)
            required = min_p_ff(c_star, cls.fraction) if math.isfinite(c_star) else 1.0
            q_crosses = cls.q_mass >= c_star
            if cls.fraction >= c_star:
                verdict = "uniform class mass already enough"
            elif q_crosses:
                verdict = "Q-source concentration crosses"
            elif required >= 1.0:
                verdict = "needs near-closed F retention"
            else:
                verdict = "needs measured F retention"
            rows.append(
                TargetRow(
                    fraction=cls.fraction,
                    target=target.name,
                    target_bits_per_word=target_word,
                    c_star=c_star,
                    q_mass=cls.q_mass,
                    q_source_crosses=q_crosses,
                    p_ff_needed_uniform_bg=required,
                    d16_lane_loss=cls.d16_lane_loss,
                    d64_lane_loss=cls.d64_lane_loss,
                    verdict=verdict,
                )
            )
    return rows


def print_domain(domain: Domain) -> None:
    print("== exact public-Q domain ==")
    print(
        f"B={domain.block_bits}, N={domain.atoms}, K={domain.max_arity}, "
        f"D={domain.depth_bits}, domain={len(domain.q)}"
    )
    print(f"raw bits:                 {domain.raw_bits:.6f}")
    print(f"E_U log2(Q/U):            {domain.uniform_mean_score:.6f}")
    print(f"uniform excess bits:      {-domain.uniform_mean_score:.6f}")
    print(f"E_Q log2(Q/U):            {domain.q_mean_score:.6f}")
    print(f"Q-source saving bits:     {domain.q_mean_score:.6f}")
    print()


def print_class_rows(rows: list[ClassRow]) -> None:
    print("== public high-Q class sweep ==")
    print(
        f"{'f':>7} {'count':>6} {'Q(F)':>9} {'mu_F':>9} {'mu_O':>9} "
        f"{'lift':>9} {'lane16':>8} {'lane64':>8} "
        f"{'shuf avg':>9} {'shuf max':>9}"
    )
    for row in rows:
        print(
            f"{row.fraction:7.3f} {row.count:6d} {row.q_mass:9.4f} "
            f"{row.mu_f:9.3f} {row.mu_o:9.3f} {row.lift_over_uniform:9.3f} "
            f"{row.d16_lane_loss:8.3f} {row.d64_lane_loss:8.3f} "
            f"{row.shuffled_lift_avg:9.3f} {row.shuffled_lift_max:9.3f}"
        )
    print()


def print_special_controls(domain: Domain) -> None:
    print("== public threshold and bottom controls ==")
    specials = [
        ("F_positive Q>U", row_for_indices(domain, positive_class_indices(domain.scores))),
        ("top 25%", row_for_indices(domain, top_class_indices(domain.scores, 0.25))),
        ("bottom 25%", row_for_indices(domain, bottom_class_indices(domain.scores, 0.25))),
    ]
    print(
        f"{'class':<16} {'f':>7} {'count':>6} {'Q(F)':>9} {'mu_F':>9} "
        f"{'mu_O':>9} {'lift':>9} {'lane16':>8} {'shuf max':>9}"
    )
    for label, row in specials:
        print(
            f"{label:<16} {row.fraction:7.3f} {row.count:6d} "
            f"{row.q_mass:9.4f} {row.mu_f:9.3f} {row.mu_o:9.3f} "
            f"{row.lift_over_uniform:9.3f} {row.d16_lane_loss:8.3f} "
            f"{row.shuffled_lift_max:9.3f}"
        )
    print()


def print_target_rows(rows: list[TargetRow]) -> None:
    print("== target thresholds by class size ==")
    print(
        "Targets are scaled to this finite word as bits_per_atom * N. "
        "Q-source crossing is source-shaped evidence, not an all-data claim."
    )
    print(
        f"{'f':>7} {'target':<11} {'t_word':>8} {'c*':>8} {'Q(F)':>9} "
        f"{'pFF need':>9} {'lane16':>8} {'lane64':>8} {'verdict':<34}"
    )
    for row in rows:
        if row.target in ("zero", "H58 scaled", "H7 scaled") and row.fraction in (
            0.030029296875,
            0.10009765625,
            0.250,
            0.500,
        ):
            print(
                f"{row.fraction:7.3f} {row.target:<11} "
                f"{row.target_bits_per_word:8.4f} {row.c_star:8.4f} "
                f"{row.q_mass:9.4f} {row.p_ff_needed_uniform_bg:9.4f} "
                f"{row.d16_lane_loss:8.3f} {row.d64_lane_loss:8.3f} "
                f"{row.verdict:<34}"
            )
    print()


def print_frontier(rows: list[TargetRow]) -> None:
    print("== nearest source-shaped frontier ==")
    for target in ("zero", "H58 scaled", "H7 scaled"):
        target_rows_for_name = [row for row in rows if row.target == target]
        best_q = max(target_rows_for_name, key=lambda row: row.q_mass - row.c_star)
        best_retention = min(target_rows_for_name, key=lambda row: row.p_ff_needed_uniform_bg)
        print(
            f"{target}: best Q(F)-c* at f={best_q.fraction:.3f}: "
            f"{best_q.q_mass - best_q.c_star:+.4f}; "
            f"lowest pFF need at f={best_retention.fraction:.3f}: "
            f"{best_retention.p_ff_needed_uniform_bg:.4f}"
        )
    print()


def main() -> None:
    domain = exact_domain()
    fractions = (0.01, 0.025, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50, 0.75)
    classes = [class_row(domain, fraction) for fraction in fractions]
    rows = target_rows(domain, classes)
    print_domain(domain)
    print_class_rows(classes)
    print_special_controls(domain)
    print_target_rows(rows)
    print_frontier(rows)
    print("== reading ==")
    print(
        "A public high-Q class can be a real source-shaped lane: Q(F) can exceed "
        "the c* needed to beat tiny target gaps. The uniform control is still "
        "negative by D(U||Q), and shuffled classes lose the value lift. This "
        "does not solve roughly-all uniform recursion; it identifies the exact "
        "public source/fertility row a real stateless mechanism would need to "
        "maintain without witness-choice leakage."
    )


if __name__ == "__main__":
    main()
