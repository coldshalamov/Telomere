#!/usr/bin/env python3
"""Probe context-conditioned fifth-byte steering masks on held-out corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_fifth_byte_residual
import generate_fifth_byte_steering
import generate_manifold_report
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESIDUAL_JSON = DOCS / "fifth_byte_residual.json"
CONTEXTUAL_JSON = DOCS / "contextual_fifth_byte_steering.json"
CONTEXTUAL_MD = DOCS / "CONTEXTUAL_FIFTH_BYTE_STEERING.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
DISPLAY_LIMIT = 24
SOURCE_ROW_LIMIT = 4
CONTEXT_SCHEMES = (
    {"name": "prev-class-p4", "period": 4, "kind": "prev-class", "class_count": 9},
    {"name": "prev-class-p8", "period": 8, "kind": "prev-class", "class_count": 9},
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:96]


def byte_class(value: int | None) -> str:
    if value is None:
        return "start"
    if value in (9, 10, 13, 32):
        return "ws"
    if 48 <= value <= 57:
        return "digit"
    if 65 <= value <= 90 or 97 <= value <= 122:
        return "alpha"
    if value in (34, 39, 96):
        return "quote"
    if value in b"{}[]()<>=:/,.;_-":
        return "delim"
    if value in b"#$@!&|+*?%\\":
        return "symbol"
    if value >= 128:
        return "high"
    return "other"


def context_key_from_prev(prev: int | None, idx: int, scheme: dict[str, Any]) -> str:
    period = int(scheme["period"])
    phase = idx % period
    kind = scheme["kind"]
    if kind == "prev-class":
        suffix = byte_class(prev)
    elif kind == "prev-low-nibble":
        suffix = "start" if prev is None else f"{prev & 0x0F:x}"
    elif kind == "prev-high-nibble":
        suffix = "start" if prev is None else f"{prev >> 4:x}"
    else:
        raise ValueError(kind)
    return f"{phase}:{suffix}"


def context_key(data: bytes, idx: int, scheme: dict[str, Any]) -> str:
    prev = data[idx - 1] if idx > 0 else None
    return context_key_from_prev(prev, idx, scheme)


def context_key_space(scheme: dict[str, Any]) -> list[str]:
    kind = scheme["kind"]
    period = int(scheme["period"])
    if kind == "prev-class":
        labels = ("start", "ws", "digit", "alpha", "quote", "delim", "symbol", "high", "other")
    elif kind in {"prev-low-nibble", "prev-high-nibble"}:
        labels = ("start", *[f"{value:x}" for value in range(16)])
    else:
        raise ValueError(kind)
    return [f"{phase}:{label}" for phase in range(period) for label in labels]


def supported_source(row: dict[str, Any]) -> bool:
    return row["family"] in {
        "transform-validation",
        "periodic-transform-probe",
        "composed-transform-probe",
    }


def source_rows(residual: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    seen_inputs: set[str] = set()
    for row in residual["results"]:
        if not supported_source(row):
            continue
        if row["prefix4_events"] < residual["robust_min_prefix4_events"]:
            continue
        if row["distinct_target_fifths"] < residual["robust_min_target_fifths"]:
            continue
        input_sha256 = row.get("input_sha256", row["name"])
        if input_sha256 in seen_inputs:
            continue
        seen_inputs.add(input_sha256)
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            row["prefix4_events"],
            row["distinct_target_fifths"],
            row["name"],
        ),
        reverse=True,
    )[:SOURCE_ROW_LIMIT]


def source_manifest() -> list[dict[str, Any]]:
    residual = load_json(RESIDUAL_JSON)
    fields = (
        "name",
        "family",
        "corpus",
        "role",
        "transform",
        "prefix4_events",
        "distinct_target_fifths",
    )
    return [{field: row[field] for field in fields} for row in source_rows(residual)]


def source_manifest_hash() -> str:
    payload = json.dumps(source_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def base_metadata_bytes(row: dict[str, Any]) -> int:
    return generate_fifth_byte_steering.base_metadata_bytes(row)


def seed_fifth_byte_map() -> tuple[dict[bytes, Counter[int]], set[bytes]]:
    return generate_fifth_byte_residual.seed_fifth_byte_map(MAX_SEED_LEN)


def residual_counters_by_context(
    row: dict[str, Any],
    scheme: dict[str, Any],
    operation: str,
    prefix4_to_fifth: dict[bytes, Counter[int]],
    prefix5_set: set[bytes],
) -> dict[str, Counter[int]]:
    data = generate_fifth_byte_residual.transformed_bytes_for_row(row)
    counters: dict[str, Counter[int]] = defaultdict(Counter)
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        expected_counter = prefix4_to_fifth.get(span[:4])
        if expected_counter is None or span[:5] in prefix5_set:
            continue
        idx = start + 4
        key = context_key(data, idx, scheme)
        target_fifth = span[4]
        for expected_fifth, weight in expected_counter.items():
            if operation == "xor-context":
                residual = target_fifth ^ expected_fifth
            elif operation == "add-context":
                residual = (expected_fifth - target_fifth) & 0xFF
            else:
                raise ValueError(operation)
            counters[key][residual] += weight
    return counters


def learned_mask(counters: dict[str, Counter[int]], scheme: dict[str, Any]) -> dict[str, int]:
    mask: dict[str, int] = {}
    for key in context_key_space(scheme):
        counter = counters.get(key)
        if not counter:
            mask[key] = 0
            continue
        mask[key] = int(counter.most_common(1)[0][0]) & 0xFF
    return mask


def mask_hex(mask: dict[str, int], scheme: dict[str, Any]) -> str:
    return "".join(f"{mask[key]:02x}" for key in context_key_space(scheme))


def permutation_mask(mask: dict[str, int], scheme: dict[str, Any]) -> dict[str, int]:
    keys = context_key_space(scheme)
    values = [mask[key] for key in keys]
    if not values:
        return {}
    # Deterministic same-shape null: rotate learned values out of their contexts.
    offset = max(1, len(values) // 3)
    rotated = values[offset:] + values[:offset]
    return dict(zip(keys, rotated))


def candidate_manifest(residual: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    residual = residual or load_json(RESIDUAL_JSON)
    prefix4_to_fifth, prefix5_set = seed_fifth_byte_map()
    candidates: list[dict[str, Any]] = []
    for row in source_rows(residual):
        for scheme in CONTEXT_SCHEMES:
            for operation in ("xor-context", "add-context"):
                counters = residual_counters_by_context(
                    row,
                    scheme,
                    operation,
                    prefix4_to_fifth,
                    prefix5_set,
                )
                mask = learned_mask(counters, scheme)
                if not any(mask.values()):
                    continue
                candidates.append(
                    {
                        "name": (
                            f"{operation}-{scheme['name']}-{slug(row['name'])}-"
                            f"{hashlib.sha256(mask_hex(mask, scheme).encode('ascii')).hexdigest()[:12]}"
                        ),
                        "operation": operation,
                        "context_scheme": scheme["name"],
                        "context_kind": scheme["kind"],
                        "period": scheme["period"],
                        "mask": mask,
                        "mask_hex_sha256": hashlib.sha256(
                            mask_hex(mask, scheme).encode("ascii")
                        ).hexdigest(),
                        "source_case": row["name"],
                        "source_family": row["family"],
                        "source_corpus": row["corpus"],
                        "source_role": row["role"],
                        "source_transform": row["transform"],
                        "source_prefix4_events": row["prefix4_events"],
                        "source_distinct_target_fifths": row["distinct_target_fifths"],
                        "base_metadata_bytes": base_metadata_bytes(row),
                        "correction_metadata_bytes": len(context_key_space(scheme)) + 2,
                        "metadata_bytes": base_metadata_bytes(row)
                        + len(context_key_space(scheme))
                        + 2,
                    }
                )
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        unique.setdefault(candidate["name"], candidate)
    return sorted(unique.values(), key=lambda item: item["name"])


def candidate_manifest_hash(candidates: list[dict[str, Any]] | None = None) -> str:
    candidates = candidates or candidate_manifest()
    payload = json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def apply_base(data: bytes, candidate: dict[str, Any]) -> bytes:
    return generate_fifth_byte_steering.apply_base(data, candidate)


def candidate_scheme(candidate: dict[str, Any]) -> dict[str, Any]:
    for scheme in CONTEXT_SCHEMES:
        if scheme["name"] == candidate["context_scheme"]:
            return scheme
    raise ValueError(candidate["context_scheme"])


def apply_contextual(data: bytes, candidate: dict[str, Any]) -> bytes:
    scheme = candidate_scheme(candidate)
    mask = candidate["mask"]
    out = bytearray(len(data))
    for idx, byte in enumerate(data):
        key = context_key(data, idx, scheme)
        value = int(mask.get(key, 0)) & 0xFF
        if candidate["operation"] == "xor-context":
            out[idx] = byte ^ value
        elif candidate["operation"] == "add-context":
            out[idx] = (byte + value) & 0xFF
        else:
            raise ValueError(candidate["operation"])
    return bytes(out)


def invert_contextual(data: bytes, candidate: dict[str, Any]) -> bytes:
    scheme = candidate_scheme(candidate)
    mask = candidate["mask"]
    out = bytearray(len(data))
    for idx, byte in enumerate(data):
        prev = out[idx - 1] if idx > 0 else None
        key = context_key_from_prev(prev, idx, scheme)
        value = int(mask.get(key, 0)) & 0xFF
        if candidate["operation"] == "xor-context":
            out[idx] = byte ^ value
        elif candidate["operation"] == "add-context":
            out[idx] = (byte - value) & 0xFF
        else:
            raise ValueError(candidate["operation"])
    return bytes(out)


def with_null_mask(candidate: dict[str, Any]) -> dict[str, Any]:
    scheme = candidate_scheme(candidate)
    clone = dict(candidate)
    clone["mask"] = permutation_mask(candidate["mask"], scheme)
    clone["name"] = f"null-{candidate['name']}"
    clone["mask_hex_sha256"] = hashlib.sha256(mask_hex(clone["mask"], scheme).encode("ascii")).hexdigest()
    return clone


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def analyze_candidate_on_corpus(
    candidate: dict[str, Any],
    corpus: dict[str, Any],
    prefix_sets: list[set[bytes]],
    *,
    null_control: bool = False,
) -> dict[str, Any]:
    source = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    base = apply_base(source, candidate)
    corrected = apply_contextual(base, candidate)
    if invert_contextual(corrected, candidate) != base:
        raise RuntimeError(f"{candidate['name']}: contextual transform failed inversion")
    base_metrics = generate_transform_probe.analyze_bytes(base, prefix_sets)
    corrected_metrics = generate_transform_probe.analyze_bytes(corrected, prefix_sets)
    validation_kind = (
        "self-source"
        if corpus["corpus"] == candidate["source_corpus"]
        else "cross-corpus"
    )
    if corpus["role"] == "discovery":
        validation_kind = "discovery"
    if null_control:
        validation_kind = f"null-{validation_kind}"
    return {
        "name": f"{corpus['name']}::{candidate['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "control_kind": corpus.get("control_kind", "ordinary-structured"),
        "paired_with": corpus.get("paired_with"),
        "validation_kind": validation_kind,
        "null_control": null_control,
        "candidate": candidate["name"],
        "operation": candidate["operation"],
        "context_scheme": candidate["context_scheme"],
        "source_case": candidate["source_case"],
        "source_corpus": candidate["source_corpus"],
        "source_transform": candidate["source_transform"],
        "metadata_bytes": candidate["metadata_bytes"],
        "input_bytes": len(corrected),
        "input_sha256": hashlib.sha256(corrected).hexdigest(),
        "base_prefix_ge_3": base_metrics["prefix_ge_3_count"],
        "base_prefix_ge_4": base_metrics["prefix_ge_4_count"],
        "base_prefix_ge_5": base_metrics["prefix_ge_5_count"],
        "base_prefix_ge_6": base_metrics["prefix_ge_6_count"],
        "base_exact_hits": base_metrics["exact_span_hits"],
        "corrected_prefix_ge_3": corrected_metrics["prefix_ge_3_count"],
        "corrected_prefix_ge_4": corrected_metrics["prefix_ge_4_count"],
        "corrected_prefix_ge_5": corrected_metrics["prefix_ge_5_count"],
        "corrected_prefix_ge_6": corrected_metrics["prefix_ge_6_count"],
        "corrected_exact_hits": corrected_metrics["exact_span_hits"],
        "prefix_ge_3_delta_vs_base": corrected_metrics["prefix_ge_3_count"]
        - base_metrics["prefix_ge_3_count"],
        "prefix_ge_4_delta_vs_base": corrected_metrics["prefix_ge_4_count"]
        - base_metrics["prefix_ge_4_count"],
        "prefix_ge_5_delta_vs_base": corrected_metrics["prefix_ge_5_count"]
        - base_metrics["prefix_ge_5_count"],
        "prefix_ge_6_delta_vs_base": corrected_metrics["prefix_ge_6_count"]
        - base_metrics["prefix_ge_6_count"],
        "exact_delta_vs_base": corrected_metrics["exact_span_hits"]
        - base_metrics["exact_span_hits"],
        "prefix5_from_prefix4": ratio(
            corrected_metrics["prefix_ge_5_count"],
            corrected_metrics["prefix_ge_4_count"],
        ),
        "expected_random_prefix_ge_5": corrected_metrics["candidate_spans"]
        * len(prefix_sets[5])
        / float(2 ** 40),
    }


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    return (
        row["corrected_exact_hits"],
        row["exact_delta_vs_base"],
        row["prefix_ge_5_delta_vs_base"],
        row["corrected_prefix_ge_5"],
        row["prefix_ge_4_delta_vs_base"],
        row["corrected_prefix_ge_4"],
        row["candidate"],
    )


def summarize(rows: list[dict[str, Any]], null_rows: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    heldout_cross = [
        row
        for row in rows
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "cross-corpus"
    ]
    null_heldout_cross = [
        row
        for row in null_rows
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "null-cross-corpus"
    ]
    self_rows = [row for row in rows if row["validation_kind"] == "self-source"]
    cross_prefix5_wins = [
        row for row in heldout_cross if row["prefix_ge_5_delta_vs_base"] > 0
    ]
    null_cross_prefix5_wins = [
        row for row in null_heldout_cross if row["prefix_ge_5_delta_vs_base"] > 0
    ]
    cross_exact_rows = [row for row in heldout_cross if row["corrected_exact_hits"] > 0]
    null_cross_exact_rows = [
        row for row in null_heldout_cross if row["corrected_exact_hits"] > 0
    ]
    prefix5_corpora = sorted({row["corpus"] for row in cross_prefix5_wins})
    null_prefix5_corpora = sorted({row["corpus"] for row in null_cross_prefix5_wins})
    shadow_cross = [row for row in heldout_cross if row["control_kind"] == "shadow-vocab"]
    binary_cross = [row for row in heldout_cross if row["control_kind"].startswith("binary-")]
    shadow_prefix5 = [row for row in shadow_cross if row["prefix_ge_5_delta_vs_base"] > 0]
    binary_prefix5 = [row for row in binary_cross if row["prefix_ge_5_delta_vs_base"] > 0]
    shadow_exact = [row for row in shadow_cross if row["corrected_exact_hits"] > 0]
    binary_exact = [row for row in binary_cross if row["corrected_exact_hits"] > 0]
    best_cross = max(heldout_cross, key=row_score, default=None)
    best_null = max(null_heldout_cross, key=row_score, default=None)
    promotion_met = bool(cross_exact_rows) or (
        len(prefix5_corpora) >= 2
        and len(cross_prefix5_wins) > len(null_cross_prefix5_wins)
        and len(prefix5_corpora) > len(null_prefix5_corpora)
    )
    conclusion = (
        "Contextual fifth-byte steering did not pass the held-out promotion gate."
        if not promotion_met
        else "A contextual fifth-byte steering candidate passed the held-out promotion gate."
    )
    return {
        "candidate_count": len(candidates),
        "validation_rows": len(rows),
        "null_validation_rows": len(null_rows),
        "heldout_cross_rows": len(heldout_cross),
        "cross_prefix5_win_rows": len(cross_prefix5_wins),
        "cross_prefix5_win_corpora": len(prefix5_corpora),
        "cross_exact_hit_rows": len(cross_exact_rows),
        "cross_exact_hits": sum(row["corrected_exact_hits"] for row in cross_exact_rows),
        "shadow_cross_rows": len(shadow_cross),
        "shadow_prefix5_win_rows": len(shadow_prefix5),
        "shadow_exact_hit_rows": len(shadow_exact),
        "binary_cross_rows": len(binary_cross),
        "binary_prefix5_win_rows": len(binary_prefix5),
        "binary_exact_hit_rows": len(binary_exact),
        "null_cross_prefix5_win_rows": len(null_cross_prefix5_wins),
        "null_cross_prefix5_win_corpora": len(null_prefix5_corpora),
        "null_cross_exact_hit_rows": len(null_cross_exact_rows),
        "self_prefix5_win_rows": sum(1 for row in self_rows if row["prefix_ge_5_delta_vs_base"] > 0),
        "best_cross_case": best_cross["name"] if best_cross else None,
        "best_cross_prefix_ge_5": best_cross["corrected_prefix_ge_5"] if best_cross else 0,
        "best_cross_prefix_ge_5_delta": best_cross["prefix_ge_5_delta_vs_base"] if best_cross else 0,
        "best_cross_exact_hits": best_cross["corrected_exact_hits"] if best_cross else 0,
        "best_null_case": best_null["name"] if best_null else None,
        "best_null_prefix_ge_5_delta": best_null["prefix_ge_5_delta_vs_base"] if best_null else 0,
        "promotion_met": promotion_met,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    residual = load_json(RESIDUAL_JSON)
    candidates = candidate_manifest(residual)
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    rows = [
        analyze_candidate_on_corpus(candidate, corpus, prefix_sets)
        for candidate in candidates
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
    ]
    null_rows = [
        analyze_candidate_on_corpus(with_null_mask(candidate), corpus, prefix_sets, null_control=True)
        for candidate in candidates
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
    ]
    return {
        "generated_by": "scripts/generate_contextual_fifth_byte_steering.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "fifth_byte_residual_sha256": sha256(RESIDUAL_JSON),
        },
        "source_manifest_sha256": source_manifest_hash(),
        "candidate_manifest_sha256": candidate_manifest_hash(candidates),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "context_schemes": CONTEXT_SCHEMES,
        "display_limit": DISPLAY_LIMIT,
        "candidates": candidates,
        "results": rows,
        "null_results": null_rows,
        "summary": summarize(rows, null_rows, candidates),
        "promotion_rule": (
            "Promote only if any held-out non-self-source exact hit appears, "
            "or prefix>=5 uplift appears on at least two unrelated held-out corpora "
            "and beats same-shape permutation controls."
        ),
        "stop_rule": (
            "Stop this transform family if cross-corpus prefix>=5 uplift and exact hits "
            "remain zero, or if apparent movement is self-source only."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(rows, key=row_score, reverse=True)[:limit]


def write_report(payload: dict[str, Any]) -> None:
    CONTEXTUAL_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    heldout_cross = [
        row
        for row in payload["results"]
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "cross-corpus"
    ]
    null_heldout_cross = [
        row
        for row in payload["null_results"]
        if row["corpus_role"] == "held-out" and row["validation_kind"] == "null-cross-corpus"
    ]
    lines = [
        "# Telomere Contextual Fifth-Byte Steering",
        "",
        "Generated by `scripts/generate_contextual_fifth_byte_steering.py` from the fifth-byte residual artifact.",
        "This diagnostic trains bounded context-conditioned masks and validates them cross-corpus.",
        "It is not `.tlmr` format support and not a compression claim.",
        "",
        f"Candidate masks: `{summary['candidate_count']}`.",
        f"Held-out cross-corpus rows: `{summary['heldout_cross_rows']}`.",
        f"Cross-corpus prefix >=5 win rows: `{summary['cross_prefix5_win_rows']}`.",
        f"Cross-corpus prefix >=5 win corpora: `{summary['cross_prefix5_win_corpora']}`.",
        f"Cross-corpus exact-hit rows: `{summary['cross_exact_hit_rows']}`.",
        f"Vocabulary-disjoint shadow prefix >=5 win rows: `{summary['shadow_prefix5_win_rows']}`.",
        f"Binary TLV/varint prefix >=5 win rows: `{summary['binary_prefix5_win_rows']}`.",
        f"Null-control prefix >=5 win rows: `{summary['null_cross_prefix5_win_rows']}`.",
        f"Promotion met: `{summary['promotion_met']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best cross-corpus case: `{summary['best_cross_case']}`.",
        f"Best cross-corpus prefix>=5 delta: `{summary['best_cross_prefix_ge_5_delta']}`.",
        f"Best cross-corpus exact hits: `{summary['best_cross_exact_hits']}`.",
        f"Best null-control case: `{summary['best_null_case']}`.",
        f"Best null-control prefix>=5 delta: `{summary['best_null_prefix_ge_5_delta']}`.",
        "",
        "## Candidate Masks",
        "",
        "| candidate | op | context | source case | source prefix4 | metadata bytes |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            "| {name} | {operation} | {context_scheme} | {source_case} | "
            "{source_prefix4_events} | {metadata_bytes} |".format(**candidate)
        )

    lines.extend(
        [
            "",
            "## Top Cross-Corpus Rows",
            "",
            "| case | kind | candidate | base p4 | corrected p4 | base p5 | corrected p5 | p5 delta | p5/p4 | exact hits |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(heldout_cross, payload["display_limit"]):
        p5p4 = "-" if row["prefix5_from_prefix4"] is None else f"{row['prefix5_from_prefix4']:.3f}"
        lines.append(
            "| {name} | {control_kind} | {candidate} | {base_prefix_ge_4} | {corrected_prefix_ge_4} | "
            "{base_prefix_ge_5} | {corrected_prefix_ge_5} | {prefix_ge_5_delta_vs_base:+} | "
            "{p5p4} | {corrected_exact_hits} |".format(p5p4=p5p4, **row)
        )

    lines.extend(
        [
            "",
            "## Top Null-Control Rows",
            "",
            "| case | candidate | corrected p5 | p5 delta | exact hits |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(null_heldout_cross, payload["display_limit"]):
        lines.append(
            "| {name} | {candidate} | {corrected_prefix_ge_5} | "
            "{prefix_ge_5_delta_vs_base:+} | {corrected_exact_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Promotion And Stop Rules",
            "",
            f"- Promotion rule: {payload['promotion_rule']}",
            f"- Stop rule: {payload['stop_rule']}",
            "",
            "## Interpretation",
            "",
            "- Context keys depend only on position and already-decoded previous bytes, so the transform is sequentially reversible.",
            "- Self-source rows are diagnostic only; held-out cross-corpus rows are the promotion gate.",
            "- Vocabulary-disjoint and binary TLV/varint controls are reported separately so token/syntax artifacts do not masquerade as seed-manifold signal.",
            "- Same-shape permutation controls protect against candidate-count artifacts and accidental phase wins.",
            "- Prefix >=5 movement is a promotion signal for narrower follow-up, not proof of compression.",
        ]
    )
    CONTEXTUAL_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not CONTEXTUAL_JSON.exists() or not CONTEXTUAL_MD.exists():
        raise SystemExit("generated contextual fifth-byte steering files are missing")
    payload = load_json(CONTEXTUAL_JSON)
    if payload.get("generated_by") != "scripts/generate_contextual_fifth_byte_steering.py":
        raise SystemExit("contextual_fifth_byte_steering.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != {
        "fifth_byte_residual_sha256": sha256(RESIDUAL_JSON),
    }:
        raise SystemExit("contextual_fifth_byte_steering.json artifact hashes are stale")
    if payload.get("source_manifest_sha256") != source_manifest_hash():
        raise SystemExit("contextual_fifth_byte_steering.json source manifest hash is stale")
    expected_candidates = candidate_manifest()
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash(expected_candidates):
        raise SystemExit("contextual_fifth_byte_steering.json candidate manifest hash is stale")
    if payload.get("summary", {}).get("candidate_count") != len(expected_candidates):
        raise SystemExit("contextual_fifth_byte_steering.json candidate count is stale")
    expected_rows = len(expected_candidates) * len(
        generate_transform_validation.CORPUS_VALIDATION_MATRIX
    )
    if len(payload.get("results", [])) != expected_rows:
        raise SystemExit("contextual_fifth_byte_steering.json validation row count is stale")
    if len(payload.get("null_results", [])) != expected_rows:
        raise SystemExit("contextual_fifth_byte_steering.json null-control row count is stale")
    text = CONTEXTUAL_MD.read_text(encoding="utf-8")
    for phrase in (
        "context-conditioned masks",
        "Cross-corpus prefix >=5 win rows",
        "Vocabulary-disjoint shadow",
        "Binary TLV/varint",
        "same-shape permutation controls",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"CONTEXTUAL_FIFTH_BYTE_STEERING.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated contextual steering files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
