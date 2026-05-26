#!/usr/bin/env python3
"""Generate a bounded FASTA ablation for the seed-table replay signal.

This artifact asks whether the only negative replay group in the current
seed-table evidence is sequence payload signal or synthetic FASTA header
vocabulary. It reuses the frozen leave-FASTA-out preset table, performs no
seed search, and does not promote any `.tlmr` format claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_seed_table_preset_probe as preset_probe


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "seed_table_fasta_ablation.json"
REPORT_MD = DOCS / "SEED_TABLE_FASTA_ABLATION.md"
GENERATED_BY = "scripts/generate_seed_table_fasta_ablation.py"

SOURCE_PATHS = {
    "seed_table_preset_replay_sha256": DOCS / "seed_table_preset_replay.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "seed_table_preset_probe_generator_sha256": ROOT
    / "scripts"
    / "generate_seed_table_preset_probe.py",
    "corpus_matrix_sha256": DOCS / "corpus_matrix.json",
    "corpus_matrix_generator_sha256": ROOT / "scripts" / "generate_corpus_matrix.py",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "fasta_ablation_generator_sha256": ROOT
    / "scripts"
    / "generate_seed_table_fasta_ablation.py",
}

FASTA_CASES = [
    {
        "name": "fasta-original-replay",
        "role": "diagnostic",
        "control_kind": "ordinary-structured",
        "independence_group": "sequence-fasta-original",
        "promotion_eligible": False,
        "builder": "original",
        "description": "current generated FASTA bytes with synthetic headers intact",
    },
    {
        "name": "fasta-header-scrubbed-sequence",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "sequence-fasta-scrubbed",
        "promotion_eligible": True,
        "builder": "header-scrubbed-sequence",
        "description": "same sequence lines and wrapping with header vocabulary replaced by deterministic hex IDs",
    },
    {
        "name": "fasta-sequence-only-wrapped",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "sequence-fasta-wrapped",
        "promotion_eligible": True,
        "builder": "sequence-only-wrapped",
        "description": "headers removed; sequence lines and wrapping preserved",
    },
    {
        "name": "fasta-sequence-only-concat",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "sequence-fasta-concat",
        "promotion_eligible": True,
        "builder": "sequence-only-concat",
        "description": "headers and FASTA syntax removed; sequence bytes concatenated",
    },
    {
        "name": "fasta-header-only-control",
        "role": "control",
        "control_kind": "fasta-header-control",
        "independence_group": "fasta-header-only-control",
        "promotion_eligible": False,
        "builder": "header-only-random-sequence",
        "description": "original headers retained while sequence lines are deterministic random ACGTN",
    },
    {
        "name": "fasta-header-scrubbed-random-sequence-control",
        "role": "control",
        "control_kind": "fasta-random-sequence-control",
        "independence_group": "fasta-scrubbed-random-control",
        "promotion_eligible": False,
        "builder": "header-scrubbed-random-sequence",
        "description": "headers scrubbed and sequence lines replaced by deterministic random ACGTN",
    },
    {
        "name": "fasta-header-scrubbed-shuffled-sequence-control",
        "role": "control",
        "control_kind": "fasta-shuffled-sequence-control",
        "independence_group": "fasta-scrubbed-shuffled-control",
        "promotion_eligible": False,
        "builder": "header-scrubbed-shuffled-sequence",
        "description": "headers scrubbed and per-record bases shuffled while counts and wrapping are preserved",
    },
]

REPLAY_CONTROL_CASES = [
    {
        "name": "shadow-json-control-replay",
        "corpus": "shadow-json",
        "control_kind": "paired-shadow-control",
        "independence_group": "shadow-json",
        "description": "existing paired shadow-vocabulary control from seed-table replay",
    },
    {
        "name": "binary-tlv-control-replay",
        "corpus": "binary-tlv",
        "control_kind": "binary-control",
        "independence_group": "binary-tlv",
        "description": "existing binary TLV control from seed-table replay",
    },
    {
        "name": "binary-varint-control-replay",
        "corpus": "binary-varint",
        "control_kind": "binary-control",
        "independence_group": "binary-varint",
        "description": "existing binary varint control from seed-table replay",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def case_manifest() -> dict[str, Any]:
    return {
        "name": "seed-table-fasta-ablation-v0",
        "scope": "bounded FASTA attribution ablation",
        "not_tlmr_format_support": True,
        "not_natural_corpus_proof": True,
        "performs_seed_search": False,
        "table_policy": "leave FASTA out of canonical preset training, then replay ablations",
        "max_seed_len": preset_probe.MAX_SEED_LEN,
        "table_entry_count": preset_probe.TABLE_ENTRY_COUNT,
        "span_lens": list(preset_probe.SPAN_LENS),
        "span_step": preset_probe.SPAN_STEP,
        "fasta_cases": FASTA_CASES,
        "replay_control_cases": REPLAY_CONTROL_CASES,
        "sequence_lane_reopen_rule": (
            "header-scrubbed sequence and at least one sequence-only row must be "
            "negative, all controls must be non-negative, canonical rows must beat "
            "sha256 baseline, and selected spans must be mostly sequence-attributed"
        ),
    }


def case_manifest_hash() -> str:
    payload = json.dumps(case_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def split_line_ending(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n"):
        return line[:-1], b"\n"
    return line, b""


def parse_fasta(data: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in data.splitlines(keepends=True):
        body, newline = split_line_ending(line)
        if body.startswith(b">"):
            if current is not None:
                records.append(current)
            current = {"header": body, "newline": newline, "sequence_lines": []}
        elif current is not None:
            current["sequence_lines"].append((body, newline))
    if current is not None:
        records.append(current)
    if not records:
        raise RuntimeError("generated FASTA corpus produced no records")
    return records


def scrub_header(index: int, length: int) -> bytes:
    digest = hashlib.sha256(f"fasta-header-scrub\0{index}".encode("ascii")).hexdigest()
    material = (">" + digest * ((length // len(digest)) + 2)).encode("ascii")
    return material[:length]


def deterministic_sequence(label: str, length: int) -> bytes:
    alphabet = b"ACGTN"
    out = bytearray()
    counter = 0
    while len(out) < length:
        digest = hashlib.sha256(f"{label}\0{counter}".encode("ascii")).digest()
        for byte in digest:
            out.append(alphabet[byte % len(alphabet)])
            if len(out) == length:
                break
        counter += 1
    return bytes(out)


def shuffled_record_sequence(index: int, lines: list[tuple[bytes, bytes]]) -> bytes:
    sequence = b"".join(line for line, _newline in lines)
    keyed = [
        (
            hashlib.sha256(
                b"fasta-shuffle\0"
                + index.to_bytes(4, "big")
                + pos.to_bytes(4, "big")
                + bytes([base])
            ).digest(),
            base,
        )
        for pos, base in enumerate(sequence)
    ]
    return bytes(base for _key, base in sorted(keyed))


def append_segment(
    parts: list[bytes], regions: list[dict[str, Any]], label: str, data: bytes
) -> None:
    if not data:
        return
    start = sum(len(part) for part in parts)
    parts.append(data)
    regions.append({"start": start, "end": start + len(data), "region": label})


def split_by_lengths(data: bytes, lengths: list[int]) -> list[bytes]:
    out = []
    offset = 0
    for length in lengths:
        out.append(data[offset : offset + length])
        offset += length
    return out


def build_from_records(builder: str) -> tuple[bytes, list[dict[str, Any]]]:
    records = parse_fasta(generate_corpus_matrix.fasta_bytes())
    parts: list[bytes] = []
    regions: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        sequence_lines = record["sequence_lines"]
        line_lengths = [len(line) for line, _newline in sequence_lines]
        if builder == "original":
            header = record["header"]
            lines = [line for line, _newline in sequence_lines]
            include_header = True
            concat_only = False
        elif builder == "header-scrubbed-sequence":
            header = scrub_header(index, len(record["header"]))
            lines = [line for line, _newline in sequence_lines]
            include_header = True
            concat_only = False
        elif builder == "sequence-only-wrapped":
            header = b""
            lines = [line for line, _newline in sequence_lines]
            include_header = False
            concat_only = False
        elif builder == "sequence-only-concat":
            header = b""
            lines = [b"".join(line for line, _newline in sequence_lines)]
            include_header = False
            concat_only = True
        elif builder == "header-only-random-sequence":
            header = record["header"]
            random_sequence = deterministic_sequence(
                f"header-only-random-sequence:{index}", sum(line_lengths)
            )
            lines = split_by_lengths(random_sequence, line_lengths)
            include_header = True
            concat_only = False
        elif builder == "header-scrubbed-random-sequence":
            header = scrub_header(index, len(record["header"]))
            random_sequence = deterministic_sequence(
                f"header-scrubbed-random-sequence:{index}", sum(line_lengths)
            )
            lines = split_by_lengths(random_sequence, line_lengths)
            include_header = True
            concat_only = False
        elif builder == "header-scrubbed-shuffled-sequence":
            header = scrub_header(index, len(record["header"]))
            shuffled = shuffled_record_sequence(index, sequence_lines)
            lines = split_by_lengths(shuffled, line_lengths)
            include_header = True
            concat_only = False
        else:
            raise ValueError(builder)

        if include_header:
            append_segment(parts, regions, "header", header)
            append_segment(parts, regions, "syntax", record["newline"])
        for line_index, line in enumerate(lines):
            append_segment(parts, regions, "sequence", line)
            if not concat_only:
                newline = sequence_lines[line_index][1]
                append_segment(parts, regions, "syntax", newline)
    return b"".join(parts), regions


def control_corpus_bytes(corpus: str) -> bytes:
    row = {
        "family": "corpus-matrix",
        "corpus": corpus,
    }
    return preset_probe.corpus_bytes(row)


def all_region(data: bytes, region: str) -> list[dict[str, Any]]:
    return [{"start": 0, "end": len(data), "region": region}] if data else []


def discovery_rows(exclude_corpus: str) -> list[dict[str, Any]]:
    return [
        row
        for row in preset_probe.corpus_manifest()
        if row["can_train"] and row["corpus"] != exclude_corpus
    ]


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for item in FASTA_CASES:
        data, regions = build_from_records(item["builder"])
        cases.append(
            {
                **item,
                "family": "fasta-ablation",
                "corpus": item["builder"],
                "split": "bounded-fasta-ablation",
                "paired_with": "fasta",
                "can_train": False,
                "data": data,
                "regions": regions,
            }
        )
    for item in REPLAY_CONTROL_CASES:
        data = control_corpus_bytes(item["corpus"])
        cases.append(
            {
                **item,
                "role": "control",
                "family": "corpus-matrix",
                "split": "bounded-fasta-ablation-control",
                "paired_with": None,
                "promotion_eligible": False,
                "can_train": False,
                "data": data,
                "regions": all_region(data, "control"),
            }
        )
    return cases


def classify_span(
    regions: list[dict[str, Any]], start: int, end: int
) -> tuple[str, list[str]]:
    labels = {
        row["region"]
        for row in regions
        if row["start"] < end and row["end"] > start and row["region"] != "syntax"
    }
    if not labels:
        labels = {
            row["region"]
            for row in regions
            if row["start"] < end and row["end"] > start
        }
    if not labels:
        return "unattributed", []
    if len(labels) == 1:
        label = next(iter(labels))
        return label, sorted(labels)
    return "mixed", sorted(labels)


def attribution_summary(
    selected: list[dict[str, Any]], regions: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: dict[str, int] = defaultdict(int)
    savings: dict[str, int] = defaultdict(int)
    for row in selected:
        region, labels = classify_span(regions, row["start_offset"], row["end_offset"])
        row["region"] = region
        row["region_labels"] = labels
        row["span_ascii"] = bytes.fromhex(row["span_hex"]).decode("ascii", errors="replace")
        counts[region] += 1
        savings[region] += int(row["savings_bytes"])
    total = len(selected)
    sequence_count = counts.get("sequence", 0)
    header_count = counts.get("header", 0)
    return {
        "selected_span_count": total,
        "selected_spans_by_region": dict(sorted(counts.items())),
        "savings_bytes_by_region": dict(sorted(savings.items())),
        "sequence_selected_spans": sequence_count,
        "header_selected_spans": header_count,
        "sequence_selected_ratio": round(sequence_count / total, 4) if total else 0.0,
        "header_selected_ratio": round(header_count / total, 4) if total else 0.0,
    }


def analyze_data_with_table(
    row_id: int,
    case: dict[str, Any],
    mode: str,
    entries: list[bytes],
    table_payload_bytes: int,
) -> dict[str, Any]:
    data = case["data"]
    maps = preset_probe.prefix_maps(entries)
    candidates: list[dict[str, Any]] = []
    for span_len, mapping in maps.items():
        for start in preset_probe.iter_starts(data, span_len):
            span = data[start : start + span_len]
            hit = mapping.get(span)
            if hit is None:
                continue
            encoded_len = preset_probe.SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
            candidates.append(
                {
                    "start_offset": start,
                    "end_offset": start + span_len,
                    "span_len": span_len,
                    "seed_index": int(hit["seed_index"]),
                    "seed_len": int(hit["seed_len"]),
                    "seed_hex": hit["seed_hex"],
                    "encoded_len": encoded_len,
                    "savings_bytes": span_len - encoded_len,
                    "span_hex": span.hex(),
                }
            )
    selected = preset_probe.select_weighted(candidates)
    attribution = attribution_summary(selected, case["regions"])
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    literal_bytes = preset_probe.literal_record_bytes(len(data), selected)
    metadata_bytes = (
        preset_probe.V2_HEADER_AND_LAYER_BYTES
        + preset_probe.PRESET_METADATA_BYTES
        + table_payload_bytes
    )
    encoded_bytes = literal_bytes + selected_record_bytes + metadata_bytes
    delta_bytes = encoded_bytes - len(data)
    row = {
        key: value
        for key, value in case.items()
        if key not in {"data", "regions", "builder"}
    }
    return {
        **row,
        "row_id": f"{mode}:{row_id:03d}:{case['name']}",
        "mode": mode,
        "input_bytes": len(data),
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta_bytes,
        "delta_pct": round((delta_bytes / len(data)) * 100, 4) if data else 0.0,
        "metadata_bytes": metadata_bytes,
        "v2_header_and_layer_bytes": preset_probe.V2_HEADER_AND_LAYER_BYTES,
        "preset_metadata_bytes": preset_probe.PRESET_METADATA_BYTES,
        "table_payload_bytes": table_payload_bytes,
        "literal_record_bytes": literal_bytes,
        "selected_record_bytes": selected_record_bytes,
        "candidate_hits": len(candidates),
        "selected_span_count": len(selected),
        "exact_decode": preset_probe.prove_decode(data, entries, selected),
        "corrupt_rejection": preset_probe.corrupt_rejection_verified(entries, selected),
        "source_control_group": case["control_kind"],
        "table_sha256": preset_probe.table_digest(entries),
        "attribution": attribution,
        "selected_span_sample": selected[: preset_probe.SELECTED_SPAN_SAMPLE_LIMIT],
    }


def analyze_cases() -> list[dict[str, Any]]:
    cases = build_cases()
    canonical_entries = preset_probe.ranked_span_entries(discovery_rows("fasta"))
    sha_entries = preset_probe.sha256_baseline_table()
    rows: list[dict[str, Any]] = []
    for row_id, case in enumerate(cases):
        rows.append(
            analyze_data_with_table(
                row_id,
                case,
                "leave-fasta-out-canonical",
                canonical_entries,
                0,
            )
        )
        rows.append(
            analyze_data_with_table(
                row_id,
                case,
                "sha256-baseline",
                sha_entries,
                0,
            )
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)
    canonical = by_mode["leave-fasta-out-canonical"]
    sha = by_mode["sha256-baseline"]
    by_name = {row["name"]: row for row in canonical}
    original = by_name["fasta-original-replay"]
    scrubbed = by_name["fasta-header-scrubbed-sequence"]
    sequence_only = [
        by_name["fasta-sequence-only-wrapped"],
        by_name["fasta-sequence-only-concat"],
    ]
    controls = [row for row in canonical if row["role"] == "control"]
    control_negative_groups = {
        row["independence_group"] for row in controls if row["delta_bytes"] < 0
    }
    control_negative_cases = [row["name"] for row in controls if row["delta_bytes"] < 0]
    sequence_negative_cases = [
        row["name"]
        for row in [scrubbed, *sequence_only]
        if row["delta_bytes"] < 0
    ]
    sequence_attribution_rows = [scrubbed, *sequence_only]
    total_sequence_selected = sum(
        row["attribution"]["sequence_selected_spans"] for row in canonical
    )
    total_header_selected = sum(
        row["attribution"]["header_selected_spans"] for row in canonical
    )
    sequence_candidate_sequence_selected = sum(
        row["attribution"]["sequence_selected_spans"]
        for row in sequence_attribution_rows
    )
    sequence_candidate_header_selected = sum(
        row["attribution"]["header_selected_spans"] for row in sequence_attribution_rows
    )
    sequence_total = sum(row["selected_span_count"] for row in sequence_attribution_rows)
    selected_spans_mostly_sequence = (
        sequence_total > 0
        and sequence_candidate_sequence_selected > sequence_candidate_header_selected
        and sequence_candidate_sequence_selected / sequence_total >= 0.6
    )
    canonical_selected = sum(row["selected_span_count"] for row in canonical)
    sha_selected = sum(row["selected_span_count"] for row in sha)
    canonical_best = min(canonical, key=lambda row: row["delta_bytes"])
    sha_best_delta = min(row["delta_bytes"] for row in sha)
    beats_sha = canonical_selected > sha_selected and canonical_best["delta_bytes"] < sha_best_delta
    header_only = by_name["fasta-header-only-control"]
    sequence_lane_reopen_candidate = (
        scrubbed["delta_bytes"] < 0
        and any(row["delta_bytes"] < 0 for row in sequence_only)
        and not control_negative_groups
        and beats_sha
        and selected_spans_mostly_sequence
    )
    stop_reasons = []
    if original["delta_bytes"] < 0 and scrubbed["delta_bytes"] >= 0:
        stop_reasons.append("win_disappears_after_header_scrubbing")
    if header_only["delta_bytes"] < 0:
        stop_reasons.append("header_only_control_negative")
    if control_negative_groups:
        stop_reasons.append("control_negative_group_present")
    if sequence_total and not selected_spans_mostly_sequence:
        stop_reasons.append("selected_spans_not_mostly_sequence_attributed")
    header_artifact_likely = bool(stop_reasons) and not sequence_lane_reopen_candidate
    return {
        "ablation_status": "bounded_fasta_ablation_complete",
        "row_count": len(rows),
        "case_count": len({row["name"] for row in rows}),
        "canonical_selected_spans": canonical_selected,
        "sha256_selected_spans": sha_selected,
        "canonical_negative_rows": sum(1 for row in canonical if row["delta_bytes"] < 0),
        "control_negative_groups": len(control_negative_groups),
        "control_negative_group_names": sorted(control_negative_groups),
        "control_negative_cases": control_negative_cases,
        "sequence_negative_cases": sequence_negative_cases,
        "fasta_original_delta_bytes": original["delta_bytes"],
        "fasta_header_scrubbed_delta_bytes": scrubbed["delta_bytes"],
        "fasta_sequence_only_best_delta_bytes": min(
            row["delta_bytes"] for row in sequence_only
        ),
        "fasta_header_only_control_delta_bytes": header_only["delta_bytes"],
        "total_sequence_selected_spans": total_sequence_selected,
        "total_header_selected_spans": total_header_selected,
        "sequence_candidate_sequence_selected_spans": sequence_candidate_sequence_selected,
        "sequence_candidate_header_selected_spans": sequence_candidate_header_selected,
        "sequence_candidate_sequence_selected_ratio": round(
            sequence_candidate_sequence_selected / sequence_total, 4
        )
        if sequence_total
        else 0.0,
        "selected_spans_mostly_sequence": selected_spans_mostly_sequence,
        "beats_sha256_baseline": beats_sha,
        "sequence_lane_reopen_candidate": sequence_lane_reopen_candidate,
        "header_artifact_likely": header_artifact_likely,
        "stop_reasons": stop_reasons,
        "natural_corpus_proven": False,
        "format_promotion_allowed": False,
        "broad_search_allowed": False,
        "claim_boundary": (
            "No Seed Search; bounded FASTA attribution ablation only; not "
            "natural-corpus proof; not production proof; not .tlmr format support."
        ),
        "conclusion": (
            "The sequence lane can reopen only if header-scrubbed and sequence-only "
            "FASTA rows stay negative while controls remain null and selected spans "
            "are mostly sequence-attributed."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["delta_bytes"],
            -row["selected_span_count"],
            row["mode"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    replay = load_json(DOCS / "seed_table_preset_replay.json")
    replay_summary = replay["summary"]
    if replay_summary["ordinary_negative_group_names"] != ["sequence-fasta"]:
        raise RuntimeError("FASTA ablation expects sequence-fasta to be the lone replay win")
    rows = analyze_cases()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "bounded FASTA attribution ablation",
            "performs_seed_search": False,
            "performs_preset_lookup": True,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
        },
        "source_hashes": source_hashes(),
        "case_manifest_sha256": case_manifest_hash(),
        "case_manifest": case_manifest(),
        "summary": summarize(rows),
        "top_rows": top_rows(rows),
        "rows": rows,
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Seed Table FASTA Ablation",
        "",
        f"Generated by `{GENERATED_BY}` from the bounded seed-table replay signal.",
        "This is a No Seed Search attribution artifact. It launches no agents, performs no broad seed search, is not natural-corpus proof, is not production proof, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Ablation status: `{summary['ablation_status']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Canonical selected spans: `{summary['canonical_selected_spans']}`",
        f"- SHA256 selected spans: `{summary['sha256_selected_spans']}`",
        f"- Canonical negative rows: `{summary['canonical_negative_rows']}`",
        f"- Control negative groups: `{summary['control_negative_groups']}`",
        f"- FASTA original delta bytes: `{summary['fasta_original_delta_bytes']}`",
        f"- Header-scrubbed sequence delta bytes: `{summary['fasta_header_scrubbed_delta_bytes']}`",
        f"- Best sequence-only delta bytes: `{summary['fasta_sequence_only_best_delta_bytes']}`",
        f"- Header-only control delta bytes: `{summary['fasta_header_only_control_delta_bytes']}`",
        f"- Total sequence-attributed selected spans: `{summary['total_sequence_selected_spans']}`",
        f"- Total header-attributed selected spans: `{summary['total_header_selected_spans']}`",
        f"- Sequence-candidate sequence spans: `{summary['sequence_candidate_sequence_selected_spans']}`",
        f"- Sequence-candidate header spans: `{summary['sequence_candidate_header_selected_spans']}`",
        f"- Sequence-candidate sequence ratio: `{summary['sequence_candidate_sequence_selected_ratio']}`",
        f"- Selected spans mostly sequence-attributed: `{summary['selected_spans_mostly_sequence']}`",
        f"- Beats SHA256 baseline: `{summary['beats_sha256_baseline']}`",
        f"- Sequence lane reopen candidate: `{summary['sequence_lane_reopen_candidate']}`",
        f"- Header artifact likely: `{summary['header_artifact_likely']}`",
        f"- Stop reasons: `{', '.join(summary['stop_reasons']) if summary['stop_reasons'] else 'none'}`",
        "",
        summary["conclusion"],
        "",
        "## Design",
        "",
        "- Reuses the same leave-FASTA-out canonical table policy as the seed-table replay.",
        "- Separates original FASTA bytes into header, sequence, syntax, mixed, and control attribution regions.",
        "- Tests header scrub, sequence-only, header-only, random-sequence, shuffled-sequence, shadow, and binary controls.",
        "- This artifact intentionally does not add preset metadata to `.tlmr`.",
        "",
        "## Top Rows",
        "",
        "| case | mode | kind | selected spans | sequence spans | header spans | delta bytes | exact decode |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["top_rows"]:
        attribution = row["attribution"]
        lines.append(
            f"| `{cell(row['name'])}` | `{cell(row['mode'])}` | "
            f"`{cell(row['control_kind'])}` | {row['selected_span_count']} | "
            f"{attribution['sequence_selected_spans']} | "
            f"{attribution['header_selected_spans']} | {row['delta_bytes']} | "
            f"`{row['exact_decode']}` |"
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "- `fasta-header-scrubbed-sequence` must have `delta_bytes < 0`.",
            "- At least one sequence-only row must have `delta_bytes < 0`.",
            "- FASTA controls and replay controls must have zero negative groups.",
            "- Canonical selected spans must be nonzero and beat the SHA256 baseline.",
            "- Selected spans must be mostly sequence-attributed, not header-attributed.",
            "- Passing this gate reopens only a bounded sequence-specific lane; it is not natural-corpus proof or format promotion.",
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this ablation to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.append(f"- `case_manifest_sha256`: `{payload['case_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated seed table FASTA ablation files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("seed_table_fasta_ablation.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("seed table FASTA ablation source hashes are stale")
    if payload.get("case_manifest_sha256") != case_manifest_hash():
        raise SystemExit("seed table FASTA ablation case manifest hash is stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("seed_table_fasta_ablation.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "allows_broad_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"seed table FASTA ablation scope field must be false: {field}")
    summary = payload["summary"]
    if summary["natural_corpus_proven"] is not False:
        raise SystemExit("seed table FASTA ablation must not claim natural-corpus proof")
    if summary["format_promotion_allowed"] is not False:
        raise SystemExit("seed table FASTA ablation must not allow format promotion")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Seed Table FASTA Ablation",
        "No Seed Search",
        "not natural-corpus proof",
        "not `.tlmr` format support",
        "header",
        "sequence",
        "Promotion Gate",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"SEED_TABLE_FASTA_ABLATION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
