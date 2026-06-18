#!/usr/bin/env python3
"""H90 - witness Kraft variational bound.

H89 showed that score-tilted and even oracle-saving soft laws stay negative
when measured against actual selected witness costs. H90 proves the exact
finite-domain reason.

Let U be uniform over M raw words and let a public witness family assign each
word x a best witness Kraft weight w(x)=2^-cost(x). The actual saving is:

    S(x) = log2(M) + log2 w(x)

For any public source/output law P over the same words:

    E_P[S] - D(P||U) <= log2(sum_x w(x))

with equality at P*(x) = w(x) / sum_y w(y).

So if the selected-witness Kraft mass Z_best=sum_x w_best(x) is below 1, no
public native source law over that fixed witness family can have a positive
source-cycle margin. The same statement applies to a collective/total witness
weight Q_raw(x) with Z_total=sum_x Q_raw(x).
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H89_PATH = Path(__file__).resolve().with_name("H89-actual_witness_savings.py")
_h89_spec = importlib.util.spec_from_file_location("h89_actual_witness_savings", H89_PATH)
if _h89_spec is None or _h89_spec.loader is None:
    raise RuntimeError("could not load H89 actual witness kernel")
_h89 = importlib.util.module_from_spec(_h89_spec)
sys.modules[_h89_spec.name] = _h89
_h89_spec.loader.exec_module(_h89)


@dataclass(frozen=True)
class BoundRow:
    name: str
    kraft_mass: float
    variational_bound: float
    equality_entropy: float
    equality_delta: float
    equality_expected_saving: float
    positive_fraction: float
    max_saving: float


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


def bound_row(name: str, weights: list[float], raw_bits: int) -> BoundRow:
    z_mass = sum(weights)
    if z_mass <= 0.0:
        raise ValueError("Kraft mass must be positive")
    law = [weight / z_mass for weight in weights]
    savings = [raw_bits + math.log2(weight) for weight in weights]
    h_law = entropy(law)
    delta = raw_bits - h_law
    expected_saving = expectation(law, savings)
    return BoundRow(
        name=name,
        kraft_mass=z_mass,
        variational_bound=math.log2(z_mass),
        equality_entropy=h_law,
        equality_delta=delta,
        equality_expected_saving=expected_saving,
        positive_fraction=sum(1 for saving in savings if saving > 0.0) / len(savings),
        max_saving=max(savings),
    )


def print_proof() -> None:
    print("== proof sketch ==")
    print("For S(x)=log2(M)+log2 w(x) and U(x)=1/M:")
    print("  E_P[S] - D(P||U)")
    print("= sum_x P(x)[log2(M)+log2 w(x)] - sum_x P(x)log2(P(x)/U(x))")
    print("= sum_x P(x)log2(w(x)/P(x))")
    print("= log2 Z - D(P || w/Z), where Z=sum_x w(x)")
    print("<= log2 Z, with equality at P=w/Z.")
    print()


def print_rows(rows: list[BoundRow]) -> None:
    print("== witness-family variational bounds ==")
    print(
        f"{'family':<18} {'Z':>12} {'log2 Z':>10} {'H(P*)':>10} "
        f"{'D(P*||U)':>10} {'E_P*S':>10} {'pos frac':>9} {'max S':>8}"
    )
    for row in rows:
        print(
            f"{row.name:<18} {row.kraft_mass:12.9f} {row.variational_bound:10.6f} "
            f"{row.equality_entropy:10.6f} {row.equality_delta:10.6f} "
            f"{row.equality_expected_saving:10.6f} {row.positive_fraction:9.6f} "
            f"{row.max_saving:8.3f}"
        )
    print()


def print_reading(best: BoundRow, total: BoundRow) -> None:
    print("== reading ==")
    print(
        "The H89 best-cover oracle was not merely under-tuned. For the fixed "
        f"selected-witness family, the best possible public source law is capped "
        f"at log2 Z_best={best.variational_bound:.6f} bits/word. Because that is "
        "negative, no soft native grammar over the same selected witnesses can "
        "cross without changing the witness family or adding paid information."
    )
    print(
        f"The collective all-description family has a larger cap, log2 Z_total="
        f"{total.variational_bound:.6f}, but it is still negative in this exact "
        "domain. The next constructive target is therefore not a better tilt; "
        "it is a mechanism that increases the honest witness Kraft mass above "
        "1, or a separate public invariant whose own visible-state bill is paid."
    )


def main() -> None:
    domain = _h89.exact_witness_domain()
    best_weights = [2.0 ** (-cost) for cost in domain.best_costs]
    # q in H89 is normalized total mass. Recover raw total weights via Z_total.
    total_weights = [probability * domain.z_total for probability in domain.q]
    best = bound_row("best selected", best_weights, domain.raw_bits)
    total = bound_row("all descriptions", total_weights, domain.raw_bits)
    print_proof()
    print_rows([best, total])
    print_reading(best, total)


if __name__ == "__main__":
    main()
