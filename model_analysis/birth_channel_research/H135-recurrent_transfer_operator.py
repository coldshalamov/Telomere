#!/usr/bin/env python3
"""H135 - exact recurrent neutral-transfer operator.

H96 measured one-step neutral transfer: choose a visible record string that
decodes to the current word and is easier to rewrite next pass. H135 makes the
operator recurrent:

    T_lambda(x) = argmax_c [ len(x)-len(c) + lambda * fertility(c) ]

where c is a concrete paid visible record string that decodes to x and
fertility(c) is the actual all-description next-pass saving of c, not a proxy
Q score. The chosen bits are the next layer, so no selector is stored.

This is a favorable exact toy. If even this expands over repeated passes, the
neutral-transfer signal is a source/fertility clue, not a source-free recursive
compressor.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h135", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"could not load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


@dataclass(frozen=True)
class Choice:
    input_bits: str
    output_bits: str
    current_saving: float
    future_saving: float
    score: float
    description_count: int


@dataclass(frozen=True)
class TransferRow:
    lambda_value: float
    passes: int
    max_bits: int
    fail_rate: float
    mean_total_saving: float
    mean_saving_per_pass: float
    positive_fraction: float
    mean_final_bits: float
    mean_growth_ratio: float
    mean_first_future: float
    mean_first_random_future: float
    mean_first_lift_vs_random: float
    mean_description_count: float


def bits_for_word(word: int, atoms: int) -> str:
    return format(word, f"0{atoms}b")


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else float("-inf")


def run_rows(
    atoms: int = 5,
    max_arity: int = 3,
    depth_bits: int = 3,
    seed: int = 96000,
    max_bits: int = 28,
    lambdas: tuple[float, ...] = (0.0, 1.0, 2.0),
    pass_counts: tuple[int, ...] = (2,),
) -> list[TransferRow]:
    by_value, edge_weights, edge_maxes = h96.build_record_family(
        block_bits=1,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    rng = random.Random(seed + 135)

    @lru_cache(maxsize=None)
    def fertility(bits: str) -> float:
        if len(bits) > max_bits:
            return float("-inf")
        total, _ = h96.all_description_mass_for_bits(bits, max_arity, edge_weights, edge_maxes)
        if total <= 0.0:
            return float("-inf")
        return len(bits) + math.log2(total)

    @lru_cache(maxsize=None)
    def descriptions_for(bits: str) -> tuple[h96.Description, ...]:
        if len(bits) > max_bits:
            return tuple()
        return tuple(
            h96.enumerate_descriptions(
                h96.word_from_bits(bits),
                len(bits),
                max_arity,
                by_value,
            )
        )

    @lru_cache(maxsize=None)
    def choose(bits: str, lambda_value: float) -> Choice | None:
        descriptions = descriptions_for(bits)
        if not descriptions:
            return None
        best: tuple[float, float, int, str, h96.Description] | None = None
        for description in descriptions:
            future = fertility(description.bits)
            if not math.isfinite(future):
                continue
            current = len(bits) - description.cost
            score = current + lambda_value * future
            key = (score, current, -description.cost, description.bits, description)
            if best is None or key > best:
                best = key
        if best is None:
            return None
        score, current, _neg_cost, _bits, description = best
        return Choice(
            input_bits=bits,
            output_bits=description.bits,
            current_saving=current,
            future_saving=fertility(description.bits),
            score=score,
            description_count=len(descriptions),
        )

    def random_same_length_future(length: int) -> float:
        bits = "".join("1" if rng.randrange(2) else "0" for _ in range(length))
        return fertility(bits)

    result: list[TransferRow] = []
    initial = [bits_for_word(word, atoms) for word in range(1 << atoms)]

    for lambda_value in lambdas:
        for passes in pass_counts:
            failed = 0
            totals: list[float] = []
            final_lengths: list[int] = []
            growth_ratios: list[float] = []
            first_futures: list[float] = []
            first_randoms: list[float] = []
            desc_counts: list[float] = []
            for start in initial:
                bits = start
                total_saving = 0.0
                first_choice: Choice | None = None
                ok = True
                for pass_index in range(passes):
                    choice = choose(bits, lambda_value)
                    if choice is None or len(choice.output_bits) > max_bits:
                        ok = False
                        break
                    if pass_index == 0:
                        first_choice = choice
                    total_saving += choice.current_saving
                    desc_counts.append(choice.description_count)
                    bits = choice.output_bits
                if not ok:
                    failed += 1
                    continue
                totals.append(total_saving)
                final_lengths.append(len(bits))
                growth_ratios.append(len(bits) / len(start))
                if first_choice is not None:
                    first_futures.append(first_choice.future_saving)
                    first_randoms.append(random_same_length_future(len(first_choice.output_bits)))
            finite_count = len(totals)
            fail_rate = failed / len(initial)
            result.append(
                TransferRow(
                    lambda_value=lambda_value,
                    passes=passes,
                    max_bits=max_bits,
                    fail_rate=fail_rate,
                    mean_total_saving=finite_mean(totals),
                    mean_saving_per_pass=finite_mean(totals) / passes if finite_count else float("-inf"),
                    positive_fraction=sum(1 for value in totals if value > 0.0) / finite_count if finite_count else 0.0,
                    mean_final_bits=finite_mean([float(value) for value in final_lengths]),
                    mean_growth_ratio=finite_mean(growth_ratios),
                    mean_first_future=finite_mean(first_futures),
                    mean_first_random_future=finite_mean(first_randoms),
                    mean_first_lift_vs_random=finite_mean(
                        [future - random for future, random in zip(first_futures, first_randoms)]
                    ),
                    mean_description_count=finite_mean(desc_counts),
                )
            )
    return result


def print_rows(rows: list[TransferRow], atoms: int, max_arity: int, depth_bits: int) -> None:
    print("== exact recurrent transfer operator ==")
    print(
        f"B=1,N={atoms},K={max_arity},D={depth_bits}. "
        "Chosen visible bits are the next layer; no selector side channel."
    )
    print(
        f"{'lambda':>7} {'P':>3} {'fail':>8} {'total':>10} {'per pass':>10} "
        f"{'pos':>8} {'final bits':>11} {'growth':>9} {'fut':>9} {'rand':>9} {'lift':>9} {'descs':>9}"
    )
    for row in rows:
        print(
            f"{row.lambda_value:7.2f} {row.passes:3d} {row.fail_rate:8.6f} "
            f"{row.mean_total_saving:10.6f} {row.mean_saving_per_pass:10.6f} "
            f"{row.positive_fraction:8.6f} {row.mean_final_bits:11.6f} "
            f"{row.mean_growth_ratio:9.6f} {row.mean_first_future:9.6f} "
            f"{row.mean_first_random_future:9.6f} {row.mean_first_lift_vs_random:9.6f} "
            f"{row.mean_description_count:9.3f}"
        )
    print()


def print_reading(rows: list[TransferRow]) -> None:
    zero_fail = [row for row in rows if row.fail_rate == 0.0]
    print("== reading ==")
    print(
        "The transfer objective can pick genotypes with better next-pass fertility, "
        "but the current layer pays their visible length. The pass loop is the "
        "hard check: does the chosen representation keep shrinking?"
    )
    if not zero_fail:
        print(
            "No zero-failure recurrent row exists in this bounded exact run. "
            "That means the visible strings chosen in pass one are outside the "
            "small record family's next-pass support or exceed the cap."
        )
        return
    best = max(zero_fail, key=lambda row: row.mean_total_saving)
    print(
        f"Best zero-failure row here is lambda={best.lambda_value:.2f}, "
        f"P={best.passes}, total saving {best.mean_total_saving:.6f} bits/word "
        f"({best.mean_saving_per_pass:.6f} bits/pass)."
    )
    if best.mean_total_saving <= 0.0:
        print(
            "Since every zero-failure row is negative in this exact toy, the "
            "observed neutral future lift remains a source/fertility signal "
            "rather than a source-free recursive compressor."
        )
    else:
        print(
            "This row is positive and needs a larger exact rerun plus random "
            "same-length controls before it can be promoted."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=5)
    parser.add_argument("--max-arity", type=int, default=3)
    parser.add_argument("--depth-bits", type=int, default=3)
    parser.add_argument("--seed", type=int, default=96000)
    parser.add_argument("--max-bits", type=int, default=28)
    parser.add_argument("--lambda-value", type=float, action="append", default=[])
    parser.add_argument("--passes", type=int, action="append", default=[])
    args = parser.parse_args()

    rows = run_rows(
        atoms=args.atoms,
        max_arity=args.max_arity,
        depth_bits=args.depth_bits,
        seed=args.seed,
        max_bits=args.max_bits,
        lambdas=tuple(args.lambda_value) if args.lambda_value else (0.0, 1.0, 2.0),
        pass_counts=tuple(args.passes) if args.passes else (2,),
    )
    print_rows(rows, args.atoms, args.max_arity, args.depth_bits)
    print_reading(rows)


if __name__ == "__main__":
    main()
