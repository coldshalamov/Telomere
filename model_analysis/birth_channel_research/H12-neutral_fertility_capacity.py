#!/usr/bin/env python3
"""Neutral witness multiplicity capacity for recursive fertility.

Total-Cover H9 fixed slack makes witness width decoder-derived:

    W = min(D, arity * B - slack)

If a selected span has more than one matching seed inside the same W-bit
witness space, the encoder may choose among those seed witnesses without
changing decode length or the previous-layer bytes. H12 prices only the
capacity of that neutral choice:

    M ~ Binomial(2^W, 2^-L) | M >= 1
      ~= Poisson(lambda=2^(W-L)) | M >= 1

    neutral_bits = E[log2(M) | M >= 1]

This is not counted as immediate compression. It is an optimistic upper bound
on future-fertility capacity: even if every neutral bit saved one future bit,
does it cover the paid H9 miss?
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
from total_cover_public_model_kernel import Cover  # noqa: E402


H9_PATH = Path(__file__).with_name("H9-total_cover_fixed_slack.py")


def load_h9() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h9_total_cover_fixed_slack", H9_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H9 kernel from {H9_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H9 = load_h9()


@dataclass(frozen=True)
class CapacityRow:
    slack: int
    coverage: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    avg_lambda: float
    neutral_bits_per_record: float
    neutral_bits_per_atom: float
    perfect_credit_gain_per_atom: float
    residual_missing_bits_per_record: float


def poisson_log2_m_given_nonzero(lam: float) -> float:
    """E[log2(M) | M>=1] for M~Poisson(lam)."""

    if lam <= 0.0:
        return 0.0
    if lam > 700.0:
        # More than enough for our grids. First-order delta-method fallback.
        return max(0.0, math.log2(lam) - 0.5 / (lam * math.log(2.0)))

    p0 = math.exp(-lam)
    denom = -math.expm1(-lam)
    if denom <= 0.0:
        return 0.0

    total = 0.0
    prob = p0
    limit = max(64, int(lam + 12.0 * math.sqrt(max(lam, 1.0)) + 16.0))
    for count in range(1, limit + 1):
        prob *= lam / count
        total += math.log2(count) * prob
    return total / denom


def neutral_bits_for_record(target_bits: int, width_bits: int) -> tuple[float, float]:
    diff = width_bits - target_bits
    lam = math.ldexp(1.0, diff) if -1074 <= diff <= 1023 else (0.0 if diff < 0 else float("inf"))
    if not math.isfinite(lam):
        return lam, max(0.0, diff)
    return lam, poisson_log2_m_given_nonzero(lam)


def evaluate_slack(
    train_samples: list[list[list[EdgeSample]]],
    eval_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    slack: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
) -> CapacityRow:
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
    eval_covers: list[Cover] = [
        H9.cover_with_slack(trial, block_bits, max_arity, frontier, model, slack, flush_bits)
        for trial in eval_samples
    ]
    h9_row = H9.summarize(slack, train_covers, eval_covers, block_bits)
    covered = [cover for cover in eval_covers if cover.covered]
    if not covered:
        return CapacityRow(
            slack=slack,
            coverage=h9_row.coverage,
            eval_gain_per_atom=float("-inf"),
            missing_bits_per_record=float("inf"),
            records_per_atom=0.0,
            avg_arity=0.0,
            avg_width=0.0,
            avg_lambda=0.0,
            neutral_bits_per_record=0.0,
            neutral_bits_per_atom=0.0,
            perfect_credit_gain_per_atom=float("-inf"),
            residual_missing_bits_per_record=float("inf"),
        )

    neutral_bits = []
    lambdas = []
    records = [record for cover in covered for record in cover.records]
    for record in records:
        lam, bits = neutral_bits_for_record(record.target_bits, record.local_payload_bits)
        lambdas.append(lam)
        neutral_bits.append(bits)

    neutral_per_record = mean(neutral_bits) if neutral_bits else 0.0
    neutral_per_atom = h9_row.records_per_atom * neutral_per_record
    perfect_gain = h9_row.eval_gain_per_atom + neutral_per_atom
    residual = max(0.0, h9_row.missing_bits_per_record - neutral_per_record)

    return CapacityRow(
        slack=slack,
        coverage=h9_row.coverage,
        eval_gain_per_atom=h9_row.eval_gain_per_atom,
        missing_bits_per_record=h9_row.missing_bits_per_record,
        records_per_atom=h9_row.records_per_atom,
        avg_arity=h9_row.avg_arity,
        avg_width=h9_row.avg_width_bits,
        avg_lambda=mean(lambdas) if lambdas else 0.0,
        neutral_bits_per_record=neutral_per_record,
        neutral_bits_per_atom=neutral_per_atom,
        perfect_credit_gain_per_atom=perfect_gain,
        residual_missing_bits_per_record=residual,
    )


def render(rows: list[CapacityRow], block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Neutral-Fertility Capacity Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Neutral bits are `E[log2(M) | M>=1]` for matching seeds inside the",
        "same fixed-width H9 witness bucket. The `perfect credit` column is an",
        "optimistic upper bound that pretends every neutral bit saves one future",
        "bit. It is not an achieved compression result.",
        "",
        "| slack | cover | gain/atom | missing bits/rec | rec/atom | avg arity | avg width | avg lambda | neutral bits/rec | neutral bits/atom | perfect credit gain/atom | residual miss/rec |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.slack} | {row.coverage:.3f} | {row.eval_gain_per_atom:.6f} | "
            f"{row.missing_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | {row.avg_lambda:.3f} | "
            f"{row.neutral_bits_per_record:.3f} | {row.neutral_bits_per_atom:.6f} | "
            f"{row.perfect_credit_gain_per_atom:.6f} | {row.residual_missing_bits_per_record:.3f} |"
        )

    best_capacity = max(rows, key=lambda row: row.perfect_credit_gain_per_atom)
    best_actual = max(rows, key=lambda row: (row.coverage >= 1.0, row.eval_gain_per_atom))
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Best actual paid row: slack `{best_actual.slack}` at "
            f"`{best_actual.eval_gain_per_atom:.6f}` bits/input atom.",
            f"Best perfect-neutral-credit row: slack `{best_capacity.slack}` at "
            f"`{best_capacity.perfect_credit_gain_per_atom:.6f}` bits/input atom, "
            f"with residual `{best_capacity.residual_missing_bits_per_record:.3f}` bits/record.",
            "A positive perfect-credit row is only a capacity flag. A negative",
            "perfect-credit row would close this neutral-fertility variant.",
        ]
    )
    return "\n".join(lines)


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
    parser.add_argument("--slacks", type=int, nargs="+", default=[-4, -3, -2, -1, 0, 1, 2])
    parser.add_argument("--seed", type=int, default=2609)
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
    rows = [
        evaluate_slack(
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
    print(render(rows, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
