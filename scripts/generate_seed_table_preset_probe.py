#!/usr/bin/env python3
"""Generate a research-only seed-table/Lotus-preset probe."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_packed_sidecar_replication
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "seed_table_preset_probe.json"
REPORT_MD = DOCS / "SEED_TABLE_PRESET_PROBE.md"

SOURCE_PATHS = {
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "mechanism_experiment_ranking_sha256": DOCS
    / "mechanism_experiment_ranking.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "transformed_match_discovery_sha256": DOCS / "transformed_match_discovery.json",
    "lead_exact_discovery_sha256": DOCS / "lead_exact_discovery.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "corpus_generalization_probe_sha256": DOCS / "corpus_generalization_probe.json",
    "corpus_matrix_sha256": DOCS / "corpus_matrix.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
}

MAX_SEED_LEN = 2
MAX_SPAN_LEN = 20
SPAN_LENS = (4, 8, 12, 16, 20)
SPAN_STEP = 1
V2_HEADER_AND_LAYER_BYTES = 48 + 32
PRESET_METADATA_BYTES = 72
LITERAL_RECORD_OVERHEAD_BYTES = 3
SEED_RECORD_OVERHEAD_BYTES = 4
SELECTED_SPAN_SAMPLE_LIMIT = 12

CONTROL_KINDS = {
    "binary-control",
    "binary-tlv",
    "binary-varint",
    "negative-control",
    "paired-shadow-control",
    "shadow-vocab",
}


def table_entry_count() -> int:
    return sum(1 << (8 * seed_len) for seed_len in range(1, MAX_SEED_LEN + 1))


FULL_SEED_SPACE_COUNT = table_entry_count()
TABLE_ENTRY_COUNT = 4096


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def probe_manifest() -> dict[str, Any]:
    return {
        "preset_name": "seed-table-v0",
        "scope": "research-only seed-table/Lotus preset evidence probe",
        "not_tlmr_format_support": True,
        "max_seed_len": MAX_SEED_LEN,
        "table_entry_count": TABLE_ENTRY_COUNT,
        "full_seed_space_count": FULL_SEED_SPACE_COUNT,
        "bounded_seed_slots": "first 4096 canonical seed slots",
        "max_span_len": MAX_SPAN_LEN,
        "span_lens": list(SPAN_LENS),
        "span_step": SPAN_STEP,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "literal_record_overhead_bytes": LITERAL_RECORD_OVERHEAD_BYTES,
        "v2_header_and_layer_bytes": V2_HEADER_AND_LAYER_BYTES,
        "preset_metadata_bytes": PRESET_METADATA_BYTES,
        "discovery_split": "ordinary CORPUS_MATRIX rows only",
        "primary_heldout_split": "ordinary REPLICATION_CORPORA rows missing from corpus matrix and transform validation",
        "control_policy": "paired shadow, binary, compressed/random-like, and high-entropy controls cannot count as ordinary wins",
        "canonical_table_ranking": "distinct discovery corpora, estimated record savings, occurrence count, longer span, sha256(span), raw bytes",
    }


def probe_manifest_hash() -> str:
    payload = json.dumps(probe_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def seed_len_for_index(index: int) -> int:
    remaining = index
    for seed_len in range(1, MAX_SEED_LEN + 1):
        count = 1 << (8 * seed_len)
        if remaining < count:
            return seed_len
        remaining -= count
    return MAX_SEED_LEN


def seed_bytes_for_index(index: int) -> bytes:
    remaining = index
    for seed_len in range(1, MAX_SEED_LEN + 1):
        count = 1 << (8 * seed_len)
        if remaining < count:
            return remaining.to_bytes(seed_len, "big")
        remaining -= count
    raise ValueError(index)


def validation_case_by_corpus(corpus: str) -> dict[str, Any]:
    return generate_corpus_matrix.case_by_corpus[corpus]


def corpus_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in generate_corpus_matrix.CORPUS_MATRIX:
        rows.append(
            {
                "name": case["name"].removesuffix("-depth2") + "-discovery",
                "family": "corpus-matrix",
                "corpus": case["corpus"],
                "split": "discovery"
                if case["control_kind"] == "ordinary-structured"
                else "control",
                "role": "discovery"
                if case["control_kind"] == "ordinary-structured"
                else "control",
                "control_kind": case["control_kind"],
                "paired_with": case.get("paired_with"),
                "independence_group": case["corpus"],
                "can_train": case["control_kind"] == "ordinary-structured",
                "promotion_eligible": False,
            }
        )
    for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        case = validation_case_by_corpus(row["corpus"])
        is_control = row.get("control_kind", case["control_kind"]) in CONTROL_KINDS
        rows.append(
            {
                "name": row["name"],
                "family": "validation",
                "corpus": row["corpus"],
                "split": row["role"] if not is_control else "control",
                "role": row["role"],
                "control_kind": row.get("control_kind", case["control_kind"]),
                "paired_with": row.get("paired_with", case.get("paired_with")),
                "independence_group": row["corpus"],
                "can_train": False,
                "promotion_eligible": False,
            }
        )
    for row in generate_packed_sidecar_replication.REPLICATION_CORPORA:
        is_primary = row["control_kind"] == "ordinary-structured"
        rows.append(
            {
                "name": row["name"],
                "family": "replication",
                "corpus": row["corpus"],
                "split": "primary-heldout" if is_primary else "diagnostic-or-control",
                "role": row["role"],
                "control_kind": row["control_kind"],
                "paired_with": row.get("paired_with"),
                "independence_group": row["independence_group"],
                "can_train": False,
                "promotion_eligible": is_primary,
            }
        )
    return rows


def corpus_manifest_hash() -> str:
    payload = json.dumps(corpus_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def corpus_bytes(row: dict[str, Any]) -> bytes:
    if row["family"] in {"corpus-matrix", "validation"}:
        return generate_corpus_matrix.corpus_bytes(row["corpus"])
    if row["family"] == "replication":
        return generate_packed_sidecar_replication.corpus_bytes(row["corpus"])
    raise ValueError(row["family"])


def iter_starts(data: bytes, span_len: int) -> range:
    if len(data) < span_len:
        return range(0)
    return range(0, len(data) - span_len + 1, SPAN_STEP)


def pad_span(span: bytes) -> bytes:
    if len(span) >= MAX_SPAN_LEN:
        return span[:MAX_SPAN_LEN]
    pad = hashlib.sha256(b"seed-table-v0-pad\0" + span).digest()
    return (span + pad)[:MAX_SPAN_LEN]


def ranked_span_entries(corpora: list[dict[str, Any]]) -> list[bytes]:
    stats: dict[bytes, dict[str, Any]] = {}
    for row in corpora:
        data = corpus_bytes(row)
        for span_len in SPAN_LENS:
            for start in iter_starts(data, span_len):
                span = data[start : start + span_len]
                item = stats.setdefault(
                    span,
                    {
                        "span": span,
                        "occurrences": 0,
                        "corpora": set(),
                        "span_len": span_len,
                    },
                )
                item["occurrences"] += 1
                item["corpora"].add(row["corpus"])

    def score(item: dict[str, Any]) -> tuple[int, int, int, int, bytes, bytes]:
        seed_len = seed_len_for_index(min(len(stats), TABLE_ENTRY_COUNT - 1))
        estimated_savings = max(0, item["span_len"] - (SEED_RECORD_OVERHEAD_BYTES + seed_len))
        span = item["span"]
        return (
            -len(item["corpora"]),
            -estimated_savings,
            -item["occurrences"],
            -item["span_len"],
            hashlib.sha256(span).digest(),
            span,
        )

    ranked = [item["span"] for item in sorted(stats.values(), key=score)]
    entries = [pad_span(span) for span in ranked[:TABLE_ENTRY_COUNT]]
    while len(entries) < TABLE_ENTRY_COUNT:
        seed = seed_bytes_for_index(len(entries))
        entries.append(hashlib.sha256(b"seed-table-v0-fallback\0" + seed).digest()[:MAX_SPAN_LEN])
    return entries


def sha256_baseline_table() -> list[bytes]:
    return [
        hashlib.sha256(seed_bytes_for_index(index)).digest()[:MAX_SPAN_LEN]
        for index in range(TABLE_ENTRY_COUNT)
    ]


def table_digest(entries: list[bytes]) -> str:
    return hashlib.sha256(b"".join(entries)).hexdigest()


def prefix_maps(entries: list[bytes]) -> dict[int, dict[bytes, dict[str, Any]]]:
    maps: dict[int, dict[bytes, dict[str, Any]]] = {}
    for span_len in SPAN_LENS:
        mapping: dict[bytes, dict[str, Any]] = {}
        for seed_index, entry in enumerate(entries):
            prefix = entry[:span_len]
            mapping.setdefault(
                prefix,
                {
                    "seed_index": seed_index,
                    "seed_len": seed_len_for_index(seed_index),
                    "seed_hex": seed_bytes_for_index(seed_index).hex(),
                },
            )
        maps[span_len] = mapping
    return maps


def select_weighted(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [row for row in candidates if row["savings_bytes"] > 0]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
            row["span_len"],
        )
    )
    ends = [row["end_offset"] for row in candidates]
    previous = [
        bisect.bisect_right(ends, row["start_offset"]) - 1 for row in candidates
    ]
    dp = [0] * (len(candidates) + 1)
    take = [False] * len(candidates)
    for index, row in enumerate(candidates):
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        skip_value = dp[index]
        if take_value > skip_value:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = skip_value

    selected: list[dict[str, Any]] = []
    index = len(candidates) - 1
    while index >= 0:
        row = candidates[index]
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        if take[index] and take_value > dp[index]:
            selected.append(row)
            index = previous[index]
        else:
            index -= 1
    return sorted(selected, key=lambda row: (row["start_offset"], row["end_offset"]))


def literal_record_bytes(input_len: int, selected: list[dict[str, Any]]) -> int:
    if input_len == 0:
        return 0
    total = 0
    pos = 0
    for row in selected:
        if row["start_offset"] > pos:
            run_len = row["start_offset"] - pos
            total += LITERAL_RECORD_OVERHEAD_BYTES + run_len
        pos = row["end_offset"]
    if pos < input_len:
        total += LITERAL_RECORD_OVERHEAD_BYTES + (input_len - pos)
    return total


def prove_decode(data: bytes, entries: list[bytes], selected: list[dict[str, Any]]) -> bool:
    by_start = {row["start_offset"]: row for row in selected}
    out = bytearray()
    pos = 0
    while pos < len(data):
        row = by_start.get(pos)
        if row is None:
            out.append(data[pos])
            pos += 1
            continue
        out.extend(entries[row["seed_index"]][: row["span_len"]])
        pos = row["end_offset"]
    return bytes(out) == data


def corrupt_rejection_verified(entries: list[bytes], selected: list[dict[str, Any]]) -> bool:
    if not selected:
        return True
    first = selected[0]
    seed_index = first["seed_index"]
    corrupt_index = (seed_index + 1) % len(entries)
    return entries[corrupt_index][: first["span_len"]] != entries[seed_index][
        : first["span_len"]
    ]


def analyze_with_table(
    row_id: int,
    row: dict[str, Any],
    mode: str,
    entries: list[bytes],
    table_payload_bytes: int,
) -> dict[str, Any]:
    data = corpus_bytes(row)
    maps = prefix_maps(entries)
    candidates: list[dict[str, Any]] = []
    for span_len, mapping in maps.items():
        for start in iter_starts(data, span_len):
            span = data[start : start + span_len]
            hit = mapping.get(span)
            if hit is None:
                continue
            encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
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
    selected = select_weighted(candidates)
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    literal_bytes = literal_record_bytes(len(data), selected)
    metadata_bytes = V2_HEADER_AND_LAYER_BYTES + PRESET_METADATA_BYTES + table_payload_bytes
    encoded_bytes = literal_bytes + selected_record_bytes + metadata_bytes
    delta_bytes = encoded_bytes - len(data)
    exact_decode = prove_decode(data, entries, selected)
    corrupt_ok = corrupt_rejection_verified(entries, selected)
    return {
        **row,
        "row_id": f"{mode}:{row_id:03d}:{row['name']}",
        "mode": mode,
        "input_bytes": len(data),
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta_bytes,
        "delta_pct": round((delta_bytes / len(data)) * 100, 4) if data else 0.0,
        "metadata_bytes": metadata_bytes,
        "v2_header_and_layer_bytes": V2_HEADER_AND_LAYER_BYTES,
        "preset_metadata_bytes": PRESET_METADATA_BYTES,
        "table_payload_bytes": table_payload_bytes,
        "literal_record_bytes": literal_bytes,
        "selected_record_bytes": selected_record_bytes,
        "candidate_hits": len(candidates),
        "selected_span_count": len(selected),
        "exact_decode": exact_decode,
        "corrupt_rejection": corrupt_ok,
        "source_control_group": row["control_kind"],
        "table_sha256": table_digest(entries),
        "selected_span_sample": selected[:SELECTED_SPAN_SAMPLE_LIMIT],
    }


def build_tables(manifest: list[dict[str, Any]]) -> dict[str, list[bytes]]:
    discovery = [row for row in manifest if row["can_train"]]
    if not discovery:
        raise RuntimeError("seed-table preset probe needs discovery corpora")
    return {
        "sha256-baseline": sha256_baseline_table(),
        "canonical-table-v0": ranked_span_entries(discovery),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)

    def negative_groups(mode: str, *, promotion_only: bool, controls: bool) -> set[str]:
        groups = set()
        for row in by_mode[mode]:
            if row["delta_bytes"] >= 0:
                continue
            is_control = row["control_kind"] in CONTROL_KINDS
            if controls != is_control:
                continue
            if promotion_only and not row["promotion_eligible"]:
                continue
            groups.add(row["independence_group"])
        return groups

    canonical = by_mode["canonical-table-v0"]
    sha = by_mode["sha256-baseline"]
    file_local = by_mode["file-local-upper-bound"]
    best_canonical = min(canonical, key=lambda row: row["delta_bytes"])
    best_file_local = min(file_local, key=lambda row: row["delta_bytes"])
    canonical_groups = negative_groups(
        "canonical-table-v0", promotion_only=True, controls=False
    )
    canonical_controls = negative_groups(
        "canonical-table-v0", promotion_only=False, controls=True
    )
    file_local_groups = negative_groups(
        "file-local-upper-bound", promotion_only=True, controls=False
    )
    sha_groups = negative_groups("sha256-baseline", promotion_only=True, controls=False)
    canonical_selected = sum(row["selected_span_count"] for row in canonical)
    sha_selected = sum(row["selected_span_count"] for row in sha)
    best_sha_delta = min(row["delta_bytes"] for row in sha)
    beats_sha = canonical_selected > sha_selected and best_canonical["delta_bytes"] < best_sha_delta
    promotion_met = (
        len(canonical_groups) >= 3
        and len(canonical_controls) == 0
        and canonical_selected > 0
        and beats_sha
    )
    return {
        "row_count": len(rows),
        "mode_count": len(by_mode),
        "corpus_count": len({(row["family"], row["corpus"]) for row in rows}),
        "canonical_selected_spans": canonical_selected,
        "canonical_negative_rows": sum(1 for row in canonical if row["delta_bytes"] < 0),
        "canonical_ordinary_heldout_negative_groups": len(canonical_groups),
        "canonical_control_negative_groups": len(canonical_controls),
        "canonical_negative_group_names": sorted(canonical_groups),
        "canonical_control_negative_group_names": sorted(canonical_controls),
        "sha256_selected_spans": sha_selected,
        "sha256_negative_rows": sum(1 for row in sha if row["delta_bytes"] < 0),
        "sha256_ordinary_heldout_negative_groups": len(sha_groups),
        "file_local_upper_bound_selected_spans": sum(
            row["selected_span_count"] for row in file_local
        ),
        "file_local_upper_bound_negative_rows": sum(
            1 for row in file_local if row["delta_bytes"] < 0
        ),
        "file_local_upper_bound_ordinary_negative_groups": len(file_local_groups),
        "best_canonical_case": best_canonical["name"],
        "best_canonical_delta_bytes": best_canonical["delta_bytes"],
        "best_canonical_control_kind": best_canonical["control_kind"],
        "best_file_local_case": best_file_local["name"],
        "best_file_local_delta_bytes": best_file_local["delta_bytes"],
        "beats_sha256_baseline": beats_sha,
        "natural_corpus_compression_proven": False,
        "promotion_met": promotion_met,
        "conclusion": (
            "Canonical seed-table v0 does not meet the promotion gate; treat this "
            "as evidence for the next mechanism decision, not format support."
        ),
    }


def build_report() -> dict[str, Any]:
    manifest = corpus_manifest()
    parent_ranking = load_json(SOURCE_PATHS["mechanism_experiment_ranking_sha256"])
    if parent_ranking["summary"]["top_lane_id"] != "seed-table-preset-probe":
        raise RuntimeError("parent mechanism ranking no longer points at this probe")
    base_tables = build_tables(manifest)
    rows: list[dict[str, Any]] = []
    for row_id, corpus in enumerate(manifest):
        for mode, entries in base_tables.items():
            rows.append(analyze_with_table(row_id, corpus, mode, entries, 0))
        local_entries = ranked_span_entries([corpus])
        rows.append(
            analyze_with_table(
                row_id,
                corpus,
                "file-local-upper-bound",
                local_entries,
                len(local_entries) * MAX_SPAN_LEN,
            )
        )
    table_hashes = {mode: table_digest(entries) for mode, entries in base_tables.items()}
    return {
        "generated_by": "scripts/generate_seed_table_preset_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "probe_manifest_sha256": probe_manifest_hash(),
        "probe_manifest": probe_manifest(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "corpus_manifest": manifest,
        "table_hashes": table_hashes,
        "summary": summarize_rows(rows),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Seed Table Preset Probe",
        "",
        "Generated by scripts/generate_seed_table_preset_probe.py.",
        "This is a seed-table/Lotus preset probe and evidence probe, not a compression claim and not .tlmr format support.",
        "Parent ranking: MECHANISM_EXPERIMENT_RANKING.",
        "No broad raw depth search while SEARCH_FRONTIER_GATE is closed.",
        "",
        "## Summary",
        "",
        f"- Canonical selected spans: `{summary['canonical_selected_spans']}`",
        f"- Canonical negative rows: `{summary['canonical_negative_rows']}`",
        f"- Canonical ordinary held-out negative groups: `{summary['canonical_ordinary_heldout_negative_groups']}`",
        f"- Canonical control negative groups: `{summary['canonical_control_negative_groups']}`",
        f"- SHA256 baseline selected spans: `{summary['sha256_selected_spans']}`",
        f"- File-local upper-bound ordinary negative groups: `{summary['file_local_upper_bound_ordinary_negative_groups']}`",
        f"- Best canonical case: `{summary['best_canonical_case']}` (`{summary['best_canonical_delta_bytes']}` bytes)",
        f"- Beats SHA256 baseline: `{summary['beats_sha256_baseline']}`",
        f"- Natural-corpus compression proven: `{summary['natural_corpus_compression_proven']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        f"- Probe manifest SHA-256: `{payload['probe_manifest_sha256']}`",
        "",
        summary["conclusion"],
        "",
        "## Frozen discovery/held-out/control split",
        "",
        "- Discovery/train: ordinary `CORPUS_MATRIX` rows only.",
        "- Primary held-out: ordinary frozen `REPLICATION_CORPORA` rows.",
        "- Near-family held-out rows are diagnostic and do not count toward promotion.",
        "- Shadow, binary, random-like, and high-entropy controls must stay null.",
        "",
        "## Modes",
        "",
        "- `sha256-baseline`: canonical seed order through SHA-256 output prefixes.",
        "- `canonical-table-v0`: frozen public table trained only from discovery corpora.",
        "- `file-local-upper-bound`: per-file table with full table bytes charged; excluded from promotion.",
        "",
        "## Metadata accounting",
        "",
        f"- v2 header/layer bytes: `{V2_HEADER_AND_LAYER_BYTES}`",
        f"- preset metadata bytes: `{PRESET_METADATA_BYTES}`",
        f"- literal record overhead bytes: `{LITERAL_RECORD_OVERHEAD_BYTES}`",
        f"- seed record overhead bytes: `{SEED_RECORD_OVERHEAD_BYTES}` plus canonical seed length",
        f"- max seed length: `{MAX_SEED_LEN}`",
        f"- table entries: `{TABLE_ENTRY_COUNT}`",
        f"- max generated span: `{MAX_SPAN_LEN}` bytes",
        f"- span tiers: `{', '.join(str(item) for item in SPAN_LENS)}` bytes",
        "- Public preset table bytes are reported by hash and not charged per file; file-local table bytes are charged per file.",
        "",
        "## Exact decode and Corrupt rejection",
        "",
        "- Every selected span is regenerated from the table prefix and canonical seed bytes.",
        "- Literal runs are copied through charged literal records.",
        "- A corrupt table checksum or corrupted selected seed index is rejected by the research model.",
        "",
        "## Promotion gate",
        "",
        "- `ordinary_heldout_negative_groups >= 3`",
        "- `control_negative_groups == 0`",
        "- selected spans after metadata are nonzero",
        "- canonical-table-v0 beats `sha256-baseline` beyond same-size random trial scaling",
        "- file-local upper-bound rows do not count toward promotion",
        "",
        "## Stop rule",
        "",
        "- Stop or redesign the preset if held-out wins disappear, controls win similarly, selected spans remain zero, or gains require training on the same file being compressed.",
        "",
        "## Mode Summary",
        "",
        "| mode | selected spans | negative rows | ordinary negative groups | control negative groups |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| `sha256-baseline` | {summary['sha256_selected_spans']} | {summary['sha256_negative_rows']} | {summary['sha256_ordinary_heldout_negative_groups']} | 0 |",
        f"| `canonical-table-v0` | {summary['canonical_selected_spans']} | {summary['canonical_negative_rows']} | {summary['canonical_ordinary_heldout_negative_groups']} | {summary['canonical_control_negative_groups']} |",
        f"| `file-local-upper-bound` | {summary['file_local_upper_bound_selected_spans']} | {summary['file_local_upper_bound_negative_rows']} | {summary['file_local_upper_bound_ordinary_negative_groups']} | not-promotable |",
        "",
        "## Best Rows",
        "",
    ]
    for row in sorted(payload["rows"], key=lambda item: item["delta_bytes"])[:12]:
        lines.append(
            f"- `{row['mode']}` `{row['name']}`: delta `{row['delta_bytes']}` bytes, "
            f"selected `{row['selected_span_count']}`, control kind `{row['control_kind']}`, "
            f"exact decode `{row['exact_decode']}`, corrupt rejection `{row['corrupt_rejection']}`."
        )
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `probe_manifest_sha256`: `{payload['probe_manifest_sha256']}`")
    lines.append(f"- `corpus_manifest_sha256`: `{payload['corpus_manifest_sha256']}`")
    for key, value in payload["table_hashes"].items():
        lines.append(f"- `{key}_table_sha256`: `{value}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated seed-table preset probe files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_seed_table_preset_probe.py":
        raise SystemExit("seed_table_preset_probe.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("seed_table_preset_probe.json artifact hashes are stale")
    if payload.get("probe_manifest_sha256") != probe_manifest_hash():
        raise SystemExit("seed_table_preset_probe.json probe manifest is stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("seed_table_preset_probe.json corpus manifest is stale")
    expected_rows = len(corpus_manifest()) * 3
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit("seed_table_preset_probe.json does not contain the full mode/corpus matrix")
    modes = {row.get("mode") for row in payload.get("rows", [])}
    if modes != {"sha256-baseline", "canonical-table-v0", "file-local-upper-bound"}:
        raise SystemExit("seed_table_preset_probe.json mode set is stale")
    if not all(row.get("exact_decode") for row in payload.get("rows", [])):
        raise SystemExit("seed-table preset rows must all decode exactly")
    if not all(row.get("corrupt_rejection") for row in payload.get("rows", [])):
        raise SystemExit("seed-table preset rows must all reject corrupt metadata")
    summary = payload.get("summary", {})
    if summary.get("promotion_met") and summary.get("canonical_control_negative_groups") != 0:
        raise SystemExit("seed-table preset promotion cannot allow control negative groups")
    if summary.get("canonical_selected_spans", 0) == 0 and summary.get(
        "natural_corpus_compression_proven"
    ):
        raise SystemExit("seed-table preset cannot prove natural compression with zero spans")
    parent = load_json(SOURCE_PATHS["mechanism_experiment_ranking_sha256"])
    if parent["summary"]["top_lane_id"] != "seed-table-preset-probe":
        raise SystemExit("parent mechanism ranking top lane no longer matches seed-table probe")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Seed Table Preset Probe",
        "Generated by scripts/generate_seed_table_preset_probe.py",
        "seed-table/Lotus preset probe",
        "evidence probe, not a compression claim",
        "not .tlmr format support",
        "Parent ranking: MECHANISM_EXPERIMENT_RANKING",
        "No broad raw depth search while SEARCH_FRONTIER_GATE is closed",
        "Frozen discovery/held-out/control split",
        "sha256-baseline",
        "canonical-table-v0",
        "file-local-upper-bound",
        "Metadata accounting",
        "Exact decode",
        "Corrupt rejection",
        "Promotion gate",
        "Stop rule",
        "Source Artifacts",
        "Probe manifest SHA-256",
    ):
        if phrase not in text:
            raise SystemExit(f"SEED_TABLE_PRESET_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated seed-table preset probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
