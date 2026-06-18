#!/usr/bin/env python3
"""H129 - fixed zones with counted raw prefixes.

H124's markerless raw fallback hid a raw/record type bitmap. H125 fixed public
lanes were parseable but too rigid; H126 paid raw segment lists were too
expensive. This kernel tests Avicenna's counted stable-partition idea in a
parseable form:

    each fixed output zone = [raw atom prefix][record suffix]

The decoder knows the zone size from the public profile/header and reads one
raw-count per zone. Within a zone, raw atoms are fixed B-bit atoms and records
are parsed by their arity + witness. There is no per-item type bitmap.

This is still a lower-bound geometry: total output item count and typed-board
target length are treated optimistically. The measured question is whether a
small count ledger can approximate H124's adaptive type stream tightly enough.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

H125_PATH = Path(__file__).with_name("H125-public_raw_lane_repair.py")
H125_SPEC = importlib.util.spec_from_file_location("h125_public_raw_lane", H125_PATH)
if H125_SPEC is None or H125_SPEC.loader is None:
    raise RuntimeError(f"could not load {H125_PATH}")
h125 = importlib.util.module_from_spec(H125_SPEC)
sys.modules[H125_SPEC.name] = h125
H125_SPEC.loader.exec_module(h125)
h123 = h125.h123
h116 = h125.h116
h115 = h125.h115


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    count_bits: float
    input_bits: int
    output_bits: int
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    expired_records: int
    expiry_tax_bits: int
    padding_bits: int
    output_items: int
    raw_items: int


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    quantile: float
    zone_size: int
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    count_bits_per_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    output_items_per_atom_pass: float
    raw_items_per_atom_pass: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def count_ledger_bits(output_items: int, zone_size: int) -> float:
    full, partial = divmod(output_items, zone_size)
    bits = full * math.log2(zone_size + 1)
    if partial:
        bits += math.log2(partial + 1)
    return bits


def transition_outputs(
    config: h115.Config,
    outputs: list[h115.Item],
    zone_size: int,
    out_mod: int,
    in_record_suffix: int,
) -> tuple[int, int] | None:
    mod = out_mod
    suffix = in_record_suffix
    for item in outputs:
        is_raw = h125.is_markerless_raw_atom(config, item)
        if is_raw:
            if suffix:
                return None
        else:
            suffix = 1
        mod += 1
        if mod == zone_size:
            mod = 0
            suffix = 0
    return mod, suffix


def gap_for(table: h125.GapTable, edge: h116.RichEdge) -> int:
    return table.gaps.get(h123.context_for(table.context, edge), table.fallback_gap)


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    table: h125.GapTable | None,
    zone_size: int,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats, list[h116.RichEdge]]:
    edges_by_start = h123.sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    dp: list[dict[tuple[int, int, int], float]] = [dict() for _ in range(n + 1)]
    prev: dict[
        tuple[int, int, int, int],
        tuple[int, int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ] = {}
    dp[0][(0, 0, 0)] = 0.0

    def update(
        end: int,
        raw_done: int,
        out_mod: int,
        suffix: int,
        candidate: float,
        prior: tuple[int, int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ) -> None:
        key = (raw_done, out_mod, suffix)
        if candidate < dp[end].get(key, float("inf")):
            dp[end][key] = candidate
            prev[(end, raw_done, out_mod, suffix)] = prior

    for pos in range(n):
        for (raw_done, out_mod, suffix), base in list(dp[pos].items()):
            skip_delta, outputs, expired, tax = h125.raw_atom_outputs(config, items[pos])
            advanced = transition_outputs(config, outputs, zone_size, out_mod, suffix)
            if math.isfinite(skip_delta) and advanced is not None:
                next_mod, next_suffix = advanced
                update(
                    pos + 1,
                    raw_done,
                    next_mod,
                    next_suffix,
                    base + skip_delta,
                    (pos, raw_done, out_mod, suffix, "skip", None, outputs, expired, tax, 0),
                )

            for edge in edges_by_start[pos]:
                if table is None:
                    delta = edge.local_delta
                    width = edge.payload_width
                    padding = 0
                else:
                    gap = gap_for(table, edge)
                    if not h123.is_gap_candidate(edge, gap):
                        continue
                    delta = h123.gap_delta(edge, gap)
                    width = edge.target_bits - gap
                    padding = width - edge.payload_width
                output = [h115.Item(bits=edge.arity_bits + width, raw_bits=edge.raw_bits, record_age=0)]
                advanced = transition_outputs(config, output, zone_size, out_mod, suffix)
                if advanced is None:
                    continue
                next_mod, next_suffix = advanced
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                update(
                    end,
                    new_raw,
                    next_mod,
                    next_suffix,
                    base + delta,
                    (pos, raw_done, out_mod, suffix, "edge", edge, output, 0, 0, padding),
                )

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_key: tuple[int, int, int] | None = None
    best_delta = float("inf")
    for (raw_done, out_mod, suffix), delta in dp[n].items():
        if raw_done >= min_raw and delta < best_delta:
            best_delta = delta
            best_key = (raw_done, out_mod, suffix)
    if best_key is None:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(float("inf"), 0.0, input_bits, input_bits, 0, 0, due_seen, 0, 0, 0, 0, 0, 0), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    expired_records = 0
    expiry_tax = 0
    padding_bits = 0
    selected_edges: list[h116.RichEdge] = []
    pos = n
    raw, out_mod, suffix = best_key
    while pos > 0:
        entry = prev[(pos, raw, out_mod, suffix)]
        prior_pos, prior_raw, prior_mod, prior_suffix, kind, edge, outputs, expired, tax, padding = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            padding_bits += padding
            if edge is None:
                raise AssertionError("selected edge missing")
            due_covered += edge.old_count
            if collect_edges:
                selected_edges.append(edge)
        expired_records += expired
        expiry_tax += tax
        pos = prior_pos
        raw = prior_raw
        out_mod = prior_mod
        suffix = prior_suffix

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    raw_items = sum(1 for item in next_items if h125.is_markerless_raw_atom(config, item))
    count_bits = count_ledger_bits(len(next_items), zone_size)
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    selected_edges.reverse()
    return next_items, StepStats(
        delta_bits=best_delta + count_bits,
        count_bits=count_bits,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_key[0],
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        expired_records=expired_records,
        expiry_tax_bits=expiry_tax,
        padding_bits=padding_bits,
        output_items=len(next_items),
        raw_items=raw_items,
    ), selected_edges


def collect_local_edges(
    config: h115.Config,
    slack: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    zone_size: int,
) -> list[h116.RichEdge]:
    items = h115.initial_items(config)
    edges: list[h116.RichEdge] = []
    for step in range(passes):
        next_items, _stats, selected = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            None,
            zone_size,
            collect_edges=True,
        )
        if next_items is None:
            break
        edges.extend(selected)
        items = next_items
    return edges


def fit_table(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    zone_size: int,
) -> h125.GapTable:
    buckets: dict[tuple[int, ...], list[int]] = defaultdict(list)
    all_gaps: list[int] = []
    for trial in range(train_trials):
        edges = collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
            zone_size,
        )
        for edge in edges:
            gap = h123.actual_gap(edge)
            buckets[h123.context_for(context, edge)].append(gap)
            all_gaps.append(gap)
    fallback = h123.quantile_gap(all_gaps, quantile)
    gaps = {key: h123.quantile_gap(values, quantile) for key, values in buckets.items()}
    return h125.GapTable(context=context, gaps=gaps, fallback_gap=fallback, quantile=quantile)


@dataclass(frozen=True)
class TrialStats:
    failed: bool
    delta_per_atom: float
    delta_per_atom_pass: float
    count_bits_per_atom_pass: float
    selected_per_atom_pass: float
    expired_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_per_selected: float
    output_items_per_atom_pass: float
    raw_items_per_atom_pass: float


def simulate_trial(
    config: h115.Config,
    slack: int,
    table: h125.GapTable,
    zone_size: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> TrialStats:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    total_delta = 0.0
    count_bits = 0.0
    selected = 0
    due_seen = 0
    due_covered = 0
    expired = 0
    expiry_tax = 0
    padding = 0
    output_items = 0
    raw_items = 0
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats, _selected_edges = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            table,
            zone_size,
        )
        if next_items is None:
            return TrialStats(True, float("inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        total_delta += stats.delta_bits
        count_bits += stats.count_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        expired += stats.expired_records
        expiry_tax += stats.expiry_tax_bits
        padding += stats.padding_bits
        output_items += stats.output_items
        raw_items += stats.raw_items
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items
    return TrialStats(
        False,
        total_delta / raw_atoms,
        total_delta / raw_atoms / passes,
        count_bits / raw_atoms / passes,
        selected / raw_atoms / passes,
        expired / raw_atoms / passes,
        expiry_tax / raw_atoms / passes,
        mean(rewrite_fracs) if rewrite_fracs else 0.0,
        1.0 if due_seen == 0 else due_covered / due_seen,
        padding / max(1, selected),
        output_items / raw_atoms / passes,
        raw_items / raw_atoms / passes,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    zone_size: int,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    table = fit_table(
        config,
        slack,
        context,
        quantile,
        passes,
        train_trials,
        seed,
        min_rewrite_raw_fraction,
        zone_size,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            table,
            zone_size,
            passes,
            seed + 99_999_937 + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for trial in range(eval_trials)
    ]
    finite = [trial for trial in trials if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trials)
    table_gaps = list(table.gaps.values())
    if not finite:
        return Row(
            config.name,
            context.name,
            quantile,
            zone_size,
            config.atoms,
            passes,
            eval_trials,
            min_rewrite_raw_fraction,
            float("inf"),
            float("inf"),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            fail_rate,
            table.fallback_gap,
            mean(table_gaps) if table_gaps else float(table.fallback_gap),
            len(table.gaps),
        )
    return Row(
        config.name,
        context.name,
        quantile,
        zone_size,
        config.atoms,
        passes,
        eval_trials,
        min_rewrite_raw_fraction,
        mean(trial.delta_per_atom for trial in finite),
        mean(trial.delta_per_atom_pass for trial in finite),
        mean(trial.count_bits_per_atom_pass for trial in finite),
        mean(trial.selected_per_atom_pass for trial in finite),
        mean(trial.expired_per_atom_pass for trial in finite),
        mean(trial.expiry_tax_per_atom_pass for trial in finite),
        mean(trial.avg_rewrite_fraction for trial in finite),
        mean(trial.due_cover_rate for trial in finite),
        mean(trial.padding_per_selected for trial in finite),
        mean(trial.output_items_per_atom_pass for trial in finite),
        mean(trial.raw_items_per_atom_pass for trial in finite),
        fail_rate,
        table.fallback_gap,
        mean(table_gaps) if table_gaps else float(table.fallback_gap),
        len(table.gaps),
    )


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,q,zone,atoms,passes,trials,min_rewrite,delta/atom,"
        "delta/atom/pass,count/atom/pass,sel/atom/pass,expired/atom/pass,"
        "expiry_tax/atom/pass,rewrite_frac,due_cover,padding/sel,"
        "out_items/atom/pass,raw_items/atom/pass,fail,fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.quantile:.2f},"
            f"{row.zone_size},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{fmt(row.delta_per_atom)},"
            f"{fmt(row.delta_per_atom_pass)},"
            f"{fmt(row.count_bits_per_atom_pass)},"
            f"{fmt(row.selected_records_per_atom_pass)},"
            f"{fmt(row.expired_records_per_atom_pass)},"
            f"{fmt(row.expiry_tax_per_atom_pass)},"
            f"{fmt(row.avg_rewrite_fraction)},"
            f"{fmt(row.due_cover_rate)},"
            f"{fmt(row.padding_bits_per_selected)},"
            f"{fmt(row.output_items_per_atom_pass)},"
            f"{fmt(row.raw_items_per_atom_pass)},"
            f"{fmt(row.fail_rate)},"
            f"{row.fallback_gap},{fmt(row.avg_table_gap)},"
            f"{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=129_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--zone-size", type=int, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = h123.default_contexts(period=16, phase=0)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    zone_sizes = args.zone_size or [8, 16, 32, 64, 128]
    quantiles = args.quantile or [0.10]
    rows: list[Row] = []
    for config in configs:
        for context in contexts:
            for quantile in quantiles:
                for zone_size in zone_sizes:
                    rows.append(
                        evaluate(
                            config=config,
                            slack=args.slack,
                            context=context,
                            quantile=quantile,
                            zone_size=zone_size,
                            passes=args.passes,
                            train_trials=args.train_trials,
                            eval_trials=args.eval_trials,
                            seed=args.seed + zone_size * 1_000_003,
                            min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                        )
                    )
    print_rows(rows)


if __name__ == "__main__":
    main()
