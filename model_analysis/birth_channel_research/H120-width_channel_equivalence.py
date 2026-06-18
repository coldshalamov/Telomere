#!/usr/bin/env python3
"""H120 - equivalence ledger for payload-width boundary channels.

H118/H119 showed that explicit width streams, collective width streams, and
fixed public widths all miss. This kernel prices the same selected width
sequence under several disguises:

* explicit enumerative width stream;
* optimal seed-class supply loss for width-derived seed classes;
* prefix/self-synchronizing lower bound;
* trial-decode/checksum referee ambiguity.

The point is to test whether "hide the width symbol in X" changes the currency.
It should not: for a selected width distribution p(w), any prefix/seed-class
scheme pays at least H(W) per selected record unless it changes p(w) or makes W
public by an independent invariant.
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

H118_PATH = Path(__file__).with_name("H118-collective_width_amortization.py")
H118_SPEC = importlib.util.spec_from_file_location("h118_collective_width", H118_PATH)
if H118_SPEC is None or H118_SPEC.loader is None:
    raise RuntimeError(f"could not load {H118_PATH}")
h118 = importlib.util.module_from_spec(H118_SPEC)
sys.modules[H118_SPEC.name] = h118
H118_SPEC.loader.exec_module(h118)
h116 = h118.h116


@dataclass(frozen=True)
class Row:
    config_name: str
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    scale: int
    selected: int
    fail_rate: float
    local_delta_per_atom_pass: float
    fixed_bits_per_record: float
    enum_bits_per_record: float
    count_paid_bits_per_record: float
    entropy_bits_per_record: float
    seed_class_bits_per_record: float
    referee_known_counts_bits_per_record: float
    referee_no_counts_bits_per_record: float
    checksum64_records_known_counts: float
    total_enum_per_atom_pass: float
    total_seed_class_per_atom_pass: float


def entropy_bits(counts: Counter[int]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return sum(count * math.log2(total / count) for count in counts.values())


def collect_ledgers(
    config: h118.h115.Config,
    slack: int,
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> tuple[list[h118.PassLedger], int]:
    pass_ledgers: list[h118.PassLedger] = []
    failed_trials = 0
    for trial in range(trials):
        ledgers = h118.run_trial(
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
    return pass_ledgers, failed_trials


def evaluate(
    config: h118.h115.Config,
    slack: int,
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    scale: int,
) -> Row:
    ledgers, failed_trials = collect_ledgers(
        config,
        slack,
        passes,
        trials,
        seed,
        min_rewrite_raw_fraction,
    )
    if not ledgers:
        return Row(
            config_name=config.name,
            atoms=config.atoms,
            passes=passes,
            trials=trials,
            min_rewrite=min_rewrite_raw_fraction,
            scale=scale,
            selected=0,
            fail_rate=failed_trials / trials,
            local_delta_per_atom_pass=float("inf"),
            fixed_bits_per_record=float("inf"),
            enum_bits_per_record=float("inf"),
            count_paid_bits_per_record=float("inf"),
            entropy_bits_per_record=float("inf"),
            seed_class_bits_per_record=float("inf"),
            referee_known_counts_bits_per_record=float("inf"),
            referee_no_counts_bits_per_record=float("inf"),
            checksum64_records_known_counts=0.0,
            total_enum_per_atom_pass=float("inf"),
            total_seed_class_per_atom_pass=float("inf"),
        )

    widths: list[int] = []
    total_local_delta = 0.0
    total_atom_passes = 0.0
    selected_unscaled = 0
    for ledger in ledgers:
        widths.extend(ledger.widths)
        total_local_delta += ledger.local_delta * scale
        total_atom_passes += ledger.raw_atoms * scale
        selected_unscaled += ledger.selected

    if not widths:
        selected = 0
        fixed_bits = enum_bits = count_paid_bits = entropy = 0.0
    else:
        selected = len(widths) * scale
        fixed_bits = selected * math.ceil(math.log2(config.frontier))
        enum_bits = h118.width_stream_bits(tuple(widths), config.frontier, "enum_free", scale)
        count_paid_bits = h118.width_stream_bits(tuple(widths), config.frontier, "enum_count_paid", scale)
        counts = Counter(widths)
        if scale > 1:
            counts = Counter({width: count * scale for width, count in counts.items()})
        entropy = entropy_bits(counts)

    selected_per_atom_pass = selected / total_atom_passes if total_atom_passes else 0.0
    local_delta_per_atom_pass = total_local_delta / total_atom_passes if total_atom_passes else float("inf")
    enum_per_record = enum_bits / max(1, selected)
    entropy_per_record = entropy / max(1, selected)
    seed_class_per_record = entropy_per_record
    referee_known_per_record = enum_per_record
    referee_no_counts_per_record = math.ceil(math.log2(config.frontier)) if selected else 0.0
    checksum64_records = 64.0 / referee_known_per_record if referee_known_per_record > 0 else float("inf")

    return Row(
        config_name=config.name,
        atoms=config.atoms,
        passes=passes,
        trials=trials,
        min_rewrite=min_rewrite_raw_fraction,
        scale=scale,
        selected=selected,
        fail_rate=failed_trials / trials,
        local_delta_per_atom_pass=local_delta_per_atom_pass,
        fixed_bits_per_record=fixed_bits / max(1, selected),
        enum_bits_per_record=enum_per_record,
        count_paid_bits_per_record=count_paid_bits / max(1, selected),
        entropy_bits_per_record=entropy_per_record,
        seed_class_bits_per_record=seed_class_per_record,
        referee_known_counts_bits_per_record=referee_known_per_record,
        referee_no_counts_bits_per_record=referee_no_counts_per_record,
        checksum64_records_known_counts=checksum64_records,
        total_enum_per_atom_pass=local_delta_per_atom_pass + enum_per_record * selected_per_atom_pass,
        total_seed_class_per_atom_pass=local_delta_per_atom_pass + seed_class_per_record * selected_per_atom_pass,
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,atoms,passes,trials,min_rewrite,scale,selected,fail,"
        "local_delta/atom/pass,fixed/rec,enum/rec,count_paid/rec,"
        "entropy/rec,seed_class/rec,ref_known/rec,ref_no_counts/rec,"
        "checksum64_records,total_enum/atom/pass,total_seed_class/atom/pass"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{row.scale},{row.selected},"
            f"{format_float(row.fail_rate)},"
            f"{format_float(row.local_delta_per_atom_pass)},"
            f"{format_float(row.fixed_bits_per_record)},"
            f"{format_float(row.enum_bits_per_record)},"
            f"{format_float(row.count_paid_bits_per_record)},"
            f"{format_float(row.entropy_bits_per_record)},"
            f"{format_float(row.seed_class_bits_per_record)},"
            f"{format_float(row.referee_known_counts_bits_per_record)},"
            f"{format_float(row.referee_no_counts_bits_per_record)},"
            f"{format_float(row.checksum64_records_known_counts)},"
            f"{format_float(row.total_enum_per_atom_pass)},"
            f"{format_float(row.total_seed_class_per_atom_pass)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=120_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--scale", type=int, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]
    scales = args.scale or [1, 16, 256, 1024]

    rows: list[Row] = []
    for config in configs:
        for scale in scales:
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    passes=args.passes,
                    trials=args.trials,
                    seed=args.seed,
                    min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                    scale=scale,
                )
            )
    print_rows(rows)


if __name__ == "__main__":
    main()
