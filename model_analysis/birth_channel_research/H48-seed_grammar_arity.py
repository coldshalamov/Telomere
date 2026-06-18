#!/usr/bin/env python3
"""H48 - seed-grammar arity embedding.

Question: can the decoder derive arity from the seed witness itself, removing
the explicit arity stream?

Mechanism under test:

    seed universe = disjoint public arity classes
    arity(seed) = class(seed)
    record = [seed witness]

If arity ``a`` receives fraction ``q_a`` of the seed universe, then searching
that arity is thinned by ``q_a``. Under the uniform hash law the first-hit rank
shifts by ``-log2(q_a)``. This is the hidden bill that an arity-in-seed grammar
must beat.

The kernel reports three modes:

* ``arity_seed_fixed_lower``: optimistic lower bound. It charges the thinned
  fixed-width global seed rank and assumes the decoder somehow knows the exact
  witness width. This is not parseable by itself.
* ``arity_seed_j3d1``: parseable seed-only record. It charges the thinned
  global rank as a self-delimiting J3D1 seed field and removes explicit arity.
* ``arity_width_grammar``: seed class derives both arity and width. This is
  equivalent to paying a public ``(arity,width)`` symbol distribution through
  seed-space thinning plus local payload bits.

Total-Cover semantics are unchanged: every record opens; no birth/open/carry
channel, no sparse hit map, and no final-position note.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import MAX_PAYLOAD_WIDTH_BITS, j3d1_cost_for_payload_width  # noqa: E402
from total_cover_lotus_crossover import (  # noqa: E402
    EdgeSample,
    SelectedRecord,
    generate_samples,
    local_payload_bits_from_log_rank,
    lotus_payload_width_from_log_rank,
)
from total_cover_public_model_kernel import Cover  # noqa: E402


Context = tuple[int, ...]


@dataclass(frozen=True)
class GrammarModel:
    mode: str
    context_scheme: str
    arity_counts: dict[Context, Counter[int]]
    symbol_counts: dict[Context, Counter[tuple[int, int]]]
    max_arity: int
    frontier: int
    alpha: float


@dataclass(frozen=True)
class GrammarRow:
    mode: str
    context_scheme: str
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    coverage: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    avg_seed_penalty: float
    avg_cost_per_record: float
    parseable: bool


def remaining_bucket(remaining: int, max_arity: int) -> int:
    if remaining <= max_arity:
        return remaining
    ratio = (remaining + max_arity - 1) // max_arity
    return max_arity + min(16, int(math.log2(ratio)) + 1)


def context_for(scheme: str, remaining: int, max_arity: int) -> Context:
    if scheme == "global":
        return ()
    if scheme == "remaining":
        return (remaining_bucket(remaining, max_arity),)
    raise ValueError(scheme)


def arity_probability(model: GrammarModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return 0.0
    context = context_for(model.context_scheme, remaining, model.max_arity)
    counts = model.arity_counts.get(context, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return (counts.get(arity, 0) + model.alpha) / denom


def symbol_probability(model: GrammarModel, remaining: int, arity: int, width: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max or not 1 <= width <= model.frontier:
        return 0.0
    context = context_for(model.context_scheme, remaining, model.max_arity)
    counts = model.symbol_counts.get(context, Counter())
    legal_symbols = legal_max * model.frontier
    denom = sum(counts.values()) + model.alpha * legal_symbols
    return (counts.get((arity, width), 0) + model.alpha) / denom


def thinned_log2_rank(edge: EdgeSample, q: float) -> float:
    if q <= 0.0:
        return float("inf")
    return edge.log2_rank - math.log2(q)


def edge_cost(edge: EdgeSample, arity: int, remaining: int, model: GrammarModel) -> tuple[float, float]:
    """Return (cost_bits, seed_space_penalty_bits)."""

    if model.mode in {"arity_seed_fixed_lower", "arity_seed_j3d1"}:
        q = arity_probability(model, remaining, arity)
        penalty = -math.log2(q) if q > 0.0 else float("inf")
        log_rank = thinned_log2_rank(edge, q)
        if model.mode == "arity_seed_fixed_lower":
            return float(local_payload_bits_from_log_rank(log_rank)), penalty
        width = lotus_payload_width_from_log_rank(log_rank)
        if width > model.frontier or width > MAX_PAYLOAD_WIDTH_BITS:
            return float("inf"), penalty
        return float(j3d1_cost_for_payload_width(width)), penalty

    if model.mode == "arity_width_grammar":
        q = symbol_probability(model, remaining, arity, edge.lotus_payload_width)
        penalty = -math.log2(q) if q > 0.0 else float("inf")
        return float(edge.lotus_payload_width) + penalty, penalty

    raise ValueError(model.mode)


def cover_with_model(
    trial: list[list[EdgeSample]],
    model: GrammarModel,
    flush_bits: float,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, float, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, edge in enumerate(trial[index], start=1):
            if arity > model.max_arity or edge.lotus_payload_width > model.frontier:
                continue
            cost, penalty = edge_cost(edge, arity, remaining, model)
            if cost == float("inf"):
                continue
            candidate = base + cost
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, cost, penalty)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())

    records: list[SelectedRecord] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, cost, penalty = entry
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
    mode: str,
    context_scheme: str,
    covers: list[Cover],
    max_arity: int,
    frontier: int,
    alpha: float,
) -> GrammarModel:
    arity_counts: dict[Context, Counter[int]] = {}
    symbol_counts: dict[Context, Counter[tuple[int, int]]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            context = context_for(context_scheme, remaining, max_arity)
            arity_counts.setdefault(context, Counter())[record.arity] += 1
            symbol_counts.setdefault(context, Counter())[
                (record.arity, record.lotus_payload_width)
            ] += 1
            consumed += record.arity
    return GrammarModel(mode, context_scheme, arity_counts, symbol_counts, max_arity, frontier, alpha)


def train_model(
    mode: str,
    context_scheme: str,
    samples: list[list[list[EdgeSample]]],
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
) -> tuple[GrammarModel, list[Cover]]:
    model = GrammarModel(mode, context_scheme, {}, {}, max_arity, frontier, alpha)
    covers: list[Cover] = []
    for _ in range(iterations):
        covers = [cover_with_model(trial, model, flush_bits) for trial in samples]
        model = fit_model(mode, context_scheme, covers, max_arity, frontier, alpha)
    return model, covers


def gain(covers: list[Cover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    model: GrammarModel,
    train_covers: list[Cover],
    eval_covers: list[Cover],
    block_bits: int,
    atoms: int,
) -> GrammarRow:
    covered = [cover for cover in eval_covers if cover.covered]
    coverage = len(covered) / len(eval_covers) if eval_covers else 0.0
    if not covered:
        return GrammarRow(
            model.mode,
            model.context_scheme,
            gain(train_covers, block_bits, atoms),
            float("-inf"),
            float("inf"),
            coverage,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            model.mode != "arity_seed_fixed_lower",
        )

    eval_gain = gain(covered, block_bits, atoms)
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    all_records = [record for cover in covered for record in cover.records]

    penalties: list[float] = []
    costs: list[float] = []
    for cover in covered:
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            # Recompute on the chosen record to split the thinning penalty.
            edge = EdgeSample(
                rank=record.rank,
                log2_rank=math.log2(record.rank) if record.rank > 0 else 0.0,
                lotus_payload_width=record.lotus_payload_width,
                local_payload_bits=record.local_payload_bits,
                target_bits=record.target_bits,
            )
            cost, penalty = edge_cost(edge, record.arity, remaining, model)
            costs.append(cost)
            penalties.append(penalty)
            consumed += record.arity

    return GrammarRow(
        mode=model.mode,
        context_scheme=model.context_scheme,
        train_gain_per_atom=gain(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        coverage=coverage,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in all_records),
        avg_width=mean(record.lotus_payload_width for record in all_records),
        avg_seed_penalty=mean(penalties),
        avg_cost_per_record=mean(costs),
        parseable=model.mode != "arity_seed_fixed_lower",
    )


def render(rows: list[GrammarRow], block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Seed-Grammar Arity Embedding Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Arity is derived from a public seed-space partition. The arity class",
        "fraction appears as lost match supply: `penalty = -log2(q_class)`.",
        "",
        "| mode | context | parseable | cover | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | seed penalty/rec | cost/rec |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.context_scheme} | {str(row.parseable).lower()} | "
            f"{row.coverage:.3f} | {row.train_gain_per_atom:.6f} | "
            f"{row.eval_gain_per_atom:.6f} | {row.missing_bits_per_record:.3f} | "
            f"{row.records_per_atom:.6f} | {row.avg_arity:.2f} | "
            f"{row.avg_width:.2f} | {row.avg_seed_penalty:.3f} | "
            f"{row.avg_cost_per_record:.3f} |"
        )

    best_parseable = max(
        (row for row in rows if row.parseable),
        key=lambda row: row.eval_gain_per_atom,
    )
    best_any = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Best row including non-parseable lower bounds: `{best_any.mode}` / "
            f"`{best_any.context_scheme}` at `{best_any.eval_gain_per_atom:.6f}` "
            "bits/input atom.",
            f"Best parseable row: `{best_parseable.mode}` / "
            f"`{best_parseable.context_scheme}` at "
            f"`{best_parseable.eval_gain_per_atom:.6f}` bits/input atom.",
            "If only the lower bound crosses, the missing channel is witness",
            "length/boundary. If parseable rows miss, arity-in-seed is just a",
            "different way to pay the selector through seed-space thinning.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--train-trials", type=int, default=16)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["arity_seed_fixed_lower", "arity_seed_j3d1", "arity_width_grammar"],
        default=["arity_seed_fixed_lower", "arity_seed_j3d1", "arity_width_grammar"],
    )
    parser.add_argument("--contexts", nargs="+", choices=["global", "remaining"], default=["global", "remaining"])
    parser.add_argument("--seed", type=int, default=5209)
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
    rows: list[GrammarRow] = []
    for mode in args.modes:
        for context in args.contexts:
            model, train_covers = train_model(
                mode,
                context,
                train_samples,
                args.max_arity,
                args.frontier,
                args.iterations,
                args.alpha,
                args.flush_bits,
            )
            eval_covers = [cover_with_model(trial, model, args.flush_bits) for trial in eval_samples]
            rows.append(summarize(model, train_covers, eval_covers, args.block_bits, args.atoms))
    print(render(rows, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
