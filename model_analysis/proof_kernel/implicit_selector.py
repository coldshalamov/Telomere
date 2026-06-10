"""Implicit deterministic selector (decode-by-replay) with charged escapes.

Context. A rechunked layer mixes seed records with verbatim chunks. The v1
arity alphabet is Kraft-complete, so a decoder cannot discriminate "record"
from "verbatim bits" by parse failure, and replacement positions are
content-dependent, so they cannot be a profile constant. The discrimination
channel must therefore be paid for. Two charged constructions are modeled:

1. ``explicit_flag``: profile-constant prefix code, 1 bit per element
   (0 -> c verbatim bits follow, 1 -> a record follows). Charged in the wire;
   flagged chunks also enlarge spans (a-entry window = a*(1+c) wire bits).

2. ``implicit_selector`` (this module): the decoder replays the encoder's
   deterministic acceptance test. At each chunk boundary it parses a record R
   (always possible), expands it, and checks whether R is the canonical
   accepted record for E(R). Real replacements self-identify. The tax moves
   to an escape channel: whenever verbatim bits would *falsely* fire the
   test, the encoder must disambiguate. The model uses HDLC-style stuffing:
   after every fire (true or false) one disambiguation bit is charged
   (1 = real replacement, 0 = verbatim continues). The decoder strips it,
   staying in sync. All stuffing bits are charged wire bits.

Replay cost disclosure (required): the replay test makes the DECODER rerun
the canonical seed search over each fired window. Decode compute per layer is
therefore O(fires x search_cost(span)), reported separately as
``decode_replay_expansions`` — it is not hidden in the size ledger.

Structural result (proved by the Kraft ledger below, reported numerically in
the artifacts): a canonical compressive record of cost r matching a span S
with gain g = S - r contributes ~2^-S * g expected gain bits per window but
~2^-r = 2^-S * 2^g expected false-fire mass per chunk position. Net per
position is proportional to sum cnt * (g - 2^g) * 2^-S, and 2^g > g for all
g >= 1, so the per-fire stuffing tax strictly dominates the gain at every
chunk size, depth, and budget. A k-bit signature thins hits and false fires
by the same 2^-k and cannot change the sign. The zero-escape variant is
reported as a diagnostic upper bound only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from costs import (
    arity_cost,
    j3d1_cost_for_payload_width,
    payload_width_count_le,
)


@dataclass(frozen=True)
class EscapeEconomics:
    chunk_bits: int
    arity_cap: int
    depth_bits: int
    fire_mass_per_chunk: float  # expected false fires per chunk position
    stuff_bits_per_chunk: float  # charged escape bits per chunk position
    record_marker_bits: float  # disambiguation bit per real record
    kraft_gain_mass_per_chunk: float  # sum cnt * g * 2^-S per chunk position
    kraft_fire_minus_gain: float  # sum cnt * (2^g - g) * 2^-S (>0 => dominated)
    dominated: bool


def _depth_capped_exact_count(payload_width: int, depth_bits: int) -> int:
    """Seeds with exactly this payload width whose index is within depth."""

    cap = 1 << depth_bits
    le_w = min(payload_width_count_le(payload_width), cap)
    le_prev = min(payload_width_count_le(payload_width - 1), cap)
    return max(0, le_w - le_prev)


@lru_cache(maxsize=None)
def escape_economics(
    chunk_bits: int,
    arity_cap: int,
    depth_bits: int,
) -> EscapeEconomics:
    """Exact Kraft ledger for the per-fire stuffing protocol.

    A false fire at a chunk position is the event that the upcoming verbatim
    bits equal some canonical compressive record R (strict: cost(R) < span of
    its arity window). For each such record the probability is exactly
    2^-cost(R); canonicality of a random record is ~1 in this regime (the
    competing-match mass M/2^S is ~1e-4 or less), and ignoring it only makes
    the escape charge conservative by under 0.1%.
    """

    fire_mass = 0.0
    gain_mass = 0.0
    fire_minus_gain = 0.0
    for arity in range(1, arity_cap + 1):
        span_bits = arity * chunk_bits
        budget = span_bits - 1  # strict compressive requirement
        a_bits = arity_cost(arity)
        for payload_width in range(1, budget + 1):
            cost = a_bits + j3d1_cost_for_payload_width(payload_width)
            if cost > budget:
                break
            cnt = _depth_capped_exact_count(payload_width, depth_bits)
            if cnt <= 0:
                continue
            gain = span_bits - cost
            fire_mass += cnt * (2.0**-cost)
            gain_mass += cnt * gain * (2.0**-span_bits)
            fire_minus_gain += cnt * ((2.0**gain) - gain) * (2.0**-span_bits)
    return EscapeEconomics(
        chunk_bits=chunk_bits,
        arity_cap=arity_cap,
        depth_bits=depth_bits,
        fire_mass_per_chunk=fire_mass,
        stuff_bits_per_chunk=fire_mass,  # one stuffing bit per false fire
        record_marker_bits=1.0,  # one disambiguation bit per real record
        kraft_gain_mass_per_chunk=gain_mass,
        kraft_fire_minus_gain=fire_minus_gain,
        dominated=fire_minus_gain > 0.0,
    )


def decode_replay_expansions(
    chunks: float,
    fire_mass_per_chunk: float,
    accepted_records: float,
) -> float:
    """Replay test invocations per layer (each one is a canonical search)."""

    return chunks * fire_mass_per_chunk + accepted_records


def dominance_table(
    chunk_bits_axis: tuple[int, ...] = (1, 2, 3, 4, 6, 8, 12, 16),
    arity_cap: int = 5,
    depth_axis: tuple[int, ...] = (16, 32, 64, 121, 160),
) -> list[dict[str, float | int | bool]]:
    """Numeric verification of the structural dominance result."""

    rows: list[dict[str, float | int | bool]] = []
    for chunk_bits in chunk_bits_axis:
        for depth_bits in depth_axis:
            eco = escape_economics(chunk_bits, arity_cap, depth_bits)
            rows.append(
                {
                    "chunk_bits": chunk_bits,
                    "depth_bits": depth_bits,
                    "fire_mass_per_chunk": eco.fire_mass_per_chunk,
                    "gain_mass_per_chunk": eco.kraft_gain_mass_per_chunk,
                    "tax_minus_gain_per_chunk": eco.kraft_fire_minus_gain,
                    "dominated": eco.dominated,
                }
            )
    return rows


def validate_dominance() -> dict[str, int | bool]:
    """Every swept point must show tax >= gain; equality only at zero mass."""

    rows = dominance_table()
    violations = [
        row
        for row in rows
        if row["gain_mass_per_chunk"] > 0 and not row["dominated"]
    ]
    if violations:
        raise AssertionError(f"dominance violated: {violations[:3]}")
    nonzero = sum(1 for row in rows if row["gain_mass_per_chunk"] > 0)
    return {"points": len(rows), "nonzero_gain_points": nonzero, "all_dominated": True}


if __name__ == "__main__":
    print(validate_dominance())
    for row in dominance_table((2, 3, 4, 8), 5, (16, 64)):
        print(row)
