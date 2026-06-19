#!/usr/bin/env python3
"""H169 - public visible-class actual witness-savings scan.

H168 left one live route: a public recurrent fertility law. The decoder must be
able to recognize the class from visible bits/rules, and any restriction of
witnesses to that class pays the supply tax -log2(f).

This kernel reuses H89's exact tiny witness domain and tests only predeclared
visible classes: prefixes, suffixes, popcount, transition/run, and periodic
features. For each class F it reports actual paid future witness savings from
H89, then subtracts the class supply tax. It also prints post-hoc oracle
ceilings labeled as disallowed; those show how much a hidden selector could buy
if it were allowed to choose the class from the paid_saving table itself.

The H89 domain is a toy bits/word domain, not the production total-cover
bits/record domain. Comparisons to H168's 8.112500-bit target are therefore
diagnostic only: a visible class that cannot even make v_F - tax positive here
is not a breakthrough, while a positive row would still need a native
record-language recurrence proof.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


H89_PATH = Path(__file__).resolve().with_name("H89-actual_witness_savings.py")
_h89_spec = importlib.util.spec_from_file_location("h89_actual_witness_savings_for_h169", H89_PATH)
if _h89_spec is None or _h89_spec.loader is None:
    raise RuntimeError("could not load H89 actual witness-savings kernel")
_h89 = importlib.util.module_from_spec(_h89_spec)
sys.modules[_h89_spec.name] = _h89
_h89_spec.loader.exec_module(_h89)


POST_H165_TARGET_BITS = 8.112500
CONSERVATIVE_TARGET_BITS = 8.361777
SHUFFLE_TRIALS = 512


Predicate = Callable[[str], bool]


@dataclass(frozen=True)
class ClassSpec:
    name: str
    family: str
    predicate: Predicate


@dataclass(frozen=True)
class ClassRow:
    name: str
    family: str
    count: int
    fraction: float
    tax: float
    v_f: float
    v_o: float
    lift_vs_outside: float
    lift_vs_uniform: float
    net_after_tax: float
    post_h165_margin: float
    conservative_margin: float
    shuffled_avg_net: float
    shuffled_max_net: float
    allowed: bool


def bits_of(word: int, width: int) -> str:
    return f"{word:0{width}b}"


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def complement_mean(values: list[float], selected: set[int]) -> float:
    rest = [value for index, value in enumerate(values) if index not in selected]
    return mean(rest)


def class_tax(fraction: float) -> float:
    if fraction <= 0.0:
        return math.inf
    return -math.log2(fraction)


def shuffled_net_controls(
    values: list[float],
    count: int,
    tax: float,
    *,
    trials: int = SHUFFLE_TRIALS,
    seed: int = 169000,
) -> tuple[float, float]:
    if count <= 0:
        return float("-inf"), float("-inf")
    rng = random.Random(seed + count)
    population = list(range(len(values)))
    nets: list[float] = []
    for _ in range(trials):
        sample = rng.sample(population, count)
        nets.append(mean([values[index] for index in sample]) - tax)
    return mean(nets), max(nets)


def make_specs(width: int) -> list[ClassSpec]:
    specs: list[ClassSpec] = []

    def add(name: str, family: str, predicate: Predicate) -> None:
        specs.append(ClassSpec(name, family, predicate))

    for size in (1, 2, 3, 4):
        for value in range(1 << size):
            pattern = f"{value:0{size}b}"
            add(
                f"prefix{size}={pattern}",
                "prefix",
                lambda bits, pattern=pattern: bits.startswith(pattern),
            )
            add(
                f"suffix{size}={pattern}",
                "suffix",
                lambda bits, pattern=pattern: bits.endswith(pattern),
            )

    arity_prefixes = {
        "arity1_00": "00",
        "arity2_01": "01",
        "arity3_100": "100",
        "arity4_101": "101",
        "arity5_110": "110",
        "literal_111": "111",
    }
    for name, pattern in arity_prefixes.items():
        add(
            f"lotus_{name}",
            "lotus-prefix",
            lambda bits, pattern=pattern: bits.startswith(pattern),
        )

    for threshold in range(1, min(width, 6) + 1):
        add(
            f"ones<={threshold}",
            "popcount-tail",
            lambda bits, threshold=threshold: bits.count("1") <= threshold,
        )
        add(
            f"ones>={width - threshold}",
            "popcount-tail",
            lambda bits, threshold=threshold: bits.count("1") >= width - threshold,
        )

    for residue in range(2):
        add(
            f"parity={residue}",
            "popcount-mod",
            lambda bits, residue=residue: bits.count("1") % 2 == residue,
        )
    for residue in range(4):
        add(
            f"ones_mod4={residue}",
            "popcount-mod",
            lambda bits, residue=residue: bits.count("1") % 4 == residue,
        )

    def transitions(bits: str) -> int:
        return sum(1 for left, right in zip(bits, bits[1:]) if left != right)

    for threshold in (1, 2, 3, 4):
        add(
            f"transitions<={threshold}",
            "transition",
            lambda bits, threshold=threshold: transitions(bits) <= threshold,
        )
        add(
            f"transitions>={width - threshold}",
            "transition",
            lambda bits, threshold=threshold: transitions(bits) >= width - threshold,
        )

    def max_run(bits: str) -> int:
        best = 0
        current = 0
        previous = ""
        for bit in bits:
            current = current + 1 if bit == previous else 1
            previous = bit
            best = max(best, current)
        return best

    for threshold in (2, 3, 4, 5, 6):
        add(
            f"max_run<={threshold}",
            "run",
            lambda bits, threshold=threshold: max_run(bits) <= threshold,
        )
        add(
            f"max_run>={threshold}",
            "run",
            lambda bits, threshold=threshold: max_run(bits) >= threshold,
        )

    for period in (2, 3, 4, 6):
        add(
            f"period{period}",
            "periodic",
            lambda bits, period=period: all(bits[index] == bits[index % period] for index in range(len(bits))),
        )

    for size in (1, 2, 3, 4):
        add(
            f"prefix_eq_suffix{size}",
            "border",
            lambda bits, size=size: bits[:size] == bits[-size:],
        )

    add(
        "balanced_5_to_7_ones",
        "popcount-band",
        lambda bits: 5 <= bits.count("1") <= 7,
    )
    add(
        "middle_four_equal",
        "local-repeat",
        lambda bits: len(set(bits[(width // 2 - 2) : (width // 2 + 2)])) == 1,
    )
    add(
        "first_half_eq_second_half",
        "periodic",
        lambda bits: bits[: width // 2] == bits[width // 2 :],
    )
    add(
        "first_half_complement_second_half",
        "periodic",
        lambda bits: all(a != b for a, b in zip(bits[: width // 2], bits[width // 2 :])),
    )
    return specs


def evaluate_class(
    spec: ClassSpec,
    bit_strings: list[str],
    values: list[float],
    uniform_value: float,
) -> ClassRow | None:
    indices = [index for index, bits in enumerate(bit_strings) if spec.predicate(bits)]
    if not indices or len(indices) == len(bit_strings):
        return None
    selected = set(indices)
    fraction = len(indices) / len(bit_strings)
    tax = class_tax(fraction)
    v_f = mean([values[index] for index in indices])
    v_o = complement_mean(values, selected)
    net = v_f - tax
    shuffled_avg, shuffled_max = shuffled_net_controls(values, len(indices), tax)
    return ClassRow(
        name=spec.name,
        family=spec.family,
        count=len(indices),
        fraction=fraction,
        tax=tax,
        v_f=v_f,
        v_o=v_o,
        lift_vs_outside=v_f - v_o,
        lift_vs_uniform=v_f - uniform_value,
        net_after_tax=net,
        post_h165_margin=net - POST_H165_TARGET_BITS,
        conservative_margin=net - CONSERVATIVE_TARGET_BITS,
        shuffled_avg_net=shuffled_avg,
        shuffled_max_net=shuffled_max,
        allowed=True,
    )


def oracle_rows(values: list[float], fractions: list[float]) -> list[ClassRow]:
    rows: list[ClassRow] = []
    width = len(values)
    uniform_value = mean(values)
    order = sorted(range(width), key=lambda index: values[index], reverse=True)
    for fraction in fractions:
        count = max(1, round(width * fraction))
        indices = order[:count]
        selected = set(indices)
        actual_fraction = count / width
        tax = class_tax(actual_fraction)
        v_f = mean([values[index] for index in indices])
        v_o = complement_mean(values, selected)
        net = v_f - tax
        shuffled_avg, shuffled_max = shuffled_net_controls(values, count, tax, seed=169900)
        rows.append(
            ClassRow(
                name=f"oracle_top_paid_saving_f={actual_fraction:.3f}",
                family="oracle-disallowed",
                count=count,
                fraction=actual_fraction,
                tax=tax,
                v_f=v_f,
                v_o=v_o,
                lift_vs_outside=v_f - v_o,
                lift_vs_uniform=v_f - uniform_value,
                net_after_tax=net,
                post_h165_margin=net - POST_H165_TARGET_BITS,
                conservative_margin=net - CONSERVATIVE_TARGET_BITS,
                shuffled_avg_net=shuffled_avg,
                shuffled_max_net=shuffled_max,
                allowed=False,
            )
        )
    return rows


def print_rows(title: str, rows: list[ClassRow], *, limit: int = 20) -> None:
    print(title)
    print(
        f"{'class':<34} {'family':<16} {'n':>5} {'f':>8} {'tax':>8} "
        f"{'vF':>9} {'vO':>9} {'lift':>9} {'net':>9} {'mPost':>9} {'shufMax':>9}"
    )
    for row in rows[:limit]:
        print(
            f"{row.name:<34} {row.family:<16} {row.count:5d} "
            f"{row.fraction:8.5f} {row.tax:8.5f} {row.v_f:9.5f} "
            f"{row.v_o:9.5f} {row.lift_vs_outside:9.5f} "
            f"{row.net_after_tax:9.5f} {row.post_h165_margin:9.5f} "
            f"{row.shuffled_max_net:9.5f}"
        )
    print()


def print_family_summary(rows: list[ClassRow]) -> None:
    best_by_family: dict[str, ClassRow] = {}
    for row in rows:
        current = best_by_family.get(row.family)
        if current is None or row.net_after_tax > current.net_after_tax:
            best_by_family[row.family] = row
    print("== best public row by family ==")
    print(
        f"{'family':<16} {'class':<34} {'f':>8} {'vF':>9} "
        f"{'net':>9} {'mPost':>9} {'shufMax':>9}"
    )
    for family, row in sorted(best_by_family.items(), key=lambda item: item[1].net_after_tax, reverse=True):
        print(
            f"{family:<16} {row.name:<34} {row.fraction:8.5f} "
            f"{row.v_f:9.5f} {row.net_after_tax:9.5f} "
            f"{row.post_h165_margin:9.5f} {row.shuffled_max_net:9.5f}"
        )
    print()


def print_population_conservation(uniform_value: float) -> None:
    print("== population-start conservation ==")
    print(
        "For any partition of the uniform domain, f*vF + (1-f)*vO equals the "
        f"uniform paid saving {uniform_value:.6f} bits/word. A no-tax population "
        "claim therefore needs a real recurrence that changes c_t, not just a "
        "public label on the pass-0 uniform population."
    )
    print(
        f"Uniform-start margin versus H168 post-H165 target: "
        f"{uniform_value - POST_H165_TARGET_BITS:.6f} bits/word (toy-units)."
    )
    print()


def print_reading(best_public: ClassRow, best_oracle: ClassRow, uniform_value: float) -> None:
    print("== reading ==")
    print(
        "H169 is a visible-class sanity scan, not a full production proof. The "
        "allowed rows use only predeclared properties of the visible word. The "
        "oracle rows sort by paid_saving itself and are forbidden as a codec "
        "mechanism unless a future public grammar makes that ranking decoder-"
        "derivable without a side profile."
    )
    print(
        f"Best allowed public net is {best_public.net_after_tax:.6f} bits/word "
        f"({best_public.name}); best disallowed oracle net is "
        f"{best_oracle.net_after_tax:.6f} bits/word. Uniform is "
        f"{uniform_value:.6f} bits/word."
    )
    print(
        "A real positive would require net_after_tax to beat the current "
        "bits/record gap in a native record-language model, then show recurrence "
        "of the class fraction across passes. This scan finds candidates or "
        "rules out the easy visible classes; it does not use open/carry, birth "
        "passes, final positions, or hidden pass state."
    )


def main() -> None:
    domain = _h89.exact_witness_domain()
    width = domain.raw_bits
    bit_strings = [bits_of(word, width) for word in range(1 << width)]
    values = list(domain.paid_savings)
    uniform_value = mean(values)

    specs = make_specs(width)
    public_rows = [
        row
        for spec in specs
        if (row := evaluate_class(spec, bit_strings, values, uniform_value)) is not None
    ]
    public_rows.sort(key=lambda row: row.net_after_tax, reverse=True)
    oracle = oracle_rows(values, [0.50, 0.25, 0.10, 0.03, 0.01])
    oracle.sort(key=lambda row: row.net_after_tax, reverse=True)

    print("== visible class actual witness-savings scan ==")
    print(
        f"H89 domain: B={domain.block_bits}, N={domain.atoms}, K={domain.max_arity}, "
        f"D={domain.depth_bits}, words={len(values)}"
    )
    print(f"E_U paid_saving: {uniform_value:.6f} bits/word")
    print(f"H168 post-H165 target used as diagnostic: {POST_H165_TARGET_BITS:.6f} bits/record")
    print(f"H168 conservative target used as diagnostic: {CONSERVATIVE_TARGET_BITS:.6f} bits/record")
    print()

    print_rows("== best allowed public visible classes ==", public_rows)
    print_family_summary(public_rows)
    print_rows("== disallowed post-hoc oracle ceilings ==", oracle, limit=len(oracle))
    print_population_conservation(uniform_value)
    print_reading(public_rows[0], oracle[0], uniform_value)


if __name__ == "__main__":
    main()
