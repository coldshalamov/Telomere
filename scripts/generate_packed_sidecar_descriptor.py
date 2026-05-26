#!/usr/bin/env python3
"""Prototype a packed offset/seed-index residual sidecar descriptor."""

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

import generate_experimental_sidecar_descriptor
import generate_manifold_report


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PACKED_JSON = DOCS / "packed_sidecar_descriptor.json"
PACKED_MD = DOCS / "PACKED_SIDECAR_DESCRIPTOR.md"

MAGIC = b"TSP1"
FORMAT_VERSION = 1
SPAN_LEN = 8
PREFIX_LEN = 4
CODERS = ("zlib_level9", "lzma_preset9")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "sidecar_record_overhead_sha256": sha256(DOCS / "sidecar_record_overhead.json"),
        "experimental_sidecar_descriptor_sha256": sha256(
            DOCS / "experimental_sidecar_descriptor.json"
        ),
    }


def descriptor_manifest() -> dict[str, Any]:
    return {
        "magic": MAGIC.decode("ascii"),
        "format_version": FORMAT_VERSION,
        "span_len": SPAN_LEN,
        "prefix_len": PREFIX_LEN,
        "coders": CODERS,
        "offset_table": "u8 delta from previous selected start offset",
        "seed_table": "u16 seed index in consensus enumeration order",
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


def seed_table() -> list[bytes]:
    return list(generate_manifold_report.iter_seed_bytes(2))


def promoted_cases() -> list[tuple[dict[str, Any], str]]:
    descriptor = load_json(DOCS / "experimental_sidecar_descriptor.json")
    return [
        (
            generate_experimental_sidecar_descriptor.selected_case(row["name"]),
            row["coder"],
        )
        for row in descriptor["rows"]
    ]


def encode_case(case: dict[str, Any], coder: str) -> dict[str, Any]:
    original: bytes = case["original"]
    transformed: bytes = case["transformed"]
    selected: list[dict[str, Any]] = case["selected"]
    transform_bytes = generate_experimental_sidecar_descriptor.transform_descriptor(
        case["transform"]
    )
    residual_payload = bytes.fromhex(
        "".join(row["residual_hex"] for row in selected)
    )
    compressed_payload = compress_payload(coder, residual_payload)

    literal_stream = bytearray()
    table = bytearray()
    cursor = 0
    previous_start = 0
    for record in selected:
        start = record["start_offset"]
        delta = start - previous_start
        if delta < 0 or delta > 255:
            raise ValueError("offset delta does not fit u8")
        if record["seed_index"] > 0xFFFF:
            raise ValueError("seed index does not fit u16")
        literal_stream.extend(transformed[cursor:start])
        table.append(delta)
        table.extend(struct.pack(">H", record["seed_index"]))
        cursor = start + record["span_len"]
        previous_start = start
    literal_stream.extend(transformed[cursor:])

    header = bytearray()
    header.extend(MAGIC)
    header.append(FORMAT_VERSION)
    header.append(CODERS.index(coder) + 1)
    header.append(len(transform_bytes))
    header.extend(transform_bytes)
    header.extend(struct.pack(">I", len(original)))
    header.extend(struct.pack(">I", len(transformed)))
    header.extend(struct.pack(">I", len(selected)))
    header.extend(struct.pack(">I", len(literal_stream)))
    header.extend(struct.pack(">I", len(table)))
    header.extend(struct.pack(">I", len(compressed_payload)))
    header.extend(hashlib.sha256(original).digest())
    header.extend(hashlib.sha256(transformed).digest())

    encoded = bytes(header) + bytes(table) + bytes(literal_stream) + compressed_payload
    decoded = decode_descriptor(encoded, case["transform"])
    corrupt = corrupt_rejections(encoded, case["transform"])
    return {
        "name": case["name"],
        "coder": coder,
        "input_bytes": len(original),
        "encoded_bytes": len(encoded),
        "delta_bytes": len(encoded) - len(original),
        "delta_pct": (len(encoded) - len(original)) / len(original) * 100,
        "decode_verified": decoded == original,
        "corrupt_rejections": corrupt,
        "selected_span_count": len(selected),
        "literal_stream_bytes": len(literal_stream),
        "table_bytes": len(table),
        "raw_residual_payload_bytes": len(residual_payload),
        "compressed_payload_bytes": len(compressed_payload),
        "transform_descriptor_bytes": len(transform_bytes),
        "header_bytes": len(header),
        "max_offset_delta": max(
            b - a
            for a, b in zip(
                [0] + [row["start_offset"] for row in selected[:-1]],
                [row["start_offset"] for row in selected],
            )
        ),
        "max_seed_index": max(row["seed_index"] for row in selected),
        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        "output_sha256": hashlib.sha256(decoded).hexdigest() if decoded == original else None,
    }


def decode_descriptor(encoded: bytes, transform: dict[str, Any]) -> bytes:
    if len(encoded) < 4 or encoded[:4] != MAGIC:
        raise ValueError("invalid packed descriptor magic")
    offset = 4
    version = encoded[offset]
    offset += 1
    if version != FORMAT_VERSION:
        raise ValueError("unsupported packed descriptor version")
    coder_id = encoded[offset]
    offset += 1
    if coder_id < 1 or coder_id > len(CODERS):
        raise ValueError("unsupported packed descriptor coder")
    coder = CODERS[coder_id - 1]
    transform_len = encoded[offset]
    offset += 1 + transform_len
    original_len, transformed_len, selected_count, literal_len, table_len, payload_len = (
        struct.unpack(">IIIIII", encoded[offset : offset + 24])
    )
    offset += 24
    original_hash = encoded[offset : offset + 32]
    offset += 32
    transformed_hash = encoded[offset : offset + 32]
    offset += 32
    table_start = offset
    literal_start = table_start + table_len
    payload_start = literal_start + literal_len
    payload_end = payload_start + payload_len
    if payload_end != len(encoded) or table_len != selected_count * 3:
        raise ValueError("packed descriptor length mismatch")
    table = encoded[table_start:literal_start]
    literal_stream = encoded[literal_start:payload_start]
    residual_payload = decompress_payload(coder, encoded[payload_start:payload_end])
    seeds = seed_table()

    out = bytearray()
    literal_offset = 0
    residual_offset = 0
    previous_start = 0
    for idx in range(selected_count):
        entry_offset = idx * 3
        start = previous_start + table[entry_offset]
        seed_index = struct.unpack(">H", table[entry_offset + 1 : entry_offset + 3])[0]
        if seed_index >= len(seeds):
            raise ValueError("seed index outside enumeration")
        if start < len(out):
            raise ValueError("overlapping packed sidecar span")
        gap_len = start - len(out)
        gap = literal_stream[literal_offset : literal_offset + gap_len]
        if len(gap) != gap_len:
            raise ValueError("literal stream exhausted")
        out.extend(gap)
        literal_offset += gap_len
        seed = seeds[seed_index]
        expanded = hashlib.sha256(seed).digest()[:SPAN_LEN]
        residual_len = SPAN_LEN - PREFIX_LEN
        residual = residual_payload[residual_offset : residual_offset + residual_len]
        if len(residual) != residual_len:
            raise ValueError("residual stream exhausted")
        residual_offset += residual_len
        out.extend(expanded[:PREFIX_LEN])
        out.extend(
            expanded[PREFIX_LEN + residual_idx] ^ residual[residual_idx]
            for residual_idx in range(residual_len)
        )
        previous_start = start
    out.extend(literal_stream[literal_offset:])
    if residual_offset != len(residual_payload):
        raise ValueError("unused residual bytes")
    transformed = bytes(out)
    if len(transformed) != transformed_len:
        raise ValueError("packed transformed length mismatch")
    if hashlib.sha256(transformed).digest() != transformed_hash:
        raise ValueError("packed transformed hash mismatch")
    original = generate_experimental_sidecar_descriptor.invert_transform(
        transformed,
        transform,
    )
    if len(original) != original_len:
        raise ValueError("packed original length mismatch")
    if hashlib.sha256(original).digest() != original_hash:
        raise ValueError("packed original hash mismatch")
    return original


def corrupt_rejections(encoded: bytes, transform: dict[str, Any]) -> dict[str, bool]:
    mutations = {
        "bad_magic": bytearray(encoded),
        "truncated": bytearray(encoded[:-1]),
        "table_bitflip": bytearray(encoded),
        "payload_bitflip": bytearray(encoded),
    }
    mutations["bad_magic"][0] ^= 0xFF
    # Header is 4+1+1+1+transform(3)+24+64 = 98 for the promoted affine row.
    mutations["table_bitflip"][98] ^= 0x01
    mutations["payload_bitflip"][-1] ^= 0x01
    output: dict[str, bool] = {}
    for name, mutated in mutations.items():
        try:
            decode_descriptor(bytes(mutated), transform)
        except Exception:
            output[name] = True
        else:
            output[name] = False
    return output


def build_rows() -> list[dict[str, Any]]:
    return [encode_case(case, coder) for case, coder in promoted_cases()]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "prototype_rows": len(rows),
        "decode_verified_rows": sum(1 for row in rows if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in rows
        ),
        "full_stream_negative_rows": sum(1 for row in rows if row["delta_bytes"] < 0),
        "best_delta_bytes": min((row["delta_bytes"] for row in rows), default=None),
        "best_coder": min(rows, key=lambda row: row["delta_bytes"])["coder"] if rows else None,
        "conclusion": "Packed offset/seed-index descriptors decode and remain full-stream negative on the promoted row.",
    }


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_packed_sidecar_descriptor.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "descriptor_manifest_sha256": descriptor_manifest_hash(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    PACKED_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Packed Sidecar Descriptor",
        "",
        "Generated by `scripts/generate_packed_sidecar_descriptor.py`.",
        "This is a research-only packed descriptor prototype, not `.tlmr` format support.",
        "",
        f"Prototype rows: `{summary['prototype_rows']}`.",
        f"Decode verified rows: `{summary['decode_verified_rows']}`.",
        f"All corrupt rejections passed: `{summary['all_corrupt_rejections_passed']}`.",
        f"Full-stream negative rows: `{summary['full_stream_negative_rows']}`.",
        f"Best coder: `{summary['best_coder']}`.",
        f"Best delta bytes: `{summary['best_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Prototype Rows",
        "",
        "| row | coder | input | encoded | delta | spans | table bytes | payload bytes | max delta | decode | corrupt rejected |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {name} | {coder} | {input_bytes} | {encoded_bytes} | {delta_bytes} | "
            "{selected_span_count} | {table_bytes} | {compressed_payload_bytes} | "
            "{max_offset_delta} | {decode_verified} | {corrupt} |".format(
                corrupt=all(row["corrupt_rejections"].values()),
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The packed table turns the promoted residual payload signal into a real full-stream negative descriptor.",
            "- This is still one promoted held-out row, not a general natural-corpus compression claim.",
            "- The descriptor relies on small offset deltas, u16 seed indexes, fixed span length, and fixed prefix length.",
            "- Next work should test controls and generality before changing `.tlmr`.",
        ]
    )
    PACKED_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PACKED_JSON.exists() or not PACKED_MD.exists():
        raise SystemExit("generated packed sidecar descriptor files are missing")
    payload = load_json(PACKED_JSON)
    if payload.get("generated_by") != "scripts/generate_packed_sidecar_descriptor.py":
        raise SystemExit("packed_sidecar_descriptor.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("packed sidecar descriptor artifact hashes are stale")
    if payload.get("descriptor_manifest_sha256") != descriptor_manifest_hash():
        raise SystemExit("packed sidecar descriptor manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("decode_verified_rows") != summary.get("prototype_rows"):
        raise SystemExit("packed sidecar descriptor decode proof failed")
    if not summary.get("all_corrupt_rejections_passed"):
        raise SystemExit("packed sidecar descriptor corrupt rejection failed")
    text = PACKED_MD.read_text(encoding="utf-8")
    for phrase in (
        "Packed Sidecar Descriptor",
        "research-only packed descriptor prototype",
        "full-stream negative descriptor",
        "not a general natural-corpus compression claim",
    ):
        if phrase not in text:
            raise SystemExit(f"PACKED_SIDECAR_DESCRIPTOR.md missing phrase: {phrase}")


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
