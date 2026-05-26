#!/usr/bin/env python3
"""Diagnose fifth-byte residuals for Telomere prefix-4 near misses."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_composed_transform_probe
import generate_manifold_report
import generate_periodic_transform_probe
import generate_prefix_ladder
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PREFIX_LADDER_JSON = DOCS / "prefix_ladder.json"
RESIDUAL_JSON = DOCS / "fifth_byte_residual.json"
RESIDUAL_MD = DOCS / "FIFTH_BYTE_RESIDUAL.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
DISPLAY_LIMIT = 16
ROBUST_MIN_PREFIX4_EVENTS = 16
ROBUST_MIN_TARGET_FIFTHS = 4


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "prefix_ladder_sha256": sha256(PREFIX_LADDER_JSON),
    }


def seed_fifth_byte_map(max_seed_len: int) -> tuple[dict[bytes, Counter[int]], set[bytes]]:
    prefix4_to_fifth: dict[bytes, Counter[int]] = defaultdict(Counter)
    prefix5_set: set[bytes] = set()
    for seed in generate_manifold_report.iter_seed_bytes(max_seed_len):
        digest = hashlib.sha256(seed).digest()[:SPAN_LEN]
        prefix4_to_fifth[digest[:4]][digest[4]] += 1
        prefix5_set.add(digest[:5])
    return dict(prefix4_to_fifth), prefix5_set


def validation_transform_by_name(name: str) -> dict[str, Any]:
    for transform in generate_transform_validation.TRANSFORM_VALIDATION_MATRIX:
        if transform["name"] == name:
            return transform
    raise KeyError(name)


def periodic_candidate_by_name(name: str) -> dict[str, Any]:
    for candidate in generate_periodic_transform_probe.candidate_manifest():
        if candidate["name"] == name:
            return candidate
    raise KeyError(name)


def composed_candidate_by_name(name: str) -> dict[str, Any]:
    for candidate in generate_composed_transform_probe.candidate_manifest():
        if candidate["name"] == name:
            return candidate
    raise KeyError(name)


def transformed_bytes_for_row(row: dict[str, Any]) -> bytes:
    family = row["family"]
    if family == "transform-validation":
        transform = validation_transform_by_name(row["transform"])
        source = generate_corpus_matrix.corpus_bytes(row["corpus"])
        return generate_transform_probe.apply_probe(
            source,
            generate_transform_validation.probe_from_validation_transform(transform),
        )
    if family == "periodic-transform-probe":
        candidate = periodic_candidate_by_name(row["transform"])
        source = generate_corpus_matrix.corpus_bytes(row["corpus"])
        return generate_periodic_transform_probe.apply_candidate(source, candidate)
    if family == "composed-transform-probe":
        candidate = composed_candidate_by_name(row["transform"])
        source = generate_corpus_matrix.corpus_bytes(row["corpus"])
        return generate_composed_transform_probe.apply_composed(source, candidate)
    if family == "manifold":
        for case in generate_manifold_report.MANIFOLD_CASES:
            if case["name"] == row["name"]:
                data, _ = generate_manifold_report.transformed_bytes(case)
                return data
    raise ValueError(f"unsupported row family: {family}")


def top_counter(counter: Counter[int], limit: int = 8) -> list[dict[str, Any]]:
    return [
        {"value": value, "value_hex": f"{value:02x}", "count": count}
        for value, count in counter.most_common(limit)
    ]


def top_position_residuals(
    counters: dict[int, Counter[int]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows = []
    for position, counter in sorted(counters.items()):
        if not counter:
            continue
        value, count = counter.most_common(1)[0]
        rows.append(
            {
                "position_mod": position,
                "value": value,
                "value_hex": f"{value:02x}",
                "count": count,
            }
        )
    return rows[:limit]


def analyze_row(
    row: dict[str, Any],
    prefix4_to_fifth: dict[bytes, Counter[int]],
    prefix5_set: set[bytes],
) -> dict[str, Any]:
    data = transformed_bytes_for_row(row)
    xor_residuals: Counter[int] = Counter()
    add_residuals: Counter[int] = Counter()
    target_fifths: Counter[int] = Counter()
    expected_fifths: Counter[int] = Counter()
    xor_by_mod4: dict[int, Counter[int]] = defaultdict(Counter)
    add_by_mod4: dict[int, Counter[int]] = defaultdict(Counter)
    prefix4_events = 0
    prefix5_events = 0
    residual_samples = 0

    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        expected_counter = prefix4_to_fifth.get(span[:4])
        if expected_counter is None:
            continue
        prefix4_events += 1
        if span[:5] in prefix5_set:
            prefix5_events += 1
            continue
        target_fifth = span[4]
        target_fifths[target_fifth] += 1
        position_mod4 = (start + 4) % 4
        for expected_fifth, weight in expected_counter.items():
            residual_samples += weight
            expected_fifths[expected_fifth] += weight
            xor_value = target_fifth ^ expected_fifth
            add_value = (expected_fifth - target_fifth) & 0xFF
            xor_residuals[xor_value] += weight
            add_residuals[add_value] += weight
            xor_by_mod4[position_mod4][xor_value] += weight
            add_by_mod4[position_mod4][add_value] += weight

    top_xor = xor_residuals.most_common(1)[0] if xor_residuals else (None, 0)
    top_add = add_residuals.most_common(1)[0] if add_residuals else (None, 0)
    return {
        "name": row["name"],
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "transform": row["transform"],
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "candidate_spans": generate_manifold_report.candidate_span_count(
            len(data),
            SPAN_LEN,
            SPAN_STEP,
        ),
        "prefix4_events": prefix4_events,
        "prefix5_events": prefix5_events,
        "fifth_byte_misses": prefix4_events - prefix5_events,
        "residual_samples": residual_samples,
        "distinct_target_fifths": len(target_fifths),
        "distinct_expected_fifths": len(expected_fifths),
        "top_xor_residual": top_xor[0],
        "top_xor_residual_hex": f"{top_xor[0]:02x}" if top_xor[0] is not None else None,
        "top_xor_residual_count": top_xor[1],
        "top_xor_residual_coverage": (top_xor[1] / residual_samples)
        if residual_samples
        else 0.0,
        "top_add_residual": top_add[0],
        "top_add_residual_hex": f"{top_add[0]:02x}" if top_add[0] is not None else None,
        "top_add_residual_count": top_add[1],
        "top_add_residual_coverage": (top_add[1] / residual_samples)
        if residual_samples
        else 0.0,
        "top_xor_residuals": top_counter(xor_residuals),
        "top_add_residuals": top_counter(add_residuals),
        "top_target_fifths": top_counter(target_fifths),
        "top_expected_fifths": top_counter(expected_fifths),
        "top_xor_by_position_mod4": top_position_residuals(xor_by_mod4),
        "top_add_by_position_mod4": top_position_residuals(add_by_mod4),
    }


def selected_rows(prefix_ladder: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in prefix_ladder["best_rows"]
        if row["prefix_ge_4_count"] > 0 and row["role"] != "discovery"
    ][:DISPLAY_LIMIT]


def build_report() -> dict[str, Any]:
    prefix_ladder = load_json(PREFIX_LADDER_JSON)
    prefix4_to_fifth, prefix5_set = seed_fifth_byte_map(MAX_SEED_LEN)
    rows = [
        analyze_row(row, prefix4_to_fifth, prefix5_set)
        for row in selected_rows(prefix_ladder)
    ]
    best_xor = max(rows, key=lambda row: row["top_xor_residual_coverage"], default=None)
    best_add = max(rows, key=lambda row: row["top_add_residual_coverage"], default=None)
    robust_rows = [
        row
        for row in rows
        if row["prefix4_events"] >= ROBUST_MIN_PREFIX4_EVENTS
        and row["distinct_target_fifths"] >= ROBUST_MIN_TARGET_FIFTHS
    ]
    robust_best_xor = max(
        robust_rows,
        key=lambda row: row["top_xor_residual_coverage"],
        default=None,
    )
    robust_best_add = max(
        robust_rows,
        key=lambda row: row["top_add_residual_coverage"],
        default=None,
    )
    total_prefix4 = sum(row["prefix4_events"] for row in rows)
    total_prefix5 = sum(row["prefix5_events"] for row in rows)
    robust_best_coverage = max(
        robust_best_xor["top_xor_residual_coverage"] if robust_best_xor else 0.0,
        robust_best_add["top_add_residual_coverage"] if robust_best_add else 0.0,
    )
    conclusion = (
        "Robust prefix-4 near misses do not share a dominant fifth-byte residual; "
        "simple one-byte residual correction is not yet a credible promotion path."
        if robust_best_coverage < 0.5
        else "A robust fifth-byte residual concentration exists and should be tested as a transform lead."
    )
    return {
        "generated_by": "scripts/generate_fifth_byte_residual.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "selected_row_limit": DISPLAY_LIMIT,
        "robust_min_prefix4_events": ROBUST_MIN_PREFIX4_EVENTS,
        "robust_min_target_fifths": ROBUST_MIN_TARGET_FIFTHS,
        "seed_prefix4_count": len(prefix4_to_fifth),
        "seed_prefix5_count": len(prefix5_set),
        "results": rows,
        "summary": {
            "rows_analyzed": len(rows),
            "robust_rows_analyzed": len(robust_rows),
            "total_prefix4_events": total_prefix4,
            "total_prefix5_events": total_prefix5,
            "best_xor_case": best_xor["name"] if best_xor else None,
            "best_xor_residual_hex": best_xor["top_xor_residual_hex"] if best_xor else None,
            "best_xor_residual_coverage": best_xor["top_xor_residual_coverage"]
            if best_xor
            else 0.0,
            "best_add_case": best_add["name"] if best_add else None,
            "best_add_residual_hex": best_add["top_add_residual_hex"] if best_add else None,
            "best_add_residual_coverage": best_add["top_add_residual_coverage"]
            if best_add
            else 0.0,
            "robust_best_xor_case": robust_best_xor["name"] if robust_best_xor else None,
            "robust_best_xor_residual_hex": robust_best_xor["top_xor_residual_hex"]
            if robust_best_xor
            else None,
            "robust_best_xor_residual_coverage": robust_best_xor[
                "top_xor_residual_coverage"
            ]
            if robust_best_xor
            else 0.0,
            "robust_best_add_case": robust_best_add["name"] if robust_best_add else None,
            "robust_best_add_residual_hex": robust_best_add["top_add_residual_hex"]
            if robust_best_add
            else None,
            "robust_best_add_residual_coverage": robust_best_add[
                "top_add_residual_coverage"
            ]
            if robust_best_add
            else 0.0,
            "conclusion": conclusion,
        },
    }


def pct(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def write_report(payload: dict[str, Any]) -> None:
    RESIDUAL_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Fifth-Byte Residual",
        "",
        "Generated by `scripts/generate_fifth_byte_residual.py` from the prefix-ladder artifact.",
        "This diagnostic inspects prefix-4 near misses and compares their fifth byte against actual depth-2 SHA-256 seed outputs.",
        "",
        f"Rows analyzed: `{summary['rows_analyzed']}`.",
        f"Robust rows analyzed: `{summary['robust_rows_analyzed']}`.",
        f"Total prefix-4 events: `{summary['total_prefix4_events']}`.",
        f"Total prefix-5 events: `{summary['total_prefix5_events']}`.",
        f"Seed prefix-4 count: `{payload['seed_prefix4_count']}`.",
        f"Seed prefix-5 count: `{payload['seed_prefix5_count']}`.",
        f"Robust row threshold: `prefix4 >= {payload['robust_min_prefix4_events']}` and `distinct target fifths >= {payload['robust_min_target_fifths']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best raw XOR residual case: `{summary['best_xor_case']}` residual `0x{summary['best_xor_residual_hex']}` covering `{pct(summary['best_xor_residual_coverage'])}`.",
        f"Best raw add residual case: `{summary['best_add_case']}` residual `0x{summary['best_add_residual_hex']}` covering `{pct(summary['best_add_residual_coverage'])}`.",
        f"Best robust XOR residual case: `{summary['robust_best_xor_case']}` residual `0x{summary['robust_best_xor_residual_hex']}` covering `{pct(summary['robust_best_xor_residual_coverage'])}`.",
        f"Best robust add residual case: `{summary['robust_best_add_case']}` residual `0x{summary['robust_best_add_residual_hex']}` covering `{pct(summary['robust_best_add_residual_coverage'])}`.",
        "",
        "## Residual Matrix",
        "",
        "| case | transform | prefix4 | prefix5 | target fifths | expected fifths | top xor | xor coverage | top add | add coverage |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |",
    ]
    for row in payload["results"]:
        lines.append(
            "| {name} | {transform} | {prefix4_events} | {prefix5_events} | "
            "{distinct_target_fifths} | {distinct_expected_fifths} | 0x{top_xor_residual_hex} | {xor_cov} | "
            "0x{top_add_residual_hex} | {add_cov} |".format(
                xor_cov=pct(row["top_xor_residual_coverage"]),
                add_cov=pct(row["top_add_residual_coverage"]),
                **row,
            )
        )

    lines.extend(
        [
            "",
            "## Top Residuals",
            "",
        ]
    )
    for row in payload["results"][:8]:
        xor_values = ", ".join(
            f"0x{item['value_hex']}:{item['count']}" for item in row["top_xor_residuals"][:4]
        )
        add_values = ", ".join(
            f"0x{item['value_hex']}:{item['count']}" for item in row["top_add_residuals"][:4]
        )
        lines.append(f"- `{row['name']}` XOR [{xor_values}] ADD [{add_values}]")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A strong residual concentration would suggest a small reversible transform might move prefix-4 hits to prefix-5.",
            "- Low residual coverage means the fifth-byte failures look dispersed rather than correctable by a simple one-byte mask.",
            "- This artifact is intentionally diagnostic; it does not add `.tlmr` transform metadata or claim compression.",
        ]
    )
    RESIDUAL_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not RESIDUAL_JSON.exists() or not RESIDUAL_MD.exists():
        raise SystemExit("generated fifth-byte residual files are missing")
    payload = load_json(RESIDUAL_JSON)
    if payload.get("generated_by") != "scripts/generate_fifth_byte_residual.py":
        raise SystemExit("fifth_byte_residual.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("fifth-byte residual artifact hashes are stale")
    text = RESIDUAL_MD.read_text(encoding="utf-8")
    for phrase in (
        "prefix-4 near misses",
        "Residual Matrix",
        "simple one-byte mask",
        "does not add `.tlmr` transform metadata",
    ):
        if phrase not in text:
            raise SystemExit(f"FIFTH_BYTE_RESIDUAL.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated fifth-byte residual report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
