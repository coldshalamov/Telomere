#!/usr/bin/env python3
"""Generate deterministic candidate-lattice and superposition telemetry."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "superposition_telemetry.json"
REPORT_MD = DOCS / "SUPERPOSITION_TELEMETRY.md"
GENERATED_BY = "scripts/generate_superposition_telemetry.py"
RETAINED_DELTA_BYTES = 4

SOURCE_PATHS = {
    "candidate_lattice_doc_sha256": DOCS / "CANDIDATE_LATTICE.md",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "indexed_engine_sha256": ROOT / "src" / "indexed.rs",
    "superposition_engine_sha256": ROOT / "src" / "superposition.rs",
    "indexed_v2_tests_sha256": ROOT / "tests" / "indexed_v2.rs",
    "superposition_tests_sha256": ROOT / "tests" / "superposition.rs",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def candidate(
    fixture: str,
    label: str,
    start: int,
    span_len: int,
    savings: int,
    seed_index: int,
) -> dict[str, Any]:
    return {
        "fixture": fixture,
        "label": label,
        "start_offset": start,
        "end_offset": start + span_len,
        "span_len": span_len,
        "seed_index": seed_index,
        "seed_len": 1 if seed_index < 256 else 2,
        "encoded_len": span_len - savings,
        "savings_bytes": savings,
    }


def fixture_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": "wide-vs-two-narrow",
            "purpose": "weighted selection must keep two narrower spans instead of one tempting wide span",
            "candidates": [
                candidate("wide-vs-two-narrow", "wide", 0, 14, 10, 9),
                candidate("wide-vs-two-narrow", "left", 0, 7, 7, 1),
                candidate("wide-vs-two-narrow", "right", 7, 7, 7, 2),
                candidate("wide-vs-two-narrow", "tail", 16, 4, 2, 3),
            ],
        },
        {
            "name": "tie-break-by-position-and-seed",
            "purpose": "equal alternatives must be deterministic",
            "candidates": [
                candidate("tie-break-by-position-and-seed", "first", 0, 5, 5, 4),
                candidate("tie-break-by-position-and-seed", "same-start-later-seed", 0, 5, 5, 8),
                candidate("tie-break-by-position-and-seed", "after", 5, 5, 5, 5),
            ],
        },
        {
            "name": "all-positive-non-overlap",
            "purpose": "greedy and weighted agree when there is no overlap",
            "candidates": [
                candidate("all-positive-non-overlap", "a", 0, 6, 4, 11),
                candidate("all-positive-non-overlap", "b", 8, 6, 4, 12),
                candidate("all-positive-non-overlap", "c", 16, 6, 4, 13),
            ],
        },
        {
            "name": "non-positive-control",
            "purpose": "non-positive spans remain visible in telemetry but cannot be selected",
            "candidates": [
                candidate("non-positive-control", "zero", 0, 4, 0, 20),
                candidate("non-positive-control", "negative", 2, 6, -2, 21),
                candidate("non-positive-control", "positive", 10, 5, 3, 22),
            ],
        },
    ]


def fixtures_hash() -> str:
    encoded = json.dumps(fixture_manifest(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["start_offset"] < right["end_offset"] and right["start_offset"] < left["end_offset"]


def non_overlapping(rows: list[dict[str, Any]]) -> bool:
    ordered = sorted(rows, key=lambda row: (row["start_offset"], row["end_offset"]))
    return all(
        ordered[index]["end_offset"] <= ordered[index + 1]["start_offset"]
        for index in range(len(ordered) - 1)
    )


def greedy_select(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in sorted(
        candidates,
        key=lambda item: (
            -item["savings_bytes"],
            -item["span_len"],
            item["start_offset"],
            item["seed_index"],
        ),
    ):
        if row["savings_bytes"] <= 0:
            continue
        if any(overlaps(row, selected_row) for selected_row in selected):
            continue
        selected.append(row)
    return sorted(selected, key=lambda item: (item["start_offset"], item["seed_index"]))


def weighted_select(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positive = [row for row in candidates if row["savings_bytes"] > 0]
    ordered = sorted(
        positive,
        key=lambda item: (
            item["end_offset"],
            item["start_offset"],
            -item["savings_bytes"],
            item["seed_index"],
        ),
    )
    previous: list[int] = []
    for index, row in enumerate(ordered):
        prev = -1
        for other_index in range(index - 1, -1, -1):
            if ordered[other_index]["end_offset"] <= row["start_offset"]:
                prev = other_index
                break
        previous.append(prev)

    best: list[tuple[int, tuple[str, ...], tuple[int, ...]]] = [(0, (), ())]
    for index, row in enumerate(ordered, start=1):
        without = best[index - 1]
        prev_score, prev_labels, prev_seeds = best[previous[index - 1] + 1]
        with_row = (
            prev_score + row["savings_bytes"],
            prev_labels + (row["label"],),
            prev_seeds + (row["seed_index"],),
        )
        if (with_row[0], tuple(-seed for seed in with_row[2])) > (
            without[0],
            tuple(-seed for seed in without[2]),
        ):
            best.append(with_row)
        else:
            best.append(without)
    selected_labels = set(best[-1][1])
    return sorted(
        [row for row in ordered if row["label"] in selected_labels],
        key=lambda item: (item["start_offset"], item["seed_index"]),
    )


def total_savings(rows: list[dict[str, Any]]) -> int:
    return sum(row["savings_bytes"] for row in rows)


def lattice_width(candidates: list[dict[str, Any]]) -> int:
    points = sorted({point for row in candidates for point in (row["start_offset"], row["end_offset"])})
    max_width = 0
    for point in points:
        active = sum(
            1 for row in candidates if row["start_offset"] <= point < row["end_offset"]
        )
        max_width = max(max_width, active)
    return max_width


def explain_discard(
    row: dict[str, Any],
    selected: list[dict[str, Any]],
    greedy_selected: list[dict[str, Any]],
) -> tuple[str, bool]:
    if row["savings_bytes"] <= 0:
        return "non-positive-savings", False
    overlapping_selected = [item for item in selected if overlaps(row, item)]
    if not overlapping_selected:
        return "unexplained-positive-non-overlap", False
    overlap_savings = total_savings(overlapping_selected)
    retained = abs(overlap_savings - row["savings_bytes"]) <= RETAINED_DELTA_BYTES
    if any(item["label"] == row["label"] for item in greedy_selected):
        return "greedy-would-select-but-weighted-overlap-set-wins", retained
    if overlap_savings >= row["savings_bytes"]:
        return "overlaps-selected-set-with-equal-or-higher-total-savings", retained
    return "overlaps-selected-set-but-needs-review", retained


def analyze_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    candidates = fixture["candidates"]
    weighted = weighted_select(candidates)
    greedy = greedy_select(candidates)
    selected_labels = {row["label"] for row in weighted}
    greedy_labels = {row["label"] for row in greedy}
    discarded = []
    retained_count = 0
    unexplained_count = 0
    for row in candidates:
        if row["label"] in selected_labels:
            continue
        explanation, retained = explain_discard(row, weighted, greedy)
        retained_count += int(retained)
        unexplained_count += int(explanation.startswith("unexplained"))
        discarded.append(
            {
                "label": row["label"],
                "savings_bytes": row["savings_bytes"],
                "overlaps_selected": [
                    selected_row["label"]
                    for selected_row in weighted
                    if overlaps(row, selected_row)
                ],
                "greedy_would_select": row["label"] in greedy_labels,
                "retained_for_telemetry": retained,
                "explanation": explanation,
            }
        )
    return {
        "name": fixture["name"],
        "purpose": fixture["purpose"],
        "candidate_count": len(candidates),
        "max_lattice_width": lattice_width(candidates),
        "weighted_selected_labels": [row["label"] for row in weighted],
        "greedy_selected_labels": [row["label"] for row in greedy],
        "weighted_total_savings": total_savings(weighted),
        "greedy_total_savings": total_savings(greedy),
        "weighted_beats_greedy": total_savings(weighted) > total_savings(greedy),
        "selected_non_overlapping": non_overlapping(weighted),
        "selected_positive_savings": all(row["savings_bytes"] > 0 for row in weighted),
        "discarded": discarded,
        "discarded_count": len(discarded),
        "retained_alternative_count": retained_count,
        "unexplained_discard_count": unexplained_count,
        "candidates": candidates,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_count = sum(row["candidate_count"] for row in rows)
    retained = sum(row["retained_alternative_count"] for row in rows)
    discarded = sum(row["discarded_count"] for row in rows)
    unexplained = sum(row["unexplained_discard_count"] for row in rows)
    weighted_gain = sum(row["weighted_total_savings"] for row in rows)
    greedy_gain = sum(row["greedy_total_savings"] for row in rows)
    weighted_beats = sum(1 for row in rows if row["weighted_beats_greedy"])
    all_non_overlapping = all(row["selected_non_overlapping"] for row in rows)
    all_positive = all(row["selected_positive_savings"] for row in rows)
    promotion_met = (
        weighted_beats >= 1
        and unexplained == 0
        and retained >= 1
        and all_non_overlapping
        and all_positive
    )
    return {
        "fixture_count": len(rows),
        "candidate_count": candidate_count,
        "retained_alternative_count": retained,
        "discarded_candidate_count": discarded,
        "explained_discard_count": discarded - unexplained,
        "unexplained_discard_count": unexplained,
        "max_lattice_width": max(row["max_lattice_width"] for row in rows),
        "weighted_total_savings": weighted_gain,
        "greedy_total_savings": greedy_gain,
        "weighted_extra_savings": weighted_gain - greedy_gain,
        "weighted_beats_greedy_fixture_count": weighted_beats,
        "all_selected_non_overlapping": all_non_overlapping,
        "all_selected_positive_savings": all_positive,
        "promotion_met": promotion_met,
        "claim_level": "selection_telemetry_correctness_only",
        "conclusion": (
            "Candidate-lattice telemetry satisfies the deterministic selector gate."
            if promotion_met
            else "Candidate-lattice telemetry is incomplete; keep the lane open."
        ),
    }


def build_report() -> dict[str, Any]:
    rows = [analyze_fixture(fixture) for fixture in fixture_manifest()]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_artifact_hashes": source_artifact_hashes(),
        "fixture_manifest_sha256": fixtures_hash(),
        "retained_delta_bytes": RETAINED_DELTA_BYTES,
        "summary": summarize(rows),
        "fixtures": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Superposition Telemetry",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "This is a deterministic candidate-lattice telemetry artifact, not `.tlmr` format support and not natural-corpus compression evidence.",
        "",
        "## Summary",
        "",
        f"- Fixtures: `{summary['fixture_count']}`",
        f"- Candidates: `{summary['candidate_count']}`",
        f"- Retained alternatives: `{summary['retained_alternative_count']}`",
        f"- Discarded candidates: `{summary['discarded_candidate_count']}`",
        f"- Explained discards: `{summary['explained_discard_count']}`",
        f"- Unexplained discards: `{summary['unexplained_discard_count']}`",
        f"- Max lattice width: `{summary['max_lattice_width']}`",
        f"- Weighted total savings: `{summary['weighted_total_savings']}`",
        f"- Greedy total savings: `{summary['greedy_total_savings']}`",
        f"- Weighted extra savings: `{summary['weighted_extra_savings']}`",
        f"- Weighted beats greedy fixtures: `{summary['weighted_beats_greedy_fixture_count']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        f"- Claim level: `{summary['claim_level']}`",
        "",
        summary["conclusion"],
        "",
        "## Promotion Gate",
        "",
        "- At least one deterministic overlap fixture must show weighted selection beating greedy selection.",
        "- Every discarded candidate must have an explicit explanation.",
        "- At least one discarded positive candidate must be retained as telemetry.",
        "- Selected candidates must remain non-overlapping and positive-saving.",
        "- This gate only validates selector auditability; it does not prove new compression viability.",
        "",
        "## Fixtures",
        "",
        "| fixture | weighted | greedy | extra savings | retained | unexplained |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in payload["fixtures"]:
        lines.append(
            f"| `{row['name']}` | `{', '.join(row['weighted_selected_labels'])}` | "
            f"`{', '.join(row['greedy_selected_labels'])}` | "
            f"{row['weighted_total_savings'] - row['greedy_total_savings']} | "
            f"{row['retained_alternative_count']} | {row['unexplained_discard_count']} |"
        )
    lines.extend(
        [
            "",
            "## Discard Explanations",
            "",
            "| fixture | candidate | explanation | retained |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in payload["fixtures"]:
        for discarded in row["discarded"]:
            lines.append(
                f"| `{row['name']}` | `{discarded['label']}` | "
                f"`{discarded['explanation']}` | `{discarded['retained_for_telemetry']}` |"
            )
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in payload["source_artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `fixture_manifest_sha256`: `{payload['fixture_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated superposition telemetry files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("superposition_telemetry.json has wrong generated_by marker")
    if payload.get("source_artifact_hashes") != source_artifact_hashes():
        raise SystemExit("superposition telemetry source hashes are stale")
    if payload.get("fixture_manifest_sha256") != fixtures_hash():
        raise SystemExit("superposition telemetry fixture manifest is stale")
    summary = payload.get("summary", {})
    if not summary.get("all_selected_non_overlapping"):
        raise SystemExit("superposition telemetry selected spans must be non-overlapping")
    if summary.get("unexplained_discard_count") != 0:
        raise SystemExit("superposition telemetry has unexplained discards")
    if summary.get("promotion_met") and summary.get("weighted_beats_greedy_fixture_count", 0) < 1:
        raise SystemExit("superposition telemetry promotion requires weighted > greedy")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Superposition Telemetry",
        f"Generated by `{GENERATED_BY}`",
        "not `.tlmr` format support",
        "Promotion Gate",
        "Discard Explanations",
        "weighted selection beating greedy selection",
        "selector auditability",
    ):
        if phrase not in text:
            raise SystemExit(f"SUPERPOSITION_TELEMETRY.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated superposition telemetry report",
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
