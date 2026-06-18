#!/usr/bin/env python3
"""Trained public CRF cover-shape code for Total-Cover.

H13 tested a raw/tilted semi-Markov partition code over whole cover shapes.
H14 adds a small public feature model:

    q(shape) = product psi(edge) / Z(N)
    log2 psi(edge) = raw_width_law + beta * delta + record_bias
                     + sum feature_weights[f]

The feature weights are trained only from independent uniform-law samples by a
fixed algorithm. They are public profile constants, not per-file metadata. The
selected target file still pays:

    sum(width_j) + log2 Z(N) - sum(log2 psi_j)

for the shape plus exact seed residuals.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402


H13_PATH = Path(__file__).with_name("H13-joint_selected_cover_partition.py")


def load_h13() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h13_joint_selected_cover_partition", H13_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H13 kernel from {H13_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H13 = load_h13()


@dataclass(frozen=True)
class CrfCover:
    covered: bool
    charged_bits: float
    records: tuple[SelectedRecord, ...]
    shape_bits: float
    payload_bits: float
    logz_bits: float


@dataclass(frozen=True)
class CrfRow:
    atoms: int
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    payload_bits_per_record: float
    shape_bits_per_record: float
    logz_bits_per_record: float
    feature_bits_per_record: float
    coverage: float
    weight_count: int
    weight_l1: float


def bucket_power(value: int) -> str:
    if value <= 1:
        return "1"
    if value <= 3:
        return "2_3"
    if value <= 7:
        return "4_7"
    if value <= 15:
        return "8_15"
    if value <= 31:
        return "16_31"
    if value <= 63:
        return "32_63"
    if value <= 127:
        return "64_127"
    return "128_plus"


def bucket_remaining(remaining: int) -> str:
    if remaining <= 16:
        return "le16"
    if remaining <= 32:
        return "17_32"
    if remaining <= 64:
        return "33_64"
    if remaining <= 128:
        return "65_128"
    return "gt128"


def bucket_delta(delta: int) -> str:
    if delta <= -16:
        return "le_neg16"
    if delta <= -8:
        return "neg15_neg8"
    if delta <= -4:
        return "neg7_neg4"
    if delta <= -1:
        return "neg3_neg1"
    if delta == 0:
        return "zero"
    if delta == 1:
        return "one"
    if delta == 2:
        return "two"
    if delta <= 4:
        return "three_four"
    if delta <= 8:
        return "five_eight"
    return "ge9"


def features(remaining: int, arity: int, target_bits: int, width: int) -> tuple[str, ...]:
    arity_bucket = bucket_power(arity)
    delta_bucket = bucket_delta(target_bits - width)
    remaining_bucket = bucket_remaining(remaining)
    return (
        f"a:{arity_bucket}",
        f"d:{delta_bucket}",
        f"r:{remaining_bucket}",
        f"ad:{arity_bucket}|{delta_bucket}",
    )


def feature_sum(weights: dict[str, float], remaining: int, arity: int, target_bits: int, width: int) -> float:
    return sum(weights.get(feature, 0.0) for feature in features(remaining, arity, target_bits, width))


def log2_psi(
    weights: dict[str, float],
    remaining: int,
    arity: int,
    target_bits: int,
    width: int,
    frontier: int,
    beta: float,
    record_bias: float,
) -> float:
    return (
        H13.raw_width_logprob_nats(target_bits, width, frontier) / H13.LN2
        + beta * (target_bits - width)
        + record_bias
        + feature_sum(weights, remaining, arity, target_bits, width)
    )


def logsumexp2_pair(a: float, b: float) -> float:
    if a == float("-inf"):
        return b
    if b == float("-inf"):
        return a
    if b > a:
        a, b = b, a
    return a + math.log2(1.0 + 2.0 ** (b - a))


def logz_bits(
    atoms: int,
    block_bits: int,
    max_arity: int,
    frontier: int,
    beta: float,
    record_bias: float,
    weights: dict[str, float],
) -> float:
    dp = [float("-inf")] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("-inf"):
            continue
        remaining = atoms - index
        for arity in range(1, min(max_arity, remaining) + 1):
            target_bits = arity * block_bits
            edge_sum = float("-inf")
            for width in range(1, frontier + 1):
                edge_sum = logsumexp2_pair(
                    edge_sum,
                    log2_psi(weights, remaining, arity, target_bits, width, frontier, beta, record_bias),
                )
            dp[index + arity] = logsumexp2_pair(dp[index + arity], base + edge_sum)
    return dp[atoms]


def expected_feature_counts(
    atoms: int,
    block_bits: int,
    max_arity: int,
    frontier: int,
    beta: float,
    record_bias: float,
    weights: dict[str, float],
) -> Counter[str]:
    forward = [float("-inf")] * (atoms + 1)
    backward = [float("-inf")] * (atoms + 1)
    forward[0] = 0.0
    backward[atoms] = 0.0

    for index in range(atoms):
        base = forward[index]
        if base == float("-inf"):
            continue
        remaining = atoms - index
        for arity in range(1, min(max_arity, remaining) + 1):
            target_bits = arity * block_bits
            for width in range(1, frontier + 1):
                edge = log2_psi(weights, remaining, arity, target_bits, width, frontier, beta, record_bias)
                forward[index + arity] = logsumexp2_pair(forward[index + arity], base + edge)

    for index in range(atoms - 1, -1, -1):
        remaining = atoms - index
        total = float("-inf")
        for arity in range(1, min(max_arity, remaining) + 1):
            target_bits = arity * block_bits
            suffix = backward[index + arity]
            if suffix == float("-inf"):
                continue
            for width in range(1, frontier + 1):
                edge = log2_psi(weights, remaining, arity, target_bits, width, frontier, beta, record_bias)
                total = logsumexp2_pair(total, edge + suffix)
        backward[index] = total

    z = forward[atoms]
    counts: Counter[str] = Counter()
    if z == float("-inf"):
        return counts
    for index in range(atoms):
        remaining = atoms - index
        prefix = forward[index]
        if prefix == float("-inf"):
            continue
        for arity in range(1, min(max_arity, remaining) + 1):
            target_bits = arity * block_bits
            suffix = backward[index + arity]
            if suffix == float("-inf"):
                continue
            for width in range(1, frontier + 1):
                edge = log2_psi(weights, remaining, arity, target_bits, width, frontier, beta, record_bias)
                probability = 2.0 ** (prefix + edge + suffix - z)
                if probability == 0.0:
                    continue
                for feature in features(remaining, arity, target_bits, width):
                    counts[feature] += probability
    return counts


def cover_with_crf(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    beta: float,
    record_bias: float,
    weights: dict[str, float],
) -> CrfCover:
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
            psi = log2_psi(
                weights,
                remaining,
                arity,
                edge.target_bits,
                edge.lotus_payload_width,
                frontier,
                beta,
                record_bias,
            )
            local = edge.lotus_payload_width - psi
            candidate = base + local
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, psi)
    if dp[atoms] == float("inf"):
        return CrfCover(False, float("inf"), (), float("inf"), float("inf"), float("inf"))

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
    logz = logz_bits(atoms, block_bits, max_arity, frontier, beta, record_bias, weights)
    shape_bits = logz - psi_sum
    return CrfCover(True, payload_bits + shape_bits, tuple(records), shape_bits, payload_bits, logz)


def cover_feature_counts(cover: CrfCover, atoms: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    consumed = 0
    for record in cover.records:
        remaining = atoms - consumed
        for feature in features(remaining, record.arity, record.target_bits, record.lotus_payload_width):
            counts[feature] += 1.0
        consumed += record.arity
    return counts


def train_weights(
    train_samples: list[list[list[EdgeSample]]],
    atoms: int,
    block_bits: int,
    max_arity: int,
    frontier: int,
    beta: float,
    record_bias: float,
    iterations: int,
    learning_rate: float,
    l2: float,
    clip: float,
) -> tuple[dict[str, float], list[CrfCover]]:
    weights: dict[str, float] = {}
    covers: list[CrfCover] = []
    for _ in range(iterations):
        covers = [
            cover_with_crf(trial, block_bits, max_arity, frontier, beta, record_bias, weights)
            for trial in train_samples
        ]
        empirical: Counter[str] = Counter()
        covered = [cover for cover in covers if cover.covered]
        if not covered:
            break
        for cover in covered:
            empirical.update(cover_feature_counts(cover, atoms))
        for key in list(empirical):
            empirical[key] /= len(covered)
        expected = expected_feature_counts(atoms, block_bits, max_arity, frontier, beta, record_bias, weights)
        keys = set(empirical) | set(expected) | set(weights)
        updated: dict[str, float] = {}
        for key in keys:
            gradient = empirical.get(key, 0.0) - expected.get(key, 0.0) - l2 * weights.get(key, 0.0)
            value = weights.get(key, 0.0) + learning_rate * gradient
            if value > clip:
                value = clip
            elif value < -clip:
                value = -clip
            if abs(value) > 1e-9:
                updated[key] = value
        weights = updated
    covers = [
        cover_with_crf(trial, block_bits, max_arity, frontier, beta, record_bias, weights)
        for trial in train_samples
    ]
    return weights, covers


def gain(covers: list[CrfCover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    atoms: int,
    train_covers: list[CrfCover],
    eval_covers: list[CrfCover],
    block_bits: int,
    weights: dict[str, float],
) -> CrfRow:
    covered = [cover for cover in eval_covers if cover.covered]
    coverage = len(covered) / len(eval_covers) if eval_covers else 0.0
    if not covered:
        return CrfRow(atoms, float("-inf"), float("-inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, coverage, len(weights), sum(abs(value) for value in weights.values()))
    records = [record for cover in covered for record in cover.records]
    record_count = len(records)
    eval_gain = gain(covered, block_bits, atoms)
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    feature_bits = []
    for cover in covered:
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            feature_bits.append(feature_sum(weights, remaining, record.arity, record.target_bits, record.lotus_payload_width))
            consumed += record.arity
    return CrfRow(
        atoms=atoms,
        train_gain_per_atom=gain(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in records),
        avg_width=mean(record.lotus_payload_width for record in records),
        payload_bits_per_record=sum(cover.payload_bits for cover in covered) / record_count,
        shape_bits_per_record=sum(cover.shape_bits for cover in covered) / record_count,
        logz_bits_per_record=sum(cover.logz_bits for cover in covered) / record_count,
        feature_bits_per_record=mean(feature_bits) if feature_bits else 0.0,
        coverage=coverage,
        weight_count=len(weights),
        weight_l1=sum(abs(value) for value in weights.values()),
    )


def evaluate(args: argparse.Namespace, atoms: int) -> CrfRow:
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
    weights, train_covers = train_weights(
        train_samples,
        atoms,
        args.block_bits,
        args.max_arity,
        args.frontier,
        args.beta,
        args.record_bias,
        args.iterations,
        args.learning_rate,
        args.l2,
        args.clip,
    )
    eval_covers = [
        cover_with_crf(trial, args.block_bits, args.max_arity, args.frontier, args.beta, args.record_bias, weights)
        for trial in eval_samples
    ]
    return summarize(atoms, train_covers, eval_covers, args.block_bits, weights)


def render(rows: list[CrfRow], args: argparse.Namespace) -> str:
    lines = [
        "# Public CRF Cover-Partition Kernel",
        "",
        f"`B={args.block_bits}`, `K={args.max_arity}`, `D={args.frontier}`, "
        f"`beta={args.beta}`, `record_bias={args.record_bias}`.",
        "",
        "Feature weights are trained only on independent uniform-law samples by",
        "a fixed public algorithm. Exact seed residuals are still paid as",
        "`width` bits per record.",
        "",
        "| N | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | payload bits/rec | shape bits/rec | feature bits/rec | logZ bits/rec | weights | L1 | cover |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.atoms} | {row.train_gain_per_atom:.6f} | {row.eval_gain_per_atom:.6f} | "
            f"{row.missing_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | {row.payload_bits_per_record:.3f} | "
            f"{row.shape_bits_per_record:.3f} | {row.feature_bits_per_record:.3f} | "
            f"{row.logz_bits_per_record:.3f} | {row.weight_count} | {row.weight_l1:.3f} | "
            f"{row.coverage:.3f} |"
        )
    best = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Best held-out row in this fixed public-profile run: `N={best.atoms}` "
            f"with `{best.eval_gain_per_atom:.6f}` bits/input atom.",
            "A positive row would be a candidate public CRF witness mode. A",
            "negative row means the learned public feature weights still do not",
            "buy the missing witness bits.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, nargs="+", default=[128])
    parser.add_argument("--train-trials", type=int, default=16)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--beta", type=float, default=0.5)
    parser.add_argument("--record-bias", type=float, default=-10.0)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=0.02)
    parser.add_argument("--clip", type=float, default=4.0)
    parser.add_argument("--seed", type=int, default=4219)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [evaluate(args, atoms) for atoms in args.atoms]
    print(render(rows, args))


if __name__ == "__main__":
    main()
