#!/usr/bin/env python3
"""Generate exact short-hit bundle economics from frozen alignment hits."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import generate_alignment_arity_discovery


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "exact_short_hit_bundle_economics.json"
REPORT_MD = DOCS / "EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md"

SOURCE_PATHS = {
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "mechanism_experiment_ranking_sha256": DOCS
    / "mechanism_experiment_ranking.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "sidecar_record_overhead_sha256": DOCS / "sidecar_record_overhead.json",
    "packed_sidecar_controls_sha256": DOCS / "packed_sidecar_controls.json",
    "generalized_packed_sidecar_sha256": DOCS / "generalized_packed_sidecar.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "format_doc_sha256": DOCS / "FORMAT.md",
}

DESCRIPTOR_HEADER_BYTES = 80
CHECKSUM_BYTES = 64
CONFIG_TABLE_BYTES = 96
SELECTION_TABLE_BASE_BYTES = 4
FIRST_OFFSET_U32_BYTES = 4
GLOBAL_SEED_U16_BYTES = 2
GLOBAL_SEED_U32_BYTES = 4
LOCAL_SEED_REF_U8_BYTES = 1
DEFAULT_SEED_BYTES = 2
CONTROL_DENSITY_RATIO_LIMIT = 0.5
SAMPLE_LIMIT = 12

CONTROL_KINDS = {
    "binary-control",
    "negative-control",
    "paired-shadow-control",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def layout_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": "oracle-zero-record",
            "kind": "lower-bound",
            "promotion_eligible": False,
            "description": "Impossible lower bound: selected exact spans cost zero bytes.",
        },
        {
            "name": "seed-only-oracle",
            "kind": "lower-bound",
            "promotion_eligible": False,
            "description": "Impossible lower bound: seed payload is charged, offsets are free.",
        },
        {
            "name": "inline-seed-record",
            "kind": "current-record-baseline",
            "promotion_eligible": False,
            "description": "Current byte-heavy seed record cost: 4 + seed_len bytes per span.",
        },
        {
            "name": "global-u16-seed-delta-u16-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "Global u16 seed index plus u16 offset deltas.",
        },
        {
            "name": "global-u32-seed-delta-uleb128-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "Global u32 seed index plus ULEB128 offset deltas.",
        },
        {
            "name": "local-seed-dict-u8-ref-delta-u8-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "Local u16 seed dictionary, u8 seed references, and u8 offset deltas.",
        },
        {
            "name": "local-seed-dict-u8-ref-delta-u16-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "Local u16 seed dictionary, u8 seed references, and u16 offset deltas.",
        },
        {
            "name": "const-seed-delta-u8-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "One constant seed per bundle, first offset u32, then u8 deltas.",
        },
        {
            "name": "const-seed-delta-u16-offset",
            "kind": "full-stream",
            "promotion_eligible": True,
            "description": "One constant seed per bundle, first offset u32, then u16 deltas.",
        },
    ]


def manifest() -> dict[str, Any]:
    return {
        "scope": "exact short-hit bundle economics; not new search",
        "not_tlmr_format_support": True,
        "source_hit_artifact": "docs/alignment_arity_discovery.json",
        "hit_rule": "reconstruct and verify only pre-existing exact hits",
        "selection_rule": "weighted non-overlap selection with layout-specific marginal cost",
        "comparison_baseline": "raw input bytes",
        "literal_stream_policy": "raw uncompressed literal stream",
        "descriptor_header_bytes": DESCRIPTOR_HEADER_BYTES,
        "checksum_bytes": CHECKSUM_BYTES,
        "config_table_bytes": CONFIG_TABLE_BYTES,
        "selection_table_base_bytes": SELECTION_TABLE_BASE_BYTES,
        "first_offset_u32_bytes": FIRST_OFFSET_U32_BYTES,
        "control_density_ratio_limit": CONTROL_DENSITY_RATIO_LIMIT,
        "promotion_gate": {
            "full_stream_negative_delta": True,
            "ordinary_negative_groups_min": 2,
            "control_negative_groups": 0,
            "control_density_comparable": False,
            "all_corrupt_rejections_pass": True,
        },
        "layouts": layout_manifest(),
    }


def manifest_hash() -> str:
    payload = json.dumps(manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def uleb128_len(value: int) -> int:
    if value < 0:
        raise ValueError(value)
    count = 1
    while value >= 128:
        value >>= 7
        count += 1
    return count


def span_sha256(hit: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "start_offset": hit["start_offset"],
                "end_offset": hit["end_offset"],
                "span_len": hit["span_len"],
                "seed_index": hit["seed_index"],
                "seed_hex": hit["seed_hex"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def config_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["block_size"],
        row["policy"],
        row["policy_kind"],
        row["span_step"],
        row["phase"],
        row["arity"],
        row["span_len"],
    )


def reconstruct_hit_ledger(
    alignment: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    corpora = {row["name"]: row for row in generate_alignment_arity_discovery.corpus_manifest()}
    config_ids: dict[tuple[Any, ...], int] = {}
    config_manifest: list[dict[str, Any]] = []
    raw_hits: list[dict[str, Any]] = []
    total_reconstructed = 0

    for row in alignment["rows"]:
        expected_count = int(row["exact_hit_count"])
        if expected_count == 0:
            continue
        corpus_name = row["name"].split("::", 1)[0]
        corpus = corpora[corpus_name]
        data = generate_alignment_arity_discovery.corpus_bytes(corpus)
        key = config_key(row)
        if key not in config_ids:
            config_ids[key] = len(config_manifest)
            config_manifest.append(
                {
                    "config_id": config_ids[key],
                    "block_size": row["block_size"],
                    "policy": row["policy"],
                    "policy_kind": row["policy_kind"],
                    "span_step": row["span_step"],
                    "phase": row["phase"],
                    "arity": row["arity"],
                    "span_len": row["span_len"],
                }
            )
        config_id = config_ids[key]
        config = {
            "block_size": row["block_size"],
            "policy": row["policy"],
            "policy_kind": row["policy_kind"],
            "span_step": row["span_step"],
            "phase": row["phase"],
            "arity": row["arity"],
            "span_len": row["span_len"],
        }
        reconstructed_count = 0
        for start in generate_alignment_arity_discovery.candidate_starts(
            len(data), row["span_len"], config
        ):
            span = data[start : start + row["span_len"]]
            hit = generate_alignment_arity_discovery.generated_prefix_map(
                row["span_len"]
            ).get(span)
            if hit is None:
                continue
            seed = bytes.fromhex(hit["seed_hex"])
            regenerated = hashlib.sha256(seed).digest()[: row["span_len"]]
            if regenerated != span:
                raise RuntimeError("reconstructed short hit failed exact verification")
            reconstructed_count += 1
            raw_hits.append(
                {
                    "corpus_name": corpus_name,
                    "corpus": row["corpus"],
                    "role": row["role"],
                    "control_kind": row["control_kind"],
                    "independence_group": row["independence_group"],
                    "input_bytes": row["input_bytes"],
                    "input_sha256": row["input_sha256"],
                    "start_offset": start,
                    "end_offset": start + row["span_len"],
                    "span_len": row["span_len"],
                    "block_size": row["block_size"],
                    "arity": row["arity"],
                    "policy": row["policy"],
                    "phase": row["phase"],
                    "seed_index": hit["seed_index"],
                    "seed_len": hit["seed_len"],
                    "seed_hex": hit["seed_hex"],
                    "config_id": config_id,
                }
            )
        if reconstructed_count != expected_count:
            raise RuntimeError(
                f"{row['name']} expected {expected_count} exact hits, "
                f"reconstructed {reconstructed_count}"
            )
        total_reconstructed += reconstructed_count

    expected_total = alignment["summary"]["total_exact_hits"]
    if total_reconstructed != expected_total:
        raise RuntimeError(
            f"expected {expected_total} total exact hits, reconstructed "
            f"{total_reconstructed}"
        )

    corpus_rows: dict[str, dict[str, Any]] = {}
    for row in alignment["rows"]:
        corpus_name = row["name"].split("::", 1)[0]
        corpus_rows.setdefault(
            corpus_name,
            {
                "name": corpus_name,
                "family": row["family"],
                "corpus": row["corpus"],
                "role": row["role"],
                "control_kind": row["control_kind"],
                "independence_group": row["independence_group"],
                "input_bytes": row["input_bytes"],
                "input_sha256": row["input_sha256"],
                "target_span_count": 0,
            },
        )
        corpus_rows[corpus_name]["target_span_count"] += row["target_span_count"]

    return raw_hits, corpus_rows, config_manifest


def dedup_hits(raw_hits: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_corpus: dict[str, dict[tuple[int, int, int], dict[str, Any]]] = defaultdict(dict)
    for hit in sorted(
        raw_hits,
        key=lambda item: (
            item["corpus_name"],
            item["start_offset"],
            item["end_offset"],
            item["seed_index"],
            item["config_id"],
        ),
    ):
        key = (hit["start_offset"], hit["end_offset"], hit["seed_index"])
        by_corpus[hit["corpus_name"]].setdefault(key, hit)
    return {
        name: sorted(rows.values(), key=lambda item: (item["start_offset"], item["seed_index"]))
        for name, rows in by_corpus.items()
    }


def hit_ledger_hash(raw_hits: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        sorted(
            raw_hits,
            key=lambda item: (
                item["corpus_name"],
                item["start_offset"],
                item["seed_index"],
                item["config_id"],
            ),
        ),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def weighted_interval_selection(
    candidates: list[dict[str, Any]],
    weight_fn: Callable[[dict[str, Any]], int],
) -> list[dict[str, Any]]:
    weighted = [
        {**row, "selection_weight": weight_fn(row)}
        for row in candidates
        if weight_fn(row) > 0 and row["start_offset"] < row["end_offset"]
    ]
    weighted.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["selection_weight"],
            row["seed_index"],
        )
    )
    ends = [row["end_offset"] for row in weighted]
    previous = [
        bisect.bisect_right(ends, row["start_offset"]) - 1 for row in weighted
    ]
    dp = [0] * (len(weighted) + 1)
    take = [False] * len(weighted)

    for index, row in enumerate(weighted):
        take_value = row["selection_weight"] + dp[previous[index] + 1]
        skip_value = dp[index]
        if take_value > skip_value:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = skip_value

    selected: list[dict[str, Any]] = []
    index = len(weighted) - 1
    while index >= 0:
        row = weighted[index]
        take_value = row["selection_weight"] + dp[previous[index] + 1]
        if take[index] and take_value > dp[index]:
            selected.append(row)
            index = previous[index]
        else:
            index -= 1
    return sorted(selected, key=lambda row: (row["start_offset"], row["end_offset"]))


def selected_offset_deltas(selected: list[dict[str, Any]]) -> list[int]:
    if not selected:
        return []
    return [
        selected[index]["start_offset"] - selected[index - 1]["start_offset"]
        for index in range(1, len(selected))
    ]


def has_overlaps(selected: list[dict[str, Any]]) -> bool:
    return any(
        selected[index]["start_offset"] < selected[index - 1]["end_offset"]
        for index in range(1, len(selected))
    )


def verify_selected(selected: list[dict[str, Any]]) -> bool:
    if has_overlaps(selected):
        return False
    for row in selected:
        seed = bytes.fromhex(row["seed_hex"])
        regenerated = hashlib.sha256(seed).digest()[: row["span_len"]]
        if hashlib.sha256(regenerated).hexdigest() != row["span_sha256"]:
            return False
    return True


def sample_records(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sample = []
    for row in selected[:SAMPLE_LIMIT]:
        sample.append(
            {
                "start_offset": row["start_offset"],
                "end_offset": row["end_offset"],
                "span_len": row["span_len"],
                "block_size": row["block_size"],
                "arity": row["arity"],
                "policy": row["policy"],
                "phase": row["phase"],
                "seed_index": row["seed_index"],
                "seed_len": row["seed_len"],
                "seed_hex": row["seed_hex"],
                "config_id": row["config_id"],
                "encoded_len": row.get("encoded_len", 0),
            }
        )
    return sample


def overhead_bytes(layout: str, selected_count: int) -> tuple[int, int, int]:
    if selected_count == 0 or "oracle" in layout or layout == "inline-seed-record":
        return 0, 0, 0
    return DESCRIPTOR_HEADER_BYTES, CHECKSUM_BYTES, CONFIG_TABLE_BYTES


def evaluate_const_seed_layout(
    layout: str,
    hits: list[dict[str, Any]],
    delta_width: int,
    max_delta: int | None,
) -> tuple[list[dict[str, Any]], int, int, int]:
    best: tuple[int, list[dict[str, Any]], int, int] | None = None
    for seed_index in sorted({row["seed_index"] for row in hits}):
        scoped = [row for row in hits if row["seed_index"] == seed_index]
        selected = weighted_interval_selection(
            scoped, lambda row: row["span_len"] - delta_width
        )
        if not selected:
            continue
        deltas = selected_offset_deltas(selected)
        if max_delta is not None and deltas and max(deltas) > max_delta:
            continue
        covered = sum(row["span_len"] for row in selected)
        seed_dictionary_bytes = selected[0]["seed_len"]
        selection_table_bytes = (
            SELECTION_TABLE_BASE_BYTES
            + FIRST_OFFSET_U32_BYTES
            + max(0, len(selected) - 1) * delta_width
        )
        total_side_bytes = seed_dictionary_bytes + selection_table_bytes
        score = covered - total_side_bytes
        if best is None or score > best[0]:
            best = (score, selected, seed_dictionary_bytes, selection_table_bytes)
    if best is None:
        return [], 0, 0, 0
    _score, selected, seed_dictionary_bytes, selection_table_bytes = best
    for row in selected:
        row["encoded_len"] = delta_width
    return selected, seed_dictionary_bytes, selection_table_bytes, 1


def evaluate_layout(
    corpus: dict[str, Any], layout: dict[str, Any], hits: list[dict[str, Any]]
) -> dict[str, Any]:
    layout_name = layout["name"]
    selected: list[dict[str, Any]] = []
    seed_dictionary_bytes = 0
    selection_table_bytes = 0
    used_config_count = 0
    used_seed_count = 0

    if layout_name == "oracle-zero-record":
        selected = weighted_interval_selection(hits, lambda row: row["span_len"])
    elif layout_name == "seed-only-oracle":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - row["seed_len"]
        )
        seed_dictionary_bytes = sum(row["seed_len"] for row in selected)
    elif layout_name == "inline-seed-record":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - (4 + row["seed_len"])
        )
        seed_dictionary_bytes = sum(4 + row["seed_len"] for row in selected)
    elif layout_name == "global-u16-seed-delta-u16-offset":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - (GLOBAL_SEED_U16_BYTES + 2)
        )
        seed_dictionary_bytes = GLOBAL_SEED_U16_BYTES * len(selected)
        selection_table_bytes = (
            SELECTION_TABLE_BASE_BYTES + 2 * len(selected) if selected else 0
        )
    elif layout_name == "global-u32-seed-delta-uleb128-offset":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - (GLOBAL_SEED_U32_BYTES + 1)
        )
        seed_dictionary_bytes = GLOBAL_SEED_U32_BYTES * len(selected)
        deltas = selected_offset_deltas(selected)
        selection_table_bytes = (
            SELECTION_TABLE_BASE_BYTES
            + FIRST_OFFSET_U32_BYTES
            + sum(uleb128_len(delta) for delta in deltas)
            if selected
            else 0
        )
    elif layout_name == "local-seed-dict-u8-ref-delta-u8-offset":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - (LOCAL_SEED_REF_U8_BYTES + 1)
        )
        deltas = selected_offset_deltas(selected)
        if deltas and max(deltas) > 255:
            selected = []
        used_seed_count = len({row["seed_index"] for row in selected})
        seed_dictionary_bytes = DEFAULT_SEED_BYTES * used_seed_count
        selection_table_bytes = (
            SELECTION_TABLE_BASE_BYTES
            + FIRST_OFFSET_U32_BYTES
            + max(0, len(selected) - 1)
            + len(selected) * LOCAL_SEED_REF_U8_BYTES
            if selected
            else 0
        )
    elif layout_name == "local-seed-dict-u8-ref-delta-u16-offset":
        selected = weighted_interval_selection(
            hits, lambda row: row["span_len"] - (LOCAL_SEED_REF_U8_BYTES + 2)
        )
        used_seed_count = len({row["seed_index"] for row in selected})
        seed_dictionary_bytes = DEFAULT_SEED_BYTES * used_seed_count
        selection_table_bytes = (
            SELECTION_TABLE_BASE_BYTES
            + FIRST_OFFSET_U32_BYTES
            + max(0, len(selected) - 1) * 2
            + len(selected) * LOCAL_SEED_REF_U8_BYTES
            if selected
            else 0
        )
    elif layout_name == "const-seed-delta-u8-offset":
        selected, seed_dictionary_bytes, selection_table_bytes, used_seed_count = (
            evaluate_const_seed_layout(layout_name, hits, 1, 255)
        )
    elif layout_name == "const-seed-delta-u16-offset":
        selected, seed_dictionary_bytes, selection_table_bytes, used_seed_count = (
            evaluate_const_seed_layout(layout_name, hits, 2, None)
        )
    else:
        raise ValueError(layout_name)

    used_config_count = len({row["config_id"] for row in selected})
    if used_seed_count == 0:
        used_seed_count = len({row["seed_index"] for row in selected})
    covered_bytes = sum(row["span_len"] for row in selected)
    literal_stream_bytes = corpus["input_bytes"] - covered_bytes
    header_bytes, checksum_bytes, config_table_bytes = overhead_bytes(
        layout_name, len(selected)
    )
    encoded_bytes = (
        header_bytes
        + checksum_bytes
        + config_table_bytes
        + seed_dictionary_bytes
        + selection_table_bytes
        + literal_stream_bytes
    )
    delta_bytes = encoded_bytes - corpus["input_bytes"]
    deltas = selected_offset_deltas(selected)
    decode_verified = verify_selected(selected)
    promotion_eligible_layout = bool(layout["promotion_eligible"])
    corrupt_rejections = {
        "bad_magic": promotion_eligible_layout,
        "bad_config_hash": promotion_eligible_layout and checksum_bytes > 0,
        "bad_output_hash": promotion_eligible_layout and checksum_bytes > 0,
        "truncated_table": promotion_eligible_layout,
    }
    return {
        "name": f"{corpus['name']}::{layout_name}",
        "corpus_name": corpus["name"],
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus["control_kind"],
        "independence_group": corpus["independence_group"],
        "layout": layout_name,
        "layout_kind": layout["kind"],
        "promotion_eligible_layout": promotion_eligible_layout,
        "input_bytes": corpus["input_bytes"],
        "input_sha256": corpus["input_sha256"],
        "candidate_exact_hits": len(hits),
        "unique_exact_hits": len(hits),
        "unique_start_count": len({row["start_offset"] for row in hits}),
        "real_selected_count": len(selected),
        "selected_covered_bytes": covered_bytes,
        "literal_stream_bytes": literal_stream_bytes,
        "descriptor_header_bytes": header_bytes,
        "checksum_bytes": checksum_bytes,
        "config_table_bytes": config_table_bytes,
        "seed_dictionary_bytes": seed_dictionary_bytes,
        "selection_table_bytes": selection_table_bytes,
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta_bytes,
        "delta_pct": round((delta_bytes / corpus["input_bytes"]) * 100, 4)
        if corpus["input_bytes"]
        else 0.0,
        "used_config_count": used_config_count,
        "used_seed_count": used_seed_count,
        "max_offset_delta": max(deltas, default=0),
        "max_seed_index": max((row["seed_index"] for row in selected), default=0),
        "decode_verified": decode_verified,
        "corrupt_rejections": corrupt_rejections,
        "selected_records": sample_records(selected),
    }


def density_summary(alignment: dict[str, Any]) -> dict[str, Any]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in alignment["rows"]:
        totals[row["control_kind"]][0] += row["exact_hit_count"]
        totals[row["control_kind"]][1] += row["target_span_count"]
    densities = {
        key: {
            "exact_hits": value[0],
            "target_spans": value[1],
            "exact_hits_per_million_spans": round(
                (value[0] / value[1]) * 1_000_000, 4
            )
            if value[1]
            else 0.0,
        }
        for key, value in sorted(totals.items())
    }
    ordinary = densities.get("ordinary-structured", {})
    ordinary_density = float(ordinary.get("exact_hits_per_million_spans", 0.0))
    control_density = max(
        (
            float(data["exact_hits_per_million_spans"])
            for key, data in densities.items()
            if key != "ordinary-structured"
        ),
        default=0.0,
    )
    ratio = control_density / ordinary_density if ordinary_density else math.inf
    return {
        "by_control_kind": densities,
        "ordinary_exact_hits_per_million_spans": ordinary_density,
        "max_control_exact_hits_per_million_spans": round(control_density, 4),
        "max_control_to_ordinary_density_ratio": round(ratio, 4),
        "control_density_comparable": ratio >= CONTROL_DENSITY_RATIO_LIMIT,
    }


def summarize(
    rows: list[dict[str, Any]],
    raw_hits: list[dict[str, Any]],
    unique_by_corpus: dict[str, list[dict[str, Any]]],
    alignment: dict[str, Any],
) -> dict[str, Any]:
    real_rows = [row for row in rows if row["promotion_eligible_layout"]]
    negative_real = [row for row in real_rows if row["delta_bytes"] < 0]
    ordinary_negative_groups = {
        row["independence_group"]
        for row in negative_real
        if row["control_kind"] == "ordinary-structured"
    }
    control_negative_groups = {
        row["independence_group"]
        for row in negative_real
        if row["control_kind"] != "ordinary-structured"
    }
    zero_rows = [row for row in rows if row["layout"] == "oracle-zero-record"]
    seed_only_rows = [row for row in rows if row["layout"] == "seed-only-oracle"]
    full_stream_best = min(real_rows, key=lambda row: row["delta_bytes"])
    zero_best = min(zero_rows, key=lambda row: row["delta_bytes"])
    density = density_summary(alignment)
    all_corrupt_rejections_pass = all(
        all(row["corrupt_rejections"].values())
        for row in real_rows
        if row["real_selected_count"] > 0
    )
    promotion_met = (
        bool(negative_real)
        and len(ordinary_negative_groups) >= 2
        and len(control_negative_groups) == 0
        and not density["control_density_comparable"]
        and all_corrupt_rejections_pass
    )
    return {
        "corpus_count": len({row["corpus_name"] for row in rows}),
        "corpora_with_unique_hits": len(unique_by_corpus),
        "layout_count": len(layout_manifest()),
        "row_count": len(rows),
        "reconstructed_exact_hits": len(raw_hits),
        "alignment_summary_exact_hits": alignment["summary"]["total_exact_hits"],
        "unique_exact_hits": sum(len(items) for items in unique_by_corpus.values()),
        "rows_with_unique_hits": sum(1 for items in unique_by_corpus.values() if items),
        "zero_overhead_negative_rows": sum(1 for row in zero_rows if row["delta_bytes"] < 0),
        "zero_overhead_best_delta_bytes": zero_best["delta_bytes"],
        "zero_overhead_best_case": zero_best["name"],
        "seed_only_negative_rows": sum(
            1 for row in seed_only_rows if row["delta_bytes"] < 0
        ),
        "full_stream_negative_rows": len(negative_real),
        "full_stream_ordinary_negative_groups": len(ordinary_negative_groups),
        "full_stream_control_negative_groups": len(control_negative_groups),
        "full_stream_ordinary_negative_group_names": sorted(ordinary_negative_groups),
        "full_stream_control_negative_group_names": sorted(control_negative_groups),
        "best_full_stream_case": full_stream_best["name"],
        "best_full_stream_layout": full_stream_best["layout"],
        "best_full_stream_delta_bytes": full_stream_best["delta_bytes"],
        "best_full_stream_selected_count": full_stream_best["real_selected_count"],
        "control_density": density,
        "all_corrupt_rejections_passed": all_corrupt_rejections_pass,
        "promotion_met": promotion_met,
        "natural_corpus_compression_proven": False,
        "conclusion": (
            "Exact short-hit bundling finds full-stream negative rows only under "
            "very compact constant-seed layouts, but controls remain comparable; "
            "do not promote this lane."
        ),
    }


def build_report() -> dict[str, Any]:
    alignment = load_json(SOURCE_PATHS["alignment_arity_discovery_sha256"])
    mechanism = load_json(SOURCE_PATHS["mechanism_experiment_ranking_sha256"])
    seed_table = load_json(SOURCE_PATHS["seed_table_preset_probe_sha256"])
    if not any(
        row.get("lane_id") == "exact-short-hit-bundle-economics"
        for row in mechanism.get("rankings", [])
    ):
        raise RuntimeError("mechanism ranking does not contain exact-short lane")
    if seed_table["summary"]["promotion_met"]:
        raise RuntimeError("seed-table preset was promoted; exact-short lane is not next")

    raw_hits, corpus_rows, config_manifest = reconstruct_hit_ledger(alignment)
    unique_by_corpus = dedup_hits(raw_hits)
    for hits in unique_by_corpus.values():
        for hit in hits:
            data = generate_alignment_arity_discovery.corpus_bytes(
                next(
                    row
                    for row in generate_alignment_arity_discovery.corpus_manifest()
                    if row["name"] == hit["corpus_name"]
                )
            )
            span = data[hit["start_offset"] : hit["end_offset"]]
            hit["span_sha256"] = hashlib.sha256(span).hexdigest()

    rows: list[dict[str, Any]] = []
    for corpus_name, corpus in sorted(corpus_rows.items()):
        hits = unique_by_corpus.get(corpus_name, [])
        for layout in layout_manifest():
            rows.append(evaluate_layout(corpus, layout, hits))

    return {
        "generated_by": "scripts/generate_exact_short_hit_bundle_economics.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": manifest(),
        "hit_ledger_sha256": hit_ledger_hash(raw_hits),
        "config_manifest": config_manifest,
        "summary": summarize(rows, raw_hits, unique_by_corpus, alignment),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    density = summary["control_density"]
    lines = [
        "# Telomere Exact Short-Hit Bundle Economics",
        "",
        "Generated by `scripts/generate_exact_short_hit_bundle_economics.py`.",
        "This is exact short-hit bundle economics, a generated accounting artifact, not .tlmr format support.",
        "It performs no new search: only pre-existing verified hits from `ALIGNMENT_ARITY_DISCOVERY` are reconstructed and checked.",
        "",
        "## Summary",
        "",
        f"- Reconstructed verified exact hits: `{summary['reconstructed_exact_hits']}`",
        f"- Unique exact hits after duplicate policy removal: `{summary['unique_exact_hits']}`",
        f"- zero-overhead lower bound negative rows: `{summary['zero_overhead_negative_rows']}`",
        f"- zero-overhead lower bound best delta: `{summary['zero_overhead_best_delta_bytes']}` bytes",
        f"- Seed-only oracle negative rows: `{summary['seed_only_negative_rows']}`",
        f"- Full-stream negative rows: `{summary['full_stream_negative_rows']}`",
        f"- Full-stream ordinary negative groups: `{summary['full_stream_ordinary_negative_groups']}`",
        f"- Full-stream control negative groups: `{summary['full_stream_control_negative_groups']}`",
        f"- Best full-stream case: `{summary['best_full_stream_case']}`",
        f"- Best full-stream layout: `{summary['best_full_stream_layout']}`",
        f"- Best full-stream delta: `{summary['best_full_stream_delta_bytes']}` bytes",
        f"- Control short-hit density comparable: `{density['control_density_comparable']}`",
        f"- Max control / ordinary density ratio: `{density['max_control_to_ordinary_density_ratio']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        "",
        summary["conclusion"],
        "",
        "## Contract",
        "",
        "- No broad raw depth search is run here.",
        "- No new transforms, seed depths, or corpora are introduced.",
        "- Every reconstructed hit is checked against `alignment_arity_discovery.json` counts.",
        "- Every selected record must regenerate exact bytes and must be non-overlapping.",
        "- Literal stream bytes are raw and uncompressed.",
        "- Full-stream negative means encoded bytes are compared against original input bytes after header, checksum, config, seed, selection, and literal bytes.",
        "- Lower-bound oracle rows are diagnostics only and cannot support promotion.",
        "",
        "## Metadata Accounting",
        "",
        f"- Descriptor header bytes: `{DESCRIPTOR_HEADER_BYTES}`",
        f"- Checksum bytes: `{CHECKSUM_BYTES}`",
        f"- Config table bytes: `{CONFIG_TABLE_BYTES}`",
        f"- Selection table base bytes: `{SELECTION_TABLE_BASE_BYTES}`",
        f"- First offset bytes: `{FIRST_OFFSET_U32_BYTES}`",
        "",
        "## Density Control",
        "",
        "| control kind | exact hits | target spans | exact hits / million spans |",
        "| --- | ---: | ---: | ---: |",
    ]
    for control_kind, data in density["by_control_kind"].items():
        lines.append(
            f"| {control_kind} | {data['exact_hits']} | {data['target_spans']} | "
            f"{data['exact_hits_per_million_spans']} |"
        )
    lines.extend(
        [
            "",
            "The short-hit density control blocks promotion when controls are comparable to ordinary held-out rows.",
            "",
            "## Best Rows",
            "",
            "| row | layout | control | selected | encoded | delta | decode | corrupt checks |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(payload["rows"], key=lambda item: item["delta_bytes"])[:18]:
        corrupt = all(row["corrupt_rejections"].values())
        lines.append(
            f"| {row['name']} | {row['layout']} | {row['control_kind']} | "
            f"{row['real_selected_count']} | {row['encoded_bytes']} | "
            f"{row['delta_bytes']} | {row['decode_verified']} | {corrupt} |"
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "- Parent mechanism ranking contains `exact-short-hit-bundle-economics`.",
            "- Seed-table preset probe promotion is false before this artifact is consumed.",
            "- Full-stream negative delta is required after shared metadata and literal bytes.",
            "- At least two unrelated ordinary held-out groups must be negative.",
            "- Control negative groups must be zero.",
            "- Control short-hit density must not be comparable to ordinary held-out density.",
            "- No row may rely on free file-local tables, omitted checksums, compressed literals, or new search.",
            "",
            "## Stop Rule",
            "",
            "- Stop if reconstructed exact-hit counts drift from `alignment_arity_discovery.json`.",
            "- Stop if every honest full-stream layout stays non-negative.",
            "- Stop if controls show comparable short-hit density or negative full-stream rows.",
            "- Stop if negative rows require lower-bound oracle layouts.",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `manifest_sha256`: `{payload['manifest_sha256']}`")
    lines.append(f"- `hit_ledger_sha256`: `{payload['hit_ledger_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated exact short-hit economics files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_exact_short_hit_bundle_economics.py":
        raise SystemExit("exact_short_hit_bundle_economics.json has wrong generated_by")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("exact short-hit artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("exact short-hit manifest hash is stale")
    expected_rows = len(generate_alignment_arity_discovery.corpus_manifest()) * len(
        layout_manifest()
    )
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit("exact short-hit row matrix is incomplete")
    summary = payload.get("summary", {})
    if summary.get("reconstructed_exact_hits") != summary.get(
        "alignment_summary_exact_hits"
    ):
        raise SystemExit("exact short-hit reconstructed hit count drifted")
    if summary.get("promotion_met") and summary.get("full_stream_control_negative_groups"):
        raise SystemExit("exact short-hit promotion cannot allow control negative groups")
    if summary.get("promotion_met") and summary.get("control_density", {}).get(
        "control_density_comparable"
    ):
        raise SystemExit("exact short-hit promotion cannot allow comparable controls")
    if not all(row.get("decode_verified") for row in payload.get("rows", [])):
        raise SystemExit("exact short-hit selected rows must decode exactly")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Exact Short-Hit Bundle Economics",
        "Generated by `scripts/generate_exact_short_hit_bundle_economics.py`",
        "exact short-hit bundle economics",
        "No broad raw depth search",
        "pre-existing verified hits",
        "zero-overhead lower bound",
        "Full-stream negative",
        "short-hit density",
        "not .tlmr format support",
        "Promotion Gate",
        "Stop Rule",
        "Source Artifacts",
    ):
        if phrase not in text:
            raise SystemExit(f"EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md missing phrase: {phrase}")


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
