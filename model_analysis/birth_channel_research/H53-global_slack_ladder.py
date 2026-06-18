#!/usr/bin/env python3
"""H53 - paid global slack ladder.

H52 found that strict fixed slack moves the repeated-pass frontier but still
misses. The next honest variant is a global ladder:

    choose one slack value from a small public set for the whole layer/pass
    charge a selector once for that layer
    decode all record widths with that public slack

This is stateless if the slack selector is in the layer header/stream. The
hidden-channel risk is pretending the selector is free.

H53 preserves correlation between ladder levels. For each interval it samples
one exponential first-hit variable E; slack `s` is available iff:

    E <= 2^(min(D, aB-s) - aB)

Thus a slack-2 hit is also a slack-1 and slack-0 hit. The ladder does not get
independent redraws for each slack.
"""

from __future__ import annotations

import argparse
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class ArityModel:
    counts: dict[int, Counter[int]]
    max_arity: int
    alpha: float


@dataclass(frozen=True)
class Record:
    arity: int
    width: int
    cost_bits: float


@dataclass(frozen=True)
class Cover:
    covered: bool
    charged_bits: float
    records: tuple[Record, ...]
    slack: int | None = None


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class Row:
    config: Config
    slacks: tuple[int, ...]
    selector_bits: float
    mode: str
    status: str
    coverage: float
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    avg_slack: float


def width_bits_for(block_bits: int, frontier: int, arity: int, slack: int) -> int | None:
    width = min(frontier, arity * block_bits - slack)
    if width < 1:
        return None
    return width


def hit_threshold(block_bits: int, frontier: int, arity: int, slack: int) -> float:
    width = width_bits_for(block_bits, frontier, arity, slack)
    if width is None:
        return 0.0
    exponent = width - arity * block_bits
    if exponent >= 0:
        return float(1 << exponent)
    if exponent < -60:
        return 0.0
    return 2.0**exponent


def arity_cost(model: ArityModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def sample_scores(
    max_arity: int,
    atoms: int,
    rng: random.Random,
) -> list[list[float]]:
    rows: list[list[float]] = []
    for index in range(atoms):
        legal = min(max_arity, atoms - index)
        rows.append([rng.expovariate(1.0) for _ in range(legal)])
    return rows


def cover_scores(
    scores: list[list[float]],
    block_bits: int,
    frontier: int,
    model: ArityModel,
    slack: int,
) -> Cover:
    atoms = len(scores)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, score in enumerate(scores[index], start=1):
            threshold = hit_threshold(block_bits, frontier, arity, slack)
            if score > threshold:
                continue
            width = width_bits_for(block_bits, frontier, arity, slack)
            if width is None:
                continue
            cost = width + arity_cost(model, remaining, arity)
            candidate = base + cost
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, width, cost)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), (), slack)

    records: list[Record] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, width, cost = entry
        records.append(Record(arity, width, cost))
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms], tuple(records), slack)


