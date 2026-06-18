#!/usr/bin/env python3
"""Public parametric delta/slack models for high-arity Total-Cover.

H5/H6 narrowed the live high-arity Total-Cover bill to payload width/slack:

    delta = arity * B - payload_width

This kernel tests whether that bill is an artifact of sparse suffix tables or a
real entropy channel. It keeps Total-Cover semantics: every record opens, no
birth/open/carry cost, no sparse cover map, no per-file counts.

Delta modes:

* ``suffix``: H6-style P(delta | exact remaining, exact arity)
* ``global``: public selected-delta table shared by all arities
* ``arity``: public selected-delta table by arity only
* ``raw``: analytic first-hit width law under the uniform hash law
* ``tilted``: raw first-hit law tilted by a single public beta fit on
  independent selected covers

All empirical tables and beta are trained only on independent uniform-law
samples, then evaluated on held-out samples.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402
from total_cover_public_model_kernel import Cover, selected_rank_bits  # noqa: E402


LN2 = math.log(2.0)


@dataclass(frozen=True)
class DeltaModel:
    mode: str
    arity_counts: dict[int, Counter[int]]
    suffix_delta_counts: dict[tuple[int, int], Counter[int]]
    arity_delta_counts: dict[int, Counter[int]]
    global_delta_counts: Counter[int]
    max_arity: int
    frontier: int
    alpha: float
    beta: float = 0.0


@dataclass(frozen=True)
class EvalRow:
    mode: str
    beta: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    rank_bits_per_record: float
    arity_bits_per_record: float
    delta_bits_per_record: float
    gain_per_atom: float
    missing_bits_per_record: float


def payload_width_count_le(width: int) -> int:
    if width < 1:
        return 0
    return (1 << (width + 1)) - 3


def logsubexp(log_a: float, log_b: float) -> float:
    """Return log(exp(log_a)-exp(log_b)) for log_a >= log_b."""

    if log_b == float("-inf"):
        return log_a
    if log_b > log_a:
        log_a, log_b = log_b, log_a
    gap = log_b - log_a
    if gap >= -1e-15:
        return float("-inf")
    if gap < -745.0:
        return log_a
    return log_a + math.log1p(-math.exp(gap))


@lru_cache(maxsize=None)
def raw_width_logprob(target_bits: int, width: int, frontier: int) -> float:
    """Natural log P(payload_width=width | payload_width<=frontier).

    The first-hit rank R is geometric with p=2^-target_bits. Width ``w`` means
    R lies in (count_le(w-1), count_le(w)]. For the target sizes used here,
    the exponential race approximation is numerically stable and matches the
    uniform-law sampler used by the Total-Cover kernels.
    """

    if width < 1 or width > frontier:
        return float("-inf")
    lo = payload_width_count_le(width - 1) + 1
    hi = payload_width_count_le(width)
    hi_frontier = payload_width_count_le(frontier)
    q = math.ldexp(1.0, -target_bits)
    log_surv_before = -(lo - 1) * q
    log_surv_after = -hi * q
    log_mass = logsubexp(log_surv_before, log_surv_after)
    log_legal = logsubexp(0.0, -hi_frontier * q)
    return log_mass - log_legal


@lru_cache(maxsize=None)
def tilted_log_z(target_bits: int, frontier: int, beta_centi: int) -> float:
    beta = beta_centi / 100.0
    values = []
    for width in range(1, frontier + 1):
        delta = target_bits - width
        values.append(raw_width_logprob(target_bits, width, frontier) + beta * delta * LN2)
    m = max(values)
    return m + math.log(sum(math.exp(value - m) for value in values))


def raw_or_tilted_delta_cost(target_bits: int, width: int, frontier: int, beta: float) -> float:
    beta_centi = round(beta * 100)
    delta = target_bits - width
    logp = raw_width_logprob(target_bits, width, frontier)
    if beta_centi:
        logp = logp + (beta_centi / 100.0) * delta * LN2 - tilted_log_z(target_bits, frontier, beta_centi)
    return -logp / LN2


def arity_cost(model: DeltaModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.arity_counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def table_delta_cost(counts: Counter[int], model: DeltaModel, target_bits: int, delta: int) -> float:
    lo = target_bits - model.frontier
    hi = target_bits - 1
    denom_count = sum(count for value, count in counts.items() if lo <= value <= hi)
    denom = denom_count + model.alpha * model.frontier
    return -math.log2((counts.get(delta, 0) + model.alpha) / denom)


def delta_cost(model: DeltaModel, block_bits: int, remaining: int, arity: int, width: int) -> float:
    target_bits = arity * block_bits
    delta = target_bits - width
    if model.mode == "suffix":
        return table_delta_cost(model.suffix_delta_counts.get((remaining, arity), Counter()), model, target_bits, delta)
    if model.mode == "global":
        return table_delta_cost(model.global_delta_counts, model, target_bits, delta)
    if model.mode == "arity":
        return table_delta_cost(model.arity_delta_counts.get(arity, Counter()), model, target_bits, delta)
    if model.mode == "raw":
        return raw_or_tilted_delta_cost(target_bits, width, model.frontier, 0.0)
    if model.mode == "tilted":
        return raw_or_tilted_delta_cost(target_bits, width, model.frontier, model.beta)
    raise ValueError(model.mode)


def code_cost(model: DeltaModel, block_bits: int, remaining: int, arity: int, edge: EdgeSample, rank_code: str) -> float:
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
        + delta_cost(model, block_bits, remaining, arity, edge.lotus_payload_width)
    )


def cover_with_model(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: DeltaModel,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity or edge.lotus_payload_width > frontier:
                continue
            candidate = base + code_cost(model, block_bits, remaining, arity, edge, rank_code)
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())
    records: list[SelectedRecord] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge = entry
        cost = code_cost(model, block_bits, atoms - prior, arity, edge, rank_code)
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


def fit_beta(records: list[SelectedRecord], frontier: int) -> float:
    if not records:
        return 0.0
    best_beta = 0.0
    best_cost = float("inf")
    for index in range(0, 401):
        beta = index / 100.0
        cost = 0.0
        for record in records:
            cost += raw_or_tilted_delta_cost(
                record.target_bits,
                record.lotus_payload_width,
                frontier,
                beta,
            )
        if cost < best_cost:
            best_cost = cost
            best_beta = beta
    return best_beta


def fit_model(
    mode: str,
    covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    alpha: float,
) -> DeltaModel:
    arity_counts: dict[int, Counter[int]] = {}
    suffix_delta_counts: dict[tuple[int, int], Counter[int]] = {}
    arity_delta_counts: dict[int, Counter[int]] = {}
    global_delta_counts: Counter[int] = Counter()
    all_records: list[SelectedRecord] = []
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            delta = record.arity * block_bits - record.lotus_payload_width
            arity_counts.setdefault(remaining, Counter())[record.arity] += 1
            suffix_delta_counts.setdefault((remaining, record.arity), Counter())[delta] += 1
            arity_delta_counts.setdefault(record.arity, Counter())[delta] += 1
            global_delta_counts[delta] += 1
            all_records.append(record)
            consumed += record.arity
    beta = fit_beta(all_records, frontier) if mode == "tilted" else 0.0
    return DeltaModel(
        mode=mode,
        arity_counts=arity_counts,
        suffix_delta_counts=suffix_delta_counts,
        arity_delta_counts=arity_delta_counts,
        global_delta_counts=global_delta_counts,
        max_arity=max_arity,
        frontier=frontier,
        alpha=alpha,
        beta=beta,
    )


def train_model(
    mode: str,
    train_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> DeltaModel:
    model = DeltaModel(mode, {}, {}, {}, Counter(), max_arity, frontier, alpha)
    for _ in range(iterations):
        covers = [
            cover_with_model(trial, block_bits, max_arity, frontier, model, flush_bits, rank_code)
            for trial in train_samples
        ]
        model = fit_model(mode, covers, block_bits, max_arity, frontier, alpha)
    return model


def summarize(
    mode: str,
    model: DeltaModel,
    covers: list[Cover],
    block_bits: int,
    rank_code: str,
    flush_bits: float,
) -> EvalRow:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return EvalRow(mode, model.beta, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, float("-inf"), float("inf"))
    atoms = sum(record.arity for record in covered[0].records)
    raw_bits = atoms * block_bits
    gains = [(raw_bits - cover.charged_bits) / atoms for cover in covered]
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    all_records = [record for cover in covered for record in cover.records]
    rank_bits = mean(selected_rank_bits(record, rank_code) for record in all_records)
    arity_bits = []
    delta_bits = []
    for cover in covered:
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_bits.append(arity_cost(model, remaining, record.arity))
            delta_bits.append(delta_cost(model, block_bits, remaining, record.arity, record.lotus_payload_width))
            consumed += record.arity
    gain = mean(gains)
    missing = max(0.0, -gain / records_per_atom) if records_per_atom else float("inf")
    return EvalRow(
        mode=mode,
        beta=model.beta,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in all_records),
        avg_width=mean(record.lotus_payload_width for record in all_records),
        rank_bits_per_record=rank_bits,
        arity_bits_per_record=mean(arity_bits) + (flush_bits / len(all_records) if all_records else 0.0),
        delta_bits_per_record=mean(delta_bits),
        gain_per_atom=gain,
        missing_bits_per_record=missing,
    )


def render(rows: list[EvalRow], block_bits: int, max_arity: int, frontier: int, alpha: float) -> str:
    lines = [
        "# Parametric Delta Total-Cover Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`, `alpha={alpha}`.",
        "",
        "| delta mode | beta | gain/atom | missing bits/rec | rec/atom | avg arity | avg width | rank bits/rec | arity bits/rec | delta bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.beta:.2f} | {row.gain_per_atom:.6f} | "
            f"{row.missing_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | {row.rank_bits_per_record:.3f} | "
            f"{row.arity_bits_per_record:.3f} | {row.delta_bits_per_record:.3f} |"
        )
    best = max(rows, key=lambda row: row.gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Best paid mode: `{best.mode}` at `{best.gain_per_atom:.6f}` bits/input atom.",
            "A positive row would be a candidate paid Total-Cover witness language.",
            "A negative row means the delta/slack bill is still real under that",
            "public model.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=32)
    parser.add_argument("--eval-trials", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["suffix", "global", "arity", "raw", "tilted"],
        default=["suffix", "global", "arity", "raw", "tilted"],
    )
    parser.add_argument("--seed", type=int, default=1201)
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
    rows = []
    for mode in args.modes:
        model = train_model(
            mode,
            train_samples,
            args.block_bits,
            args.max_arity,
            args.frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        covers = [
            cover_with_model(
                trial,
                args.block_bits,
                args.max_arity,
                args.frontier,
                model,
                args.flush_bits,
                args.rank_code,
            )
            for trial in eval_samples
        ]
        rows.append(summarize(mode, model, covers, args.block_bits, args.rank_code, args.flush_bits))
    print(render(rows, args.block_bits, args.max_arity, args.frontier, args.alpha))


if __name__ == "__main__":
    main()
