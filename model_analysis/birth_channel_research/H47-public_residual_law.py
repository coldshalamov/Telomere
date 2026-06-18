#!/usr/bin/env python3
"""H47 - frozen public residual law for high-arity Total-Cover.

H11 tested a low-dimensional selected-order-statistic law directly:

    width ~= min of m_eff public first-hit draws

H47 tests the next systematic refinement. It centers each selected width on
that public lattice/Gumbel-style mode, then arithmetic-codes the residual with
a small public table trained on independent uniform-law covers and frozen before
held-out evaluation.

This is still a Total-Cover branch:

* every record opens;
* no birth/open/carry channel is charged;
* no hit bitmap or final-position note exists;
* the stream is still [arity][seed witness].

The only question is whether a richer public residual law can honestly save
the remaining ~1.36 bits per selected record without using target-file-specific
hidden candidate counts.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402
from total_cover_public_model_kernel import Cover, selected_rank_bits  # noqa: E402


H11_PATH = Path(__file__).with_name("H11-total_cover_order_stat_delta.py")


def load_h11() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h11_total_cover_order_stat_delta", H11_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H11 kernel from {H11_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H11 = load_h11()


@dataclass(frozen=True)
class ResidualLaw:
    name: str
    m_kind: str
    context: str
    value: float = 1.0

    def m_eff(self, remaining: int, arity: int, max_arity: int) -> float:
        legal = max(1, min(max_arity, remaining))
        if self.m_kind == "constant":
            return max(1.0, self.value)
        if self.m_kind == "legal":
            return float(legal)
        if self.m_kind == "sqrt_legal":
            return math.sqrt(float(legal))
        if self.m_kind == "arity":
            return float(max(1, arity))
        if self.m_kind == "sqrt_arity":
            return math.sqrt(float(max(1, arity)))
        raise ValueError(self.m_kind)


@dataclass(frozen=True)
class ResidualModel:
    law: ResidualLaw
    arity_counts: dict[int, Counter[int]]
    residual_counts: dict[tuple[int, ...], Counter[int]]
    max_arity: int
    frontier: int
    alpha: float


@dataclass(frozen=True)
class ResidualRow:
    law: ResidualLaw
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    coverage: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    rank_bits_per_record: float
    arity_bits_per_record: float
    residual_bits_per_record: float


def arity_bucket(arity: int) -> int:
    if arity <= 1:
        return 0
    return min(8, int(math.log2(arity)))


def remaining_bucket(remaining: int, max_arity: int) -> int:
    if remaining <= max_arity:
        return remaining
    ratio = (remaining + max_arity - 1) // max_arity
    return max_arity + min(16, int(math.log2(ratio)) + 1)


def context_for(law: ResidualLaw, remaining: int, arity: int, max_arity: int) -> tuple[int, ...]:
    if law.context == "global":
        return ()
    if law.context == "arity_bucket":
        return (arity_bucket(arity),)
    if law.context == "arity_exact":
        return (arity,)
    if law.context == "remaining_arity_bucket":
        return (remaining_bucket(remaining, max_arity), arity_bucket(arity))
    if law.context == "remaining_arity_exact":
        return (remaining_bucket(remaining, max_arity), arity)
    raise ValueError(law.context)


@lru_cache(maxsize=None)
def modal_width(target_bits: int, frontier: int, m_milli: int) -> int:
    """Mode of the public selected-width law from H11."""

    m_eff = m_milli / 1000.0
    best_width = 1
    best_logp = float("-inf")
    for width in range(1, frontier + 1):
        logp = H11.selected_width_logprob(target_bits, width, frontier, m_eff)
        if logp > best_logp:
            best_logp = logp
            best_width = width
    return best_width


def residual_for(
    law: ResidualLaw,
    remaining: int,
    arity: int,
    max_arity: int,
    target_bits: int,
    width: int,
    frontier: int,
) -> int:
    m_milli = max(1000, round(law.m_eff(remaining, arity, max_arity) * 1000.0))
    return width - modal_width(target_bits, frontier, m_milli)


def arity_cost(model: ResidualModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.arity_counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def residual_cost(
    model: ResidualModel,
    remaining: int,
    arity: int,
    target_bits: int,
    width: int,
) -> float:
    context = context_for(model.law, remaining, arity, model.max_arity)
    residual = residual_for(
        model.law,
        remaining,
        arity,
        model.max_arity,
        target_bits,
        width,
        model.frontier,
    )
    counts = model.residual_counts.get(context, Counter())
    denom = sum(counts.values()) + model.alpha * model.frontier
    return -math.log2((counts.get(residual, 0) + model.alpha) / denom)


def code_cost(
    edge: EdgeSample,
    arity: int,
    remaining: int,
    model: ResidualModel,
    rank_code: str,
) -> float:
    record = SelectedRecord(
        arity=arity,
        rank=edge.rank,
        target_bits=edge.target_bits,
        lotus_payload_width=edge.lotus_payload_width,
        local_payload_bits=edge.local_payload_bits,
        cost_bits=0.0,
    )
    return (
        selected_rank_bits(record, rank_code)
        + arity_cost(model, remaining, arity)
        + residual_cost(model, remaining, arity, edge.target_bits, edge.lotus_payload_width)
    )


def cover_with_model(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
    model: ResidualModel,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity or edge.lotus_payload_width > frontier:
                continue
            cost = code_cost(edge, arity, remaining, model, rank_code)
            if cost == float("inf"):
                continue
            candidate = base + cost
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, cost)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())

    records: list[SelectedRecord] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, cost = entry
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=cost,
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms] + flush_bits, tuple(records))


def fit_model(
    law: ResidualLaw,
    covers: list[Cover],
    max_arity: int,
    frontier: int,
    alpha: float,
) -> ResidualModel:
    arity_counts: dict[int, Counter[int]] = {}
    residual_counts: dict[tuple[int, ...], Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_counts.setdefault(remaining, Counter())[record.arity] += 1
            context = context_for(law, remaining, record.arity, max_arity)
            residual = residual_for(
                law,
                remaining,
                record.arity,
                max_arity,
                record.target_bits,
                record.lotus_payload_width,
                frontier,
            )
            residual_counts.setdefault(context, Counter())[residual] += 1
            consumed += record.arity
    return ResidualModel(law, arity_counts, residual_counts, max_arity, frontier, alpha)


def train_model(
    samples: list[list[list[EdgeSample]]],
    law: ResidualLaw,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> tuple[ResidualModel, list[Cover]]:
    model = ResidualModel(law, {}, {}, max_arity, frontier, alpha)
    covers: list[Cover] = []
    for _ in range(iterations):
        covers = [
            cover_with_model(trial, max_arity, frontier, model, flush_bits, rank_code)
            for trial in samples
        ]
        model = fit_model(law, covers, max_arity, frontier, alpha)
    return model, covers


def gain(covers: list[Cover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    law: ResidualLaw,
    model: ResidualModel,
    train_covers: list[Cover],
    eval_covers: list[Cover],
    block_bits: int,
    atoms: int,
    rank_code: str,
) -> ResidualRow:
    covered = [cover for cover in eval_covers if cover.covered]
    coverage = len(covered) / len(eval_covers) if eval_covers else 0.0
    if not covered:
        return ResidualRow(law, gain(train_covers, block_bits, atoms), float("-inf"), float("inf"), coverage, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    eval_gain = gain(covered, block_bits, atoms)
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    all_records = [record for cover in covered for record in cover.records]
    rank_bits = [selected_rank_bits(record, rank_code) for record in all_records]
    arity_bits: list[float] = []
    residual_bits: list[float] = []
    for cover in covered:
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_bits.append(arity_cost(model, remaining, record.arity))
            residual_bits.append(
                residual_cost(
                    model,
                    remaining,
                    record.arity,
                    record.target_bits,
                    record.lotus_payload_width,
                )
            )
            consumed += record.arity

    return ResidualRow(
        law=law,
        train_gain_per_atom=gain(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        coverage=coverage,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in all_records),
        avg_width=mean(record.lotus_payload_width for record in all_records),
        rank_bits_per_record=mean(rank_bits),
        arity_bits_per_record=mean(arity_bits),
        residual_bits_per_record=mean(residual_bits),
    )


def default_laws() -> list[ResidualLaw]:
    laws: list[ResidualLaw] = []
    for value in (1.0, 4.0, 8.0, 16.0):
        laws.append(ResidualLaw(f"m{value:g}/arity_bucket", "constant", "arity_bucket", value))
    laws.extend(
        [
            ResidualLaw("legal/remaining_arity_bucket", "legal", "remaining_arity_bucket"),
            ResidualLaw("arity/remaining_arity_bucket", "arity", "remaining_arity_bucket"),
        ]
    )
    return laws


def render(rows: list[ResidualRow], selected: ResidualRow, block_bits: int, max_arity: int, frontier: int) -> str:
    best_eval = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines = [
        "# Frozen Public Residual-Law Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Each law centers width on the public H11 selected-extreme mode, then",
        "codes the residual with an independent-training public table. The",
        "train-selected row is the honest frozen-profile result; best held-out",
        "row is diagnostic only.",
        "",
        "| law | cover | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | rank bits/rec | arity bits/rec | residual bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        marker = "*" if row.law == selected.law else ""
        lines.append(
            f"| {row.law.name}{marker} | {row.coverage:.3f} | "
            f"{row.train_gain_per_atom:.6f} | {row.eval_gain_per_atom:.6f} | "
            f"{row.missing_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | "
            f"{row.rank_bits_per_record:.3f} | {row.arity_bits_per_record:.3f} | "
            f"{row.residual_bits_per_record:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Train-selected law: `{selected.law.name}` with held-out gain "
            f"`{selected.eval_gain_per_atom:.6f}` bits/input atom and missing "
            f"`{selected.missing_bits_per_record:.3f}` bits/record.",
            f"Best held-out diagnostic law: `{best_eval.law.name}` with "
            f"`{best_eval.eval_gain_per_atom:.6f}` bits/input atom.",
            "A positive train-selected row would be a candidate paid public",
            "Total-Cover witness language. A negative row means the extra",
            "residual structure still does not capture the missing record bits.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--train-trials", type=int, default=8)
    parser.add_argument("--eval-trials", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument("--train-seed", type=int, default=2603)
    parser.add_argument("--eval-seeds", type=int, nargs="+", default=[3701, 4801])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.train_seed + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples: list[list[list[EdgeSample]]] = []
    for seed in args.eval_seeds:
        eval_samples.extend(
            generate_samples(
                args.block_bits,
                args.max_arity,
                args.atoms,
                args.eval_trials,
                seed + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
            )
        )

    rows: list[ResidualRow] = []
    for law in default_laws():
        model, train_covers = train_model(
            train_samples,
            law,
            args.max_arity,
            args.frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        eval_covers = [
            cover_with_model(trial, args.max_arity, args.frontier, model, args.flush_bits, args.rank_code)
            for trial in eval_samples
        ]
        rows.append(
            summarize(
                law,
                model,
                train_covers,
                eval_covers,
                args.block_bits,
                args.atoms,
                args.rank_code,
            )
        )
    selected = max(rows, key=lambda row: row.train_gain_per_atom)
    print(render(rows, selected, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
