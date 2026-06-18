#!/usr/bin/env python3
"""H52 - fixed-slack percolation reproduction sweep.

H9/H50 showed that fixed-width witnesses are the cleanest stateless way to
remove the width/delta channel:

    width(a) = min(D, a*B - slack)

The decoder knows `B`, `D`, `a`, and `slack`, so the witness boundary is public.
The price is lost match supply. Under the uniform hash law, an interval of
`a*B` bits has a fixed-width witness iff at least one of the first `2^width`
seeds matches:

    p_hit = 1 - exp(-2^(width - a*B))

H52 samples that Bernoulli edge event directly. This is the same fixed-width
law H9 tests via sampled ranks, but much faster for high K because no large
rank objects or Lotus widths are needed. It lets us ask whether more slack and
larger K can make the repeated-pass reproduction number cross:

    need held-out E[log rho] < 0
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


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class Row:
    config: Config
    slack: int
    status: str
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    coverage: float


def width_bits_for(block_bits: int, frontier: int, arity: int, slack: int) -> int | None:
    width = min(frontier, arity * block_bits - slack)
    if width < 1:
        return None
    return width


def hit_probability(block_bits: int, frontier: int, arity: int, slack: int) -> float:
    width = width_bits_for(block_bits, frontier, arity, slack)
    if width is None:
        return 0.0
    exponent = width - arity * block_bits
    if exponent >= 0:
        return -math.expm1(-float(1 << exponent))
    if exponent < -60:
        return 2.0**exponent
    return -math.expm1(-(2.0**exponent))


def arity_cost(model: ArityModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def sample_availability(
    block_bits: int,
    max_arity: int,
    frontier: int,
    atoms: int,
    slack: int,
    rng: random.Random,
) -> list[list[bool]]:
    rows: list[list[bool]] = []
    probs = [
        hit_probability(block_bits, frontier, arity, slack)
        for arity in range(1, max_arity + 1)
    ]
    for index in range(atoms):
        legal = min(max_arity, atoms - index)
        rows.append([rng.random() < probs[arity - 1] for arity in range(1, legal + 1)])
    return rows


def cover_sample(
    available: list[list[bool]],
    block_bits: int,
    frontier: int,
    model: ArityModel,
    slack: int,
) -> Cover:
    atoms = len(available)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, ok in enumerate(available[index], start=1):
            if not ok:
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
        return Cover(False, float("inf"), ())

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
    return Cover(True, dp[atoms], tuple(records))


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
    samples = [
        sample_availability(block_bits, max_arity, frontier, atoms, slack, rng)
        for _ in range(train_trials)
    ]
    model = ArityModel({}, max_arity, alpha)
    for _ in range(iterations):
        covers = [
            cover_sample(sample, block_bits, frontier, model, slack)
            for sample in samples
        ]
        model = fit_model(covers, max_arity, alpha)
    return model


def eval_covers(
    block_bits: int,
    max_arity: int,
    frontier: int,
    atoms: int,
    slack: int,
    model: ArityModel,
    trials: int,
    seed: int,
) -> list[Cover]:
    rng = random.Random(seed)
    return [
        cover_sample(
            sample_availability(block_bits, max_arity, frontier, atoms, slack, rng),
            block_bits,
            frontier,
            model,
            slack,
        )
        for _ in range(trials)
    ]


def simulate_config(args: argparse.Namespace, config: Config, slack: int) -> Row:
    current_bits = [float(config.atoms * config.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    log_rhos: list[float] = []
    all_covers: list[Cover] = []
    covered_count = 0
    total_cover_attempts = 0

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
                + slack * 7919
                + pass_index * 104729
                + atoms * 17
            )
            model = train_model(
                config.block_bits,
                config.max_arity,
                config.frontier,
                atoms,
                slack,
                args.train_trials,
                args.iterations,
                args.alpha,
                seed_base,
            )
            covers = eval_covers(
                config.block_bits,
                config.max_arity,
                config.frontier,
                atoms,
                slack,
                model,
                len(trial_indices),
                seed_base + 424242,
            )
            for trial_index, cover in zip(trial_indices, covers):
                covers_by_trial[trial_index] = cover

        ordered = [cover for cover in covers_by_trial if cover is not None]
        total_cover_attempts += len(ordered)
        covered_count += sum(1 for cover in ordered if cover.covered)
        if not all(cover.covered for cover in ordered):
            all_covers.extend(ordered)
            return summarize_row(config, slack, "failed", log_rhos, current_bits, initial_bits, all_covers, covered_count, total_cover_attempts)

        outputs = [cover.charged_bits for cover in ordered]
        log_rhos.extend(math.log2(out / inp) for out, inp in zip(outputs, padded_bits))
        current_bits = outputs
        all_covers.extend(ordered)

    return summarize_row(config, slack, "compressive" if mean(log_rhos) < 0.0 else "expanding", log_rhos, current_bits, initial_bits, all_covers, covered_count, total_cover_attempts)


def summarize_row(
    config: Config,
    slack: int,
    status: str,
    log_rhos: list[float],
    current_bits: list[float],
    initial_bits: list[float],
    covers: list[Cover],
    covered_count: int,
    cover_attempts: int,
) -> Row:
    covered = [cover for cover in covers if cover.covered]
    records = [record for cover in covered for record in cover.records]
    mean_log = mean(log_rhos) if log_rhos else float("nan")
    return Row(
        config=config,
        slack=slack,
        status=status,
        mean_log2_rho=mean_log,
        geometric_rho=(2.0**mean_log) if not math.isnan(mean_log) else float("nan"),
        final_bits_avg=mean(current_bits) if current_bits else float("nan"),
        total_ratio_avg=mean(final / start for final, start in zip(current_bits, initial_bits)) if current_bits else float("nan"),
        records_per_atom=(len(records) / sum(sum(record.arity for record in cover.records) for cover in covered)) if records else 0.0,
        avg_arity=mean(record.arity for record in records) if records else 0.0,
        avg_width=mean(record.width for record in records) if records else 0.0,
        coverage=(covered_count / cover_attempts) if cover_attempts else 0.0,
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
        Config(4, 128, 512, 160),
        Config(4, 192, 768, 192),
    ]


def fmt(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.6f}"


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# Fixed-Slack Percolation Reproduction Sweep",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`, "
        f"`train_trials={args.train_trials}`, `iterations={args.iterations}`.",
        "",
        "Each interval is available with exact fixed-width probability",
        "`1-exp(-2^(width-aB))`. This is a high-K surrogate for H9, not an",
        "oracle: width is decoder-derived and the arity model is trained on",
        "independent covers.",
        "",
        "| B | K | D | atoms | slack | status | coverage | mean log2 rho | geometric rho | final bits avg | total ratio avg | rec/atom | avg arity | avg width |",
        "| ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        c = row.config
        lines.append(
            f"| {c.block_bits} | {c.max_arity} | {c.frontier} | {c.atoms} | "
            f"{row.slack} | {row.status} | {row.coverage:.3f} | "
            f"{fmt(row.mean_log2_rho)} | {fmt(row.geometric_rho)} | "
            f"{fmt(row.final_bits_avg)} | {fmt(row.total_ratio_avg)} | "
            f"{row.records_per_atom:.6f} | {row.avg_arity:.2f} | "
            f"{row.avg_width:.2f} |"
        )

    paid = [row for row in rows if row.status != "failed" and not math.isnan(row.mean_log2_rho)]
    lines.extend(["", "## Reading", ""])
    if paid:
        best = min(paid, key=lambda row: row.mean_log2_rho)
        lines.append(
            "Best covered row: "
            f"`B={best.config.block_bits},K={best.config.max_arity},"
            f"D={best.config.frontier},slack={best.slack}` with "
            f"`mean log2 rho={best.mean_log2_rho:.6f}`."
        )
    else:
        lines.append("No row maintained full cover across tested passes.")
    lines.append(
        "A positive row means the extra saved slack is still returned through "
        "coverage loss, arity cost, or padding. A failed row means the fixed "
        "witness supply cannot maintain total cover in the tested regime."
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", action="append", type=parse_config, dest="configs")
    parser.add_argument("--slacks", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--train-trials", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=9209)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs if args.configs else default_configs()
    rows = [simulate_config(args, config, slack) for config in configs for slack in args.slacks]
    print(render(rows, args))


if __name__ == "__main__":
    main()
