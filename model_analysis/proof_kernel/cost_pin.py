"""Exact cost pinning for the Telomere proof kernel.

Pins, in one place and with one JSON artifact (``cost_pin_report.json``):

- literal marker cost (3 bits) and the three literal initialization variants
  (worst-case pad 10, byte-aligned 8, BIT_LITERAL 3);
- LITERAL_RUN header costs ``[111][Lotus(run_len)]`` for both jumpstarter
  profiles;
- arity 1..5 record costs at every payload-width boundary;
- J3D1 vs J2D1 field costs, minimum records, and payload caps;
- the reference J3D1 bit layout (jumpstarter stores tier_width-1) golden
  vectors, including the tw=8 boundary that the previous reference encoder
  could not represent;
- the 127-vs-508 payload-cap discrepancy analysis.

The Rust probe is attempted; when cargo is unavailable the report says so
honestly instead of claiming a fresh pin. Local re-pin:

    cargo run --quiet --bin v1_cost_table
    python model_analysis/proof_kernel/cost_pin.py
"""

from __future__ import annotations

import json
from pathlib import Path

from costs import (
    LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS,
    LITERAL_ENTRY_OVERHEAD_BITS,
    LITERAL_MARKER_BITS,
    MAX_PAYLOAD_WIDTH_BITS,
    arity_cost,
    boundary_payload_widths,
    j3d1_cost_for_payload_width,
    j3d1_cost_for_seed_index,
    literal_run_header_bits,
    lotus_cost_for_payload_width,
    lotus_width_for_value,
    max_payload_width_for_j_bits,
    payload_width_count_le,
    payload_width_for_seed_index,
    record_cost,
    record_cost_for_payload_width,
    record_cost_for_payload_width_j,
    seed_records_with_cost_le,
    seed_records_with_cost_le_j,
    validate_against_rust_probe,
)

KERNEL_DIR = Path(__file__).resolve().parent
BIT_LITERAL_OVERHEAD_BITS = 3  # v-next: [111][block_bits raw], zero pad


def reference_j3d1_encode(seed_index: int) -> str:
    value = seed_index + 1
    pw = payload_width_for_seed_index(seed_index)
    tw = lotus_width_for_value(pw)
    assert 1 <= tw <= 8, f"tier width {tw} out of 3-bit jumpstarter range"
    return (
        format(tw - 1, "03b")
        + format(pw - ((1 << tw) - 2), f"0{tw}b")
        + format(value - ((1 << pw) - 2), f"0{pw}b")
    )


def reference_j3d1_decode(stream: str, pos: int) -> tuple[int, int]:
    tw = int(stream[pos : pos + 3], 2) + 1
    pos += 3
    pw = int(stream[pos : pos + tw], 2) + ((1 << tw) - 2)
    pos += tw
    value = int(stream[pos : pos + pw], 2) + ((1 << pw) - 2)
    pos += pw
    return value - 1, pos


def golden_vector_rows() -> list[dict]:
    """Round-trip + width golden vectors across every tier boundary."""

    rows = []
    probe_indices: set[int] = set()
    for pw in list(boundary_payload_widths()) + [125, 126, 253, 254]:
        if pw > MAX_PAYLOAD_WIDTH_BITS:
            continue
        lo_value = (1 << pw) - 2
        hi_value = (1 << (pw + 1)) - 3
        for value in (lo_value, hi_value):
            if value >= 1:
                probe_indices.add(value - 1)
    for seed_index in sorted(probe_indices):
        bits = reference_j3d1_encode(seed_index)
        decoded, consumed = reference_j3d1_decode(bits, 0)
        expected_bits = j3d1_cost_for_seed_index(seed_index)
        ok = decoded == seed_index and consumed == len(bits) == expected_bits
        rows.append(
            {
                "seed_index": seed_index,
                "payload_width": payload_width_for_seed_index(seed_index),
                "wire_bits": len(bits),
                "costs_py_bits": expected_bits,
                "round_trip_ok": ok,
            }
        )
        if not ok:
            raise AssertionError(f"golden vector failed at seed_index={seed_index}")
    # dense sweep over the first 4096 indices plus random deep indices
    import random

    rng = random.Random(20260610)
    deep = [rng.randrange(1 << 60, 1 << 64) for _ in range(64)]
    deep += [rng.randrange(1 << 120, 1 << 121) for _ in range(8)]
    for seed_index in list(range(4096)) + deep:
        bits = reference_j3d1_encode(seed_index)
        decoded, consumed = reference_j3d1_decode(bits, 0)
        if decoded != seed_index or consumed != len(bits) != j3d1_cost_for_seed_index(seed_index):
            raise AssertionError(f"dense golden sweep failed at {seed_index}")
    return rows


