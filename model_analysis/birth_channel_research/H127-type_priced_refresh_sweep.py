#!/usr/bin/env python3
"""H127 - type-priced partial refresh sweep.

H124 showed a negative raw-atom fallback lower bound at 25% rewrite, but the
hidden raw/record placement stream erased it. This kernel sweeps the rewrite
quota to test the user's proposed sweet spot:

    replace enough material to keep freshness, but not so much that placement
    and fallback metadata consume the savings.

Rows report the apparent H124 delta and two honest repairs:

* bitmap_net = delta + log2(C(output_items, raw_items));
* run_net = delta + log2(C(output_items + 1, 2 * raw_runs)).

Negative net rows would be candidate parse languages. Positive rows mean the
refresh gain is still being stored in the raw/record type stream.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path

H124_PATH = Path(__file__).with_name("H124-gap_table_fallback_repair.py")
H124_SPEC = importlib.util.spec_from_file_location("h124_gap_table_fallback", H124_PATH)
if H124_SPEC is None or H124_SPEC.loader is None:
    raise RuntimeError(f"could not load {H124_PATH}")
h124 = importlib.util.module_from_spec(H124_SPEC)
sys.modules[H124_SPEC.name] = h124
H124_SPEC.loader.exec_module(h124)
h123 = h124.h123
h116 = h124.h116


@dataclass(frozen=True)
class NetRow:
    config_name: str
    context_name: str
    quantile: float
    min_rewrite: float
    trials: int
    delta_per_atom_pass: float
    bitmap_net_per_atom_pass: float
    run_net_per_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    raw_items_per_atom_pass: float
    raw_runs_per_atom_pass: float
    bitmap_cost_per_atom_pass: float
    run_cost_per_atom_pass: float
    rewrite_fraction: float
    due_cover_rate: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[NetRow]) -> None:
    print(
        "config,context,q,min_rewrite,trials,delta/pass,bitmap_net/pass,"
        "run_net/pass,sel/atom/pass,expired/atom/pass,raw_items/atom/pass,"
        "raw_runs/atom/pass,bitmap_cost/pass,run_cost/pass,rewrite_frac,"
        "due_cover,fail,fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.quantile:.2f},"
            f"{row.min_rewrite:.3f},{row.trials},"
            f"{fmt(row.delta_per_atom_pass)},"
            f"{fmt(row.bitmap_net_per_atom_pass)},"
            f"{fmt(row.run_net_per_atom_pass)},"
            f"{fmt(row.selected_records_per_atom_pass)},"
            f"{fmt(row.expired_records_per_atom_pass)},"
            f"{fmt(row.raw_items_per_atom_pass)},"
            f"{fmt(row.raw_runs_per_atom_pass)},"
            f"{fmt(row.bitmap_cost_per_atom_pass)},"
            f"{fmt(row.run_cost_per_atom_pass)},"
            f"{fmt(row.rewrite_fraction)},"
            f"{fmt(row.due_cover_rate)},"
            f"{fmt(row.fail_rate)},"
            f"{row.fallback_gap},{fmt(row.avg_table_gap)},{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=6)
    parser.add_argument("--eval-trials", type=int, default=12)
    parser.add_argument("--seed", type=int, default=127_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--min-rewrite", type=float, action="append", default=[])
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

    quantiles = args.quantile or [0.10]
    min_rewrites = args.min_rewrite or [0.01, 0.03, 0.05, 0.10, 0.15, 0.25]
    rows: list[NetRow] = []
    for config in configs:
        for context in contexts:
            for quantile in quantiles:
                for min_rewrite in min_rewrites:
                    result = h124.evaluate(
                        config=config,
                        slack=args.slack,
                        context=context,
                        quantile=quantile,
                        expiry_mode="expire_raw_atoms",
                        passes=args.passes,
                        train_trials=args.train_trials,
                        eval_trials=args.eval_trials,
                        seed=args.seed,
                        min_rewrite_raw_fraction=min_rewrite,
                    )
                    rows.append(
                        NetRow(
                            config_name=result.config_name,
                            context_name=result.context_name,
                            quantile=result.quantile,
                            min_rewrite=result.min_rewrite,
                            trials=result.trials,
                            delta_per_atom_pass=result.delta_per_atom_pass,
                            bitmap_net_per_atom_pass=(
                                result.delta_per_atom_pass
                                + result.type_bitmap_bits_per_atom_pass
                            ),
                            run_net_per_atom_pass=(
                                result.delta_per_atom_pass
                                + result.type_run_bits_per_atom_pass
                            ),
                            selected_records_per_atom_pass=result.selected_records_per_atom_pass,
                            expired_records_per_atom_pass=result.expired_records_per_atom_pass,
                            raw_items_per_atom_pass=result.raw_items_per_atom_pass,
                            raw_runs_per_atom_pass=result.raw_runs_per_atom_pass,
                            bitmap_cost_per_atom_pass=result.type_bitmap_bits_per_atom_pass,
                            run_cost_per_atom_pass=result.type_run_bits_per_atom_pass,
                            rewrite_fraction=result.avg_rewrite_fraction,
                            due_cover_rate=result.due_cover_rate,
                            fail_rate=result.fail_rate,
                            fallback_gap=result.fallback_gap,
                            avg_table_gap=result.avg_table_gap,
                            table_entries=result.table_entries,
                        )
                    )
    print_rows(rows)


if __name__ == "__main__":
    main()
