#!/usr/bin/env python3
"""H57 - normalized collective-cover Q at the high-K percolation frontier.

H51 proved exact tiny normalized-Q accounting:

    Q_raw(x) = sum_{covers c -> x} 2^-L(c)
    Q(x)     = Q_raw(x) / Z
    paid_bits(x) = -log2 Q(x)

H57 moves that idea to the H52/H53 high-K fixed-width frontier with a
percolation approximation. Instead of choosing one cover and paying its
selected witness fields, it sums every matching cover as latent mass.

For an interval with arity a and width w=min(D,aB), the number of matching
witnesses under the uniform hash law is:

    C_i,a ~ Poisson(2^(w-aB))

The edge contributes mass:

    C_i,a * 2^-(w + arity_cost(remaining,a))

The public normalization uses the expected edge mass:

    E[C_i,a] * 2^-(w + arity_cost) = 2^(-aB - arity_cost)

Then for raw layer size n=N*B:

    paid_bits(x) = n - log2(Q_raw(x)) + log2(E_uniform[Q_raw(X)])

This is a scout, not a production arithmetic coder. It intentionally reports
expected-length and repeated-pass log-rho so the Jensen/counting trap is visible.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from statistics import mean


NEG_INF = float("-inf")


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class Row:
    config: Config
    arity_model: str
    status: str
    coverage: float
    avg_paid_bits: float
    avg_excess_bits: float
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    below_raw_fraction: float
    min_paid_bits: float
    max_paid_bits: float


def log2_add(lhs: float, rhs: float) -> float:
    if lhs == NEG_INF:
        return rhs
    if rhs == NEG_INF:
        return lhs
    if rhs > lhs:
        lhs, rhs = rhs, lhs
    return lhs + math.log2(1.0 + 2.0 ** (rhs - lhs))


def poisson(lam: float, rng: random.Random) -> int:
    if lam <= 0.0:
        return 0
    if lam < 30.0:
        limit = math.exp(-lam)
        k = 0
        product = 1.0
        while product > limit:
            k += 1
            product *= rng.random()
        return k - 1
    # Normal approximation is only for completeness; default rows use lam=1.
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def width_bits_for(block_bits: int, frontier: int, arity: int) -> int:
    return min(frontier, arity * block_bits)


def arity_cost(model: str, max_arity: int, remaining: int, arity: int) -> float:
    legal_max = min(max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    if model == "uniform":
        return math.log2(legal_max)
    raise ValueError(model)


def expected_log_qraw(config: Config, atoms: int, arity_model: str) -> float:
    """Return log2(E_uniform[Q_raw(X)]) for N atoms."""

    dp = [NEG_INF] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == NEG_INF:
            continue
        remaining = atoms - index
        legal_max = min(config.max_arity, remaining)
        for arity in range(1, legal_max + 1):
            cost = arity_cost(arity_model, config.max_arity, remaining, arity)
            edge_log = -(arity * config.block_bits) - cost
            dp[index + arity] = log2_add(dp[index + arity], base + edge_log)
    return dp[atoms]


def sampled_log_qraw(
    config: Config,
    atoms: int,
    arity_model: str,
    rng: random.Random,
) -> float:
    dp = [NEG_INF] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == NEG_INF:
            continue
        remaining = atoms - index
        legal_max = min(config.max_arity, remaining)
        for arity in range(1, legal_max + 1):
            width = width_bits_for(config.block_bits, config.frontier, arity)
            lam = 2.0 ** (width - arity * config.block_bits)
            count = poisson(lam, rng)
            if count <= 0:
                continue
            cost = width + arity_cost(arity_model, config.max_arity, remaining, arity)
            edge_log = math.log2(count) - cost
            dp[index + arity] = log2_add(dp[index + arity], base + edge_log)
    return dp[atoms]


def paid_bits_for_sample(
    config: Config,
    atoms: int,
    arity_model: str,
    rng: random.Random,
) -> float:
    sampled = sampled_log_qraw(config, atoms, arity_model, rng)
    if sampled == NEG_INF:
        return float("inf")
    expected = expected_log_qraw(config, atoms, arity_model)
    raw_bits = atoms * config.block_bits
    return raw_bits - sampled + expected


def simulate_config(args: argparse.Namespace, config: Config, arity_model: str) -> Row:
    current_bits = [float(config.atoms * config.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    log_rhos: list[float] = []
    paid_values: list[float] = []
    covered = 0
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
            paid = paid_bits_for_sample(config, atoms, arity_model, random.Random(seed))
            attempts += 1
            if not math.isfinite(paid):
                paid_values.append(float("inf"))
                next_bits.append(float("inf"))
                continue
            covered += 1
            paid_values.append(paid)
            log_rhos.append(math.log2(paid / padded_bits))
            next_bits.append(paid)
        if any(not math.isfinite(value) for value in next_bits):
            return summarize_row(config, arity_model, "failed", paid_values, log_rhos, current_bits, initial_bits, covered, attempts)
        current_bits = next_bits

    return summarize_row(
        config,
        arity_model,
        "compressive" if mean(log_rhos) < 0.0 else "expanding",
        paid_values,
        log_rhos,
        current_bits,
        initial_bits,
        covered,
        attempts,
    )


def summarize_row(
    config: Config,
    arity_model: str,
    status: str,
    paid_values: list[float],
    log_rhos: list[float],
    current_bits: list[float],
    initial_bits: list[float],
    covered: int,
    attempts: int,
) -> Row:
    finite_paid = [value for value in paid_values if math.isfinite(value)]
    raw_bits = config.atoms * config.block_bits
    initial_avg = mean(initial_bits) if initial_bits else float(raw_bits)
    final_avg = mean(current_bits) if current_bits else float("inf")
    return Row(
        config=config,
        arity_model=arity_model,
        status=status,
        coverage=covered / attempts if attempts else 0.0,
        avg_paid_bits=mean(finite_paid) if finite_paid else float("inf"),
        avg_excess_bits=mean(value - raw_bits for value in finite_paid)
        if finite_paid
        else float("inf"),
        mean_log2_rho=mean(log_rhos) if log_rhos else float("inf"),
        geometric_rho=2.0 ** mean(log_rhos) if log_rhos else float("inf"),
        final_bits_avg=final_avg,
        total_ratio_avg=final_avg / initial_avg if initial_avg else float("inf"),
        below_raw_fraction=sum(1 for value in finite_paid if value < raw_bits) / len(finite_paid)
        if finite_paid
        else 0.0,
        min_paid_bits=min(finite_paid) if finite_paid else float("inf"),
        max_paid_bits=max(finite_paid) if finite_paid else float("inf"),
    )


def parse_config(text: str) -> Config:
    block_bits, max_arity, frontier, atoms = (int(part) for part in text.split(","))
    return Config(block_bits, max_arity, frontier, atoms)


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# H57 - Normalized Collective-Q Percolation RG",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`.",
        "",
        "This sums all matching covers as latent mass and normalizes by the public",
        "uniform-law expected mass. Uniform expected bits remain the honest test;",
        "`mean log2 rho` is the repeated-pass reproduction diagnostic.",
        "",
        "| B | K | D | atoms | arity model | status | coverage | avg paid bits | avg excess bits | mean log2 rho | geom rho | final bits avg | total ratio | below raw | min bits | max bits |",
        "| ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        cfg = row.config
        lines.append(
            f"| {cfg.block_bits} | {cfg.max_arity} | {cfg.frontier} | {cfg.atoms} | "
            f"{row.arity_model} | {row.status} | {row.coverage:.3f} | "
            f"{row.avg_paid_bits:.6f} | {row.avg_excess_bits:.6f} | "
            f"{row.mean_log2_rho:.6f} | {row.geometric_rho:.6f} | "
            f"{row.final_bits_avg:.6f} | {row.total_ratio_avg:.6f} | "
            f"{row.below_raw_fraction:.3f} | {row.min_paid_bits:.6f} | "
            f"{row.max_paid_bits:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A negative `mean log2 rho` with positive `avg excess bits` would still",
            "be suspect under uniform coding; both must be negative before promotion.",
            "If this misses, collective-cover normalization remains a source-prior",
            "tool rather than a roughly-all-data recursive compressor.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", dest="configs", type=parse_config, action="append", default=None)
    parser.add_argument("--arity-models", choices=["uniform"], nargs="+", default=["uniform"])
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=424242)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs or [
        Config(4, 128, 512, 160),
        Config(4, 192, 768, 192),
        Config(4, 256, 1024, 256),
    ]
    rows = [
        simulate_config(args, config, arity_model)
        for config in configs
        for arity_model in args.arity_models
    ]
    print(render(rows, args))


if __name__ == "__main__":
    main()