def payload_cap_analysis() -> dict:
    """The 127-vs-508 question, resolved as far as repo evidence allows."""

    return {
        "repo_rust_probe_cap": max_payload_width_for_j_bits(3),
        "repo_python_cap": MAX_PAYLOAD_WIDTH_BITS,
        "pasted_note_cap": 127,
        "conventions": {
            "plain_binary_7bit_length_field": {
                "cap": 127,
                "consistent_with_header_rs_costs": False,
                "note": "would change every cost; contradicts v1_cost_table.rs arithmetic",
            },
            "lotus_offset_tw_raw_0_to_7": {
                "cap": 253,
                "consistent_with_header_rs_costs": "yes for payload widths <= 253",
                "note": "previous reference encoder; wastes the tw=0 slot, overflows at width 254",
            },
            "lotus_offset_tw_minus_1": {
                "cap": 508,
                "consistent_with_header_rs_costs": True,
                "note": "matches max_width_for_config(3,1)=508; adopted reference layout",
            },
        },
        "operating_range_impact": (
            "All swept depths (<=160 bits => payload widths <= ~161) cost identically "
            "under the 253- and 508-cap conventions; only depth-axis points above 253 "
            "would differ, and none are swept. A true 127 cap would invalidate the "
            "depth-160 axis; it is inconsistent with src/bin/v1_cost_table.rs."
        ),
        "final_pin_requires": "golden vectors against the sibling ../lotus crate (not in this checkout)",
    }


def pinned_cost_table() -> dict:
    table = {
        "literal_marker_bits": LITERAL_MARKER_BITS,
        "literal_worst_case_overhead_bits": LITERAL_ENTRY_OVERHEAD_BITS,
        "literal_byte_aligned_overhead_bits": LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS,
        "bit_literal_overhead_bits": BIT_LITERAL_OVERHEAD_BITS,
        "literal_run_header_bits_j3d1": {
            run: literal_run_header_bits(run, 3) for run in (1, 2, 3, 4, 8, 16, 64, 1024, 1_000_000)
        },
        "literal_run_header_bits_j2d1": {
            run: literal_run_header_bits(run, 2) for run in (1, 2, 3, 4, 8, 16, 64, 1024, 1_000_000)
        },
        "tail_literal_rule": (
            "termination is out-of-band (original_len / payload_bit_len / last_block_size); "
            "the final literal carries last_block_size raw payload under the same marker — "
            "no extra in-band terminator cost (FORMAT_CANONICAL.md §6)"
        ),
        "min_record_bits": {
            "J3D1_arity1_seed0": record_cost(1, 0),
            "J2D1_arity1_seed0": record_cost_for_payload_width_j(1, 1, 2),
        },
        "payload_caps": {
            "J2D1": max_payload_width_for_j_bits(2),
            "J3D1": max_payload_width_for_j_bits(3),
        },
        "arity_record_bits_by_payload_width": {},
        "j_field_bits_by_payload_width": {},
        "seed_index_boundaries": {},
        "M_examples": {
            "J3D1_a1_r12_D96": seed_records_with_cost_le(1, 12, 96),
            "J3D1_a1_r23_D96": seed_records_with_cost_le(1, 23, 96),
            "J2D1_a1_r12_D28": seed_records_with_cost_le_j(1, 12, 28, 2),
            "J2D1_a1_r23_D28": seed_records_with_cost_le_j(1, 23, 28, 2),
        },
    }
    for pw in boundary_payload_widths():
        if pw > MAX_PAYLOAD_WIDTH_BITS:
            continue
        table["j_field_bits_by_payload_width"][pw] = {
            "J3D1": j3d1_cost_for_payload_width(pw),
            "J2D1": lotus_cost_for_payload_width(pw, 2) if pw <= max_payload_width_for_j_bits(2) else None,
        }
        table["arity_record_bits_by_payload_width"][pw] = {
            arity: record_cost_for_payload_width(arity, pw) for arity in range(1, 6)
        }
        lo = (1 << pw) - 2 - 1
        hi = (1 << (pw + 1)) - 3 - 1
        table["seed_index_boundaries"][pw] = {"min_seed_index": max(0, lo), "max_seed_index": hi}
    return table


