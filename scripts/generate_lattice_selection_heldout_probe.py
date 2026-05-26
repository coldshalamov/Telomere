#!/usr/bin/env python3
"""Generate the held-out candidate-lattice selection probe.

The deterministic superposition fixture proves selector auditability. This
probe asks whether the current non-planted held-out candidate sets actually gain
bytes from weighted lattice selection compared with a greedy selector. It
replays existing exact dictionary candidates only; it performs no seed search.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_public_preset_control_rerun as public_rerun
import generate_schema_native_public_dictionaries as schema_native
import generate_schema_native_public_dictionary_replication as replication


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "lattice_selection_heldout_probe.json"
REPORT_MD = DOCS / "LATTICE_SELECTION_HELDOUT_PROBE.md"
GENERATED_BY = "scripts/generate_lattice_selection_heldout_probe.py"

SOURCE_PATHS = {
    "candidate_lattice_doc_sha256": DOCS / "CANDIDATE_LATTICE.md",
    "superposition_telemetry_sha256": DOCS / "superposition_telemetry.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "schema_native_replication_generator_sha256": ROOT
    / "scripts"
    / "generate_schema_native_public_dictionary_replication.py",
    "public_preset_control_rerun_generator_sha256": ROOT
    / "scripts"
    / "generate_public_preset_control_rerun.py",
}

REPLICATION_MODES = (
    "schema-v0-family-on-replication",
    "generic-public-token-dictionary-v1",
    "standards-public-v1",
    "wrong-family-public-v1",
    "same-size-random-table-v1",
    "shadow-public-v1",
)

RERUN_VARIANTS = (
    "standards-no-project-tokens",
    "standards-no-common-entries",
    "standards-family-only-no-project",
    "standards-leave-family-out",
    "standards-leave-family-out-no-project",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["start_offset"] < right["end_offset"]
        and right["start_offset"] < left["end_offset"]
    )


def greedy_select(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in sorted(
        [candidate for candidate in candidates if candidate["savings_bytes"] > 0],
        key=lambda item: (
            -item["savings_bytes"],
            -item["span_len"],
            item["start_offset"],
            item["seed_index"],
            item["entry_name"],
        ),
    ):
        if any(overlaps(row, selected_row) for selected_row in selected):
            continue
        selected.append(row)
    return sorted(
        selected,
        key=lambda item: (item["start_offset"], item["end_offset"], item["seed_index"]),
    )


def total_savings(rows: list[dict[str, Any]]) -> int:
    return sum(row["savings_bytes"] for row in rows)


def entry_rows(corpus: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    if mode.startswith("rerun:"):
        return public_rerun.variant_entries(corpus, mode.removeprefix("rerun:"))
    return replication.selected_entries(mode, corpus)


def mode_manifest() -> list[dict[str, str]]:
    rows = [
        {
            "mode_id": mode,
            "source": "schema-replication",
        }
        for mode in REPLICATION_MODES
    ]
    rows.extend(
        {
            "mode_id": f"rerun:{variant}",
            "source": "public-preset-control-rerun",
        }
        for variant in RERUN_VARIANTS
    )
    return rows


def mode_manifest_hash() -> str:
    encoded = json.dumps(mode_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def analyze_row(corpus: dict[str, Any], mode: dict[str, str]) -> dict[str, Any]:
    entries = entry_rows(corpus, mode["mode_id"])
    data = replication.corpus_bytes(corpus)
    candidates = schema_native.find_candidates(data, entries)
    weighted = schema_native.weighted_selection(candidates)
    greedy = greedy_select(candidates)
    weighted_savings = total_savings(weighted)
    greedy_savings = total_savings(greedy)
    extra = weighted_savings - greedy_savings
    return {
        "row_id": f"{mode['mode_id']}:{corpus['name']}",
        "name": corpus["name"],
        "corpus": corpus["corpus"],
        "mode_id": mode["mode_id"],
        "mode_source": mode["source"],
        "control_kind": corpus["control_kind"],
        "promotion_eligible": corpus["promotion_eligible"],
        "diagnostic_only": corpus["diagnostic_only"],
        "independence_group": corpus["independence_group"],
        "schema_family": corpus["schema_family"],
        "input_bytes": corpus["input_bytes"],
        "dictionary_entry_count": len(entries),
        "candidate_count": len(candidates),
        "positive_candidate_count": sum(
            1 for row in candidates if row["savings_bytes"] > 0
        ),
        "weighted_selected_count": len(weighted),
        "greedy_selected_count": len(greedy),
        "weighted_total_savings": weighted_savings,
        "greedy_total_savings": greedy_savings,
        "weighted_extra_savings": extra,
        "weighted_beats_greedy": extra > 0,
        "weighted_equals_greedy": extra == 0,
        "weighted_loses_to_greedy": extra < 0,
        "weighted_selected_sample": [
            {
                "start_offset": row["start_offset"],
                "span_len": row["span_len"],
                "entry_name": row["entry_name"],
                "savings_bytes": row["savings_bytes"],
            }
            for row in weighted[: schema_native.SELECTED_SAMPLE_LIMIT]
        ],
    }


def build_rows() -> list[dict[str, Any]]:
    corpora = replication.replication_corpus_manifest()
    modes = mode_manifest()
    return [analyze_row(corpus, mode) for corpus in corpora for mode in modes]


def summarize(rows: list[dict[str, Any]], superposition: dict[str, Any]) -> dict[str, Any]:
    weighted_extra_rows = [row for row in rows if row["weighted_beats_greedy"]]
    ordinary_extra_rows = [
        row
        for row in weighted_extra_rows
        if row["promotion_eligible"] and row["control_kind"] == "ordinary-structured"
    ]
    control_extra_rows = [
        row for row in weighted_extra_rows if row["control_kind"] in replication.CONTROL_KINDS
    ]
    selected_rows = [row for row in rows if row["weighted_selected_count"] > 0]
    candidate_rows = [row for row in rows if row["candidate_count"] > 0]
    promotion_met = len(ordinary_extra_rows) >= 3 and not control_extra_rows
    return {
        "probe_status": "heldout_lattice_selection_not_promoted",
        "corpus_count": len(replication.replication_corpus_manifest()),
        "mode_count": len(mode_manifest()),
        "row_count": len(rows),
        "candidate_row_count": len(candidate_rows),
        "selected_row_count": len(selected_rows),
        "total_candidate_count": sum(row["candidate_count"] for row in rows),
        "total_positive_candidate_count": sum(
            row["positive_candidate_count"] for row in rows
        ),
        "weighted_extra_savings_total": sum(
            row["weighted_extra_savings"] for row in rows
        ),
        "weighted_extra_positive_row_count": len(weighted_extra_rows),
        "ordinary_weighted_extra_row_count": len(ordinary_extra_rows),
        "ordinary_weighted_extra_groups": len(
            {row["independence_group"] for row in ordinary_extra_rows}
        ),
        "control_weighted_extra_row_count": len(control_extra_rows),
        "control_weighted_extra_groups": len(
            {row["independence_group"] for row in control_extra_rows}
        ),
        "weighted_loses_row_count": sum(1 for row in rows if row["weighted_loses_to_greedy"]),
        "superposition_fixture_promotion_met": superposition["promotion_met"],
        "superposition_fixture_extra_savings": superposition["weighted_extra_savings"],
        "promotion_met": promotion_met,
        "claim_boundary": (
            "No Seed Search; exact candidate replay only; selector utility probe; "
            "not `.tlmr` format support; not natural-corpus proof."
        ),
        "conclusion": (
            "Deterministic superposition fixtures prove selector auditability, but "
            "current non-planted held-out candidate sets show zero selected-byte "
            "improvement over greedy selection."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["candidate_count"],
            -row["weighted_total_savings"],
            row["mode_id"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    superposition = summary(load_json(DOCS / "superposition_telemetry.json"))
    rows = build_rows()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "held-out candidate-lattice selection probe",
            "performs_seed_search": False,
            "performs_exact_candidate_replay": True,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
        },
        "source_hashes": source_hashes(),
        "mode_manifest_sha256": mode_manifest_hash(),
        "mode_manifest": mode_manifest(),
        "summary": summarize(rows, superposition),
        "top_candidate_rows": top_rows(rows),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Lattice Selection Held-Out Probe",
        "",
        f"Generated by `{GENERATED_BY}` from existing exact dictionary candidate sets.",
        "This is a No Seed Search selector-utility probe. It launches no agents, is not a compression claim, is not `.tlmr` format support, and is not natural-corpus proof.",
        "",
        "## Summary",
        "",
        f"- Probe status: `{summary_payload['probe_status']}`",
        f"- Corpora: `{summary_payload['corpus_count']}`",
        f"- Modes: `{summary_payload['mode_count']}`",
        f"- Rows: `{summary_payload['row_count']}`",
        f"- Candidate rows: `{summary_payload['candidate_row_count']}`",
        f"- Selected rows: `{summary_payload['selected_row_count']}`",
        f"- Total candidates: `{summary_payload['total_candidate_count']}`",
        f"- Weighted extra savings total: `{summary_payload['weighted_extra_savings_total']}`",
        f"- Weighted-extra positive rows: `{summary_payload['weighted_extra_positive_row_count']}`",
        f"- Ordinary weighted-extra groups: `{summary_payload['ordinary_weighted_extra_groups']}`",
        f"- Control weighted-extra groups: `{summary_payload['control_weighted_extra_groups']}`",
        f"- Superposition fixture extra savings: `{summary_payload['superposition_fixture_extra_savings']}`",
        f"- Promotion met: `{summary_payload['promotion_met']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Held-Out Result",
        "",
        "The deterministic fixture result remains useful as selector correctness evidence, but this held-out replay finds no current non-planted row where weighted lattice selection beats greedy selection. That blocks the candidate-lattice lane as a compression-utility claim until future hit-discovery artifacts produce overlapping candidates with real byte gain.",
        "",
        "## Top Candidate Rows",
        "",
        "| row | mode | kind | candidates | weighted savings | greedy savings | extra | selected |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["top_candidate_rows"]:
        lines.append(
            f"| `{cell(row['name'])}` | `{cell(row['mode_id'])}` | "
            f"`{cell(row['control_kind'])}` | {row['candidate_count']} | "
            f"{row['weighted_total_savings']} | {row['greedy_total_savings']} | "
            f"{row['weighted_extra_savings']} | {row['weighted_selected_count']} |"
        )
    lines.extend(
        [
            "",
            "## Selector Scope",
            "",
            "- Weighted selection may still be the correct canonical selector.",
            "- This artifact only says current held-out exact-dictionary candidates do not benefit from the lattice.",
            "- Recursive superposition remains disallowed; selected outputs must collapse to ordinary v1/v2 records.",
            "- Reopen only when future non-planted candidates produce positive weighted-extra rows while controls stay null.",
            "",
            "## Mode Manifest",
            "",
            "| mode | source |",
            "| --- | --- |",
        ]
    )
    for mode in payload["mode_manifest"]:
        lines.append(f"| `{cell(mode['mode_id'])}` | `{cell(mode['source'])}` |")
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this probe to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.append(f"- `mode_manifest_sha256`: `{payload['mode_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated lattice selection held-out probe files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("lattice_selection_heldout_probe.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("lattice selection held-out source hashes are stale")
    if payload.get("mode_manifest_sha256") != mode_manifest_hash():
        raise SystemExit("lattice selection held-out mode manifest is stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("lattice_selection_heldout_probe.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"lattice selection held-out scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["promotion_met"]:
        raise SystemExit("lattice held-out probe cannot currently promote the lattice")
    if summary_payload["weighted_extra_savings_total"] != 0:
        raise SystemExit("current held-out lattice replay should have zero extra savings")
    if summary_payload["weighted_extra_positive_row_count"] != 0:
        raise SystemExit("current held-out lattice replay should have no positive rows")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Lattice Selection Held-Out Probe",
        "No Seed Search",
        "not `.tlmr` format support",
        "Held-Out Result",
        "Selector Scope",
        "weighted lattice selection beats greedy selection",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"LATTICE_SELECTION_HELDOUT_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated lattice selection probe"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
