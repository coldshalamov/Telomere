#!/usr/bin/env python3
"""Generate Telomere seed-output manifold proximity diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results
import generate_transform_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFOLD_JSON = DOCS / "manifold.json"
MANIFOLD_MD = DOCS / "MANIFOLD.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1


MANIFOLD_CASES: list[dict[str, Any]] = [
    {
        "name": "structured-json-raw",
        "kind": "structured-control",
        "source": "structured-json",
        "transform": "identity",
        "note": "Raw deterministic structured JSON corpus.",
    },
    {
        "name": "structured-json-static-token",
        "kind": "transform-control",
        "source": "structured-json",
        "transform": "static-json-token",
        "note": "Static token preconditioner bytes before any format support.",
    },
    {
        "name": "random-same-size",
        "kind": "random-control",
        "source": "random-same-size",
        "transform": "identity",
        "note": "Deterministic pseudorandom bytes with the same size as structured JSON.",
    },
    {
        "name": "planted-span8-positive",
        "kind": "planted-positive-control",
        "source": "planted-span8-full",
        "transform": "identity",
        "note": "Repeated SHA256(seed 0) span8 fixture; proves the detector sees planted manifold membership.",
    },
]


def seed_count(max_seed_len: int) -> int:
    return sum(256**length for length in range(1, max_seed_len + 1))


def iter_seed_bytes(max_seed_len: int):
    for seed_len in range(1, max_seed_len + 1):
        for value in range(256**seed_len):
            yield value.to_bytes(seed_len, "big")


def generated_prefix_sets(max_seed_len: int, span_len: int) -> list[set[bytes]]:
    prefixes = [set() for _ in range(span_len + 1)]
    for seed in iter_seed_bytes(max_seed_len):
        digest = hashlib.sha256(seed).digest()[:span_len]
        for prefix_len in range(1, span_len + 1):
            prefixes[prefix_len].add(digest[:prefix_len])
    return prefixes


def candidate_span_count(input_bytes: int, span_len: int, span_step: int) -> int:
    if input_bytes < span_len:
        return 0
    return 1 + (input_bytes - span_len) // span_step


def expected_random_ge_count(
    candidate_spans: int,
    prefix_sets: list[set[bytes]],
    prefix_len: int,
) -> float:
    return candidate_spans * len(prefix_sets[prefix_len]) / float(2 ** (8 * prefix_len))


def corpus_bytes(source: str) -> bytes:
    if source == "structured-json":
        return generate_results.structured_json_bytes()
    if source == "random-same-size":
        return generate_results.deterministic_bytes(
            "manifold-random-same-size",
            len(generate_results.structured_json_bytes()),
        )
    if source == "planted-span8-full":
        return generate_results.planted_span(SPAN_LEN) * 128
    raise ValueError(source)


def transformed_bytes(case: dict[str, Any]) -> tuple[bytes, int]:
    data = corpus_bytes(case["source"])
    transform = case["transform"]
    if transform == "identity":
        return data, 0
    transformed = generate_transform_sweeps.apply_transform(transform, data)
    restored = generate_transform_sweeps.invert_transform(
        transform,
        transformed.data,
        transformed.metadata,
    )
    if restored != data:
        raise RuntimeError(f"{case['name']}: transform did not roundtrip")
    return transformed.data, transformed.overhead_bytes


def longest_generated_prefix(span: bytes, prefix_sets: list[set[bytes]]) -> int:
    for prefix_len in range(min(len(span), len(prefix_sets) - 1), 0, -1):
        if span[:prefix_len] in prefix_sets[prefix_len]:
            return prefix_len
    return 0


def analyze_case(case: dict[str, Any], prefix_sets: list[set[bytes]]) -> dict[str, Any]:
    data, transform_overhead = transformed_bytes(case)
    histogram: Counter[int] = Counter()
    spans = candidate_span_count(len(data), SPAN_LEN, SPAN_STEP)
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        histogram[longest_generated_prefix(span, prefix_sets)] += 1

    exact = histogram[SPAN_LEN]
    prefix_ge_3 = sum(count for prefix_len, count in histogram.items() if prefix_len >= 3)
    prefix_ge_4 = sum(count for prefix_len, count in histogram.items() if prefix_len >= 4)
    prefix_ge_6 = sum(count for prefix_len, count in histogram.items() if prefix_len >= 6)
    return {
        "name": case["name"],
        "kind": case["kind"],
        "source": case["source"],
        "transform": case["transform"],
        "note": case["note"],
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "input_bytes": len(data),
        "transform_overhead_bytes": transform_overhead,
        "candidate_spans": spans,
        "longest_prefix_histogram": {str(key): histogram.get(key, 0) for key in range(SPAN_LEN + 1)},
        "exact_span_hits": exact,
        "prefix_ge_3_count": prefix_ge_3,
        "prefix_ge_4_count": prefix_ge_4,
        "prefix_ge_6_count": prefix_ge_6,
        "prefix_ge_3_rate": prefix_ge_3 / spans if spans else 0.0,
        "prefix_ge_4_rate": prefix_ge_4 / spans if spans else 0.0,
        "prefix_ge_6_rate": prefix_ge_6 / spans if spans else 0.0,
        "expected_random_prefix_ge_3": expected_random_ge_count(spans, prefix_sets, 3),
        "expected_random_prefix_ge_4": expected_random_ge_count(spans, prefix_sets, 4),
        "expected_random_prefix_ge_6": expected_random_ge_count(spans, prefix_sets, 6),
        "expected_random_exact": expected_random_ge_count(spans, prefix_sets, SPAN_LEN),
    }


def case_manifest() -> list[dict[str, Any]]:
    fields = ("name", "kind", "source", "transform", "note")
    return [{field: case[field] for field in fields} for case in MANIFOLD_CASES]


def case_manifest_hash() -> str:
    payload = json.dumps(case_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_report() -> dict[str, Any]:
    prefix_sets = generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    results = [analyze_case(case, prefix_sets) for case in MANIFOLD_CASES]
    best_non_planted = max(
        (row for row in results if row["kind"] != "planted-positive-control"),
        key=lambda row: (row["prefix_ge_4_count"], row["prefix_ge_6_count"], row["exact_span_hits"]),
    )
    best_non_planted_prefix3 = max(
        (row for row in results if row["kind"] != "planted-positive-control"),
        key=lambda row: row["prefix_ge_3_count"],
    )
    return {
        "generated_by": "scripts/generate_manifold_report.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "case_manifest_sha256": case_manifest_hash(),
        "case_manifest": case_manifest(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_count": seed_count(MAX_SEED_LEN),
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "generated_prefix_counts": {
            str(prefix_len): len(prefix_sets[prefix_len]) for prefix_len in range(1, SPAN_LEN + 1)
        },
        "results": results,
        "summary": {
            "best_non_planted_case": best_non_planted["name"],
            "best_non_planted_prefix_ge_4_count": best_non_planted["prefix_ge_4_count"],
            "best_non_planted_exact_span_hits": best_non_planted["exact_span_hits"],
            "best_non_planted_prefix_ge_3_case": best_non_planted_prefix3["name"],
            "best_non_planted_prefix_ge_3_count": best_non_planted_prefix3["prefix_ge_3_count"],
            "best_non_planted_prefix_ge_3_expected_random": best_non_planted_prefix3[
                "expected_random_prefix_ge_3"
            ],
            "conclusion": (
                "Current non-planted controls do not show meaningful proximity to the "
                "depth-2 SHA-256 Lotus seed-output manifold; the planted control does."
            ),
        },
    }


def write_report(payload: dict[str, Any]) -> None:
    MANIFOLD_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Manifold Proximity Report",
        "",
        "Generated by `scripts/generate_manifold_report.py`.",
        "This is a diagnostic, not a compression benchmark: it asks how close target spans are to generated Lotus seed-output prefixes.",
        "",
        f"Hasher: `{payload['hasher']}`.",
        f"Max seed len: `{payload['max_seed_len']}`.",
        f"Seed count: `{payload['seed_count']}`.",
        f"Span len: `{payload['span_len']}`.",
        f"Span step: `{payload['span_step']}`.",
        "",
        "## Generated Prefix Set",
        "",
        "| prefix bytes | distinct generated prefixes |",
        "| ---: | ---: |",
    ]
    for prefix_len, count in payload["generated_prefix_counts"].items():
        lines.append(f"| {prefix_len} | {count} |")

    lines.extend(
        [
            "",
            "## Proximity Matrix",
            "",
            "| case | kind | bytes | spans | exact hits | prefix >=3 | expected >=3 | prefix >=4 | expected >=4 | prefix >=6 | expected >=6 | expected exact |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["results"]:
        lines.append(
            "| {name} | {kind} | {input_bytes} | {candidate_spans} | {exact_span_hits} | "
            "{prefix_ge_3_count} | {expected_random_prefix_ge_3:.3f} | "
            "{prefix_ge_4_count} | {expected_random_prefix_ge_4:.3f} | "
            "{prefix_ge_6_count} | {expected_random_prefix_ge_6:.3e} | "
            "{expected_random_exact:.3e} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Longest Prefix Histograms",
            "",
            "Each histogram bucket is the longest generated-prefix length matched by a target span.",
        ]
    )
    for row in payload["results"]:
        histogram = ", ".join(
            f"{prefix}:{count}"
            for prefix, count in row["longest_prefix_histogram"].items()
            if count
        )
        lines.append(f"- `{row['name']}`: {histogram}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            payload["summary"]["conclusion"],
            "The strongest non-planted prefix-3 signal is `{}` with {} spans versus {:.3f} expected under the random model; this is not yet close to a profitable v2 seed-span record, but it is a useful target for future transform design.".format(
                payload["summary"]["best_non_planted_prefix_ge_3_case"],
                payload["summary"]["best_non_planted_prefix_ge_3_count"],
                payload["summary"]["best_non_planted_prefix_ge_3_expected_random"],
            ),
            "",
            "- Exact seed-span hits remain the compressor's hard requirement.",
            "- Prefix proximity is useful research telemetry because a natural corpus with many long generated-prefix overlaps would justify deeper search or candidate bundling work.",
            "- If raw and transformed controls look like random controls, more compute alone has no observed gradient yet.",
            "- The planted positive control prevents a false negative in the diagnostic harness.",
        ]
    )
    MANIFOLD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not MANIFOLD_JSON.exists() or not MANIFOLD_MD.exists():
        raise SystemExit("generated manifold report files are missing")
    payload = json.loads(MANIFOLD_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_manifold_report.py":
        raise SystemExit("manifold.json has wrong generated_by marker")
    if payload.get("case_manifest_sha256") != case_manifest_hash():
        raise SystemExit("manifold.json case manifest hash is stale")
    expected_names = [case["name"] for case in MANIFOLD_CASES]
    actual_names = [row.get("name") for row in payload.get("results", [])]
    if actual_names != expected_names:
        raise SystemExit("manifold.json does not contain the full case matrix")
    planted = next(row for row in payload["results"] if row["name"] == "planted-span8-positive")
    if planted["exact_span_hits"] == 0:
        raise SystemExit("manifold positive control did not find exact hits")
    text = MANIFOLD_MD.read_text(encoding="utf-8")
    for phrase in (
        "diagnostic, not a compression benchmark",
        "Generated Prefix Set",
        "Proximity Matrix",
        "planted positive control",
    ):
        if phrase not in text:
            raise SystemExit(f"MANIFOLD.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated manifold report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
