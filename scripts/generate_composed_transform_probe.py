#!/usr/bin/env python3
"""Probe composed context and periodic reversible transforms."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_periodic_transform_probe
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PERIODIC_PROBE_JSON = DOCS / "periodic_transform_probe.json"
TRANSFORM_VALIDATION_JSON = DOCS / "transform_validation.json"
PROBE_JSON = DOCS / "composed_transform_probe.json"
PROBE_MD = DOCS / "COMPOSED_TRANSFORM_PROBE.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
DISCOVERY_CORPUS = generate_periodic_transform_probe.DISCOVERY_CORPUS
VALIDATION_CORPORA = generate_periodic_transform_probe.VALIDATION_CORPORA
DISCOVERY_LEAD_LIMIT = 32
IDENTITY_COMPOSED_NAME = "identity__identity"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_manifest() -> list[dict[str, Any]]:
    return [dict(transform) for transform in generate_transform_validation.TRANSFORM_VALIDATION_MATRIX]


def selected_periodic_manifest() -> list[dict[str, Any]]:
    periodic_payload = load_json(PERIODIC_PROBE_JSON)
    periodic_by_name = {
        candidate["name"]: candidate
        for candidate in generate_periodic_transform_probe.candidate_manifest()
    }
    selected: list[dict[str, Any]] = []
    for name in periodic_payload["selected_transform_names"]:
        if name not in periodic_by_name:
            raise RuntimeError(f"periodic transform {name} is not in the candidate manifest")
        selected.append(dict(periodic_by_name[name]))
    return selected


def candidate_manifest() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for base in base_manifest():
        for periodic in selected_periodic_manifest():
            candidates.append(
                {
                    "name": f"{base['name']}__{periodic['name']}",
                    "base_transform": base,
                    "periodic_transform": periodic,
                    "metadata_bytes": base["metadata_bytes"] + periodic["metadata_bytes"],
                    "description": (
                        "Apply a context/residual transform first, then a selected "
                        "periodic reversible mask."
                    ),
                }
            )
    return candidates


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def candidate_manifest_hash() -> str:
    return canonical_hash(candidate_manifest())


def base_manifest_hash() -> str:
    return canonical_hash(base_manifest())


def selected_periodic_manifest_hash() -> str:
    return canonical_hash(selected_periodic_manifest())


def source_hashes() -> dict[str, str]:
    return {
        "periodic_transform_probe_sha256": sha256(PERIODIC_PROBE_JSON),
        "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_JSON),
    }


def apply_composed(data: bytes, candidate: dict[str, Any]) -> bytes:
    base_probe = generate_transform_validation.probe_from_validation_transform(
        candidate["base_transform"]
    )
    base_data = generate_transform_probe.apply_probe(data, base_probe)
    return generate_periodic_transform_probe.apply_candidate(
        base_data,
        candidate["periodic_transform"],
    )


def analyze_candidate(
    corpus: dict[str, Any],
    candidate: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    source = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    transformed = apply_composed(source, candidate)
    metrics = generate_transform_probe.analyze_bytes(transformed, prefix_sets)
    base = candidate["base_transform"]
    periodic = candidate["periodic_transform"]
    return {
        "name": f"{corpus['name']}::{candidate['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "transform": candidate["name"],
        "base_transform": base["name"],
        "base_family": base["family"],
        "base_parameter": base["parameter"],
        "periodic_transform": periodic["name"],
        "periodic_family": periodic["family"],
        "periodic_period": periodic["period"],
        "periodic_mask_hex": "".join(f"{byte:02x}" for byte in periodic["mask"]),
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
    selected = [IDENTITY_COMPOSED_NAME]
    ranked = sorted(
        [row for row in rows if row["transform"] != IDENTITY_COMPOSED_NAME],
        key=row_score,
        reverse=True,
    )
    for row in ranked:
        if row["transform"] not in selected:
            selected.append(row["transform"])
        if len(selected) >= DISCOVERY_LEAD_LIMIT + 1:
            break
    return selected


def identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["corpus"]: row for row in rows if row["transform"] == IDENTITY_COMPOSED_NAME}


def best_non_identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["transform"] == IDENTITY_COMPOSED_NAME:
            continue
        current = best.get(row["corpus"])
        if current is None or row_score(row) > row_score(current):
            best[row["corpus"]] = row
    return best


def best_by_metric(rows: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: (row[metric], row_score(row)))


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
                "best_base_transform": best["base_transform"],
                "best_periodic_transform": best["periodic_transform"],
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
    heldout_rows = [row for row in validation_rows if row["corpus_role"] == "held-out"]
    best_prefix4 = best_by_metric(heldout_rows, "prefix_ge_4_count")
    best_prefix5 = best_by_metric(heldout_rows, "prefix_ge_5_count")
    best_exact = best_by_metric(heldout_rows, "exact_span_hits")
    conclusion = (
        "Composed context+periodic transforms did not promote held-out near misses "
        "to prefix >=5 or exact 8-byte seed-span hits."
        if heldout_prefix5_wins == 0 and heldout_exact_hits == 0
        else "A composed context+periodic transform produced a longer-prefix held-out lead that deserves follow-up."
    )
    return {
        "corpus_summaries": corpus_summaries,
        "heldout_prefix4_win_corpora": heldout_prefix4_wins,
        "heldout_prefix5_win_corpora": heldout_prefix5_wins,
        "heldout_exact_hits": heldout_exact_hits,
        "best_heldout_prefix4_case": best_prefix4["name"] if best_prefix4 else None,
        "best_heldout_prefix4_count": best_prefix4["prefix_ge_4_count"] if best_prefix4 else 0,
        "best_heldout_prefix5_case": best_prefix5["name"] if best_prefix5 else None,
        "best_heldout_prefix5_count": best_prefix5["prefix_ge_5_count"] if best_prefix5 else 0,
        "best_heldout_exact_case": best_exact["name"] if best_exact else None,
        "best_heldout_exact_hits": best_exact["exact_span_hits"] if best_exact else 0,
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
        "generated_by": "scripts/generate_composed_transform_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "candidate_manifest_sha256": candidate_manifest_hash(),
        "base_manifest_sha256": base_manifest_hash(),
        "selected_periodic_manifest_sha256": selected_periodic_manifest_hash(),
        "source_hashes": source_hashes(),
        "candidate_count": len(candidates),
        "base_transform_count": len(base_manifest()),
        "selected_periodic_transform_count": len(selected_periodic_manifest()),
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
        "discovery_results": selected_discovery_rows,
        "validation_results": validation_rows,
        "summary": summarize(validation_rows),
    }


def compact_discovery_row(row: dict[str, Any]) -> str:
    return (
        "| {transform} | {metadata_bytes} | {prefix_ge_3_count} | "
        "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
        "{exact_span_hits} |".format(**row)
    )


def write_report(payload: dict[str, Any]) -> None:
    PROBE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Composed Transform Probe",
        "",
        "Generated by `scripts/generate_composed_transform_probe.py`.",
        "This is a composed context+periodic reversible-transform research probe, not `.tlmr` format support and not a compression claim.",
        "",
        f"Candidate count: `{payload['candidate_count']}`.",
        f"Base transforms: `{payload['base_transform_count']}`.",
        f"Selected periodic transforms: `{payload['selected_periodic_transform_count']}`.",
        f"Selected discovery leads: `{payload['selected_transform_count']}`.",
        f"Hasher: `{payload['hasher']}`.",
        f"Max seed len: `{payload['max_seed_len']}`.",
        f"Span len: `{payload['span_len']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Held-out corpora with prefix >=4 uplift: `{summary['heldout_prefix4_win_corpora']}`.",
        f"Held-out corpora with prefix >=5 uplift: `{summary['heldout_prefix5_win_corpora']}`.",
        f"Held-out exact hits: `{summary['heldout_exact_hits']}`.",
        f"Best held-out prefix >=4 case: `{summary['best_heldout_prefix4_case']}` with `{summary['best_heldout_prefix4_count']}` spans.",
        f"Best held-out prefix >=5 case: `{summary['best_heldout_prefix5_case']}` with `{summary['best_heldout_prefix5_count']}` spans.",
        f"Best held-out exact case: `{summary['best_heldout_exact_case']}` with `{summary['best_heldout_exact_hits']}` hits.",
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
            "| corpus | role | identity prefix >=5 | best base | best periodic | best prefix >=3 | best prefix >=4 | best prefix >=5 | prefix >=5 delta | best exact hits |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["corpus_summaries"]:
        lines.append(
            "| {corpus} | {role} | {identity_prefix_ge_5} | {best_base_transform} | "
            "{best_periodic_transform} | {best_prefix_ge_3} | {best_prefix_ge_4} | "
            "{best_prefix_ge_5} | {prefix_ge_5_delta_vs_identity:+} | {best_exact_hits} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Validation Matrix",
            "",
            "| case | role | base | periodic | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["validation_results"]:
        lines.append(
            "| {corpus} | {corpus_role} | {base_transform} | {periodic_transform} | "
            "{prefix_ge_3_count} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_span_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Composing context/residual transforms with periodic masks is the next bounded search lane after testing each family alone.",
            "- Discovery leads are selected on JSON only; held-out rows are the promotion gate.",
            "- Prefix >=5 uplift or exact hits would justify deeper seed/depth work; prefix <=4 alone does not.",
            "- This artifact must remain outside `.tlmr` format support until a repeatable exact seed-span win appears.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated composed transform probe files are missing")
    payload = load_json(PROBE_JSON)
    if payload.get("generated_by") != "scripts/generate_composed_transform_probe.py":
        raise SystemExit("composed_transform_probe.json has wrong generated_by marker")
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash():
        raise SystemExit("composed_transform_probe.json candidate manifest hash is stale")
    if payload.get("base_manifest_sha256") != base_manifest_hash():
        raise SystemExit("composed_transform_probe.json base manifest hash is stale")
    if payload.get("selected_periodic_manifest_sha256") != selected_periodic_manifest_hash():
        raise SystemExit("composed_transform_probe.json selected periodic manifest hash is stale")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("composed_transform_probe.json source hashes are stale")
    if payload.get("candidate_count") != len(candidate_manifest()):
        raise SystemExit("composed_transform_probe.json candidate count is stale")
    expected_rows = len(VALIDATION_CORPORA) * payload.get("selected_transform_count", 0)
    if len(payload.get("validation_results", [])) != expected_rows:
        raise SystemExit("composed_transform_probe.json does not contain the full validation matrix")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "composed context+periodic",
        "Held-out corpora with prefix >=5 uplift",
        "Held-out exact hits",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"COMPOSED_TRANSFORM_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated composed transform probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
