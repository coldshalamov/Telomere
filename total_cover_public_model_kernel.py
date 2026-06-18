#!/usr/bin/env python3
"""Public-model Total-Cover witness kernel.

This tests the most plausible non-file-specific escape hatch after the
finite-count sanity check: make the witness-symbol stream arithmetic-coded by a
public distribution learned from the uniform-hash Total-Cover process itself.
Supported symbol models include iid `(arity,width)`, coarse decoder-derived
contexts, and a factored arity-then-width-delta stream.

No per-file symbol counts or model parameters are charged here. That is honest
only for a model frozen into the codec/spec for a fixed `(B,K,D,objective)`.
If the model is transmitted per file, use the paid-count modes in
`total_cover_lotus_crossover.py` instead.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import (  # noqa: E402
    EdgeSample,
    SelectedRecord,
    generate_samples,
)


Symbol = tuple[int, int]
Context = tuple[int, ...]
FIRST_PREVIOUS = (-1, -1)


@dataclass(frozen=True)
class PublicModel:
    costs: dict[Symbol, float]
    default_cost: float
    total_observations: int
    alphabet_size: int


@dataclass(frozen=True)
class PublicMarkovModel:
    start_costs: dict[Symbol, float]
    start_default_cost: float
    transition_costs: dict[Symbol, dict[Symbol, float]]
    transition_default_costs: dict[Symbol, float]
    unseen_previous_cost: float
    total_observations: int
    alphabet_size: int


@dataclass(frozen=True)
class PublicContextModel:
    costs: dict[Context, dict[Symbol, float]]
    default_costs: dict[Context, float]
    global_default_cost: float
    total_observations: int
    alphabet_size: int


@dataclass(frozen=True)
class PublicFactoredModel:
    arity_counts: dict[Context, Counter[int]]
    delta_counts: dict[Context, Counter[int]]
    total_observations: int
    max_arity: int
    frontier: int
    alpha: float


@dataclass(frozen=True)
class Cover:
    covered: bool
    charged_bits: float
    records: tuple[SelectedRecord, ...]


@dataclass(frozen=True)
class ResultRow:
    block_bits: int
    max_arity: int
    frontier: int
    cover_rate: float
    gain_per_atom: float
    gain_per_byte: float
    records_per_atom: float
    avg_arity: float
    avg_payload_width: float
    avg_rank_bits: float
    stream_bits_per_record: float
    total_bits_per_record: float
    missing_bits_per_record: float


def uniform_model(max_arity: int, frontier: int) -> PublicModel:
    alphabet_size = max_arity * frontier
    return PublicModel({}, math.log2(alphabet_size), 0, alphabet_size)


def arity_bucket(arity: int) -> int:
    if arity <= 0:
        return -1
    return min(7, int(math.log2(arity)))


def delta_bucket(delta: int) -> int:
    if delta <= -17:
        return -4
    if delta <= -9:
        return -3
    if delta <= -5:
        return -2
    if delta <= -1:
        return -1
    if delta <= 3:
        return 0
    if delta <= 7:
        return 1
    if delta <= 15:
        return 2
    return 3


def previous_bucket(symbol: Symbol, block_bits: int) -> tuple[int, int]:
    arity, width = symbol
    if arity <= 0:
        return FIRST_PREVIOUS
    return (arity_bucket(arity), delta_bucket(arity * block_bits - width))


def progress_bucket(pos: int, atoms: int, buckets: int) -> int:
    if atoms <= 0:
        return 0
    return min(buckets - 1, (pos * buckets) // atoms)


def remaining_bucket(remaining: int, max_arity: int) -> int:
    if remaining <= max_arity:
        return remaining
    ratio = (remaining + max_arity - 1) // max_arity
    return max_arity + min(16, int(math.log2(ratio)) + 1)


def context_for(
    pos: int,
    atoms: int,
    prev_bucket: tuple[int, int],
    scheme: str,
    max_arity: int | None = None,
) -> Context:
    remaining = atoms - pos
    if scheme == "remaining":
        if max_arity is None:
            raise ValueError("max_arity required for remaining context")
        return (remaining_bucket(remaining, max_arity),)
    if scheme == "remaining_prev_coarse":
        if max_arity is None:
            raise ValueError("max_arity required for remaining context")
        return (remaining_bucket(remaining, max_arity), *prev_bucket)
    if scheme == "progress4":
        return (progress_bucket(pos, atoms, 4),)
    if scheme == "progress8":
        return (progress_bucket(pos, atoms, 8),)
    if scheme == "prev_coarse":
        return prev_bucket
    if scheme == "progress4_prev_coarse":
        return (progress_bucket(pos, atoms, 4), *prev_bucket)
    if scheme == "progress8_prev_coarse":
        return (progress_bucket(pos, atoms, 8), *prev_bucket)
    raise ValueError(scheme)


def context_uses_previous(scheme: str) -> bool:
    return "prev" in scheme


def fit_iid_model(covers: list[Cover], max_arity: int, frontier: int, alpha: float) -> PublicModel:
    counts: Counter[Symbol] = Counter()
    for cover in covers:
        if not cover.covered:
            continue
        counts.update((record.arity, record.lotus_payload_width) for record in cover.records)
    total = sum(counts.values())
    alphabet_size = max_arity * frontier
    denom = total + alpha * alphabet_size
    default_cost = -math.log2(alpha / denom)
    costs = {symbol: -math.log2((count + alpha) / denom) for symbol, count in counts.items()}
    return PublicModel(costs, default_cost, total, alphabet_size)


def fit_markov_model(covers: list[Cover], max_arity: int, frontier: int, alpha: float) -> PublicMarkovModel:
    start_counts: Counter[Symbol] = Counter()
    transitions: dict[Symbol, Counter[Symbol]] = {}
    sequence_count = 0
    transition_total = 0
    for cover in covers:
        if not cover.covered or not cover.records:
            continue
        symbols = [(record.arity, record.lotus_payload_width) for record in cover.records]
        start_counts[symbols[0]] += 1
        sequence_count += 1
        for prev, curr in zip(symbols, symbols[1:]):
            transitions.setdefault(prev, Counter())[curr] += 1
            transition_total += 1

    alphabet_size = max_arity * frontier
    start_denom = sequence_count + alpha * alphabet_size
    start_default = -math.log2(alpha / start_denom)
    start_costs = {
        symbol: -math.log2((count + alpha) / start_denom)
        for symbol, count in start_counts.items()
    }
    transition_costs: dict[Symbol, dict[Symbol, float]] = {}
    transition_defaults: dict[Symbol, float] = {}
    for prev, counts in transitions.items():
        total = sum(counts.values())
        denom = total + alpha * alphabet_size
        transition_defaults[prev] = -math.log2(alpha / denom)
        transition_costs[prev] = {
            curr: -math.log2((count + alpha) / denom)
            for curr, count in counts.items()
        }
    return PublicMarkovModel(
        start_costs=start_costs,
        start_default_cost=start_default,
        transition_costs=transition_costs,
        transition_default_costs=transition_defaults,
        unseen_previous_cost=math.log2(alphabet_size),
        total_observations=sequence_count + transition_total,
        alphabet_size=alphabet_size,
    )


def fit_context_model(
    covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    alpha: float,
    scheme: str,
) -> PublicContextModel:
    by_context: dict[Context, Counter[Symbol]] = {}
    observations = 0
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        pos = 0
        prev = FIRST_PREVIOUS
        for record in cover.records:
            context = context_for(pos, atoms, prev, scheme)
            symbol = (record.arity, record.lotus_payload_width)
            by_context.setdefault(context, Counter())[symbol] += 1
            observations += 1
            pos += record.arity
            prev = previous_bucket(symbol, block_bits)

    alphabet_size = max_arity * frontier
    global_default = math.log2(alphabet_size)
    costs: dict[Context, dict[Symbol, float]] = {}
    defaults: dict[Context, float] = {}
    for context, counts in by_context.items():
        total = sum(counts.values())
        denom = total + alpha * alphabet_size
        defaults[context] = -math.log2(alpha / denom)
        costs[context] = {
            symbol: -math.log2((count + alpha) / denom)
            for symbol, count in counts.items()
        }
    return PublicContextModel(costs, defaults, global_default, observations, alphabet_size)


def fit_factored_model(
    covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    alpha: float,
    scheme: str,
) -> PublicFactoredModel:
    arity_counts: dict[Context, Counter[int]] = {}
    delta_counts: dict[Context, Counter[int]] = {}
    observations = 0
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        pos = 0
        prev = FIRST_PREVIOUS
        for record in cover.records:
            context = context_for(pos, atoms, prev, scheme, max_arity)
            arity_counts.setdefault(context, Counter())[record.arity] += 1
            delta_context = (*context, arity_bucket(record.arity))
            delta = record.arity * block_bits - record.lotus_payload_width
            delta_counts.setdefault(delta_context, Counter())[delta] += 1
            observations += 1
            pos += record.arity
            prev = previous_bucket((record.arity, record.lotus_payload_width), block_bits)
    return PublicFactoredModel(arity_counts, delta_counts, observations, max_arity, frontier, alpha)


def code_cost(model: PublicModel, symbol: Symbol) -> float:
    return model.costs.get(symbol, model.default_cost)


def uniform_markov_model(max_arity: int, frontier: int) -> PublicMarkovModel:
    alphabet_size = max_arity * frontier
    uniform_cost = math.log2(alphabet_size)
    return PublicMarkovModel({}, uniform_cost, {}, {}, uniform_cost, 0, alphabet_size)


def markov_code_cost(model: PublicMarkovModel, previous: Symbol | None, symbol: Symbol) -> float:
    if previous is None:
        return model.start_costs.get(symbol, model.start_default_cost)
    if previous not in model.transition_costs:
        return model.unseen_previous_cost
    return model.transition_costs[previous].get(symbol, model.transition_default_costs[previous])


def context_code_cost(model: PublicContextModel, context: Context, symbol: Symbol) -> float:
    if context not in model.costs:
        return model.global_default_cost
    return model.costs[context].get(symbol, model.default_costs[context])


def factored_arity_cost(model: PublicFactoredModel, context: Context, arity: int, remaining: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.arity_counts.get(context, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def factored_delta_cost(
    model: PublicFactoredModel,
    context: Context,
    block_bits: int,
    arity: int,
    width: int,
) -> float:
    delta_context = (*context, arity_bucket(arity))
    counts = model.delta_counts.get(delta_context, Counter())
    delta = arity * block_bits - width
    lo = arity * block_bits - model.frontier
    hi = arity * block_bits - 1
    denom_count = sum(count for value, count in counts.items() if lo <= value <= hi)
    denom = denom_count + model.alpha * model.frontier
    return -math.log2((counts.get(delta, 0) + model.alpha) / denom)


def factored_code_cost(
    model: PublicFactoredModel,
    context: Context,
    remaining: int,
    block_bits: int,
    arity: int,
    width: int,
) -> float:
    return factored_arity_cost(model, context, arity, remaining) + factored_delta_cost(
        model,
        context,
        block_bits,
        arity,
        width,
    )


def payload_width_count_le(width: int) -> int:
    if width < 1:
        return 0
    return (1 << (width + 1)) - 3


def truncated_geometric_rank_bits_for(rank: int, target_bits: int, width: int) -> float:
    lo = payload_width_count_le(width - 1) + 1
    hi = payload_width_count_le(width)
    rank = min(max(rank, lo), hi)
    q = 2.0 ** (-target_bits)
    if q == 0.0:
        return float(width)
    ln1m = math.log1p(-q)
    log_a = (lo - 1) * ln1m
    log_b = hi * ln1m
    delta = log_b - log_a
    if delta < -745.0:
        log_z = log_a
    else:
        log_z = log_a + math.log(-math.expm1(delta))
    log2_z = log_z / math.log(2.0)
    rank_bits = target_bits - (rank - 1) * (ln1m / math.log(2.0)) + log2_z
    return max(0.0, rank_bits)


def truncated_geometric_rank_bits(edge: EdgeSample) -> float:
    """Code exact first-hit rank after its Lotus payload-width bucket is known."""

    return truncated_geometric_rank_bits_for(edge.rank, edge.target_bits, edge.lotus_payload_width)


def rank_bits(edge: EdgeSample, rank_code: str) -> float:
    if rank_code == "fixed":
        return float(edge.lotus_payload_width)
    if rank_code == "truncated-geometric":
        return truncated_geometric_rank_bits(edge)
    raise ValueError(rank_code)


def selected_rank_bits(record: SelectedRecord, rank_code: str) -> float:
    if rank_code == "fixed":
        return float(record.lotus_payload_width)
    if rank_code == "truncated-geometric":
        return truncated_geometric_rank_bits_for(record.rank, record.target_bits, record.lotus_payload_width)
    raise ValueError(rank_code)


def cover_with_iid_model(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
    model: PublicModel,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset, edge in enumerate(trial[index], start=1):
            if offset > max_arity or edge.lotus_payload_width > frontier:
                continue
            symbol = (offset, edge.lotus_payload_width)
            candidate = base + rank_bits(edge, rank_code) + code_cost(model, symbol)
            end = index + offset
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, offset, edge)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())

    cursor = atoms
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge = entry
        symbol = (arity, edge.lotus_payload_width)
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=rank_bits(edge, rank_code) + code_cost(model, symbol),
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms] + flush_bits, tuple(records))


def cover_with_markov_model(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
    model: PublicMarkovModel,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    start: Symbol | None = None
    dp: dict[int, dict[Symbol | None, float]] = {0: {start: 0.0}}
    back: dict[int, dict[Symbol | None, tuple[int, Symbol | None, int, EdgeSample] | None]] = {
        0: {start: None}
    }
    for index in range(atoms):
        if index not in dp:
            continue
        for previous, base in list(dp[index].items()):
            for offset, edge in enumerate(trial[index], start=1):
                if offset > max_arity or edge.lotus_payload_width > frontier:
                    continue
                symbol = (offset, edge.lotus_payload_width)
                candidate = base + rank_bits(edge, rank_code) + markov_code_cost(model, previous, symbol)
                end = index + offset
                if end not in dp:
                    dp[end] = {}
                    back[end] = {}
                if candidate < dp[end].get(symbol, float("inf")):
                    dp[end][symbol] = candidate
                    back[end][symbol] = (index, previous, offset, edge)
    if atoms not in dp:
        return Cover(False, float("inf"), ())

    final_symbol = min(dp[atoms], key=lambda symbol: dp[atoms][symbol])
    cursor = atoms
    symbol: Symbol | None = final_symbol
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = back[cursor][symbol]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, previous, arity, edge = entry
        current = (arity, edge.lotus_payload_width)
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=rank_bits(edge, rank_code) + markov_code_cost(model, previous, current),
            )
        )
        cursor = prior
        symbol = previous
    records.reverse()
    return Cover(True, dp[atoms][final_symbol] + flush_bits, tuple(records))


def cover_with_context_model(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: PublicContextModel,
    flush_bits: float,
    rank_code: str,
    scheme: str,
) -> Cover:
    atoms = len(trial)
    use_prev = context_uses_previous(scheme)
    start_state = FIRST_PREVIOUS if use_prev else (0, 0)
    dp: dict[int, dict[tuple[int, int], float]] = {0: {start_state: 0.0}}
    back: dict[int, dict[tuple[int, int], tuple[int, tuple[int, int], int, EdgeSample] | None]] = {
        0: {start_state: None}
    }
    for index in range(atoms):
        if index not in dp:
            continue
        for prev, base in list(dp[index].items()):
            context = context_for(index, atoms, prev if use_prev else FIRST_PREVIOUS, scheme)
            for offset, edge in enumerate(trial[index], start=1):
                if offset > max_arity or edge.lotus_payload_width > frontier:
                    continue
                symbol = (offset, edge.lotus_payload_width)
                candidate = base + rank_bits(edge, rank_code) + context_code_cost(model, context, symbol)
                end = index + offset
                next_state = previous_bucket(symbol, block_bits) if use_prev else start_state
                if end not in dp:
                    dp[end] = {}
                    back[end] = {}
                if candidate < dp[end].get(next_state, float("inf")):
                    dp[end][next_state] = candidate
                    back[end][next_state] = (index, prev, offset, edge)
    if atoms not in dp:
        return Cover(False, float("inf"), ())

    final_state = min(dp[atoms], key=lambda state: dp[atoms][state])
    cursor = atoms
    state = final_state
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = back[cursor][state]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, prev, arity, edge = entry
        symbol = (arity, edge.lotus_payload_width)
        context = context_for(prior, atoms, prev if use_prev else FIRST_PREVIOUS, scheme)
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=rank_bits(edge, rank_code) + context_code_cost(model, context, symbol),
            )
        )
        cursor = prior
        state = prev
    records.reverse()
    return Cover(True, dp[atoms][final_state] + flush_bits, tuple(records))


def cover_with_factored_model(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: PublicFactoredModel,
    flush_bits: float,
    rank_code: str,
    scheme: str,
) -> Cover:
    atoms = len(trial)
    use_prev = context_uses_previous(scheme)
    start_state = FIRST_PREVIOUS if use_prev else (0, 0)
    dp: dict[int, dict[tuple[int, int], float]] = {0: {start_state: 0.0}}
    back: dict[int, dict[tuple[int, int], tuple[int, tuple[int, int], int, EdgeSample] | None]] = {
        0: {start_state: None}
    }
    for index in range(atoms):
        if index not in dp:
            continue
        remaining = atoms - index
        for prev, base in list(dp[index].items()):
            context = context_for(index, atoms, prev if use_prev else FIRST_PREVIOUS, scheme, max_arity)
            for offset, edge in enumerate(trial[index], start=1):
                if offset > max_arity or edge.lotus_payload_width > frontier:
                    continue
                code = factored_code_cost(
                    model,
                    context,
                    remaining,
                    block_bits,
                    offset,
                    edge.lotus_payload_width,
                )
                candidate = base + rank_bits(edge, rank_code) + code
                end = index + offset
                next_state = previous_bucket((offset, edge.lotus_payload_width), block_bits) if use_prev else start_state
                if end not in dp:
                    dp[end] = {}
                    back[end] = {}
                if candidate < dp[end].get(next_state, float("inf")):
                    dp[end][next_state] = candidate
                    back[end][next_state] = (index, prev, offset, edge)
    if atoms not in dp:
        return Cover(False, float("inf"), ())

    final_state = min(dp[atoms], key=lambda state: dp[atoms][state])
    cursor = atoms
    state = final_state
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = back[cursor][state]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, prev, arity, edge = entry
        remaining = atoms - prior
        context = context_for(prior, atoms, prev if use_prev else FIRST_PREVIOUS, scheme, max_arity)
        code = factored_code_cost(
            model,
            context,
            remaining,
            block_bits,
            arity,
            edge.lotus_payload_width,
        )
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=rank_bits(edge, rank_code) + code,
            )
        )
        cursor = prior
        state = prev
    records.reverse()
    return Cover(True, dp[atoms][final_state] + flush_bits, tuple(records))


def train_public_iid(
    train_samples: list[list[list[EdgeSample]]],
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> PublicModel:
    model = uniform_model(max_arity, frontier)
    for _ in range(iterations):
        covers = [
            cover_with_iid_model(trial, max_arity, frontier, model, flush_bits, rank_code)
            for trial in train_samples
        ]
        model = fit_iid_model(covers, max_arity, frontier, alpha)
    return model


def train_public_markov(
    train_samples: list[list[list[EdgeSample]]],
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> PublicMarkovModel:
    model = uniform_markov_model(max_arity, frontier)
    for _ in range(iterations):
        covers = [
            cover_with_markov_model(trial, max_arity, frontier, model, flush_bits, rank_code)
            for trial in train_samples
        ]
        model = fit_markov_model(covers, max_arity, frontier, alpha)
    return model


def train_public_context(
    train_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
    scheme: str,
) -> PublicContextModel:
    # Start with a globally uniform conditional model for every context.
    alphabet_size = max_arity * frontier
    model = PublicContextModel({}, {}, math.log2(alphabet_size), 0, alphabet_size)
    for _ in range(iterations):
        covers = [
            cover_with_context_model(
                trial,
                block_bits,
                max_arity,
                frontier,
                model,
                flush_bits,
                rank_code,
                scheme,
            )
            for trial in train_samples
        ]
        model = fit_context_model(covers, block_bits, max_arity, frontier, alpha, scheme)
    return model


def train_public_factored(
    train_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
    scheme: str,
) -> PublicFactoredModel:
    model = PublicFactoredModel({}, {}, 0, max_arity, frontier, alpha)
    for _ in range(iterations):
        covers = [
            cover_with_factored_model(
                trial,
                block_bits,
                max_arity,
                frontier,
                model,
                flush_bits,
                rank_code,
                scheme,
            )
            for trial in train_samples
        ]
        model = fit_factored_model(covers, block_bits, max_arity, frontier, alpha, scheme)
    return model


def summarize(
    covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rank_code: str,
) -> ResultRow:
    covered = [cover for cover in covers if cover.covered]
    cover_rate = len(covered) / len(covers) if covers else 0.0
    atoms = sum(record.arity for record in covered[0].records) if covered else 0
    raw_bits = atoms * block_bits
    gain_per_atom = mean((raw_bits - cover.charged_bits) / atoms for cover in covered) if covered else float("-inf")
    record_counts = [len(cover.records) for cover in covered]
    records_per_atom = mean(count / atoms for count in record_counts) if covered else 0.0
    all_records = [record for cover in covered for record in cover.records]
    avg_arity = mean(record.arity for record in all_records) if all_records else 0.0
    avg_payload = mean(record.lotus_payload_width for record in all_records) if all_records else 0.0
    avg_rank = mean(selected_rank_bits(record, rank_code) for record in all_records) if all_records else 0.0
    total_bits_per_record = mean(cover.charged_bits / len(cover.records) for cover in covered) if covered else float("inf")
    stream_bits_per_record = total_bits_per_record - avg_rank if covered else float("inf")
    missing = max(0.0, -gain_per_atom / records_per_atom) if records_per_atom else float("inf")
    return ResultRow(
        block_bits=block_bits,
        max_arity=max_arity,
        frontier=frontier,
        cover_rate=cover_rate,
        gain_per_atom=gain_per_atom,
        gain_per_byte=gain_per_atom * (8.0 / block_bits) if gain_per_atom != float("-inf") else float("-inf"),
        records_per_atom=records_per_atom,
        avg_arity=avg_arity,
        avg_payload_width=avg_payload,
        avg_rank_bits=avg_rank,
        stream_bits_per_record=stream_bits_per_record,
        total_bits_per_record=total_bits_per_record,
        missing_bits_per_record=missing,
    )


def evaluate_frontier(args: argparse.Namespace, frontier: int) -> tuple[ResultRow, PublicModel | PublicMarkovModel]:
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.seed + args.block_bits * 1009 + args.max_arity * 9173 + frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.eval_trials,
        args.seed + args.block_bits * 8081 + args.max_arity * 3571 + frontier * 43,
    )
    if args.model == "iid":
        model = train_public_iid(
            train_samples,
            args.max_arity,
            frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        covers = [
            cover_with_iid_model(trial, args.max_arity, frontier, model, args.flush_bits, args.rank_code)
            for trial in eval_samples
        ]
    elif args.model == "markov1":
        model = train_public_markov(
            train_samples,
            args.max_arity,
            frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        covers = [
            cover_with_markov_model(trial, args.max_arity, frontier, model, args.flush_bits, args.rank_code)
            for trial in eval_samples
        ]
    elif args.model == "context":
        model = train_public_context(
            train_samples,
            args.block_bits,
            args.max_arity,
            frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
            args.context,
        )
        covers = [
            cover_with_context_model(
                trial,
                args.block_bits,
                args.max_arity,
                frontier,
                model,
                args.flush_bits,
                args.rank_code,
                args.context,
            )
            for trial in eval_samples
        ]
    elif args.model == "factored":
        model = train_public_factored(
            train_samples,
            args.block_bits,
            args.max_arity,
            frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
            args.context,
        )
        covers = [
            cover_with_factored_model(
                trial,
                args.block_bits,
                args.max_arity,
                frontier,
                model,
                args.flush_bits,
                args.rank_code,
                args.context,
            )
            for trial in eval_samples
        ]
    else:
        raise ValueError(args.model)
    return summarize(covers, args.block_bits, args.max_arity, frontier, args.rank_code), model


def render_table(rows: list[ResultRow]) -> str:
    lines = [
        "| B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | avg rank bits | stream bits/rec | total bits/rec | missing bits/rec |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.block_bits} | {row.max_arity} | {row.frontier} | {row.cover_rate:.3f} | "
            f"{row.gain_per_atom:.4f} | {row.gain_per_byte:.4f} | {row.records_per_atom:.4f} | "
            f"{row.avg_arity:.2f} | {row.avg_payload_width:.2f} | {row.avg_rank_bits:.2f} | {row.stream_bits_per_record:.2f} | "
            f"{row.total_bits_per_record:.2f} | {row.missing_bits_per_record:.3f} |"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, required=True)
    parser.add_argument("--max-arity", type=int, required=True)
    parser.add_argument("--frontiers", type=int, nargs="+", required=True)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--train-trials", type=int, default=64)
    parser.add_argument("--eval-trials", type=int, default=64)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--flush-bits", type=float, default=2.0)
    parser.add_argument("--model", choices=("iid", "markov1", "context", "factored"), default="iid")
    parser.add_argument(
        "--context",
        choices=(
            "remaining",
            "remaining_prev_coarse",
            "progress4",
            "progress8",
            "prev_coarse",
            "progress4_prev_coarse",
            "progress8_prev_coarse",
        ),
        default="remaining",
    )
    parser.add_argument("--rank-code", choices=("fixed", "truncated-geometric"), default="fixed")
    parser.add_argument("--seed", type=int, default=20260617)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[ResultRow] = []
    models: dict[int, dict[str, float | int]] = {}
    for frontier in args.frontiers:
        row, model = evaluate_frontier(args, frontier)
        rows.append(row)
        if isinstance(model, PublicModel):
            default_cost = model.default_cost
        elif isinstance(model, PublicMarkovModel):
            default_cost = model.start_default_cost
        elif isinstance(model, PublicContextModel):
            default_cost = model.global_default_cost
        else:
            default_cost = math.log2(model.max_arity) + math.log2(model.frontier)
        models[frontier] = {
            "observations": model.total_observations,
            "alphabet_size": (
                model.alphabet_size
                if not isinstance(model, PublicFactoredModel)
                else model.max_arity * model.frontier
            ),
            "default_cost": default_cost,
            "stored_per_file": 0,
        }
    rows.sort(key=lambda row: row.gain_per_atom, reverse=True)
    print("# Public-Model Total-Cover Witness Kernel")
    print()
    print(f"Model: `{args.model}`")
    if args.model in {"context", "factored"}:
        print(f"Context: `{args.context}`")
    print(f"Rank code: `{args.rank_code}`")
    print()
    print("No per-file symbol counts are charged; this is only honest for a public, frozen model.")
    print()
    print(render_table(rows))
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {
                    "config": vars(args) | {"json_out": str(args.json_out) if args.json_out else None},
                    "rows": [row.__dict__ for row in rows],
                    "models": models,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
