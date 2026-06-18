#!/usr/bin/env python3
"""H83 - length-preserving relabeling ledger.

A scout proposed Kraft-preserving/native alphabet relabeling: keep the same
codeword lengths, but publicly permute labels so the visible native syntax lands
more often in H80's fertile class.

For a fixed source law Q and a fixed class F, a length-preserving relabeling is
just a permutation of visible words. This can move Q mass into F, but it cannot
create source mass. The best permutation puts the largest |F| probabilities in
F; if F is already the top-Q class, identity is optimal. If a profile chooses
among many relabelings after seeing a target/source, that profile identity is
visible state.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


H80_PATH = Path(__file__).resolve().with_name("H80-public_q_fertility_lane.py")
_h80_spec = importlib.util.spec_from_file_location("h80_public_q_fertility_lane", H80_PATH)
if _h80_spec is None or _h80_spec.loader is None:
    raise RuntimeError("could not load H80 public-Q fertility lane kernel")
_h80 = importlib.util.module_from_spec(_h80_spec)
sys.modules[_h80_spec.name] = _h80
_h80_spec.loader.exec_module(_h80)


def log2_factorial(n: int) -> float:
    return math.lgamma(n + 1) / math.log(2.0)


def log2_choose(n: int, k: int) -> float:
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


@dataclass(frozen=True)
class RelabelRow:
    class_name: str
    count: int
    fraction: float
    identity_q_mass: float
    optimal_q_mass: float
    worst_q_mass: float
    random_avg: float
    random_max: float
    identity_gap_to_opt: float
    profile_subset_bits: float
    c_star_h7: float
    best_possible_source_margin_h7: float | None
    verdict: str


def class_indices(domain, name: str) -> list[int]:
    if name == "top10":
        return _h80.top_class_indices(domain.scores, 0.10)
    if name == "top25":
        return _h80.top_class_indices(domain.scores, 0.25)
    if name == "F_positive":
        return _h80.positive_class_indices(domain.scores)
    if name == "bottom25":
        return _h80.bottom_class_indices(domain.scores, 0.25)
    if name == "random25":
        return random.Random(83025).sample(list(range(len(domain.q))), len(domain.q) // 4)
    raise ValueError(name)


def h7_c_star_for_indices(domain, indices: list[int]) -> tuple[float, bool]:
    row = _h80.row_for_indices(domain, indices)
    if row.mu_f <= row.mu_o:
        return math.inf, False
    target_word = 0.011929 * domain.atoms
    c_star = (target_word - row.mu_o) / (row.mu_f - row.mu_o)
    return c_star, 0.0 <= c_star <= 1.0


def relabel_row(domain, name: str, trials: int = 256) -> RelabelRow:
    indices = class_indices(domain, name)
    count = len(indices)
    total = len(domain.q)
    q_sorted = sorted(domain.q, reverse=True)
    q_ascending = list(reversed(q_sorted))
    identity_q = sum(domain.q[index] for index in indices)
    optimal_q = sum(q_sorted[:count])
    worst_q = sum(q_ascending[:count])
    rng = random.Random(83083 + count)
    random_masses: list[float] = []
    population = list(range(total))
    for _ in range(trials):
        sample = rng.sample(population, count)
        random_masses.append(sum(domain.q[index] for index in sample))
    c_star, valid_target = h7_c_star_for_indices(domain, indices)
    margin = optimal_q - c_star if valid_target else None
    if not valid_target:
        verdict = "invalid value-lift class"
    elif abs(identity_q - optimal_q) < 1e-12:
        verdict = "identity already optimal"
    elif optimal_q >= c_star and identity_q < c_star:
        verdict = "only best-profile relabel crosses"
    else:
        verdict = "relabeling changes placement only"
    return RelabelRow(
        class_name=name,
        count=count,
        fraction=count / total,
        identity_q_mass=identity_q,
        optimal_q_mass=optimal_q,
        worst_q_mass=worst_q,
        random_avg=sum(random_masses) / len(random_masses),
        random_max=max(random_masses),
        identity_gap_to_opt=optimal_q - identity_q,
        profile_subset_bits=log2_choose(total, count),
        c_star_h7=c_star,
        best_possible_source_margin_h7=margin,
        verdict=verdict,
    )


def print_rows(rows: list[RelabelRow]) -> None:
    print("== length-preserving relabeling ledger ==")
    print(
        "Optimal relabeling puts the largest |F| Q probabilities in F. "
        "Profile subset bits show how large the choose-F channel would be "
        "if the class/relabeling were selected rather than frozen."
    )
    print(
        f"{'class':<11} {'f':>7} {'id Q(F)':>9} {'opt Q(F)':>9} "
        f"{'worst':>9} {'rand avg':>9} {'rand max':>9} {'gap':>8} "
        f"{'log C':>9} {'c*H7':>8} {'opt-c*':>8} {'verdict':<28}"
    )
    for row in rows:
        c_star = "invalid" if not math.isfinite(row.c_star_h7) else f"{row.c_star_h7:8.4f}"
        margin = "invalid" if row.best_possible_source_margin_h7 is None else f"{row.best_possible_source_margin_h7:8.4f}"
        print(
            f"{row.class_name:<11} {row.fraction:7.3f} "
            f"{row.identity_q_mass:9.4f} {row.optimal_q_mass:9.4f} "
            f"{row.worst_q_mass:9.4f} {row.random_avg:9.4f} "
            f"{row.random_max:9.4f} {row.identity_gap_to_opt:8.4f} "
            f"{row.profile_subset_bits:9.1f} "
            f"{c_star:>8} {margin:>8} {row.verdict:<28}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Length-preserving relabeling can align a fixed source law with a fixed "
        "visible class, but it cannot create extra source mass. For top-Q "
        "classes, identity is already optimal. For bottom/random classes, an "
        "optimal relabeling is just choosing a different public profile or "
        "class; if selected adaptively, the profile channel is enormous. This "
        "keeps the native-syntax target alive only in the narrower form: a "
        "predeclared graded record law, not a relabeling chosen to make a row "
        "look fertile."
    )


def main() -> None:
    domain = _h80.exact_domain()
    rows = [relabel_row(domain, name) for name in ("top10", "top25", "F_positive", "bottom25", "random25")]
    print_rows(rows)
    print_reading()


if __name__ == "__main__":
    main()
