#!/usr/bin/env python3
"""Joint selected-cover partition code for Total-Cover.

H13 tests whether the selected cover can be coded as one normalized public
object instead of as independent record fields. A cover shape is the sequence:

    (arity_1, width_1), ..., (arity_m, width_m)

with starts implied by cumulative arity. The exact seed residual is still paid
as ``width`` bits per selected record. The public shape model is:

    q(shape) = product psi(remaining, arity, width) / Z(N)

so the paid code length is:

    sum(width_j) + log2 Z(N) - sum(log2 psi_j)

No unselected candidate edge, per-file histogram, checksum, or target-specific
side channel is available to the decoder.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402
from total_cover_public_model_kernel import Cover  # noqa: E402


LN2 = math.log(2.0)


@dataclass(frozen=True)
class PartitionCover:
    covered: bool
    charged_bits: float
    records: tuple[SelectedRecord, ...]
    shape_bits: float
    payload_bits: float
    logz_bits: float


@dataclass(frozen=True)
class PartitionRow:
    atoms: int
    beta: float
    record_bias: float
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    payload_bits_per_record: float
    shape_bits_per_record: float
    logz_bits_per_record: float
    coverage: float


def payload_width_count_le(width: int) -> int:
    if width < 1:
        return 0
    return (1 << (width + 1)) - 3


def logsubexp(log_a: float, log_b: float) -> float:
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


def logsumexp2(values: list[float]) -> float:
    finite = [value for value in values if value != float("-inf")]
    if not finite:
        return float("-inf")
    peak = max(finite)
    return peak + math.log2(sum(2.0 ** (value - peak) for value in finite))


@lru_cache(maxsize=None)
def raw_width_logprob_nats(target_bits: int, width: int, frontier: int) -> float:
    """Exact geometric log P(width | width<=frontier)."""

    if width < 1 or width > frontier:
        return float("-inf")
    q = math.ldexp(1.0, -target_bits)
    log_one_minus_q = math.log1p(-q)
    lo = payload_width_count_le(width - 1) + 1
    hi = payload_width_count_le(width)
    hi_frontier = payload_width_count_le(frontier)
    log_surv_before = (lo - 1) * log_one_minus_q
    log_surv_after = hi * log_one_minus_q
    log_mass = logsubexp(log_surv_before, log_surv_after)
    log_legal = logsubexp(0.0, hi_frontier * log_one_minus_q)
    return log_mass - log_legal


def milli(value: float) -> int:
    return int(round(value * 1000.0))


@lru_cache(maxsize=None)
def log2_psi(target_bits: int, width: int, frontier: int, beta_milli: int, record_bias_milli: int) -> float:
    """Public edge potential in log2 units."""

    logp = raw_width_logprob_nats(target_bits, width, frontier) / LN2
    beta = beta_milli / 1000.0
    record_bias = record_bias_milli / 1000.0
    return logp + beta * (target_bits - width) + record_bias


@lru_cache(maxsize=None)
def log2_sum_psi(target_bits: int, frontier: int, beta_milli: int, record_bias_milli: int) -> float:
    return logsumexp2([
        log2_psi(target_bits, width, frontier, beta_milli, record_bias_milli)
        for width in range(1, frontier + 1)
    ])


@lru_cache(maxsize=None)
def logz_bits(atoms: int, block_bits: int, max_arity: int, frontier: int, beta_milli: int, record_bias_milli: int) -> float:
    """Semi-Markov partition function over all public cover shapes."""

    dp = [float("-inf")] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("-inf"):
            continue
        remaining = atoms - index
        for arity in range(1, min(max_arity, remaining) + 1):
            target_bits = arity * block_bits
            weight = log2_sum_psi(target_bits, frontier, beta_milli, record_bias_milli)
            end = index + arity
            dp[end] = logsumexp2([dp[end], base + weight])
    return dp[atoms]


def cover_with_partition(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    beta: float,
    record_bias: float,
) -> PartitionCover:
    atoms = len(trial)
    beta_milli = milli(beta)
    record_bias_milli = milli(record_bias)
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
            psi = log2_psi(edge.target_bits, edge.lotus_payload_width, frontier, beta_milli, record_bias_milli)
            if psi == float("-inf"):
                continue
            local = edge.lotus_payload_width - psi
            candidate = base + local
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, psi)
    if dp[atoms] == float("inf"):
        return PartitionCover(False, float("inf"), (), float("inf"), float("inf"), float("inf"))

    records: list[SelectedRecord] = []
    payload_bits = 0.0
    psi_sum = 0.0
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, psi = entry
        payload_bits += edge.lotus_payload_width
        psi_sum += psi
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.lotus_payload_width,
                cost_bits=edge.lotus_payload_width - psi,
            )
        )
        cursor = prior
    records.reverse()
    logz = logz_bits(atoms, block_bits, max_arity, frontier, beta_milli, record_bias_milli)
    shape_bits = logz - psi_sum
    charged = payload_bits + shape_bits
    return PartitionCover(True, charged, tuple(records), shape_bits, payload_bits, logz)


def gain(covers: list[PartitionCover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    atoms: int,
    beta: float,
    record_bias: float,
    train_covers: list[PartitionCover],
    eval_covers: list[PartitionCover],
    block_bits: int,
) -> PartitionRow:
    covered = [cover for cover in eval_covers if cover.covered]
    coverage = len(covered) / len(eval_covers) if eval_covers else 0.0
    if not covered:
        return PartitionRow(atoms, beta, record_bias, float("-inf"), float("-inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, coverage)

    eval_gain = gain(covered, block_bits, atoms)
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    records = [record for cover in covered for record in cover.records]
    record_count = sum(len(cover.records) for cover in covered)
    return PartitionRow(
        atoms=atoms,
        beta=beta,
        record_bias=record_bias,
        train_gain_per_atom=gain(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in records),
        avg_width=mean(record.lotus_payload_width for record in records),
        payload_bits_per_record=sum(cover.payload_bits for cover in covered) / record_count,
        shape_bits_per_record=sum(cover.shape_bits for cover in covered) / record_count,
        logz_bits_per_record=sum(cover.logz_bits for cover in covered) / record_count,
        coverage=coverage,
    )


def evaluate_atoms(args: argparse.Namespace, atoms: int) -> list[PartitionRow]:
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        atoms,
        args.train_trials,
        args.seed + atoms * 1000003 + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        atoms,
        args.eval_trials,
        args.seed + atoms * 917519 + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
    )
    rows: list[PartitionRow] = []
    for beta in args.betas:
        for record_bias in args.record_biases:
            train_covers = [
                cover_with_partition(trial, args.block_bits, args.max_arity, args.frontier, beta, record_bias)
                for trial in train_samples
            ]
            eval_covers = [
                cover_with_partition(trial, args.block_bits, args.max_arity, args.frontier, beta, record_bias)
                for trial in eval_samples
            ]
            rows.append(summarize(atoms, beta, record_bias, train_covers, eval_covers, args.block_bits))
    return rows


def render(all_rows: list[PartitionRow], block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Joint Selected-Cover Partition Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "The shape stream is one normalized semi-Markov cover code. Exact seed",
        "residuals are still paid as `width` bits per record. Train-selected",
        "beta/record-bias is the public-profile result per atom count; best",
        "held-out beta/record-bias is diagnostic only.",
        "",
        "| N | beta | record bias | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | payload bits/rec | shape bits/rec | logZ bits/rec | cover |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in all_rows:
        rows_for_n = [candidate for candidate in all_rows if candidate.atoms == row.atoms]
        selected = max(rows_for_n, key=lambda candidate: candidate.train_gain_per_atom)
        marker = "*" if row == selected else ""
        lines.append(
            f"| {row.atoms} | {row.beta:.3f}{marker} | {row.record_bias:.3f} | {row.train_gain_per_atom:.6f} | "
            f"{row.eval_gain_per_atom:.6f} | {row.missing_bits_per_record:.3f} | "
            f"{row.records_per_atom:.6f} | {row.avg_arity:.2f} | {row.avg_width:.2f} | "
            f"{row.payload_bits_per_record:.3f} | {row.shape_bits_per_record:.3f} | "
            f"{row.logz_bits_per_record:.3f} | {row.coverage:.3f} |"
        )

    lines.extend(["", "## Reading", ""])
    for atoms in sorted({row.atoms for row in all_rows}):
        rows_for_n = [row for row in all_rows if row.atoms == atoms]
        selected = max(rows_for_n, key=lambda row: row.train_gain_per_atom)
        best_eval = max(rows_for_n, key=lambda row: row.eval_gain_per_atom)
        lines.append(
            f"`N={atoms}` train-selected beta `{selected.beta:.3f}`, record bias "
            f"`{selected.record_bias:.3f}` has held-out "
            f"gain `{selected.eval_gain_per_atom:.6f}` bits/input atom."
        )
        lines.append(
            f"`N={atoms}` best held-out diagnostic beta `{best_eval.beta:.3f}`, "
            f"record bias `{best_eval.record_bias:.3f}` has "
            f"`{best_eval.eval_gain_per_atom:.6f}` bits/input atom."
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, nargs="+", default=[64])
    parser.add_argument("--train-trials", type=int, default=16)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--betas", type=float, nargs="+", default=[-0.5, 0.0, 0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--record-biases", type=float, nargs="+", default=[-8.0, -4.0, -2.0, 0.0])
    parser.add_argument("--seed", type=int, default=3217)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_rows: list[PartitionRow] = []
    for atoms in args.atoms:
        all_rows.extend(evaluate_atoms(args, atoms))
    print(render(all_rows, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
