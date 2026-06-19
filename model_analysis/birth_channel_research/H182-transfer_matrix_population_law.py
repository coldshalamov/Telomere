#!/usr/bin/env python3
"""H182 - public transfer-matrix population law.

This kernel tests the strongest remaining "DNA-like" no-tax shape:

    A decoder-visible record/class population evolves under a public transfer
    law whose fertile classes keep producing more future exact-witness supply.

For a fixed public class law, the weighted transfer matrix W carries the full
honest accounting.  W_ij is the total paid witness/Kraft mass for a class-i
item to emit class-j next-layer items, after all arity, witness, width, rank,
selector, and filter costs that the law claims to pay.

The asymptotic no-tax population margin is:

    log2(rho(W))

where rho(W) is the Perron spectral radius.  If every row has mass <= 1, then
rho(W) <= 1, so a valid fixed public law has no positive roughly-all-data
drift.  Any row with rho(W)>1 is an overfull law unless the input/source is
actually restricted or generated, in which case the source/reachable tax must
be paid separately.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


LN2 = math.log(2.0)
TARGET_GAP_BITS_PER_RECORD = 8.112500


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


def mat_vec(matrix: tuple[tuple[float, ...], ...], vector: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(sum(row[j] * vector[j] for j in range(len(vector))) for row in matrix)


def spectral_radius(matrix: tuple[tuple[float, ...], ...]) -> float:
    n = len(matrix)
    if n == 0:
        return 0.0
    vector = tuple(1.0 / n for _ in range(n))
    radius = 0.0
    for _ in range(512):
        new_vector = mat_vec(matrix, vector)
        norm = max(new_vector)
        if norm <= 0.0:
            return 0.0
        new_vector = tuple(value / norm for value in new_vector)
        if abs(norm - radius) < 1e-14:
            radius = norm
            break
        radius = norm
        vector = new_vector
    return radius


def row_sums(matrix: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    return tuple(sum(row) for row in matrix)


def column_sums(matrix: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    n = len(matrix)
    return tuple(sum(matrix[i][j] for i in range(n)) for j in range(n))


def scale_matrix(matrix: tuple[tuple[float, ...], ...], scale: float) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(scale * value for value in row) for row in matrix)


def rank_one_matrix(weights: tuple[float, ...], rows: int | None = None) -> tuple[tuple[float, ...], ...]:
    count = rows if rows is not None else len(weights)
    return tuple(weights for _ in range(count))


def kl_bits(p: tuple[float, ...], q: tuple[float, ...]) -> float:
    total = 0.0
    for pi, qi in zip(p, q, strict=True):
        if pi > 0.0:
            total += pi * math.log2(pi / qi)
    return total


def normalize(values: tuple[float, ...]) -> tuple[float, ...]:
    total = sum(values)
    if total <= 0.0:
        raise ValueError("cannot normalize nonpositive vector")
    return tuple(value / total for value in values)


def independent_z(background: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum(f * (2.0**value) for f, value in zip(background, values, strict=True))


def equality_distribution(background: tuple[float, ...], values: tuple[float, ...]) -> tuple[float, ...]:
    z = independent_z(background, values)
    return tuple(f * (2.0**value) / z for f, value in zip(background, values, strict=True))


def value_at(population: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum(p * v for p, v in zip(population, values, strict=True))


@dataclass(frozen=True)
class Law:
    name: str
    classes: tuple[str, ...]
    matrix: tuple[tuple[float, ...], ...]
    note: str


@dataclass(frozen=True)
class LawRow:
    name: str
    rho: float
    log2_rho: float
    max_row_sum: float
    max_col_sum: float
    valid_row_mass: bool
    target_margin: float
    verdict: str
    note: str


@dataclass(frozen=True)
class IndependentRow:
    name: str
    z: float
    log2_z: float
    equality_population: tuple[float, ...]
    equality_kl: float
    equality_value: float
    equality_net: float
    unpaid_shuffle_net: float
    verdict: str


@dataclass(frozen=True)
class GeneratedRow:
    root_bits: int
    phenotype_bits: int
    header_bits: int
    inside_gain: int
    reachable_tax: int
    uniform_net: int


def exact_arity_kraft_v1() -> float:
    return sum(2.0 ** (-costs.ARITY_BITS[arity]) for arity in range(1, 6))


def fixed_arity_kraft(max_arity: int) -> float:
    width = (max_arity - 1).bit_length()
    return max_arity * (2.0 ** (-width))


def independent_laws() -> list[tuple[str, tuple[float, ...], tuple[float, ...]]]:
    rare = (0.9, 0.1)
    fertile_value = 3.0
    balanced_other = math.log2((1.0 - rare[1] * (2.0**fertile_value)) / rare[0])
    return [
        ("balanced_rare_fertile", rare, (balanced_other, fertile_value)),
        ("overfull_rare_fertile", rare, (0.0, fertile_value)),
        ("strict_saving_valid", (0.5, 0.5), (-1.0, -1.0)),
        ("fixed_flat_critical", (0.5, 0.5), (0.0, 0.0)),
    ]


def law_rows() -> list[Law]:
    v1_kraft = exact_arity_kraft_v1()
    fixed_k8 = fixed_arity_kraft(8)
    rare = (0.9, 0.1)
    balanced_other = math.log2((1.0 - rare[1] * 8.0) / rare[0])
    balanced_weights = (rare[0] * (2.0**balanced_other), rare[1] * 8.0)
    overfull_weights = (rare[0], rare[1] * 8.0)
    closed_valid = ((0.05, 0.00), (0.00, 1.00))
    closed_overfull = ((0.05, 0.00), (0.00, 1.08))
    return [
        Law(
            "v1_flat_rank_one",
            ("any", "any"),
            scale_matrix(rank_one_matrix((0.5, 0.5)), v1_kraft),
            "exact V1 arity Kraft mass, flat witness",
        ),
        Law(
            "fixed_K8_flat",
            ("any", "any"),
            scale_matrix(rank_one_matrix((0.5, 0.5)), fixed_k8),
            "complete fixed arity, flat critical witness",
        ),
        Law(
            "fixed_K8_strict_s1",
            ("any", "any"),
            scale_matrix(rank_one_matrix((0.5, 0.5)), fixed_k8 * 0.5),
            "one paid bit saved per record",
        ),
        Law(
            "balanced_rare_rank_one",
            ("ordinary", "fertile"),
            rank_one_matrix(balanced_weights),
            "fertile class has +3 bits but ordinary class is penalized so Z=1",
        ),
        Law(
            "overfull_rare_rank_one",
            ("ordinary", "fertile"),
            rank_one_matrix(overfull_weights),
            "same +3 fertile boost without paying complement mass",
        ),
        Law(
            "closed_fertile_valid",
            ("ordinary", "fertile"),
            closed_valid,
            "public closed fertile SCC at exactly unit mass",
        ),
        Law(
            "closed_fertile_overfull",
            ("ordinary", "fertile"),
            closed_overfull,
            "closed fertile SCC with hidden overfull mass",
        ),
    ]


def classify_law(rho: float, max_row: float) -> str:
    if rho > 1.0 + 1e-12 and max_row <= 1.0 + 1e-12:
        return "BUG: positive with valid row mass"
    if rho > 1.0 + 1e-12:
        return "positive only by overfull mass"
    if abs(rho - 1.0) <= 1e-12:
        return "critical; no strict negative drift"
    return "valid negative drift"


def build_law_rows() -> list[LawRow]:
    rows: list[LawRow] = []
    for law in law_rows():
        rho = spectral_radius(law.matrix)
        logs = math.log2(rho) if rho > 0.0 else float("-inf")
        rows.append(
            LawRow(
                name=law.name,
                rho=rho,
                log2_rho=logs,
                max_row_sum=max(row_sums(law.matrix)),
                max_col_sum=max(column_sums(law.matrix)),
                valid_row_mass=max(row_sums(law.matrix)) <= 1.0 + 1e-12,
                target_margin=logs - TARGET_GAP_BITS_PER_RECORD,
                verdict=classify_law(rho, max(row_sums(law.matrix))),
                note=law.note,
            )
        )
    return rows


def build_independent_rows() -> list[IndependentRow]:
    rows: list[IndependentRow] = []
    for name, background, values in independent_laws():
        z = independent_z(background, values)
        log2_z = math.log2(z)
        equality = equality_distribution(background, values)
        eq_kl = kl_bits(equality, background)
        eq_value = value_at(equality, values)
        eq_net = eq_value - eq_kl
        shuffled_values = tuple(reversed(values))
        shuffled_z = independent_z(background, shuffled_values)
        unpaid_shuffle_net = math.log2(shuffled_z)
        if log2_z > 1e-12:
            verdict = "positive only if source/overfull tax paid"
        elif abs(log2_z) <= 1e-12:
            verdict = "balanced; KL cancels visible value"
        else:
            verdict = "negative"
        rows.append(
            IndependentRow(
                name=name,
                z=z,
                log2_z=log2_z,
                equality_population=equality,
                equality_kl=eq_kl,
                equality_value=eq_value,
                equality_net=eq_net,
                unpaid_shuffle_net=unpaid_shuffle_net,
                verdict=verdict,
            )
        )
    return rows


def generated_rows() -> list[GeneratedRow]:
    rows: list[GeneratedRow] = []
    for root_bits, phenotype_bits, header_bits in ((12, 64 * 128, 0), (24, 128 * 128, 64)):
        inside_gain = phenotype_bits - root_bits - header_bits
        reachable_tax = phenotype_bits - root_bits
        rows.append(
            GeneratedRow(
                root_bits=root_bits,
                phenotype_bits=phenotype_bits,
                header_bits=header_bits,
                inside_gain=inside_gain,
                reachable_tax=reachable_tax,
                uniform_net=inside_gain - reachable_tax,
            )
        )
    return rows


def random_substochastic_law(size: int, rng: random.Random) -> tuple[tuple[float, ...], ...]:
    rows: list[tuple[float, ...]] = []
    for _ in range(size):
        raw = [rng.random() for _ in range(size)]
        total = sum(raw)
        row_budget = rng.random()
        rows.append(tuple(row_budget * value / total for value in raw))
    return tuple(rows)


def print_law_table() -> None:
    print("== H182 transfer-matrix population law ==")
    print(
        "W_ij is paid public witness/Kraft mass from visible class i to class j; "
        "asymptotic margin is log2 spectral radius."
    )
    print(
        f"{'law':<26} {'rho':>10} {'log2rho':>10} {'maxRow':>9} "
        f"{'maxCol':>9} {'valid?':>7} {'targetGap':>10} {'verdict':<34} {'note'}"
    )
    for row in build_law_rows():
        print(
            f"{row.name:<26} {fmt(row.rho):>10} {fmt(row.log2_rho):>10} "
            f"{fmt(row.max_row_sum):>9} {fmt(row.max_col_sum):>9} "
            f"{str(row.valid_row_mass):>7} {fmt(row.target_margin):>10} "
            f"{row.verdict:<34} {row.note}"
        )


def print_independent_table() -> None:
    print()
    print("== independent visible-class variational check ==")
    print(
        "For background f and class values v, max no-tax margin is "
        "log2(sum_i f_i 2^v_i)."
    )
    print(
        f"{'case':<26} {'Z':>10} {'log2Z':>10} {'eqPop':>18} "
        f"{'KL_eq':>10} {'V_eq':>10} {'net_eq':>10} {'unpaidShuf':>10} {'verdict':<36}"
    )
    for row in build_independent_rows():
        eq_pop = ",".join(fmt(value) for value in row.equality_population)
        print(
            f"{row.name:<26} {fmt(row.z):>10} {fmt(row.log2_z):>10} "
            f"{eq_pop:>18} {fmt(row.equality_kl):>10} "
            f"{fmt(row.equality_value):>10} {fmt(row.equality_net):>10} "
            f"{fmt(row.unpaid_shuffle_net):>10} {row.verdict:<36}"
        )
    print("unpaidShuf deliberately reuses values under the wrong class masses; positive rows are overfull.")


def print_random_controls(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    max_rho = 0.0
    max_row = 0.0
    for _ in range(args.random_controls):
        matrix = random_substochastic_law(args.random_size, rng)
        max_rho = max(max_rho, spectral_radius(matrix))
        max_row = max(max_row, max(row_sums(matrix)))
    print()
    print("== same-visible random substochastic controls ==")
    print(
        f"controls={args.random_controls} size={args.random_size} "
        f"max_rho={fmt(max_rho)} max_row={fmt(max_row)} "
        f"log2(max_rho)={fmt(math.log2(max_rho) if max_rho > 0 else float('-inf'))}"
    )


def print_generated_table() -> None:
    print()
    print("== generated/reachable regime ledger ==")
    print(
        "Inside a generated class, roots can be tiny. For arbitrary uniform data, "
        "membership in that reachable set costs the same phenotype-minus-root bits."
    )
    print(
        f"{'G':>5} {'phenotype':>10} {'header':>7} {'inside_gain':>12} "
        f"{'reach_tax':>10} {'uniform_net':>11}"
    )
    for row in generated_rows():
        print(
            f"{row.root_bits:5d} {row.phenotype_bits:10d} {row.header_bits:7d} "
            f"{row.inside_gain:12d} {row.reachable_tax:10d} {row.uniform_net:11d}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A frozen public class law has no-tax recurrent margin log2 rho(W).")
    print("If every row of W has paid mass <= 1, then rho(W) <= 1.")
    print("Positive rho therefore requires overfull hidden mass, real source bias,")
    print("or a generated/reachable restriction whose membership tax is paid.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-controls", type=int, default=1000)
    parser.add_argument("--random-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=182182)
    args = parser.parse_args()

    print_law_table()
    print_independent_table()
    print_random_controls(args)
    print_generated_table()
    print_theorem()


if __name__ == "__main__":
    main()