def fit_model(covers: list[Cover], max_arity: int, alpha: float) -> ArityModel:
    counts: dict[int, Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            counts.setdefault(remaining, Counter())[record.arity] += 1
            consumed += record.arity
    return ArityModel(counts, max_arity, alpha)


def train_model(
    block_bits: int,
    max_arity: int,
    frontier: int,
    atoms: int,
    slack: int,
    train_trials: int,
    iterations: int,
    alpha: float,
    seed: int,
) -> ArityModel:
    rng = random.Random(seed)
    samples = [sample_scores(max_arity, atoms, rng) for _ in range(train_trials)]
    model = ArityModel({}, max_arity, alpha)
    for _ in range(iterations):
        covers = [cover_scores(sample, block_bits, frontier, model, slack) for sample in samples]
        model = fit_model(covers, max_arity, alpha)
    return model


def choose_cover(
    scores: list[list[float]],
    block_bits: int,
    frontier: int,
    models: dict[int, ArityModel],
    slacks: tuple[int, ...],
    selector_bits: float,
    mode: str,
) -> Cover:
    covers = [cover_scores(scores, block_bits, frontier, models[slack], slack) for slack in slacks]
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return Cover(False, float("inf"), (), None)
    if mode == "paid_best":
        best = min(covered, key=lambda cover: cover.charged_bits)
    elif mode == "paid_first_full":
        # Slacks are interpreted in the provided order. This still needs the
        # selector for stateless decoding; the rule is tested as a diagnostic.
        best = covered[0]
    elif mode == "oracle_unpaid_best":
        best = min(covered, key=lambda cover: cover.charged_bits)
        return best
    else:
        raise ValueError(mode)
    return Cover(best.covered, best.charged_bits + selector_bits, best.records, best.slack)


def simulate_config(args: argparse.Namespace, config: Config, mode: str) -> Row:
    slacks = tuple(args.slacks)
    selector_bits = 0.0 if mode == "oracle_unpaid_best" else math.log2(len(slacks))
    current_bits = [float(config.atoms * config.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    log_rhos: list[float] = []
    all_covers: list[Cover] = []
    covered_count = 0
    total_attempts = 0

    for pass_index in range(1, args.passes + 1):
        input_atoms = [max(1, math.ceil(bits / config.block_bits)) for bits in current_bits]
        padded_bits = [atoms * config.block_bits for atoms in input_atoms]
        covers_by_trial: list[Cover | None] = [None] * args.trials
        groups: dict[int, list[int]] = defaultdict(list)
        for trial_index, atoms in enumerate(input_atoms):
            groups[atoms].append(trial_index)

        for atoms, trial_indices in groups.items():
            seed_base = (
                args.seed
                + config.block_bits * 1000003
                + config.max_arity * 10007
                + config.frontier * 101
                + pass_index * 104729
                + atoms * 17
            )
            models = {
                slack: train_model(
                    config.block_bits,
                    config.max_arity,
                    config.frontier,
                    atoms,
                    slack,
                    args.train_trials,
                    args.iterations,
                    args.alpha,
                    seed_base + slack * 7919,
                )
                for slack in slacks
            }
            rng = random.Random(seed_base + 424242)
            for trial_index in trial_indices:
                scores = sample_scores(config.max_arity, atoms, rng)
                covers_by_trial[trial_index] = choose_cover(
                    scores,
                    config.block_bits,
                    config.frontier,
                    models,
                    slacks,
                    selector_bits,
                    mode,
                )

        ordered = [cover for cover in covers_by_trial if cover is not None]
        total_attempts += len(ordered)
        covered_count += sum(1 for cover in ordered if cover.covered)
        if not all(cover.covered for cover in ordered):
            all_covers.extend(ordered)
            return summarize_row(config, slacks, selector_bits, mode, "failed", log_rhos, current_bits, initial_bits, all_covers, covered_count, total_attempts)

        outputs = [cover.charged_bits for cover in ordered]
        log_rhos.extend(math.log2(out / inp) for out, inp in zip(outputs, padded_bits))
        current_bits = outputs
        all_covers.extend(ordered)

    return summarize_row(
        config,
        slacks,
        selector_bits,
        mode,
        "compressive" if mean(log_rhos) < 0.0 else "expanding",
        log_rhos,
        current_bits,
        initial_bits,
        all_covers,
        covered_count,
        total_attempts,
    )


def summarize_row(
    config: Config,
    slacks: tuple[int, ...],
    selector_bits: float,
    mode: str,
    status: str,
    log_rhos: list[float],
    current_bits: list[float],
    initial_bits: list[float],
    covers: list[Cover],
    covered_count: int,
    attempts: int,
) -> Row:
    covered = [cover for cover in covers if cover.covered]
    records = [record for cover in covered for record in cover.records]
    mean_log = mean(log_rhos) if log_rhos else float("nan")
    chosen_slacks = [cover.slack for cover in covered if cover.slack is not None]
    return Row(
        config=config,
        slacks=slacks,
        selector_bits=selector_bits,
        mode=mode,
        status=status,
        coverage=(covered_count / attempts) if attempts else 0.0,
        mean_log2_rho=mean_log,
        geometric_rho=(2.0**mean_log) if not math.isnan(mean_log) else float("nan"),
        final_bits_avg=mean(current_bits) if current_bits else float("nan"),
        total_ratio_avg=mean(final / start for final, start in zip(current_bits, initial_bits)) if current_bits else float("nan"),
        records_per_atom=(len(records) / sum(sum(record.arity for record in cover.records) for cover in covered)) if records else 0.0,
        avg_arity=mean(record.arity for record in records) if records else 0.0,
        avg_width=mean(record.width for record in records) if records else 0.0,
        avg_slack=mean(chosen_slacks) if chosen_slacks else 0.0,
    )


def parse_config(text: str) -> Config:
    parts = [int(part) for part in text.split(",")]
    if len(parts) not in {3, 4}:
        raise argparse.ArgumentTypeError("config must be B,K,D or B,K,D,atoms")
    block_bits, max_arity, frontier = parts[:3]
    atoms = parts[3] if len(parts) == 4 else max(96, max_arity)
    return Config(block_bits, max_arity, frontier, atoms)


def default_configs() -> list[Config]:
    return [
        Config(4, 192, 768, 192),
    ]


def fmt(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.6f}"


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# Paid Global Slack Ladder",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`, "
        f"`train_trials={args.train_trials}`, `iterations={args.iterations}`, "
        f"`slacks={args.slacks}`.",
        "",
        "One slack is chosen per layer/pass from the public set. Paid modes charge",
        "`log2(|S|)` selector bits for the layer. `oracle_unpaid_best` is a",
        "labeled lower bound.",
        "",
        "| B | K | D | atoms | mode | selector bits | status | coverage | mean log2 rho | geom rho | final bits avg | total ratio avg | rec/atom | avg arity | avg width | avg slack |",
        "| ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        c = row.config
        lines.append(
            f"| {c.block_bits} | {c.max_arity} | {c.frontier} | {c.atoms} | "
            f"{row.mode} | {row.selector_bits:.3f} | {row.status} | "
            f"{row.coverage:.3f} | {fmt(row.mean_log2_rho)} | "
            f"{fmt(row.geometric_rho)} | {fmt(row.final_bits_avg)} | "
            f"{fmt(row.total_ratio_avg)} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | {row.avg_slack:.2f} |"
        )

    paid = [row for row in rows if row.mode != "oracle_unpaid_best" and row.status != "failed"]
    oracle = [row for row in rows if row.mode == "oracle_unpaid_best" and row.status != "failed"]
    lines.extend(["", "## Reading", ""])
    if paid:
        best_paid = min(paid, key=lambda row: row.mean_log2_rho)
        lines.append(
            "Best paid row: "
            f"`B={best_paid.config.block_bits},K={best_paid.config.max_arity},"
            f"D={best_paid.config.frontier},{best_paid.mode}` with "
            f"`mean log2 rho={best_paid.mean_log2_rho:.6f}`."
        )
    if oracle:
        best_oracle = min(oracle, key=lambda row: row.mean_log2_rho)
        lines.append(
            "Best unpaid lower bound: "
            f"`B={best_oracle.config.block_bits},K={best_oracle.config.max_arity},"
            f"D={best_oracle.config.frontier}` with "
            f"`mean log2 rho={best_oracle.mean_log2_rho:.6f}`."
        )
    lines.append(
        "If the unpaid ladder helps but the paid ladder does not, the global "
        "slack choice is itself the missing channel."
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", action="append", type=parse_config, dest="configs")
    parser.add_argument("--slacks", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--modes", nargs="+", default=["paid_best", "oracle_unpaid_best"])
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=10103)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs if args.configs else default_configs()
    rows = [simulate_config(args, config, mode) for config in configs for mode in args.modes]
    print(render(rows, args))


if __name__ == "__main__":
    main()
