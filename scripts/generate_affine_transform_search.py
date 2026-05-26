#!/usr/bin/env python3
"""Search reversible affine byte remaps across held-out corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
AFFINE_JSON = DOCS / "affine_transform_search.json"
AFFINE_MD = DOCS / "AFFINE_TRANSFORM_SEARCH.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
DISCOVERY_CORPUS = "json"
DISPLAY_LIMIT = 24

AFFINE_MULTIPLIERS = (1, 3, 5, 7, 11, 17, 31, 63, 127, 255)
PHASE_MULTIPLIERS = (1, 3, 5, 17, 31, 127, 255)
PHASE_PERIODS = (2, 4, 8)
PHASE_OFFSETS = tuple(range(0, 256, 4))
PHASE_DELTAS = (1, 3, 17, 63)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
    }


def candidate_manifest() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [
        {
            "name": "identity",
            "family": "identity",
            "parameter": 0,
            "metadata_bytes": 0,
            "description": "No transform baseline.",
        }
    ]
    candidates.extend(
        {
            "name": f"affine-a{multiplier:03d}-b{offset:03d}",
            "family": "affine",
            "parameter": {"multiplier": multiplier, "offset": offset},
            "metadata_bytes": 2,
            "description": "Global reversible byte remap y=(a*x+b) mod 256.",
        }
        for multiplier in AFFINE_MULTIPLIERS
        for offset in range(256)
    )
    candidates.extend(
        {
            "name": f"phase-affine-p{period}-a{multiplier:03d}-b{offset:03d}-c{delta:03d}",
            "family": "phase-affine",
            "parameter": {
                "period": period,
                "multiplier": multiplier,
                "offset": offset,
                "phase_delta": delta,
            },
            "metadata_bytes": 4,
            "description": "Position-phased reversible byte remap y=(a*x+b+c*(i mod p)) mod 256.",
        }
        for period in PHASE_PERIODS
        for multiplier in PHASE_MULTIPLIERS
        for offset in PHASE_OFFSETS
        for delta in PHASE_DELTAS
    )
    return candidates


def candidate_manifest_hash() -> str:
    payload = json.dumps(candidate_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def mod_inverse_256(value: int) -> int:
    if value % 2 == 0:
        raise ValueError("only odd byte multipliers are invertible modulo 256")
    for candidate in range(1, 256, 2):
        if (value * candidate) & 0xFF == 1:
            return candidate
    raise ValueError(value)


def apply_candidate(data: bytes, candidate: dict[str, Any]) -> bytes:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return data
    if family == "affine":
        multiplier = int(parameter["multiplier"])
        offset = int(parameter["offset"])
        inverse = mod_inverse_256(multiplier)
        transformed = bytes(((multiplier * byte + offset) & 0xFF) for byte in data)
        restored = bytes(((inverse * ((byte - offset) & 0xFF)) & 0xFF) for byte in transformed)
        if restored != data:
            raise RuntimeError("affine transform failed reversibility")
        return transformed
    if family == "phase-affine":
        period = int(parameter["period"])
        multiplier = int(parameter["multiplier"])
        offset = int(parameter["offset"])
        phase_delta = int(parameter["phase_delta"])
        inverse = mod_inverse_256(multiplier)
        transformed = bytes(
            (
                multiplier * byte
                + offset
                + phase_delta * (idx % period)
            )
            & 0xFF
            for idx, byte in enumerate(data)
        )
        restored = bytes(
            (
                inverse
                * (
                    byte
                    - offset
                    - phase_delta * (idx % period)
                )
            )
            & 0xFF
            for idx, byte in enumerate(transformed)
        )
        if restored != data:
            raise RuntimeError("phase-affine transform failed reversibility")
        return transformed
    raise ValueError(family)


def analyze_bytes(data: bytes, prefix_sets: list[set[bytes]]) -> dict[str, Any]:
    return generate_transform_probe.analyze_bytes(data, prefix_sets)


def analyze_candidate(
    data: bytes,
    candidate: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    transformed = apply_candidate(data, candidate)
    return {
        "candidate": candidate["name"],
        "family": candidate["family"],
        "parameter": candidate["parameter"],
        "metadata_bytes": candidate["metadata_bytes"],
        "input_sha256": hashlib.sha256(transformed).hexdigest(),
        "input_bytes": len(transformed),
        **analyze_bytes(transformed, prefix_sets),
    }


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    return (
        row["exact_span_hits"],
        row["prefix_ge_6_count"],
        row["prefix_ge_5_count"],
        row["prefix_ge_4_count"],
        row["prefix_ge_3_count"],
        -row["metadata_bytes"],
        row["candidate"],
    )


def top_rows(rows: list[dict[str, Any]], limit: int = DISPLAY_LIMIT) -> list[dict[str, Any]]:
    return sorted(rows, key=row_score, reverse=True)[:limit]


def select_candidates(
    candidates: list[dict[str, Any]],
    discovery_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {candidate["name"]: candidate for candidate in candidates}
    selected_names = {"identity"}
    for key in (
        "exact_span_hits",
        "prefix_ge_6_count",
        "prefix_ge_5_count",
        "prefix_ge_4_count",
        "prefix_ge_3_count",
    ):
        selected_names.update(
            row["candidate"]
            for row in sorted(
                discovery_rows,
                key=lambda row: (
                    row[key],
                    row["exact_span_hits"],
                    row["prefix_ge_5_count"],
                    row["prefix_ge_4_count"],
                    row["prefix_ge_3_count"],
                    -row["metadata_bytes"],
                    row["candidate"],
                ),
                reverse=True,
            )[:16]
        )
    return [by_name[name] for name in sorted(selected_names)]


def discovery_search(
    candidates: list[dict[str, Any]],
    prefix_sets: list[set[bytes]],
) -> list[dict[str, Any]]:
    source = generate_corpus_matrix.corpus_bytes(DISCOVERY_CORPUS)
    rows = []
    for candidate in candidates:
        rows.append(analyze_candidate(source, candidate, prefix_sets))
    return rows


def analyze_validation_case(
    corpus: dict[str, Any],
    candidate: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    source = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    metrics = analyze_candidate(source, candidate, prefix_sets)
    return {
        "name": f"{corpus['name']}::{candidate['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "control_kind": corpus.get("control_kind", "ordinary-structured"),
        "paired_with": corpus.get("paired_with"),
        **metrics,
    }


def identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["corpus"]: row for row in rows if row["candidate"] == "identity"}


def best_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = output.get(row["corpus"])
        if current is None or row_score(row) > row_score(current):
            output[row["corpus"]] = row
    return output


def summarize(
    discovery_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    selected_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    identities = identity_by_corpus(validation_rows)
    bests = best_by_corpus(validation_rows)
    corpus_summaries = []
    heldout_prefix4_wins = 0
    heldout_prefix5_wins = 0
    heldout_exact_hits = 0
    shadow_prefix5_wins = 0
    binary_prefix5_wins = 0
    binary_exact_hits = 0
    for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        identity = identities[corpus["corpus"]]
        best = bests[corpus["corpus"]]
        prefix4_delta = best["prefix_ge_4_count"] - identity["prefix_ge_4_count"]
        prefix5_delta = best["prefix_ge_5_count"] - identity["prefix_ge_5_count"]
        exact_delta = best["exact_span_hits"] - identity["exact_span_hits"]
        kind = corpus.get("control_kind", "ordinary-structured")
        if corpus["role"] == "held-out":
            heldout_exact_hits += best["exact_span_hits"]
            if prefix4_delta > 0:
                heldout_prefix4_wins += 1
            if prefix5_delta > 0:
                heldout_prefix5_wins += 1
            if kind == "shadow-vocab" and prefix5_delta > 0:
                shadow_prefix5_wins += 1
            if kind.startswith("binary-"):
                binary_exact_hits += best["exact_span_hits"]
                if prefix5_delta > 0:
                    binary_prefix5_wins += 1
        corpus_summaries.append(
            {
                "corpus": corpus["corpus"],
                "role": corpus["role"],
                "control_kind": kind,
                "paired_with": corpus.get("paired_with"),
                "identity_prefix_ge_4": identity["prefix_ge_4_count"],
                "identity_prefix_ge_5": identity["prefix_ge_5_count"],
                "identity_exact_hits": identity["exact_span_hits"],
                "best_candidate": best["candidate"],
                "best_family": best["family"],
                "best_prefix_ge_3": best["prefix_ge_3_count"],
                "best_prefix_ge_4": best["prefix_ge_4_count"],
                "best_prefix_ge_5": best["prefix_ge_5_count"],
                "best_exact_hits": best["exact_span_hits"],
                "prefix_ge_4_delta_vs_identity": prefix4_delta,
                "prefix_ge_5_delta_vs_identity": prefix5_delta,
                "exact_delta_vs_identity": exact_delta,
            }
        )
    best_discovery = max(discovery_rows, key=row_score)
    best_validation = max(validation_rows, key=row_score)
    heldout_rows = [row for row in validation_rows if row["corpus_role"] == "held-out"]
    best_heldout = max(heldout_rows, key=row_score)
    promotion_met = heldout_prefix5_wins > 0 or heldout_exact_hits > 0
    return {
        "searched_candidate_count": len(discovery_rows),
        "selected_candidate_count": len(selected_candidates),
        "validation_rows": len(validation_rows),
        "heldout_prefix4_win_corpora": heldout_prefix4_wins,
        "heldout_prefix5_win_corpora": heldout_prefix5_wins,
        "heldout_exact_hits": heldout_exact_hits,
        "shadow_prefix5_win_corpora": shadow_prefix5_wins,
        "binary_prefix5_win_corpora": binary_prefix5_wins,
        "binary_exact_hits": binary_exact_hits,
        "best_discovery_case": best_discovery["candidate"],
        "best_discovery_prefix_ge_5": best_discovery["prefix_ge_5_count"],
        "best_discovery_exact_hits": best_discovery["exact_span_hits"],
        "best_validation_case": best_validation["name"],
        "best_validation_prefix_ge_5": best_validation["prefix_ge_5_count"],
        "best_validation_exact_hits": best_validation["exact_span_hits"],
        "best_heldout_case": best_heldout["name"],
        "best_heldout_prefix_ge_5": best_heldout["prefix_ge_5_count"],
        "best_heldout_exact_hits": best_heldout["exact_span_hits"],
        "promotion_met": promotion_met,
        "stop_rule_triggered": heldout_prefix4_wins == 0,
        "conclusion": (
            "Affine remap search produced a held-out prefix >=5 or exact-hit promotion signal."
            if promotion_met
            else "Affine remap search did not produce held-out prefix >=5 uplift or exact seed-span hits."
        ),
        "corpus_summaries": corpus_summaries,
    }


def build_report() -> dict[str, Any]:
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    candidates = candidate_manifest()
    discovery_rows = discovery_search(candidates, prefix_sets)
    selected_candidates = select_candidates(candidates, discovery_rows)
    validation_rows = [
        analyze_validation_case(corpus, candidate, prefix_sets)
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
        for candidate in selected_candidates
    ]
    return {
        "generated_by": "scripts/generate_affine_transform_search.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "candidate_manifest_sha256": candidate_manifest_hash(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "discovery_corpus": DISCOVERY_CORPUS,
        "candidates": candidates,
        "selected_candidates": selected_candidates,
        "discovery_top_rows": top_rows(discovery_rows),
        "validation_results": validation_rows,
        "summary": summarize(discovery_rows, validation_rows, selected_candidates),
    }


def write_report(payload: dict[str, Any]) -> None:
    AFFINE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Affine Transform Search",
        "",
        "Generated by `scripts/generate_affine_transform_search.py`.",
        "This is a reversible affine byte-remap search over discovery and held-out corpora; it is not `.tlmr` format support.",
        "",
        f"Searched candidates: `{summary['searched_candidate_count']}`.",
        f"Selected validation candidates: `{summary['selected_candidate_count']}`.",
        f"Validation rows: `{summary['validation_rows']}`.",
        f"Held-out prefix >=4 win corpora: `{summary['heldout_prefix4_win_corpora']}`.",
        f"Held-out prefix >=5 win corpora: `{summary['heldout_prefix5_win_corpora']}`.",
        f"Held-out exact hits: `{summary['heldout_exact_hits']}`.",
        f"Vocabulary-disjoint shadow prefix >=5 win corpora: `{summary['shadow_prefix5_win_corpora']}`.",
        f"Binary TLV/varint prefix >=5 win corpora: `{summary['binary_prefix5_win_corpora']}`.",
        f"Binary exact hits: `{summary['binary_exact_hits']}`.",
        f"Promotion met: `{summary['promotion_met']}`.",
        f"Stop rule triggered: `{summary['stop_rule_triggered']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best discovery candidate: `{summary['best_discovery_case']}` with prefix>=5 `{summary['best_discovery_prefix_ge_5']}` and exact hits `{summary['best_discovery_exact_hits']}`.",
        f"Best held-out case: `{summary['best_heldout_case']}` with prefix>=5 `{summary['best_heldout_prefix_ge_5']}` and exact hits `{summary['best_heldout_exact_hits']}`.",
        "",
        "## Corpus Summary",
        "",
        "| corpus | role | kind | best candidate | identity p4 | best p4 | best p5 | p4 delta | p5 delta | exact hits |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["corpus_summaries"]:
        lines.append(
            "| {corpus} | {role} | {control_kind} | {best_candidate} | "
            "{identity_prefix_ge_4} | {best_prefix_ge_4} | {best_prefix_ge_5} | "
            "{prefix_ge_4_delta_vs_identity:+} | {prefix_ge_5_delta_vs_identity:+} | "
            "{best_exact_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Discovery Leads",
            "",
            "| candidate | family | metadata bytes | p3 | p4 | p5 | p6 | exact |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["discovery_top_rows"]:
        lines.append(
            "| {candidate} | {family} | {metadata_bytes} | {prefix_ge_3_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_span_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Promotion requires held-out prefix >=5 uplift or exact 8-byte seed-span hits.",
            "- Affine byte remaps are reversible with small metadata, so they are a plausible preconditioner family but not current format support.",
            "- Vocabulary-disjoint and binary TLV/varint controls are included so alphabet remaps do not masquerade as semantic compression.",
            "- If held-out prefix >=4 uplift does not repeat, this family should be treated as a null result and not escalated to depth-3 search.",
        ]
    )
    AFFINE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not AFFINE_JSON.exists() or not AFFINE_MD.exists():
        raise SystemExit("generated affine transform search files are missing")
    payload = load_json(AFFINE_JSON)
    if payload.get("generated_by") != "scripts/generate_affine_transform_search.py":
        raise SystemExit("affine_transform_search.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("affine_transform_search.json artifact hashes are stale")
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash():
        raise SystemExit("affine_transform_search.json candidate manifest hash is stale")
    if len(payload.get("candidates", [])) != len(candidate_manifest()):
        raise SystemExit("affine_transform_search.json candidate count is stale")
    selected_count = len(payload.get("selected_candidates", []))
    expected_rows = selected_count * len(generate_transform_validation.CORPUS_VALIDATION_MATRIX)
    if len(payload.get("validation_results", [])) != expected_rows:
        raise SystemExit("affine_transform_search.json validation row count is stale")
    text = AFFINE_MD.read_text(encoding="utf-8")
    for phrase in (
        "Affine Transform Search",
        "reversible affine byte-remap search",
        "Promotion requires held-out prefix >=5 uplift",
        "Vocabulary-disjoint",
        "binary TLV/varint",
        "not current format support",
    ):
        if phrase not in text:
            raise SystemExit(f"AFFINE_TRANSFORM_SEARCH.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated affine search")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
