#!/usr/bin/env python3
"""Forecast exact-hit odds from observed Telomere prefix near misses."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TRANSFORM_VALIDATION_JSON = DOCS / "transform_validation.json"
PERIODIC_PROBE_JSON = DOCS / "periodic_transform_probe.json"
COMPOSED_PROBE_JSON = DOCS / "composed_transform_probe.json"
MANIFOLD_JSON = DOCS / "manifold.json"
FORECAST_JSON = DOCS / "nearmiss_forecast.json"
FORECAST_MD = DOCS / "NEARMISS_FORECAST.md"

SPAN_LEN = 8
PREFIX_LENGTHS = (3, 4, 5, 6)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_forecast_from_prefix(prefix_count: int, prefix_len: int) -> float:
    remaining_bits = 8 * (SPAN_LEN - prefix_len)
    return prefix_count / float(2**remaining_bits)


def scale_bytes_for_one_expected_hit(input_bytes: int, prefix_count: int, prefix_len: int) -> float | None:
    if prefix_count <= 0 or input_bytes <= 0:
        return None
    expected = exact_forecast_from_prefix(prefix_count, prefix_len)
    if expected <= 0:
        return None
    return input_bytes / expected


def source_rows(
    transform_validation: dict[str, Any],
    periodic_probe: dict[str, Any],
    composed_probe: dict[str, Any],
    manifold: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in transform_validation["results"]:
        rows.append(
            {
                "name": row["name"],
                "family": "transform-validation",
                "corpus": row["corpus"],
                "role": row["corpus_role"],
                "transform": row["transform"],
                "input_bytes": row["input_bytes"],
                "prefix_ge_3_count": row["prefix_ge_3_count"],
                "prefix_ge_4_count": row["prefix_ge_4_count"],
                "prefix_ge_5_count": row["prefix_ge_5_count"],
                "prefix_ge_6_count": row["prefix_ge_6_count"],
                "exact_span_hits": row["exact_span_hits"],
            }
        )
    for row in periodic_probe["validation_results"]:
        rows.append(
            {
                "name": row["name"],
                "family": "periodic-transform-probe",
                "corpus": row["corpus"],
                "role": row["corpus_role"],
                "transform": row["transform"],
                "input_bytes": row["input_bytes"],
                "prefix_ge_3_count": row["prefix_ge_3_count"],
                "prefix_ge_4_count": row["prefix_ge_4_count"],
                "prefix_ge_5_count": row["prefix_ge_5_count"],
                "prefix_ge_6_count": row["prefix_ge_6_count"],
                "exact_span_hits": row["exact_span_hits"],
            }
        )
    for row in composed_probe["validation_results"]:
        rows.append(
            {
                "name": row["name"],
                "family": "composed-transform-probe",
                "corpus": row["corpus"],
                "role": row["corpus_role"],
                "transform": row["transform"],
                "input_bytes": row["input_bytes"],
                "prefix_ge_3_count": row["prefix_ge_3_count"],
                "prefix_ge_4_count": row["prefix_ge_4_count"],
                "prefix_ge_5_count": row["prefix_ge_5_count"],
                "prefix_ge_6_count": row["prefix_ge_6_count"],
                "exact_span_hits": row["exact_span_hits"],
            }
        )
    for row in manifold["results"]:
        rows.append(
            {
                "name": row["name"],
                "family": "manifold",
                "corpus": row["source"],
                "role": row["kind"],
                "transform": row["transform"],
                "input_bytes": row["input_bytes"],
                "prefix_ge_3_count": row.get("prefix_ge_3_count", 0),
                "prefix_ge_4_count": row["prefix_ge_4_count"],
                "prefix_ge_5_count": sum(
                    int(count)
                    for prefix, count in row["longest_prefix_histogram"].items()
                    if int(prefix) >= 5
                ),
                "prefix_ge_6_count": row["prefix_ge_6_count"],
                "exact_span_hits": row["exact_span_hits"],
            }
        )
    return rows


def forecast_row(row: dict[str, Any]) -> dict[str, Any]:
    forecasts = {}
    for prefix_len in PREFIX_LENGTHS:
        count = row[f"prefix_ge_{prefix_len}_count"]
        expected = exact_forecast_from_prefix(count, prefix_len)
        bytes_for_one = scale_bytes_for_one_expected_hit(
            row["input_bytes"],
            count,
            prefix_len,
        )
        forecasts[str(prefix_len)] = {
            "prefix_count": count,
            "expected_exact_hits_in_observed_bytes": expected,
            "bytes_for_one_expected_exact_hit": bytes_for_one,
            "gib_for_one_expected_exact_hit": (bytes_for_one / (1024**3))
            if bytes_for_one is not None
            else None,
        }
    best_prefix_len = max(
        PREFIX_LENGTHS,
        key=lambda prefix_len: (
            forecasts[str(prefix_len)]["expected_exact_hits_in_observed_bytes"],
            prefix_len,
        ),
    )
    return {
        **row,
        "forecasts": forecasts,
        "best_forecast_prefix_len": best_prefix_len,
        "best_expected_exact_hits": forecasts[str(best_prefix_len)][
            "expected_exact_hits_in_observed_bytes"
        ],
        "best_gib_for_one_expected_exact_hit": forecasts[str(best_prefix_len)][
            "gib_for_one_expected_exact_hit"
        ],
    }


def build_report() -> dict[str, Any]:
    transform_validation = load_json(TRANSFORM_VALIDATION_JSON)
    periodic_probe = load_json(PERIODIC_PROBE_JSON)
    composed_probe = load_json(COMPOSED_PROBE_JSON)
    manifold = load_json(MANIFOLD_JSON)
    rows = [
        forecast_row(row)
        for row in source_rows(transform_validation, periodic_probe, composed_probe, manifold)
    ]
    non_planted = [
        row
        for row in rows
        if is_non_planted(row)
        and row["corpus"] != "planted-span8-full"
    ]
    best_non_planted = max(
        non_planted,
        key=lambda row: (
            row["best_expected_exact_hits"],
            row["exact_span_hits"],
            row["prefix_ge_4_count"],
            row["prefix_ge_3_count"],
        ),
    )
    return {
        "generated_by": "scripts/generate_nearmiss_forecast.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_JSON),
            "periodic_transform_probe_sha256": sha256(PERIODIC_PROBE_JSON),
            "composed_transform_probe_sha256": sha256(COMPOSED_PROBE_JSON),
            "manifold_sha256": sha256(MANIFOLD_JSON),
        },
        "model": "expected_exact_hits = prefix_count / 2^(8*(8-prefix_len))",
        "span_len": SPAN_LEN,
        "prefix_lengths": list(PREFIX_LENGTHS),
        "results": rows,
        "summary": {
            "best_non_planted_case": best_non_planted["name"],
            "best_non_planted_prefix_len": best_non_planted["best_forecast_prefix_len"],
            "best_non_planted_expected_exact_hits": best_non_planted[
                "best_expected_exact_hits"
            ],
            "best_non_planted_gib_for_one_expected_hit": best_non_planted[
                "best_gib_for_one_expected_exact_hit"
            ],
            "best_non_planted_exact_hits": best_non_planted["exact_span_hits"],
            "conclusion": (
                "Observed non-planted near misses remain far from one expected exact "
                "8-byte seed-span hit under the random-suffix model."
            ),
        },
    }


def is_non_planted(row: dict[str, Any]) -> bool:
    return (
        row["role"] not in ("planted-positive-control", "discovery")
        and row["corpus"] != "planted-span8-full"
    )


def format_gib(value: float | None) -> str:
    if value is None:
        return "-"
    if value >= 1000:
        return f"{value:.3e}"
    return f"{value:.3f}"


def write_report(payload: dict[str, Any]) -> None:
    FORECAST_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Near-Miss Forecast",
        "",
        "Generated by `scripts/generate_nearmiss_forecast.py`.",
        "This is a random-suffix forecast from observed prefix near misses, not a compression claim.",
        "",
        f"Model: `{payload['model']}`.",
        f"Span len: `{payload['span_len']}`.",
        "",
        "## Best Non-Planted Forecast",
        "",
        f"Case: `{payload['summary']['best_non_planted_case']}`.",
        f"Best prefix length: `{payload['summary']['best_non_planted_prefix_len']}`.",
        f"Expected exact hits in observed bytes: `{payload['summary']['best_non_planted_expected_exact_hits']:.3e}`.",
        f"GiB for one expected exact hit: `{format_gib(payload['summary']['best_non_planted_gib_for_one_expected_hit'])}`.",
        f"Observed exact hits: `{payload['summary']['best_non_planted_exact_hits']}`.",
        "",
        "## Forecast Matrix",
        "",
        "This table excludes planted positive controls and discovery-only rows because neither is a held-out promotion gate.",
        "",
        "| case | role | transform | bytes | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | best prefix | expected exact | GiB for one exact | observed exact |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    display_rows = sorted(
        [row for row in payload["results"] if is_non_planted(row)],
        key=lambda row: (
            row["best_expected_exact_hits"],
            row["exact_span_hits"],
            row["prefix_ge_4_count"],
            row["prefix_ge_3_count"],
        ),
        reverse=True,
    )[:24]
    for row in display_rows:
        lines.append(
            "| {name} | {role} | {transform} | {input_bytes} | {prefix_ge_3_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{best_forecast_prefix_len} | {best_expected_exact_hits:.3e} | {gib} | "
            "{exact_span_hits} |".format(
                gib=format_gib(row["best_gib_for_one_expected_exact_hit"]),
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            payload["summary"]["conclusion"],
            "",
            "- Prefix-3 and prefix-4 movement is useful for transform design only if later experiments show a repeatable ladder toward longer prefixes.",
            "- Exact 8-byte seed-span hits remain the compression-relevant event.",
            "- If the best case still needs many GiB for one expected exact hit, deeper search should be gated behind stronger corpus evidence or a better transform family.",
        ]
    )
    FORECAST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not FORECAST_JSON.exists() or not FORECAST_MD.exists():
        raise SystemExit("generated near-miss forecast files are missing")
    payload = load_json(FORECAST_JSON)
    if payload.get("generated_by") != "scripts/generate_nearmiss_forecast.py":
        raise SystemExit("nearmiss_forecast.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != build_report()["artifact_hashes"]:
        raise SystemExit("nearmiss forecast artifact hashes are stale")
    text = FORECAST_MD.read_text(encoding="utf-8")
    for phrase in (
        "random-suffix forecast",
        "Best Non-Planted Forecast",
        "excludes planted positive controls",
        "GiB for one expected exact hit",
        "Exact 8-byte seed-span hits remain",
    ):
        if phrase not in text:
            raise SystemExit(f"NEARMISS_FORECAST.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated near-miss forecast")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
