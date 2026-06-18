#!/usr/bin/env python3
"""Split ledger for the best public Total-Cover witness branch.

This diagnostic answers a narrow question: in the near-flat high-arity
Total-Cover rows, which field is carrying the remaining deficit?

The modeled record is still:

    [arity][seed witness]

and the branch remains Total-Cover: every record opens, no birth/open/carry
channel, no sparse cover map. The script reuses the public factored model from
``total_cover_public_model_kernel.py`` and splits each selected record into:

* exact rank / payload bits;
* arity bits under the legal remaining-atom mask;
* width-delta bits, where ``delta = arity * B - payload_width``.

Rows named ``free_*`` are lower-bound diagnostics, not valid codecs. If a
``free_*`` row crosses but ``paid`` does not, the named field is the bill that
would need a real decoder-derived invariant before the branch is constructive.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import generate_samples  # noqa: E402
from total_cover_public_model_kernel import (  # noqa: E402
    FIRST_PREVIOUS,
    Cover,
    PublicFactoredModel,
    context_for,
    context_uses_previous,
    cover_with_factored_model,
    factored_arity_cost,
    factored_delta_cost,
    previous_bucket,
    selected_rank_bits,
    train_public_factored,
)


@dataclass(frozen=True)
class SplitTotals:
    rank_bits: float
    arity_bits: float
    delta_bits: float
    flush_bits: float
    records: int
    atoms: int
    avg_arity: float
    avg_width: float

    @property
    def paid_bits(self) -> float:
        return self.rank_bits + self.arity_bits + self.delta_bits + self.flush_bits


@dataclass(frozen=True)
class ScenarioRow:
    name: str
    charged_bits: float
    gain_per_atom: float
    gain_per_byte: float
    bits_per_record: float
    missing_bits_per_record: float


def split_cover(
    cover: Cover,
    model: PublicFactoredModel,
    block_bits: int,
    max_arity: int,
    rank_code: str,
    scheme: str,
    flush_bits: float,
) -> SplitTotals:
    atoms = sum(record.arity for record in cover.records)
    use_prev = context_uses_previous(scheme)
    state = FIRST_PREVIOUS if use_prev else (0, 0)
    index = 0
    rank_total = 0.0
    arity_total = 0.0
    delta_total = 0.0
    for record in cover.records:
        remaining = atoms - index
        context = context_for(index, atoms, state if use_prev else FIRST_PREVIOUS, scheme, max_arity)
        rank_total += selected_rank_bits(record, rank_code)
        arity_total += factored_arity_cost(model, context, record.arity, remaining)
        delta_total += factored_delta_cost(
            model,
            context,
            block_bits,
            record.arity,
            record.lotus_payload_width,
        )
        if use_prev:
            state = previous_bucket((record.arity, record.lotus_payload_width), block_bits)
        index += record.arity
    widths = [record.lotus_payload_width for record in cover.records]
    arities = [record.arity for record in cover.records]
    return SplitTotals(
        rank_bits=rank_total,
        arity_bits=arity_total,
        delta_bits=delta_total,
        flush_bits=flush_bits,
        records=len(cover.records),
        atoms=atoms,
        avg_arity=mean(arities) if arities else 0.0,
        avg_width=mean(widths) if widths else 0.0,
    )


def scenario_rows(totals: list[SplitTotals], block_bits: int) -> list[ScenarioRow]:
    raw_bits = totals[0].atoms * block_bits if totals else 0
    scenarios = {
        "paid": lambda t: t.rank_bits + t.arity_bits + t.delta_bits + t.flush_bits,
        "free_arity": lambda t: t.rank_bits + t.delta_bits + t.flush_bits,
        "free_delta": lambda t: t.rank_bits + t.arity_bits + t.flush_bits,
        "free_stream": lambda t: t.rank_bits + t.flush_bits,
        "free_rank": lambda t: t.arity_bits + t.delta_bits + t.flush_bits,
    }
    rows: list[ScenarioRow] = []
    for name, charge in scenarios.items():
        charged_values = [charge(total) for total in totals]
        gains = [(raw_bits - charged) / total.atoms for charged, total in zip(charged_values, totals)]
        records = [total.records for total in totals]
        gain = mean(gains) if gains else float("-inf")
        bits_per_record = mean(
            charged / record_count for charged, record_count in zip(charged_values, records) if record_count
        )
        records_per_atom = mean(total.records / total.atoms for total in totals) if totals else 0.0
        missing = max(0.0, -gain / records_per_atom) if records_per_atom else float("inf")
        rows.append(
            ScenarioRow(
                name=name,
                charged_bits=mean(charged_values) if charged_values else float("inf"),
                gain_per_atom=gain,
                gain_per_byte=gain * (8.0 / block_bits) if gain != float("-inf") else float("-inf"),
                bits_per_record=bits_per_record,
                missing_bits_per_record=missing,
            )
        )
    return rows


def render(
    totals: list[SplitTotals],
    rows: list[ScenarioRow],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rank_code: str,
    context: str,
) -> str:
    records_per_atom = mean(total.records / total.atoms for total in totals) if totals else 0.0
    avg_arity = mean(total.avg_arity for total in totals) if totals else 0.0
    avg_width = mean(total.avg_width for total in totals) if totals else 0.0
    rank_per_record = mean(total.rank_bits / total.records for total in totals if total.records)
    arity_per_record = mean(total.arity_bits / total.records for total in totals if total.records)
    delta_per_record = mean(total.delta_bits / total.records for total in totals if total.records)
    paid = next(row for row in rows if row.name == "paid")
    best_stream_free = max(
        (row for row in rows if row.name in {"free_arity", "free_delta", "free_stream"}),
        key=lambda row: row.gain_per_atom,
    )
    lines = [
        "# Total-Cover Split Ledger",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`, rank code `{rank_code}`, "
        f"context `{context}`.",
        "",
        "This is a diagnostic lower-bound ledger for the public factored",
        "Total-Cover witness branch. Rows named `free_*` are not valid codecs;",
        "they identify which field would need a real decoder-derived invariant.",
        "",
        "| records/atom | avg arity | avg width | rank bits/rec | arity bits/rec | delta bits/rec | paid missing bits/rec |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {records_per_atom:.6f} | {avg_arity:.2f} | {avg_width:.2f} | "
        f"{rank_per_record:.3f} | {arity_per_record:.3f} | {delta_per_record:.3f} | "
        f"{paid.missing_bits_per_record:.3f} |",
        "",
        "| scenario | gain/atom | gain/byte | bits/record | missing bits/record |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.name} | {row.gain_per_atom:.6f} | {row.gain_per_byte:.6f} | "
            f"{row.bits_per_record:.3f} | {row.missing_bits_per_record:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"The best non-rank free-field diagnostic is `{best_stream_free.name}` at "
            f"`{best_stream_free.gain_per_atom:.6f}` bits/input atom. `free_rank` is",
            "included only as a sanity check: seed/rank bits are the payload, so",
            "making them free is not a plausible witness-language improvement.",
            "If `free_delta` or `free_stream` crosses while `paid` does not, the",
            "named stream field is the remaining information channel that must",
            "either be paid or made decoder-derived by a new invariant.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=32)
    parser.add_argument("--eval-trials", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.25)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument(
        "--context",
        choices=[
            "remaining",
            "remaining_prev_coarse",
            "progress4",
            "progress8",
            "prev_coarse",
            "progress4_prev_coarse",
            "progress8_prev_coarse",
        ],
        default="remaining",
    )
    parser.add_argument("--seed", type=int, default=777)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.seed + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.eval_trials,
        args.seed + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
    )
    model = train_public_factored(
        train_samples,
        args.block_bits,
        args.max_arity,
        args.frontier,
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
            args.frontier,
            model,
            args.flush_bits,
            args.rank_code,
            args.context,
        )
        for trial in eval_samples
    ]
    covered = [cover for cover in covers if cover.covered]
    if len(covered) != len(covers):
        print(f"coverage {len(covered)}/{len(covers)}; refusing split on incomplete cover set")
        return
    totals = [
        split_cover(
            cover,
            model,
            args.block_bits,
            args.max_arity,
            args.rank_code,
            args.context,
            args.flush_bits,
        )
        for cover in covered
    ]
    rows = scenario_rows(totals, args.block_bits)
    print(
        render(
            totals,
            rows,
            args.block_bits,
            args.max_arity,
            args.frontier,
            args.rank_code,
            args.context,
        )
    )


if __name__ == "__main__":
    main()
