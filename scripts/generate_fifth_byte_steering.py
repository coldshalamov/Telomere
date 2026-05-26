#!/usr/bin/env python3
"""Probe residual-derived fifth-byte steering masks across held-out corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_composed_transform_probe
import generate_fifth_byte_residual
import generate_manifold_report
import generate_periodic_transform_probe
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESIDUAL_JSON = DOCS / "fifth_byte_residual.json"
STEERING_JSON = DOCS / "fifth_byte_steering.json"
STEERING_MD = DOCS / "FIFTH_BYTE_STEERING.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PERIOD = 4
DISPLAY_LIMIT = 24


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "fifth_byte_residual_sha256": sha256(RESIDUAL_JSON),
    }


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def supported_source(row: dict[str, Any]) -> bool:
    return row["family"] in {
        "transform-validation",
        "periodic-transform-probe",
        "composed-transform-probe",
    }


def mask_from_position_rows(rows: list[dict[str, Any]]) -> list[int]:
    mask = [0 for _ in range(PERIOD)]
    for row in rows:
        position = int(row["position_mod"]) % PERIOD
        mask[position] = int(row["value"]) & 0xFF
    return mask


def base_metadata_bytes(row: dict[str, Any]) -> int:
    if row["family"] == "transform-validation":
        transform = generate_fifth_byte_residual.validation_transform_by_name(row["transform"])
        return int(transform["metadata_bytes"])
    if row["family"] == "periodic-transform-probe":
        candidate = generate_fifth_byte_residual.periodic_candidate_by_name(row["transform"])
        return int(candidate["metadata_bytes"])
    if row["family"] == "composed-transform-probe":
        candidate = generate_fifth_byte_residual.composed_candidate_by_name(row["transform"])
        return int(candidate["metadata_bytes"])
    raise ValueError(f"unsupported source family: {row['family']}")


def candidate_manifest(residual: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in residual["results"]:
        if not supported_source(row):
            continue
        if row["prefix4_events"] < residual["robust_min_prefix4_events"]:
            continue
        if row["distinct_target_fifths"] < residual["robust_min_target_fifths"]:
            continue
        for operation, position_key, coverage_key in (
            ("xor-phase", "top_xor_by_position_mod4", "top_xor_residual_coverage"),
            ("add-phase", "top_add_by_position_mod4", "top_add_residual_coverage"),
        ):
            mask = mask_from_position_rows(row[position_key])
            if not any(mask):
                continue
            candidates.append(
                {
                    "name": (
                        f"{operation}-{slug(row['name'])}-"
                        f"{''.join(f'{byte:02x}' for byte in mask)}"
                    ),
                    "operation": operation,
                    "period": PERIOD,
                    "mask": mask,
                    "mask_hex": "".join(f"{byte:02x}" for byte in mask),
                    "source_case": row["name"],
                    "source_family": row["family"],
                    "source_corpus": row["corpus"],
                    "source_role": row["role"],
                    "source_transform": row["transform"],
                    "source_prefix4_events": row["prefix4_events"],
                    "source_distinct_target_fifths": row["distinct_target_fifths"],
                    "source_residual_coverage": row[coverage_key],
                    "base_metadata_bytes": base_metadata_bytes(row),
                    "correction_metadata_bytes": PERIOD + 1,
                    "metadata_bytes": base_metadata_bytes(row) + PERIOD + 1,
                }
            )
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        unique.setdefault(candidate["name"], candidate)
    return sorted(unique.values(), key=lambda item: item["name"])


def candidate_manifest_hash(candidates: list[dict[str, Any]]) -> str:
    payload = json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def apply_base(data: bytes, candidate: dict[str, Any]) -> bytes:
    family = candidate["source_family"]
    transform_name = candidate["source_transform"]
    if family == "transform-validation":
        transform = generate_fifth_byte_residual.validation_transform_by_name(transform_name)
        return generate_transform_probe.apply_probe(
            data,
            generate_transform_validation.probe_from_validation_transform(transform),
        )
    if family == "periodic-transform-probe":
        transform = generate_fifth_byte_residual.periodic_candidate_by_name(transform_name)
        return generate_periodic_transform_probe.apply_candidate(data, transform)
    if family == "composed-transform-probe":
        transform = generate_fifth_byte_residual.composed_candidate_by_name(transform_name)
        return generate_composed_transform_probe.apply_composed(data, transform)
    raise ValueError(f"unsupported source family: {family}")


def apply_steering(data: bytes, candidate: dict[str, Any]) -> bytes:
    mask = candidate["mask"]
    out = bytearray(len(data))
    if candidate["operation"] == "xor-phase":
        for idx, byte in enumerate(data):
            out[idx] = byte ^ mask[idx % PERIOD]
        return bytes(out)
    if candidate["operation"] == "add-phase":
        for idx, byte in enumerate(data):
            out[idx] = (byte + mask[idx % PERIOD]) & 0xFF
        return bytes(out)
    raise ValueError(candidate["operation"])


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    return (
        row["corrected_exact_hits"],
        row["exact_delta_vs_base"],
        row["prefix_ge_5_delta_vs_base"],
        row["corrected_prefix_ge_5"],
        row["prefix_ge_4_delta_vs_base"],
        row["corrected_prefix_ge_4"],
        row["candidate"],
    )


def analyze_candidate_on_corpus(
    candidate: dict[str, Any],
    corpus: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    source = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    base = apply_base(source, candidate)
    corrected = apply_steering(base, candidate)
    base_metrics = generate_transform_probe.analyze_bytes(base, prefix_sets)
    corrected_metrics = generate_transform_probe.analyze_bytes(corrected, prefix_sets)
    validation_kind = (
        "self-source"
        if corpus["corpus"] == candidate["source_corpus"]
        else "cross-corpus"
    )
    return {
        "name": f"{corpus['name']}::{candidate['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "validation_kind": validation_kind,
        "candidate": candidate["name"],
        "operation": candidate["operation"],
        "mask_hex": candidate["mask_hex"],
        "source_case": candidate["source_case"],
        "source_corpus": candidate["source_corpus"],
        "source_transform": candidate["source_transform"],
        "metadata_bytes": candidate["metadata_bytes"],
        "input_bytes": len(corrected),
        "input_sha256": hashlib.sha256(corrected).hexdigest(),
        "base_prefix_ge_4": base_metrics["prefix_ge_4_count"],
        "base_prefix_ge_5": base_metrics["prefix_ge_5_count"],
        "base_exact_hits": base_metrics["exact_span_hits"],
        "corrected_prefix_ge_3": corrected_metrics["prefix_ge_3_count"],
        "corrected_prefix_ge_4": corrected_metrics["prefix_ge_4_count"],
        "corrected_prefix_ge_5": corrected_metrics["prefix_ge_5_count"],
        "corrected_prefix_ge_6": corrected_metrics["prefix_ge_6_count"],
        "corrected_exact_hits": corrected_metrics["exact_span_hits"],
        "prefix_ge_4_delta_vs_base": (
            corrected_metrics["prefix_ge_4_count"] - base_metrics["prefix_ge_4_count"]
        ),
        "prefix_ge_5_delta_vs_base": (
            corrected_metrics["prefix_ge_5_count"] - base_metrics["prefix_ge_5_count"]
        ),
        "exact_delta_vs_base": (
            corrected_metrics["exact_span_hits"] - base_metrics["exact_span_hits"]
        ),
    }


def summarize(rows: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    heldout_cross = [
        row
        for row in rows
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "cross-corpus"
    ]
    self_rows = [row for row in rows if row["validation_kind"] == "self-source"]
    cross_prefix5_wins = [
        row for row in heldout_cross if row["prefix_ge_5_delta_vs_base"] > 0
    ]
    cross_prefix4_wins = [
        row for row in heldout_cross if row["prefix_ge_4_delta_vs_base"] > 0
    ]
    cross_exact_rows = [row for row in heldout_cross if row["corrected_exact_hits"] > 0]
    self_prefix5_wins = [row for row in self_rows if row["prefix_ge_5_delta_vs_base"] > 0]
    best_cross = max(heldout_cross, key=row_score, default=None)
    best_self = max(self_rows, key=row_score, default=None)
    conclusion = (
        "Residual-derived phase masks did not generalize into cross-corpus prefix>=5 "
        "uplift or exact seed-span hits."
        if not cross_prefix5_wins and not cross_exact_rows
        else "A residual-derived phase mask produced cross-corpus prefix>=5 uplift or exact hits and deserves follow-up."
    )
    return {
        "candidate_count": len(candidates),
        "validation_rows": len(rows),
        "heldout_cross_rows": len(heldout_cross),
        "cross_prefix4_win_rows": len(cross_prefix4_wins),
        "cross_prefix5_win_rows": len(cross_prefix5_wins),
        "cross_exact_hit_rows": len(cross_exact_rows),
        "self_prefix5_win_rows": len(self_prefix5_wins),
        "best_cross_case": best_cross["name"] if best_cross else None,
        "best_cross_prefix_ge_5": best_cross["corrected_prefix_ge_5"] if best_cross else 0,
        "best_cross_prefix_ge_5_delta": (
            best_cross["prefix_ge_5_delta_vs_base"] if best_cross else 0
        ),
        "best_cross_exact_hits": best_cross["corrected_exact_hits"] if best_cross else 0,
        "best_self_case": best_self["name"] if best_self else None,
        "best_self_prefix_ge_5_delta": (
            best_self["prefix_ge_5_delta_vs_base"] if best_self else 0
        ),
        "best_self_exact_hits": best_self["corrected_exact_hits"] if best_self else 0,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    residual = load_json(RESIDUAL_JSON)
    candidates = candidate_manifest(residual)
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    rows = [
        analyze_candidate_on_corpus(candidate, corpus, prefix_sets)
        for candidate in candidates
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
    ]
    return {
        "generated_by": "scripts/generate_fifth_byte_steering.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "candidate_manifest_sha256": candidate_manifest_hash(candidates),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "period": PERIOD,
        "display_limit": DISPLAY_LIMIT,
        "candidates": candidates,
        "results": rows,
        "summary": summarize(rows, candidates),
    }


def top_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(rows, key=row_score, reverse=True)[:limit]


def write_report(payload: dict[str, Any]) -> None:
    STEERING_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    heldout_cross = [
        row
        for row in payload["results"]
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "cross-corpus"
    ]
    lines = [
        "# Telomere Fifth-Byte Steering",
        "",
        "Generated by `scripts/generate_fifth_byte_steering.py` from the fifth-byte residual artifact.",
        "This diagnostic composes residual-derived period-4 correction masks after the source transform and validates them cross-corpus.",
        "It is not `.tlmr` format support and not a compression claim.",
        "",
        f"Candidate masks: `{summary['candidate_count']}`.",
        f"Held-out cross-corpus rows: `{summary['heldout_cross_rows']}`.",
        f"Cross-corpus prefix >=4 win rows: `{summary['cross_prefix4_win_rows']}`.",
        f"Cross-corpus prefix >=5 win rows: `{summary['cross_prefix5_win_rows']}`.",
        f"Cross-corpus exact-hit rows: `{summary['cross_exact_hit_rows']}`.",
        f"Self-source prefix >=5 win rows: `{summary['self_prefix5_win_rows']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best cross-corpus case: `{summary['best_cross_case']}`.",
        f"Best cross-corpus prefix>=5 delta: `{summary['best_cross_prefix_ge_5_delta']}`.",
        f"Best cross-corpus exact hits: `{summary['best_cross_exact_hits']}`.",
        "",
        "## Candidate Masks",
        "",
        "| candidate | operation | mask | source case | source prefix4 | residual coverage | metadata bytes |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            "| {name} | {operation} | {mask_hex} | {source_case} | "
            "{source_prefix4_events} | {source_residual_coverage:.2%} | "
            "{metadata_bytes} |".format(**candidate)
        )

    lines.extend(
        [
            "",
            "## Top Cross-Corpus Rows",
            "",
            "| case | source | operation | mask | base p5 | corrected p5 | p5 delta | exact hits |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(heldout_cross, payload["display_limit"]):
        lines.append(
            "| {name} | {source_case} | {operation} | {mask_hex} | "
            "{base_prefix_ge_5} | {corrected_prefix_ge_5} | "
            "{prefix_ge_5_delta_vs_base:+} | {corrected_exact_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The promotion gate is cross-corpus prefix >=5 uplift or exact seed-span hits; self-source movement is treated as overfit.",
            "- A residual correction may reduce prefix>=4 counts while chasing fifth-byte alignment, so prefix>=5 and exact rows are the decision signal.",
            "- Null results keep the queue pointed at stronger transform families rather than deeper blind search.",
        ]
    )
    STEERING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not STEERING_JSON.exists() or not STEERING_MD.exists():
        raise SystemExit("generated fifth-byte steering files are missing")
    payload = load_json(STEERING_JSON)
    if payload.get("generated_by") != "scripts/generate_fifth_byte_steering.py":
        raise SystemExit("fifth_byte_steering.json has wrong generated_by marker")
    residual = load_json(RESIDUAL_JSON)
    expected_candidates = candidate_manifest(residual)
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("fifth_byte_steering.json artifact hashes are stale")
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash(expected_candidates):
        raise SystemExit("fifth_byte_steering.json candidate manifest hash is stale")
    if payload.get("summary", {}).get("candidate_count") != len(expected_candidates):
        raise SystemExit("fifth_byte_steering.json candidate count is stale")
    text = STEERING_MD.read_text(encoding="utf-8")
    for phrase in (
        "cross-corpus",
        "prefix >=5",
        "not `.tlmr` format support",
        "self-source movement is treated as overfit",
    ):
        if phrase not in text:
            raise SystemExit(f"FIFTH_BYTE_STEERING.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated steering files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
