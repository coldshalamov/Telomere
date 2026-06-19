#!/usr/bin/env python3
"""H173 - population concentration variational bound.

H168/H171 leave one tempting escape: do not restrict witnesses to a fertile
class F, so no class tax is charged; instead let the emitted/source population
actually concentrate in F over passes.

For roughly-all uniform data, that concentration is not free. If F has public
background fraction f, a population fraction c carries:

    D(Bern(c) || Bern(f))

bits/record of source/output information. With class values a for F and b for
not-F, the exact binary variational identity is:

    c*a + (1-c)*b - D(c||f)
      = log2 Z - D(Bern(c) || Bern(c_eq))

where:

    Z = f*2^a + (1-f)*2^b
    c_eq = f*2^a / Z

So the best possible no-tax population law over uniform data is log2 Z. If the
designed law is Kraft-valid, Z <= 1 and the population route cannot produce
positive roughly-all drift. If it claims margin r, it needs Z >= 2^r: the same
overfull/hiddencapacity bill H171/H172 found.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    label: str
    post_gap_bits_per_record: float
    conservative_gap_bits_per_record: float


@dataclass(frozen=True)
class PopulationLawRow:
    fraction: float
    alpha: float
    tax: float
    value_f: float
    value_o: float
    z_mass: float
    log2_z: float
    equality_fraction: float
    equality_kl: float
    equality_value: float
    uniform_value: float
    post_margin: float
    conservative_margin: float


@dataclass(frozen=True)
class TargetRow:
    target: str
    fraction: float
    required_log2_z_post: float
    required_log2_z_conservative: float
    required_z_post: float
    required_z_conservative: float
    equality_fraction_if_overfull: float
    source_kl_at_equality: float


TARGETS = [
    Target("H162 K5 D80", 8.112500, 8.361777),
    Target("H163 K5 D256", 9.457453, 9.688172),
    Target("H163 K5 D512", 10.392213, 10.626718),
    Target("H163 K16 D512", 10.926442, 11.143925),
]

FRACTIONS = [0.50, 0.10, 0.03, 0.01, 0.003, 0.001]
ALPHAS = [0.50, 0.90, 0.99]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    if math.isnan(value):
        return "nan"
    if abs(value) >= 10_000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def tax(fraction: float) -> float:
    return -math.log2(fraction)


def kl_bernoulli(p: float, q: float) -> float:
    total = 0.0
    if p > 0.0:
        total += p * math.log2(p / q)
    if p < 1.0:
        total += (1.0 - p) * math.log2((1.0 - p) / (1.0 - q))
    return total


def complement_penalty_for_z(fraction: float, value_f: float, z_mass: float = 1.0) -> float:
    remaining = z_mass - fraction * (2.0**value_f)
    if remaining <= 0.0:
        return float("-inf")
    return math.log2(remaining / (1.0 - fraction))


def z_mass(fraction: float, value_f: float, value_o: float) -> float:
    return fraction * (2.0**value_f) + (1.0 - fraction) * (2.0**value_o)


def equality_fraction(fraction: float, value_f: float, z_value: float) -> float:
    if z_value <= 0.0:
        return float("nan")
    return fraction * (2.0**value_f) / z_value


def value_at(c: float, value_f: float, value_o: float) -> float:
    return c * value_f + (1.0 - c) * value_o


def net_at(c: float, fraction: float, value_f: float, value_o: float) -> float:
    return value_at(c, value_f, value_o) - kl_bernoulli(c, fraction)


def min_p_ff(c: float, p_of: float) -> float:
    if c <= 0.0:
        return 0.0
    if c > 1.0:
        return math.inf
    return max(0.0, min(1.0, (c - (1.0 - c) * p_of) / c))


def population_rows() -> list[PopulationLawRow]:
    rows: list[PopulationLawRow] = []
    post_gap = TARGETS[0].post_gap_bits_per_record
    conservative_gap = TARGETS[0].conservative_gap_bits_per_record
    for fraction in FRACTIONS:
        t = tax(fraction)
        for alpha in ALPHAS:
            value_f = alpha * t
            value_o = complement_penalty_for_z(fraction, value_f, z_mass=1.0)
            z = z_mass(fraction, value_f, value_o)
            c_eq = equality_fraction(fraction, value_f, z)
            eq_kl = kl_bernoulli(c_eq, fraction)
            eq_value = value_at(c_eq, value_f, value_o)
            rows.append(
                PopulationLawRow(
                    fraction=fraction,
                    alpha=alpha,
                    tax=t,
                    value_f=value_f,
                    value_o=value_o,
                    z_mass=z,
                    log2_z=math.log2(z),
                    equality_fraction=c_eq,
                    equality_kl=eq_kl,
                    equality_value=eq_value,
                    uniform_value=value_at(fraction, value_f, value_o),
                    post_margin=math.log2(z) - post_gap,
                    conservative_margin=math.log2(z) - conservative_gap,
                )
            )
    return rows


def target_rows() -> list[TargetRow]:
    rows: list[TargetRow] = []
    for target in TARGETS:
        required_z_post = 2.0 ** target.post_gap_bits_per_record
        required_z_conservative = 2.0 ** target.conservative_gap_bits_per_record
        for fraction in (0.10, 0.01, 0.003, 0.001):
            # Show the equality law if F alone carries the required mass.
            c_eq = min(1.0, fraction * required_z_post)
            rows.append(
                TargetRow(
                    target=target.label,
                    fraction=fraction,
                    required_log2_z_post=target.post_gap_bits_per_record,
                    required_log2_z_conservative=target.conservative_gap_bits_per_record,
                    required_z_post=required_z_post,
                    required_z_conservative=required_z_conservative,
                    equality_fraction_if_overfull=c_eq,
                    source_kl_at_equality=kl_bernoulli(c_eq, fraction),
                )
            )
    return rows


def print_proof() -> None:
    print("== binary public-class variational identity ==")
    print("For public class F with background f, values a,b, and population c:")
    print("  V(c) = c*a + (1-c)*b")
    print("  concentration cost = D(Bern(c)||Bern(f))")
    print("  V(c)-D(c||f) = log2 Z - D(Bern(c)||Bern(c_eq))")
    print("  Z = f*2^a + (1-f)*2^b")
    print("  c_eq = f*2^a / Z")
    print("So the best no-tax population margin under uniform data is log2 Z.")
    print()


def print_population_rows() -> None:
    print("== Kraft-balanced population laws ==")
    print(
        "Rows choose b so Z=1. They may concentrate the equality population in F, "
        "but the KL cost exactly cancels the value."
    )
    print(
        f"{'f':>7} {'alpha':>6} {'a':>9} {'b':>9} {'c_eq':>9} "
        f"{'KL_eq':>9} {'E_eq':>9} {'net*':>9} {'mPost':>9} {'mCons':>9}"
    )
    for row in population_rows():
        print(
            f"{fmt(row.fraction):>7} {fmt(row.alpha):>6} "
            f"{fmt(row.value_f):>9} {fmt(row.value_o):>9} "
            f"{fmt(row.equality_fraction):>9} {fmt(row.equality_kl):>9} "
            f"{fmt(row.equality_value):>9} {fmt(row.log2_z):>9} "
            f"{fmt(row.post_margin):>9} {fmt(row.conservative_margin):>9}"
        )
    print()


def print_target_rows() -> None:
    print("== overfull mass needed for positive population margin ==")
    print(
        "To get r bits/record of no-tax population margin on uniform data, "
        "the public law needs Z>=2^r. This is source bias if supplied by the "
        "input distribution; it is overfull hidden capacity if supplied by the codec."
    )
    print(
        f"{'target':<22} {'f':>7} {'need log2Z':>11} {'needZ post':>12} "
        f"{'needZ cons':>12} {'c_eq F-only':>13} {'KL(c_eq||f)':>13}"
    )
    for row in target_rows():
        print(
            f"{row.target:<22} {fmt(row.fraction):>7} "
            f"{fmt(row.required_log2_z_post):>11} {fmt(row.required_z_post):>12} "
            f"{fmt(row.required_z_conservative):>12} "
            f"{fmt(row.equality_fraction_if_overfull):>15} "
            f"{fmt(row.source_kl_at_equality):>13}"
        )
    print()


def print_threshold_scan() -> None:
    print("== finite concentration scan for easiest target ==")
    print(
        "Example: f=0.003, alpha=0.99 is one of H171's rare-class rows. "
        "The raw value crosses r only near pure F, but value minus KL never crosses."
    )
    fraction = 0.003
    alpha = 0.99
    value_f = alpha * tax(fraction)
    value_o = complement_penalty_for_z(fraction, value_f)
    gap = TARGETS[0].post_gap_bits_per_record
    print(f"{'c':>8} {'value':>9} {'KL':>9} {'net':>9} {'net-r':>9}")
    for c in (fraction, 0.10, 0.25, 0.50, 0.75, 0.90, 0.985168, 0.999, 1.0):
        value = value_at(c, value_f, value_o)
        kl = kl_bernoulli(c, fraction)
        net = value - kl
        print(f"{fmt(c):>8} {fmt(value):>9} {fmt(kl):>9} {fmt(net):>9} {fmt(net-gap):>9}")
    print()


def print_recurrence_table() -> None:
    print("== recurrence concentration check ==")
    print(
        "Using the same f=0.003, alpha=0.99 row with background p_OF=f. "
        "Holding high c_t requires near-closed p_FF, and the KL-priced margin "
        "still never pays the easiest post-H165 gap."
    )
    fraction = 0.003
    alpha = 0.99
    value_f = alpha * tax(fraction)
    value_o = complement_penalty_for_z(fraction, value_f)
    z = z_mass(fraction, value_f, value_o)
    c_eq = equality_fraction(fraction, value_f, z)
    gap = TARGETS[0].post_gap_bits_per_record
    raw_c_star = (gap - value_o) / (value_f - value_o)
    print(f"{'claim c':>10} {'min pFF':>9} {'value':>9} {'KL':>9} {'net':>9} {'net-r':>9}")
    for c in (fraction, c_eq, raw_c_star, 0.999, 1.0):
        value = value_at(c, value_f, value_o)
        kl = kl_bernoulli(c, fraction)
        net = value - kl
        print(
            f"{fmt(c):>10} {fmt(min_p_ff(c, fraction)):>9} {fmt(value):>9} "
            f"{fmt(kl):>9} {fmt(net):>9} {fmt(net - gap):>9}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Population mode is not a free third channel for roughly-all uniform data. "
        "If the emitted stream is more concentrated in a rare public fertile class "
        "than the background rate, that concentration itself is information. "
        "Paying D(c||f) reduces the best possible margin to log2 Z."
    )
    print(
        "Therefore a valid Kraft-balanced designed law has maximum no-tax "
        "population margin 0, and cannot pay the positive H168 gap. A positive "
        "population result must either be source-shaped, or identify an honest "
        "mechanism that makes Z>1 without hidden selector/profile/layout state."
    )


def main() -> None:
    print_proof()
    print_population_rows()
    print_target_rows()
    print_threshold_scan()
    print_recurrence_table()
    print_reading()


if __name__ == "__main__":
    main()
