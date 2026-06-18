#!/usr/bin/env python3
"""H121 - ideal public-gap typed board for forced due refresh.

H119 fixed absolute payload width and failed. Herschel's stronger geometry is a
typed public board where the decoder knows target length before reading the
payload, so width can be a fixed public gap:

    T_pub = sum public child item lengths
    W = T_pub - G
    record = [arity][W payload bits]

This attacks the H117 circularity directly. The kernel below is an optimistic
typed-board lower bound: it lets T_pub equal the actual interval bit length.
That is only legal if a real board/type invariant makes the same length public
to the decoder; otherwise H(T) must be charged and the row is invalid.

The price tested here is match supply. A candidate is usable only if its sampled
payload width is <= T_pub - G. If selected, its delta is arity_bits - G.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
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


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    gap: int
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
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    gap: int
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
    fail_rate: float


def sample_edges(config: h115.Config, items: list[h115.Item], slack: int, seed: int) -> list[list[h116.RichEdge]]:
    return h116.sample_rich_edges(config, items, slack, random.Random(seed))


def is_gap_candidate(edge: h116.RichEdge, gap: int) -> bool:
    width = edge.target_bits - gap
    return width >= edge.payload_width and width >= 0


def gap_delta(edge: h116.RichEdge, gap: int) -> int:
    return edge.arity_bits - gap


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    gap: int,
) -> tuple[list[h115.Item] | None, StepStats]:
    edges_by_start = sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    local_candidates = sum(len(edges) for edges in edges_by_start)
    supply_candidates = sum(1 for edges in edges_by_start for edge in edges if is_gap_candidate(edge, gap))
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, h116.RichEdge | None, list[h115.Item], int] | None]] = [
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
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs, 0)

            for edge in edges_by_start[pos]:
                if not is_gap_candidate(edge, gap):
                    continue
                delta = gap_delta(edge, gap)
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                width = edge.target_bits - gap
                padding = width - edge.payload_width
                output = [
                    h115.Item(
                        bits=edge.arity_bits + width,
                        raw_bits=edge.raw_bits,
                        record_age=0,
                    )
                ]
                candidate = base + delta
                if candidate < dp[end][new_raw]:
                    dp[end][new_raw] = candidate
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output, padding)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(inf, input_bits, input_bits, 0, 0, due_seen, 0, 0, supply_candidates, local_candidates)

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    padding_bits = 0
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, edge, outputs, padding = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            padding_bits += padding
            if edge is None:
                raise AssertionError("selected edge missing")
            due_covered += edge.old_count
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
    )


def simulate_trial(
    config: h115.Config,
    slack: int,
    gap: int,
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
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            gap,
        )
        supply_candidates += stats.supply_candidates
        local_candidates += stats.local_candidates
        if next_items is None:
            ratio = supply_candidates / max(1, local_candidates)
            return TrialStats(
                config_name=config.name,
                gap=gap,
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
                failed=True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        padding += stats.padding_bits
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    ratio = supply_candidates / max(1, local_candidates)
    return TrialStats(
        config_name=config.name,
        gap=gap,
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
        failed=False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    gap: int,
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    trial_rows = [
        simulate_trial(
            config,
            slack,
            gap,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for trial in range(trials)
    ]
    finite = [trial for trial in trial_rows if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trial_rows)
    if not finite:
        return Row(
            config_name=config.name,
            gap=gap,
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
            supply_loss_bits=mean(trial.supply_loss_bits for trial in trial_rows if math.isfinite(trial.supply_loss_bits)),
            fail_rate=fail_rate,
        )
    return Row(
        config_name=config.name,
        gap=gap,
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
        fail_rate=fail_rate,
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,gap,atoms,passes,trials,min_rewrite,delta/atom,"
        "delta/atom/pass,sel/atom/pass,rewrite_frac,due_cover,"
        "padding/sel,supply_ratio,supply_loss,fail"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.gap},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.supply_ratio)},"
            f"{format_float(row.supply_loss_bits)},"
            f"{format_float(row.fail_rate)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=121_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--gap", type=int, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]
    gaps = args.gap or [1, 2, 3, 4, 5, 6, 8, 10, 12, 16]

    rows: list[Row] = []
    for config in configs:
        for gap in gaps:
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    gap=gap,
                    passes=args.passes,
                    trials=args.trials,
                    seed=args.seed,
                    min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                )
            )
    print_rows(rows)


if __name__ == "__main__":
    main()
