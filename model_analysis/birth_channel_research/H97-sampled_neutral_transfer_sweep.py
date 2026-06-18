#!/usr/bin/env python3
"""H97 - sampled neutral-transfer sweep.

H96 exactly enumerates the smallest visible-genotype transfer operator. Exact
enumeration becomes combinatorial as D grows, so H97 keeps the same accounting
but samples candidate descriptions:

* current layer target x is a B=1 word;
* a candidate genotype is a concrete paid V1 record string that decodes to x;
* current cost is the visible bit length of that genotype;
* future value is the all-description saving of those visible bits next pass;
* the encoder may choose the best sampled genotype, but no selector is stored
  because the chosen genotype bits are the output.

Rows are not proof of positivity. They are response-surface probes for whether
neutral future lift scales before current visible cost overwhelms it.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


H96_PATH = Path(__file__).resolve().with_name("H96-neutral_transfer_operator.py")
_h96_spec = importlib.util.spec_from_file_location("h96_neutral_transfer_operator", H96_PATH)
if _h96_spec is None or _h96_spec.loader is None:
    raise RuntimeError("could not load H96 neutral transfer kernel")
_h96 = importlib.util.module_from_spec(_h96_spec)
sys.modules[_h96_spec.name] = _h96
_h96_spec.loader.exec_module(_h96)


@dataclass(frozen=True)
class Config:
    name: str
    atoms: int
    max_arity: int
    depth_bits: int
    word_trials: int
    candidates_per_word: int
    seed: int


@dataclass(frozen=True)
class SampledWordRow:
    word: int
    reachable: bool
    z_current: float
    collective_current_saving: float
    best_current_saving: float
    posterior_one_cycle: float
    posterior_one_future: float
    posterior_future_estimate: float
    unique_candidates: int
    best_transfer_cycle: float
    best_transfer_cycle_logm_net: float
    best_transfer_current: float
    best_transfer_future: float
    random_same_length_future: float
    random_same_length_best_future: float
    best_transfer_len: int


@dataclass(frozen=True)
class SummaryRow:
    name: str
    atoms: int
    max_arity: int
    depth_bits: int
    word_trials: int
    candidates_per_word: int
    reachable_fraction: float
    avg_unique_candidates: float
    collective_current_saving: float
    best_current_saving: float
    posterior_one_cycle: float
    posterior_one_future: float
    posterior_future_estimate: float
    best_transfer_cycle: float
    selector_tax_logm: float
    best_transfer_cycle_logm_net: float
    transfer_current: float
    transfer_future: float
    transfer_len: float
    random_same_length_future: float
    random_same_length_best_future: float
    neutral_future_lift: float
    neutral_future_lift_vs_best_random: float
    future_lift_vs_posterior: float
    positive_cycle_fraction: float
    positive_logm_net_fraction: float
    current_positive_fraction: float


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else float("-inf")


def weighted_choice(rng: random.Random, options: list[tuple[object, float]]) -> object:
    total = sum(weight for _, weight in options)
    if total <= 0.0:
        raise ValueError("empty weighted choice")
    draw = rng.random() * total
    running = 0.0
    for item, weight in options:
        running += weight
        if draw <= running:
            return item
    return options[-1][0]


def backward_masses(
    word: int,
    atoms: int,
    max_arity: int,
    by_value: list[list[list]],
    beta: float,
) -> list[float]:
    back = [0.0] * (atoms + 1)
    back[atoms] = 1.0
    for pos in range(atoms - 1, -1, -1):
        total = 0.0
        for arity in range(1, min(max_arity, atoms - pos) + 1):
            value = _h96.span_value(word, pos, arity, atoms)
            records = by_value[arity][value]
            edge_mass = sum(record.weight**beta for record in records)
            total += edge_mass * back[pos + arity]
        back[pos] = total
    return back


def sample_description(
    word: int,
    atoms: int,
    max_arity: int,
    by_value: list[list[list]],
    backward: list[float],
    beta: float,
    rng: random.Random,
) -> _h96.Description | None:
    if backward[0] <= 0.0:
        return None
    pos = 0
    cost = 0
    weight = 1.0
    bits = ""
    while pos < atoms:
        options: list[tuple[object, float]] = []
        for arity in range(1, min(max_arity, atoms - pos) + 1):
            value = _h96.span_value(word, pos, arity, atoms)
            for record in by_value[arity][value]:
                option_weight = (record.weight**beta) * backward[pos + arity]
                if option_weight > 0.0:
                    options.append((record, option_weight))
        if not options:
            return None
        record = weighted_choice(rng, options)
        cost += record.cost
        weight *= record.weight
        bits += record.bits
        pos += record.arity
    return _h96.Description(weight=weight, cost=cost, bits=bits)


def best_current_description(
    word: int,
    atoms: int,
    max_arity: int,
    by_value: list[list[list]],
) -> _h96.Description | None:
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, object] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for pos in range(atoms):
        if dp[pos] == float("inf"):
            continue
        for arity in range(1, min(max_arity, atoms - pos) + 1):
            value = _h96.span_value(word, pos, arity, atoms)
            for record in by_value[arity][value]:
                end = pos + arity
                candidate = dp[pos] + record.cost
                if candidate < dp[end]:
                    dp[end] = candidate
                    prev[end] = (pos, record)
    if dp[atoms] == float("inf"):
        return None
    records = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            return None
        prior, record = entry
        records.append(record)
        cursor = prior
    records.reverse()
    bits = "".join(record.bits for record in records)
    weight = math.prod(record.weight for record in records)
    return _h96.Description(weight=weight, cost=int(dp[atoms]), bits=bits)


def choose_words(atoms: int, trials: int, rng: random.Random) -> list[int]:
    domain = 1 << atoms
    if trials >= domain:
        return list(range(domain))
    return rng.sample(range(domain), trials)


def evaluate_config(config: Config) -> SummaryRow:
    rng = random.Random(config.seed)
    by_value, edge_weights, edge_maxes = _h96.build_record_family(
        block_bits=1,
        max_arity=config.max_arity,
        depth_bits=config.depth_bits,
        seed=config.seed,
    )

    @lru_cache(maxsize=None)
    def future_collective_saving(bits: str) -> float:
        total, _ = _h96.all_description_mass_for_bits(bits, config.max_arity, edge_weights, edge_maxes)
        if total <= 0.0:
            return float("-inf")
        return len(bits) + math.log2(total)

    rows: list[SampledWordRow] = []
    beta_schedule = (1.0, 0.75, 0.5)
    words = choose_words(config.atoms, config.word_trials, rng)
    for word in words:
        backward_by_beta = {
            beta: backward_masses(word, config.atoms, config.max_arity, by_value, beta)
            for beta in beta_schedule
        }
        z_current = backward_by_beta[1.0][0]
        if z_current <= 0.0:
            rows.append(
                SampledWordRow(
                    word=word,
                    reachable=False,
                    z_current=0.0,
                    collective_current_saving=float("-inf"),
                    best_current_saving=float("-inf"),
                    posterior_one_cycle=float("-inf"),
                    posterior_one_future=float("-inf"),
                    posterior_future_estimate=float("-inf"),
                    unique_candidates=0,
                    best_transfer_cycle=float("-inf"),
                    best_transfer_cycle_logm_net=float("-inf"),
                    best_transfer_current=float("-inf"),
                    best_transfer_future=float("-inf"),
                    random_same_length_future=float("-inf"),
                    random_same_length_best_future=float("-inf"),
                    best_transfer_len=0,
                )
            )
            continue

        candidates: dict[str, _h96.Description] = {}
        best_current = best_current_description(word, config.atoms, config.max_arity, by_value)
        if best_current is not None:
            candidates[best_current.bits] = best_current

        posterior_futures: list[float] = []
        posterior_one: _h96.Description | None = None
        per_beta = max(1, config.candidates_per_word // len(beta_schedule))
        for beta in beta_schedule:
            back = backward_by_beta[beta]
            for _ in range(per_beta):
                description = sample_description(
                    word,
                    config.atoms,
                    config.max_arity,
                    by_value,
                    back,
                    beta,
                    rng,
                )
                if description is None:
                    continue
                old = candidates.get(description.bits)
                if old is None or description.cost < old.cost:
                    candidates[description.bits] = description
                if beta == 1.0:
                    if posterior_one is None:
                        posterior_one = description
                    posterior_futures.append(future_collective_saving(description.bits))

        descriptions = list(candidates.values())
        chosen = max(
            descriptions,
            key=lambda description: (
                config.atoms - description.cost + future_collective_saving(description.bits),
                config.atoms - description.cost,
            ),
        )
        chosen_future = future_collective_saving(chosen.bits)
        chosen_current = config.atoms - chosen.cost
        random_bits = "".join("1" if rng.randrange(2) else "0" for _ in range(len(chosen.bits)))
        random_future = future_collective_saving(random_bits)
        random_best_future = max(
            future_collective_saving("".join("1" if rng.randrange(2) else "0" for _ in range(len(chosen.bits))))
            for _ in range(max(1, config.candidates_per_word))
        )
        selector_tax_logm = math.log2(max(1, len(descriptions)))
        posterior_one_future = future_collective_saving(posterior_one.bits) if posterior_one is not None else float("-inf")
        posterior_one_cycle = (
            config.atoms - posterior_one.cost + posterior_one_future
            if posterior_one is not None
            else float("-inf")
        )
        rows.append(
            SampledWordRow(
                word=word,
                reachable=True,
                z_current=z_current,
                collective_current_saving=config.atoms + math.log2(z_current),
                best_current_saving=config.atoms - best_current.cost if best_current is not None else float("-inf"),
                posterior_one_cycle=posterior_one_cycle,
                posterior_one_future=posterior_one_future,
                posterior_future_estimate=finite_mean(posterior_futures),
                unique_candidates=len(descriptions),
                best_transfer_cycle=chosen_current + chosen_future,
                best_transfer_cycle_logm_net=chosen_current + chosen_future - selector_tax_logm,
                best_transfer_current=chosen_current,
                best_transfer_future=chosen_future,
                random_same_length_future=random_future,
                random_same_length_best_future=random_best_future,
                best_transfer_len=len(chosen.bits),
            )
        )

    reachable = [row for row in rows if row.reachable]
    if not reachable:
        raise RuntimeError(f"no reachable words for {config}")
    return SummaryRow(
        name=config.name,
        atoms=config.atoms,
        max_arity=config.max_arity,
        depth_bits=config.depth_bits,
        word_trials=len(words),
        candidates_per_word=config.candidates_per_word,
        reachable_fraction=len(reachable) / len(rows),
        avg_unique_candidates=finite_mean([row.unique_candidates for row in reachable]),
        collective_current_saving=finite_mean([row.collective_current_saving for row in reachable]),
        best_current_saving=finite_mean([row.best_current_saving for row in reachable]),
        posterior_one_cycle=finite_mean([row.posterior_one_cycle for row in reachable]),
        posterior_one_future=finite_mean([row.posterior_one_future for row in reachable]),
        posterior_future_estimate=finite_mean([row.posterior_future_estimate for row in reachable]),
        best_transfer_cycle=finite_mean([row.best_transfer_cycle for row in reachable]),
        selector_tax_logm=finite_mean([math.log2(max(1, row.unique_candidates)) for row in reachable]),
        best_transfer_cycle_logm_net=finite_mean([row.best_transfer_cycle_logm_net for row in reachable]),
        transfer_current=finite_mean([row.best_transfer_current for row in reachable]),
        transfer_future=finite_mean([row.best_transfer_future for row in reachable]),
        transfer_len=finite_mean([row.best_transfer_len for row in reachable]),
        random_same_length_future=finite_mean([row.random_same_length_future for row in reachable]),
        random_same_length_best_future=finite_mean([row.random_same_length_best_future for row in reachable]),
        neutral_future_lift=finite_mean(
            [row.best_transfer_future - row.random_same_length_future for row in reachable]
        ),
        neutral_future_lift_vs_best_random=finite_mean(
            [row.best_transfer_future - row.random_same_length_best_future for row in reachable]
        ),
        future_lift_vs_posterior=finite_mean(
            [row.best_transfer_future - row.posterior_future_estimate for row in reachable]
        ),
        positive_cycle_fraction=sum(1 for row in reachable if row.best_transfer_cycle > 0.0) / len(reachable),
        positive_logm_net_fraction=sum(1 for row in reachable if row.best_transfer_cycle_logm_net > 0.0) / len(reachable),
        current_positive_fraction=sum(1 for row in reachable if row.best_current_saving > 0.0) / len(reachable),
    )


def default_configs() -> list[Config]:
    return [
        Config("h96_anchor_sampled", atoms=5, max_arity=3, depth_bits=3, word_trials=32, candidates_per_word=512, seed=96000),
        Config("small_deeper", atoms=6, max_arity=3, depth_bits=4, word_trials=64, candidates_per_word=384, seed=97002),
        Config("mid_v1", atoms=8, max_arity=4, depth_bits=5, word_trials=64, candidates_per_word=512, seed=97003),
        Config("v1_frontier_probe", atoms=10, max_arity=5, depth_bits=6, word_trials=64, candidates_per_word=512, seed=97004),
    ]


def print_rows(rows: list[SummaryRow]) -> None:
    print("== sampled neutral transfer sweep ==")
    print("Rows choose among visible paid genotypes; sampling approximates encoder search.")
    print(
        f"{'name':<18} {'N':>3} {'K':>3} {'D':>3} {'words':>5} {'cand':>5} "
        f"{'uniq':>7} {'len':>7} {'post1':>9} {'cycle':>10} {'logm net':>10} "
        f"{'future':>9} {'rand1':>9} {'randM':>9} {'liftM':>9} {'pos':>7}"
    )
    for row in rows:
        print(
            f"{row.name:<18} {row.atoms:3d} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.word_trials:5d} {row.candidates_per_word:5d} "
            f"{row.avg_unique_candidates:7.1f} {row.transfer_len:7.1f} "
            f"{row.posterior_one_cycle:9.3f} {row.best_transfer_cycle:10.3f} "
            f"{row.best_transfer_cycle_logm_net:10.3f} {row.transfer_future:9.3f} "
            f"{row.random_same_length_future:9.3f} {row.random_same_length_best_future:9.3f} "
            f"{row.neutral_future_lift_vs_best_random:9.3f} "
            f"{row.positive_cycle_fraction:7.3f}"
        )
    print()
    print("Detailed current-cost telemetry:")
    print(
        f"{'name':<18} {'coll now':>10} {'best now':>10} {'chosen now':>11} "
        f"{'logm tax':>9} {'post fut':>9} {'lift1':>9}"
    )
    for row in rows:
        print(
            f"{row.name:<18} {row.collective_current_saving:10.3f} "
            f"{row.best_current_saving:10.3f} {row.transfer_current:11.3f} "
            f"{row.selector_tax_logm:9.3f} {row.posterior_future_estimate:9.3f} "
            f"{row.neutral_future_lift:9.3f}"
        )
    print()


def print_reading(rows: list[SummaryRow]) -> None:
    best = max(rows, key=lambda row: row.best_transfer_cycle)
    print("== reading ==")
    print(
        "The sampled sweep is a search-process probe, not a proof: a bigger "
        "candidate set can only improve the encoder's found genotype. The "
        "accounting is still paid because the selected genotype bits are the "
        "output."
    )
    print(
        f"Best sampled row is {best.name} with average cycle "
        f"{best.best_transfer_cycle:.6f} bits/word and positive fraction "
        f"{best.positive_cycle_fraction:.6f}."
    )
    print(
        "If a future row turns positive, it must be rerun with larger candidate "
        "counts, exact or importance-sampled confidence intervals, and a "
        "uniform/random same-length control. A positive minority without "
        "positive uniform average is a source/fertility clue, not a roughly-all "
        "compression result."
    )


def main() -> None:
    rows = [evaluate_config(config) for config in default_configs()]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
