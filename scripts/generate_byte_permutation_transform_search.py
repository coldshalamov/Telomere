#!/usr/bin/env python3
"""Search reversible byte-permutation transforms as seed-manifold alignment leads."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "byte_permutation_transform_search.json"
REPORT_MD = DOCS / "BYTE_PERMUTATION_TRANSFORM_SEARCH.md"
CORPUS_MATRIX_JSON = DOCS / "corpus_matrix.json"
TRANSFORM_VALIDATION_JSON = DOCS / "transform_validation.json"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6, 7, 8)
SEED_RECORD_OVERHEAD_BYTES = 4
EXACT_RECORD_LIMIT = 16

TRANSFORMS: tuple[dict[str, Any], ...] = (
    {
        "name": "identity",
        "family": "identity",
        "phase": 1,
        "source_order": "identity",
        "target_order": "identity",
        "target_distribution": "identity",
        "metadata_bytes": 0,
        "reason": "baseline",
    },
    {
        "name": "global-freq-to-seed-common",
        "family": "byte-permutation",
        "phase": 1,
        "source_order": "freq-desc",
        "target_order": "freq-desc",
        "target_distribution": "seed-mean",
        "metadata_bytes": 256,
        "reason": "map frequent source bytes to the most common finite seed-output bytes",
    },
    {
        "name": "global-freq-to-seed-rare",
        "family": "byte-permutation",
        "phase": 1,
        "source_order": "freq-desc",
        "target_order": "freq-asc",
        "target_distribution": "seed-mean",
        "metadata_bytes": 256,
        "reason": "opposite-rank control for global seed-output byte alignment",
    },
    {
        "name": "global-rare-to-seed-common",
        "family": "byte-permutation",
        "phase": 1,
        "source_order": "freq-asc",
        "target_order": "freq-desc",
        "target_distribution": "seed-mean",
        "metadata_bytes": 256,
        "reason": "rare-source control for finite seed-output byte alignment",
    },
    {
        "name": "phase4-freq-to-seed-pos",
        "family": "phase-byte-permutation",
        "phase": 4,
        "source_order": "freq-desc",
        "target_order": "freq-desc",
        "target_distribution": "seed-position",
        "metadata_bytes": 4 * 256,
        "reason": "map phase-local source frequencies to seed-output bytes at matching phase",
    },
    {
        "name": "phase4-rare-to-seed-pos",
        "family": "phase-byte-permutation",
        "phase": 4,
        "source_order": "freq-asc",
        "target_order": "freq-desc",
        "target_distribution": "seed-position",
        "metadata_bytes": 4 * 256,
        "reason": "phase-local rare-source control",
    },
    {
        "name": "phase8-freq-to-seed-pos",
        "family": "phase-byte-permutation",
        "phase": 8,
        "source_order": "freq-desc",
        "target_order": "freq-desc",
        "target_distribution": "seed-position",
        "metadata_bytes": 8 * 256,
        "reason": "span-position byte permutation against the first 8 seed-output bytes",
    },
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(CORPUS_MATRIX_JSON),
        "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_JSON),
    }


def seed_len_offset(seed_len: int) -> int:
    return sum(256**length for length in range(1, seed_len))


def iter_seeds(max_seed_len: int = MAX_SEED_LEN):
    for seed_len in range(1, max_seed_len + 1):
        offset = seed_len_offset(seed_len)
        for value in range(256**seed_len):
            seed = value.to_bytes(seed_len, "big")
            yield offset + value, seed


def seed_maps() -> dict[str, Any]:
    prefix_sets: dict[int, set[bytes]] = {prefix_len: set() for prefix_len in PREFIX_LADDER}
    exact_by_span: dict[bytes, dict[str, Any]] = {}
    position_counts: list[Counter[int]] = [Counter() for _ in range(SPAN_LEN)]
    mean_counts: Counter[int] = Counter()

    for seed_index, seed in iter_seeds():
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
        for position, value in enumerate(span):
            position_counts[position][value] += 1
            mean_counts[value] += 1

    return {
        "prefix_sets": prefix_sets,
        "exact_by_span": exact_by_span,
        "position_counts": position_counts,
        "mean_counts": mean_counts,
    }


def byte_rank(counter: Counter[int], order: str) -> list[int]:
    if order == "identity":
        return list(range(256))
    if order == "freq-desc":
        return sorted(range(256), key=lambda byte: (-counter[byte], byte))
    if order == "freq-asc":
        return sorted(range(256), key=lambda byte: (counter[byte], byte))
    raise ValueError(order)


def target_counter(spec: dict[str, Any], maps: dict[str, Any], phase_index: int) -> Counter[int]:
    distribution = spec["target_distribution"]
    if distribution == "identity":
        return Counter({byte: 1 for byte in range(256)})
    if distribution == "seed-mean":
        return maps["mean_counts"]
    if distribution == "seed-position":
        return maps["position_counts"][phase_index % SPAN_LEN]
    raise ValueError(distribution)


def source_phase_counts(data: bytes, phase: int) -> list[Counter[int]]:
    counters = [Counter() for _ in range(phase)]
    for offset, value in enumerate(data):
        counters[offset % phase][value] += 1
    return counters


def build_phase_maps(
    data: bytes, spec: dict[str, Any], maps: dict[str, Any]
) -> list[dict[int, int]]:
    phase = int(spec["phase"])
    if spec["source_order"] == "identity" and spec["target_order"] == "identity":
        return [{byte: byte for byte in range(256)} for _ in range(phase)]

    source_counts = source_phase_counts(data, phase)
    phase_maps: list[dict[int, int]] = []
    for phase_index in range(phase):
        source_bytes = byte_rank(source_counts[phase_index], spec["source_order"])
        target_bytes = byte_rank(target_counter(spec, maps, phase_index), spec["target_order"])
        phase_maps.append(dict(zip(source_bytes, target_bytes, strict=True)))
    return phase_maps


def apply_phase_maps(data: bytes, phase_maps: list[dict[int, int]]) -> bytes:
    phase = len(phase_maps)
    return bytes(phase_maps[offset % phase][value] for offset, value in enumerate(data))


def invert_phase_maps(phase_maps: list[dict[int, int]]) -> list[dict[int, int]]:
    return [{dst: src for src, dst in mapping.items()} for mapping in phase_maps]


def prove_reversible(data: bytes, transformed: bytes, phase_maps: list[dict[int, int]]) -> None:
    recovered = apply_phase_maps(transformed, invert_phase_maps(phase_maps))
    if recovered != data:
        raise RuntimeError("byte permutation transform is not reversible")


def count_prefixes(data: bytes, prefix_sets: dict[int, set[bytes]]) -> tuple[dict[int, int], int, int]:
    counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    span_count = 0
    if len(data) < SPAN_LEN:
        return counts, max_prefix, span_count
    for start in range(0, len(data) - SPAN_LEN + 1, SPAN_STEP):
        span_count += 1
        span = data[start : start + SPAN_LEN]
        for prefix_len in PREFIX_LADDER:
            if span[:prefix_len] in prefix_sets[prefix_len]:
                counts[prefix_len] += 1
                max_prefix = max(max_prefix, prefix_len)
    return counts, max_prefix, span_count


def exact_hits(data: bytes, exact_by_span: dict[bytes, dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if len(data) < SPAN_LEN:
        return hits
    for start in range(0, len(data) - SPAN_LEN + 1, SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        seed = exact_by_span.get(span)
        if seed is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(seed["seed_hex"])).digest()[:SPAN_LEN]
        if regenerated != span:
            raise RuntimeError("exact hit failed regeneration")
        encoded_len = int(seed["seed_len"]) + SEED_RECORD_OVERHEAD_BYTES
        hits.append(
            {
                "start": start,
                "end": start + SPAN_LEN,
                "span_len": SPAN_LEN,
                "seed_index": seed["seed_index"],
                "seed_len": seed["seed_len"],
                "seed_hex": seed["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": SPAN_LEN - encoded_len,
            }
        )
    return hits


def weighted_interval_selection(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positive = [hit for hit in hits if hit["savings_bytes"] > 0]
    if not positive:
        return []
    ordered = sorted(positive, key=lambda hit: (hit["end"], hit["start"], -hit["savings_bytes"]))
    ends = [hit["end"] for hit in ordered]
    previous: list[int] = []
    for hit in ordered:
        lo, hi = 0, len(ends)
        while lo < hi:
            mid = (lo + hi) // 2
            if ends[mid] <= hit["start"]:
                lo = mid + 1
            else:
                hi = mid
        previous.append(lo - 1)

    dp = [0] * (len(ordered) + 1)
    take = [False] * len(ordered)
    for idx, hit in enumerate(ordered, start=1):
        include = hit["savings_bytes"] + dp[previous[idx - 1] + 1]
        exclude = dp[idx - 1]
        if include > exclude:
            dp[idx] = include
            take[idx - 1] = True
        else:
            dp[idx] = exclude

    selected: list[dict[str, Any]] = []
    idx = len(ordered)
    while idx > 0:
        if take[idx - 1]:
            selected.append(ordered[idx - 1])
            idx = previous[idx - 1] + 1
        else:
            idx -= 1
    selected.reverse()
    return selected


def corpus_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX]


def analyze_case(
    corpus: dict[str, Any], spec: dict[str, Any], maps: dict[str, Any]
) -> dict[str, Any]:
    data = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    phase_maps = build_phase_maps(data, spec, maps)
    transformed = apply_phase_maps(data, phase_maps)
    prove_reversible(data, transformed, phase_maps)
    prefix_counts, max_prefix, target_span_count = count_prefixes(
        transformed, maps["prefix_sets"]
    )
    hits = exact_hits(transformed, maps["exact_by_span"])
    selected = weighted_interval_selection(hits)
    literal_bytes_replaced = sum(hit["span_len"] for hit in selected)
    encoded_seed_bytes = sum(hit["encoded_len"] for hit in selected)
    net_seed_delta = encoded_seed_bytes - literal_bytes_replaced
    net_with_metadata = net_seed_delta + int(spec["metadata_bytes"])
    transform_name = spec["name"]
    return {
        "name": f"{corpus['name']}::{transform_name}",
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus.get("control_kind", "ordinary-structured"),
        "transform": transform_name,
        "family": spec["family"],
        "phase": spec["phase"],
        "source_order": spec["source_order"],
        "target_order": spec["target_order"],
        "target_distribution": spec["target_distribution"],
        "metadata_bytes": spec["metadata_bytes"],
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "payload_sha256": hashlib.sha256(transformed).hexdigest(),
        "ascii_printable_ratio": generate_corpus_matrix.ascii_printable_ratio(transformed),
        "target_span_count": target_span_count,
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
        "prefix_ge_7_count": prefix_counts[7],
        "prefix_ge_8_count": prefix_counts[8],
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(hits),
        "positive_exact_hit_count": sum(1 for hit in hits if hit["savings_bytes"] > 0),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": literal_bytes_replaced,
        "encoded_seed_bytes": encoded_seed_bytes,
        "net_seed_delta_bytes": net_seed_delta,
        "net_with_metadata_bytes": net_with_metadata,
        "metadata_profitable": bool(selected) and net_with_metadata < 0,
        "exact_hit_records": hits[:EXACT_RECORD_LIMIT],
        "selected_records": selected[:EXACT_RECORD_LIMIT],
    }


def transform_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "compare generated SHA-256(seed) prefixes directly against raw transformed target bytes",
        "transforms": TRANSFORMS,
        "corpora": corpus_rows(),
    }


def transform_manifest_hash() -> str:
    payload = json.dumps(transform_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    exact = [row for row in rows if row["exact_hit_count"] > 0]
    selected = [row for row in rows if row["selected_span_count"] > 0]
    profitable = [row for row in rows if row["metadata_profitable"]]
    best_prefix = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["prefix_ge_3_count"],
            row["name"],
        ),
    )
    best_net = min(rows, key=lambda row: (row["net_with_metadata_bytes"], row["name"]))
    return {
        "corpus_count": len(corpus_rows()),
        "transform_count": len(TRANSFORMS),
        "row_count": len(rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(prefix5),
        "rows_with_exact_hits": len(exact),
        "rows_with_selected_spans": len(selected),
        "rows_negative_after_metadata": len(profitable),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_prefix_case": best_prefix["name"],
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_prefix_ge_5_count": best_prefix["prefix_ge_5_count"],
        "best_net_case": best_net["name"],
        "best_net_delta_bytes": best_net["net_with_metadata_bytes"],
        "conclusion": (
            "Byte-permutation transforms produced metadata-profitable selected seed-span rows."
            if profitable
            else (
                "Byte-permutation transforms produced exact hits, but none survived metadata economics."
                if exact
                else (
                    "Byte-permutation transforms produced prefix>=5 movement only."
                    if prefix5
                    else "Byte-permutation transforms did not produce prefix>=5 or exact seed-span rows."
                )
            )
        ),
    }


def top_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["metadata_profitable"],
            row["selected_span_count"],
            row["positive_exact_hit_count"],
            row["exact_hit_count"],
            row["prefix_ge_6_count"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            -row["net_with_metadata_bytes"],
        ),
        reverse=True,
    )[:24]


def build_report() -> dict[str, Any]:
    maps = seed_maps()
    rows = [
        analyze_case(corpus, spec, maps)
        for corpus in corpus_rows()
        for spec in TRANSFORMS
    ]
    return {
        "generated_by": "scripts/generate_byte_permutation_transform_search.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "transform_manifest_sha256": transform_manifest_hash(),
        "manifest": transform_manifest(),
        "summary": summarize(rows),
        "results": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Byte-Permutation Transform Search",
        "",
        "Generated by `scripts/generate_byte_permutation_transform_search.py`.",
        "This is a bounded reversible-transform research probe, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Transforms: `{summary['transform_count']}`.",
        f"Rows: `{summary['row_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Rows negative after metadata: `{summary['rows_negative_after_metadata']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        "",
        "## Conclusion",
        "",
        summary["conclusion"],
        "",
        "## Search Contract",
        "",
        "- Target block hashing: `false`.",
        "- Generated SHA-256(seed) prefixes are compared directly against raw transformed target bytes.",
        "- Every exact hit is regenerated from the seed before it is counted.",
        "- Each byte permutation is proved reversible before metrics are accepted.",
        "- Permutation table metadata is charged before any promotion claim.",
        "",
        "## Top Rows",
        "",
        "| row | transform | phase | p4 | p5 | p6 | exact | selected | net metadata |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["results"]):
        lines.append(
            "| {name} | {transform} | {phase} | {prefix_ge_4_count} | "
            "{prefix_ge_5_count} | {prefix_ge_6_count} | {exact_hit_count} | "
            "{selected_span_count} | {net_with_metadata_bytes} |".format(**row)
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated byte permutation transform search files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_byte_permutation_transform_search.py":
        raise SystemExit("byte_permutation_transform_search.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("byte permutation transform search artifact hashes are stale")
    if payload.get("transform_manifest_sha256") != transform_manifest_hash():
        raise SystemExit("byte permutation transform manifest hash is stale")
    expected_rows = len(corpus_rows()) * len(TRANSFORMS)
    if payload.get("summary", {}).get("row_count") != expected_rows:
        raise SystemExit("byte permutation transform search row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Byte-Permutation Transform Search",
        "Target block hashing: `false`",
        "Every exact hit is regenerated",
        "proved reversible",
        "metadata is charged",
    ):
        if phrase not in text:
            raise SystemExit(f"BYTE_PERMUTATION_TRANSFORM_SEARCH.md missing phrase: {phrase}")


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
