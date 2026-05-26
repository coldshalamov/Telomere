#!/usr/bin/env python3
"""Budget lower-overhead sidecar record layouts for promoted descriptor rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_experimental_sidecar_descriptor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OVERHEAD_JSON = DOCS / "sidecar_record_overhead.json"
OVERHEAD_MD = DOCS / "SIDECAR_RECORD_OVERHEAD.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "experimental_sidecar_descriptor_sha256": sha256(
            DOCS / "experimental_sidecar_descriptor.json"
        ),
        "residual_payload_compressibility_sha256": sha256(
            DOCS / "residual_payload_compressibility.json"
        ),
    }


def layout_manifest() -> dict[str, Any]:
    return {
        "layouts": [
            "current_inline_descriptor",
            "u16_literal_lengths",
            "packed_seed_index_records",
            "u16_literals_packed_seed_index",
            "absolute_offset_u16_seed_u16",
            "delta_offset_u8_seed_u16",
            "delta_offset_u8_seed_u16_no_hashes",
        ],
        "scope": "budget model only; not .tlmr format support",
    }


def layout_manifest_hash() -> str:
    payload = json.dumps(layout_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def descriptor_header_bytes(row: dict[str, Any]) -> int:
    return row["container_overhead_bytes"] - row["literal_record_header_bytes"]


def budget_rows() -> list[dict[str, Any]]:
    descriptor = load_json(DOCS / "experimental_sidecar_descriptor.json")
    rows: list[dict[str, Any]] = []
    for descriptor_row in descriptor["rows"]:
        case = generate_experimental_sidecar_descriptor.selected_case(descriptor_row["name"])
        selected = case["selected"]
        seed_index_max = max(row["seed_index"] for row in selected)
        offset_max = max(row["start_offset"] for row in selected)
        starts = [row["start_offset"] for row in selected]
        max_delta = max(b - a for a, b in zip([0] + starts[:-1], starts))
        header_bytes = descriptor_header_bytes(descriptor_row)
        literal_bytes = descriptor_row["literal_bytes"]
        payload_bytes = descriptor_row["compressed_payload_bytes"]
        selected_count = descriptor_row["selected_span_count"]
        current_encoded = descriptor_row["encoded_bytes"]
        input_bytes = descriptor_row["input_bytes"]
        sidecar_seed_bytes = sum(row["seed_len"] for row in selected)
        current_seed_record_bytes = descriptor_row["sidecar_record_bytes"]
        current_sidecar_fixed_bytes = current_seed_record_bytes - sidecar_seed_bytes
        layouts = [
            {
                "layout": "current_inline_descriptor",
                "encoded_bytes": current_encoded,
                "assumption": "Research descriptor with u32 literal runs and seed bytes in every sidecar record.",
            },
            {
                "layout": "u16_literal_lengths",
                "encoded_bytes": current_encoded
                - (2 * descriptor_row["literal_record_count"]),
                "assumption": "All literal runs fit u16 lengths; sidecar records unchanged.",
            },
            {
                "layout": "packed_seed_index_records",
                "encoded_bytes": (
                    current_encoded
                    - current_seed_record_bytes
                    + selected_count * 5
                ),
                "assumption": "Each sidecar record stores tag + u16 span/prefix policy + u16 seed index.",
            },
            {
                "layout": "u16_literals_packed_seed_index",
                "encoded_bytes": (
                    current_encoded
                    - (2 * descriptor_row["literal_record_count"])
                    - current_seed_record_bytes
                    + selected_count * 5
                ),
                "assumption": "u16 literal lengths plus packed u16 seed-index sidecar records.",
            },
            {
                "layout": "absolute_offset_u16_seed_u16",
                "encoded_bytes": (
                    header_bytes
                    + literal_bytes
                    + payload_bytes
                    + selected_count * 4
                ),
                "assumption": "Separate patch table with u16 absolute offsets and u16 seed indexes; span/prefix are global.",
            },
            {
                "layout": "delta_offset_u8_seed_u16",
                "encoded_bytes": (
                    header_bytes
                    + literal_bytes
                    + payload_bytes
                    + selected_count * 3
                ),
                "assumption": "Separate patch table with u8 offset deltas and u16 seed indexes; valid only while deltas fit u8.",
            },
            {
                "layout": "delta_offset_u8_seed_u16_no_hashes",
                "encoded_bytes": (
                    header_bytes
                    - 64
                    + literal_bytes
                    + payload_bytes
                    + selected_count * 3
                ),
                "assumption": "Same as delta table, but output hashes are moved to an outer container or omitted in a research-only budget.",
            },
        ]
        for layout in layouts:
            encoded_bytes = int(layout["encoded_bytes"])
            rows.append(
                {
                    "name": descriptor_row["name"],
                    "coder": descriptor_row["coder"],
                    "layout": layout["layout"],
                    "input_bytes": input_bytes,
                    "encoded_bytes": encoded_bytes,
                    "delta_bytes": encoded_bytes - input_bytes,
                    "delta_pct": (encoded_bytes - input_bytes) / input_bytes * 100,
                    "assumption": layout["assumption"],
                    "selected_span_count": selected_count,
                    "literal_record_count": descriptor_row["literal_record_count"],
                    "payload_bytes": payload_bytes,
                    "header_bytes": header_bytes,
                    "seed_index_max": seed_index_max,
                    "offset_max": offset_max,
                    "max_offset_delta": max_delta,
                    "current_sidecar_fixed_bytes": current_sidecar_fixed_bytes,
                    "current_seed_record_bytes": current_seed_record_bytes,
                }
            )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    negative_rows = [row for row in rows if row["delta_bytes"] < 0]
    best = min(rows, key=lambda row: row["delta_bytes"])
    best_safe = min(
        (
            row
            for row in rows
            if row["layout"] != "delta_offset_u8_seed_u16_no_hashes"
        ),
        key=lambda row: row["delta_bytes"],
    )
    return {
        "layout_rows": len(rows),
        "negative_layout_rows": len(negative_rows),
        "best_layout": best["layout"],
        "best_delta_bytes": best["delta_bytes"],
        "best_safe_layout": best_safe["layout"],
        "best_safe_delta_bytes": best_safe["delta_bytes"],
        "conclusion": (
            "Packed offset/seed tables can make the promoted sidecar row full-stream negative in the budget model."
            if negative_rows
            else "No tested lower-overhead layout closes the promoted sidecar full-stream gap."
        ),
    }


def build_report() -> dict[str, Any]:
    rows = budget_rows()
    return {
        "generated_by": "scripts/generate_sidecar_record_overhead.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "layout_manifest_sha256": layout_manifest_hash(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    OVERHEAD_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Sidecar Record Overhead",
        "",
        "Generated by `scripts/generate_sidecar_record_overhead.py`.",
        "This is a record-layout budget, not `.tlmr` format support.",
        "",
        f"Layout rows: `{summary['layout_rows']}`.",
        f"Negative layout rows: `{summary['negative_layout_rows']}`.",
        f"Best layout: `{summary['best_layout']}`.",
        f"Best delta bytes: `{summary['best_delta_bytes']}`.",
        f"Best safe layout: `{summary['best_safe_layout']}`.",
        f"Best safe delta bytes: `{summary['best_safe_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Layout Rows",
        "",
        "| row | coder | layout | encoded | delta | selected spans | max offset delta | assumption |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(payload["rows"], key=lambda item: item["delta_bytes"]):
        lines.append(
            "| {name} | {coder} | {layout} | {encoded_bytes} | {delta_bytes} | "
            "{selected_span_count} | {max_offset_delta} | {assumption} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The current inline literal-run descriptor bloats because literal headers and sidecar record bytes dominate the local payload win.",
            "- A separate offset table with packed seed indexes is the first budget model that can go full-stream negative.",
            "- The budget depends on small offset deltas and seed indexes; it needs an exact decoder prototype before any format claim.",
            "- Do not broaden sidecar research until the packed-table descriptor is proven or falsified with decode and corruption tests.",
        ]
    )
    OVERHEAD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not OVERHEAD_JSON.exists() or not OVERHEAD_MD.exists():
        raise SystemExit("generated sidecar record overhead files are missing")
    payload = load_json(OVERHEAD_JSON)
    if payload.get("generated_by") != "scripts/generate_sidecar_record_overhead.py":
        raise SystemExit("sidecar_record_overhead.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("sidecar record overhead artifact hashes are stale")
    if payload.get("layout_manifest_sha256") != layout_manifest_hash():
        raise SystemExit("sidecar record overhead layout manifest hash is stale")
    if not payload.get("rows"):
        raise SystemExit("sidecar record overhead has no rows")
    text = OVERHEAD_MD.read_text(encoding="utf-8")
    for phrase in (
        "Sidecar Record Overhead",
        "record-layout budget, not `.tlmr` format support",
        "Packed offset/seed tables",
        "exact decoder prototype",
    ):
        if phrase not in text:
            raise SystemExit(f"SIDECAR_RECORD_OVERHEAD.md missing phrase: {phrase}")


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
