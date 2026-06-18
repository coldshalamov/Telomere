#!/usr/bin/env python3
"""H89 - actual witness savings under soft native laws.

H86-H88 showed that a frozen public soft-law grammar can be parseable and can
score well under V(x)=log2(Q(x)/U(x)). H89 tests the missing implication:

    does V-lift become actual Telomere selected-record savings?

For each word in the exact H80/H74 finite domain, compute the actual best
cover cost from the H74 max-product DP:

    best_cost(x) = -log2(max_description_weight(x))
    paid_saving(x) = raw_bits - best_cost(x)

Then evaluate soft laws P_theta built from the H80 value score. A source-shaped
cycle with an ideal distribution matcher would need:

    E_P[paid_saving] - D(P||U) > 0

and a finite frozen type-class matcher needs:

    E_Phat[paid_saving] - finite_bill > 0

Uniform and shuffled controls catch cases where the score lift is not tied to
actual paid witness savings.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)


@dataclass(frozen=True)
class WitnessDomain:
    block_bits: int
    atoms: int
    max_arity: int
    depth_bits: int
    seed: int
    q: list[float]
    scores: list[float]
    paid_savings: list[float]
    best_costs: list[float]
    z_total: float
    z_best: float

    @property
    def raw_bits(self) -> int:
        return self.block_bits * self.atoms


@dataclass(frozen=True)
class IdealRow:
    name: str
    delta: float
    entropy_bits: float
    score_lift: float
    actual_saving: float
    actual_lift: float
    cycle_margin: float
    lift_margin: float
    top25_mass: float


@dataclass(frozen=True)
class FiniteRow:
    theta: float
    block_len: int
    active_symbols: int
    finite_bill: float
    score_lift: float
    actual_saving: float
    cycle_margin: float
    top25_mass: float


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


def tilted_law(values: list[float], theta: float) -> list[float]:
    exponents = [theta * value for value in values]
    max_exponent = max(exponents)
    weights = [2.0 ** (exponent - max_exponent) for exponent in exponents]
    total = sum(weights)
    return [weight / total for weight in weights]


def counts_for_law(probabilities: list[float], block_len: int) -> list[int]:
    scaled = [block_len * p for p in probabilities]
    counts = [math.floor(value) for value in scaled]
    remainder = block_len - sum(counts)
    order = sorted(range(len(probabilities)), key=lambda i: scaled[i] - counts[i], reverse=True)
    for index in order[:remainder]:
        counts[index] += 1
    return counts


def log2_factorial(n: int) -> float:
    return math.lgamma(n + 1) / math.log(2.0)


def log2_type_size(counts: list[int]) -> float:
    total = sum(counts)
    return log2_factorial(total) - sum(log2_factorial(count) for count in counts if count)


def law_on_counts(counts: list[int]) -> list[float]:
    total = sum(counts)
    return [count / total for count in counts]


def top_indices(values: list[float], fraction: float) -> list[int]:
    count = max(1, round(fraction * len(values)))
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:count]


def exact_witness_domain(
    block_bits: int = 1,
    atoms: int = 12,
    max_arity: int = 6,
    depth_bits: int = 8,
    seed: int = 75,
) -> WitnessDomain:
    domain_size = 1 << (block_bits * atoms)
    edge_weights, edge_maxes = _h74.build_edge_weights(block_bits, max_arity, depth_bits, seed)
    q_raw: list[float] = []
    best_raw: list[float] = []
    for word in range(domain_size):
        total, best = _h74.dp_mass_for_word(word, atoms, block_bits, max_arity, edge_weights, edge_maxes)
        q_raw.append(total)
        best_raw.append(best)
    z_total = sum(q_raw)
    z_best = sum(best_raw)
    if z_total <= 0.0 or any(value <= 0.0 for value in q_raw) or any(value <= 0.0 for value in best_raw):
        raise RuntimeError("H89 expects positive total and best mass for every word in this tiny domain")
    raw_bits = block_bits * atoms
    uniform_probability = 1.0 / domain_size
    q = [value / z_total for value in q_raw]
    scores = [math.log2(value / uniform_probability) for value in q]
    best_costs = [-math.log2(value) for value in best_raw]
    paid_savings = [raw_bits - cost for cost in best_costs]
    return WitnessDomain(
        block_bits=block_bits,
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
        q=q,
        scores=scores,
        paid_savings=paid_savings,
        best_costs=best_costs,
        z_total=z_total,
        z_best=z_best,
    )


def ideal_row(name: str, probabilities: list[float], domain: WitnessDomain, top25: list[int]) -> IdealRow:
    raw_bits = domain.raw_bits
    h_p = entropy(probabilities)
    delta = raw_bits - h_p
    uniform_score = sum(domain.scores) / len(domain.scores)
    uniform_saving = sum(domain.paid_savings) / len(domain.paid_savings)
    score_lift = expectation(probabilities, domain.scores) - uniform_score
    actual_saving = expectation(probabilities, domain.paid_savings)
    actual_lift = actual_saving - uniform_saving
    return IdealRow(
        name=name,
        delta=delta,
        entropy_bits=h_p,
        score_lift=score_lift,
        actual_saving=actual_saving,
        actual_lift=actual_lift,
        cycle_margin=actual_saving - delta,
        lift_margin=actual_lift - delta,
        top25_mass=sum(probabilities[index] for index in top25),
    )


def finite_row(theta: float, block_len: int, domain: WitnessDomain, top25: list[int]) -> FiniteRow:
    target = tilted_law(domain.scores, theta)
    counts = counts_for_law(target, block_len)
    empirical = law_on_counts(counts)
    log_type = log2_type_size(counts)
    payload_bits_per_word = math.floor(log_type) / block_len
    finite_bill = domain.raw_bits - payload_bits_per_word
    uniform_score = sum(domain.scores) / len(domain.scores)
    score_lift = expectation(empirical, domain.scores) - uniform_score
    actual_saving = expectation(empirical, domain.paid_savings)
    return FiniteRow(
        theta=theta,
        block_len=block_len,
        active_symbols=sum(1 for count in counts if count),
        finite_bill=finite_bill,
        score_lift=score_lift,
        actual_saving=actual_saving,
        cycle_margin=actual_saving - finite_bill,
        top25_mass=sum(empirical[index] for index in top25),
    )


def shuffled_control(
    probabilities: list[float],
    savings: list[float],
    delta_or_bill: float,
    trials: int = 256,
    seed: int = 89089,
) -> tuple[float, float]:
    rng = random.Random(seed)
    shuffled_margins: list[float] = []
    scratch = list(savings)
    for _ in range(trials):
        rng.shuffle(scratch)
        shuffled_margins.append(expectation(probabilities, scratch) - delta_or_bill)
    return sum(shuffled_margins) / len(shuffled_margins), max(shuffled_margins)


def print_domain(domain: WitnessDomain) -> None:
    uniform_saving = sum(domain.paid_savings) / len(domain.paid_savings)
    q_saving = expectation(domain.q, domain.paid_savings)
    print("== actual witness-savings domain ==")
    print(
        f"B={domain.block_bits}, N={domain.atoms}, K={domain.max_arity}, "
        f"D={domain.depth_bits}, domain={len(domain.q)}"
    )
    print(f"raw bits:                    {domain.raw_bits:.6f}")
    print(f"total-description Kraft Z:   {domain.z_total:.12e}")
    print(f"best-description Kraft Z:    {domain.z_best:.12e}")
    print(f"E_U paid_saving:             {uniform_saving:.6f}")
    print(f"E_Q paid_saving:             {q_saving:.6f}")
    print(f"positive-saving fraction:    {sum(1 for value in domain.paid_savings if value > 0.0) / len(domain.paid_savings):.6f}")
    print(f"best paid_saving:            {max(domain.paid_savings):.6f}")
    print(f"worst paid_saving:           {min(domain.paid_savings):.6f}")
    print()


def print_ideal_rows(domain: WitnessDomain, top25: list[int]) -> None:
    print("== ideal score-tilted laws, actual witness savings ==")
    print(
        f"{'law':<12} {'delta':>9} {'scoreLift':>10} {'actSave':>9} "
        f"{'actLift':>9} {'cycle':>9} {'lift-d':>9} {'top25':>9}"
    )
    rows = [
        ideal_row("uniform", [1.0 / len(domain.q)] * len(domain.q), domain, top25),
        *[
            ideal_row(f"th={theta:.2f}", tilted_law(domain.scores, theta), domain, top25)
            for theta in (0.05, 0.10, 0.30, 0.50, 0.90, 1.00, 1.05, 1.20)
        ],
        ideal_row("Q/native", domain.q, domain, top25),
    ]
    for row in rows:
        print(
            f"{row.name:<12} {row.delta:9.6f} {row.score_lift:10.6f} "
            f"{row.actual_saving:9.6f} {row.actual_lift:9.6f} "
            f"{row.cycle_margin:9.6f} {row.lift_margin:9.6f} {row.top25_mass:9.6f}"
        )
    print()


def print_finite_rows(domain: WitnessDomain, top25: list[int]) -> None:
    print("== finite frozen type-class laws, actual witness savings ==")
    print(
        f"{'theta':>6} {'m':>6} {'active':>7} {'bill':>9} "
        f"{'scoreLift':>10} {'actSave':>9} {'cycle':>9} {'top25':>9}"
    )
    for theta in (0.30, 0.50, 0.90, 1.00, 1.05):
        for block_len in (1024, 4096, 8192, 32768):
            row = finite_row(theta, block_len, domain, top25)
            print(
                f"{row.theta:6.2f} {row.block_len:6d} {row.active_symbols:7d} "
                f"{row.finite_bill:9.6f} {row.score_lift:10.6f} "
                f"{row.actual_saving:9.6f} {row.cycle_margin:9.6f} {row.top25_mass:9.6f}"
            )
        print()


def print_best_and_controls(domain: WitnessDomain, top25: list[int]) -> None:
    rows = [
        finite_row(theta / 100.0, block_len, domain, top25)
        for theta in range(1, 151)
        for block_len in (1024, 2048, 4096, 8192, 16384, 32768)
    ]
    best = max(rows, key=lambda row: row.cycle_margin)
    target = tilted_law(domain.scores, best.theta)
    counts = counts_for_law(target, best.block_len)
    empirical = law_on_counts(counts)
    shuffled_avg, shuffled_max = shuffled_control(empirical, domain.paid_savings, best.finite_bill)

    oracle_rows = [
        finite_oracle_row(theta / 100.0, block_len, domain, top25)
        for theta in range(1, 151)
        for block_len in (1024, 2048, 4096, 8192, 16384, 32768)
    ]
    oracle_best = max(oracle_rows, key=lambda row: row.cycle_margin)
    print("== best finite rows and controls ==")
    print(
        f"best score-law: theta={best.theta:.2f}, m={best.block_len}, "
        f"bill={best.finite_bill:.6f}, actual_saving={best.actual_saving:.6f}, "
        f"cycle={best.cycle_margin:.6f}, top25={best.top25_mass:.6f}"
    )
    print(
        f"shuffled savings at that law: avg_cycle={shuffled_avg:.6f}, "
        f"max_cycle={shuffled_max:.6f}"
    )
    print(
        f"best oracle-saving law: theta={oracle_best.theta:.2f}, m={oracle_best.block_len}, "
        f"bill={oracle_best.finite_bill:.6f}, actual_saving={oracle_best.actual_saving:.6f}, "
        f"cycle={oracle_best.cycle_margin:.6f}, top25={oracle_best.top25_mass:.6f}"
    )
    print()


def finite_oracle_row(theta: float, block_len: int, domain: WitnessDomain, top25: list[int]) -> FiniteRow:
    target = tilted_law(domain.paid_savings, theta)
    counts = counts_for_law(target, block_len)
    empirical = law_on_counts(counts)
    log_type = log2_type_size(counts)
    payload_bits_per_word = math.floor(log_type) / block_len
    finite_bill = domain.raw_bits - payload_bits_per_word
    uniform_score = sum(domain.scores) / len(domain.scores)
    score_lift = expectation(empirical, domain.scores) - uniform_score
    actual_saving = expectation(empirical, domain.paid_savings)
    return FiniteRow(
        theta=theta,
        block_len=block_len,
        active_symbols=sum(1 for count in counts if count),
        finite_bill=finite_bill,
        score_lift=score_lift,
        actual_saving=actual_saving,
        cycle_margin=actual_saving - finite_bill,
        top25_mass=sum(empirical[index] for index in top25),
    )


def print_reading() -> None:
    print("== reading ==")
    print(
        "H89 replaces the H86/H88 value score with actual best-cover record "
        "savings. A positive score-law cycle means the frozen soft grammar is "
        "not merely chasing a decorative Q score in this toy domain. A shuffled "
        "control near the same value would mean the apparent win is just the "
        "low-entropy source law, not score/savings alignment. Even a positive "
        "toy cycle remains source-shaped: it does not by itself prove roughly-"
        "all uniform compression over arbitrary many passes."
    )


def main() -> None:
    domain = exact_witness_domain()
    top25 = top_indices(domain.scores, 0.25)
    print_domain(domain)
    print_ideal_rows(domain, top25)
    print_finite_rows(domain, top25)
    print_best_and_controls(domain, top25)
    print_reading()


if __name__ == "__main__":
    main()
