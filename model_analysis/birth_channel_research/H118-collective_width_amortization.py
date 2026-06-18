#!/usr/bin/env python3
"""H118 - collective width-stream accounting for forced due refresh.

H117 showed that parseable per-record payload-width symbols are close only when
the DP rewrites very little. This kernel asks whether width symbols become cheap
enough when coded collectively over a pass/layer.

It uses the local-width oracle cover from H117, then prices the selected width
sequence three ways:

* fixed: each width costs ceil(log2(D)) bits;
* enum_free: exact log2 multinomial width stream, count vector not charged;
* enum_count_paid: enum_free plus an exact positive-count vector/header;
* enum_asymptotic: same formula as enum_free, but use --count-scale to repeat
  the empirical pass ledger and approach the large-file entropy rate.

This is a lower-bound accounting kernel, not a codec: the selection is still
made by the local oracle before the collective width code is charged. A
scale-1 enum_free crossing can be a short-sequence artifact; scale it before
treating it as an amortized result.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

H117_PATH = Path(__file__).with_name("H117-parseable_width_symbol.py")
H117_SPEC = importlib.util.spec_from_file_location("h117_width_symbol", H117_PATH)
if H117_SPEC is None or H117_SPEC.loader is None:
    raise RuntimeError(f"could not load {H117_PATH}")
h117 = importlib.util.module_from_spec(H117_SPEC)
sys.modules[H117_SPEC.name] = h117
H117_SPEC.loader.exec_module(h117)
h116 = h117.h116
h115 = h117.h115


@dataclass(frozen=True)
class PassLedger:
    local_delta: float
    raw_atoms: float
    selected: int
    rewritten_raw_fraction: float
    widths: tuple[int, ...]
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    mode: str
    count_scale: int
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom_pass: float
    width_bits_per_record: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    fail_rate: float


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2)


def log2_multinomial(counts: Counter[int]) -> float:
    total = sum(counts.values())
    value = math.lgamma(total + 1)
    for count in counts.values():
        value -= math.lgamma(count + 1)
    return value / math.log(2)


def positive_count_vector_bits(total: int, used_bins: int, frontier: int) -> float:
    if total == 0:
        return 0.0
    # Choose the used width symbols, then choose positive counts summing to total.
    return log2_comb(frontier, used_bins) + log2_comb(total - 1, used_bins - 1)


def width_stream_bits(widths: tuple[int, ...], frontier: int, mode: str, count_scale: int) -> float:
    if not widths:
        return 0.0
    counts = Counter(widths)
    if count_scale > 1:
        counts = Counter({width: count * count_scale for width, count in counts.items()})
    if mode == "fixed":
        return sum(counts.values()) * math.ceil(math.log2(frontier))
    if mode in {"enum_free", "enum_asymptotic"}:
        return log2_multinomial(counts)
    if mode == "enum_count_paid":
        total = sum(counts.values())
        return log2_multinomial(counts) + positive_count_vector_bits(
            total,
            len(counts),
            frontier,
        )
    raise ValueError(mode)


def run_trial(
    config: h115.Config,
    slack: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> list[PassLedger]:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    ledgers: list[PassLedger] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats, edges = h117.select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            None,
            collect_edges=True,
        )
        if next_items is None:
            ledgers.append(
                PassLedger(
                    local_delta=float("inf"),
                    raw_atoms=raw_atoms,
                    selected=0,
                    rewritten_raw_fraction=0.0,
                    widths=(),
                    failed=True,
                )
            )
            break
        ledgers.append(
            PassLedger(
                local_delta=stats.delta_bits,
                raw_atoms=raw_atoms,
                selected=stats.selected_records,
                rewritten_raw_fraction=stats.rewritten_raw_bits / max(1, total_raw),
                widths=tuple(edge.payload_width for edge in edges),
                failed=False,
            )
        )
        items = next_items
    return ledgers


def evaluate(
    config: h115.Config,
    slack: int,
    mode: str,
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    count_scale: int,
) -> Row:
    pass_ledgers: list[PassLedger] = []
    failed_trials = 0
    for trial in range(trials):
        ledgers = run_trial(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        if len(ledgers) < passes or any(ledger.failed for ledger in ledgers):
            failed_trials += 1
            continue
        pass_ledgers.extend(ledgers)

    if not pass_ledgers:
        return Row(
            config_name=config.name,
            mode=mode,
            count_scale=count_scale,
            atoms=config.atoms,
            passes=passes,
            trials=trials,
            min_rewrite=min_rewrite_raw_fraction,
            delta_per_atom_pass=float("inf"),
            width_bits_per_record=float("inf"),
            selected_records_per_atom_pass=0.0,
            avg_rewrite_fraction=0.0,
            fail_rate=failed_trials / trials,
        )

    total_delta = 0.0
    total_width_bits = 0.0
    total_selected = 0
    total_atom_passes = 0.0
    rewrite_fracs: list[float] = []
    for ledger in pass_ledgers:
        width_bits = width_stream_bits(ledger.widths, config.frontier, mode, count_scale)
        total_delta += ledger.local_delta * count_scale + width_bits
        total_width_bits += width_bits
        total_selected += ledger.selected * count_scale
        total_atom_passes += ledger.raw_atoms * count_scale
        rewrite_fracs.append(ledger.rewritten_raw_fraction)

    return Row(
        config_name=config.name,
        mode=mode,
        count_scale=count_scale,
        atoms=config.atoms,
        passes=passes,
        trials=trials,
        min_rewrite=min_rewrite_raw_fraction,
        delta_per_atom_pass=total_delta / total_atom_passes,
        width_bits_per_record=total_width_bits / max(1, total_selected),
        selected_records_per_atom_pass=total_selected / total_atom_passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        fail_rate=failed_trials / trials,
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,mode,atoms,passes,trials,min_rewrite,"
        "scale,delta/atom/pass,width_bits/record,sel/atom/pass,rewrite_frac,fail"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.mode},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{row.count_scale},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.width_bits_per_record)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.fail_rate)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=118_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, action="append", default=[])
    parser.add_argument("--mode", action="append", default=[])
    parser.add_argument("--count-scale", type=int, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    min_rewrites = args.min_rewrite_raw_frac or [0.0, 0.25]
    modes = args.mode or ["fixed", "enum_free", "enum_count_paid", "enum_asymptotic"]
    count_scales = args.count_scale or [1]

    rows: list[Row] = []
    for config in configs:
        for min_rewrite in min_rewrites:
            for mode in modes:
                for count_scale in count_scales:
                    rows.append(
                        evaluate(
                            config=config,
                            slack=args.slack,
                            mode=mode,
                            passes=args.passes,
                            trials=args.trials,
                            seed=args.seed,
                            min_rewrite_raw_fraction=min_rewrite,
                            count_scale=count_scale,
                        )
                    )
    print_rows(rows)


if __name__ == "__main__":
    main()
