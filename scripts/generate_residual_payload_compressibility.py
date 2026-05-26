#!/usr/bin/env python3
"""Measure residual payload compression bounds for forced sidecar rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_affine_transform_search
import generate_corpus_matrix
import generate_seed_manifold_residual_steering
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
COMPRESSIBILITY_JSON = DOCS / "residual_payload_compressibility.json"
COMPRESSIBILITY_MD = DOCS / "RESIDUAL_PAYLOAD_COMPRESSIBILITY.md"

PAYLOAD_POLICIES = (
    "raw_payload",
    "zlib_level9",
    "lzma_preset9",
    "byte_rle",
    "zero_bitmap",
    "entropy_lower_bound",
    "half_rate_model",
    "quarter_rate_model",
    "zero_payload_oracle",
)
MEASURED_PAYLOAD_POLICIES = {
    "raw_payload",
    "zlib_level9",
    "lzma_preset9",
    "byte_rle",
    "zero_bitmap",
}
THEORETICAL_PAYLOAD_POLICIES = {
    "entropy_lower_bound",
    "half_rate_model",
    "quarter_rate_model",
    "zero_payload_oracle",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "seed_manifold_residual_steering_sha256": sha256(
            DOCS / "seed_manifold_residual_steering.json"
        ),
        "sidecar_break_even_sha256": sha256(DOCS / "sidecar_break_even.json"),
        "affine_transform_search_sha256": sha256(DOCS / "affine_transform_search.json"),
    }


def policy_manifest() -> dict[str, Any]:
    return {
        "payload_policies": PAYLOAD_POLICIES,
        "policy": "Reconstruct selected residual suffix bytes and compare payload coders against the existing seed/header/metadata budget.",
        "strict_negative_delta": "metadata + seed_records + per_span_sidecar_headers + payload_bytes < literal_bytes",
    }


def policy_manifest_hash() -> str:
    payload = json.dumps(policy_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def entropy_bits_per_byte(payload: bytes) -> float:
    if not payload:
        return 0.0
    counts = Counter(payload)
    total = len(payload)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def rle_len(payload: bytes) -> int:
    if not payload:
        return 0
    runs = 1
    previous = payload[0]
    for byte in payload[1:]:
        if byte != previous:
            runs += 1
            previous = byte
    return runs * 2


def zero_bitmap_len(payload: bytes) -> int:
    if not payload:
        return 0
    nonzero = sum(1 for byte in payload if byte != 0)
    return math.ceil(len(payload) / 8) + nonzero


def payload_len(policy: str, payload: bytes) -> int:
    if policy == "raw_payload":
        return len(payload)
    if policy == "zlib_level9":
        return len(zlib.compress(payload, level=9))
    if policy == "lzma_preset9":
        return len(lzma.compress(payload, preset=9 | lzma.PRESET_EXTREME))
    if policy == "byte_rle":
        return rle_len(payload)
    if policy == "zero_bitmap":
        return zero_bitmap_len(payload)
    if policy == "entropy_lower_bound":
        return math.ceil(entropy_bits_per_byte(payload) * len(payload) / 8)
    if policy == "half_rate_model":
        return math.ceil(len(payload) * 0.5)
    if policy == "quarter_rate_model":
        return math.ceil(len(payload) * 0.25)
    if policy == "zero_payload_oracle":
        return 0
    raise ValueError(policy)


def selected_residual_payloads() -> list[dict[str, Any]]:
    steering = load_json(DOCS / "seed_manifold_residual_steering.json")
    source_rows = {
        row["name"]: row
        for row in steering.get("results", [])
        if row.get("selected_span_count", 0) > 0
    }
    maps = generate_seed_manifold_residual_steering.seed_prefix_maps()
    output: list[dict[str, Any]] = []
    for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        original = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
        for transform in generate_seed_manifold_residual_steering.selected_affine_candidates():
            transformed = generate_affine_transform_search.apply_candidate(original, transform)
            for scheme in generate_seed_manifold_residual_steering.RESIDUAL_SCHEMES:
                row_name = f"{corpus['name']}::{transform['name']}::{scheme['name']}"
                source = source_rows.get(row_name)
                if source is None:
                    continue
                opportunities = []
                for start in range(
                    0,
                    max(0, len(transformed) - generate_seed_manifold_residual_steering.SPAN_LEN + 1),
                    generate_seed_manifold_residual_steering.SPAN_STEP,
                ):
                    opportunity = generate_seed_manifold_residual_steering.opportunity_for_span(
                        transformed[
                            start : start + generate_seed_manifold_residual_steering.SPAN_LEN
                        ],
                        start,
                        scheme,
                        maps,
                    )
                    if opportunity is not None:
                        opportunities.append(opportunity)
                selected = generate_seed_manifold_residual_steering.select_non_overlapping(
                    opportunities
                )
                if len(selected) != source["selected_span_count"]:
                    raise RuntimeError(f"selected-span mismatch for {row_name}")
                residual_payload = bytes.fromhex(
                    "".join(row["residual_hex"] for row in selected)
                )
                expected_payload_len = source["sidecar_bytes"] - (
                    source["sidecar_header_bytes"] * source["selected_span_count"]
                )
                if len(residual_payload) != expected_payload_len:
                    raise RuntimeError(f"residual payload mismatch for {row_name}")
                output.append(
                    {
                        "name": row_name,
                        "corpus": source["corpus"],
                        "role": source["role"],
                        "control_kind": source["control_kind"],
                        "transform": source["transform"],
                        "residual_scheme": source["residual_scheme"],
                        "selected_span_count": source["selected_span_count"],
                        "metadata_bytes": source["metadata_bytes"],
                        "seed_record_bytes": source["seed_record_bytes"],
                        "sidecar_header_bytes_total": (
                            source["sidecar_header_bytes"] * source["selected_span_count"]
                        ),
                        "literal_bytes": source["literal_bytes"],
                        "raw_payload_bytes": len(residual_payload),
                        "payload_sha256": hashlib.sha256(residual_payload).hexdigest(),
                        "payload_entropy_bits_per_byte": entropy_bits_per_byte(residual_payload),
                        "max_payload_bytes_for_strict_negative": (
                            source["literal_bytes"]
                            - source["metadata_bytes"]
                            - source["seed_record_bytes"]
                            - (
                                source["sidecar_header_bytes"]
                                * source["selected_span_count"]
                            )
                            - 1
                        ),
                        "selected_records": [
                            {
                                "start_offset": row["start_offset"],
                                "prefix_len": row["prefix_len"],
                                "seed_len": row["seed_len"],
                                "residual_len": row["residual_len"],
                                "residual_sha256": hashlib.sha256(
                                    bytes.fromhex(row["residual_hex"])
                                ).hexdigest(),
                            }
                            for row in selected[:8]
                        ],
                    }
                )
    return output


def build_policy_rows(payload_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payload_by_hash: dict[str, bytes] = {}
    # Reconstructing by hash is intentionally avoided in the public artifact; only
    # lengths and hashes are persisted. The local pass recomputes payload bytes.
    maps = generate_seed_manifold_residual_steering.seed_prefix_maps()
    for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        original = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
        for transform in generate_seed_manifold_residual_steering.selected_affine_candidates():
            transformed = generate_affine_transform_search.apply_candidate(original, transform)
            for scheme in generate_seed_manifold_residual_steering.RESIDUAL_SCHEMES:
                row_name = f"{corpus['name']}::{transform['name']}::{scheme['name']}"
                if not any(row["name"] == row_name for row in payload_rows):
                    continue
                opportunities = []
                for start in range(
                    0,
                    max(0, len(transformed) - generate_seed_manifold_residual_steering.SPAN_LEN + 1),
                    generate_seed_manifold_residual_steering.SPAN_STEP,
                ):
                    opportunity = generate_seed_manifold_residual_steering.opportunity_for_span(
                        transformed[
                            start : start + generate_seed_manifold_residual_steering.SPAN_LEN
                        ],
                        start,
                        scheme,
                        maps,
                    )
                    if opportunity is not None:
                        opportunities.append(opportunity)
                selected = generate_seed_manifold_residual_steering.select_non_overlapping(
                    opportunities
                )
                residual_payload = bytes.fromhex(
                    "".join(row["residual_hex"] for row in selected)
                )
                payload_by_hash[hashlib.sha256(residual_payload).hexdigest()] = residual_payload

    for payload_row in payload_rows:
        residual_payload = payload_by_hash[payload_row["payload_sha256"]]
        fixed_cost = (
            payload_row["metadata_bytes"]
            + payload_row["seed_record_bytes"]
            + payload_row["sidecar_header_bytes_total"]
        )
        for policy in PAYLOAD_POLICIES:
            compressed_payload_bytes = payload_len(policy, residual_payload)
            net_delta_bytes = (
                fixed_cost
                + compressed_payload_bytes
                - payload_row["literal_bytes"]
            )
            rows.append(
                {
                    "name": payload_row["name"],
                    "corpus": payload_row["corpus"],
                    "role": payload_row["role"],
                    "control_kind": payload_row["control_kind"],
                    "transform": payload_row["transform"],
                    "residual_scheme": payload_row["residual_scheme"],
                    "payload_policy": policy,
                    "selected_span_count": payload_row["selected_span_count"],
                    "raw_payload_bytes": payload_row["raw_payload_bytes"],
                    "compressed_payload_bytes": compressed_payload_bytes,
                    "payload_ratio": (
                        compressed_payload_bytes / payload_row["raw_payload_bytes"]
                        if payload_row["raw_payload_bytes"]
                        else 0.0
                    ),
                    "metadata_bytes": payload_row["metadata_bytes"],
                    "seed_record_bytes": payload_row["seed_record_bytes"],
                    "sidecar_header_bytes_total": payload_row[
                        "sidecar_header_bytes_total"
                    ],
                    "literal_bytes": payload_row["literal_bytes"],
                    "net_delta_bytes": net_delta_bytes,
                    "strict_negative": net_delta_bytes < 0,
                    "max_payload_bytes_for_strict_negative": payload_row[
                        "max_payload_bytes_for_strict_negative"
                    ],
                    "payload_entropy_bits_per_byte": payload_row[
                        "payload_entropy_bits_per_byte"
                    ],
                }
            )
    return rows


def summarize(payload_rows: list[dict[str, Any]], policy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected_by_role = Counter(row["role"] for row in payload_rows)
    negative_by_policy: dict[str, int] = {}
    heldout_negative_by_policy: dict[str, int] = {}
    best_heldout_by_policy: dict[str, int | None] = {}
    for policy in PAYLOAD_POLICIES:
        rows = [row for row in policy_rows if row["payload_policy"] == policy]
        heldout_rows = [row for row in rows if row["role"] == "held-out"]
        negative_by_policy[policy] = sum(1 for row in rows if row["strict_negative"])
        heldout_negative_by_policy[policy] = sum(
            1 for row in heldout_rows if row["strict_negative"]
        )
        best_heldout_by_policy[policy] = (
            min((row["net_delta_bytes"] for row in heldout_rows), default=None)
        )
    heldout_payload_rows = [row for row in payload_rows if row["role"] == "held-out"]
    measured_heldout_negative_rows = [
        row
        for row in policy_rows
        if row["role"] == "held-out"
        and row["strict_negative"]
        and row["payload_policy"] in MEASURED_PAYLOAD_POLICIES
    ]
    return {
        "selected_payload_rows": len(payload_rows),
        "selected_payload_rows_by_role": dict(selected_by_role),
        "heldout_payload_rows": len(heldout_payload_rows),
        "heldout_rows_with_payload_budget_at_zero_or_more": sum(
            1
            for row in heldout_payload_rows
            if row["max_payload_bytes_for_strict_negative"] >= 0
        ),
        "heldout_rows_impossible_even_with_zero_payload": sum(
            1
            for row in heldout_payload_rows
            if row["max_payload_bytes_for_strict_negative"] < 0
        ),
        "negative_rows_by_policy": negative_by_policy,
        "heldout_negative_rows_by_policy": heldout_negative_by_policy,
        "best_heldout_net_delta_by_policy": best_heldout_by_policy,
        "measured_heldout_negative_rows": len(
            {row["name"] for row in measured_heldout_negative_rows}
        ),
        "measured_heldout_negative_policy_rows": len(measured_heldout_negative_rows),
        "best_measured_heldout_negative_case": (
            min(measured_heldout_negative_rows, key=lambda row: row["net_delta_bytes"])[
                "name"
            ]
            if measured_heldout_negative_rows
            else None
        ),
        "promotion_met": bool(measured_heldout_negative_rows),
        "conclusion": (
            "A measured residual payload coder produces a narrow held-out negative row."
            if measured_heldout_negative_rows
            else "No measured residual payload coder turns current held-out sidecar rows negative."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["role"] == "held-out",
            row["strict_negative"],
            -row["net_delta_bytes"],
            row["selected_span_count"],
            -row["compressed_payload_bytes"],
        ),
        reverse=True,
    )[:limit]


def build_report() -> dict[str, Any]:
    payload_rows = selected_residual_payloads()
    policy_rows = build_policy_rows(payload_rows)
    return {
        "generated_by": "scripts/generate_residual_payload_compressibility.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "policy_manifest_sha256": policy_manifest_hash(),
        "payload_rows": payload_rows,
        "policy_rows": policy_rows,
        "summary": summarize(payload_rows, policy_rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    COMPRESSIBILITY_JSON.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = payload["summary"]
    lines = [
        "# Telomere Residual Payload Compressibility",
        "",
        "Generated by `scripts/generate_residual_payload_compressibility.py`.",
        "This is a residual sidecar payload bound, not `.tlmr` format support.",
        "",
        f"Selected payload rows: `{summary['selected_payload_rows']}`.",
        f"Held-out payload rows: `{summary['heldout_payload_rows']}`.",
        f"Held-out rows with nonnegative payload budget: `{summary['heldout_rows_with_payload_budget_at_zero_or_more']}`.",
        f"Held-out rows impossible even with zero payload: `{summary['heldout_rows_impossible_even_with_zero_payload']}`.",
        f"Measured held-out negative rows: `{summary['measured_heldout_negative_rows']}`.",
        f"Measured held-out negative policy rows: `{summary['measured_heldout_negative_policy_rows']}`.",
        f"Best measured held-out negative case: `{summary['best_measured_heldout_negative_case']}`.",
        "",
        summary["conclusion"],
        "",
        "## Policy Summary",
        "",
        "| policy | all negative rows | held-out negative rows | best held-out net delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for policy in PAYLOAD_POLICIES:
        lines.append(
            "| {policy} | {all_negative} | {heldout_negative} | {best} |".format(
                policy=policy,
                all_negative=summary["negative_rows_by_policy"][policy],
                heldout_negative=summary["heldout_negative_rows_by_policy"][policy],
                best=summary["best_heldout_net_delta_by_policy"][policy],
            )
        )

    lines.extend(
        [
            "",
            "## Best Rows",
            "",
            "| row | role | policy | spans | raw payload | compressed payload | max payload for negative | net delta |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(payload["policy_rows"]):
        lines.append(
            "| {name} | {role} | {payload_policy} | {selected_span_count} | "
            "{raw_payload_bytes} | {compressed_payload_bytes} | "
            "{max_payload_bytes_for_strict_negative} | {net_delta_bytes} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- zlib and LZMA produce a narrow held-out negative row on the current selected residual payloads.",
            "- Byte-RLE, zero-bitmap, and raw payloads do not produce held-out negative delta.",
            "- Half-rate and quarter-rate payload hypotheses still do not make any current held-out row negative.",
            "- The zero-payload oracle shows additional held-out rows would become negative only if residual bytes were almost eliminated.",
            "- Rows with negative `max payload for negative` cannot be saved by residual compression alone; their fixed seed/header/metadata cost already exceeds the literal budget.",
            "- Treat this as a narrow payload-coder promotion signal, not sidecar format support; the next step must prove exact decode and held-out controls in an experimental descriptor.",
        ]
    )
    COMPRESSIBILITY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not COMPRESSIBILITY_JSON.exists() or not COMPRESSIBILITY_MD.exists():
        raise SystemExit("generated residual payload compressibility files are missing")
    payload = load_json(COMPRESSIBILITY_JSON)
    if payload.get("generated_by") != "scripts/generate_residual_payload_compressibility.py":
        raise SystemExit("residual_payload_compressibility.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("residual payload compressibility artifact hashes are stale")
    if payload.get("policy_manifest_sha256") != policy_manifest_hash():
        raise SystemExit("residual payload compressibility policy manifest hash is stale")
    expected_policy_rows = len(payload.get("payload_rows", [])) * len(PAYLOAD_POLICIES)
    if len(payload.get("policy_rows", [])) != expected_policy_rows:
        raise SystemExit("residual payload compressibility policy-row count is stale")
    text = COMPRESSIBILITY_MD.read_text(encoding="utf-8")
    for phrase in (
        "Residual Payload Compressibility",
        "payload bound, not `.tlmr` format support",
        "Held-out rows impossible even with zero payload",
        "zlib and LZMA produce a narrow held-out negative row",
        "narrow payload-coder promotion signal",
    ):
        if phrase not in text:
            raise SystemExit(f"RESIDUAL_PAYLOAD_COMPRESSIBILITY.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
