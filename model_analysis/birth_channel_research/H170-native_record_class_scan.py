#!/usr/bin/env python3
"""H170 - native emitted-record class scan.

H169 tested public classes on raw visible words. H170 moves one step closer to
the Telomere record language: it enumerates H96's concrete emitted record
strings, computes their actual next-pass best-cover saving, and asks whether
public record-parse features identify a high-fertility class after paying the
current witness-supply tax.

The class fraction is current witness mass, not a cosmetic count:

    f_mass = sum_{desc in F} 2^-cost(desc) / sum_{desc} 2^-cost(desc)
    tax = -log2(f_mass)
    v_F = E[future_paid_saving(desc.bits) | desc in F, weighted by 2^-cost]
    net = v_F - tax

Classes based on arity/record-count/payload-width assume the native decoder can
parse records and read those fields. Classes based only on visible bits are
included as controls. Post-hoc oracle rows are printed as forbidden ceilings.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Callable


H96_PATH = Path(__file__).resolve().with_name("H96-neutral_transfer_operator.py")
_h96_spec = importlib.util.spec_from_file_location("h96_neutral_transfer_operator_for_h170", H96_PATH)
if _h96_spec is None or _h96_spec.loader is None:
    raise RuntimeError("could not load H96 neutral transfer operator")
_h96 = importlib.util.module_from_spec(_h96_spec)
sys.modules[_h96_spec.name] = _h96
_h96_spec.loader.exec_module(_h96)


POST_H165_TARGET_BITS = 8.112500
CONSERVATIVE_TARGET_BITS = 8.361777
SHUFFLE_TRIALS = 64


@dataclass(frozen=True)
class NativeDescription:
    word: int
    weight: float
    cost: int
    bits: str
    arities: tuple[int, ...]
    record_costs: tuple[int, ...]
    payload_widths: tuple[int, ...]
    future_paid_saving: float


NativePredicate = Callable[[NativeDescription], bool]


@dataclass(frozen=True)
class NativeClassSpec:
    name: str
    family: str
    predicate: NativePredicate


@dataclass(frozen=True)
class NativeClassRow:
    name: str
    family: str
    count: int
    count_fraction: float
    mass_fraction: float
    tax: float
    v_f: float
    v_o: float
    lift_vs_outside: float
    net_after_tax: float
    post_h165_margin: float
    conservative_margin: float
    shuffled_avg_net: float
    shuffled_max_net: float
    allowed: bool


def weighted_mean(pairs: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for weight, _value in pairs)
    if total_weight <= 0.0:
        return float("nan")
    return sum(weight * value for weight, value in pairs) / total_weight


def class_tax(fraction: float) -> float:
    if fraction <= 0.0:
        return math.inf
    return -math.log2(fraction)


def transitions(bits: str) -> int:
    return sum(1 for left, right in zip(bits, bits[1:]) if left != right)


def max_run(bits: str) -> int:
    best = 0
    current = 0
    previous = ""
    for bit in bits:
        current = current + 1 if bit == previous else 1
        previous = bit
        best = max(best, current)
    return best


def payload_width(record: object) -> int:
    return int(record.cost) - len(_h96.ARITY_BITS[int(record.arity)])


def enumerate_native_descriptions(
    *,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> list[NativeDescription]:
    by_value, edge_weights, edge_maxes = _h96.build_record_family(
        block_bits=1,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )

    @lru_cache(maxsize=None)
    def future_paid_saving(bits: str) -> float:
        _total, best = _h96.all_description_mass_for_bits(
            bits,
            max_arity,
            edge_weights,
            edge_maxes,
        )
        if best <= 0.0:
            return float("-inf")
        return len(bits) + math.log2(best)

    descriptions: list[NativeDescription] = []

    def span_value(word: int, start_atom: int, arity: int) -> int:
        shift_atoms = atoms - (start_atom + arity)
        mask = (1 << arity) - 1
        return (word >> shift_atoms) & mask

    for word in range(1 << atoms):
        def rec(
            pos: int,
            weight: float,
            cost: int,
            bits: str,
            arities: tuple[int, ...],
            record_costs: tuple[int, ...],
            payload_widths: tuple[int, ...],
        ) -> None:
            if pos == atoms:
                descriptions.append(
                    NativeDescription(
                        word=word,
                        weight=weight,
                        cost=cost,
                        bits=bits,
                        arities=arities,
                        record_costs=record_costs,
                        payload_widths=payload_widths,
                        future_paid_saving=future_paid_saving(bits),
                    )
                )
                return
            for arity in range(1, min(max_arity, atoms - pos) + 1):
                value = span_value(word, pos, arity)
                for record in by_value[arity][value]:
                    rec(
                        pos + arity,
                        weight * record.weight,
                        cost + record.cost,
                        bits + record.bits,
                        arities + (arity,),
                        record_costs + (record.cost,),
                        payload_widths + (payload_width(record),),
                    )

        rec(0, 1.0, 0, "", (), (), ())

    return descriptions


def make_specs() -> list[NativeClassSpec]:
    specs: list[NativeClassSpec] = []

    def add(name: str, family: str, predicate: NativePredicate) -> None:
        specs.append(NativeClassSpec(name, family, predicate))

    for arity in (1, 2, 3):
        add(
            f"first_arity={arity}",
            "arity",
            lambda desc, arity=arity: desc.arities[0] == arity,
        )
        add(
            f"last_arity={arity}",
            "arity",
            lambda desc, arity=arity: desc.arities[-1] == arity,
        )
        add(
            f"contains_arity={arity}",
            "arity",
            lambda desc, arity=arity: arity in desc.arities,
        )
        add(
            f"max_arity={arity}",
            "arity",
            lambda desc, arity=arity: max(desc.arities) == arity,
        )

    for count in range(2, 6):
        add(
            f"record_count={count}",
            "record-count",
            lambda desc, count=count: len(desc.arities) == count,
        )
    add("record_count_even", "record-count", lambda desc: len(desc.arities) % 2 == 0)
    add("record_count_odd", "record-count", lambda desc: len(desc.arities) % 2 == 1)
    add("all_singletons", "bundle", lambda desc: max(desc.arities) == 1)
    add("any_bundle", "bundle", lambda desc: max(desc.arities) > 1)
    add("any_arity3", "bundle", lambda desc: 3 in desc.arities)
    add("all_bundles", "bundle", lambda desc: min(desc.arities) > 1)
    add("first_eq_last_arity", "arity", lambda desc: desc.arities[0] == desc.arities[-1])

    for threshold in (14, 16, 18, 20, 24, 28, 32):
        add(
            f"total_cost<={threshold}",
            "cost",
            lambda desc, threshold=threshold: desc.cost <= threshold,
        )
        add(
            f"first_record_cost<={threshold}",
            "cost",
            lambda desc, threshold=threshold: desc.record_costs[0] <= threshold,
        )
    for residue in range(2):
        add(
            f"total_cost_mod2={residue}",
            "cost-mod",
            lambda desc, residue=residue: desc.cost % 2 == residue,
        )
    for residue in range(4):
        add(
            f"total_cost_mod4={residue}",
            "cost-mod",
            lambda desc, residue=residue: desc.cost % 4 == residue,
        )

    for threshold in (5, 7, 9, 11, 13):
        add(
            f"min_payload<={threshold}",
            "payload-width",
            lambda desc, threshold=threshold: min(desc.payload_widths) <= threshold,
        )
        add(
            f"first_payload<={threshold}",
            "payload-width",
            lambda desc, threshold=threshold: desc.payload_widths[0] <= threshold,
        )
        add(
            f"all_payload<={threshold}",
            "payload-width",
            lambda desc, threshold=threshold: max(desc.payload_widths) <= threshold,
        )

    for size in (1, 2, 3):
        for value in range(1 << size):
            pattern = f"{value:0{size}b}"
            add(
                f"bits_prefix{size}={pattern}",
                "bit-prefix",
                lambda desc, pattern=pattern: desc.bits.startswith(pattern),
            )
            add(
                f"bits_suffix{size}={pattern}",
                "bit-suffix",
                lambda desc, pattern=pattern: desc.bits.endswith(pattern),
            )

    for residue in range(2):
        add(
            f"bit_parity={residue}",
            "bit-shape",
            lambda desc, residue=residue: desc.bits.count("1") % 2 == residue,
        )
    for threshold in (2, 4, 6, 8, 10):
        add(
            f"bit_transitions<={threshold}",
            "bit-shape",
            lambda desc, threshold=threshold: transitions(desc.bits) <= threshold,
        )
        add(
            f"bit_max_run>={threshold}",
            "bit-shape",
            lambda desc, threshold=threshold: max_run(desc.bits) >= threshold,
        )

    return specs


def evaluate_class(spec: NativeClassSpec, descriptions: list[NativeDescription]) -> NativeClassRow | None:
    selected_indices = [index for index, desc in enumerate(descriptions) if spec.predicate(desc)]
    if not selected_indices or len(selected_indices) == len(descriptions):
        return None
    selected = set(selected_indices)
    total_mass = sum(desc.weight for desc in descriptions)
    selected_mass = sum(descriptions[index].weight for index in selected_indices)
    other_mass = total_mass - selected_mass
    if selected_mass <= 0.0 or other_mass <= 0.0:
        return None
    mass_fraction = selected_mass / total_mass
    tax = class_tax(mass_fraction)
    v_f = weighted_mean(
        [(descriptions[index].weight, descriptions[index].future_paid_saving) for index in selected_indices]
    )
    v_o = weighted_mean(
        [
            (desc.weight, desc.future_paid_saving)
            for index, desc in enumerate(descriptions)
            if index not in selected
        ]
    )
    net = v_f - tax
    return NativeClassRow(
        name=spec.name,
        family=spec.family,
        count=len(selected_indices),
        count_fraction=len(selected_indices) / len(descriptions),
        mass_fraction=mass_fraction,
        tax=tax,
        v_f=v_f,
        v_o=v_o,
        lift_vs_outside=v_f - v_o,
        net_after_tax=net,
        post_h165_margin=net - POST_H165_TARGET_BITS,
        conservative_margin=net - CONSERVATIVE_TARGET_BITS,
        shuffled_avg_net=float("nan"),
        shuffled_max_net=float("nan"),
        allowed=True,
    )


def shuffled_net_controls(
    descriptions: list[NativeDescription],
    count: int,
    *,
    trials: int = SHUFFLE_TRIALS,
    seed: int = 170000,
) -> tuple[float, float]:
    rng = random.Random(seed + count)
    total_mass = sum(desc.weight for desc in descriptions)
    population = list(range(len(descriptions)))
    nets: list[float] = []
    for _ in range(trials):
        sample = rng.sample(population, count)
        selected_mass = sum(descriptions[index].weight for index in sample)
        if selected_mass <= 0.0:
            continue
        tax = class_tax(selected_mass / total_mass)
        value = weighted_mean(
            [(descriptions[index].weight, descriptions[index].future_paid_saving) for index in sample]
        )
        nets.append(value - tax)
    return weighted_mean([(1.0, value) for value in nets]), max(nets)


def oracle_rows(descriptions: list[NativeDescription], fractions: list[float]) -> list[NativeClassRow]:
    total_mass = sum(desc.weight for desc in descriptions)
    order = sorted(range(len(descriptions)), key=lambda index: descriptions[index].future_paid_saving, reverse=True)
    rows: list[NativeClassRow] = []
    for fraction in fractions:
        selected_indices: list[int] = []
        selected_mass = 0.0
        target_mass = fraction * total_mass
        for index in order:
            if selected_mass >= target_mass and selected_indices:
                break
            selected_indices.append(index)
            selected_mass += descriptions[index].weight
        selected = set(selected_indices)
        other_mass = total_mass - selected_mass
        if selected_mass <= 0.0 or other_mass <= 0.0:
            continue
        mass_fraction = selected_mass / total_mass
        tax = class_tax(mass_fraction)
        v_f = weighted_mean(
            [(descriptions[index].weight, descriptions[index].future_paid_saving) for index in selected_indices]
        )
        v_o = weighted_mean(
            [
                (desc.weight, desc.future_paid_saving)
                for index, desc in enumerate(descriptions)
                if index not in selected
            ]
        )
        net = v_f - tax
        rows.append(
            NativeClassRow(
                name=f"oracle_target={fraction:.3f}_actual={mass_fraction:.3f}",
                family="oracle-disallowed",
                count=len(selected_indices),
                count_fraction=len(selected_indices) / len(descriptions),
                mass_fraction=mass_fraction,
                tax=tax,
                v_f=v_f,
                v_o=v_o,
                lift_vs_outside=v_f - v_o,
                net_after_tax=net,
                post_h165_margin=net - POST_H165_TARGET_BITS,
                conservative_margin=net - CONSERVATIVE_TARGET_BITS,
                shuffled_avg_net=float("nan"),
                shuffled_max_net=float("nan"),
                allowed=False,
            )
        )
    return rows


def attach_shuffled_controls(
    rows: list[NativeClassRow],
    descriptions: list[NativeDescription],
    *,
    limit: int,
    seed: int,
) -> list[NativeClassRow]:
    updated: list[NativeClassRow] = []
    for index, row in enumerate(rows):
        if index < limit:
            shuffled_avg, shuffled_max = shuffled_net_controls(
                descriptions,
                row.count,
                seed=seed + index * 1009,
            )
            updated.append(
                replace(
                    row,
                    shuffled_avg_net=shuffled_avg,
                    shuffled_max_net=shuffled_max,
                )
            )
        else:
            updated.append(row)
    return updated


def print_rows(title: str, rows: list[NativeClassRow], *, limit: int = 20) -> None:
    print(title)
    print(
        f"{'class':<30} {'family':<14} {'n':>6} {'fCnt':>8} {'fMass':>8} "
        f"{'tax':>8} {'vF':>10} {'vO':>10} {'net':>10} {'mPost':>10} {'shufMax':>10}"
    )
    for row in rows[:limit]:
        print(
            f"{row.name:<30} {row.family:<14} {row.count:6d} "
            f"{row.count_fraction:8.5f} {row.mass_fraction:8.5f} "
            f"{row.tax:8.5f} {row.v_f:10.5f} {row.v_o:10.5f} "
            f"{row.net_after_tax:10.5f} {row.post_h165_margin:10.5f} "
            f"{row.shuffled_max_net:10.5f}"
        )
    print()


def print_family_summary(rows: list[NativeClassRow]) -> None:
    best_by_family: dict[str, NativeClassRow] = {}
    for row in rows:
        current = best_by_family.get(row.family)
        if current is None or row.net_after_tax > current.net_after_tax:
            best_by_family[row.family] = row
    print("== best native row by family ==")
    print(f"{'family':<14} {'class':<30} {'fMass':>8} {'vF':>10} {'net':>10} {'mPost':>10}")
    for family, row in sorted(best_by_family.items(), key=lambda item: item[1].net_after_tax, reverse=True):
        print(
            f"{family:<14} {row.name:<30} {row.mass_fraction:8.5f} "
            f"{row.v_f:10.5f} {row.net_after_tax:10.5f} {row.post_h165_margin:10.5f}"
        )
    print()


def print_reading(best_public: NativeClassRow, best_oracle: NativeClassRow, uniform_future: float) -> None:
    print("== reading ==")
    print(
        "H170 is more native than H169 because the class fraction is current "
        "record-witness mass and the features are visible record fields or "
        "visible record bits. It still uses H96's tiny record toy, so production "
        "H168 margins are diagnostic scale markers, not literal proof units."
    )
    print(
        f"Best allowed native class is {best_public.name} with net_after_tax="
        f"{best_public.net_after_tax:.6f} bits/record-string. Best disallowed "
        f"oracle ceiling is {best_oracle.net_after_tax:.6f}. The supply-weighted "
        f"uniform future paid saving is {uniform_future:.6f}."
    )
    print(
        "A real positive would need a public class with positive net after its "
        "mass tax, enough margin to cover the current total-cover gap, and a "
        "measured recurrence of that class across emitted passes."
    )


def main() -> None:
    atoms = 5
    max_arity = 3
    depth_bits = 3
    seed = 96000
    descriptions = enumerate_native_descriptions(
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    total_mass = sum(desc.weight for desc in descriptions)
    uniform_future = weighted_mean([(desc.weight, desc.future_paid_saving) for desc in descriptions])

    rows = [
        row
        for spec in make_specs()
        if (row := evaluate_class(spec, descriptions)) is not None
    ]
    rows.sort(key=lambda row: row.net_after_tax, reverse=True)
    rows = attach_shuffled_controls(rows, descriptions, limit=25, seed=170000)
    oracle = oracle_rows(descriptions, [0.50, 0.25, 0.10, 0.03, 0.01])
    oracle.sort(key=lambda row: row.net_after_tax, reverse=True)
    oracle = attach_shuffled_controls(oracle, descriptions, limit=len(oracle), seed=170900)

    print("== native emitted-record class scan ==")
    print(
        f"H96 domain: B=1, N={atoms}, K={max_arity}, D={depth_bits}, "
        f"descriptions={len(descriptions)}, total_mass={total_mass:.12e}"
    )
    print(f"supply-weighted E future_paid_saving: {uniform_future:.6f} bits/record-string")
    print(f"H168 post-H165 target used as diagnostic: {POST_H165_TARGET_BITS:.6f} bits/record")
    print(f"H168 conservative target used as diagnostic: {CONSERVATIVE_TARGET_BITS:.6f} bits/record")
    print()
    print_rows("== best allowed native record classes ==", rows)
    print_family_summary(rows)
    print_rows("== disallowed future-saving oracle ceilings ==", oracle, limit=len(oracle))
    print_reading(rows[0], oracle[0], uniform_future)


if __name__ == "__main__":
    main()
