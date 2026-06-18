#!/usr/bin/env python3
"""H98 - partial slack refresh kernel.

The user-proposed variant is not total-cover:

    allow +0/+1/+2 bit records,
    replace enough atoms to keep future targets fresh,
    do not require every atom to be rewritten.

That can create a real match-rate effect: an interval containing at least one
newly emitted record bit is a fresh target next pass, even if some neighbors
were carried. The trap is that carried bytes are not statelessly parseable
unless the stream also says which spans are current records and which spans are
old bytes.

This kernel keeps those two facts separate:

* ``unpaid carry``: optimistic lattice. Carried atoms cost raw bits and carry no
  parse marker. This measures the refresh effect only.
* ``H2 charged``: the same selected covers, but with a lower-bound binary
  ready/carry entropy charge H2(rewritten fraction). This is still generous:
  it does not charge full cover-shape/arity placement entropy.
* ``literal rewrite``: stateless lower-bound codec. Unmatched atoms are emitted
  as literal tokens with only a 3-bit marker, so every pass is parseable and
  every output atom is fresh. Real byte-aligned V1 literals are costlier.

No birth/open entropy is charged in the total-cover branch; this file is for
the partial-cover branch, where carries reintroduce the channel.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (
    LITERAL_MARKER_BITS,
    MAX_PAYLOAD_WIDTH_BITS,
    j3d1_cost_for_payload_width,
    record_cost_for_payload_width,
)
from total_cover_lotus_crossover import (
    fixed_arity_bits,
    lotus_payload_width_from_log_rank,
    sample_log2_first_rank,
)


@dataclass(frozen=True)
class Config:
    name: str
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class Edge:
    start: int
    arity: int
    cost: int
    payload_width: int


@dataclass(frozen=True)
class Choice:
    arity: int
    cost: int
    is_record: bool


@dataclass(frozen=True)
class PassMetrics:
    input_atoms: int
    input_bits: int
    unpaid_bits: int
    h2_paid_bits: float
    literal_bits: int
    rewritten_fraction: float
    h2_bits_per_atom: float
    fresh_fraction_unpaid: float
    fresh_fraction_paid: float
    fresh_fraction_literal: float
    records: int
    avg_arity: float
    avg_cost: float


@dataclass(frozen=True)
class Row:
    config: Config
    allowed_slack: int
    budget_bits_per_atom: float
    passes: int
    trials: int
    unpaid_mean_log2_rho: float
    h2_paid_mean_log2_rho: float
    literal_mean_log2_rho: float
    unpaid_total_ratio: float
    h2_paid_total_ratio: float
    literal_total_ratio: float
    rewritten_fraction: float
    hidden_h2_bits_per_atom: float
    final_fresh_unpaid: float
    final_fresh_paid: float
    final_fresh_literal: float
    records_per_atom: float
    avg_arity: float
    avg_record_cost: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def record_cost(block_bits: int, max_arity: int, arity: int, payload_width: int) -> int:
    if payload_width > MAX_PAYLOAD_WIDTH_BITS:
        raise ValueError("payload width exceeds J3D1 cap")
    if max_arity <= 5:
        return record_cost_for_payload_width(arity, payload_width)
    return fixed_arity_bits(max_arity, arity) + j3d1_cost_for_payload_width(payload_width)


def sample_edges(
    fresh: list[bool],
    config: Config,
    allowed_slack: int,
    rng: random.Random,
) -> list[list[Edge]]:
    edges_by_start: list[list[Edge]] = [[] for _ in fresh]
    n = len(fresh)
    for start in range(n):
        legal = min(config.max_arity, n - start)
        any_fresh = False
        for arity in range(1, legal + 1):
            any_fresh = any_fresh or fresh[start + arity - 1]
            if not any_fresh:
                continue
            target_bits = arity * config.block_bits
            log_rank = sample_log2_first_rank(target_bits, rng)
            payload_width = lotus_payload_width_from_log_rank(log_rank)
            if payload_width > min(config.frontier, MAX_PAYLOAD_WIDTH_BITS):
                continue
            cost = record_cost(config.block_bits, config.max_arity, arity, payload_width)
            if cost <= target_bits + allowed_slack:
                edges_by_start[start].append(Edge(start, arity, cost, payload_width))
    return edges_by_start


def select_max_refresh(
    fresh: list[bool],
    config: Config,
    allowed_slack: int,
    budget_bits_per_atom: float,
    rng: random.Random,
) -> tuple[list[Choice], list[bool], float]:
    """Maximize rewritten input atoms under a current-length budget.

    Fallback is an unpaid raw carry, so this is explicitly the optimistic
    lattice objective. H2/stateless charges are applied after selection.
    """

    n = len(fresh)
    budget = math.floor(n * (config.block_bits + budget_bits_per_atom))
    edges_by_start = sample_edges(fresh, config, allowed_slack, rng)
    # dp[pos][cost] = (rewritten atoms, record bits, choices)
    dp: list[dict[int, tuple[int, int, tuple[Choice, ...]]]] = [dict() for _ in range(n + 1)]
    dp[0][0] = (0, 0, ())
    for pos in range(n):
        for used, state in list(dp[pos].items()):
            rewritten, record_bits, choices = state
            carry_cost = config.block_bits
            carry_used = used + carry_cost
            if carry_used <= budget:
                candidate = (rewritten, record_bits, choices + (Choice(1, carry_cost, False),))
                old = dp[pos + 1].get(carry_used)
                if old is None or (candidate[0], candidate[1], -carry_used) > (old[0], old[1], -carry_used):
                    dp[pos + 1][carry_used] = candidate
            for edge in edges_by_start[pos]:
                record_used = used + edge.cost
                if record_used > budget:
                    continue
                candidate = (
                    rewritten + edge.arity,
                    record_bits + edge.cost,
                    choices + (Choice(edge.arity, edge.cost, True),),
                )
                old = dp[pos + edge.arity].get(record_used)
                if old is None or (candidate[0], candidate[1], -record_used) > (old[0], old[1], -record_used):
                    dp[pos + edge.arity][record_used] = candidate
    if not dp[n]:
        raise RuntimeError("raw carries should always make a cover possible")
    best_cost, best = max(
        dp[n].items(),
        key=lambda item: (item[1][0], item[1][1], -item[0]),
    )
    choices = list(best[2])
    rewritten_fraction = best[0] / n
    return choices, choices_to_fresh_atoms(choices, config.block_bits, literal=False), rewritten_fraction


def select_literal_rewrite(
    fresh: list[bool],
    config: Config,
    allowed_slack: int,
    rng: random.Random,
) -> tuple[list[Choice], list[bool]]:
    """Stateless lower-bound pass: unmatched atoms are literal tokens."""

    n = len(fresh)
    edges_by_start = sample_edges([True] * n, config, allowed_slack, rng)
    literal_cost = config.block_bits + LITERAL_MARKER_BITS
    dp = [float("inf")] * (n + 1)
    prev: list[tuple[int, Choice] | None] = [None] * (n + 1)
    dp[0] = 0.0
    for pos in range(n):
        if dp[pos] == float("inf"):
            continue
        carry = Choice(1, literal_cost, False)
        if dp[pos] + literal_cost < dp[pos + 1]:
            dp[pos + 1] = dp[pos] + literal_cost
            prev[pos + 1] = (pos, carry)
        for edge in edges_by_start[pos]:
            candidate = dp[pos] + edge.cost
            end = pos + edge.arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (pos, Choice(edge.arity, edge.cost, True))
    choices: list[Choice] = []
    cursor = n
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing literal predecessor")
        prior, choice = entry
        choices.append(choice)
        cursor = prior
    choices.reverse()
    return choices, choices_to_fresh_atoms(choices, config.block_bits, literal=True)


def choices_to_fresh_atoms(choices: list[Choice], block_bits: int, literal: bool) -> list[bool]:
    out: list[bool] = []
    for choice in choices:
        atoms = max(1, math.ceil(choice.cost / block_bits))
        if choice.is_record or literal:
            out.extend([True] * atoms)
        else:
            out.extend([False] * atoms)
    return out


def choice_bits(choices: list[Choice]) -> int:
    return sum(choice.cost for choice in choices)


def pass_metrics(
    config: Config,
    unpaid_choices: list[Choice],
    unpaid_fresh: list[bool],
    rewritten_fraction: float,
    literal_choices: list[Choice],
    literal_fresh: list[bool],
) -> PassMetrics:
    input_atoms = sum(choice.arity for choice in unpaid_choices)
    input_bits = input_atoms * config.block_bits
    unpaid_bits = choice_bits(unpaid_choices)
    h2_bits_per_atom = h2(rewritten_fraction)
    h2_paid_bits = unpaid_bits + h2_bits_per_atom * input_atoms
    h2_fresh_atoms = math.ceil((h2_bits_per_atom * input_atoms) / config.block_bits)
    paid_fresh = [True] * h2_fresh_atoms + unpaid_fresh
    literal_bits = choice_bits(literal_choices)
    records = [choice for choice in unpaid_choices if choice.is_record]
    return PassMetrics(
        input_atoms=input_atoms,
        input_bits=input_bits,
        unpaid_bits=unpaid_bits,
        h2_paid_bits=h2_paid_bits,
        literal_bits=literal_bits,
        rewritten_fraction=rewritten_fraction,
        h2_bits_per_atom=h2_bits_per_atom,
        fresh_fraction_unpaid=sum(unpaid_fresh) / len(unpaid_fresh) if unpaid_fresh else 0.0,
        fresh_fraction_paid=sum(paid_fresh) / len(paid_fresh) if paid_fresh else 0.0,
        fresh_fraction_literal=sum(literal_fresh) / len(literal_fresh) if literal_fresh else 0.0,
        records=len(records),
        avg_arity=mean(choice.arity for choice in records) if records else 0.0,
        avg_cost=mean(choice.cost for choice in records) if records else 0.0,
    )


def simulate_trial(
    config: Config,
    allowed_slack: int,
    budget_bits_per_atom: float,
    passes: int,
    seed: int,
) -> tuple[list[PassMetrics], float, float, float, float, float, float]:
    rng_unpaid = random.Random(seed)
    rng_literal = random.Random(seed + 9091)
    unpaid_fresh = [True] * config.atoms
    literal_fresh = [True] * config.atoms
    initial_bits = config.atoms * config.block_bits
    unpaid_bits = initial_bits
    h2_paid_bits = initial_bits
    literal_bits = initial_bits
    metrics: list[PassMetrics] = []
    unpaid_logs: list[float] = []
    paid_logs: list[float] = []
    literal_logs: list[float] = []
    for _pass_index in range(1, passes + 1):
        unpaid_choices, next_unpaid_fresh, rewritten_fraction = select_max_refresh(
            unpaid_fresh,
            config,
            allowed_slack,
            budget_bits_per_atom,
            rng_unpaid,
        )
        literal_choices, next_literal_fresh = select_literal_rewrite(
            literal_fresh,
            config,
            allowed_slack,
            rng_literal,
        )
        metric = pass_metrics(
            config,
            unpaid_choices,
            next_unpaid_fresh,
            rewritten_fraction,
            literal_choices,
            next_literal_fresh,
        )
        metrics.append(metric)
        padded_unpaid_input = len(unpaid_fresh) * config.block_bits
        padded_literal_input = len(literal_fresh) * config.block_bits
        unpaid_logs.append(math.log2(metric.unpaid_bits / padded_unpaid_input))
        paid_logs.append(math.log2(metric.h2_paid_bits / padded_unpaid_input))
        literal_logs.append(math.log2(metric.literal_bits / padded_literal_input))
        unpaid_bits = metric.unpaid_bits
        h2_paid_bits = metric.h2_paid_bits
        literal_bits = metric.literal_bits
        unpaid_fresh = next_unpaid_fresh
        # Paid H2 map bits are optimistic fresh header bits. They are not fed
        # back into the unpaid lattice; the paid ratio is reported separately.
        literal_fresh = next_literal_fresh
    return (
        metrics,
        mean(unpaid_logs),
        mean(paid_logs),
        mean(literal_logs),
        unpaid_bits / initial_bits,
        h2_paid_bits / initial_bits,
        literal_bits / initial_bits,
    )


def evaluate(
    config: Config,
    allowed_slack: int,
    budget_bits_per_atom: float,
    passes: int,
    trials: int,
    seed: int,
) -> Row:
    all_metrics: list[PassMetrics] = []
    unpaid_logs: list[float] = []
    paid_logs: list[float] = []
    literal_logs: list[float] = []
    unpaid_ratios: list[float] = []
    paid_ratios: list[float] = []
    literal_ratios: list[float] = []
    for trial in range(trials):
        metrics, ulog, plog, llog, ur, pr, lr = simulate_trial(
            config,
            allowed_slack,
            budget_bits_per_atom,
            passes,
            seed + trial * 1000003,
        )
        all_metrics.extend(metrics)
        unpaid_logs.append(ulog)
        paid_logs.append(plog)
        literal_logs.append(llog)
        unpaid_ratios.append(ur)
        paid_ratios.append(pr)
        literal_ratios.append(lr)
    finalish = all_metrics[-trials:] if len(all_metrics) >= trials else all_metrics
    return Row(
        config=config,
        allowed_slack=allowed_slack,
        budget_bits_per_atom=budget_bits_per_atom,
        passes=passes,
        trials=trials,
        unpaid_mean_log2_rho=mean(unpaid_logs),
        h2_paid_mean_log2_rho=mean(paid_logs),
        literal_mean_log2_rho=mean(literal_logs),
        unpaid_total_ratio=mean(unpaid_ratios),
        h2_paid_total_ratio=mean(paid_ratios),
        literal_total_ratio=mean(literal_ratios),
        rewritten_fraction=mean(m.rewritten_fraction for m in all_metrics),
        hidden_h2_bits_per_atom=mean(m.h2_bits_per_atom for m in all_metrics),
        final_fresh_unpaid=mean(m.fresh_fraction_unpaid for m in finalish),
        final_fresh_paid=mean(m.fresh_fraction_paid for m in finalish),
        final_fresh_literal=mean(m.fresh_fraction_literal for m in finalish),
        records_per_atom=mean(m.records / m.input_atoms for m in all_metrics),
        avg_arity=mean(m.avg_arity for m in all_metrics if m.records) if any(m.records for m in all_metrics) else 0.0,
        avg_record_cost=mean(m.avg_cost for m in all_metrics if m.records) if any(m.records for m in all_metrics) else 0.0,
    )


def default_configs() -> list[Config]:
    return [
        Config("v1_B8_K5", 8, 5, 40, 64),
        Config("xarity_B4_K16", 4, 16, 64, 80),
        Config("xarity_B4_K32", 4, 32, 128, 96),
    ]


def print_rows(rows: list[Row]) -> None:
    print("== partial slack refresh sweep ==")
    print("unpaid carry is a match-rate lower bound; H2 and literal columns price statelessness.")
    print(
        f"{'config':<14} {'s':>2} {'bud':>5} {'unpaid':>9} {'H2 paid':>9} "
        f"{'literal':>9} {'repl':>7} {'H2/atom':>8} {'freshU':>7} "
        f"{'freshLit':>8} {'rec/atom':>8} {'arity':>7} {'cost':>7}"
    )
    for row in rows:
        print(
            f"{row.config.name:<14} {row.allowed_slack:2d} {row.budget_bits_per_atom:5.2f} "
            f"{row.unpaid_mean_log2_rho:9.4f} {row.h2_paid_mean_log2_rho:9.4f} "
            f"{row.literal_mean_log2_rho:9.4f} {row.rewritten_fraction:7.3f} "
            f"{row.hidden_h2_bits_per_atom:8.3f} {row.final_fresh_unpaid:7.3f} "
            f"{row.final_fresh_literal:8.3f} {row.records_per_atom:8.4f} "
            f"{row.avg_arity:7.2f} {row.avg_record_cost:7.2f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    best_unpaid = min(rows, key=lambda row: row.unpaid_mean_log2_rho)
    best_paid = min(rows, key=lambda row: row.h2_paid_mean_log2_rho)
    best_literal = min(rows, key=lambda row: row.literal_mean_log2_rho)
    maintaining = [row for row in rows if row.final_fresh_unpaid >= 0.10]
    best_maintaining = min(maintaining, key=lambda row: row.unpaid_mean_log2_rho) if maintaining else None
    print("== reading ==")
    print(
        f"Best unpaid lattice row is {best_unpaid.config.name}, slack={best_unpaid.allowed_slack}, "
        f"budget={best_unpaid.budget_bits_per_atom:.2f}, mean log2 rho={best_unpaid.unpaid_mean_log2_rho:.6f}, "
        f"but final fresh fraction is {best_unpaid.final_fresh_unpaid:.6f}."
    )
    if best_maintaining is not None:
        print(
            f"Best unpaid row that keeps at least 10% fresh output is {best_maintaining.config.name}, "
            f"slack={best_maintaining.allowed_slack}, budget={best_maintaining.budget_bits_per_atom:.2f}, "
            f"mean log2 rho={best_maintaining.unpaid_mean_log2_rho:.6f}."
        )
    print(
        f"After only the binary H2 ready/carry lower bound, best row is {best_paid.config.name}, "
        f"slack={best_paid.allowed_slack}, budget={best_paid.budget_bits_per_atom:.2f}, "
        f"mean log2 rho={best_paid.h2_paid_mean_log2_rho:.6f}."
    )
    print(
        f"The stateless literal-rewrite lower bound's best row is {best_literal.config.name}, "
        f"slack={best_literal.allowed_slack}, mean log2 rho={best_literal.literal_mean_log2_rho:.6f}."
    )
    print(
        "A negative unpaid row with no final freshness is only a one-shot sparse compression result. "
        "A row that keeps fresh targets alive must also stay negative after H2/literal accounting; "
        "otherwise the claimed recursive gain was carried by an unpriced ready/carry channel."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=5)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--slacks", type=int, nargs="+", default=[0, 1, 2, 4])
    parser.add_argument("--budgets", type=float, nargs="+", default=[0.0, 0.05, 0.25])
    parser.add_argument("--seed", type=int, default=98098)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        evaluate(config, slack, budget, args.passes, args.trials, args.seed)
        for config in default_configs()
        for slack in args.slacks
        for budget in args.budgets
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
