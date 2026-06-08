"""Exact canonical v1 record costs for the Telomere proof kernel.

This module mirrors the active Rust path:

    src/header.rs::v1_record_bit_len(arity, seed_index)
      = canonical arity codeword + lotus::lotus_encoded_bit_len(seed, J3D1)

The Python arithmetic is not an approximation. It is the same width recurrence
used by the sibling Lotus crate, and ``validate_against_rust_probe`` checks it
against the Rust probe in ``src/bin/v1_cost_table.rs``.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]

ARITY_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
LITERAL_MARKER_BITS = 3
LITERAL_PAD_BUDGET_BITS = 7
LITERAL_ENTRY_OVERHEAD_BITS = LITERAL_MARKER_BITS + LITERAL_PAD_BUDGET_BITS
LITERAL_BYTE_ALIGNED_PAD_BITS = 5
LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS = LITERAL_MARKER_BITS + LITERAL_BYTE_ALIGNED_PAD_BITS
LOTUS_SEED_INDEX_J_BITS = 3
LOTUS_SEED_INDEX_TIERS = 1
MAX_PAYLOAD_WIDTH_BITS = 508


@dataclass(frozen=True)
class CostRow:
    payload_width: int
    j3d1_bits: int
    arity_bits: dict[int, int]
    rust_checked: bool


def arity_cost(arity: int) -> int:
    if arity == 0xFF:
        return LITERAL_MARKER_BITS
    return ARITY_BITS[arity]


def literal_entry_bits(raw_bits: int) -> int:
    """Worst-case v1 literal candidate cost used by ``compress.rs``."""

    return raw_bits + LITERAL_ENTRY_OVERHEAD_BITS


def byte_aligned_literal_entry_bits(raw_bits: int) -> int:
    """Literal cost when the marker begins on a byte boundary.

    The v1 writer emits the 3-bit literal marker, zero-pads to the next byte,
    then copies raw bytes. A literal immediately after another literal starts on
    a byte boundary, so its exact overhead is 3 marker bits plus 5 zero pad
    bits. The worst-case budget remains ``literal_entry_bits``.
    """

    return raw_bits + LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS


def lotus_width_for_value(value: int) -> int:
    """Width recurrence from ``../lotus/src/lib.rs::lotus_width_for_value``."""

    if value < 0:
        raise ValueError("Lotus values are unsigned")
    width = 1
    while True:
        start = (1 << width) - 2
        end = (1 << (width + 1)) - 3
        if start <= value <= end:
            return width
        width += 1


@lru_cache(maxsize=None)
def payload_width_for_seed_index(seed_index: int) -> int:
    if seed_index < 0:
        raise ValueError("seed_index must be non-negative")
    return lotus_width_for_value(seed_index + 1)


@lru_cache(maxsize=None)
def j3d1_cost_for_payload_width(payload_width: int) -> int:
    if not 1 <= payload_width <= MAX_PAYLOAD_WIDTH_BITS:
        raise ValueError(f"payload_width must be 1..={MAX_PAYLOAD_WIDTH_BITS}")
    tier_width = lotus_width_for_value(payload_width)
    return LOTUS_SEED_INDEX_J_BITS + tier_width + payload_width


def j3d1_cost_for_seed_index(seed_index: int) -> int:
    return j3d1_cost_for_payload_width(payload_width_for_seed_index(seed_index))


def record_cost_for_payload_width(arity: int, payload_width: int) -> int:
    return arity_cost(arity) + j3d1_cost_for_payload_width(payload_width)


def record_cost(arity: int, seed_index: int) -> int:
    return arity_cost(arity) + j3d1_cost_for_seed_index(seed_index)


def min_record_bits(arity: int = 1) -> int:
    return record_cost(arity, 0)


def payload_width_count_exact(payload_width: int) -> int:
    """Number of seed indices with exactly this Lotus payload width."""

    if payload_width == 1:
        return 1
    return 1 << payload_width


def payload_width_count_le(payload_width: int) -> int:
    """Number of seed indices whose Lotus payload width is <= ``payload_width``."""

    if payload_width < 1:
        return 0
    return (1 << (payload_width + 1)) - 3


def payload_width_for_count(seed_count: int) -> int:
    if seed_count <= 0:
        return 0
    width = max(1, seed_count.bit_length() - 1)
    while payload_width_count_le(width) < seed_count:
        width += 1
    return width


def seed_count_for_depth_bits(depth_bits: int) -> int:
    """Conceptual seed-depth schedule: first ``2**depth_bits`` seed records."""

    if depth_bits < 0:
        raise ValueError("depth_bits must be non-negative")
    return 1 << depth_bits


@lru_cache(maxsize=None)
def pstar_for_record_budget(arity: int, record_budget_bits: int) -> int:
    """Largest payload width whose full record cost is <= the budget."""

    best = 0
    for payload_width in range(1, MAX_PAYLOAD_WIDTH_BITS + 1):
        if record_cost_for_payload_width(arity, payload_width) <= record_budget_bits:
            best = payload_width
        else:
            break
    return best


def seed_records_with_cost_le(arity: int, record_budget_bits: int, depth_bits: int) -> int:
    """M(a, r, D): admissible seed records under both cost and depth limits."""

    payload_width = pstar_for_record_budget(arity, record_budget_bits)
    if payload_width < 1:
        return 0
    return min(payload_width_count_le(payload_width), seed_count_for_depth_bits(depth_bits))


def exact_cost_rows(max_payload_width: int = 256) -> list[CostRow]:
    return [
        CostRow(
            payload_width=payload_width,
            j3d1_bits=j3d1_cost_for_payload_width(payload_width),
            arity_bits={
                arity: record_cost_for_payload_width(arity, payload_width)
                for arity in range(1, 6)
            },
            rust_checked=payload_width <= 64,
        )
        for payload_width in range(1, max_payload_width + 1)
    ]


def rust_cost_table() -> dict:
    output = subprocess.check_output(
        ["cargo", "run", "--quiet", "--bin", "v1_cost_table"],
        cwd=ROOT,
        text=True,
    )
    return json.loads(output)


def validate_against_rust_probe(max_payload_width: int = 256) -> dict:
    """Return a validation summary, raising if Python and Rust disagree."""

    rust = rust_cost_table()
    rows = rust["payload_width_rows"]
    if len(rows) < max_payload_width:
        raise AssertionError("Rust probe returned too few payload-width rows")
    mismatches: list[str] = []
    for row in rows[:max_payload_width]:
        payload_width = int(row["payload_width"])
        expected_j = j3d1_cost_for_payload_width(payload_width)
        if int(row["j3d1_bits"]) != expected_j:
            mismatches.append(f"payload_width={payload_width} j3d1")
        for arity in range(1, 6):
            key = f"arity_{arity}_bits"
            expected = record_cost_for_payload_width(arity, payload_width)
            if int(row[key]) != expected:
                mismatches.append(f"payload_width={payload_width} arity={arity}")
    if mismatches:
        raise AssertionError("cost mismatches: " + ", ".join(mismatches[:20]))
    return {
        "payload_widths_checked": max_payload_width,
        "rust_v1_record_bit_len_checked_widths": sum(
            1 for row in rows[:max_payload_width] if row["rust_v1_record_bit_len_checked"]
        ),
        "literal_marker_bits": rust["literal_marker_bits"],
        "max_payload_width_bits": rust["max_payload_width_bits"],
    }


def cost_table_markdown(max_payload_width: int = 32) -> str:
    lines = [
        "| payload width | J3D1 bits | arity 1 | arity 2 | arity 3 | arity 4 | arity 5 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in exact_cost_rows(max_payload_width):
        lines.append(
            f"| {row.payload_width} | {row.j3d1_bits} | "
            f"{row.arity_bits[1]} | {row.arity_bits[2]} | {row.arity_bits[3]} | "
            f"{row.arity_bits[4]} | {row.arity_bits[5]} |"
        )
    return "\n".join(lines)


def boundary_payload_widths() -> Iterable[int]:
    yield from [1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 24, 32, 48, 64, 96, 121, 160, 256]


if __name__ == "__main__":
    summary = validate_against_rust_probe()
    print(json.dumps(summary, indent=2))
