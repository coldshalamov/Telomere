#!/usr/bin/env python3
"""H59 - bounded raw/Q stop mixture audit.

H57/H58 make normalized collective Q very close but still above raw in expected
bits. H59 tests the honest escape/stopping version:

    M(x) = (1-alpha) * U_n(x) + alpha/T * sum_t Q_t(x)

where each `Q_t` is a public normalized collective-cover distribution for a
public stop/pass/lane. No per-file "use Q if shorter" selector is allowed.
The raw escape and stop choices are paid by the mixture weights.

For sampled Q lengths L_t(x) = -log2 Q_t(x):

    L_M(x) = n - log2((1-alpha) + alpha/T * sum_t 2^(n-L_t(x)))

Alpha is trained on independent uniform-law samples and frozen before eval.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
H57_PATH = ROOT / "model_analysis" / "birth_channel_research" / "H57-normalized_q_percolation_rg.py"


def load_h57():
    spec = importlib.util.spec_from_file_location("h57_normalized_q_percolation_rg", H57_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {H57_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H57 = load_h57()


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class Row:
    config: Config
    stops: int
    alpha: float
    train_excess_bits: float
    eval_excess_bits: float
    eval_mean_log2_rho: float
    eval_geometric_rho: float
    eval_below_raw_fraction: float
    eval_min_bits: float
    eval_max_bits: float


def h57_config(config: Config):
    return H57.Config(config.block_bits, config.max_arity, config.frontier, config.atoms)


def q_lengths(
    config: Config,
    stops: int,
    trials: int,
    seed: int,
) -> list[list[float]]:
    hcfg = h57_config(config)
    rows: list[list[float]] = []
    for trial in range(trials):
        lane_lengths: list[float] = []
        for stop in range(stops):
            lane_seed = seed + trial * 1_000_003 + stop * 97_531
            rng = H57.random.Random(lane_seed)
            paid = H57.paid_bits_for_sample(hcfg, config.atoms, "uniform", rng)
            lane_lengths.append(paid)
        rows.append(lane_lengths)
    return rows


def mixture_bits(raw_bits: int, q_bits: list[float], alpha: float) -> float:
    if alpha <= 0.0:
        return float(raw_bits)
    if alpha >= 1.0:
        raw_weight = 0.0
    else:
        raw_weight = 1.0 - alpha
    q_weight = alpha / len(q_bits)
    scaled_mass = raw_weight
    for bits in q_bits:
        if math.isfinite(bits):
            scaled_mass += q_weight * (2.0 ** (raw_bits - bits))
    if scaled_mass <= 0.0:
        return float("inf")
    return raw_bits - math.log2(scaled_mass)


def avg_excess(raw_bits: int, samples: list[list[float]], alpha: float) -> float:
    return mean(mixture_bits(raw_bits, row, alpha) - raw_bits for row in samples)


def alpha_grid() -> list[float]:
    values = {
        0.0,
        1e-4,
        3e-4,
        1e-3,
        3e-3,
        1e-2,
        3e-2,
        0.1,
        0.2,
        0.35,
        0.5,
        0.75,
        1.0,
    }
    return sorted(values)


def run_row(args: argparse.Namespace, config: Config, stops: int) -> Row:
    raw_bits = config.atoms * config.block_bits
    train = q_lengths(config, stops, args.train_trials, args.seed + stops * 1009)
    candidates = [(avg_excess(raw_bits, train, alpha), alpha) for alpha in alpha_grid()]
    train_excess, alpha = min(candidates)
    eval_samples = q_lengths(config, stops, args.eval_trials, args.seed + 424_242 + stops * 1009)
    eval_bits = [mixture_bits(raw_bits, row, alpha) for row in eval_samples]
    log_rhos = [math.log2(bits / raw_bits) for bits in eval_bits]
    return Row(
        config=config,
        stops=stops,
        alpha=alpha,
        train_excess_bits=train_excess,
        eval_excess_bits=mean(bits - raw_bits for bits in eval_bits),
        eval_mean_log2_rho=mean(log_rhos),
        eval_geometric_rho=2.0 ** mean(log_rhos),
        eval_below_raw_fraction=sum(1 for bits in eval_bits if bits < raw_bits) / len(eval_bits),
        eval_min_bits=min(eval_bits),
        eval_max_bits=max(eval_bits),
    )


def parse_config(text: str) -> Config:
    block_bits, max_arity, frontier, atoms = (int(part) for part in text.split(","))
    return Config(block_bits, max_arity, frontier, atoms)


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# H59 - Raw/Q Stop Mixture Audit",
        "",
        f"`train_trials={args.train_trials}`, `eval_trials={args.eval_trials}`.",
        "",
        "Alpha is chosen on independent train samples, then frozen for eval. The",
        "mixture itself pays raw escape and stop/lane selection through public",
        "weights; no per-file min or kept-if-shrinks selector is used.",
        "",
        "| B | K | D | atoms | stops T | alpha | train excess | eval excess | eval mean log2 rho | geom rho | below raw | min bits | max bits |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        cfg = row.config
        lines.append(
            f"| {cfg.block_bits} | {cfg.max_arity} | {cfg.frontier} | {cfg.atoms} | "
            f"{row.stops} | {row.alpha:.4f} | {row.train_excess_bits:.6f} | "
            f"{row.eval_excess_bits:.6f} | {row.eval_mean_log2_rho:.6f} | "
            f"{row.eval_geometric_rho:.6f} | {row.eval_below_raw_fraction:.3f} | "
            f"{row.eval_min_bits:.6f} | {row.eval_max_bits:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "`alpha=0` means the best public mixture is raw escape only. Any row with",
            "`alpha>0` must still beat raw on held-out expected bits before it can be",
            "called progress toward roughly-all-data compression.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", dest="configs", type=parse_config, action="append", default=None)
    parser.add_argument("--stops", type=int, nargs="+", default=[1, 4, 16])
    parser.add_argument("--train-trials", type=int, default=32)
    parser.add_argument("--eval-trials", type=int, default=64)
    parser.add_argument("--seed", type=int, default=737373)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs or [
        Config(4, 256, 1024, 256),
        Config(4, 384, 1536, 384),
    ]
    rows = [run_row(args, config, stops) for config in configs for stops in args.stops]
    print(render(rows, args))


if __name__ == "__main__":
    main()
