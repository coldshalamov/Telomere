#!/usr/bin/env python3
"""Search bounded structural reversible transforms across held-out corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from math import gcd
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STRUCTURAL_JSON = DOCS / "structural_transform_search.json"
STRUCTURAL_MD = DOCS / "STRUCTURAL_TRANSFORM_SEARCH.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
    }


def bytes_rotl(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (8 - shift))) & 0xFF


def gray_byte(value: int) -> int:
    return value ^ (value >> 1)


def ungray_byte(value: int) -> int:
    out = value
    shift = 1
    while shift < 8:
        out ^= out >> shift
        shift <<= 1
    return out & 0xFF


def stride_permute(data: bytes, width: int, stride: int) -> bytes:
    if gcd(width, stride) != 1:
        raise ValueError("stride must be coprime to width")
    out = bytearray()
    for start in range(0, len(data), width):
        chunk = data[start : start + width]
        if len(chunk) < width:
            out.extend(chunk)
        else:
            out.extend(chunk[(idx * stride) % width] for idx in range(width))
    return bytes(out)


def invert_stride_permute(data: bytes, width: int, stride: int) -> bytes:
    out = bytearray()
    for start in range(0, len(data), width):
        chunk = data[start : start + width]
        if len(chunk) < width:
            out.extend(chunk)
            continue
        restored = bytearray(width)
        for idx, value in enumerate(chunk):
            restored[(idx * stride) % width] = value
        out.extend(restored)
    return bytes(out)


def bitplane_transpose_8(data: bytes) -> bytes:
    out = bytearray()
    for start in range(0, len(data), 8):
        chunk = data[start : start + 8]
        if len(chunk) < 8:
            out.extend(chunk)
            continue
        for bit in range(8):
            value = 0
            for idx, byte in enumerate(chunk):
                value |= ((byte >> bit) & 1) << idx
            out.append(value)
    return bytes(out)


def xor_index(data: bytes, period: int) -> bytes:
    return bytes(byte ^ (idx % period) for idx, byte in enumerate(data))


def add_index(data: bytes, period: int) -> bytes:
    return bytes((byte + (idx % period)) & 0xFF for idx, byte in enumerate(data))


def sub_index(data: bytes, period: int) -> bytes:
    return bytes((byte - (idx % period)) & 0xFF for idx, byte in enumerate(data))


def delta2(data: bytes, lag: int) -> bytes:
    if lag <= 0:
        raise ValueError("lag must be positive")
    out = bytearray(data[: 2 * lag])
    for idx in range(2 * lag, len(data)):
        predicted = (2 * data[idx - lag] - data[idx - 2 * lag]) & 0xFF
        out.append((data[idx] - predicted) & 0xFF)
    return bytes(out)


def invert_delta2(data: bytes, lag: int) -> bytes:
    out = bytearray(data[: 2 * lag])
    for idx in range(2 * lag, len(data)):
        predicted = (2 * out[idx - lag] - out[idx - 2 * lag]) & 0xFF
        out.append((data[idx] + predicted) & 0xFF)
    return bytes(out)


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
            "name": f"gray-{mode}",
            "family": "gray" if mode == "encode" else "ungray",
            "parameter": 0,
            "metadata_bytes": 1,
            "description": f"Bytewise Gray-code {mode} transform.",
        }
        for mode in ("encode", "decode")
    )
    candidates.extend(
        {
            "name": f"stride-w{width}-s{stride}",
            "family": "stride",
            "parameter": {"width": width, "stride": stride},
            "metadata_bytes": 2,
            "description": "Coprime byte permutation inside fixed chunks.",
        }
        for width in (8, 16, 32)
        for stride in (3, 5, 7, 11)
        if stride < width and gcd(width, stride) == 1
    )
    candidates.extend(
        {
            "name": f"bitplane-transpose-{repeat}",
            "family": "bitplane-transpose",
            "parameter": repeat,
            "metadata_bytes": 1,
            "description": "8x8 bitplane transpose repeated once or twice.",
        }
        for repeat in (1, 2)
    )
    candidates.extend(
        {
            "name": f"xor-index-p{period}",
            "family": "xor-index",
            "parameter": period,
            "metadata_bytes": 1,
            "description": "XOR every byte with its position modulo a period.",
        }
        for period in (4, 8, 16, 32)
    )
    candidates.extend(
        {
            "name": f"add-index-p{period}",
            "family": "add-index",
            "parameter": period,
            "metadata_bytes": 1,
            "description": "Add the byte position modulo a period.",
        }
        for period in (4, 8, 16, 32)
    )
    candidates.extend(
        {
            "name": f"delta2-lag{lag}",
            "family": "delta2",
            "parameter": lag,
            "metadata_bytes": 2 * lag,
            "description": "Second-order reversible residual against a lagged linear predictor.",
        }
        for lag in (1, 2, 4, 8)
    )
    candidates.extend(
        {
            "name": f"rotl-index-p{period}",
            "family": "rotl-index",
            "parameter": period,
            "metadata_bytes": 1,
            "description": "Rotate each byte left by position modulo 8, phased by a period.",
        }
        for period in (8, 16)
    )
    return candidates


def candidate_manifest_hash() -> str:
    payload = json.dumps(candidate_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def apply_candidate(data: bytes, candidate: dict[str, Any]) -> bytes:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return data
    if family == "gray":
        transformed = bytes(gray_byte(byte) for byte in data)
        if bytes(ungray_byte(byte) for byte in transformed) != data:
            raise RuntimeError("gray transform failed reversibility")
        return transformed
    if family == "ungray":
        transformed = bytes(ungray_byte(byte) for byte in data)
        if bytes(gray_byte(byte) for byte in transformed) != data:
            raise RuntimeError("ungray transform failed reversibility")
        return transformed
    if family == "stride":
        width = int(parameter["width"])
        stride = int(parameter["stride"])
        transformed = stride_permute(data, width, stride)
        if invert_stride_permute(transformed, width, stride) != data:
            raise RuntimeError("stride transform failed reversibility")
        return transformed
    if family == "bitplane-transpose":
        transformed = data
        for _ in range(int(parameter)):
            transformed = bitplane_transpose_8(transformed)
        restored = transformed
        for _ in range(int(parameter)):
            restored = bitplane_transpose_8(restored)
        if restored != data:
            raise RuntimeError("bitplane transpose failed reversibility")
        return transformed
    if family == "xor-index":
        transformed = xor_index(data, int(parameter))
        if xor_index(transformed, int(parameter)) != data:
            raise RuntimeError("xor-index failed reversibility")
        return transformed
    if family == "add-index":
        transformed = add_index(data, int(parameter))
        if sub_index(transformed, int(parameter)) != data:
            raise RuntimeError("add-index failed reversibility")
        return transformed
    if family == "delta2":
        transformed = delta2(data, int(parameter))
        if invert_delta2(transformed, int(parameter)) != data:
            raise RuntimeError("delta2 failed reversibility")
        return transformed
    if family == "rotl-index":
        period = int(parameter)
        transformed = bytes(bytes_rotl(byte, idx % 8) for idx, byte in enumerate(data))
        restored = bytes(bytes_rotl(byte, (8 - (idx % 8)) % 8) for idx, byte in enumerate(transformed))
        if restored != data:
            raise RuntimeError("rotl-index failed reversibility")
        return transformed
    raise ValueError(family)


def analyze_case(
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
        "control_kind": corpus.get("control_kind", "ordinary-structured"),
        "paired_with": corpus.get("paired_with"),
        "candidate": candidate["name"],
        "family": candidate["family"],
        "parameter": candidate["parameter"],
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
        row["candidate"],
    )


def best_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = output.get(row["corpus"])
        if current is None or row_score(row) > row_score(current):
            output[row["corpus"]] = row
    return output


def identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["corpus"]: row for row in rows if row["candidate"] == "identity"}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    identities = identity_by_corpus(rows)
    bests = best_by_corpus(rows)
    corpus_summaries = []
    heldout_prefix5_wins = 0
    heldout_exact_hits = 0
    shadow_prefix5_wins = 0
    binary_prefix5_wins = 0
    binary_exact_hits = 0
    for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        identity = identities[corpus["corpus"]]
        best = bests[corpus["corpus"]]
        prefix5_delta = best["prefix_ge_5_count"] - identity["prefix_ge_5_count"]
        exact_delta = best["exact_span_hits"] - identity["exact_span_hits"]
        kind = corpus.get("control_kind", "ordinary-structured")
        if corpus["role"] == "held-out":
            heldout_exact_hits += best["exact_span_hits"]
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
                "prefix_ge_4_delta_vs_identity": best["prefix_ge_4_count"]
                - identity["prefix_ge_4_count"],
                "prefix_ge_5_delta_vs_identity": prefix5_delta,
                "exact_delta_vs_identity": exact_delta,
            }
        )
    best_overall = max(rows, key=row_score, default=None)
    promotion_met = heldout_exact_hits > 0 or heldout_prefix5_wins > 0
    return {
        "candidate_count": len(candidate_manifest()),
        "validation_rows": len(rows),
        "heldout_prefix5_win_corpora": heldout_prefix5_wins,
        "heldout_exact_hits": heldout_exact_hits,
        "shadow_prefix5_win_corpora": shadow_prefix5_wins,
        "binary_prefix5_win_corpora": binary_prefix5_wins,
        "binary_exact_hits": binary_exact_hits,
        "best_overall_case": best_overall["name"] if best_overall else None,
        "best_overall_prefix_ge_5": best_overall["prefix_ge_5_count"] if best_overall else 0,
        "best_overall_exact_hits": best_overall["exact_span_hits"] if best_overall else 0,
        "promotion_met": promotion_met,
        "conclusion": (
            "Structural transform search produced a held-out prefix >=5 or exact-hit promotion signal."
            if promotion_met
            else "Structural transform search did not produce held-out prefix >=5 uplift or exact seed-span hits."
        ),
        "corpus_summaries": corpus_summaries,
    }


def build_report() -> dict[str, Any]:
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    candidates = candidate_manifest()
    rows = [
        analyze_case(corpus, candidate, prefix_sets)
        for corpus in generate_transform_validation.CORPUS_VALIDATION_MATRIX
        for candidate in candidates
    ]
    return {
        "generated_by": "scripts/generate_structural_transform_search.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "candidate_manifest_sha256": candidate_manifest_hash(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "candidates": candidates,
        "results": rows,
        "summary": summarize(rows),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(rows, key=row_score, reverse=True)[:limit]


def write_report(payload: dict[str, Any]) -> None:
    STRUCTURAL_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Structural Transform Search",
        "",
        "Generated by `scripts/generate_structural_transform_search.py`.",
        "This is a bounded reversible-transform search over held-out corpora and controls; it is not `.tlmr` format support.",
        "",
        f"Candidate transforms: `{summary['candidate_count']}`.",
        f"Validation rows: `{summary['validation_rows']}`.",
        f"Held-out prefix >=5 win corpora: `{summary['heldout_prefix5_win_corpora']}`.",
        f"Held-out exact hits: `{summary['heldout_exact_hits']}`.",
        f"Vocabulary-disjoint shadow prefix >=5 win corpora: `{summary['shadow_prefix5_win_corpora']}`.",
        f"Binary TLV/varint prefix >=5 win corpora: `{summary['binary_prefix5_win_corpora']}`.",
        f"Binary exact hits: `{summary['binary_exact_hits']}`.",
        f"Promotion met: `{summary['promotion_met']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best overall case: `{summary['best_overall_case']}` with prefix>=5 `{summary['best_overall_prefix_ge_5']}` and exact hits `{summary['best_overall_exact_hits']}`.",
        "",
        "## Corpus Summary",
        "",
        "| corpus | role | kind | best candidate | identity p4 | best p4 | best p5 | p5 delta | exact hits |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["corpus_summaries"]:
        lines.append(
            "| {corpus} | {role} | {control_kind} | {best_candidate} | "
            "{identity_prefix_ge_4} | {best_prefix_ge_4} | {best_prefix_ge_5} | "
            "{prefix_ge_5_delta_vs_identity:+} | {best_exact_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| row | kind | candidate | p3 | p4 | p5 | p6 | exact |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(payload["results"], payload.get("display_limit", 24)):
        lines.append(
            "| {name} | {control_kind} | {candidate} | {prefix_ge_3_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_span_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Promotion requires held-out prefix >=5 uplift or exact 8-byte seed-span hits.",
            "- Vocabulary-disjoint and binary TLV/varint controls are included so token-only effects do not look like manifold evidence.",
            "- Null results keep broad depth and format-transform work gated.",
        ]
    )
    STRUCTURAL_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not STRUCTURAL_JSON.exists() or not STRUCTURAL_MD.exists():
        raise SystemExit("generated structural transform search files are missing")
    payload = load_json(STRUCTURAL_JSON)
    if payload.get("generated_by") != "scripts/generate_structural_transform_search.py":
        raise SystemExit("structural_transform_search.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("structural_transform_search.json artifact hashes are stale")
    expected_candidates = candidate_manifest()
    if payload.get("candidate_manifest_sha256") != candidate_manifest_hash():
        raise SystemExit("structural_transform_search.json candidate manifest hash is stale")
    expected_rows = len(expected_candidates) * len(
        generate_transform_validation.CORPUS_VALIDATION_MATRIX
    )
    if len(payload.get("results", [])) != expected_rows:
        raise SystemExit("structural_transform_search.json result count is stale")
    text = STRUCTURAL_MD.read_text(encoding="utf-8")
    for phrase in (
        "Structural Transform Search",
        "bounded reversible-transform search",
        "Vocabulary-disjoint",
        "binary TLV/varint",
        "Promotion requires held-out prefix >=5 uplift",
    ):
        if phrase not in text:
            raise SystemExit(f"STRUCTURAL_TRANSFORM_SEARCH.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated structural search")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
