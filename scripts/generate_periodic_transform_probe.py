#!/usr/bin/env python3
"""Probe bounded periodic reversible transforms for Telomere prefix ladders."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_transform_probe


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PROBE_JSON = DOCS / "periodic_transform_probe.json"
PROBE_MD = DOCS / "PERIODIC_TRANSFORM_PROBE.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
DISCOVERY_CORPUS = {"name": "json-discovery", "corpus": "json", "role": "discovery"}
HELDOUT_CORPORA = [
    {"name": "markdown-heldout", "corpus": "markdown", "role": "held-out"},
    {"name": "csv-heldout", "corpus": "csv", "role": "held-out"},
    {"name": "rust-like-heldout", "corpus": "rust-like", "role": "held-out"},
    {"name": "html-heldout", "corpus": "html", "role": "held-out"},
    {"name": "python-like-heldout", "corpus": "python-like", "role": "held-out"},
    {"name": "sql-heldout", "corpus": "sql", "role": "held-out"},
    {"name": "toml-heldout", "corpus": "toml", "role": "held-out"},
    {"name": "xml-heldout", "corpus": "xml", "role": "held-out"},
    {"name": "log-heldout", "corpus": "log", "role": "held-out"},
    {"name": "yaml-heldout", "corpus": "yaml", "role": "held-out"},
    {"name": "css-heldout", "corpus": "css", "role": "held-out"},
    {"name": "javascript-like-heldout", "corpus": "javascript-like", "role": "held-out"},
    {"name": "graphql-heldout", "corpus": "graphql", "role": "held-out"},
    {"name": "nginx-conf-heldout", "corpus": "nginx-conf", "role": "held-out"},
]
VALIDATION_CORPORA = [DISCOVERY_CORPUS, *HELDOUT_CORPORA]

# Constants are the existing transform leads plus neutral/checkerboard masks.
MASK_CONSTANTS = (0, 85, 151, 170, 205, 213, 232, 255)
PERIODS = (2, 4)
DISCOVERY_LEAD_LIMIT = 24


def candidate_manifest() -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = [
        {
            "name": "identity",
            "family": "identity",
            "period": 1,
            "mask": [0],
            "metadata_bytes": 0,
            "description": "No transform.",
        }
    ]
    for family in ("xor-periodic", "add-periodic"):
        for period in PERIODS:
            for mask in itertools.product(MASK_CONSTANTS, repeat=period):
                mask_hex = "".join(f"{byte:02x}" for byte in mask)
                manifest.append(
                    {
                        "name": f"{family}-p{period}-{mask_hex}",
                        "family": family,
                        "period": period,
                        "mask": list(mask),
                        "metadata_bytes": period + 1,
                        "description": (
                            "Reversible byte-position periodic mask. "
                            "XOR masks invert by XOR; add masks invert by subtraction modulo 256."
                        ),
                    }
                )
    return manifest


def candidate_manifest_hash() -> str:
    payload = json.dumps(candidate_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def apply_candidate(data: bytes, candidate: dict[str, Any]) -> bytes:
    family = candidate["family"]
    if family == "identity":
        return data
    mask = candidate["mask"]
    period = int(candidate["period"])
    out = bytearray(len(data))
    if family == "xor-periodic":
        for idx, byte in enumerate(data):
            out[idx] = byte ^ mask[idx % period]
        return bytes(out)
    if family == "add-periodic":
        for idx, byte in enumerate(data):
            out[idx] = (byte + mask[idx % period]) & 0xFF
        return bytes(out)
    raise ValueError(family)


def analyze_candidate(
    corpus: dict[str, Any],
    candidate: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    source = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    transformed = apply_candidate(source, candidate)
    metrics = generate_transform_probe.analyze_bytes(transformed, prefix_sets)
    return {
        "name": f"{corpus['name']}::{candidate['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "transform": candidate["name"],
        "transform_family": candidate["family"],
        "period": candidate["period"],
        "mask_hex": "".join(f"{byte:02x}" for byte in candidate["mask"]),
        "metadata_bytes": candidate["metadata_bytes"],
        "input_sha256": hashlib.sha256(transformed).hexdigest(),
        "input_bytes": len(transformed),
        **metrics,
    }


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    return (
        row["exact_span_hits"],
        row["prefix_ge_6_count"],
        row["prefix_ge_5_count"],
        row["prefix_ge_4_count"],
        row["prefix_ge_3_count"],
        -row["metadata_bytes"],
        row["transform"],
    )


def select_discovery_leads(rows: list[dict[str, Any]]) -> list[str]:
    identity = "identity"
    ranked = sorted(
        [row for row in rows if row["transform"] != identity],
        key=row_score,
        reverse=True,
    )
    selected = [identity]
    for row in ranked:
        if row["transform"] not in selected:
            selected.append(row["transform"])
        if len(selected) >= DISCOVERY_LEAD_LIMIT + 1:
            break
    return selected


def identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["corpus"]: row for row in rows if row["transform"] == "identity"}


def best_non_identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["transform"] == "identity":
            continue
        current = best.get(row["corpus"])
        if current is None or row_score(row) > row_score(current):
            best[row["corpus"]] = row
    return best


def summarize(validation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    identity_rows = identity_by_corpus(validation_rows)
    best_rows = best_non_identity_by_corpus(validation_rows)
    corpus_summaries = []
    heldout_prefix4_wins = 0
    heldout_prefix5_wins = 0
    heldout_exact_hits = 0
    for corpus in VALIDATION_CORPORA:
        identity = identity_rows[corpus["corpus"]]
        best = best_rows[corpus["corpus"]]
        prefix4_delta = best["prefix_ge_4_count"] - identity["prefix_ge_4_count"]
        prefix5_delta = best["prefix_ge_5_count"] - identity["prefix_ge_5_count"]
        exact_delta = best["exact_span_hits"] - identity["exact_span_hits"]
        if corpus["role"] == "held-out":
            heldout_exact_hits += best["exact_span_hits"]
            if prefix4_delta > 0:
                heldout_prefix4_wins += 1
            if prefix5_delta > 0:
                heldout_prefix5_wins += 1
        corpus_summaries.append(
            {
                "corpus": corpus["corpus"],
                "role": corpus["role"],
                "identity_prefix_ge_4": identity["prefix_ge_4_count"],
                "identity_prefix_ge_5": identity["prefix_ge_5_count"],
                "identity_exact_hits": identity["exact_span_hits"],
                "best_transform": best["transform"],
                "best_prefix_ge_3": best["prefix_ge_3_count"],
                "best_prefix_ge_4": best["prefix_ge_4_count"],
                "best_prefix_ge_5": best["prefix_ge_5_count"],
                "best_prefix_ge_6": best["prefix_ge_6_count"],
                "best_exact_hits": best["exact_span_hits"],
                "prefix_ge_4_delta_vs_identity": prefix4_delta,
                "prefix_ge_5_delta_vs_identity": prefix5_delta,
                "exact_delta_vs_identity": exact_delta,
            }
        )
    conclusion = (
        "Bounded periodic masks did not promote held-out near misses to prefix >=5 "
        "or exact 8-byte seed-span hits."
        if heldout_prefix5_wins == 0 and heldout_exact_hits == 0
        else "A bounded periodic mask produced a longer-prefix held-out lead that deserves follow-up."
    )
    return {
        "corpus_summaries": corpus_summaries,
        "heldout_prefix4_win_corpora": heldout_prefix4_wins,
        "heldout_prefix5_win_corpora": heldout_prefix5_wins,
        "heldout_exact_hits": heldout_exact_hits,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    candidates = candidate_manifest()
    candidates_by_name = {candidate["name"]: candidate for candidate in candidates}
    discovery_rows = [
        analyze_candidate(DISCOVERY_CORPUS, candidate, prefix_sets)
        for candidate in candidates
    ]
    selected_names = select_discovery_leads(discovery_rows)
    validation_rows = [
        analyze_candidate(corpus, candidates_by_name[name], prefix_sets)
        for corpus in VALIDATION_CORPORA
        for name in selected_names
    ]
    selected_discovery_rows = [
        row for row in discovery_rows if row["transform"] in selected_names
    ]
    return {
        "generated_by": "scripts/generate_periodic_transform_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "candidate_manifest_sha256": candidate_manifest_hash(),
        "candidate_count": len(candidates),
        "selected_discovery_limit": DISCOVERY_LEAD_LIMIT,
        "selected_transform_names": selected_names,
        "selected_transform_count": len(selected_names),
        "discovery_corpus": DISCOVERY_CORPUS,
        "validation_corpora": VALIDATION_CORPORA,
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_count": generate_manifold_report.seed_count(MAX_SEED_LEN),
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "mask_constants": list(MASK_CONSTANTS),
        "periods": list(PERIODS),
        "discovery_results": selected_discovery_rows,
        "validation_results": validation_rows,
        "summary": summarize(validation_rows),
    }


def compact_discovery_row(row: dict[str, Any]) -> str:
    return (
        "| {transform} | {metadata_bytes} | {prefix_ge_3_count} | {prefix_ge_4_count} | "
        "{prefix_ge_5_count} | {prefix_ge_6_count} | {exact_span_hits} |".format(**row)
    )


def write_report(payload: dict[str, Any]) -> None:
    PROBE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Periodic Transform Probe",
        "",
        "Generated by `scripts/generate_periodic_transform_probe.py`.",
        "This is a bounded reversible-transform research probe, not format support and not a compression claim.",
        "",
        f"Candidate count: `{payload['candidate_count']}`.",
        f"Selected discovery leads: `{payload['selected_transform_count']}`.",
        f"Hasher: `{payload['hasher']}`.",
        f"Max seed len: `{payload['max_seed_len']}`.",
        f"Span len: `{payload['span_len']}`.",
        f"Mask constants: `{payload['mask_constants']}`.",
        f"Periods: `{payload['periods']}`.",
        "",
        "## Summary",
        "",
        payload["summary"]["conclusion"],
        f"Held-out corpora with prefix >=4 uplift: `{payload['summary']['heldout_prefix4_win_corpora']}`.",
        f"Held-out corpora with prefix >=5 uplift: `{payload['summary']['heldout_prefix5_win_corpora']}`.",
        f"Held-out exact hits: `{payload['summary']['heldout_exact_hits']}`.",
        "",
        "## Discovery Leads",
        "",
        "| transform | metadata bytes | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(payload["discovery_results"], key=row_score, reverse=True):
        lines.append(compact_discovery_row(row))

    lines.extend(
        [
            "",
            "## Corpus Summary",
            "",
            "| corpus | role | identity prefix >=5 | best transform | best prefix >=3 | best prefix >=4 | best prefix >=5 | prefix >=5 delta | best exact hits |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["summary"]["corpus_summaries"]:
        lines.append(
            "| {corpus} | {role} | {identity_prefix_ge_5} | {best_transform} | "
            "{best_prefix_ge_3} | {best_prefix_ge_4} | {best_prefix_ge_5} | "
            "{prefix_ge_5_delta_vs_identity:+} | {best_exact_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Validation Matrix",
            "",
            "| case | role | transform | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["validation_results"]:
        lines.append(
            "| {corpus} | {corpus_role} | {transform} | {prefix_ge_3_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_span_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Periodic XOR/add masks are reversible with small metadata, so they are a reasonable transform-search lane.",
            "- Discovery leads are selected on JSON only; held-out rows are the real promotion gate.",
            "- Prefix >=5 uplift or exact hits would justify deeper seed/depth work; prefix <=4 alone does not.",
            "- This artifact must remain outside `.tlmr` format support until a repeatable exact seed-span win appears.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated periodic transform probe files are missing")
    payload = json.loads(PROBE_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_periodic_transform_probe.py":
        raise SystemExit("periodic_transform_probe.json has wrong generated_by marker")
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash():
        raise SystemExit("periodic_transform_probe.json candidate manifest hash is stale")
    if payload.get("candidate_count") != len(candidate_manifest()):
        raise SystemExit("periodic_transform_probe.json candidate count is stale")
    expected_rows = len(VALIDATION_CORPORA) * payload.get("selected_transform_count", 0)
    if len(payload.get("validation_results", [])) != expected_rows:
        raise SystemExit("periodic_transform_probe.json does not contain the full validation matrix")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "bounded reversible-transform research probe",
        "Discovery Leads",
        "Held-out corpora with prefix >=5 uplift",
        "not format support",
    ):
        if phrase not in text:
            raise SystemExit(f"PERIODIC_TRANSFORM_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated periodic transform probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
