#!/usr/bin/env python3
"""Generate residual-sidecar break-even rules for Telomere steering."""

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
BREAK_EVEN_JSON = DOCS / "sidecar_break_even.json"
BREAK_EVEN_MD = DOCS / "SIDECAR_BREAK_EVEN.md"

SPAN_LENGTHS = (8, 12, 16, 20, 24, 32, 40, 64)
SEED_LENGTHS = (1, 2, 3)
SIDECAR_HEADER_BYTES = (0, 1, 2)
METADATA_BYTES_PER_SPAN = (0, 1, 2)
V2_SEED_RECORD_FIXED_BYTES = 4
V2_LITERAL_RECORD_FIXED_BYTES = 3
CURRENT_MAX_OBSERVED_PREFIX_SCHEME = 7
RESIDUAL_POLICIES = (
    {
        "name": "raw_suffix_xor",
        "residual_payload_ratio": 1.0,
        "description": "Store every unmatched suffix byte as an XOR residual.",
    },
    {
        "name": "half_rate_residual_model",
        "residual_payload_ratio": 0.5,
        "description": "Hypothetical entropy-coded sidecar at half a byte per unmatched suffix byte.",
    },
    {
        "name": "quarter_rate_residual_model",
        "residual_payload_ratio": 0.25,
        "description": "Hypothetical entropy-coded sidecar at quarter byte per unmatched suffix byte.",
    },
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "seed_manifold_residual_steering_sha256": sha256(
            DOCS / "seed_manifold_residual_steering.json"
        ),
        "affine_transform_search_sha256": sha256(DOCS / "affine_transform_search.json"),
        "format_doc_sha256": sha256(DOCS / "FORMAT.md"),
    }


def case_manifest() -> dict[str, Any]:
    return {
        "span_lengths": SPAN_LENGTHS,
        "seed_lengths": SEED_LENGTHS,
        "sidecar_header_bytes": SIDECAR_HEADER_BYTES,
        "metadata_bytes_per_span": METADATA_BYTES_PER_SPAN,
        "residual_policies": RESIDUAL_POLICIES,
        "v2_seed_record_fixed_bytes": V2_SEED_RECORD_FIXED_BYTES,
        "v2_literal_record_fixed_bytes": V2_LITERAL_RECORD_FIXED_BYTES,
        "policy": "suffix-residual sidecar: encoded = v2 seed record + sidecar header + residual payload + amortized metadata",
    }


