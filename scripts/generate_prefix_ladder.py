#!/usr/bin/env python3
"""Generate prefix-ladder diagnostics for Telomere transform leads."""

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
TRANSFORM_VALIDATION_JSON = DOCS / "transform_validation.json"
PERIODIC_PROBE_JSON = DOCS / "periodic_transform_probe.json"
COMPOSED_PROBE_JSON = DOCS / "composed_transform_probe.json"
MANIFOLD_JSON = DOCS / "manifold.json"
NEARMISS_JSON = DOCS / "nearmiss_forecast.json"
LADDER_JSON = DOCS / "prefix_ladder.json"
LADDER_MD = DOCS / "PREFIX_LADDER.md"

SPAN_LEN = 8
DISPLAY_LIMIT = 24


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ge_from_histogram(histogram: dict[str, int], threshold: int) -> int:
    return sum(count for prefix, count in histogram.items() if int(prefix) >= threshold)


def source_rows(
    transform_validation: dict[str, Any],
    periodic_probe: dict[str, Any],
    composed_probe: dict[str, Any],
    manifold: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in transform_validation["results"]:
        rows.append(
            normalize_row(
                {
                    "name": row["name"],
                    "family": "transform-validation",
                    "corpus": row["corpus"],
                    "role": row["corpus_role"],
                    "transform": row["transform"],
                    "input_bytes": row["input_bytes"],
                    "candidate_spans": row["candidate_spans"],
                    "prefix_ge_3_count": row["prefix_ge_3_count"],
                    "prefix_ge_4_count": row["prefix_ge_4_count"],
                    "prefix_ge_5_count": row["prefix_ge_5_count"],
                    "prefix_ge_6_count": row["prefix_ge_6_count"],
                    "exact_span_hits": row["exact_span_hits"],
                }
            )
        )
    for row in periodic_probe["validation_results"]:
        rows.append(
            normalize_row(
                {
                    "name": row["name"],
                    "family": "periodic-transform-probe",
                    "corpus": row["corpus"],
                    "role": row["corpus_role"],
                    "transform": row["transform"],
                    "input_bytes": row["input_bytes"],
                    "candidate_spans": row["candidate_spans"],
                    "prefix_ge_3_count": row["prefix_ge_3_count"],
                    "prefix_ge_4_count": row["prefix_ge_4_count"],
                    "prefix_ge_5_count": row["prefix_ge_5_count"],
                    "prefix_ge_6_count": row["prefix_ge_6_count"],
                    "exact_span_hits": row["exact_span_hits"],
                }
            )
        )
    for row in composed_probe["validation_results"]:
        rows.append(
            normalize_row(
                {
                    "name": row["name"],
                    "family": "composed-transform-probe",
                    "corpus": row["corpus"],
                    "role": row["corpus_role"],
                    "transform": row["transform"],
                    "input_bytes": row["input_bytes"],
                    "candidate_spans": row["candidate_spans"],
                    "prefix_ge_3_count": row["prefix_ge_3_count"],
                    "prefix_ge_4_count": row["prefix_ge_4_count"],
                    "prefix_ge_5_count": row["prefix_ge_5_count"],
                    "prefix_ge_6_count": row["prefix_ge_6_count"],
                    "exact_span_hits": row["exact_span_hits"],
                }
            )
        )
    for row in manifold["results"]:
        histogram = {str(k): int(v) for k, v in row["longest_prefix_histogram"].items()}
        rows.append(
            normalize_row(
                {
                    "name": row["name"],
                    "family": "manifold",
                    "corpus": row["source"],
                    "role": row["kind"],
                    "transform": row["transform"],
                    "input_bytes": row["input_bytes"],
                    "candidate_spans": row["candidate_spans"],
                    "prefix_ge_3_count": ge_from_histogram(histogram, 3),
                    "prefix_ge_4_count": ge_from_histogram(histogram, 4),
                    "prefix_ge_5_count": ge_from_histogram(histogram, 5),
                    "prefix_ge_6_count": ge_from_histogram(histogram, 6),
                    "exact_span_hits": row["exact_span_hits"],
                }
            )
        )
    return rows


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    prefix3 = int(row["prefix_ge_3_count"])
    prefix4 = int(row["prefix_ge_4_count"])
    prefix5 = int(row["prefix_ge_5_count"])
    prefix6 = int(row["prefix_ge_6_count"])
    exact = int(row["exact_span_hits"])
    return {
        **row,
        "prefix4_from_prefix3": ratio(prefix4, prefix3),
        "prefix5_from_prefix4": ratio(prefix5, prefix4),
        "prefix6_from_prefix5": ratio(prefix6, prefix5),
        "exact_from_prefix4": ratio(exact, prefix4),
        "expected_prefix5_from_prefix4_random_suffix": prefix4 / 256.0,
        "prefix4_multiplier_for_one_expected_prefix5": (256.0 / prefix4)
        if prefix4 > 0
        else None,
        "prefix4_multiplier_for_one_expected_exact": ((2 ** (8 * (SPAN_LEN - 4))) / prefix4)
        if prefix4 > 0
        else None,
    }


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def is_heldout_or_control(row: dict[str, Any]) -> bool:
    return row["role"] not in ("discovery", "planted-positive-control") and row["corpus"] != "planted-span8-full"


def sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    return (
        int(row["exact_span_hits"]),
        int(row["prefix_ge_6_count"]),
        int(row["prefix_ge_5_count"]),
        int(row["prefix_ge_4_count"]),
        int(row["prefix_ge_3_count"]),
        str(row["name"]),
    )


def build_report() -> dict[str, Any]:
    transform_validation = load_json(TRANSFORM_VALIDATION_JSON)
    periodic_probe = load_json(PERIODIC_PROBE_JSON)
    composed_probe = load_json(COMPOSED_PROBE_JSON)
    manifold = load_json(MANIFOLD_JSON)
    nearmiss = load_json(NEARMISS_JSON)
    rows = source_rows(transform_validation, periodic_probe, composed_probe, manifold)
    heldout_rows = [row for row in rows if is_heldout_or_control(row)]
    best_rows = sorted(heldout_rows, key=sort_key, reverse=True)[:DISPLAY_LIMIT]
    rows_with_prefix4 = [row for row in heldout_rows if row["prefix_ge_4_count"] > 0]
    rows_with_prefix5 = [row for row in heldout_rows if row["prefix_ge_5_count"] > 0]
    rows_with_exact = [row for row in heldout_rows if row["exact_span_hits"] > 0]
    best_prefix4 = max(heldout_rows, key=lambda row: row["prefix_ge_4_count"])
    conclusion = (
        "Held-out transform leads climb to prefix-4 but currently stall before prefix-5; "
        "the next research step should target the fifth byte, not deeper exact search."
        if not rows_with_prefix5 and not rows_with_exact
        else "At least one held-out row climbed beyond prefix-4 and deserves promotion review."
    )
    return {
        "generated_by": "scripts/generate_prefix_ladder.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_JSON),
            "periodic_transform_probe_sha256": sha256(PERIODIC_PROBE_JSON),
            "composed_transform_probe_sha256": sha256(COMPOSED_PROBE_JSON),
            "manifold_sha256": sha256(MANIFOLD_JSON),
            "nearmiss_forecast_sha256": sha256(NEARMISS_JSON),
        },
        "span_len": SPAN_LEN,
        "display_limit": DISPLAY_LIMIT,
        "row_count": len(rows),
        "heldout_row_count": len(heldout_rows),
        "best_rows": best_rows,
        "summary": {
            "heldout_rows_with_prefix4": len(rows_with_prefix4),
            "heldout_rows_with_prefix5": len(rows_with_prefix5),
            "heldout_rows_with_exact": len(rows_with_exact),
            "best_prefix4_case": best_prefix4["name"],
            "best_prefix4_count": best_prefix4["prefix_ge_4_count"],
            "best_prefix5_count": best_prefix4["prefix_ge_5_count"],
            "best_exact_hits": best_prefix4["exact_span_hits"],
            "best_expected_prefix5_from_prefix4_random_suffix": best_prefix4[
                "expected_prefix5_from_prefix4_random_suffix"
            ],
            "best_prefix4_multiplier_for_one_expected_prefix5": best_prefix4[
                "prefix4_multiplier_for_one_expected_prefix5"
            ],
            "best_prefix4_multiplier_for_one_expected_exact": best_prefix4[
                "prefix4_multiplier_for_one_expected_exact"
            ],
            "forecast_best_case": nearmiss["summary"]["best_non_planted_case"],
            "forecast_gib_for_one_expected_hit": nearmiss["summary"][
                "best_non_planted_gib_for_one_expected_hit"
            ],
            "conclusion": conclusion,
        },
    }


