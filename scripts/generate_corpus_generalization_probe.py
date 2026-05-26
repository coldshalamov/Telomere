#!/usr/bin/env python3
"""Generate cheap corpus generalization controls outside the expensive hash chain."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import zlib
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_results


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PROBE_JSON = DOCS / "corpus_generalization_probe.json"
PROBE_MD = DOCS / "CORPUS_GENERALIZATION_PROBE.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 24


CONTROL_MATRIX: list[dict[str, Any]] = [
    {
        "name": "shadow-csv-heldout",
        "kind": "shadow-vocab",
        "paired_with": "csv",
        "note": "CSV shape with vocabulary-disjoint hashed headers and values.",
    },
    {
        "name": "shadow-yaml-heldout",
        "kind": "shadow-vocab",
        "paired_with": "yaml",
        "note": "YAML/list shape with vocabulary-disjoint hashed keys and atoms.",
    },
    {
        "name": "natural-prose-heldout",
        "kind": "natural-prose",
        "paired_with": None,
        "note": "Deterministic public-domain-style prose with no Telomere terms.",
    },
    {
        "name": "json-record-shuffle-control",
        "kind": "record-order-control",
        "paired_with": "json",
        "note": "Structured JSON lines in deterministic hash order.",
    },
    {
        "name": "zlib-json-control",
        "kind": "compressed-control",
        "paired_with": "json",
        "note": "zlib-compressed structured JSON bytes.",
    },
    {
        "name": "length-matched-random-control",
        "kind": "random-control",
        "paired_with": "json",
        "note": "Deterministic pseudorandom bytes length-matched to structured JSON.",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
    }


def control_manifest_hash() -> str:
    payload = json.dumps(CONTROL_MATRIX, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


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
        "match_rule": "generated seed prefixes are compared directly against raw control bytes",
        "scope": "cheap corpus generalization probe only; not added to the expensive corpus matrix hash chain",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def shadow_atom(label: str, idx: int, width: int = 12) -> str:
    return hashlib.sha256(f"{label}:{idx}".encode()).hexdigest()[:width]


def shadow_csv_bytes() -> bytes:
    headers = [shadow_atom("csv-header", idx, 8) for idx in range(5)]
    rows = [",".join(headers)]
    for idx in range(260):
        rows.append(
            ",".join(
                [
                    str(idx),
                    shadow_atom("csv-sku", idx % 17, 10),
                    shadow_atom("csv-status", idx % 4, 10),
                    str((idx * 31337 + 2499) % 100_000),
                    shadow_atom("csv-region", idx % 4, 8),
                ]
            )
        )
    return ("\n".join(rows) + "\n").encode("ascii")


def shadow_yaml_bytes() -> bytes:
    lines: list[str] = []
    for idx in range(170):
        lines.extend(
            [
                f"- {shadow_atom('yaml-key', 0)}: {idx}",
                f"  {shadow_atom('yaml-key', 1)}: {shadow_atom('yaml-value', idx % 23)}",
                f"  {shadow_atom('yaml-key', 2)}:",
                f"    - {shadow_atom('yaml-list', idx % 19)}",
                f"    - {shadow_atom('yaml-list', (idx * 3 + 1) % 19)}",
                f"  {shadow_atom('yaml-key', 3)}: {(idx * 17) % 251}",
            ]
        )
    return ("\n".join(lines) + "\n").encode("ascii")


def natural_prose_bytes() -> bytes:
    paragraphs: list[str] = []
    subjects = (
        "the winter river",
        "an old observatory",
        "the harbor bell",
        "a quiet orchard",
        "the northern road",
    )
    verbs = (
        "carried",
        "remembered",
        "softened",
        "answered",
        "gathered",
    )
    objects = (
        "lamplight across the stones",
        "letters from another season",
        "rain along the slate roofs",
        "footsteps near the market",
        "salt wind under the door",
    )
    for idx in range(180):
        paragraphs.append(
            (
                f"In chapter {idx:03d}, {subjects[idx % len(subjects)]} "
                f"{verbs[(idx * 2) % len(verbs)]} {objects[(idx * 3) % len(objects)]}. "
                f"The scene moved slowly, as if each small sound had been kept for later."
            )
        )
    return ("\n\n".join(paragraphs) + "\n").encode("utf-8")


def json_record_shuffle_bytes() -> bytes:
    lines = generate_results.structured_json_bytes().splitlines()
    return b"\n".join(sorted(lines, key=lambda line: hashlib.sha256(line).digest())) + b"\n"


def zlib_json_bytes() -> bytes:
    return zlib.compress(generate_results.structured_json_bytes(), level=9)


def length_matched_random_bytes() -> bytes:
    return generate_results.deterministic_bytes(
        "corpus-generalization-length-matched-random",
        len(generate_results.structured_json_bytes()),
    )


def control_bytes(name: str) -> bytes:
    if name == "shadow-csv-heldout":
        return shadow_csv_bytes()
    if name == "shadow-yaml-heldout":
        return shadow_yaml_bytes()
    if name == "natural-prose-heldout":
        return natural_prose_bytes()
    if name == "json-record-shuffle-control":
        return json_record_shuffle_bytes()
    if name == "zlib-json-control":
        return zlib_json_bytes()
    if name == "length-matched-random-control":
        return length_matched_random_bytes()
    raise ValueError(name)


def paired_bytes(name: str | None) -> bytes | None:
    if name is None:
        return None
    return generate_corpus_matrix.corpus_bytes(name)


def text_lexemes(data: bytes) -> set[str]:
    return generate_corpus_matrix.text_lexemes(data)


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def candidate_span_count(data_len: int) -> int:
    return generate_manifold_report.candidate_span_count(data_len, SPAN_LEN, SPAN_STEP)


@lru_cache(maxsize=1)
def seed_digests() -> tuple[tuple[int, bytes, bytes], ...]:
    output = []
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        output.append((seed_index, seed, hashlib.sha256(seed).digest()))
    return tuple(output)


@lru_cache(maxsize=None)
def generated_prefix_map(prefix_len: int) -> dict[bytes, dict[str, Any]]:
    mapping: dict[bytes, dict[str, Any]] = {}
    for seed_index, seed, digest in seed_digests():
        mapping.setdefault(
            digest[:prefix_len],
            {
                "seed_index": seed_index,
                "seed_len": len(seed),
                "seed_hex": seed.hex(),
            },
        )
    return mapping


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


def analyze_control(control: dict[str, Any]) -> dict[str, Any]:
    data = control_bytes(control["name"])
    paired = paired_bytes(control.get("paired_with"))
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []

    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        dedup_spans.add(span)
        for prefix_len in PREFIX_LADDER:
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                prefix_counts[prefix_len] += 1
        for prefix_len in sorted(PREFIX_LADDER, reverse=True):
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                max_prefix = max(max_prefix, prefix_len)
                break
        hit = generated_prefix_map(SPAN_LEN).get(span)
        if hit is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(hit["seed_hex"])).digest()[:SPAN_LEN]
        if regenerated != span:
            raise RuntimeError("generated-prefix map produced an unverified hit")
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
    selected_seed_bytes = sum(row["encoded_len"] for row in selected)
    selected_literal_bytes = sum(row["span_len"] for row in selected)
    overlap = None
    if paired is not None:
        source_lexemes = text_lexemes(paired)
        control_lexemes = text_lexemes(data)
        overlap = round(
            len(source_lexemes & control_lexemes) / max(1, len(source_lexemes)),
            6,
        )

    return {
        "name": control["name"],
        "kind": control["kind"],
        "paired_with": control.get("paired_with"),
        "note": control["note"],
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "paired_sha256": hashlib.sha256(paired).hexdigest() if paired is not None else None,
        "byte_entropy": byte_entropy(data),
        "ascii_printable_ratio": generate_corpus_matrix.ascii_printable_ratio(data),
        "lexeme_overlap_rate": overlap,
        "target_span_count": candidate_span_count(len(data)),
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(
            1 for row in exact_hits if row["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": selected_literal_bytes,
        "encoded_seed_bytes": selected_seed_bytes,
        "net_seed_delta_bytes": selected_seed_bytes - selected_literal_bytes,
        "selected_records": selected[:8],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    exact = [row for row in rows if row["exact_hit_count"] > 0]
    selected = [row for row in rows if row["selected_span_count"] > 0]
    best = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["name"],
        ),
    )
    return {
        "control_count": len(rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(prefix5),
        "rows_with_exact_hits": len(exact),
        "rows_with_selected_spans": len(selected),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_prefix_case": best["name"],
        "best_prefix_observed": best["max_prefix_observed"],
        "best_prefix_ge_4_count": best["prefix_ge_4_count"],
        "conclusion": (
            "Corpus generalization controls produced selected exact spans."
            if selected
            else (
                "Corpus generalization controls produced exact hits, but no selected spans."
                if exact
                else "Corpus generalization controls did not produce exact seed-span rows."
            )
        ),
    }


def top_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["selected_span_count"],
            -row["exact_hit_count"],
            -row["max_prefix_observed"],
            -row["prefix_ge_5_count"],
            -row["prefix_ge_4_count"],
            row["name"],
        ),
    )[:TOP_LIMIT]


def build_report() -> dict[str, Any]:
    rows = [analyze_control(control) for control in CONTROL_MATRIX]
    return {
        "generated_by": "scripts/generate_corpus_generalization_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "control_manifest_sha256": control_manifest_hash(),
        "search_manifest_sha256": search_manifest_hash(),
        "search_manifest": search_manifest(),
        "controls": CONTROL_MATRIX,
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    PROBE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Corpus Generalization Probe",
        "",
        "Generated by `scripts/generate_corpus_generalization_probe.py`.",
        "This is a cheap overfitting-control probe outside the expensive corpus-matrix hash chain.",
        "",
        f"Controls: `{summary['control_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        "",
        "## Search Contract",
        "",
        f"- Hasher: `{HASHER}`.",
        f"- Max seed length: `{MAX_SEED_LEN}`.",
        f"- Span length: `{SPAN_LEN}`.",
        f"- Span step: `{SPAN_STEP}`.",
        "- Target block hashing: `false`.",
        "- Generated seed prefixes are compared directly against raw control bytes.",
        "- Promotion requires prefix>=5 movement or exact hits while shadow/random/compressed controls stay null.",
        "",
        "## Controls",
        "",
        "| control | kind | paired | bytes | entropy | lexeme overlap | p4 | p5 | p6 | exact | selected |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        overlap = "-" if row["lexeme_overlap_rate"] is None else row["lexeme_overlap_rate"]
        lines.append(
            "| {name} | {kind} | {paired} | {input_bytes} | {byte_entropy} | {overlap} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_hit_count} | {selected_span_count} |".format(
                paired=row["paired_with"] or "-",
                overlap=overlap,
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact is intentionally separate from `docs/corpus_matrix.json` so it does not stale the expensive downstream discovery chain.",
            "- Shadow controls attack literal-token overfit by preserving syntax shape while changing vocabulary.",
            "- Random and zlib controls test high-entropy behavior before any new transform lead is promoted.",
            "- If all controls stay exact-null, the next move is new record-aware transform families rather than broadening current transforms.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated corpus generalization probe files are missing")
    payload = load_json(PROBE_JSON)
    if payload.get("generated_by") != "scripts/generate_corpus_generalization_probe.py":
        raise SystemExit("corpus_generalization_probe.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("corpus generalization probe artifact hashes are stale")
    if payload.get("control_manifest_sha256") != control_manifest_hash():
        raise SystemExit("corpus generalization probe control manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("corpus generalization probe search manifest hash is stale")
    if len(payload.get("rows", [])) != len(CONTROL_MATRIX):
        raise SystemExit("corpus generalization probe row count is stale")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Corpus Generalization Probe",
        "outside the expensive corpus-matrix hash chain",
        "Target block hashing: `false`",
        "literal-token overfit",
        "Random and zlib controls",
    ):
        if phrase not in text:
            raise SystemExit(f"CORPUS_GENERALIZATION_PROBE.md missing phrase: {phrase}")


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
