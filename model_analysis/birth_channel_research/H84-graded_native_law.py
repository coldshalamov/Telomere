#!/usr/bin/env python3
"""H84 - graded native law transition versus invariant recursion.

H81-H83 narrowed the target to a graded native record probability law. H84
tests the clean finite-domain version.

Let Q be H80's fertile public source law and let R_lambda be a tilted visible
law between uniform U and Q:

    R_lambda(x) proportional to U(x) * 2^(lambda * log2(Q(x)/U(x)))

One-shot Q -> R_lambda can save bits while keeping some visible fertility,
because R_lambda has higher entropy capacity than Q. But recursion requires
the output law to become the next input law. The invariant R_lambda ->
R_lambda rate is exactly zero in this source-law model.

This does not rule out a future Telomere-specific high-entropy fertile law. It
rules out "graded Q source law" as an arbitrary-pass compressor by itself.
"""

from __future__ import annotations

import importlib.util
import math
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


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def kl(p: list[float], q: list[float]) -> float:
    return sum(pi * math.log2(pi / qi) for pi, qi in zip(p, q) if pi > 0.0)


def tilted_law(domain, lam: float) -> list[float]:
    weights = [2.0 ** (lam * score) for score in domain.scores]
    total = sum(weights)
    return [weight / total for weight in weights]


@dataclass(frozen=True)
class TiltRow:
    lam: float
    entropy_r: float
    r_top25: float
    r_f_positive: float
    q_to_r_bits: float
    q_to_r_saving: float
    r_to_r_bits: float
    r_to_r_saving: float
    r_to_q_bits: float
    r_to_q_saving: float
    h7_top25: bool
    reading: str


def visible_bits(source: list[float], code_law: list[float], output_law: list[float], raw_bits: int) -> float:
    """Visible bits per source word after coding source under code_law and
    distribution-matching into output_law.

    The code stream length is H(source)+D(source||code_law). Each raw_bits-wide
    output symbol drawn from output_law carries H(output_law) bits.
    """

    code_bits = entropy(source) + kl(source, code_law)
    capacity = entropy(output_law)
    return raw_bits * code_bits / capacity


def row_for_lambda(domain, lam: float, top25: list[int], f_positive: list[int], c_star_top25: float) -> TiltRow:
    raw_bits = domain.raw_bits
    q = domain.q
    r = tilted_law(domain, lam)
    h_r = entropy(r)
    r_top25 = sum(r[index] for index in top25)
    r_f_positive = sum(r[index] for index in f_positive)

    q_to_r = visible_bits(q, r, r, raw_bits)
    r_to_r = visible_bits(r, r, r, raw_bits)
    r_to_q = visible_bits(r, q, r, raw_bits)
    if r_top25 >= c_star_top25 and q_to_r < raw_bits:
        reading = "one-shot saves and preserves top25"
    elif r_top25 >= c_star_top25:
        reading = "fertile but no one-shot shrink"
    elif q_to_r < raw_bits:
        reading = "shrinks but not fertile enough"
    else:
        reading = "misses both"
    return TiltRow(
        lam=lam,
        entropy_r=h_r,
        r_top25=r_top25,
        r_f_positive=r_f_positive,
        q_to_r_bits=q_to_r,
        q_to_r_saving=raw_bits - q_to_r,
        r_to_r_bits=r_to_r,
        r_to_r_saving=raw_bits - r_to_r,
        r_to_q_bits=r_to_q,
        r_to_q_saving=raw_bits - r_to_q,
        h7_top25=r_top25 >= c_star_top25,
        reading=reading,
    )


def print_rows(rows: list[TiltRow], raw_bits: int, c_star: float) -> None:
    print("== graded native law tilt sweep ==")
    print(
        f"Raw bits={raw_bits}, H7 top25 threshold c*={c_star:.4f}. "
        "Q->R is one-shot; R->R is the recursive invariant case."
    )
    print(
        f"{'lambda':>6} {'H(R)':>8} {'R(top25)':>9} {'R(F+)':>8} "
        f"{'Q->R bits':>10} {'Q->R save':>10} "
        f"{'R->R save':>10} {'R->Q save':>10} {'H7?':>5} {'reading':<34}"
    )
    for row in rows:
        print(
            f"{row.lam:6.2f} {row.entropy_r:8.3f} {row.r_top25:9.4f} "
            f"{row.r_f_positive:8.4f} {row.q_to_r_bits:10.3f} "
            f"{row.q_to_r_saving:10.3f} {row.r_to_r_saving:10.3f} "
            f"{row.r_to_q_saving:10.3f} "
            f"{'yes' if row.h7_top25 else 'no':>5} {row.reading:<34}"
        )
    print()


def print_frontier(rows: list[TiltRow]) -> None:
    fertile = [row for row in rows if row.h7_top25]
    if fertile:
        best = max(fertile, key=lambda row: row.q_to_r_saving)
        print("== best one-shot fertile row ==")
        print(
            f"lambda={best.lam:.2f}, Q->R saving={best.q_to_r_saving:.6f}, "
            f"R(top25)={best.r_top25:.6f}, invariant R->R saving={best.r_to_r_saving:.6f}"
        )
        print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A tilted law gives a real one-shot tradeoff: it can compress Q into a "
        "higher-entropy visible law R while retaining enough high-Q membership. "
        "But once R is the next layer, the invariant R->R case has zero saving. "
        "Encoding R under Q is expanding unless R=Q. Therefore a graded Q-family "
        "native law is not by itself repeatable compression. The remaining "
        "breakthrough target must be a high-entropy fertile law where fertility "
        "is not merely the entropy deficit of Q."
    )


def main() -> None:
    domain = _h80.exact_domain()
    top25 = _h80.top_class_indices(domain.scores, 0.25)
    f_positive = _h80.positive_class_indices(domain.scores)
    top25_row = _h80.row_for_indices(domain, top25)
    c_star = (0.011929 * domain.atoms - top25_row.mu_o) / (top25_row.mu_f - top25_row.mu_o)
    lambdas = [index / 10.0 for index in range(0, 11)]
    rows = [row_for_lambda(domain, lam, top25, f_positive, c_star) for lam in lambdas]
    print_rows(rows, domain.raw_bits, c_star)
    print_frontier(rows)
    print_reading()


if __name__ == "__main__":
    main()
