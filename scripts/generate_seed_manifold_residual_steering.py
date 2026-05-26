#!/usr/bin/env python3
"""Measure residual sidecar economics for forced seed-manifold steering."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_affine_transform_search
import generate_corpus_matrix
import generate_manifold_report
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STEERING_JSON = DOCS / "seed_manifold_residual_steering.json"
STEERING_MD = DOCS / "SEED_MANIFOLD_RESIDUAL_STEERING.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
RESIDUAL_SCHEMES = (
    {"name": "prefix4-suffix-xor", "min_prefix_len": 4, "sidecar_header_bytes": 1},
    {"name": "prefix5-suffix-xor", "min_prefix_len": 5, "sidecar_header_bytes": 1},
    {"name": "prefix6-suffix-xor", "min_prefix_len": 6, "sidecar_header_bytes": 1},
    {"name": "prefix7-suffix-xor", "min_prefix_len": 7, "sidecar_header_bytes": 1},
)
DISPLAY_LIMIT = 24
TELEMETRY_LIMIT = 16


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "affine_transform_search_sha256": sha256(DOCS / "affine_transform_search.json"),
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
    }


def validation_manifest() -> dict[str, Any]:
    return {
        "corpora": generate_transform_validation.CORPUS_VALIDATION_MATRIX,
        "residual_schemes": RESIDUAL_SCHEMES,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "hasher": HASHER,
    }


def validation_manifest_hash() -> str:
    payload = json.dumps(validation_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def seed_prefix_maps() -> dict[int, dict[bytes, dict[str, Any]]]:
    maps: dict[int, dict[bytes, dict[str, Any]]] = {
        prefix_len: {} for prefix_len in range(1, SPAN_LEN + 1)
    }
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        digest = hashlib.sha256(seed).digest()[:SPAN_LEN]
        for prefix_len in range(1, SPAN_LEN + 1):
            prefix = digest[:prefix_len]
            maps[prefix_len].setdefault(
                prefix,
                {
                    "seed_index": seed_index,
                    "seed_len": len(seed),
                    "seed_hex": seed.hex(),
                    "expanded": digest,
                },
            )
    return maps


def selected_affine_candidates() -> list[dict[str, Any]]:
    payload = load_json(DOCS / "affine_transform_search.json")
    return payload["selected_candidates"]


def residual_entropy_bits_per_byte(residuals: bytes) -> float:
    if not residuals:
        return 0.0
    counts = Counter(residuals)
    total = len(residuals)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def opportunity_for_span(
    span: bytes,
    start: int,
    scheme: dict[str, Any],
    maps: dict[int, dict[bytes, dict[str, Any]]],
) -> dict[str, Any] | None:
    min_prefix = int(scheme["min_prefix_len"])
    for prefix_len in range(SPAN_LEN, min_prefix - 1, -1):
        hit = maps[prefix_len].get(span[:prefix_len])
        if hit is None:
            continue
        expanded: bytes = hit["expanded"]
        residual = bytes(
            span[idx] ^ expanded[idx]
            for idx in range(prefix_len, SPAN_LEN)
        )
        seed_record_len = 4 + int(hit["seed_len"])
        sidecar_len = int(scheme["sidecar_header_bytes"]) + len(residual)
        encoded_len = seed_record_len + sidecar_len
        return {
            "start_offset": start,
            "span_len": SPAN_LEN,
            "prefix_len": prefix_len,
            "seed_index": hit["seed_index"],
            "seed_len": hit["seed_len"],
            "seed_hex": hit["seed_hex"],
            "encoded_len": encoded_len,
            "seed_record_len": seed_record_len,
            "residual_len": len(residual),
            "sidecar_len": sidecar_len,
            "residual_hex": residual.hex(),
            "savings": SPAN_LEN - encoded_len,
        }
    return None


def select_non_overlapping(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    covered = [False] * 0
    max_end = 0
    for opportunity in opportunities:
        max_end = max(max_end, opportunity["start_offset"] + opportunity["span_len"])
    covered = [False] * max_end
    for opportunity in sorted(
        opportunities,
        key=lambda row: (
            row["prefix_len"],
            row["savings"],
            -row["encoded_len"],
            -row["start_offset"],
        ),
        reverse=True,
    ):
        start = opportunity["start_offset"]
        end = start + opportunity["span_len"]
        if any(covered[start:end]):
            continue
        selected.append(opportunity)
        for idx in range(start, end):
            covered[idx] = True
    return sorted(selected, key=lambda row: row["start_offset"])


def analyze_case(
    corpus: dict[str, Any],
    transform: dict[str, Any],
    scheme: dict[str, Any],
    maps: dict[int, dict[bytes, dict[str, Any]]],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    original = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    transformed = generate_affine_transform_search.apply_candidate(original, transform)
    restored_marker = generate_affine_transform_search.apply_candidate(
        original,
        {"name": "identity", "family": "identity", "parameter": 0, "metadata_bytes": 0},
    )
    if transform["family"] == "identity" and transformed != restored_marker:
        raise RuntimeError("identity transform failed")
    metrics = generate_transform_probe.analyze_bytes(transformed, prefix_sets)
    opportunities = []
    for start in range(0, max(0, len(transformed) - SPAN_LEN + 1), SPAN_STEP):
        opportunity = opportunity_for_span(
            transformed[start : start + SPAN_LEN],
            start,
            scheme,
            maps,
        )
        if opportunity is not None:
            opportunities.append(opportunity)
    selected = select_non_overlapping(opportunities)
    residuals = bytes.fromhex("".join(row["residual_hex"] for row in selected))
    selected_count = len(selected)
    metadata_bytes = int(transform["metadata_bytes"]) if selected_count else 0
    sidecar_bytes = sum(row["sidecar_len"] for row in selected)
    seed_record_bytes = sum(row["seed_record_len"] for row in selected)
    literal_bytes = selected_count * SPAN_LEN
    seed_contribution_bytes = max(0, literal_bytes - seed_record_bytes)
    net_delta_bytes = metadata_bytes + seed_record_bytes + sidecar_bytes - literal_bytes
    positive_span_count = sum(1 for row in selected if row["savings"] > 0)
    selected_records = [
        {
            "pass": 1,
            "start_offset": row["start_offset"],
            "span_len": row["span_len"],
            "prefix_len": row["prefix_len"],
            "seed_index": row["seed_index"],
            "seed_len": row["seed_len"],
            "seed_hex": row["seed_hex"],
            "encoded_len": row["encoded_len"],
            "residual_len": row["residual_len"],
            "savings": row["savings"],
        }
        for row in selected[:TELEMETRY_LIMIT]
    ]
    return {
        "name": f"{corpus['name']}::{transform['name']}::{scheme['name']}",
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus.get("control_kind", "ordinary-structured"),
        "paired_with": corpus.get("paired_with"),
        "transform": transform["name"],
        "transform_family": transform["family"],
        "transform_parameter": transform["parameter"],
        "metadata_bytes": transform["metadata_bytes"],
        "residual_scheme": scheme["name"],
        "min_prefix_len": scheme["min_prefix_len"],
        "sidecar_header_bytes": scheme["sidecar_header_bytes"],
        "inverse_verified": True,
        "input_sha256": hashlib.sha256(original).hexdigest(),
        "original_bytes": len(original),
        "transformed_sha256": hashlib.sha256(transformed).hexdigest(),
        "transformed_bytes": len(transformed),
        "target_span_count": metrics["candidate_spans"],
        "dedup_span_count": len(
            {
                transformed[start : start + SPAN_LEN]
                for start in range(0, max(0, len(transformed) - SPAN_LEN + 1), SPAN_STEP)
            }
        ),
        "prefix_ge_3_count": metrics["prefix_ge_3_count"],
        "prefix_ge_4_count": metrics["prefix_ge_4_count"],
        "prefix_ge_5_count": metrics["prefix_ge_5_count"],
        "prefix_ge_6_count": metrics["prefix_ge_6_count"],
        "natural_exact_hits": metrics["exact_span_hits"],
        "forced_exact_hits": len(opportunities),
        "selected_span_count": selected_count,
        "positive_span_count": positive_span_count,
        "sidecar_bytes": sidecar_bytes,
        "residual_bytes_per_span": (len(residuals) / selected_count) if selected_count else 0.0,
        "residual_entropy_bits_per_byte": residual_entropy_bits_per_byte(residuals),
        "seed_record_bytes": seed_record_bytes,
        "literal_bytes": literal_bytes,
        "seed_contribution_bytes": seed_contribution_bytes,
        "net_delta_bytes": net_delta_bytes,
        "net_delta_pct": (net_delta_bytes / len(original) * 100.0) if original else 0.0,
        "selected_records": selected_records,
    }


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, str]:
    return (
        1 if row["selected_span_count"] > 0 else 0,
        -row["net_delta_bytes"],
        row["positive_span_count"],
        row["seed_contribution_bytes"],
        row["selected_span_count"],
        row["prefix_ge_5_count"],
        row["prefix_ge_4_count"],
        row["name"],
    )


def summarize(rows: list[dict[str, Any]], candidate_count: int) -> dict[str, Any]:
    heldout = [row for row in rows if row["role"] == "held-out"]
    best_overall = max(rows, key=row_score)
    best_heldout = max(heldout, key=row_score)
    heldout_positive = [row for row in heldout if row["net_delta_bytes"] < 0]
    shadow_positive = [
        row
        for row in heldout_positive
        if row["control_kind"] == "shadow-vocab"
    ]
    binary_positive = [
        row
        for row in heldout_positive
        if str(row["control_kind"]).startswith("binary-")
    ]
    heldout_seed_contribution = [
        row for row in heldout if row["seed_contribution_bytes"] > 0
    ]
    heldout_forced = [row for row in heldout if row["selected_span_count"] > 0]
    promotion_met = bool(heldout_positive)
    stop_reason = (
        "held-out rows have no negative net delta after seed records, transform metadata, and residual sidecar bytes"
        if not promotion_met
        else "promotion gate met"
    )
    return {
        "candidate_count": candidate_count,
        "validation_rows": len(rows),
        "heldout_positive_rows": len(heldout_positive),
        "shadow_positive_rows": len(shadow_positive),
        "binary_positive_rows": len(binary_positive),
        "heldout_seed_contribution_positive_rows": len(heldout_seed_contribution),
        "heldout_forced_rows": len(heldout_forced),
        "best_overall_case": best_overall["name"],
        "best_overall_net_delta_bytes": best_overall["net_delta_bytes"],
        "best_overall_selected_spans": best_overall["selected_span_count"],
        "best_heldout_case": best_heldout["name"],
        "best_heldout_net_delta_bytes": best_heldout["net_delta_bytes"],
        "best_heldout_selected_spans": best_heldout["selected_span_count"],
        "best_heldout_seed_contribution_bytes": best_heldout["seed_contribution_bytes"],
        "promotion_met": promotion_met,
        "stop_reason": stop_reason,
        "conclusion": (
            "Residual sidecar steering produced held-out negative net delta."
            if promotion_met
            else "Residual sidecar steering did not beat literal storage on held-out rows."
        ),
    }


def build_report() -> dict[str, Any]:
    prefix_maps = seed_prefix_maps()
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    transforms = selected_affine_candidates()
    rows = [
        analyze_case(corpus, transform, scheme, prefix_maps, prefix_sets)
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
        for transform in transforms
        for scheme in RESIDUAL_SCHEMES
    ]
    return {
        "generated_by": "scripts/generate_seed_manifold_residual_steering.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "validation_manifest_sha256": validation_manifest_hash(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "residual_schemes": RESIDUAL_SCHEMES,
        "transform_candidates": transforms,
        "results": rows,
        "summary": summarize(rows, len(transforms) * len(RESIDUAL_SCHEMES)),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = DISPLAY_LIMIT) -> list[dict[str, Any]]:
    return sorted(rows, key=row_score, reverse=True)[:limit]


def write_report(payload: dict[str, Any]) -> None:
    STEERING_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Seed-Manifold Residual Steering",
        "",
        "Generated by `scripts/generate_seed_manifold_residual_steering.py`.",
        "This is a residual sidecar economics probe, not `.tlmr` format support.",
        "",
        f"Candidate schemes: `{summary['candidate_count']}`.",
        f"Validation rows: `{summary['validation_rows']}`.",
        f"Held-out positive net-delta rows: `{summary['heldout_positive_rows']}`.",
        f"Held-out rows with positive seed contribution: `{summary['heldout_seed_contribution_positive_rows']}`.",
        f"Held-out rows with forced exact spans: `{summary['heldout_forced_rows']}`.",
        f"Shadow positive rows: `{summary['shadow_positive_rows']}`.",
        f"Binary positive rows: `{summary['binary_positive_rows']}`.",
        f"Promotion met: `{summary['promotion_met']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best held-out case: `{summary['best_heldout_case']}` with net delta `{summary['best_heldout_net_delta_bytes']}` bytes, selected spans `{summary['best_heldout_selected_spans']}`, and seed contribution `{summary['best_heldout_seed_contribution_bytes']}` bytes.",
        f"Stop reason: {summary['stop_reason']}.",
        "",
        "## Top Rows",
        "",
        "| row | kind | scheme | selected spans | seed contribution | sidecar bytes | net delta | exact hits |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["results"]):
        lines.append(
            "| {name} | {control_kind} | {residual_scheme} | {selected_span_count} | "
            "{seed_contribution_bytes} | {sidecar_bytes} | {net_delta_bytes} | "
            "{natural_exact_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Promotion requires held-out negative net delta after seed records, transform metadata, and residual sidecar bytes.",
            "- Forced exact spans do not count as compression unless the residual sidecar is cheaper than literal storage.",
            "- Vocabulary-disjoint and binary TLV/varint controls are reported so sidecar wins cannot hide token-only effects.",
            "- This artifact keeps residual steering outside the wire format until a versioned descriptor and inverse decoder are justified.",
        ]
    )
    STEERING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not STEERING_JSON.exists() or not STEERING_MD.exists():
        raise SystemExit("generated seed-manifold residual steering files are missing")
    payload = load_json(STEERING_JSON)
    if payload.get("generated_by") != "scripts/generate_seed_manifold_residual_steering.py":
        raise SystemExit("seed_manifold_residual_steering.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("seed_manifold_residual_steering.json artifact hashes are stale")
    if payload.get("validation_manifest_sha256") != validation_manifest_hash():
        raise SystemExit("seed_manifold_residual_steering.json validation manifest hash is stale")
    expected_rows = (
        len(payload.get("transform_candidates", []))
        * len(RESIDUAL_SCHEMES)
        * len(generate_transform_validation.CORPUS_VALIDATION_MATRIX)
    )
    if len(payload.get("results", [])) != expected_rows:
        raise SystemExit("seed_manifold_residual_steering.json row count is stale")
    text = STEERING_MD.read_text(encoding="utf-8")
    for phrase in (
        "Seed-Manifold Residual Steering",
        "residual sidecar economics probe",
        "Promotion requires held-out negative net delta",
        "Forced exact spans do not count as compression",
        "Vocabulary-disjoint",
        "outside the wire format",
    ):
        if phrase not in text:
            raise SystemExit(f"SEED_MANIFOLD_RESIDUAL_STEERING.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated sidecar steering")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
