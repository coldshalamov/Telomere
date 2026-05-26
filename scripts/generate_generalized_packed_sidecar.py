#!/usr/bin/env python3
"""Generalize packed sidecar descriptors across offset table modes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import generate_experimental_sidecar_descriptor
import generate_packed_sidecar_descriptor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GENERALIZED_JSON = DOCS / "generalized_packed_sidecar.json"
GENERALIZED_MD = DOCS / "GENERALIZED_PACKED_SIDECAR.md"

MAGIC = b"TSG1"
FORMAT_VERSION = 1
SPAN_LEN = 8
PREFIX_LEN = 4
CODERS = ("zlib_level9", "lzma_preset9")
OFFSET_MODES = (
    {
        "name": "delta_u8",
        "id": 1,
        "encoding": "fixed",
        "bytes": 1,
        "basis": "delta",
        "max": 0xFF,
    },
    {
        "name": "delta_u16",
        "id": 2,
        "encoding": "fixed",
        "bytes": 2,
        "basis": "delta",
        "max": 0xFFFF,
    },
    {
        "name": "absolute_u16",
        "id": 3,
        "encoding": "fixed",
        "bytes": 2,
        "basis": "absolute",
        "max": 0xFFFF,
    },
    {
        "name": "delta_uleb128",
        "id": 4,
        "encoding": "uleb128",
        "basis": "delta",
        "max": 0xFFFFFFFF,
    },
    {
        "name": "tiered_delta",
        "id": 5,
        "encoding": "tiered_u8_or_u16",
        "basis": "delta",
        "max": 0xFFFF,
    },
)
SEED_MODES = (
    {
        "name": "global_u16",
        "id": 1,
        "kind": "global_fixed",
        "ref_bytes": 2,
        "dict_seed_bytes": 0,
        "max_seed_index": 0xFFFF,
    },
    {
        "name": "global_u32",
        "id": 2,
        "kind": "global_fixed",
        "ref_bytes": 4,
        "dict_seed_bytes": 0,
        "max_seed_index": 0xFFFFFFFF,
    },
    {
        "name": "seed_const_or_local_u8_dict_u16",
        "id": 3,
        "kind": "const_or_local_dict",
        "ref_bytes": "0-or-1",
        "dict_seed_bytes": 2,
        "max_seed_index": 0xFFFF,
    },
    {
        "name": "seed_const_or_local_u8_dict_u32",
        "id": 4,
        "kind": "const_or_local_dict",
        "ref_bytes": "0-or-1",
        "dict_seed_bytes": 4,
        "max_seed_index": 0xFFFFFFFF,
    },
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "packed_sidecar_controls_sha256": sha256(DOCS / "packed_sidecar_controls.json"),
        "packed_sidecar_descriptor_sha256": sha256(
            DOCS / "packed_sidecar_descriptor.json"
        ),
        "residual_payload_compressibility_sha256": sha256(
            DOCS / "residual_payload_compressibility.json"
        ),
    }


def manifest() -> dict[str, Any]:
    return {
        "magic": MAGIC.decode("ascii"),
        "format_version": FORMAT_VERSION,
        "span_len": SPAN_LEN,
        "prefix_len": PREFIX_LEN,
        "coders": CODERS,
        "offset_modes": OFFSET_MODES,
        "seed_modes": SEED_MODES,
        "scope": "research artifact only; not .tlmr format support",
    }


def manifest_hash() -> str:
    payload = json.dumps(manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def offset_mode_by_id(mode_id: int) -> dict[str, Any]:
    for mode in OFFSET_MODES:
        if mode["id"] == mode_id:
            return mode
    raise ValueError("unsupported offset mode")


def seed_mode_by_id(mode_id: int) -> dict[str, Any]:
    for mode in SEED_MODES:
        if mode["id"] == mode_id:
            return mode
    raise ValueError("unsupported seed mode")


def source_rows() -> list[dict[str, Any]]:
    return load_json(DOCS / "residual_payload_compressibility.json")["payload_rows"]


@lru_cache(maxsize=1)
def seed_table() -> tuple[bytes, ...]:
    return tuple(generate_packed_sidecar_descriptor.seed_table())


def encode_uleb128(table: bytearray, value: int) -> None:
    while value >= 0x80:
        table.append((value & 0x7F) | 0x80)
        value >>= 7
    table.append(value)


def read_uleb128(table: bytes, entry_offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if entry_offset >= len(table):
            raise ValueError("truncated uleb128 offset")
        byte = table[entry_offset]
        entry_offset += 1
        value |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return value, entry_offset
        shift += 7
        if shift > 35:
            raise ValueError("uleb128 offset is too large")


def encode_offset(table: bytearray, mode: dict[str, Any], start: int, previous_start: int) -> None:
    value = start - previous_start if mode["basis"] == "delta" else start
    if value < 0 or value > int(mode["max"]):
        raise ValueError(f"offset does not fit {mode['name']}")
    encoding = mode.get("encoding", "fixed")
    if encoding == "uleb128":
        encode_uleb128(table, value)
    elif encoding == "tiered_u8_or_u16":
        if value < 0xFF:
            table.append(value)
        else:
            table.append(0xFF)
            table.extend(struct.pack(">H", value))
    elif int(mode["bytes"]) == 1:
        table.append(value)
    elif int(mode["bytes"]) == 2:
        table.extend(struct.pack(">H", value))
    else:
        raise ValueError(mode["name"])


def read_offset(table: bytes, mode: dict[str, Any], entry_offset: int, previous_start: int) -> tuple[int, int]:
    encoding = mode.get("encoding", "fixed")
    if encoding == "uleb128":
        value, entry_offset = read_uleb128(table, entry_offset)
        start = previous_start + value if mode["basis"] == "delta" else value
        return start, entry_offset
    if encoding == "tiered_u8_or_u16":
        if entry_offset >= len(table):
            raise ValueError("truncated tiered offset")
        first = table[entry_offset]
        entry_offset += 1
        if first == 0xFF:
            if entry_offset + 2 > len(table):
                raise ValueError("truncated tiered u16 offset")
            value = struct.unpack(">H", table[entry_offset : entry_offset + 2])[0]
            entry_offset += 2
        else:
            value = first
        start = previous_start + value if mode["basis"] == "delta" else value
        return start, entry_offset
    width = int(mode["bytes"])
    if entry_offset + width > len(table):
        raise ValueError("truncated offset table")
    if width == 1:
        value = table[entry_offset]
    elif width == 2:
        value = struct.unpack(">H", table[entry_offset : entry_offset + 2])[0]
    else:
        raise ValueError(mode["name"])
    start = previous_start + value if mode["basis"] == "delta" else value
    return start, entry_offset + width


def unique_seed_indexes(selected: list[dict[str, Any]]) -> list[int]:
    output: list[int] = []
    seen: set[int] = set()
    for record in selected:
        seed_index = int(record["seed_index"])
        if seed_index not in seen:
            seen.add(seed_index)
            output.append(seed_index)
    return output


def pack_seed_index(value: int, width: int) -> bytes:
    if value < 0 or value >= (1 << (width * 8)):
        raise ValueError(f"seed index does not fit u{width * 8}")
    return value.to_bytes(width, "big")


def encode_seed_dictionary(
    selected: list[dict[str, Any]],
    mode: dict[str, Any],
) -> tuple[bytes, dict[int, int], int]:
    if mode["kind"] == "global_fixed":
        return b"", {}, int(mode["ref_bytes"])

    seed_width = int(mode["dict_seed_bytes"])
    seeds = unique_seed_indexes(selected)
    if len(seeds) > 256:
        raise ValueError("seed dictionary does not fit u8 local indexes")
    dictionary = bytearray()
    dictionary.extend(len(seeds).to_bytes(2, "big"))
    for seed_index in seeds:
        if seed_index > int(mode["max_seed_index"]):
            raise ValueError(f"seed index does not fit u{seed_width * 8}")
        dictionary.extend(pack_seed_index(seed_index, seed_width))
    local_by_global = {seed_index: idx for idx, seed_index in enumerate(seeds)}
    local_width = 0 if len(seeds) <= 1 else 1
    return bytes(dictionary), local_by_global, local_width


def encode_seed_ref(
    table: bytearray,
    record: dict[str, Any],
    mode: dict[str, Any],
    local_by_global: dict[int, int],
    local_width: int,
) -> None:
    seed_index = int(record["seed_index"])
    if mode["kind"] == "global_fixed":
        width = int(mode["ref_bytes"])
        if seed_index > int(mode["max_seed_index"]):
            raise ValueError(f"seed index does not fit u{width * 8}")
        table.extend(pack_seed_index(seed_index, width))
        return
    if local_width == 0:
        return
    local_index = local_by_global[seed_index]
    if local_index > 0xFF:
        raise ValueError("local seed index does not fit u8")
    table.append(local_index)


def decode_seed_dictionary(
    dictionary: bytes,
    mode: dict[str, Any],
) -> tuple[list[int], int]:
    if mode["kind"] == "global_fixed":
        if dictionary:
            raise ValueError("unexpected seed dictionary")
        return [], int(mode["ref_bytes"])
    if len(dictionary) < 2:
        raise ValueError("truncated seed dictionary")
    seed_width = int(mode["dict_seed_bytes"])
    count = int.from_bytes(dictionary[:2], "big")
    expected_len = 2 + count * seed_width
    if len(dictionary) != expected_len:
        raise ValueError("seed dictionary length mismatch")
    seeds = [
        int.from_bytes(dictionary[2 + idx * seed_width : 2 + (idx + 1) * seed_width], "big")
        for idx in range(count)
    ]
    local_width = 0 if count <= 1 else 1
    return seeds, local_width


def read_seed_ref(
    table: bytes,
    table_offset: int,
    mode: dict[str, Any],
    dictionary_seeds: list[int],
    local_width: int,
) -> tuple[int, int]:
    if mode["kind"] == "global_fixed":
        width = int(mode["ref_bytes"])
        if table_offset + width > len(table):
            raise ValueError("truncated global seed table")
        seed_index = int.from_bytes(table[table_offset : table_offset + width], "big")
        return seed_index, table_offset + width
    if not dictionary_seeds:
        raise ValueError("empty seed dictionary")
    if local_width == 0:
        return dictionary_seeds[0], table_offset
    if table_offset >= len(table):
        raise ValueError("truncated local seed table")
    local_index = table[table_offset]
    if local_index >= len(dictionary_seeds):
        raise ValueError("local seed index outside dictionary")
    return dictionary_seeds[local_index], table_offset + 1


def encode_case(
    case: dict[str, Any],
    coder: str,
    offset_mode: dict[str, Any],
    seed_mode: dict[str, Any],
) -> dict[str, Any]:
    original: bytes = case["original"]
    transformed: bytes = case["transformed"]
    selected: list[dict[str, Any]] = case["selected"]
    transform_bytes = generate_experimental_sidecar_descriptor.transform_descriptor(
        case["transform"]
    )
    residual_payload = bytes.fromhex(
        "".join(row["residual_hex"] for row in selected)
    )
    compressed_payload = generate_packed_sidecar_descriptor.compress_payload(
        coder,
        residual_payload,
    )
    seed_dictionary, local_by_global, seed_local_index_width = encode_seed_dictionary(
        selected,
        seed_mode,
    )

    literal_stream = bytearray()
    table = bytearray()
    cursor = 0
    previous_start = 0
    max_offset_value = 0
    max_absolute_start = 0
    max_seed_index = 0
    offset_table_bytes = 0
    seed_index_stream_bytes = 0
    offset_uleb_1byte_count = 0
    offset_uleb_2byte_count = 0
    offset_escape_count = 0
    for record in selected:
        start = record["start_offset"]
        value = start - previous_start if offset_mode["basis"] == "delta" else start
        max_offset_value = max(max_offset_value, value)
        max_absolute_start = max(max_absolute_start, start)
        max_seed_index = max(max_seed_index, record["seed_index"])
        before_offset = len(table)
        encode_offset(table, offset_mode, start, previous_start)
        offset_width = len(table) - before_offset
        offset_table_bytes += offset_width
        if offset_mode["name"] == "delta_uleb128":
            if offset_width == 1:
                offset_uleb_1byte_count += 1
            elif offset_width == 2:
                offset_uleb_2byte_count += 1
        if offset_mode["name"] == "tiered_delta" and offset_width == 3:
            offset_escape_count += 1
        before_seed = len(table)
        encode_seed_ref(
            table,
            record,
            seed_mode,
            local_by_global,
            seed_local_index_width,
        )
        seed_index_stream_bytes += len(table) - before_seed
        literal_stream.extend(transformed[cursor:start])
        cursor = start + record["span_len"]
        previous_start = start
    literal_stream.extend(transformed[cursor:])

    header = bytearray()
    header.extend(MAGIC)
    header.append(FORMAT_VERSION)
    header.append(CODERS.index(coder) + 1)
    header.append(int(offset_mode["id"]))
    header.append(int(seed_mode["id"]))
    header.append(len(transform_bytes))
    header.extend(transform_bytes)
    header.extend(struct.pack(">I", len(original)))
    header.extend(struct.pack(">I", len(transformed)))
    header.extend(struct.pack(">I", len(selected)))
    header.extend(struct.pack(">I", len(seed_dictionary)))
    header.extend(struct.pack(">I", len(literal_stream)))
    header.extend(struct.pack(">I", len(table)))
    header.extend(struct.pack(">I", len(compressed_payload)))
    header.extend(hashlib.sha256(original).digest())
    header.extend(hashlib.sha256(transformed).digest())

    encoded = (
        bytes(header)
        + seed_dictionary
        + bytes(table)
        + bytes(literal_stream)
        + compressed_payload
    )
    decoded = decode_descriptor(encoded, case["transform"])
    corrupt = corrupt_rejections(encoded, case["transform"])
    return {
        "name": case["name"],
        "coder": coder,
        "offset_mode": offset_mode["name"],
        "seed_mode": seed_mode["name"],
        "input_bytes": len(original),
        "encoded_bytes": len(encoded),
        "delta_bytes": len(encoded) - len(original),
        "delta_pct": (len(encoded) - len(original)) / len(original) * 100,
        "decode_verified": decoded == original,
        "corrupt_rejections": corrupt,
        "selected_span_count": len(selected),
        "span_len": SPAN_LEN,
        "prefix_len": PREFIX_LEN,
        "literal_stream_bytes": len(literal_stream),
        "offset_table_bytes": offset_table_bytes,
        "seed_dictionary_bytes": len(seed_dictionary),
        "seed_index_stream_bytes": seed_index_stream_bytes,
        "table_bytes": len(table),
        "raw_residual_payload_bytes": len(residual_payload),
        "compressed_payload_bytes": len(compressed_payload),
        "transform_descriptor_bytes": len(transform_bytes),
        "mode_descriptor_bytes": 2 + len(seed_dictionary),
        "header_bytes": len(header),
        "max_offset_delta": max_offset_value,
        "max_absolute_start": max_absolute_start,
        "offset_uleb_1byte_count": offset_uleb_1byte_count,
        "offset_uleb_2byte_count": offset_uleb_2byte_count,
        "offset_escape_count": offset_escape_count,
        "unique_seed_count": len(unique_seed_indexes(selected)),
        "max_seed_index": max_seed_index,
        "seed_local_index_width": seed_local_index_width,
        "seed_const_index": (
            unique_seed_indexes(selected)[0]
            if len(unique_seed_indexes(selected)) == 1
            else None
        ),
        "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
        "output_sha256": hashlib.sha256(decoded).hexdigest() if decoded == original else None,
    }


def decode_descriptor(encoded: bytes, transform: dict[str, Any]) -> bytes:
    if len(encoded) < 4 or encoded[:4] != MAGIC:
        raise ValueError("invalid generalized descriptor magic")
    offset = 4
    version = encoded[offset]
    offset += 1
    if version != FORMAT_VERSION:
        raise ValueError("unsupported generalized descriptor version")
    coder_id = encoded[offset]
    offset += 1
    if coder_id < 1 or coder_id > len(CODERS):
        raise ValueError("unsupported generalized descriptor coder")
    coder = CODERS[coder_id - 1]
    mode_id = encoded[offset]
    offset += 1
    offset_mode = offset_mode_by_id(mode_id)
    seed_mode_id = encoded[offset]
    offset += 1
    seed_mode = seed_mode_by_id(seed_mode_id)
    transform_len = encoded[offset]
    offset += 1 + transform_len
    (
        original_len,
        transformed_len,
        selected_count,
        dictionary_len,
        literal_len,
        table_len,
        payload_len,
    ) = (
        struct.unpack(">IIIIIII", encoded[offset : offset + 28])
    )
    offset += 28
    original_hash = encoded[offset : offset + 32]
    offset += 32
    transformed_hash = encoded[offset : offset + 32]
    offset += 32
    dictionary_start = offset
    table_start = dictionary_start + dictionary_len
    literal_start = table_start + table_len
    payload_start = literal_start + literal_len
    payload_end = payload_start + payload_len
    if payload_end != len(encoded):
        raise ValueError("generalized descriptor length mismatch")
    dictionary = encoded[dictionary_start:table_start]
    table = encoded[table_start:literal_start]
    dictionary_seeds, seed_local_index_width = decode_seed_dictionary(
        dictionary,
        seed_mode,
    )
    literal_stream = encoded[literal_start:payload_start]
    residual_payload = generate_packed_sidecar_descriptor.decompress_payload(
        coder,
        encoded[payload_start:payload_end],
    )
    seeds = seed_table()

    out = bytearray()
    literal_offset = 0
    residual_offset = 0
    previous_start = 0
    table_offset = 0
    for _ in range(selected_count):
        start, table_offset = read_offset(table, offset_mode, table_offset, previous_start)
        seed_index, table_offset = read_seed_ref(
            table,
            table_offset,
            seed_mode,
            dictionary_seeds,
            seed_local_index_width,
        )
        if seed_index >= len(seeds):
            raise ValueError("seed index outside enumeration")
        if start < len(out):
            raise ValueError("overlapping generalized sidecar span")
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
    if table_offset != len(table) or residual_offset != len(residual_payload):
        raise ValueError("generalized descriptor accounting mismatch")
    transformed = bytes(out)
    if len(transformed) != transformed_len:
        raise ValueError("generalized transformed length mismatch")
    if hashlib.sha256(transformed).digest() != transformed_hash:
        raise ValueError("generalized transformed hash mismatch")
    original = generate_experimental_sidecar_descriptor.invert_transform(
        transformed,
        transform,
    )
    if len(original) != original_len:
        raise ValueError("generalized original length mismatch")
    if hashlib.sha256(original).digest() != original_hash:
        raise ValueError("generalized original hash mismatch")
    return original


def corrupt_rejections(encoded: bytes, transform: dict[str, Any]) -> dict[str, bool]:
    mutations = {
        "bad_magic": bytearray(encoded),
        "truncated": bytearray(encoded[:-1]),
        "unsupported_seed_mode": bytearray(encoded),
        "dictionary_bitflip": bytearray(encoded),
        "table_bitflip": bytearray(encoded),
        "payload_bitflip": bytearray(encoded),
    }
    mutations["bad_magic"][0] ^= 0xFF
    mutations["unsupported_seed_mode"][7] = 0xFE
    # The table starts after the fixed header and variable transform descriptor.
    transform_len = encoded[8]
    dictionary_len_offset = 9 + transform_len + 12
    dictionary_len = struct.unpack(
        ">I",
        encoded[dictionary_len_offset : dictionary_len_offset + 4],
    )[0]
    dictionary_start = 9 + transform_len + 28 + 64
    table_start = dictionary_start + dictionary_len
    if dictionary_len:
        mutations["dictionary_bitflip"][dictionary_start] ^= 0x01
    else:
        mutations["dictionary_bitflip"][table_start] ^= 0x01
    mutations["table_bitflip"][table_start] ^= 0x01
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
    rows: list[dict[str, Any]] = []
    for source in source_rows():
        case = generate_experimental_sidecar_descriptor.selected_case(source["name"])
        for coder in CODERS:
            for offset_mode in OFFSET_MODES:
                for seed_mode in SEED_MODES:
                    mode_pair = f"{offset_mode['name']}+{seed_mode['name']}"
                    try:
                        descriptor = encode_case(
                            case,
                            coder,
                            offset_mode,
                            seed_mode,
                        )
                    except ValueError as exc:
                        rows.append(
                            {
                                "name": source["name"],
                                "coder": coder,
                                "offset_mode": offset_mode["name"],
                                "seed_mode": seed_mode["name"],
                                "mode_pair": mode_pair,
                                "role": source["role"],
                                "control_kind": source["control_kind"],
                                "corpus": source["corpus"],
                                "transform": source["transform"],
                                "encoded": False,
                                "skip_reason": str(exc),
                                "input_bytes": len(case["original"]),
                                "encoded_bytes": None,
                                "delta_bytes": None,
                                "selected_span_count": source["selected_span_count"],
                                "decode_verified": False,
                                "corrupt_rejections": {},
                            }
                        )
                        continue
                    rows.append(
                        {
                            **descriptor,
                            "mode_pair": mode_pair,
                            "role": source["role"],
                            "control_kind": source["control_kind"],
                            "corpus": source["corpus"],
                            "transform": source["transform"],
                            "encoded": True,
                            "skip_reason": None,
                        }
                    )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    encoded_rows = [row for row in rows if row["encoded"]]
    negative_rows = [row for row in encoded_rows if row["delta_bytes"] < 0]
    unique_negative_cases = {row["name"] for row in negative_rows}
    unique_encoded_cases = {row["name"] for row in encoded_rows}
    best_by_source_coder: dict[tuple[str, str], dict[str, Any]] = {}
    for row in encoded_rows:
        key = (row["name"], row["coder"])
        current = best_by_source_coder.get(key)
        if current is None or row["delta_bytes"] < current["delta_bytes"]:
            best_by_source_coder[key] = row
    best_of_supported_rows = list(best_by_source_coder.values())
    best_of_supported_negative_cases = {
        row["name"] for row in best_of_supported_rows if row["delta_bytes"] < 0
    }
    ordinary_best_negative_cases = {
        row["name"]
        for row in best_of_supported_rows
        if row["delta_bytes"] < 0
        and row["role"] == "held-out"
        and row["control_kind"] == "ordinary-structured"
    }
    ordinary_heldout_negative_cases = {
        row["name"]
        for row in negative_rows
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    encoded_by_mode = Counter(row["offset_mode"] for row in encoded_rows)
    encoded_by_seed_mode = Counter(row["seed_mode"] for row in encoded_rows)
    negative_by_mode = Counter(row["offset_mode"] for row in negative_rows)
    negative_by_seed_mode = Counter(row["seed_mode"] for row in negative_rows)
    negative_by_mode_pair = Counter(row["mode_pair"] for row in negative_rows)
    negative_by_role = Counter(row["role"] for row in negative_rows)
    negative_by_control = Counter(row["control_kind"] for row in negative_rows)
    best = min(encoded_rows, key=lambda row: row["delta_bytes"])
    baseline_rows = [
        row
        for row in encoded_rows
        if row["offset_mode"] == "delta_u16" and row["seed_mode"] == "global_u16"
    ]
    return {
        "row_count": len(rows),
        "encoded_rows": len(encoded_rows),
        "skipped_rows": len(rows) - len(encoded_rows),
        "unique_source_rows": len({row["name"] for row in rows}),
        "unique_encoded_source_rows": len(unique_encoded_cases),
        "decode_verified_rows": sum(1 for row in encoded_rows if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in encoded_rows
        ),
        "full_stream_negative_rows": len(negative_rows),
        "unique_negative_cases": len(unique_negative_cases),
        "ordinary_heldout_negative_cases": len(ordinary_heldout_negative_cases),
        "best_of_supported_mode_rows": len(best_of_supported_rows),
        "best_of_supported_unique_negative_cases": len(best_of_supported_negative_cases),
        "best_of_supported_ordinary_heldout_negative_cases": len(
            ordinary_best_negative_cases
        ),
        "encoded_rows_by_mode": dict(encoded_by_mode),
        "encoded_rows_by_seed_mode": dict(encoded_by_seed_mode),
        "negative_rows_by_mode": dict(negative_by_mode),
        "negative_rows_by_seed_mode": dict(negative_by_seed_mode),
        "negative_rows_by_mode_pair": dict(negative_by_mode_pair),
        "negative_rows_by_role": dict(negative_by_role),
        "negative_rows_by_control_kind": dict(negative_by_control),
        "best_of_supported_modes_total_table_bytes": sum(
            row["table_bytes"] + row["seed_dictionary_bytes"]
            for row in best_of_supported_rows
        ),
        "baseline_delta_u16_global_u16_total_table_bytes": sum(
            row["table_bytes"] + row["seed_dictionary_bytes"]
            for row in baseline_rows
        ),
        "best_case": best["name"],
        "best_coder": best["coder"],
        "best_offset_mode": best["offset_mode"],
        "best_seed_mode": best["seed_mode"],
        "best_delta_bytes": best["delta_bytes"],
        "conclusion": (
            "Generalized packed sidecars encode most rows and keep ordinary held-out negative cases alive."
            if len(ordinary_best_negative_cases) > 1
            else "Generalized packed sidecars encode more rows but still do not prove broad held-out viability."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if row["encoded"]],
        key=lambda row: row["delta_bytes"],
    )[:limit]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_generalized_packed_sidecar.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    GENERALIZED_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Generalized Packed Sidecar",
        "",
        "Generated by `scripts/generate_generalized_packed_sidecar.py`.",
        "This is a generalized packed descriptor matrix, not `.tlmr` format support.",
        "",
        f"Rows: `{summary['row_count']}`.",
        f"Encoded rows: `{summary['encoded_rows']}`.",
        f"Skipped rows: `{summary['skipped_rows']}`.",
        f"Unique source rows: `{summary['unique_source_rows']}`.",
        f"Unique encoded source rows: `{summary['unique_encoded_source_rows']}`.",
        f"Decode verified rows: `{summary['decode_verified_rows']}`.",
        f"All corrupt rejections passed: `{summary['all_corrupt_rejections_passed']}`.",
        f"Full-stream negative rows: `{summary['full_stream_negative_rows']}`.",
        f"Unique negative cases: `{summary['unique_negative_cases']}`.",
        f"Ordinary held-out negative cases: `{summary['ordinary_heldout_negative_cases']}`.",
        f"Best-of-supported ordinary held-out negative cases: `{summary['best_of_supported_ordinary_heldout_negative_cases']}`.",
        f"Best case: `{summary['best_case']}`.",
        f"Best mode: `{summary['best_offset_mode']}`.",
        f"Best seed mode: `{summary['best_seed_mode']}`.",
        f"Best delta bytes: `{summary['best_delta_bytes']}`.",
        f"Best-of-supported table bytes: `{summary['best_of_supported_modes_total_table_bytes']}`.",
        f"Baseline delta_u16/global_u16 table bytes: `{summary['baseline_delta_u16_global_u16_total_table_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Offset Mode Summary",
        "",
        "| mode | encoded rows | negative rows |",
        "| --- | ---: | ---: |",
    ]
    for mode in [item["name"] for item in OFFSET_MODES]:
        lines.append(
            f"| {mode} | {summary['encoded_rows_by_mode'].get(mode, 0)} | "
            f"{summary['negative_rows_by_mode'].get(mode, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Seed Mode Summary",
            "",
            "| seed mode | encoded rows | negative rows |",
            "| --- | ---: | ---: |",
        ]
    )
    for mode in [item["name"] for item in SEED_MODES]:
        lines.append(
            f"| {mode} | {summary['encoded_rows_by_seed_mode'].get(mode, 0)} | "
            f"{summary['negative_rows_by_seed_mode'].get(mode, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Best Rows",
            "",
            "| row | role | control | coder | offset | seed | input | encoded | delta | spans | table | dict | decode | corrupt rejected |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {role} | {control_kind} | {coder} | {offset_mode} | {seed_mode} | "
            "{input_bytes} | {encoded_bytes} | {delta_bytes} | "
            "{selected_span_count} | {table_bytes} | {seed_dictionary_bytes} | "
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
            "- Wider offset modes remove the strict u8-delta skip condition and make the packed descriptor applicable to most selected rows.",
            "- The negative cases remain concentrated; this is still research evidence, not `.tlmr` format support.",
            "- A promotion path needs multiple unrelated ordinary held-out negative cases and stable descriptor assumptions.",
            "- The stop condition is that wider modes improve encodability but do not improve held-out negative-case diversity.",
        ]
    )
    GENERALIZED_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not GENERALIZED_JSON.exists() or not GENERALIZED_MD.exists():
        raise SystemExit("generated generalized packed sidecar files are missing")
    payload = load_json(GENERALIZED_JSON)
    if payload.get("generated_by") != "scripts/generate_generalized_packed_sidecar.py":
        raise SystemExit("generalized_packed_sidecar.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("generalized packed sidecar artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("generalized packed sidecar manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("decode_verified_rows") != summary.get("encoded_rows"):
        raise SystemExit("generalized packed sidecar decode verification failed")
    if not summary.get("all_corrupt_rejections_passed"):
        raise SystemExit("generalized packed sidecar corrupt rejection failed")
    text = GENERALIZED_MD.read_text(encoding="utf-8")
    for phrase in (
        "Generalized Packed Sidecar",
        "generalized packed descriptor matrix",
        "Wider offset modes",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"GENERALIZED_PACKED_SIDECAR.md missing phrase: {phrase}")


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