def self_checks() -> dict:
    checks = {}
    checks["arity_codeword_bits"] = {a: arity_cost(a) for a in (1, 2, 3, 4, 5)} | {"literal": arity_cost(0xFF)}
    assert checks["arity_codeword_bits"] == {1: 2, 2: 2, 3: 3, 4: 3, 5: 3, "literal": 3}
    assert record_cost(1, 0) == 7, "smallest arity-1 seed-index-0 record must be 7 bits"
    assert record_cost_for_payload_width_j(1, 1, 2) == 6, "J2D1 minimum record must be 6 bits"
    assert max_payload_width_for_j_bits(2) == 28
    assert max_payload_width_for_j_bits(3) == 508
    assert literal_run_header_bits(1, 3) == 3 + 5  # Lotus(1): j3 + tw1 + pw1
    assert literal_run_header_bits(1_000_000, 3) == 3 + 3 + 4 + 19  # value 1e6 -> pw 19, tw 4
    # Kraft completeness of the arity alphabet
    kraft = 2 * 2**-2 + 4 * 2**-3
    assert abs(kraft - 1.0) < 1e-15
    checks["kraft_sum"] = kraft
    # count consistency: payload_width_count_le matches the value ranges
    for pw in (1, 2, 3, 8, 16):
        assert payload_width_count_le(pw) == (1 << (pw + 1)) - 3
    checks["smallest_records"] = {
        "J3D1": record_cost(1, 0),
        "J2D1": record_cost_for_payload_width_j(1, 1, 2),
    }
    return checks


def main() -> None:
    report = {
        "self_checks": self_checks(),
        "rust_probe": validate_against_rust_probe(256, allow_missing_cargo=True),
        "pinned_costs": pinned_cost_table(),
        "reference_layout_golden_vectors": golden_vector_rows(),
        "payload_cap_analysis": payload_cap_analysis(),
        "reference_layout_note": (
            "3-bit jumpstarter stores tier_width-1 (tw in 1..8). The previous "
            "reference encoder stored tw directly and could not represent payload "
            "widths >= 254; all bit WIDTHS and costs are identical, so no prior "
            "result changes. Wire-layout pin vs the lotus crate remains open."
        ),
    }
    out = KERNEL_DIR / "cost_pin_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    rust = report["rust_probe"]
    print(f"rust probe: {rust.get('status')}")
    print(f"golden vectors: {len(report['reference_layout_golden_vectors'])} boundary rows + dense sweep OK")
    print(f"J3D1 min record {report['pinned_costs']['min_record_bits']['J3D1_arity1_seed0']} bits; "
          f"J2D1 min record {report['pinned_costs']['min_record_bits']['J2D1_arity1_seed0']} bits")
    print(f"caps: J2D1 {report['pinned_costs']['payload_caps']['J2D1']}, "
          f"J3D1 {report['pinned_costs']['payload_caps']['J3D1']}")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
