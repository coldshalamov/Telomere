#!/usr/bin/env python3
"""H88 - frozen soft-law grammar finite overhead.

Lane A proposed the cleanest native-soft-law toy:

    P_theta(x) proportional to U(x) * 2^(theta * V(x))

with the law and parser frozen public. In the ideal arithmetic limit, the
visible law pays D(P||U) and gets the H86 future-value lift. H88 measures a
finite, stateless block distribution matcher for the exact H80 domain.

For block length m, choose integer counts n_x ~= m P_theta(x). The canonical
type class has:

    |T| = m! / prod_x n_x!

A decoder can unrank k=floor(log2 |T|) uniform payload bits into a sequence in
T with no per-file profile if the counts are public for (theta,m). The emitted
sequence has empirical law P_hat. The finite shaping bill is:

    bill = raw_bits - k/m

and the measured useful source/fertility investment is:

    eta = (E_Phat[V] - E_U[V]) - bill

This is still only a grammar/matcher audit. It does not prove arbitrary-data
compression unless the future-value score is realized as actual paid witness
savings under a stateless second pass.
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


def tilted_law(values: list[float], theta: float) -> list[float]:
    exponents = [theta * value for value in values]
    max_exponent = max(exponents)
    weights = [2.0 ** (exponent - max_exponent) for exponent in exponents]
    total = sum(weights)
    return [weight / total for weight in weights]


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


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


@dataclass(frozen=True)
class MatcherRow:
    theta: float
    block_len: int
    active_symbols: int
    target_delta: float
    empirical_delta: float
    log2_type: float
    payload_bits_per_word: float
    finite_bill: float
    lift: float
    eta: float
    top25_mass: float


def row_for(theta: float, block_len: int, values: list[float], top25: list[int]) -> MatcherRow:
    raw_bits = math.log2(len(values))
    target = tilted_law(values, theta)
    counts = counts_for_law(target, block_len)
    empirical = [count / block_len for count in counts]
    log_type = log2_type_size(counts)
    payload = math.floor(log_type) / block_len
    finite_bill = raw_bits - payload
    uniform_value = sum(values) / len(values)
    lift = expectation(empirical, values) - uniform_value
    return MatcherRow(
        theta=theta,
        block_len=block_len,
        active_symbols=sum(1 for count in counts if count),
        target_delta=raw_bits - entropy(target),
        empirical_delta=raw_bits - entropy(empirical),
        log2_type=log_type,
        payload_bits_per_word=payload,
        finite_bill=finite_bill,
        lift=lift,
        eta=lift - finite_bill,
        top25_mass=sum(empirical[index] for index in top25),
    )


def print_rows(values: list[float], top25: list[int]) -> None:
    print("== frozen soft-law type-class matcher ==")
    print(
        "payload is floor(log2 |T|)/m. bill is raw_bits-payload. "
        "eta is future-value lift minus finite bill."
    )
    print(
        f"{'theta':>6} {'m':>6} {'active':>7} {'targetD':>9} {'empD':>9} "
        f"{'payload':>9} {'bill':>9} {'lift':>9} {'eta':>9} {'top25':>9}"
    )
    for theta in (0.05, 0.10, 0.30, 0.50, 0.90, 1.00):
        for block_len in (64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768):
            row = row_for(theta, block_len, values, top25)
            print(
                f"{row.theta:6.2f} {row.block_len:6d} {row.active_symbols:7d} "
                f"{row.target_delta:9.6f} {row.empirical_delta:9.6f} "
                f"{row.payload_bits_per_word:9.6f} {row.finite_bill:9.6f} "
                f"{row.lift:9.6f} {row.eta:9.6f} {row.top25_mass:9.6f}"
            )
        print()


def print_best(values: list[float], top25: list[int]) -> None:
    rows = [
        row_for(theta / 100.0, block_len, values, top25)
        for theta in range(1, 151)
        for block_len in (128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768)
    ]
    best_eta = max(rows, key=lambda row: row.eta)
    best_small = max((row for row in rows if row.block_len <= 512), key=lambda row: row.eta)
    print("== best rows in scanned finite matcher ==")
    for label, row in (("best", best_eta), ("best m<=512", best_small)):
        print(
            f"{label}: theta={row.theta:.2f}, m={row.block_len}, "
            f"bill={row.finite_bill:.6f}, lift={row.lift:.6f}, "
            f"eta={row.eta:.6f}, top25={row.top25_mass:.6f}, active={row.active_symbols}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A frozen type-class matcher can realize the soft tilted law with only "
        "finite rounding overhead and no adaptive profile channel when theta "
        "and m are public constants. This makes the native-soft-law target "
        "more concrete. The remaining hard part is not parseability here; it is "
        "proving that the measured value lift becomes actual second-pass "
        "Telomere witness savings without smuggling in a source selector."
    )


def main() -> None:
    domain = _h80.exact_domain()
    values = domain.scores
    top25 = _h80.top_class_indices(values, 0.25)
    print_rows(values, top25)
    print_best(values, top25)
    print_reading()


if __name__ == "__main__":
    main()