def case_manifest_hash() -> str:
    payload = json.dumps(case_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def current_counts_by_required_prefix(sidecar: dict[str, Any]) -> dict[int, dict[str, int]]:
    output: dict[int, dict[str, int]] = {
        prefix: {"forced_rows": 0, "positive_net_rows": 0}
        for prefix in range(4, CURRENT_MAX_OBSERVED_PREFIX_SCHEME + 1)
    }
    output[8] = {"forced_rows": 0, "positive_net_rows": 0}
    for row in sidecar.get("results", []):
        if row.get("role") != "held-out":
            continue
        scheme = str(row.get("residual_scheme", ""))
        if scheme.startswith("prefix") and "-suffix" in scheme:
            prefix = int(scheme.removeprefix("prefix").split("-", 1)[0])
            bucket = output.setdefault(prefix, {"forced_rows": 0, "positive_net_rows": 0})
            if row.get("selected_span_count", 0) > 0:
                bucket["forced_rows"] += 1
            if row.get("net_delta_bytes", 0) < 0:
                bucket["positive_net_rows"] += 1
        if row.get("natural_exact_hits", 0) > 0:
            output[8]["forced_rows"] += 1
            if row.get("net_delta_bytes", 0) < 0:
                output[8]["positive_net_rows"] += 1
    return output


def observed_counts(required_prefix: int, current_counts: dict[int, dict[str, int]]) -> dict[str, Any]:
    if required_prefix <= CURRENT_MAX_OBSERVED_PREFIX_SCHEME:
        counts = current_counts.get(required_prefix, {"forced_rows": 0, "positive_net_rows": 0})
        return {
            "observed_status": "measured",
            "current_forced_rows_at_required_prefix": counts["forced_rows"],
            "current_positive_net_rows_at_required_prefix": counts["positive_net_rows"],
        }
    if required_prefix == 8:
        counts = current_counts.get(8, {"forced_rows": 0, "positive_net_rows": 0})
        return {
            "observed_status": "exact-only",
            "current_forced_rows_at_required_prefix": counts["forced_rows"],
            "current_positive_net_rows_at_required_prefix": counts["positive_net_rows"],
        }
    return {
        "observed_status": "not-measured",
        "current_forced_rows_at_required_prefix": 0,
        "current_positive_net_rows_at_required_prefix": 0,
    }


def residual_payload_bytes(span_len: int, prefix_len: int, ratio: float) -> int:
    return math.ceil(max(0, span_len - prefix_len) * ratio)


def candidate_cost(
    span_len: int,
    prefix_len: int,
    seed_record_bytes: int,
    sidecar_header_bytes: int,
    metadata_bytes_per_span: int,
    residual_ratio: float,
) -> int:
    return (
        seed_record_bytes
        + sidecar_header_bytes
        + metadata_bytes_per_span
        + residual_payload_bytes(span_len, prefix_len, residual_ratio)
    )


def required_prefix(
    span_len: int,
    seed_record_bytes: int,
    sidecar_header_bytes: int,
    metadata_bytes_per_span: int,
    residual_ratio: float,
    baseline_bytes: int,
    strict: bool,
) -> int | None:
    for prefix_len in range(1, span_len + 1):
        cost = candidate_cost(
            span_len,
            prefix_len,
            seed_record_bytes,
            sidecar_header_bytes,
            metadata_bytes_per_span,
            residual_ratio,
        )
        if cost < baseline_bytes if strict else cost <= baseline_bytes:
            return prefix_len
    return None


def build_rows(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    current_counts = current_counts_by_required_prefix(sidecar)
    max_observed_prefix = max(
        (
            int(row["min_prefix_len"])
            for row in sidecar.get("results", [])
            if row.get("role") == "held-out" and row.get("selected_span_count", 0) > 0
        ),
        default=0,
    )
    rows: list[dict[str, Any]] = []
    for span_len in SPAN_LENGTHS:
        for seed_len in SEED_LENGTHS:
            seed_record_bytes = V2_SEED_RECORD_FIXED_BYTES + seed_len
            for sidecar_header_bytes in SIDECAR_HEADER_BYTES:
                for metadata_bytes_per_span in METADATA_BYTES_PER_SPAN:
                    for policy in RESIDUAL_POLICIES:
                        ratio = float(policy["residual_payload_ratio"])
                        raw_literal_bytes = span_len
                        v2_literal_record_bytes = V2_LITERAL_RECORD_FIXED_BYTES + span_len
                        raw_equal = required_prefix(
                            span_len,
                            seed_record_bytes,
                            sidecar_header_bytes,
                            metadata_bytes_per_span,
                            ratio,
                            raw_literal_bytes,
                            strict=False,
                        )
                        raw_strict = required_prefix(
                            span_len,
                            seed_record_bytes,
                            sidecar_header_bytes,
                            metadata_bytes_per_span,
                            ratio,
                            raw_literal_bytes,
                            strict=True,
                        )
                        v2_strict = required_prefix(
                            span_len,
                            seed_record_bytes,
                            sidecar_header_bytes,
                            metadata_bytes_per_span,
                            ratio,
                            v2_literal_record_bytes,
                            strict=True,
                        )
                        residual_at_raw_strict = (
                            residual_payload_bytes(span_len, raw_strict, ratio)
                            if raw_strict is not None
                            else None
                        )
                        encoded_at_raw_strict = (
                            candidate_cost(
                                span_len,
                                raw_strict,
                                seed_record_bytes,
                                sidecar_header_bytes,
                                metadata_bytes_per_span,
                                ratio,
                            )
                            if raw_strict is not None
                            else None
                        )
                        raw_savings_at_strict = (
                            raw_literal_bytes - encoded_at_raw_strict
                            if encoded_at_raw_strict is not None
                            else None
                        )
                        cost_at_observed = (
                            candidate_cost(
                                span_len,
                                max_observed_prefix,
                                seed_record_bytes,
                                sidecar_header_bytes,
                                metadata_bytes_per_span,
                                ratio,
                            )
                            if max_observed_prefix > 0
                            else None
                        )
                        raw_delta_at_observed = (
                            cost_at_observed - raw_literal_bytes
                            if cost_at_observed is not None
                            else None
                        )
                        v2_delta_at_observed = (
                            cost_at_observed - v2_literal_record_bytes
                            if cost_at_observed is not None
                            else None
                        )
                        observed = observed_counts(raw_strict or span_len + 1, current_counts)
                        rows.append(
                            {
                                "residual_policy": policy["name"],
                                "residual_payload_ratio": ratio,
                                "span_len": span_len,
                                "seed_len": seed_len,
                                "seed_record_bytes": seed_record_bytes,
                                "raw_literal_bytes": raw_literal_bytes,
                                "v2_literal_record_bytes": v2_literal_record_bytes,
                                "sidecar_header_bytes": sidecar_header_bytes,
                                "metadata_bytes_per_span": metadata_bytes_per_span,
                                "required_prefix_raw_equal": raw_equal,
                                "required_prefix_raw_negative": raw_strict,
                                "required_prefix_v2_negative": v2_strict,
                                "required_prefix_ratio_raw": (
                                    raw_strict / span_len if raw_strict is not None else None
                                ),
                                "residual_payload_bytes_at_raw_strict": residual_at_raw_strict,
                                "encoded_bytes_at_raw_strict": encoded_at_raw_strict,
                                "raw_savings_bytes_at_strict": raw_savings_at_strict,
                                "raw_delta_bytes_at_observed_best_prefix": raw_delta_at_observed,
                                "v2_delta_bytes_at_observed_best_prefix": v2_delta_at_observed,
                                "feasible_raw_negative": raw_strict is not None,
                                "feasible_v2_negative": v2_strict is not None,
                                "requires_exact_at_span8": raw_strict is not None and raw_strict >= 8,
                                **observed,
                            }
                        )
    return rows


def build_metadata_rows() -> list[dict[str, Any]]:
    rows = []
    for selected_span_count in (1, 2, 4, 8, 16, 32):
        for metadata_bytes in (0, 2, 4):
            rows.append(
                {
                    "selected_span_count": selected_span_count,
                    "transform_metadata_bytes": metadata_bytes,
                    "metadata_bytes_per_span": metadata_bytes / selected_span_count,
                    "minimum_extra_savings_per_span_to_absorb_metadata": (
                        (metadata_bytes + selected_span_count - 1) // selected_span_count
                    ),
                }
            )
    return rows


def summarize(rows: list[dict[str, Any]], sidecar: dict[str, Any]) -> dict[str, Any]:
    strict_rows = [row for row in rows if row["feasible_raw_negative"]]
    raw_suffix_rows = [row for row in rows if row["residual_policy"] == "raw_suffix_xor"]
    sublinear_rows = [row for row in rows if row["residual_policy"] != "raw_suffix_xor"]
    measured_strict_rows = [
        row
        for row in strict_rows
        if row["observed_status"] != "not-measured"
    ]
    promoted_rows = [
        row
        for row in measured_strict_rows
        if row["current_positive_net_rows_at_required_prefix"] > 0
    ]
    model_viable_at_observed_rows = [
        row
        for row in rows
        if row["current_forced_rows_at_required_prefix"] > 0
        and row["raw_delta_bytes_at_observed_best_prefix"] is not None
        and row["raw_delta_bytes_at_observed_best_prefix"] < 0
    ]
    raw_suffix_model_viable_rows = [
        row for row in model_viable_at_observed_rows if row["residual_policy"] == "raw_suffix_xor"
    ]
    sublinear_model_viable_rows = [
        row for row in model_viable_at_observed_rows if row["residual_policy"] != "raw_suffix_xor"
    ]
    raw_suffix_measured_rows = [
        row
        for row in raw_suffix_rows
        if row["feasible_raw_negative"] and row["observed_status"] != "not-measured"
    ]
    min_required_prefix = min(row["required_prefix_raw_negative"] for row in strict_rows)
    min_raw_suffix_prefix = min(
        row["required_prefix_raw_negative"]
        for row in raw_suffix_rows
        if row["required_prefix_raw_negative"] is not None
    )
    max_observed_prefix_with_forced = max(
        (
            int(row["min_prefix_len"])
            for row in sidecar.get("results", [])
            if row.get("role") == "held-out" and row.get("selected_span_count", 0) > 0
        ),
        default=0,
    )
    exact_rows = [
        row
        for row in sidecar.get("results", [])
        if row.get("role") == "held-out" and row.get("natural_exact_hits", 0) > 0
    ]
    return {
        "row_count": len(rows),
        "raw_negative_feasible_rows": len(strict_rows),
        "measured_raw_negative_rows": len(measured_strict_rows),
        "promoted_rows": len(promoted_rows),
        "model_viable_at_observed_prefix_rows": len(model_viable_at_observed_rows),
        "raw_suffix_measured_raw_negative_rows": len(raw_suffix_measured_rows),
        "raw_suffix_viable_at_observed_prefix_rows": len(raw_suffix_model_viable_rows),
        "sublinear_model_viable_at_observed_prefix_rows": len(sublinear_model_viable_rows),
        "best_raw_suffix_observed_raw_delta_bytes": min(
            (
                row["raw_delta_bytes_at_observed_best_prefix"]
                for row in raw_suffix_rows
                if row["raw_delta_bytes_at_observed_best_prefix"] is not None
            ),
            default=None,
        ),
        "best_sublinear_observed_raw_delta_bytes": min(
            (
                row["raw_delta_bytes_at_observed_best_prefix"]
                for row in sublinear_rows
                if row["raw_delta_bytes_at_observed_best_prefix"] is not None
            ),
            default=None,
        ),
        "minimum_raw_negative_prefix_len": min_required_prefix,
        "minimum_raw_suffix_negative_prefix_len": min_raw_suffix_prefix,
        "max_observed_heldout_forced_prefix_len": max_observed_prefix_with_forced,
        "heldout_exact_rows": len(exact_rows),
        "span8_best_net_delta_bytes": sidecar["summary"]["best_heldout_net_delta_bytes"],
        "span8_heldout_positive_rows": sidecar["summary"]["heldout_positive_rows"],
        "conclusion": (
            "Current sidecar evidence meets a longer-span break-even gate."
            if promoted_rows
            else "Current sidecar evidence does not meet any measured strict break-even gate."
        ),
    }


def build_report() -> dict[str, Any]:
    sidecar = load_json(DOCS / "seed_manifold_residual_steering.json")
    rows = build_rows(sidecar)
    return {
        "generated_by": "scripts/generate_sidecar_break_even.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "case_manifest_sha256": case_manifest_hash(),
        "formula": {
            "seed_record_bytes": "4 + seed_len",
            "raw_literal_bytes": "span_len",
            "v2_literal_record_bytes": "3 + span_len",
            "sidecar_bytes": "sidecar_header_bytes + ceil(residual_payload_ratio * (span_len - prefix_len))",
            "raw_net_delta": "seed_record_bytes + sidecar_bytes + metadata_bytes_per_span - raw_literal_bytes",
            "v2_net_delta": "seed_record_bytes + sidecar_bytes + metadata_bytes_per_span - v2_literal_record_bytes",
        },
        "rows": rows,
        "metadata_rows": build_metadata_rows(),
        "summary": summarize(rows, sidecar),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["current_positive_net_rows_at_required_prefix"],
            row["current_forced_rows_at_required_prefix"],
            row["feasible_raw_negative"],
            -(row["required_prefix_raw_negative"] or 10_000),
            row["span_len"],
            -row["seed_len"],
            -row["sidecar_header_bytes"],
        ),
        reverse=True,
    )[:limit]


def write_report(payload: dict[str, Any]) -> None:
    BREAK_EVEN_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Sidecar Break-Even",
        "",
        "Generated by `scripts/generate_sidecar_break_even.py`.",
        "This is a mathematical residual-sidecar gate, not `.tlmr` format support.",
        "",
        f"Rows: `{summary['row_count']}`.",
        f"Raw-negative feasible rows: `{summary['raw_negative_feasible_rows']}`.",
        f"Measured raw-negative rows: `{summary['measured_raw_negative_rows']}`.",
        f"Promoted rows: `{summary['promoted_rows']}`.",
        f"Model-viable rows at observed prefix: `{summary['model_viable_at_observed_prefix_rows']}`.",
        f"Raw-suffix model-viable rows at observed prefix: `{summary['raw_suffix_viable_at_observed_prefix_rows']}`.",
        f"Sublinear-residual model-viable rows at observed prefix: `{summary['sublinear_model_viable_at_observed_prefix_rows']}`.",
        f"Best raw-suffix delta at observed prefix: `{summary['best_raw_suffix_observed_raw_delta_bytes']}` bytes.",
        f"Best sublinear-residual delta at observed prefix: `{summary['best_sublinear_observed_raw_delta_bytes']}` bytes.",
        f"Minimum raw-negative prefix length: `{summary['minimum_raw_negative_prefix_len']}`.",
        f"Minimum raw-suffix negative prefix length: `{summary['minimum_raw_suffix_negative_prefix_len']}`.",
        f"Max observed held-out forced prefix length: `{summary['max_observed_heldout_forced_prefix_len']}`.",
        f"Held-out exact rows: `{summary['heldout_exact_rows']}`.",
        "",
        "## Formula",
        "",
        "- v2 seed record bytes: `4 + seed_len`.",
        "- raw literal baseline bytes: `span_len`.",
        "- isolated v2 literal baseline bytes: `3 + span_len`.",
        "- suffix sidecar bytes: `sidecar_header_bytes + ceil(residual_payload_ratio * (span_len - prefix_len))`.",
        "- raw negative delta requires `seed_record_bytes + sidecar_bytes + metadata_bytes_per_span < span_len`.",
        "- v2 negative delta requires `seed_record_bytes + sidecar_bytes + metadata_bytes_per_span < 3 + span_len`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Span-8 residual steering best held-out net delta remains `{summary['span8_best_net_delta_bytes']}` bytes with `{summary['span8_heldout_positive_rows']}` positive rows.",
        "",
        "## Current Evidence Gate",
        "",
        "| policy | span | seed bytes | sidecar header | metadata/span | raw negative prefix | v2 negative prefix | observed status | forced rows | positive net rows | raw delta at observed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {residual_policy} | {span_len} | {seed_len} | {sidecar_header_bytes} | "
            "{metadata_bytes_per_span} | {required_prefix_raw_negative} | "
            "{required_prefix_v2_negative} | {observed_status} | "
            "{current_forced_rows_at_required_prefix} | "
            "{current_positive_net_rows_at_required_prefix} | "
            "{raw_delta_bytes_at_observed_best_prefix} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Prefix-4 raw suffix sidecars cannot strictly save bytes under the v2 seed record shape.",
            "- For 1-byte seeds with a 1-byte sidecar header, strict gain starts at prefix 7.",
            "- For 2-byte seeds with a 1-byte sidecar header, strict gain starts at prefix 8, which means exact span-8 evidence is required before span-8 residual steering can promote.",
        "- Longer spans only help raw suffix sidecars by lowering the required prefix ratio; absolute required prefix still depends on seed, header, and metadata bytes.",
            "- Raw suffix sidecars have zero model-viable rows at the current observed prefix frontier.",
            "- Sublinear residual models can move the arithmetic threshold, but they are hypotheses until residual payloads are actually compressed and inverted.",
            "- Sublinear model-viable rows are not promoted evidence; they only justify measuring residual payload compressibility.",
            "- Do not run another residual steering family until a candidate can plausibly reach the strict prefix gate.",
        ]
    )
    BREAK_EVEN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not BREAK_EVEN_JSON.exists() or not BREAK_EVEN_MD.exists():
        raise SystemExit("generated sidecar break-even files are missing")
    payload = load_json(BREAK_EVEN_JSON)
    if payload.get("generated_by") != "scripts/generate_sidecar_break_even.py":
        raise SystemExit("sidecar_break_even.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("sidecar_break_even.json artifact hashes are stale")
    if payload.get("case_manifest_sha256") != case_manifest_hash():
        raise SystemExit("sidecar_break_even.json case manifest hash is stale")
    expected_rows = (
        len(SPAN_LENGTHS)
        * len(SEED_LENGTHS)
        * len(SIDECAR_HEADER_BYTES)
        * len(METADATA_BYTES_PER_SPAN)
        * len(RESIDUAL_POLICIES)
    )
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit("sidecar_break_even.json row count is stale")
    text = BREAK_EVEN_MD.read_text(encoding="utf-8")
    for phrase in (
        "Sidecar Break-Even",
        "mathematical residual-sidecar gate",
        "raw negative delta requires",
        "isolated v2 literal baseline",
        "Prefix-4 raw suffix sidecars cannot strictly save bytes",
        "Do not run another residual steering family",
        "Raw suffix sidecars have zero model-viable rows",
        "Sublinear model-viable rows are not promoted evidence",
    ):
        if phrase not in text:
            raise SystemExit(f"SIDECAR_BREAK_EVEN.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated break-even report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
