#!/usr/bin/env python3
"""H58 - frozen public arity model for normalized collective-Q RG.

H57 used a uniform legal-arity model inside normalized collective cover Q.
H58 asks whether a better *public* arity law can move the high-K frontier.

The arity model is trained only on independent uniform-law samples for the
same public `(B,K,D,N)` profile, then frozen before held-out evaluation. No
target-layer counts or selected-cover metadata are used.

For a sampled layer, every interval has matching witness count:

    C_i,a ~ Poisson(2^(w-aB)), w=min(D,aB)

The collective edge mass is:

    C_i,a * q(a | context) * 2^-w

The normalized public code is:

    paid_bits(x) = n - log2(Q_raw(x)) + log2(E_uniform[Q_raw(X)])

Both repeated-pass log-rho and expected paid bits are reported. A log-rho
crossing alone is not enough for roughly-all-data compression.
"""

from __future__ import annotations

import argparse
import math
import random
from collections import Counter, defaultdict
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
class QModel:
    context_mode: str
    max_arity: int
    alpha: float
    counts: dict[tuple[int, ...], Counter[int]]


@dataclass(frozen=True)
class Row:
    config: Config
    context_mode: str
    status: str
    coverage: float
    avg_paid_bits: float
    avg_excess_bits: float
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    below_raw_fraction: float
    avg_q_entropy: float
    top_arity: int
    top_arity_prob: float


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
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def width_bits_for(block_bits: int, frontier: int, arity: int) -> int:
    return min(frontier, arity * block_bits)


def remaining_bucket(remaining: int, max_arity: int) -> int:
    if remaining <= max_arity:
        return remaining
    ratio = (remaining + max_arity - 1) // max_arity
    return max_arity + min(16, int(math.log2(ratio)) + 1)


def context_for(mode: str, remaining: int, max_arity: int) -> tuple[int, ...]:
    if mode == "global":
        return ()
    if mode == "bucket":
        return (remaining_bucket(remaining, max_arity),)
    if mode == "exact":
        return (remaining,)
    raise ValueError(mode)


