#!/usr/bin/env python3
"""Generate Telomere hit-probability and overhead theory report."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CORPUS_MATRIX_PATH = DOCS / "corpus_matrix.json"
DEEP_SWEEPS_PATH = DOCS / "deep_sweeps.json"
SWEEPS_PATH = DOCS / "sweeps.json"
THEORY_JSON = DOCS / "theory.json"
THEORY_MD = DOCS / "THEORY.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_count(max_seed_len: int) -> int:
    return sum(256**length for length in range(1, max_seed_len + 1))


def candidate_span_count(input_bytes: int, span_len: int, span_step: int) -> int:
    if input_bytes < span_len:
        return 0
    return 1 + (input_bytes - span_len) // span_step


def expected_hits(input_bytes: int, span_len: int, span_step: int, max_seed_len: int) -> float:
    spans = candidate_span_count(input_bytes, span_len, span_step)
    return spans * seed_count(max_seed_len) / float(2 ** (8 * span_len))


def seed_record_len(seed_len: int) -> int:
    # v2 seed span: tag + u16 span_len + u8 seed_len + seed bytes.
    return 4 + seed_len


def log2_seed_count(max_seed_len: int) -> float:
    return math.log2(seed_count(max_seed_len))


def profitability_frontier_row(max_seed_len: int) -> dict[str, Any]:
    minimum_profitable_span = seed_record_len(max_seed_len) + 1
    gap_bits = (8 * minimum_profitable_span) - log2_seed_count(max_seed_len)
    return {
        "max_seed_len": max_seed_len,
        "seed_count": seed_count(max_seed_len),
        "minimum_profitable_span_len": minimum_profitable_span,
        "gap_bits_at_minimum_profitable_span": round(gap_bits, 6),
        "spans_for_one_expected_hit": 2**gap_bits,
        "expected_hits_per_mib": expected_hits(
            1024 * 1024,
            minimum_profitable_span,
            1,
            max_seed_len,
        ),
        "expected_hits_per_gib": expected_hits(
            1024 * 1024 * 1024,
            minimum_profitable_span,
            1,
            max_seed_len,
        ),
    }


def row_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in rows:
        if row["name"] == name:
            return row
    raise KeyError(name)


def build_report() -> dict[str, Any]:
    corpus_matrix = load_json(CORPUS_MATRIX_PATH)
    deep_sweeps = load_json(DEEP_SWEEPS_PATH)
    sweeps = load_json(SWEEPS_PATH)

    corpus_rows = corpus_matrix["results"]
    structured_depth3 = row_by_name(
        deep_sweeps["results"],
        "structured-json-depth3-span8-step1-pass1",
    )
    seed_depth_rows = [
        row_by_name(sweeps["results"], "seed2-planted-depth1"),
        row_by_name(sweeps["results"], "seed2-planted-depth2"),
        row_by_name(deep_sweeps["results"], "seed3-planted-depth2"),
        row_by_name(deep_sweeps["results"], "seed3-planted-depth3"),
    ]

    seed_depth_table = [
        {
            "max_seed_len": depth,
            "seed_count": seed_count(depth),
            "log2_seed_count": round(log2_seed_count(depth), 6),
        }
        for depth in (1, 2, 3)
    ]

    overhead_table = [
        {
            "seed_len": seed_len,
            "record_len": seed_record_len(seed_len),
            "minimum_profitable_span_len": seed_record_len(seed_len) + 1,
            "savings_at_span8": 8 - seed_record_len(seed_len),
        }
        for seed_len in (1, 2, 3)
    ]

    structured_expectations = []
    for row in corpus_rows:
        expected = expected_hits(
            row["input_bytes"],
            row["max_span_len"],
            row["span_step"],
            row["seed_depth"],
        )
        structured_expectations.append(
            {
                "name": row["name"],
                "input_bytes": row["input_bytes"],
                "span_len": row["max_span_len"],
                "span_step": row["span_step"],
                "seed_depth": row["seed_depth"],
                "candidate_spans": candidate_span_count(
                    row["input_bytes"],
                    row["max_span_len"],
                    row["span_step"],
                ),
                "seed_count": seed_count(row["seed_depth"]),
                "expected_random_hits": expected,
                "observed_candidates": row["telemetry"]["candidate_count"],
                "observed_selected": row["telemetry"]["selected_count"],
            }
        )

    structured_depth3_expected = {
        "name": structured_depth3["name"],
        "input_bytes": structured_depth3["input_bytes"],
        "span_len": structured_depth3["span_len"],
        "span_step": structured_depth3["span_step"],
        "seed_depth": structured_depth3["seed_depth"],
        "candidate_spans": candidate_span_count(
            structured_depth3["input_bytes"],
            structured_depth3["span_len"],
            structured_depth3["span_step"],
        ),
        "seed_count": seed_count(structured_depth3["seed_depth"]),
        "expected_random_hits": expected_hits(
            structured_depth3["input_bytes"],
            structured_depth3["span_len"],
            structured_depth3["span_step"],
            structured_depth3["seed_depth"],
        ),
        "observed_candidates": structured_depth3["telemetry"]["candidate_count"],
        "observed_selected": structured_depth3["telemetry"]["selected_count"],
    }

    planted_controls = [
        {
            "name": row["name"],
            "seed_depth": row["seed_depth"],
            "delta_pct": row["delta_pct"],
            "observed_selected": row["telemetry"]["selected_count"],
            "interpretation": "planted/non-random control",
        }
        for row in seed_depth_rows
    ]

    return {
        "generated_by": "scripts/generate_theory_report.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "corpus_matrix_sha256": sha256(CORPUS_MATRIX_PATH),
            "deep_sweeps_sha256": sha256(DEEP_SWEEPS_PATH),
            "sweeps_sha256": sha256(SWEEPS_PATH),
        },
        "model": "expected_hits = candidate_spans * seed_count / 2^(8*span_len)",
        "seed_depth_table": seed_depth_table,
        "overhead_table": overhead_table,
        "minimum_profitable_frontier": [
            profitability_frontier_row(depth) for depth in range(1, 9)
        ],
        "structured_expectations": structured_expectations,
        "structured_depth3_expectation": structured_depth3_expected,
        "planted_controls": planted_controls,
        "conclusion": (
            "Current structured controls are consistent with near-zero random exact-prefix hit "
            "expectations; planted wins prove mechanism, not natural prevalence."
        ),
    }


def write_report(payload: dict[str, Any]) -> None:
    THEORY_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Telomere Theory Report",
        "",
        "Generated by `scripts/generate_theory_report.py` from checked-in artifacts.",
        "",
        f"Model: `{payload['model']}`.",
        "",
        "## Seed Space",
        "",
        "| max seed len | seed count | log2(seed count) |",
        "| ---: | ---: | ---: |",
    ]
    for row in payload["seed_depth_table"]:
        lines.append(
            "| {max_seed_len} | {seed_count} | {log2_seed_count} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## v2 Seed-Span Overhead",
            "",
            "| seed len | record len | minimum profitable span | savings at span 8 |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["overhead_table"]:
        lines.append(
            "| {seed_len} | {record_len} | {minimum_profitable_span_len} | {savings_at_span8} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Minimum Profitable Frontier",
            "",
            "At the minimum span that can beat the v2 seed-span record, deeper seed search and longer spans mostly cancel each other for random-like bytes. The fixed four-byte record overhead leaves about a 40-bit gap, so one expected random exact-prefix hit needs roughly a trillion candidate spans.",
            "",
            "| max seed len | minimum profitable span | gap bits | spans for one expected hit | expected hits per MiB | expected hits per GiB |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["minimum_profitable_frontier"]:
        lines.append(
            "| {max_seed_len} | {minimum_profitable_span_len} | {gap_bits_at_minimum_profitable_span:.2f} | {spans_for_one_expected_hit:.3e} | {expected_hits_per_mib:.3e} | {expected_hits_per_gib:.3e} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Structured Expectations",
            "",
            "| case | seed depth | spans | seeds | expected random hits | observed candidates | selected |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["structured_expectations"]:
        lines.append(
            "| {name} | {seed_depth} | {candidate_spans} | {seed_count} | {expected_random_hits:.3e} | {observed_candidates} | {observed_selected} |".format(
                **row
            )
        )
    row = payload["structured_depth3_expectation"]
    lines.append(
        "| {name} | {seed_depth} | {candidate_spans} | {seed_count} | {expected_random_hits:.3e} | {observed_candidates} | {observed_selected} |".format(
            **row
        )
    )

    lines.extend(
        [
            "",
            "## Planted Controls",
            "",
            "| case | seed depth | delta | selected | interpretation |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["planted_controls"]:
        lines.append(
            "| {name} | {seed_depth} | {delta_pct:+.2f}% | {observed_selected} | {interpretation} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            payload["conclusion"],
            "",
            "The practical implication is stark: for 8-byte exact-prefix spans, seed-depth 3 still samples far too little of the 64-bit target space to expect natural random-like hits in small structured corpora. Larger compute helps planted controls, but raw structured wins need either much deeper search, different span targets, transforms that create seed-addressable spans, or a different mechanism.",
            "",
            "The arity/depth implication is sharper: if the system grows seed depth and span length together just to stay profitable, random-like hit probability does not automatically improve. A scalable win needs non-random alignment with the Lotus seed-output manifold, metadata amortization across bundles, reversible transforms/dictionaries that are explicitly recorded by a future format, or hardware acceleration aimed at a corpus where such bias exists.",
        ]
    )
    THEORY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not THEORY_JSON.exists() or not THEORY_MD.exists():
        raise SystemExit("generated theory files are missing")
    payload = load_json(THEORY_JSON)
    if payload.get("generated_by") != "scripts/generate_theory_report.py":
        raise SystemExit("theory.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != build_report()["artifact_hashes"]:
        raise SystemExit("theory artifact hashes are stale")
    text = THEORY_MD.read_text(encoding="utf-8")
    for phrase in (
        "expected_hits = candidate_spans",
        "Minimum Profitable Frontier",
        "Structured Expectations",
        "Planted Controls",
        "near-zero random exact-prefix hit",
    ):
        if phrase not in text:
            raise SystemExit(f"THEORY.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated theory report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
