#!/usr/bin/env python3
"""H56 - self-synchronizing arity syntax for headerless slack ladders.

H55 found that some toy self-delimiting arity grammars make global slack
languages disjoint in small exact enumerations. H56 asks the next accounting
question: if the arity syntax itself is charged, can a headerless slack ladder
cross the repeated-pass reproduction target?

This is a bounded RG-style scout, not a production codec. It keeps Total-Cover
semantics: every record opens; no birth/open/carry maps are charged. A record
cost is:

    arity_syntax_bits(a) + width_s(a)

where:

    width_s(a) = min(D, aB - s)

Modes:

* headerless_best: choose the cheapest slack without selector bits. This is
  legal only for a syntax whose slack languages are proven disjoint, so treat
  it as a candidate/lower-bound row until a decoder proof exists at scale.
* paid_best: same choice plus log2(|S|) global selector bits.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


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
    slack: int | None


@dataclass(frozen=True)
class Row:
    config: Config
    code: str
    mode: str
    slacks: tuple[int, ...]
    selector_bits: float
    status: str
    coverage: float
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    avg_arity_bits: float
    avg_slack: float


def gamma_len(value: int) -> int:
    return 2 * value.bit_length() - 1


def fibonacci_len(value: int) -> int:
    fibs = [1, 2]
    while fibs[-1] < value:
        fibs.append(fibs[-1] + fibs[-2])
    used_highest = 0
    remaining = value
    for index in range(len(fibs) - 1, -1, -1):
        if fibs[index] <= remaining:
            used_highest = max(used_highest, index)
            remaining -= fibs[index]
    return used_highest + 2  # representation bits through highest + terminator


def arity_bits(code: str, max_arity: int, arity: int) -> int:
    if code == "fixed":
        return max(1, math.ceil(math.log2(max_arity + 1)))
    if code == "gamma":
        return gamma_len(arity)
    if code == "fibonacci":
        return fibonacci_len(arity)
    raise ValueError(code)


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


def sample_scores(max_arity: int, atoms: int, rng: random.Random) -> list[list[float]]:
    return [
        [rng.expovariate(1.0) for _ in range(min(max_arity, atoms - index))]
        for index in range(atoms)
    ]


def cover_scores(
    scores: list[list[float]],
    config: Config,
    slack: int,
    code: str,
) -> Cover:
    atoms = len(scores)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for arity, score in enumerate(scores[index], start=1):
            threshold = hit_threshold(config.block_bits, config.frontier, arity, slack)
            if score > threshold:
                continue
            width = width_bits_for(config.block_bits, config.frontier, arity, slack)
            if width is None:
                continue
            cost = width + arity_bits(code, config.max_arity, arity)
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


def choose_cover(
    scores: list[list[float]],
    config: Config,
    slacks: tuple[int, ...],
    code: str,
    selector_bits: float,
    mode: str,
) -> Cover:
    covers = [cover_scores(scores, config, slack, code) for slack in slacks]
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return Cover(False, float("inf"), (), None)
    best = min(covered, key=lambda cover: cover.charged_bits)
    if mode == "headerless_best":
        return best
    if mode == "paid_best":
        return Cover(True, best.charged_bits + selector_bits, best.records, best.slack)
    raise ValueError(mode)


def simulate_config(args: argparse.Namespace, config: Config, code: str, mode: str) -> Row:
    slacks = tuple(args.slacks)
    selector_bits = 0.0 if mode == "headerless_best" else math.log2(len(slacks))
    current_bits = [float(config.atoms * config.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    log_rhos: list[float] = []
    all_covers: list[Cover] = []
    covered_count = 0
    attempts = 0

    for pass_index in range(1, args.passes + 1):
        next_bits: list[float] = []
        for trial_index, bits in enumerate(current_bits):
            atoms = max(1, math.ceil(bits / config.block_bits))
            padded_bits = atoms * config.block_bits
            seed = (
                args.seed
                + config.block_bits * 1000003
                + config.max_arity * 10007
                + config.frontier * 101
                + pass_index * 104729
                + trial_index * 7919
                + atoms * 17
            )
            scores = sample_scores(config.max_arity, atoms, random.Random(seed))
            cover = choose_cover(scores, config, slacks, code, selector_bits, mode)
            attempts += 1
            covered_count += int(cover.covered)
            all_covers.append(cover)
            if not cover.covered:
                return summarize_row(
                    config,
                    code,
                    mode,
                    slacks,
                    selector_bits,
                    "failed",
                    log_rhos,
                    current_bits,
                    initial_bits,
                    all_covers,
                    covered_count,
                    attempts,
                )
            log_rhos.append(math.log2(cover.charged_bits / padded_bits))
            next_bits.append(cover.charged_bits)
        current_bits = next_bits

    return summarize_row(
        config,
        code,
        mode,
        slacks,
        selector_bits,
        "compressive" if mean(log_rhos) < 0.0 else "expanding",
        log_rhos,
        current_bits,
        initial_bits,
        all_covers,
        covered_count,
        attempts,
    )


def summarize_row(
    config: Config,
    code: str,
    mode: str,
    slacks: tuple[int, ...],
    selector_bits: float,
    status: str,
    log_rhos: list[float],
    current_bits: list[float],
    initial_bits: list[float],
    covers: list[Cover],
    covered_count: int,
    attempts: int,
) -> Row:
    records = [record for cover in covers if cover.covered for record in cover.records]
    initial_avg = mean(initial_bits) if initial_bits else float(config.atoms * config.block_bits)
    final_avg = mean(current_bits) if current_bits else float("inf")
    return Row(
        config=config,
        code=code,
        mode=mode,
        slacks=slacks,
        selector_bits=selector_bits,
        status=status,
        coverage=covered_count / attempts if attempts else 0.0,
        mean_log2_rho=mean(log_rhos) if log_rhos else float("inf"),
        geometric_rho=2.0 ** mean(log_rhos) if log_rhos else float("inf"),
        final_bits_avg=final_avg,
        total_ratio_avg=final_avg / initial_avg if initial_avg else float("inf"),
        records_per_atom=len(records) / (attempts * config.atoms) if attempts else 0.0,
        avg_arity=mean(record.arity for record in records) if records else 0.0,
        avg_width=mean(record.width for record in records) if records else 0.0,
        avg_arity_bits=mean(record.cost_bits - record.width for record in records)
        if records
        else 0.0,
        avg_slack=mean(cover.slack for cover in covers if cover.covered and cover.slack is not None)
        if any(cover.covered for cover in covers)
        else 0.0,
    )


def parse_config(text: str) -> Config:
    block_bits, max_arity, frontier, atoms = (int(part) for part in text.split(","))
    return Config(block_bits, max_arity, frontier, atoms)


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# H56 - Self-Synchronizing Slack Ladder RG",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`, `slacks={args.slacks}`.",
        "",
        "Record cost is `arity_syntax_bits + fixed slack width`. `headerless_best`",
        "does not charge a selector and is only legal if the syntax has a separate",
        "unique-survivor proof at scale.",
        "",
        "| B | K | D | atoms | code | mode | selector bits | status | coverage | mean log2 rho | geom rho | final bits avg | total ratio | rec/atom | avg arity | avg width | avg arity bits | avg slack |",
        "| ---: | ---: | ---: | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        cfg = row.config
        lines.append(
            f"| {cfg.block_bits} | {cfg.max_arity} | {cfg.frontier} | {cfg.atoms} | "
            f"{row.code} | {row.mode} | {row.selector_bits:.3f} | {row.status} | "
            f"{row.coverage:.3f} | {row.mean_log2_rho:.6f} | "
            f"{row.geometric_rho:.6f} | {row.final_bits_avg:.6f} | "
            f"{row.total_ratio_avg:.6f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width:.2f} | "
            f"{row.avg_arity_bits:.2f} | {row.avg_slack:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A negative `headerless_best` row would be a serious candidate only after",
            "an H55-style unique-language proof for the same syntax family. A positive",
            "row means the syntax-derived selector is not enough after paying the",
            "arity delimiter bits.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", dest="configs", type=parse_config, action="append", default=None)
    parser.add_argument("--slacks", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--codes", choices=["fixed", "gamma", "fibonacci"], nargs="+", default=["gamma", "fibonacci"])
    parser.add_argument("--modes", choices=["headerless_best", "paid_best"], nargs="+", default=["headerless_best", "paid_best"])
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--seed", type=int, default=90210)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs or [
        Config(4, 128, 512, 128),
        Config(4, 192, 768, 192),
        Config(4, 256, 1024, 256),
    ]
    rows = [
        simulate_config(args, config, code, mode)
        for config in configs
        for code in args.codes
        for mode in args.modes
    ]
    print(render(rows, args))


if __name__ == "__main__":
    main()