def q_prob(model: QModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return 0.0
    context = context_for(model.context_mode, remaining, model.max_arity)
    counts = model.counts.get(context, Counter())
    denom_count = sum(counts.get(value, 0.0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return (counts.get(arity, 0.0) + model.alpha) / denom


def q_tables(model: QModel, atoms: int) -> list[list[float]]:
    tables: list[list[float]] = []
    for index in range(atoms):
        remaining = atoms - index
        legal_max = min(model.max_arity, remaining)
        context = context_for(model.context_mode, remaining, model.max_arity)
        counts = model.counts.get(context, Counter())
        denom_count = sum(counts.get(value, 0.0) for value in range(1, legal_max + 1))
        denom = denom_count + model.alpha * legal_max
        tables.append(
            [
                (counts.get(arity, 0.0) + model.alpha) / denom
                for arity in range(1, legal_max + 1)
            ]
        )
    return tables


def sample_counts(config: Config, atoms: int, rng: random.Random) -> list[list[int]]:
    rows: list[list[int]] = []
    for index in range(atoms):
        legal_max = min(config.max_arity, atoms - index)
        row: list[int] = []
        for arity in range(1, legal_max + 1):
            width = width_bits_for(config.block_bits, config.frontier, arity)
            lam = 2.0 ** (width - arity * config.block_bits)
            row.append(poisson(lam, rng))
        rows.append(row)
    return rows


def forward_backward(
    counts: list[list[int]],
    config: Config,
    model: QModel,
) -> tuple[list[float], list[float], float]:
    atoms = len(counts)
    q_by_index = q_tables(model, atoms)
    forward = [NEG_INF] * (atoms + 1)
    forward[0] = 0.0
    for index in range(atoms):
        base = forward[index]
        if base == NEG_INF:
            continue
        remaining = atoms - index
        for arity, count in enumerate(counts[index], start=1):
            if count <= 0:
                continue
            width = width_bits_for(config.block_bits, config.frontier, arity)
            q = q_by_index[index][arity - 1]
            if q <= 0.0:
                continue
            edge_log = math.log2(count) + math.log2(q) - width
            forward[index + arity] = log2_add(forward[index + arity], base + edge_log)

    backward = [NEG_INF] * (atoms + 1)
    backward[atoms] = 0.0
    for index in range(atoms - 1, -1, -1):
        remaining = atoms - index
        total = NEG_INF
        for arity, count in enumerate(counts[index], start=1):
            if count <= 0:
                continue
            end = index + arity
            if end > atoms or backward[end] == NEG_INF:
                continue
            width = width_bits_for(config.block_bits, config.frontier, arity)
            q = q_by_index[index][arity - 1]
            if q <= 0.0:
                continue
            edge_log = math.log2(count) + math.log2(q) - width
            total = log2_add(total, edge_log + backward[end])
        backward[index] = total
    return forward, backward, forward[atoms]


def posterior_counts(
    samples: list[list[list[int]]],
    config: Config,
    model: QModel,
) -> dict[tuple[int, ...], Counter[int]]:
    next_counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for counts in samples:
        atoms = len(counts)
        q_by_index = q_tables(model, atoms)
        forward, backward, total = forward_backward(counts, config, model)
        if total == NEG_INF:
            continue
        for index in range(atoms):
            if forward[index] == NEG_INF:
                continue
            remaining = atoms - index
            context = context_for(model.context_mode, remaining, model.max_arity)
            for arity, count in enumerate(counts[index], start=1):
                if count <= 0:
                    continue
                end = index + arity
                if end > atoms or backward[end] == NEG_INF:
                    continue
                width = width_bits_for(config.block_bits, config.frontier, arity)
                q = q_by_index[index][arity - 1]
                if q <= 0.0:
                    continue
                edge_log = math.log2(count) + math.log2(q) - width
                responsibility = 2.0 ** (forward[index] + edge_log + backward[end] - total)
                next_counts[context][arity] += responsibility
    return dict(next_counts)


def train_model(
    config: Config,
    atoms: int,
    context_mode: str,
    train_trials: int,
    iterations: int,
    alpha: float,
    seed: int,
) -> QModel:
    rng = random.Random(seed)
    samples = [sample_counts(config, atoms, rng) for _ in range(train_trials)]
    model = QModel(context_mode, config.max_arity, alpha, {})
    for _ in range(iterations):
        model = QModel(
            context_mode,
            config.max_arity,
            alpha,
            posterior_counts(samples, config, model),
        )
    return model


def expected_log_qraw(config: Config, atoms: int, model: QModel) -> float:
    q_by_index = q_tables(model, atoms)
    dp = [NEG_INF] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == NEG_INF:
            continue
        remaining = atoms - index
        legal_max = min(config.max_arity, remaining)
        for arity in range(1, legal_max + 1):
            q = q_by_index[index][arity - 1]
            if q <= 0.0:
                continue
            edge_log = math.log2(q) - arity * config.block_bits
            dp[index + arity] = log2_add(dp[index + arity], base + edge_log)
    return dp[atoms]


def sampled_log_qraw(config: Config, atoms: int, model: QModel, rng: random.Random) -> float:
    counts = sample_counts(config, atoms, rng)
    _, _, total = forward_backward(counts, config, model)
    return total


def paid_bits_for_sample(config: Config, atoms: int, model: QModel, rng: random.Random) -> float:
    sampled = sampled_log_qraw(config, atoms, model, rng)
    if sampled == NEG_INF:
        return float("inf")
    expected = expected_log_qraw(config, atoms, model)
    raw_bits = atoms * config.block_bits
    return raw_bits - sampled + expected


def q_summary(model: QModel, atoms: int) -> tuple[float, int, float]:
    probs = q_tables(model, atoms)[0]
    entropy = -sum(prob * math.log2(prob) for prob in probs if prob > 0.0)
    top_index = max(range(len(probs)), key=probs.__getitem__) if probs else 0
    return entropy, top_index + 1, probs[top_index] if probs else 0.0


def simulate_config(args: argparse.Namespace, config: Config, context_mode: str) -> Row:
    current_bits = [float(config.atoms * config.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    log_rhos: list[float] = []
    paid_values: list[float] = []
    covered = 0
    attempts = 0
    entropy_samples: list[float] = []
    top_arities: list[int] = []
    top_probs: list[float] = []

    for pass_index in range(1, args.passes + 1):
        next_bits: list[float] = []
        groups: dict[int, list[int]] = defaultdict(list)
        for trial_index, bits in enumerate(current_bits):
            groups[max(1, math.ceil(bits / config.block_bits))].append(trial_index)

        models: dict[int, QModel] = {}
        for atoms in groups:
            seed = (
                args.seed
                + config.block_bits * 1000003
                + config.max_arity * 10007
                + config.frontier * 101
                + pass_index * 104729
                + atoms * 17
                + {"global": 11, "bucket": 23, "exact": 37}[context_mode]
            )
            model = train_model(
                config,
                atoms,
                context_mode,
                args.train_trials,
                args.iterations,
                args.alpha,
                seed,
            )
            models[atoms] = model
            entropy, top_arity, top_prob = q_summary(model, atoms)
            entropy_samples.append(entropy)
            top_arities.append(top_arity)
            top_probs.append(top_prob)

        for trial_index, bits in enumerate(current_bits):
            atoms = max(1, math.ceil(bits / config.block_bits))
            padded_bits = atoms * config.block_bits
            seed = (
                args.seed
                + config.block_bits * 1000003
                + config.max_arity * 10007
                + config.frontier * 101
                + pass_index * 99991
                + trial_index * 7919
                + atoms * 23
                + {"global": 11, "bucket": 23, "exact": 37}[context_mode]
            )
            paid = paid_bits_for_sample(config, atoms, models[atoms], random.Random(seed))
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
            return summarize_row(
                config,
                context_mode,
                "failed",
                paid_values,
                log_rhos,
                current_bits,
                initial_bits,
                covered,
                attempts,
                entropy_samples,
                top_arities,
                top_probs,
            )
        current_bits = next_bits

    return summarize_row(
        config,
        context_mode,
        "compressive" if mean(log_rhos) < 0.0 else "expanding",
        paid_values,
        log_rhos,
        current_bits,
        initial_bits,
        covered,
        attempts,
        entropy_samples,
        top_arities,
        top_probs,
    )


def summarize_row(
    config: Config,
    context_mode: str,
    status: str,
    paid_values: list[float],
    log_rhos: list[float],
    current_bits: list[float],
    initial_bits: list[float],
    covered: int,
    attempts: int,
    entropy_samples: list[float],
    top_arities: list[int],
    top_probs: list[float],
) -> Row:
    finite_paid = [value for value in paid_values if math.isfinite(value)]
    raw_bits = config.atoms * config.block_bits
    initial_avg = mean(initial_bits) if initial_bits else float(raw_bits)
    final_avg = mean(current_bits) if current_bits else float("inf")
    top_arity = Counter(top_arities).most_common(1)[0][0] if top_arities else 0
    return Row(
        config=config,
        context_mode=context_mode,
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
        avg_q_entropy=mean(entropy_samples) if entropy_samples else 0.0,
        top_arity=top_arity,
        top_arity_prob=mean(top_probs) if top_probs else 0.0,
    )


def parse_config(text: str) -> Config:
    block_bits, max_arity, frontier, atoms = (int(part) for part in text.split(","))
    return Config(block_bits, max_arity, frontier, atoms)


def render(rows: list[Row], args: argparse.Namespace) -> str:
    lines = [
        "# H58 - Frozen Public-Q Arity Model RG",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`, "
        f"`train_trials={args.train_trials}`, `iterations={args.iterations}`.",
        "",
        "Arity models are trained on independent uniform-law samples and then",
        "frozen before held-out evaluation. Expected paid bits must cross raw;",
        "a negative log-rho diagnostic alone is not promoted.",
        "",
        "| B | K | D | atoms | context | status | coverage | avg paid bits | avg excess bits | mean log2 rho | geom rho | final bits avg | total ratio | below raw | q entropy | top arity | top prob |",
        "| ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        cfg = row.config
        lines.append(
            f"| {cfg.block_bits} | {cfg.max_arity} | {cfg.frontier} | {cfg.atoms} | "
            f"{row.context_mode} | {row.status} | {row.coverage:.3f} | "
            f"{row.avg_paid_bits:.6f} | {row.avg_excess_bits:.6f} | "
            f"{row.mean_log2_rho:.6f} | {row.geometric_rho:.6f} | "
            f"{row.final_bits_avg:.6f} | {row.total_ratio_avg:.6f} | "
            f"{row.below_raw_fraction:.3f} | {row.avg_q_entropy:.3f} | "
            f"{row.top_arity} | {row.top_arity_prob:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A frozen public arity law may reduce the normalized-Q geometric gap, but",
            "for uniform fixed-length data the expected-length gate remains:",
            "",
            "```text",
            "E_U[-log2 Q(X)] = n + KL(U || Q) >= n",
            "```",
            "",
            "Rows with `avg excess bits > 0` are misses even if `mean log2 rho` is",
            "near zero or negative.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", dest="configs", type=parse_config, action="append", default=None)
    parser.add_argument("--contexts", choices=["global", "bucket", "exact"], nargs="+", default=["global", "bucket"])
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--train-trials", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=515151)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs or [
        Config(4, 256, 1024, 256),
        Config(4, 384, 1536, 384),
        Config(4, 512, 2048, 512),
    ]
    rows = [
        simulate_config(args, config, context_mode)
        for config in configs
        for context_mode in args.contexts
    ]
    print(render(rows, args))


if __name__ == "__main__":
    main()