def format_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    if value == 0:
        return "0"
    if value < 0.001:
        return f"{value:.3e}"
    return f"{value:.3f}"


def format_float(value: float | None) -> str:
    if value is None:
        return "-"
    if math.isfinite(value) and value >= 1000:
        return f"{value:.3e}"
    return f"{value:.3f}"


def write_report(payload: dict[str, Any]) -> None:
    LADDER_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Prefix Ladder",
        "",
        "Generated by `scripts/generate_prefix_ladder.py` from transform validation, periodic probe, composed transform probe, manifold, and near-miss artifacts.",
        "This diagnostic explains where near misses stop; it is not a compression claim.",
        "",
        f"Span len: `{payload['span_len']}`.",
        f"Held-out/control rows inspected: `{payload['heldout_row_count']}`.",
        "",
        "## Summary",
        "",
        payload["summary"]["conclusion"],
        f"Held-out/control rows with prefix >=4: `{summary['heldout_rows_with_prefix4']}`.",
        f"Held-out/control rows with prefix >=5: `{summary['heldout_rows_with_prefix5']}`.",
        f"Held-out/control rows with exact hits: `{summary['heldout_rows_with_exact']}`.",
        f"Best prefix-4 case: `{summary['best_prefix4_case']}` with `{summary['best_prefix4_count']}` prefix>=4 spans.",
        f"Expected prefix>=5 in that case under random suffix: `{format_float(summary['best_expected_prefix5_from_prefix4_random_suffix'])}`.",
        f"Prefix-4 multiplier for one expected prefix>=5: `{format_float(summary['best_prefix4_multiplier_for_one_expected_prefix5'])}`.",
        f"Prefix-4 multiplier for one expected exact 8-byte hit: `{format_float(summary['best_prefix4_multiplier_for_one_expected_exact'])}`.",
        "",
        "## Top Held-Out Ladders",
        "",
        "| case | family | transform | prefix >=3 | prefix >=4 | prefix >=5 | exact | p4/p3 | p5/p4 | exact/p4 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["best_rows"]:
        lines.append(
            "| {name} | {family} | {transform} | {prefix_ge_3_count} | {prefix_ge_4_count} | "
            "{prefix_ge_5_count} | {exact_span_hits} | {p4p3} | {p5p4} | {exactp4} |".format(
                p4p3=format_ratio(row["prefix4_from_prefix3"]),
                p5p4=format_ratio(row["prefix5_from_prefix4"]),
                exactp4=format_ratio(row["exact_from_prefix4"]),
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Prefix-4 movement is real enough to track, but current held-out rows have no prefix-5 or exact events.",
            "- With the best current held-out prefix-4 count, even one prefix-5 event is still below expectation on this corpus size.",
            "- Deeper seed search is still gated; the next transform-search lane should target position-specific fifth-byte survival.",
            "- This artifact is a promotion gate companion for `docs/NEARMISS_FORECAST.md`.",
        ]
    )
    LADDER_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not LADDER_JSON.exists() or not LADDER_MD.exists():
        raise SystemExit("generated prefix ladder files are missing")
    payload = load_json(LADDER_JSON)
    if payload.get("generated_by") != "scripts/generate_prefix_ladder.py":
        raise SystemExit("prefix_ladder.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != build_report()["artifact_hashes"]:
        raise SystemExit("prefix ladder artifact hashes are stale")
    text = LADDER_MD.read_text(encoding="utf-8")
    for phrase in (
        "where near misses stop",
        "Top Held-Out Ladders",
        "prefix >=5",
        "position-specific fifth-byte survival",
    ):
        if phrase not in text:
            raise SystemExit(f"PREFIX_LADDER.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated prefix ladder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
