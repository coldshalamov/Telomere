#!/usr/bin/env python3
"""Profile frozen held-out replication corpora before expanding expensive matrices."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_packed_sidecar_replication
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "heldout_corpus_expansion.json"
REPORT_MD = DOCS / "HELDOUT_CORPUS_EXPANSION.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6, 8)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 32
TOKEN_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_-]*|\d+")
INTEGER_RE = re.compile(rb"[+-]?\d+")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
        "packed_sidecar_replication_sha256": sha256(
            DOCS / "packed_sidecar_replication.json"
        ),
    }


def search_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte seeds, each bucket big-endian",
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "generated seed prefixes are compared directly against raw held-out corpus bytes",
        "scope": "held-out corpus expansion audit only; does not mutate transform-validation or .tlmr format support",
    }


def manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def current_corpus_matrix_names() -> set[str]:
    return {row["corpus"] for row in generate_corpus_matrix.CORPUS_MATRIX}


def current_validation_corpus_names() -> set[str]:
    return {row["corpus"] for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX}


def corpus_manifest() -> list[dict[str, Any]]:
    matrix_names = current_corpus_matrix_names()
    validation_names = current_validation_corpus_names()
    rows: list[dict[str, Any]] = []
    for row in generate_packed_sidecar_replication.REPLICATION_CORPORA:
        rows.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "role": row["role"],
                "control_kind": row["control_kind"],
                "independence_group": row["independence_group"],
                "paired_with": row.get("paired_with"),
                "in_corpus_matrix": row["corpus"] in matrix_names,
                "in_transform_validation": row["corpus"] in validation_names,
            }
        )
    return rows


def corpus_manifest_hash() -> str:
    payload = json.dumps(corpus_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def seed_maps() -> dict[str, Any]:
    prefix_sets: dict[int, set[bytes]] = {prefix_len: set() for prefix_len in PREFIX_LADDER}
    exact_by_span: dict[bytes, dict[str, Any]] = {}
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        digest = hashlib.sha256(seed).digest()
        span = digest[:SPAN_LEN]
        for prefix_len in PREFIX_LADDER:
            prefix_sets[prefix_len].add(span[:prefix_len])
        exact_by_span.setdefault(
            span,
            {
                "seed_index": seed_index,
                "seed_len": len(seed),
                "seed_hex": seed.hex(),
            },
        )
    return {"prefix_sets": prefix_sets, "exact_by_span": exact_by_span}


def ascii_printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for byte in data if byte in b"\t\r\n" or 32 <= byte <= 126)
    return round(printable / len(data), 4)


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * (count / total).bit_length() for count in counts.values()),
        4,
    )


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    import math

    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def candidate_span_count(data_len: int) -> int:
    if data_len < SPAN_LEN:
        return 0
    return ((data_len - SPAN_LEN) // SPAN_STEP) + 1


def weighted_interval_selection(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in opportunities
        if row["savings_bytes"] > 0 and row["start_offset"] < row["end_offset"]
    ]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
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


def analyze_corpus(row: dict[str, Any], maps: dict[str, Any]) -> dict[str, Any]:
    data = generate_packed_sidecar_replication.corpus_bytes(row["corpus"])
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        dedup_spans.add(span)
        for prefix_len in PREFIX_LADDER:
            if span[:prefix_len] in maps["prefix_sets"][prefix_len]:
                prefix_counts[prefix_len] += 1
                max_prefix = max(max_prefix, prefix_len)
        hit = maps["exact_by_span"].get(span)
        if hit is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(hit["seed_hex"])).digest()[:SPAN_LEN]
        if regenerated != span:
            raise RuntimeError("held-out exact hit failed regeneration")
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
        exact_hits.append(
            {
                "start_offset": start,
                "end_offset": start + SPAN_LEN,
                "span_len": SPAN_LEN,
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": SPAN_LEN - encoded_len,
                "regeneration_verified": True,
            }
        )

    selected = weighted_interval_selection(exact_hits)
    return {
        **row,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "byte_entropy": shannon_entropy(data),
        "ascii_printable_ratio": ascii_printable_ratio(data),
        "token_count": len(TOKEN_RE.findall(data)),
        "numeric_token_count": len(INTEGER_RE.findall(data)),
        "target_span_count": candidate_span_count(len(data)),
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
        "prefix_ge_8_count": prefix_counts[8],
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(
            1 for opportunity in exact_hits if opportunity["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": sum(opportunity["span_len"] for opportunity in selected),
        "encoded_seed_bytes": sum(opportunity["encoded_len"] for opportunity in selected),
        "net_seed_delta_bytes": sum(
            opportunity["encoded_len"] - opportunity["span_len"]
            for opportunity in selected
        ),
        "sample_selected_records": selected[:8],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_matrix = [row for row in rows if not row["in_corpus_matrix"]]
    missing_validation = [row for row in rows if not row["in_transform_validation"]]
    ordinary_rows = [
        row for row in rows if row["control_kind"] == "ordinary-structured"
    ]
    prefix5_rows = [row for row in rows if row["prefix_ge_5_count"] > 0]
    exact_rows = [row for row in rows if row["exact_hit_count"] > 0]
    selected_rows = [row for row in rows if row["selected_span_count"] > 0]
    ordinary_prefix5_groups = {
        row["independence_group"]
        for row in prefix5_rows
        if row["control_kind"] == "ordinary-structured"
    }
    control_prefix5_groups = {
        row["independence_group"]
        for row in prefix5_rows
        if row["control_kind"] != "ordinary-structured"
    }
    best_prefix = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["input_bytes"],
        ),
    )
    return {
        "corpus_count": len(rows),
        "ordinary_corpus_count": len(ordinary_rows),
        "control_corpus_count": len(rows) - len(ordinary_rows),
        "missing_corpus_matrix_count": len(missing_matrix),
        "missing_transform_validation_count": len(missing_validation),
        "missing_corpus_matrix_names": [row["name"] for row in missing_matrix],
        "missing_transform_validation_names": [row["name"] for row in missing_validation],
        "independence_group_count": len({row["independence_group"] for row in rows}),
        "total_input_bytes": sum(row["input_bytes"] for row in rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "numeric_token_count": sum(row["numeric_token_count"] for row in rows),
        "rows_with_prefix_ge_5": len(prefix5_rows),
        "rows_with_exact_hits": len(exact_rows),
        "rows_with_selected_spans": len(selected_rows),
        "ordinary_prefix5_group_count": len(ordinary_prefix5_groups),
        "control_prefix5_group_count": len(control_prefix5_groups),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_prefix_case": best_prefix["name"],
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_prefix_ge_5_count": best_prefix["prefix_ge_5_count"],
        "recommendation": (
            "Replication corpora expand held-out diversity, but raw bytes do not "
            "yet show prefix>=5, exact, or selected seed-span evidence."
            if not prefix5_rows and not exact_rows and not selected_rows
            else "Replication corpora produced raw prefix or exact signal that needs transform-specific follow-up."
        ),
    }


def top_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["max_prefix_observed"],
            -row["prefix_ge_5_count"],
            -row["prefix_ge_4_count"],
            -row["exact_hit_count"],
            -row["input_bytes"],
            row["name"],
        ),
    )[:TOP_LIMIT]


def build_report() -> dict[str, Any]:
    maps = seed_maps()
    rows = [analyze_corpus(row, maps) for row in corpus_manifest()]
    return {
        "generated_by": "scripts/generate_heldout_corpus_expansion.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "search_manifest_sha256": manifest_hash(),
        "search_manifest": search_manifest(),
        "corpora": corpus_manifest(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Held-Out Corpus Expansion",
        "",
        "Generated by `scripts/generate_heldout_corpus_expansion.py`.",
        "This is a corpus-coverage and raw seed-frontier audit, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Ordinary corpora: `{summary['ordinary_corpus_count']}`.",
        f"Control corpora: `{summary['control_corpus_count']}`.",
        f"Independence groups: `{summary['independence_group_count']}`.",
        f"Missing from corpus matrix: `{summary['missing_corpus_matrix_count']}`.",
        f"Missing from transform validation: `{summary['missing_transform_validation_count']}`.",
        f"Total input bytes: `{summary['total_input_bytes']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Numeric tokens: `{summary['numeric_token_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Ordinary prefix>=5 groups: `{summary['ordinary_prefix5_group_count']}`.",
        f"Control prefix>=5 groups: `{summary['control_prefix5_group_count']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        "",
        "## Summary",
        "",
        summary["recommendation"],
        "",
        "## Search Contract",
        "",
        f"- Hasher: `{HASHER}`.",
        f"- Max seed length: `{MAX_SEED_LEN}`.",
        f"- Span length: `{SPAN_LEN}`.",
        f"- Span step: `{SPAN_STEP}`.",
        "- Target block hashing: `false`.",
        "- Generated seed prefixes are compared directly against raw held-out corpus bytes.",
        "- This artifact deliberately avoids mutating the transform-validation matrix, so expensive downstream match/depth ledgers stay stable.",
        "- Promotion gate: add these corpora to transform validation only after a transform-specific follow-up predicts non-null prefix>=5 or exact-hit movement.",
        "- Stop rule: if raw prefix>=5, exact, and selected rows are all zero, do not spend on broad depth search solely because these corpora are larger.",
        "",
        "## Top Rows",
        "",
        "| corpus | kind | group | bytes | entropy | ascii | tokens | numbers | p4 | p5 | p6 | exact | selected | matrix | validation |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {control_kind} | {independence_group} | {input_bytes} | "
            "{byte_entropy} | {ascii_printable_ratio} | {token_count} | "
            "{numeric_token_count} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_hit_count} | {selected_span_count} | "
            "{in_corpus_matrix} | {in_transform_validation} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Missing Matrix Coverage",
            "",
            "Missing from `generate_corpus_matrix.CORPUS_MATRIX`:",
            "",
        ]
    )
    lines.extend(f"- `{name}`" for name in summary["missing_corpus_matrix_names"])
    lines.extend(
        [
            "",
            "Missing from `generate_transform_validation.CORPUS_VALIDATION_MATRIX`:",
            "",
        ]
    )
    lines.extend(f"- `{name}`" for name in summary["missing_transform_validation_names"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The replication corpora already exercise schema, API, medical, business, calendar, email, citation, ledger, patch, protocol, fixed-width, paired-shadow, and binary-control families.",
            "- This artifact makes their coverage explicit without invalidating expensive match-discovery and depth-search ledgers.",
            "- A future corpus-matrix expansion should be intentional and accompanied by regenerated transform-validation, match-discovery, alignment, and exact-discovery artifacts.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated held-out corpus expansion files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_heldout_corpus_expansion.py":
        raise SystemExit("heldout_corpus_expansion.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("held-out corpus expansion artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("held-out corpus expansion corpus manifest hash is stale")
    if payload.get("search_manifest_sha256") != manifest_hash():
        raise SystemExit("held-out corpus expansion search manifest hash is stale")
    if len(payload.get("rows", [])) != len(corpus_manifest()):
        raise SystemExit("held-out corpus expansion row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Held-Out Corpus Expansion",
        "raw seed-frontier audit",
        "Target block hashing: `false`",
        "Missing Matrix Coverage",
        "Promotion gate",
        "Stop rule",
    ):
        if phrase not in text:
            raise SystemExit(f"HELDOUT_CORPUS_EXPANSION.md missing phrase: {phrase}")


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
