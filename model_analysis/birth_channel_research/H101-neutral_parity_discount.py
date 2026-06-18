#!/usr/bin/env python3
"""H101 - neutral multiplicity as a parity discount.

H100 found that a forced two-epoch stateless lane needs a seed-class bit:

    current pass births class t mod 2
    decoder opens that class and carries the other class once

Naively, accepting only one seed class costs 1 bit/record of match supply. But
if a selected span has many matching seeds inside the same fixed witness bucket,
the encoder may be able to choose a seed with the desired class at less than a
full 1-bit penalty.

For one record with Poisson match intensity:

    lambda = 2^(witness_width - target_bits)

the probability of at least one match is:

    p_all = 1 - exp(-lambda)

and the probability of at least one match in a specific C=2^c seed class is:

    p_class = 1 - exp(-lambda / C)

The Kraft-equivalent class penalty is:

    class_loss = -log2(p_class / p_all)

This tends to c bits when lambda is tiny and tends to 0 when lambda is huge.
H101 asks whether this discount can make the H100 parity layer affordable after
the extra witness width needed to create neutral multiplicity is already paid.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, generate_samples  # noqa: E402


H9_PATH = Path(__file__).with_name("H9-total_cover_fixed_slack.py")
H12_PATH = Path(__file__).with_name("H12-neutral_fertility_capacity.py")


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H9 = load_module("h9_total_cover_fixed_slack_for_h101", H9_PATH)
H12 = load_module("h12_neutral_fertility_capacity_for_h101", H12_PATH)


@dataclass(frozen=True)
class Row:
    slack: int
    class_bits: int
    coverage: float
    gain_per_atom: float
    records_per_atom: float
    base_margin_per_record: float
    missing_bits_per_record: float
    avg_lambda: float
    neutral_bits_per_record: float
    class_loss_per_record: float
    one_bit_parity_net_atom: float
    discounted_parity_net_atom: float
    margin_after_discount_per_record: float


@dataclass(frozen=True)
class SlackEval:
    slack: int
    coverage: float
    gain_per_atom: float
    records_per_atom: float
    base_margin_per_record: float
    missing_bits_per_record: float
    lambdas: tuple[float, ...]
    neutral_bits: tuple[float, ...]


def class_loss_for_lambda(lam: float, class_bits: int) -> float:
    if lam <= 0.0:
        return float(class_bits)
    classes = 1 << class_bits
    p_all = -math.expm1(-lam)
    p_class = -math.expm1(-(lam / classes))
    if p_all <= 0.0 or p_class <= 0.0:
        return float(class_bits)
    return -math.log2(p_class / p_all)


def collect_slack_eval(
    train_samples: list[list[list[EdgeSample]]],
    eval_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    slack: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
) -> SlackEval:
    model, train_covers = H9.train_model(
        train_samples,
        block_bits,
        max_arity,
        frontier,
        slack,
        iterations,
        alpha,
        flush_bits,
    )
    eval_covers = [
        H9.cover_with_slack(trial, block_bits, max_arity, frontier, model, slack, flush_bits)
        for trial in eval_samples
    ]
    h9_row = H9.summarize(slack, train_covers, eval_covers, block_bits)
    records = [record for cover in eval_covers if cover.covered for record in cover.records]
    if not records or h9_row.records_per_atom <= 0.0:
        return SlackEval(
            slack=slack,
            coverage=h9_row.coverage,
            gain_per_atom=float("-inf"),
            records_per_atom=0.0,
            base_margin_per_record=float("-inf"),
            missing_bits_per_record=float("inf"),
            lambdas=(),
            neutral_bits=(),
        )

    lambdas: list[float] = []
    neutral_bits: list[float] = []
    for record in records:
        lam, bits = H12.neutral_bits_for_record(record.target_bits, record.local_payload_bits)
        if not math.isfinite(lam):
            lam = 2.0 ** max(-1023, min(1023, record.local_payload_bits - record.target_bits))
        lambdas.append(lam)
        neutral_bits.append(bits)

    margin = h9_row.eval_gain_per_atom / h9_row.records_per_atom
    return SlackEval(
        slack=slack,
        coverage=h9_row.coverage,
        gain_per_atom=h9_row.eval_gain_per_atom,
        records_per_atom=h9_row.records_per_atom,
        base_margin_per_record=margin,
        missing_bits_per_record=h9_row.missing_bits_per_record,
        lambdas=tuple(lambdas),
        neutral_bits=tuple(neutral_bits),
    )


def row_from_slack(slack_eval: SlackEval, class_bits: int) -> Row:
    if not slack_eval.lambdas or slack_eval.records_per_atom <= 0.0:
        return Row(
            slack=slack_eval.slack,
            class_bits=class_bits,
            coverage=slack_eval.coverage,
            gain_per_atom=float("-inf"),
            records_per_atom=0.0,
            base_margin_per_record=float("-inf"),
            missing_bits_per_record=float("inf"),
            avg_lambda=0.0,
            neutral_bits_per_record=0.0,
            class_loss_per_record=float(class_bits),
            one_bit_parity_net_atom=float("-inf"),
            discounted_parity_net_atom=float("-inf"),
            margin_after_discount_per_record=float("-inf"),
        )

    class_losses = [class_loss_for_lambda(lam, class_bits) for lam in slack_eval.lambdas]
    class_loss = mean(class_losses)
    neutral = mean(slack_eval.neutral_bits)
    margin = slack_eval.base_margin_per_record
    return Row(
        slack=slack_eval.slack,
        class_bits=class_bits,
        coverage=slack_eval.coverage,
        gain_per_atom=slack_eval.gain_per_atom,
        records_per_atom=slack_eval.records_per_atom,
        base_margin_per_record=margin,
        missing_bits_per_record=slack_eval.missing_bits_per_record,
        avg_lambda=mean(slack_eval.lambdas),
        neutral_bits_per_record=neutral,
        class_loss_per_record=class_loss,
        one_bit_parity_net_atom=slack_eval.gain_per_atom - slack_eval.records_per_atom * class_bits,
        discounted_parity_net_atom=slack_eval.gain_per_atom - slack_eval.records_per_atom * class_loss,
        margin_after_discount_per_record=margin - class_loss,
    )


def print_rows(rows: list[Row]) -> None:
    print("== neutral parity discount ==")
    print("class loss is -log2(P(class hit)/P(any hit)) under the selected fixed-width bucket.")
    print(
        f"{'s':>4} {'c':>2} {'cover':>6} {'gain/atom':>10} {'margin':>9} "
        f"{'lambda':>9} {'neutral':>8} {'class':>8} {'net/atom':>10} "
        f"{'m-class':>9}"
    )
    for row in rows:
        print(
            f"{row.slack:4d} {row.class_bits:2d} {row.coverage:6.3f} "
            f"{row.gain_per_atom:10.6f} {row.base_margin_per_record:9.3f} "
            f"{row.avg_lambda:9.3f} {row.neutral_bits_per_record:8.3f} "
            f"{row.class_loss_per_record:8.3f} {row.discounted_parity_net_atom:10.6f} "
            f"{row.margin_after_discount_per_record:9.3f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    parity_rows = [row for row in rows if row.class_bits == 1 and math.isfinite(row.discounted_parity_net_atom)]
    best = max(parity_rows, key=lambda row: row.discounted_parity_net_atom)
    cheapest_class = min(parity_rows, key=lambda row: row.class_loss_per_record)
    print("== reading ==")
    print(
        f"Best discounted parity row is slack={best.slack}: net "
        f"{best.discounted_parity_net_atom:.6f} bits/atom, class loss "
        f"{best.class_loss_per_record:.6f} bits/record, base margin "
        f"{best.base_margin_per_record:.6f} bits/record."
    )
    print(
        f"Cheapest parity class row is slack={cheapest_class.slack}: class loss "
        f"{cheapest_class.class_loss_per_record:.6f} bits/record, but base margin "
        f"{cheapest_class.base_margin_per_record:.6f} bits/record."
    )
    print(
        "Neutral multiplicity can make the parity bit cheap only by using wider "
        "witness buckets. In the tested frontier, the width cost overwhelms the "
        "discount before the parity-ready two-epoch lane crosses."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=24)
    parser.add_argument("--eval-trials", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--slacks", type=int, nargs="+", default=[-12, -8, -6, -4, -2, 0, 1, 2])
    parser.add_argument("--class-bits", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--seed", type=int, default=10101)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.seed + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.eval_trials,
        args.seed + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
    )
    slack_evals = [
        collect_slack_eval(
            train_samples,
            eval_samples,
            args.block_bits,
            args.max_arity,
            args.frontier,
            slack,
            args.iterations,
            args.alpha,
            args.flush_bits,
        )
        for slack in args.slacks
    ]
    rows = [
        row_from_slack(slack_eval, class_bits)
        for slack_eval in slack_evals
        for class_bits in args.class_bits
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
