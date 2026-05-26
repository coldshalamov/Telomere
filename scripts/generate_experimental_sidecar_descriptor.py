#!/usr/bin/env python3
"""Prototype an experimental residual sidecar descriptor for promoted rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_affine_transform_search
import generate_corpus_matrix
import generate_seed_manifold_residual_steering
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DESCRIPTOR_JSON = DOCS / "experimental_sidecar_descriptor.json"
DESCRIPTOR_MD = DOCS / "EXPERIMENTAL_SIDECAR_DESCRIPTOR.md"

MAGIC = b"TSD1"
FORMAT_VERSION = 1
CODERS = ("zlib_level9", "lzma_preset9")

TAG_SIDECAR = 0x02
TAG_LITERAL = 0xFF


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "residual_payload_compressibility_sha256": sha256(
            DOCS / "residual_payload_compressibility.json"
        ),
        "seed_manifold_residual_steering_sha256": sha256(
            DOCS / "seed_manifold_residual_steering.json"
        ),
        "format_doc_sha256": sha256(DOCS / "FORMAT.md"),
    }


def descriptor_manifest() -> dict[str, Any]:
    return {
        "magic": MAGIC.decode("ascii"),
        "format_version": FORMAT_VERSION,
        "coders": CODERS,
        "literal_record": "tag 0xff + u32 length + literal bytes",
        "sidecar_record": "tag 0x02 + u16 span_len + u8 prefix_len + u8 seed_len + seed bytes",
        "payload": "single compressed residual byte stream consumed by sidecar records in order",
        "scope": "research artifact only; not .tlmr format support",
    }


def descriptor_manifest_hash() -> str:
    payload = json.dumps(
        descriptor_manifest(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compress_payload(coder: str, payload: bytes) -> bytes:
    if coder == "zlib_level9":
        return zlib.compress(payload, level=9)
    if coder == "lzma_preset9":
        return lzma.compress(payload, preset=9 | lzma.PRESET_EXTREME)
    raise ValueError(coder)


def decompress_payload(coder: str, payload: bytes) -> bytes:
    if coder == "zlib_level9":
        return zlib.decompress(payload)
    if coder == "lzma_preset9":
        return lzma.decompress(payload)
    raise ValueError(coder)


def transform_descriptor(candidate: dict[str, Any]) -> bytes:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return bytes([0])
    if family == "affine":
        return bytes([1, int(parameter["multiplier"]), int(parameter["offset"])])
    if family == "phase-affine":
        return bytes(
            [
                2,
                int(parameter["period"]),
                int(parameter["multiplier"]),
                int(parameter["offset"]),
                int(parameter["phase_delta"]),
            ]
        )
    raise ValueError(family)


def invert_transform(data: bytes, candidate: dict[str, Any]) -> bytes:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return data
    if family == "affine":
        multiplier = int(parameter["multiplier"])
        offset = int(parameter["offset"])
        inverse = generate_affine_transform_search.mod_inverse_256(multiplier)
        return bytes(((inverse * ((byte - offset) & 0xFF)) & 0xFF) for byte in data)
    if family == "phase-affine":
        period = int(parameter["period"])
        multiplier = int(parameter["multiplier"])
        offset = int(parameter["offset"])
        phase_delta = int(parameter["phase_delta"])
        inverse = generate_affine_transform_search.mod_inverse_256(multiplier)
        return bytes(
            (
                inverse
                * (
                    byte
                    - offset
                    - phase_delta * (idx % period)
                )
            )
            & 0xFF
            for idx, byte in enumerate(data)
        )
    raise ValueError(family)


def promoted_policy_rows() -> list[dict[str, Any]]:
    payload = load_json(DOCS / "residual_payload_compressibility.json")
    return [
        row
        for row in payload["policy_rows"]
        if row["role"] == "held-out"
        and row["payload_policy"] in CODERS
        and row["strict_negative"]
    ]


def selected_case(row_name: str) -> dict[str, Any]:
    parts = row_name.split("::")
    if len(parts) != 3:
        raise ValueError(row_name)
    corpus_name, transform_name, scheme_name = parts
    corpus = next(
        row for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX
        if row["name"] == corpus_name
    )
    transform = next(
        row for row in generate_seed_manifold_residual_steering.selected_affine_candidates()
        if row["name"] == transform_name
    )
    scheme = next(
        row for row in generate_seed_manifold_residual_steering.RESIDUAL_SCHEMES
        if row["name"] == scheme_name
    )
    original = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    transformed = generate_affine_transform_search.apply_candidate(original, transform)
    maps = generate_seed_manifold_residual_steering.seed_prefix_maps()
    opportunities = []
    for start in range(
        0,
        max(0, len(transformed) - generate_seed_manifold_residual_steering.SPAN_LEN + 1),
        generate_seed_manifold_residual_steering.SPAN_STEP,
    ):
        opportunity = generate_seed_manifold_residual_steering.opportunity_for_span(
            transformed[start : start + generate_seed_manifold_residual_steering.SPAN_LEN],
            start,
            scheme,
            maps,
        )
        if opportunity is not None:
            opportunities.append(opportunity)
    selected = generate_seed_manifold_residual_steering.select_non_overlapping(
        opportunities
    )
    return {
        "name": row_name,
        "corpus": corpus,
        "transform": transform,
        "scheme": scheme,
        "original": original,
        "transformed": transformed,
        "selected": selected,
    }


def encode_literal(buf: bytearray, literal: bytes) -> None:
    buf.append(TAG_LITERAL)
    buf.extend(struct.pack(">I", len(literal)))
    buf.extend(literal)


def encode_sidecar(buf: bytearray, record: dict[str, Any]) -> None:
    seed = bytes.fromhex(record["seed_hex"])
    buf.append(TAG_SIDECAR)
    buf.extend(struct.pack(">H", record["span_len"]))
    buf.append(record["prefix_len"])
    buf.append(record["seed_len"])
    buf.extend(seed)


def build_descriptor(case: dict[str, Any], coder: str) -> dict[str, Any]:
    original: bytes = case["original"]
    transformed: bytes = case["transformed"]
    selected: list[dict[str, Any]] = case["selected"]
    residual_payload = bytes.fromhex(
        "".join(row["residual_hex"] for row in selected)
    )
    compressed_payload = compress_payload(coder, residual_payload)
    transform_bytes = transform_descriptor(case["transform"])

    records = bytearray()
    cursor = 0
    literal_record_count = 0
    sidecar_record_count = 0
    for record in selected:
        start = record["start_offset"]
        if start > cursor:
            encode_literal(records, transformed[cursor:start])
            literal_record_count += 1
        encode_sidecar(records, record)
        sidecar_record_count += 1
        cursor = start + record["span_len"]
    if cursor < len(transformed):
        encode_literal(records, transformed[cursor:])
        literal_record_count += 1

    header = bytearray()
    header.extend(MAGIC)
    header.append(FORMAT_VERSION)
    header.append(CODERS.index(coder) + 1)
    header.append(len(transform_bytes))
    header.extend(transform_bytes)
    header.extend(struct.pack(">I", len(original)))
    header.extend(struct.pack(">I", len(transformed)))
    header.extend(struct.pack(">I", len(selected)))
    header.extend(struct.pack(">I", len(records)))
    header.extend(struct.pack(">I", len(compressed_payload)))
    header.extend(hashlib.sha256(original).digest())
    header.extend(hashlib.sha256(transformed).digest())
    encoded = bytes(header) + bytes(records) + compressed_payload

    decoded = decode_descriptor(encoded, case["transform"])
    decode_verified = decoded == original
    corrupt_results = corrupt_rejection_results(encoded, case["transform"])

    literal_bytes = len(transformed) - sum(row["span_len"] for row in selected)
    literal_record_header_bytes = literal_record_count * 5
    sidecar_record_bytes = sum(5 + row["seed_len"] for row in selected)
    local_selected_delta = (
        len(transform_bytes)
        + sidecar_record_bytes
        + len(compressed_payload)
        - sum(row["span_len"] for row in selected)
    )
    full_stream_delta = len(encoded) - len(original)

    return {
        "name": case["name"],
        "coder": coder,
        "input_bytes": len(original),
        "encoded_bytes": len(encoded),
        "full_stream_delta_bytes": full_stream_delta,
        "full_stream_delta_pct": full_stream_delta / len(original) * 100,
        "local_selected_delta_bytes": local_selected_delta,
        "decode_verified": decode_verified,
        "corrupt_rejections": corrupt_results,
        "selected_span_count": len(selected),
        "literal_record_count": literal_record_count,
        "sidecar_record_count": sidecar_record_count,
        "literal_bytes": literal_bytes,
        "literal_record_header_bytes": literal_record_header_bytes,
        "sidecar_record_bytes": sidecar_record_bytes,
        "raw_residual_payload_bytes": len(residual_payload),
        "compressed_payload_bytes": len(compressed_payload),
        "payload_ratio": len(compressed_payload) / len(residual_payload),
        "transform_descriptor_bytes": len(transform_bytes),
        "container_overhead_bytes": len(encoded)
        - literal_bytes
        - sidecar_record_bytes
        - len(compressed_payload),
        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        "output_sha256": hashlib.sha256(decoded).hexdigest() if decode_verified else None,
    }


def decode_descriptor(encoded: bytes, transform: dict[str, Any]) -> bytes:
    if len(encoded) < 4 or encoded[:4] != MAGIC:
        raise ValueError("invalid descriptor magic")
    offset = 4
    version = encoded[offset]
    offset += 1
    if version != FORMAT_VERSION:
        raise ValueError("unsupported descriptor version")
    coder_id = encoded[offset]
    offset += 1
    if coder_id < 1 or coder_id > len(CODERS):
        raise ValueError("unsupported residual coder")
    coder = CODERS[coder_id - 1]
    transform_len = encoded[offset]
    offset += 1
    offset += transform_len
    original_len, transformed_len, selected_count, records_len, payload_len = struct.unpack(
        ">IIIII",
        encoded[offset : offset + 20],
    )
    offset += 20
    original_hash = encoded[offset : offset + 32]
    offset += 32
    transformed_hash = encoded[offset : offset + 32]
    offset += 32
    records_end = offset + records_len
    payload_end = records_end + payload_len
    if records_end > len(encoded) or payload_end != len(encoded):
        raise ValueError("descriptor length mismatch")
    records = encoded[offset:records_end]
    payload = decompress_payload(coder, encoded[records_end:payload_end])
    payload_offset = 0
    selected_seen = 0
    out = bytearray()
    rec_offset = 0
    while rec_offset < len(records):
        tag = records[rec_offset]
        rec_offset += 1
        if tag == TAG_LITERAL:
            if rec_offset + 4 > len(records):
                raise ValueError("truncated literal length")
            literal_len = struct.unpack(">I", records[rec_offset : rec_offset + 4])[0]
            rec_offset += 4
            literal = records[rec_offset : rec_offset + literal_len]
            if len(literal) != literal_len:
                raise ValueError("truncated literal payload")
            out.extend(literal)
            rec_offset += literal_len
            continue
        if tag == TAG_SIDECAR:
            if rec_offset + 4 > len(records):
                raise ValueError("truncated sidecar record")
            span_len = struct.unpack(">H", records[rec_offset : rec_offset + 2])[0]
            rec_offset += 2
            prefix_len = records[rec_offset]
            rec_offset += 1
            seed_len = records[rec_offset]
            rec_offset += 1
            seed = records[rec_offset : rec_offset + seed_len]
            rec_offset += seed_len
            if len(seed) != seed_len or prefix_len > span_len:
                raise ValueError("invalid sidecar seed")
            expanded = hashlib.sha256(seed).digest()[:span_len]
            residual_len = span_len - prefix_len
            residual = payload[payload_offset : payload_offset + residual_len]
            if len(residual) != residual_len:
                raise ValueError("residual payload exhausted")
            payload_offset += residual_len
            out.extend(expanded[:prefix_len])
            out.extend(
                expanded[prefix_len + idx] ^ residual[idx]
                for idx in range(residual_len)
            )
            selected_seen += 1
            continue
        raise ValueError("unknown descriptor record tag")
    if payload_offset != len(payload) or selected_seen != selected_count:
        raise ValueError("descriptor payload accounting mismatch")
    transformed = bytes(out)
    if len(transformed) != transformed_len:
        raise ValueError("decoded transformed length mismatch")
    if hashlib.sha256(transformed).digest() != transformed_hash:
        raise ValueError("decoded transformed hash mismatch")
    original = invert_transform(transformed, transform)
    if len(original) != original_len:
        raise ValueError("decoded original length mismatch")
    if hashlib.sha256(original).digest() != original_hash:
        raise ValueError("decoded original hash mismatch")
    return original


def corrupt_rejection_results(encoded: bytes, transform: dict[str, Any]) -> dict[str, bool]:
    mutations = {
        "bad_magic": bytearray(encoded),
        "truncated": bytearray(encoded[:-1]),
        "payload_bitflip": bytearray(encoded),
    }
    mutations["bad_magic"][0] ^= 0xFF
    mutations["payload_bitflip"][-1] ^= 0x01
    results: dict[str, bool] = {}
    for name, mutated in mutations.items():
        try:
            decode_descriptor(bytes(mutated), transform)
        except Exception:
            results[name] = True
        else:
            results[name] = False
    return results


def build_rows() -> list[dict[str, Any]]:
    rows = []
    for policy_row in promoted_policy_rows():
        case = selected_case(policy_row["name"])
        rows.append(build_descriptor(case, policy_row["payload_policy"]))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "prototype_rows": len(rows),
        "decode_verified_rows": sum(1 for row in rows if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in rows
        ),
        "local_selected_negative_rows": sum(
            1 for row in rows if row["local_selected_delta_bytes"] < 0
        ),
        "full_stream_negative_rows": sum(
            1 for row in rows if row["full_stream_delta_bytes"] < 0
        ),
        "best_full_stream_delta_bytes": min(
            (row["full_stream_delta_bytes"] for row in rows),
            default=None,
        ),
        "best_local_selected_delta_bytes": min(
            (row["local_selected_delta_bytes"] for row in rows),
            default=None,
        ),
        "conclusion": (
            "The promoted payload signal decodes correctly but does not survive full-stream descriptor overhead."
        ),
    }


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_experimental_sidecar_descriptor.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "descriptor_manifest_sha256": descriptor_manifest_hash(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    DESCRIPTOR_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Experimental Sidecar Descriptor",
        "",
        "Generated by `scripts/generate_experimental_sidecar_descriptor.py`.",
        "This is a research-only descriptor prototype, not `.tlmr` format support.",
        "",
        f"Prototype rows: `{summary['prototype_rows']}`.",
        f"Decode verified rows: `{summary['decode_verified_rows']}`.",
        f"All corrupt rejections passed: `{summary['all_corrupt_rejections_passed']}`.",
        f"Local selected negative rows: `{summary['local_selected_negative_rows']}`.",
        f"Full-stream negative rows: `{summary['full_stream_negative_rows']}`.",
        f"Best full-stream delta bytes: `{summary['best_full_stream_delta_bytes']}`.",
        f"Best local selected delta bytes: `{summary['best_local_selected_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Prototype Rows",
        "",
        "| row | coder | input | encoded | full delta | local selected delta | spans | payload | decode | corrupt rejected |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {name} | {coder} | {input_bytes} | {encoded_bytes} | "
            "{full_stream_delta_bytes} | {local_selected_delta_bytes} | "
            "{selected_span_count} | {compressed_payload_bytes} | "
            "{decode_verified} | {corrupt} |".format(
                corrupt=all(row["corrupt_rejections"].values()),
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The zlib/LZMA residual payload signal is real at the selected-span accounting layer.",
            "- A decodable whole-stream descriptor pays literal-run and container overhead, so the current promoted row still bloats as a file.",
            "- This falsifies immediate sidecar format promotion while preserving the payload signal as a target for lower-overhead record design.",
            "- The next useful sidecar work is record-overhead reduction or larger span bundles, not broader compute scale-up.",
        ]
    )
    DESCRIPTOR_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not DESCRIPTOR_JSON.exists() or not DESCRIPTOR_MD.exists():
        raise SystemExit("generated experimental sidecar descriptor files are missing")
    payload = load_json(DESCRIPTOR_JSON)
    if payload.get("generated_by") != "scripts/generate_experimental_sidecar_descriptor.py":
        raise SystemExit("experimental_sidecar_descriptor.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("experimental sidecar descriptor artifact hashes are stale")
    if payload.get("descriptor_manifest_sha256") != descriptor_manifest_hash():
        raise SystemExit("experimental sidecar descriptor manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("decode_verified_rows") != summary.get("prototype_rows"):
        raise SystemExit("experimental sidecar descriptor decode proof failed")
    if not summary.get("all_corrupt_rejections_passed"):
        raise SystemExit("experimental sidecar descriptor corrupt rejection failed")
    text = DESCRIPTOR_MD.read_text(encoding="utf-8")
    for phrase in (
        "Experimental Sidecar Descriptor",
        "research-only descriptor prototype",
        "Full-stream negative rows",
        "does not survive full-stream descriptor overhead",
        "record-overhead reduction or larger span bundles",
    ):
        if phrase not in text:
            raise SystemExit(f"EXPERIMENTAL_SIDECAR_DESCRIPTOR.md missing phrase: {phrase}")


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
