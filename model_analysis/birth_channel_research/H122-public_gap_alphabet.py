#!/usr/bin/env python3
"""H122 - public gap alphabets for an optimistic typed board.

H121 tested one public gap G at a time:

    W = T_pub - G

and missed. This kernel tests the next obvious middle ground: a small public
gap alphabet. The decoder reads a paid gap class, derives W from the public
target length, then reads exactly W payload bits:

    [arity][gap-class][W payload bits]

The kernel remains an optimistic typed-board lower bound: T_pub is set to the
actual interval bit length. A real codec must make that length public by board
geometry or charge it.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

H116_PATH = Path(__file__).with_name("H116-public_width_law_search.py")
H116_SPEC = importlib.util.spec_from_file_location("h116_public_width", H116_PATH)
if H116_SPEC is None or H116_SPEC.loader is None:
    raise RuntimeError(f"could not load {H116_PATH}")
h116 = importlib.util.module_from_spec(H116_SPEC)
sys.modules[H116_SPEC.name] = h116
H116_SPEC.loader.exec_module(h116)
h115 = h116.h115


@dataclass(frozen=True)
class EdgeChoice:
    edge: h116.RichEdge
    gap: int
    gap_bits: int

    @property
    def width(self) -> int:
        return self.edge.target_bits - self.gap

    @property
    def padding(self) -> int:
        return self.width - self.edge.payload_width

    @property
    def delta(self) -> int:
        return self.edge.arity_bits + self.gap_bits - self.gap


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    padding_bits: int
    supply_candidates: int
    local_candidates: int
    selected_gaps: tuple[int, ...]


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    alphabet: str
    gap_bits: int
    passes: int
    total_delta_bits: float
    delta_per_raw_atom: float
    delta_per_raw_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    supply_ratio: float
    supply_loss_bits: float
    gap_entropy_bits_per_selected: float
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    alphabet: str
    gap_bits: int
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    supply_ratio: float
    supply_loss_bits: float
    gap_entropy_bits_per_selected: float
    fail_rate: float


def parse_gap_set(text: str) -> tuple[int, ...]:
    gaps = tuple(sorted({int(part) for part in text.split(",") if part.strip()}))
    if not gaps or any(gap <= 0 for gap in gaps):
        raise ValueError(f"invalid gap set: {text}")
    return gaps


def sample_edges(config: h115.Config, items: list[h115.Item], slack: int, seed: int) -> list[list[h116.RichEdge]]:
    return h116.sample_rich_edges(config, items, slack, random.Random(seed))


def possible_choices(edge: h116.RichEdge, gaps: tuple[int, ...], gap_bits: int) -> list[EdgeChoice]:
    choices: list[EdgeChoice] = []
    for gap in gaps:
        width = edge.target_bits - gap
        if width >= 0 and edge.payload_width <= width:
            choices.append(EdgeChoice(edge=edge, gap=gap, gap_bits=gap_bits))
    return choices


def entropy_bits(values: tuple[int, ...]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return sum(count * math.log2(total / count) for count in counts.values())


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    gaps: tuple[int, ...],
) -> tuple[list[h115.Item] | None, StepStats]:
    edges_by_start = sample_edges(config, items, slack, seed)
    gap_bits = math.ceil(math.log2(len(gaps)))
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    local_candidates = sum(len(edges) for edges in edges_by_start)
    supply_candidates = sum(
        1
        for edges in edges_by_start
        for edge in edges
        if possible_choices(edge, gaps, gap_bits)
    )
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, EdgeChoice | None, list[h115.Item]] | None]] = [
        [None] * (total_raw + 1) for _ in range(n + 1)
    ]
    dp[0][0] = 0.0

    for pos in range(n):
        for raw_done in range(total_raw + 1):
            base = dp[pos][raw_done]
            if base == inf:
                continue

            skip_delta, outputs, _expired, _tax = h115.skip_outputs(config, items[pos], "force_refresh")
            if math.isfinite(skip_delta):
                candidate = base + skip_delta
                if candidate < dp[pos + 1][raw_done]:
                    dp[pos + 1][raw_done] = candidate
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs)

            for edge in edges_by_start[pos]:
                for choice in possible_choices(edge, gaps, gap_bits):
                    end = pos + edge.arity
                    new_raw = min(total_raw, raw_done + edge.raw_bits)
                    output = [
                        h115.Item(
                            bits=edge.arity_bits + gap_bits + choice.width,
                            raw_bits=edge.raw_bits,
                            record_age=0,
                        )
                    ]
                    candidate = base + choice.delta
                    if candidate < dp[end][new_raw]:
                        dp[end][new_raw] = candidate
                        prev[end][new_raw] = (pos, raw_done, "edge", choice, output)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(
            inf,
            input_bits,
            input_bits,
            0,
            0,
            due_seen,
            0,
            0,
            supply_candidates,
            local_candidates,
            (),
        )

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    padding_bits = 0
    selected_gaps: list[int] = []
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, choice, outputs = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            if choice is None:
                raise AssertionError("selected choice missing")
            due_covered += choice.edge.old_count
            padding_bits += choice.padding
            selected_gaps.append(choice.gap)
        pos = prior_pos
        raw = prior_raw

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    return next_items, StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        padding_bits=padding_bits,
        supply_candidates=supply_candidates,
        local_candidates=local_candidates,
        selected_gaps=tuple(selected_gaps),
    )


def simulate_trial(
    config: h115.Config,
    slack: int,
    gaps: tuple[int, ...],
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> TrialStats:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    total_delta = 0.0
    selected = 0
    due_seen = 0
    due_covered = 0
    padding = 0
    supply_candidates = 0
    local_candidates = 0
    selected_gaps: list[int] = []
    rewrite_fracs: list[float] = []
    gap_bits = math.ceil(math.log2(len(gaps)))

    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            gaps,
        )
        supply_candidates += stats.supply_candidates
        local_candidates += stats.local_candidates
        if next_items is None:
            ratio = supply_candidates / max(1, local_candidates)
            return TrialStats(
                config_name=config.name,
                alphabet=",".join(str(gap) for gap in gaps),
                gap_bits=gap_bits,
                passes=passes,
                total_delta_bits=float("inf"),
                delta_per_raw_atom=float("inf"),
                delta_per_raw_atom_pass=float("inf"),
                selected_records_per_atom_pass=selected / raw_atoms / max(1, step + 1),
                avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
                due_cover_rate=0.0 if due_seen == 0 else due_covered / due_seen,
                padding_bits_per_selected=padding / max(1, selected),
                supply_ratio=ratio,
                supply_loss_bits=-math.log2(ratio) if ratio > 0 else float("inf"),
                gap_entropy_bits_per_selected=entropy_bits(tuple(selected_gaps)) / max(1, selected),
                failed=True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        padding += stats.padding_bits
        selected_gaps.extend(stats.selected_gaps)
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    ratio = supply_candidates / max(1, local_candidates)
    return TrialStats(
        config_name=config.name,
        alphabet=",".join(str(gap) for gap in gaps),
        gap_bits=gap_bits,
        passes=passes,
        total_delta_bits=total_delta,
        delta_per_raw_atom=total_delta / raw_atoms,
        delta_per_raw_atom_pass=total_delta / raw_atoms / passes,
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        due_cover_rate=1.0 if due_seen == 0 else due_covered / due_seen,
        padding_bits_per_selected=padding / max(1, selected),
        supply_ratio=ratio,
        supply_loss_bits=-math.log2(ratio) if ratio > 0 else float("inf"),
        gap_entropy_bits_per_selected=entropy_bits(tuple(selected_gaps)) / max(1, selected),
        failed=False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    gaps: tuple[int, ...],
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    trial_rows = [
        simulate_trial(
            config,
            slack,
            gaps,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for trial in range(trials)
    ]
    finite = [trial for trial in trial_rows if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trial_rows)
    alphabet = ",".join(str(gap) for gap in gaps)
    gap_bits = math.ceil(math.log2(len(gaps)))
    if not finite:
        finite_supply = [trial.supply_loss_bits for trial in trial_rows if math.isfinite(trial.supply_loss_bits)]
        return Row(
            config_name=config.name,
            alphabet=alphabet,
            gap_bits=gap_bits,
            atoms=config.atoms,
            passes=passes,
            trials=trials,
            min_rewrite=min_rewrite_raw_fraction,
            delta_per_atom=float("inf"),
            delta_per_atom_pass=float("inf"),
            selected_records_per_atom_pass=0.0,
            avg_rewrite_fraction=0.0,
            due_cover_rate=0.0,
            padding_bits_per_selected=0.0,
            supply_ratio=mean(trial.supply_ratio for trial in trial_rows),
            supply_loss_bits=mean(finite_supply) if finite_supply else float("inf"),
            gap_entropy_bits_per_selected=0.0,
            fail_rate=fail_rate,
        )
    return Row(
        config_name=config.name,
        alphabet=alphabet,
        gap_bits=gap_bits,
        atoms=config.atoms,
        passes=passes,
        trials=trials,
        min_rewrite=min_rewrite_raw_fraction,
        delta_per_atom=mean(trial.delta_per_raw_atom for trial in finite),
        delta_per_atom_pass=mean(trial.delta_per_raw_atom_pass for trial in finite),
        selected_records_per_atom_pass=mean(trial.selected_records_per_atom_pass for trial in finite),
        avg_rewrite_fraction=mean(trial.avg_rewrite_fraction for trial in finite),
        due_cover_rate=mean(trial.due_cover_rate for trial in finite),
        padding_bits_per_selected=mean(trial.padding_bits_per_selected for trial in finite),
        supply_ratio=mean(trial.supply_ratio for trial in finite),
        supply_loss_bits=mean(trial.supply_loss_bits for trial in finite),
        gap_entropy_bits_per_selected=mean(trial.gap_entropy_bits_per_selected for trial in finite),
        fail_rate=fail_rate,
    )


@dataclass(frozen=True)
class Row:
    config_name: str
    alphabet: str
    gap_bits: int
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    supply_ratio: float
    supply_loss_bits: float
    gap_entropy_bits_per_selected: float
    fail_rate: float


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,gaps,gap_bits,atoms,passes,trials,min_rewrite,delta/atom,"
        "delta/atom/pass,sel/atom/pass,rewrite_frac,due_cover,padding/sel,"
        "supply_ratio,supply_loss,gap_entropy/sel,fail"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.alphabet},{row.gap_bits},{row.atoms},"
            f"{row.passes},{row.trials},{row.min_rewrite:.3f},"
            f"{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.supply_ratio)},"
            f"{format_float(row.supply_loss_bits)},"
            f"{format_float(row.gap_entropy_bits_per_selected)},"
            f"{format_float(row.fail_rate)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=122_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--gap-set", action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]
    gap_sets = [parse_gap_set(text) for text in args.gap_set] or [
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (4, 5, 6, 8),
        (4, 6, 8, 10),
        (5, 6, 8, 10, 12),
        (6, 8, 10, 12, 16),
    ]

    rows: list[Row] = []
    for config in configs:
        for gaps in gap_sets:
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    gaps=gaps,
                    passes=args.passes,
                    trials=args.trials,
                    seed=args.seed,
                    min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                )
            )
    print_rows(rows)


if __name__ == "__main__":
    main()
