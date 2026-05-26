#!/usr/bin/env python3
"""Run packed sidecar descriptors across selected residual control rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_experimental_sidecar_descriptor
import generate_packed_sidecar_descriptor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CONTROLS_JSON = DOCS / "packed_sidecar_controls.json"
CONTROLS_MD = DOCS / "PACKED_SIDECAR_CONTROLS.md"
CODERS = ("zlib_level9", "lzma_preset9")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "packed_sidecar_descriptor_sha256": sha256(
            DOCS / "packed_sidecar_descriptor.json"
        ),
        "residual_payload_compressibility_sha256": sha256(
            DOCS / "residual_payload_compressibility.json"
        ),
    }


def control_manifest() -> dict[str, Any]:
    return {
        "coders": CODERS,
        "source_rows": "all selected payload rows from residual_payload_compressibility.json",
        "scope": "control matrix only; not .tlmr format support",
    }


def control_manifest_hash() -> str:
    payload = json.dumps(control_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def build_rows() -> list[dict[str, Any]]:
    payload = load_json(DOCS / "residual_payload_compressibility.json")
    rows: list[dict[str, Any]] = []
    for payload_row in payload["payload_rows"]:
        case = generate_experimental_sidecar_descriptor.selected_case(payload_row["name"])
        for coder in CODERS:
            try:
                descriptor = generate_packed_sidecar_descriptor.encode_case(case, coder)
            except ValueError as exc:
                rows.append(
                    {
                        "name": payload_row["name"],
                        "coder": coder,
                        "role": payload_row["role"],
                        "control_kind": payload_row["control_kind"],
                        "corpus": payload_row["corpus"],
                        "transform": payload_row["transform"],
                        "residual_scheme": payload_row["residual_scheme"],
                        "encoded": False,
                        "skip_reason": str(exc),
                        "input_bytes": len(case["original"]),
                        "encoded_bytes": None,
                        "delta_bytes": None,
                        "selected_span_count": payload_row["selected_span_count"],
                        "decode_verified": False,
                        "corrupt_rejections": {},
                    }
                )
                continue
            rows.append(
                {
                    **descriptor,
                    "encoded": True,
                    "skip_reason": None,
                    "role": payload_row["role"],
                    "control_kind": payload_row["control_kind"],
                    "corpus": payload_row["corpus"],
                    "transform": payload_row["transform"],
                    "residual_scheme": payload_row["residual_scheme"],
                }
            )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    encoded_rows = [row for row in rows if row["encoded"]]
    skipped_rows = [row for row in rows if not row["encoded"]]
    negative_rows = [row for row in encoded_rows if row["delta_bytes"] < 0]
    heldout_rows = [row for row in encoded_rows if row["role"] == "held-out"]
    ordinary_heldout_rows = [
        row
        for row in heldout_rows
        if row["control_kind"] == "ordinary-structured"
    ]
    negative_by_role = Counter(row["role"] for row in negative_rows)
    negative_by_control = Counter(row["control_kind"] for row in negative_rows)
    unique_negative_cases = {row["name"] for row in negative_rows}
    unique_ordinary_heldout_negative = {
        row["name"]
        for row in ordinary_heldout_rows
        if row["delta_bytes"] < 0
    }
    best = min(encoded_rows, key=lambda row: row["delta_bytes"])
    best_ordinary_heldout = min(
        ordinary_heldout_rows,
        key=lambda row: row["delta_bytes"],
        default=None,
    )
    return {
        "control_rows": len(rows),
        "encoded_rows": len(encoded_rows),
        "skipped_rows": len(skipped_rows),
        "unique_source_rows": len({row["name"] for row in rows}),
        "decode_verified_rows": sum(1 for row in encoded_rows if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in encoded_rows
        ),
        "full_stream_negative_rows": len(negative_rows),
        "unique_negative_cases": len(unique_negative_cases),
        "ordinary_heldout_negative_cases": len(unique_ordinary_heldout_negative),
        "negative_rows_by_role": dict(negative_by_role),
        "negative_rows_by_control_kind": dict(negative_by_control),
        "best_case": best["name"],
        "best_coder": best["coder"],
        "best_delta_bytes": best["delta_bytes"],
        "best_ordinary_heldout_case": (
            best_ordinary_heldout["name"] if best_ordinary_heldout else None
        ),
        "best_ordinary_heldout_delta_bytes": (
            best_ordinary_heldout["delta_bytes"] if best_ordinary_heldout else None
        ),
        "conclusion": (
            "Packed sidecar descriptors produce multiple full-stream negative rows, including ordinary held-out controls."
            if unique_ordinary_heldout_negative
            else "Packed sidecar descriptors do not generalize beyond the promoted row."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if row["encoded"]],
        key=lambda row: row["delta_bytes"],
    )[:limit]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_packed_sidecar_controls.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "control_manifest_sha256": control_manifest_hash(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    CONTROLS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Packed Sidecar Controls",
        "",
        "Generated by `scripts/generate_packed_sidecar_controls.py`.",
        "This is a packed descriptor control matrix, not `.tlmr` format support.",
        "",
        f"Control rows: `{summary['control_rows']}`.",
        f"Encoded rows: `{summary['encoded_rows']}`.",
        f"Skipped rows: `{summary['skipped_rows']}`.",
        f"Unique source rows: `{summary['unique_source_rows']}`.",
        f"Decode verified rows: `{summary['decode_verified_rows']}`.",
        f"All corrupt rejections passed: `{summary['all_corrupt_rejections_passed']}`.",
        f"Full-stream negative rows: `{summary['full_stream_negative_rows']}`.",
        f"Unique negative cases: `{summary['unique_negative_cases']}`.",
        f"Ordinary held-out negative cases: `{summary['ordinary_heldout_negative_cases']}`.",
        f"Best case: `{summary['best_case']}`.",
        f"Best delta bytes: `{summary['best_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Best Rows",
        "",
        "| row | role | control | coder | input | encoded | delta | spans | decode | corrupt rejected |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {role} | {control_kind} | {coder} | {input_bytes} | "
            "{encoded_bytes} | {delta_bytes} | {selected_span_count} | "
            "{decode_verified} | {corrupt} |".format(
                corrupt=all(row["corrupt_rejections"].values()),
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Packed sidecar descriptors are no longer a single-row-only signal if ordinary held-out negative cases remain above zero.",
            "- Shadow and binary controls are reported separately so vocabulary or binary-shape artifacts cannot hide in the aggregate.",
            "- This still does not make `.tlmr` format support; it is a research descriptor matrix.",
            "- The next step is to freeze descriptor assumptions and compare against existing v2 records on a wider generated corpus matrix.",
        ]
    )
    CONTROLS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not CONTROLS_JSON.exists() or not CONTROLS_MD.exists():
        raise SystemExit("generated packed sidecar control files are missing")
    payload = load_json(CONTROLS_JSON)
    if payload.get("generated_by") != "scripts/generate_packed_sidecar_controls.py":
        raise SystemExit("packed_sidecar_controls.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("packed sidecar controls artifact hashes are stale")
    if payload.get("control_manifest_sha256") != control_manifest_hash():
        raise SystemExit("packed sidecar controls manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("decode_verified_rows") != summary.get("encoded_rows"):
        raise SystemExit("packed sidecar controls decode verification failed")
    if not summary.get("all_corrupt_rejections_passed"):
        raise SystemExit("packed sidecar controls corrupt rejection failed")
    text = CONTROLS_MD.read_text(encoding="utf-8")
    for phrase in (
        "Packed Sidecar Controls",
        "packed descriptor control matrix",
        "Ordinary held-out negative cases",
        "Shadow and binary controls",
    ):
        if phrase not in text:
            raise SystemExit(f"PACKED_SIDECAR_CONTROLS.md missing phrase: {phrase}")


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
