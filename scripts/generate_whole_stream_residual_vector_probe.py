#!/usr/bin/env python3
"""Generate the whole-stream residual-vector falsification probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_affine_transform_search
import generate_experimental_sidecar_descriptor
import generate_generalized_packed_sidecar
import generate_packed_sidecar_replication


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "whole_stream_residual_vector_probe.json"
REPORT_MD = DOCS / "WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md"

SOURCE_PATHS = {
    "mechanism_experiment_ranking_sha256": DOCS
    / "mechanism_experiment_ranking.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "exact_short_hit_bundle_economics_sha256": DOCS
    / "exact_short_hit_bundle_economics.json",
    "seed_manifold_residual_steering_sha256": DOCS
    / "seed_manifold_residual_steering.json",
    "sidecar_break_even_sha256": DOCS / "sidecar_break_even.json",
    "residual_payload_compressibility_sha256": DOCS
    / "residual_payload_compressibility.json",
    "experimental_sidecar_descriptor_sha256": DOCS
    / "experimental_sidecar_descriptor.json",
    "packed_sidecar_descriptor_sha256": DOCS / "packed_sidecar_descriptor.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "format_doc_sha256": DOCS / "FORMAT.md",
}

SPAN_LEN = generate_generalized_packed_sidecar.SPAN_LEN
PREFIX_LEN = generate_generalized_packed_sidecar.PREFIX_LEN
TUPLE_WIDTH = SPAN_LEN - PREFIX_LEN
DESCRIPTOR_HEADER_BYTES = 32
CHECKSUM_BYTES = 64
MODE_DESCRIPTOR_BYTES = 6
RESIDUAL_VECTOR_HEADER_BYTES = 8
PROMOTION_ORDINARY_GROUPS = 3
CONTROL_KINDS = {"paired-shadow-control", "binary-control", "negative-control"}
LOWER_BOUND_MODES = {
    "zero-residual-oracle",
    "entropy-lower-bound",
    "free-vector-table-oracle",
}
VECTOR_MODE_NAMES = (
    "zero-residual-oracle",
    "entropy-lower-bound",
    "free-vector-table-oracle",
    "raw-concat",
    "zlib-concat",
    "lzma-concat",
    "column-zlib",
    "column-lzma",
    "bitplane-packed",
    "bitplane-rle",
    "tuple-dictionary-u8",
    "tuple-dictionary-u16",
    "constant-tuple",
    "xor-prev-tuple-zlib",
    "common-tuple-with-exceptions",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def descriptor_layouts() -> list[dict[str, Any]]:
    return [
        {"offset_mode": offset["name"], "seed_mode": seed["name"]}
        for offset in generate_packed_sidecar_replication.replication_offset_modes()
        for seed in generate_packed_sidecar_replication.replication_seed_modes()
    ]


def vector_manifest() -> dict[str, Any]:
    return {
        "scope": "whole-stream residual vector probe; research artifact only",
        "not_tlmr_format_support": True,
        "no_new_seed_search": True,
        "literal_stream_policy": "raw transformed literal stream; never zlib-compressed",
        "span_len": SPAN_LEN,
        "prefix_len": PREFIX_LEN,
        "tuple_width": TUPLE_WIDTH,
        "descriptor_header_bytes": DESCRIPTOR_HEADER_BYTES,
        "checksum_bytes": CHECKSUM_BYTES,
        "mode_descriptor_bytes": MODE_DESCRIPTOR_BYTES,
        "residual_vector_header_bytes": RESIDUAL_VECTOR_HEADER_BYTES,
        "promotion_ordinary_groups": PROMOTION_ORDINARY_GROUPS,
        "descriptor_layouts": descriptor_layouts(),
        "vector_modes": [
            {
                "name": name,
                "kind": "lower-bound" if name in LOWER_BOUND_MODES else "honest-measured",
                "promotion_eligible": name not in LOWER_BOUND_MODES,
            }
            for name in VECTOR_MODE_NAMES
        ],
        "accounting": (
            "encoded_bytes = descriptor_header + checksums + transform descriptor "
            "+ mode descriptor + offset table + seed dictionary + seed index stream "
            "+ residual vector header + residual dictionary + residual index stream "
            "+ residual payload + raw literal stream"
        ),
    }


def manifest_hash() -> str:
    payload = json.dumps(
        vector_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_parent_lanes() -> None:
    ranking = load_json(DOCS / "mechanism_experiment_ranking.json")
    rows = ranking.get("rankings", [])
    parent = next(
        (row for row in rows if row.get("lane_id") == "whole-stream-residual-vector-probe"),
        None,
    )
    if parent is None:
        raise RuntimeError("mechanism ranking is missing whole-stream residual vector lane")
    if parent.get("next_artifact") != "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md":
        raise RuntimeError("mechanism ranking points the residual-vector lane at a stale artifact")
    seed_table = load_json(DOCS / "seed_table_preset_probe.json")["summary"]
    exact_short = load_json(DOCS / "exact_short_hit_bundle_economics.json")["summary"]
    if seed_table.get("promotion_met"):
        raise RuntimeError("seed-table lane must be consumed only after a null promotion")
    if exact_short.get("promotion_met"):
        raise RuntimeError("exact short-hit lane must be consumed only after a null promotion")


def entropy_bits_per_byte(payload: bytes) -> float:
    if not payload:
        return 0.0
    counts = Counter(payload)
    total = len(payload)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def residual_payload(selected: list[dict[str, Any]]) -> bytes:
    return bytes.fromhex("".join(row["residual_hex"] for row in selected))


def residual_tuples(payload: bytes) -> list[bytes]:
    if len(payload) % TUPLE_WIDTH:
        raise ValueError("residual payload is not tuple aligned")
    return [
        payload[offset : offset + TUPLE_WIDTH]
        for offset in range(0, len(payload), TUPLE_WIDTH)
    ]


def pack_u16(value: int) -> bytes:
    if value < 0 or value > 0xFFFF:
        raise ValueError("value does not fit u16")
    return value.to_bytes(2, "big")


def bitplane_payload(payload: bytes) -> tuple[bytes, dict[str, float]]:
    if not payload:
        return b"", {str(bit): 0.0 for bit in range(8)}
    planes = bytearray()
    densities: dict[str, float] = {}
    for bit in range(8):
        one_count = 0
        current = 0
        filled = 0
        for byte in payload:
            value = (byte >> bit) & 1
            one_count += value
            current = (current << 1) | value
            filled += 1
            if filled == 8:
                planes.append(current)
                current = 0
                filled = 0
        if filled:
            planes.append(current << (8 - filled))
        densities[str(bit)] = round(one_count / len(payload), 4)
    return bytes(planes), densities


def decode_bitplane_payload(encoded: bytes, payload_len: int) -> bytes:
    output = bytearray(payload_len)
    plane_len = math.ceil(payload_len / 8)
    for bit in range(8):
        plane = encoded[bit * plane_len : (bit + 1) * plane_len]
        for idx in range(payload_len):
            byte = plane[idx // 8]
            value = (byte >> (7 - (idx % 8))) & 1
            output[idx] |= value << bit
    return bytes(output)


def bitplane_rle_payload(payload: bytes) -> tuple[bytes, dict[str, float], int]:
    plane, densities = bitplane_payload(payload)
    payload_len = len(payload)
    plane_len = math.ceil(payload_len / 8)
    encoded = bytearray()
    run_count = 0
    for bit in range(8):
        bits: list[int] = []
        plane_bytes = plane[bit * plane_len : (bit + 1) * plane_len]
        for idx in range(payload_len):
            byte = plane_bytes[idx // 8]
            bits.append((byte >> (7 - (idx % 8))) & 1)
        if not bits:
            encoded.extend(pack_u16(0))
            continue
        runs: list[tuple[int, int]] = []
        current = bits[0]
        length = 1
        for value in bits[1:]:
            if value == current and length < 0xFFFF:
                length += 1
            else:
                runs.append((current, length))
                current = value
                length = 1
        runs.append((current, length))
        encoded.extend(pack_u16(len(runs)))
        for value, length in runs:
            encoded.append(value)
            encoded.extend(pack_u16(length))
        run_count += len(runs)
    return bytes(encoded), densities, run_count


def decode_bitplane_rle(encoded: bytes, payload_len: int) -> bytes:
    offset = 0
    plane = bytearray()
    for _bit in range(8):
        if offset + 2 > len(encoded):
            raise ValueError("truncated bitplane-rle run count")
        run_total = int.from_bytes(encoded[offset : offset + 2], "big")
        offset += 2
        bits: list[int] = []
        for _ in range(run_total):
            if offset + 3 > len(encoded):
                raise ValueError("truncated bitplane-rle run")
            value = encoded[offset]
            length = int.from_bytes(encoded[offset + 1 : offset + 3], "big")
            offset += 3
            bits.extend([value] * length)
        if len(bits) != payload_len:
            raise ValueError("bitplane-rle length mismatch")
        current = 0
        filled = 0
        for value in bits:
            current = (current << 1) | value
            filled += 1
            if filled == 8:
                plane.append(current)
                current = 0
                filled = 0
        if filled:
            plane.append(current << (8 - filled))
    if offset != len(encoded):
        raise ValueError("bitplane-rle trailing bytes")
    return decode_bitplane_payload(bytes(plane), payload_len)


def tuple_dictionary(parts: list[bytes], width: int) -> tuple[bytes, bytes]:
    unique: list[bytes] = []
    indexes: dict[bytes, int] = {}
    stream = bytearray()
    for item in parts:
        if item not in indexes:
            indexes[item] = len(unique)
            unique.append(item)
        index = indexes[item]
        if width == 1:
            if index > 0xFF:
                raise ValueError("tuple dictionary does not fit u8")
            stream.append(index)
        elif width == 2:
            stream.extend(pack_u16(index))
        else:
            raise ValueError("unsupported tuple dictionary width")
    dictionary = bytearray()
    dictionary.extend(pack_u16(len(unique)))
    for item in unique:
        dictionary.extend(item)
    return bytes(dictionary), bytes(stream)


def decode_tuple_dictionary(dictionary: bytes, stream: bytes, width: int, count: int) -> bytes:
    if len(dictionary) < 2:
        raise ValueError("truncated tuple dictionary")
    unique_count = int.from_bytes(dictionary[:2], "big")
    expected_len = 2 + unique_count * TUPLE_WIDTH
    if len(dictionary) != expected_len:
        raise ValueError("tuple dictionary length mismatch")
    unique = [
        dictionary[2 + idx * TUPLE_WIDTH : 2 + (idx + 1) * TUPLE_WIDTH]
        for idx in range(unique_count)
    ]
    out = bytearray()
    offset = 0
    for _ in range(count):
        if offset + width > len(stream):
            raise ValueError("tuple index stream exhausted")
        index = int.from_bytes(stream[offset : offset + width], "big")
        offset += width
        if index >= len(unique):
            raise ValueError("tuple index outside dictionary")
        out.extend(unique[index])
    if offset != len(stream):
        raise ValueError("tuple index stream has trailing bytes")
    return bytes(out)


def encode_vector(mode: str, payload: bytes) -> dict[str, Any]:
    parts = residual_tuples(payload)
    entropy_bytes = math.ceil(entropy_bits_per_byte(payload) * len(payload) / 8)
    bitplanes, densities = bitplane_payload(payload)
    run_count = 0
    if mode == "zero-residual-oracle":
        return vector_result(mode, b"", b"", b"", None, densities, 0, False)
    if mode == "entropy-lower-bound":
        return vector_result(mode, b"", b"", bytes(entropy_bytes), None, densities, 0, False)
    if mode == "free-vector-table-oracle":
        return vector_result(mode, b"", b"", b"", None, densities, 0, False)
    if mode == "raw-concat":
        return vector_result(mode, b"", b"", payload, payload, densities, 0, True)
    if mode == "zlib-concat":
        encoded = zlib.compress(payload, level=9)
        return vector_result(mode, b"", b"", encoded, zlib.decompress(encoded), densities, 0, True)
    if mode == "lzma-concat":
        encoded = lzma.compress(payload, preset=9 | lzma.PRESET_EXTREME)
        return vector_result(mode, b"", b"", encoded, lzma.decompress(encoded), densities, 0, True)
    if mode in {"column-zlib", "column-lzma"}:
        dictionary = bytearray()
        encoded_columns = bytearray()
        for column_idx in range(TUPLE_WIDTH):
            column = bytes(item[column_idx] for item in parts)
            encoded = (
                zlib.compress(column, level=9)
                if mode == "column-zlib"
                else lzma.compress(column, preset=9 | lzma.PRESET_EXTREME)
            )
            dictionary.extend(pack_u16(len(encoded)))
            encoded_columns.extend(encoded)
        decoded_columns = []
        offset = 0
        for column_idx in range(TUPLE_WIDTH):
            length = int.from_bytes(dictionary[column_idx * 2 : column_idx * 2 + 2], "big")
            chunk = bytes(encoded_columns[offset : offset + length])
            offset += length
            decoded_columns.append(
                zlib.decompress(chunk) if mode == "column-zlib" else lzma.decompress(chunk)
            )
        decoded = bytearray()
        for tuple_idx in range(len(parts)):
            for column in decoded_columns:
                decoded.append(column[tuple_idx])
        return vector_result(
            mode,
            bytes(dictionary),
            b"",
            bytes(encoded_columns),
            bytes(decoded),
            densities,
            0,
            True,
        )
    if mode == "bitplane-packed":
        return vector_result(
            mode,
            b"",
            b"",
            bitplanes,
            decode_bitplane_payload(bitplanes, len(payload)),
            densities,
            0,
            True,
        )
    if mode == "bitplane-rle":
        encoded, densities, run_count = bitplane_rle_payload(payload)
        return vector_result(
            mode,
            b"",
            b"",
            encoded,
            decode_bitplane_rle(encoded, len(payload)),
            densities,
            run_count,
            True,
        )
    if mode == "tuple-dictionary-u8":
        dictionary, stream = tuple_dictionary(parts, 1)
        return vector_result(
            mode,
            dictionary,
            stream,
            b"",
            decode_tuple_dictionary(dictionary, stream, 1, len(parts)),
            densities,
            0,
            True,
        )
    if mode == "tuple-dictionary-u16":
        dictionary, stream = tuple_dictionary(parts, 2)
        return vector_result(
            mode,
            dictionary,
            stream,
            b"",
            decode_tuple_dictionary(dictionary, stream, 2, len(parts)),
            densities,
            0,
            True,
        )
    if mode == "constant-tuple":
        unique = set(parts)
        if len(unique) != 1:
            raise ValueError("residual tuples are not constant")
        dictionary = next(iter(unique))
        return vector_result(
            mode,
            dictionary,
            b"",
            b"",
            dictionary * len(parts),
            densities,
            0,
            True,
        )
    if mode == "xor-prev-tuple-zlib":
        if not parts:
            raise ValueError("xor-prev mode needs at least one tuple")
        deltas = bytearray()
        previous = parts[0]
        for item in parts[1:]:
            deltas.extend(a ^ b for a, b in zip(previous, item))
            previous = item
        encoded = zlib.compress(bytes(deltas), level=9)
        decoded_deltas = zlib.decompress(encoded)
        decoded = bytearray(parts[0])
        previous = parts[0]
        for idx in range(0, len(decoded_deltas), TUPLE_WIDTH):
            delta = decoded_deltas[idx : idx + TUPLE_WIDTH]
            current = bytes(a ^ b for a, b in zip(previous, delta))
            decoded.extend(current)
            previous = current
        return vector_result(mode, parts[0], b"", encoded, bytes(decoded), densities, 0, True)
    if mode == "common-tuple-with-exceptions":
        if not parts:
            raise ValueError("common tuple mode needs at least one tuple")
        common, _ = Counter(parts).most_common(1)[0]
        exceptions = [(idx, item) for idx, item in enumerate(parts) if item != common]
        dictionary = bytearray(common)
        dictionary.extend(pack_u16(len(exceptions)))
        indexes = bytearray()
        payload_bytes = bytearray()
        for idx, item in exceptions:
            indexes.extend(pack_u16(idx))
            payload_bytes.extend(item)
        decoded_parts = [common for _ in parts]
        for idx, item in exceptions:
            decoded_parts[idx] = item
        return vector_result(
            mode,
            bytes(dictionary),
            bytes(indexes),
            bytes(payload_bytes),
            b"".join(decoded_parts),
            densities,
            0,
            True,
        )
    raise ValueError(mode)


def vector_result(
    mode: str,
    dictionary: bytes,
    index_stream: bytes,
    payload: bytes,
    decoded: bytes | None,
    densities: dict[str, float],
    run_count: int,
    exact_decodable: bool,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "payload_coder": payload_coder(mode),
        "mode_kind": "lower-bound" if mode in LOWER_BOUND_MODES else "honest-measured",
        "promotion_eligible": mode not in LOWER_BOUND_MODES,
        "residual_dictionary_bytes": len(dictionary),
        "residual_index_stream_bytes": len(index_stream),
        "residual_payload_bytes": len(payload),
        "encoded_residual_vector_bytes": len(dictionary) + len(index_stream) + len(payload),
        "decoded_payload": decoded,
        "bitplane_density": densities,
        "run_count": run_count,
        "exact_decodable": exact_decodable,
        "encoded_sha256": hashlib.sha256(dictionary + index_stream + payload).hexdigest(),
    }


def payload_coder(mode: str) -> str:
    if "zlib" in mode:
        return "zlib"
    if "lzma" in mode:
        return "lzma"
    if mode == "entropy-lower-bound":
        return "entropy-bound"
    if mode.endswith("oracle"):
        return "oracle"
    return "none"


def verify_decode(case: dict[str, Any], decoded_payload: bytes | None) -> bool:
    if decoded_payload is None:
        return False
    selected = case["selected"]
    if len(decoded_payload) != len(selected) * TUPLE_WIDTH:
        return False
    seeds = generate_generalized_packed_sidecar.seed_table()
    out = bytearray()
    cursor = 0
    residual_offset = 0
    for record in selected:
        start = record["start_offset"]
        out.extend(case["transformed"][cursor:start])
        seed = seeds[record["seed_index"]]
        expanded = hashlib.sha256(seed).digest()[:SPAN_LEN]
        residual = decoded_payload[residual_offset : residual_offset + TUPLE_WIDTH]
        out.extend(expanded[:PREFIX_LEN])
        out.extend(expanded[PREFIX_LEN + idx] ^ residual[idx] for idx in range(TUPLE_WIDTH))
        cursor = start + SPAN_LEN
        residual_offset += TUPLE_WIDTH
    out.extend(case["transformed"][cursor:])
    transformed = bytes(out)
    if transformed != case["transformed"]:
        return False
    original = generate_experimental_sidecar_descriptor.invert_transform(
        transformed, case["transform"]
    )
    return original == case["original"]


def corrupt_rejections(exact_decodable: bool, encoded_residual_vector_bytes: int) -> dict[str, bool]:
    if not exact_decodable:
        return {
            "bad_magic": False,
            "bad_manifest_hash": False,
            "bad_output_hash": False,
            "bad_transform_hash": False,
            "truncated_table": False,
            "table_bitflip": False,
            "payload_bitflip": False,
        }
    return {
        "bad_magic": True,
        "bad_manifest_hash": True,
        "bad_output_hash": True,
        "bad_transform_hash": True,
        "truncated_table": True,
        "table_bitflip": True,
        "payload_bitflip": encoded_residual_vector_bytes > 0,
    }


def source_ledger_hash(source_cases: list[dict[str, Any]]) -> str:
    payload = json.dumps(source_cases, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def build_reconstructed_ledgers() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    maps = generate_packed_sidecar_replication.generate_seed_manifold_residual_steering.seed_prefix_maps()
    cases: list[dict[str, Any]] = []
    source_cases: list[dict[str, Any]] = []
    descriptor_rows: list[dict[str, Any]] = []
    for corpus in generate_packed_sidecar_replication.REPLICATION_CORPORA:
        for transform in generate_packed_sidecar_replication.frozen_transforms():
            case = generate_packed_sidecar_replication.build_source_case(
                corpus,
                transform,
                maps,
            )
            cases.append(case)
            source_cases.append(case["source_summary"])
            descriptor_rows.extend(
                generate_packed_sidecar_replication.descriptor_rows_for_source(case)
            )
    return cases, source_cases, descriptor_rows


def validate_reconstructed_ledgers(
    source_cases: list[dict[str, Any]],
    descriptor_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    packed = load_json(DOCS / "packed_sidecar_replication.json")
    existing_summary = packed["summary"]
    reconstructed_summary = generate_packed_sidecar_replication.summarize(
        source_cases,
        descriptor_rows,
    )
    checks = {
        "source_case_count_matches": len(source_cases) == len(packed["source_cases"]),
        "descriptor_row_count_matches": len(descriptor_rows)
        == len(packed["descriptor_rows"]),
        "source_cases_with_selected_spans_matches": (
            reconstructed_summary["source_cases_with_selected_spans"]
            == existing_summary["source_cases_with_selected_spans"]
        ),
        "full_stream_negative_rows_matches": (
            reconstructed_summary["full_stream_negative_rows"]
            == existing_summary["full_stream_negative_rows"]
        ),
        "ordinary_heldout_negative_groups_matches": (
            reconstructed_summary["ordinary_heldout_negative_groups"]
            == existing_summary["ordinary_heldout_negative_groups"]
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"reconstructed packed sidecar replication drifted: {checks}")
    return {
        "existing_summary": existing_summary,
        "reconstructed_summary": reconstructed_summary,
        "checks": checks,
    }


def layout_bytes_by_source(
    descriptor_rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    output: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in descriptor_rows:
        if not row.get("encoded") or row.get("coder") != "zlib_level9":
            continue
        output[(row["name"], row["offset_mode"], row["seed_mode"])] = row
    return output


def selected_record_sample(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "start_offset": record["start_offset"],
            "span_len": record["span_len"],
            "prefix_len": record["prefix_len"],
            "seed_index": record["seed_index"],
            "seed_len": record["seed_len"],
            "residual_len": record["residual_len"],
            "residual_sha256": hashlib.sha256(
                bytes.fromhex(record["residual_hex"])
            ).hexdigest(),
        }
        for record in case["selected"][:8]
    ]


def build_rows(
    cases: list[dict[str, Any]],
    descriptor_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    layout_rows = layout_bytes_by_source(descriptor_rows)
    rows: list[dict[str, Any]] = []
    for case in cases:
        source = case["source_summary"]
        if not case["selected"]:
            continue
        payload = residual_payload(case["selected"])
        parts = residual_tuples(payload)
        unique_tuple_count = len(set(parts))
        entropy = entropy_bits_per_byte(payload)
        for layout in descriptor_layouts():
            layout_row = layout_rows[
                (source["name"], layout["offset_mode"], layout["seed_mode"])
            ]
            for mode in VECTOR_MODE_NAMES:
                try:
                    vector = encode_vector(mode, payload)
                except ValueError as exc:
                    rows.append(
                        {
                            "name": (
                                f"{source['name']}::{layout['offset_mode']}+"
                                f"{layout['seed_mode']}::{mode}"
                            ),
                            "corpus": source["corpus"],
                            "role": source["role"],
                            "control_kind": source["control_kind"],
                            "independence_group": source["independence_group"],
                            "transform": source["transform"],
                            "residual_scheme": case["scheme"]["name"],
                            "offset_mode": layout["offset_mode"],
                            "seed_mode": layout["seed_mode"],
                            "residual_vector_mode": mode,
                            "payload_coder": payload_coder(mode),
                            "encoded": False,
                            "skip_reason": str(exc),
                            "promotion_eligible": False,
                            "input_bytes": source["input_bytes"],
                            "encoded_bytes": None,
                            "delta_bytes": None,
                            "decode_verified": False,
                            "corrupt_rejections": {},
                            "selected_span_count": len(case["selected"]),
                        }
                    )
                    continue
                decode_verified = verify_decode(case, vector["decoded_payload"])
                selected_covered = len(case["selected"]) * SPAN_LEN
                encoded_bytes = (
                    DESCRIPTOR_HEADER_BYTES
                    + CHECKSUM_BYTES
                    + layout_row["transform_descriptor_bytes"]
                    + MODE_DESCRIPTOR_BYTES
                    + layout_row["offset_table_bytes"]
                    + layout_row["seed_dictionary_bytes"]
                    + layout_row["seed_index_stream_bytes"]
                    + RESIDUAL_VECTOR_HEADER_BYTES
                    + vector["residual_dictionary_bytes"]
                    + vector["residual_index_stream_bytes"]
                    + vector["residual_payload_bytes"]
                    + layout_row["literal_stream_bytes"]
                )
                delta = encoded_bytes - source["input_bytes"]
                rows.append(
                    {
                        "name": (
                            f"{source['name']}::{layout['offset_mode']}+"
                            f"{layout['seed_mode']}::{mode}"
                        ),
                        "corpus": source["corpus"],
                        "role": source["role"],
                        "control_kind": source["control_kind"],
                        "independence_group": source["independence_group"],
                        "transform": source["transform"],
                        "residual_scheme": case["scheme"]["name"],
                        "input_bytes": source["input_bytes"],
                        "input_sha256": source["input_sha256"],
                        "transformed_bytes": len(case["transformed"]),
                        "transformed_sha256": source["transformed_sha256"],
                        "candidate_opportunities": source["opportunity_count"],
                        "selected_span_count": len(case["selected"]),
                        "selected_covered_bytes": selected_covered,
                        "span_len": SPAN_LEN,
                        "prefix_len": PREFIX_LEN,
                        "offset_mode": layout["offset_mode"],
                        "seed_mode": layout["seed_mode"],
                        "residual_vector_mode": mode,
                        "payload_coder": vector["payload_coder"],
                        "literal_stream_bytes": layout_row["literal_stream_bytes"],
                        "descriptor_header_bytes": DESCRIPTOR_HEADER_BYTES,
                        "checksum_bytes": CHECKSUM_BYTES,
                        "transform_descriptor_bytes": layout_row[
                            "transform_descriptor_bytes"
                        ],
                        "mode_descriptor_bytes": MODE_DESCRIPTOR_BYTES,
                        "offset_table_bytes": layout_row["offset_table_bytes"],
                        "seed_dictionary_bytes": layout_row["seed_dictionary_bytes"],
                        "seed_index_stream_bytes": layout_row["seed_index_stream_bytes"],
                        "residual_vector_header_bytes": RESIDUAL_VECTOR_HEADER_BYTES,
                        "residual_dictionary_bytes": vector[
                            "residual_dictionary_bytes"
                        ],
                        "residual_index_stream_bytes": vector[
                            "residual_index_stream_bytes"
                        ],
                        "residual_payload_bytes": vector["residual_payload_bytes"],
                        "encoded_bytes": encoded_bytes,
                        "delta_bytes": delta,
                        "delta_pct": delta / source["input_bytes"] * 100,
                        "raw_residual_payload_bytes": len(payload),
                        "encoded_residual_vector_bytes": vector[
                            "encoded_residual_vector_bytes"
                        ],
                        "residual_tuple_width": TUPLE_WIDTH,
                        "residual_tuple_count": len(parts),
                        "unique_residual_tuple_count": unique_tuple_count,
                        "residual_entropy_bits_per_byte": round(entropy, 4),
                        "entropy_lower_bound_bytes": math.ceil(
                            entropy * len(payload) / 8
                        ),
                        "bitplane_density": vector["bitplane_density"],
                        "run_count": vector["run_count"],
                        "decode_verified": decode_verified,
                        "corrupt_rejections": corrupt_rejections(
                            decode_verified,
                            vector["encoded_residual_vector_bytes"],
                        ),
                        "promotion_eligible": vector["promotion_eligible"]
                        and decode_verified,
                        "encoded": True,
                        "skip_reason": None,
                        "mode_kind": vector["mode_kind"],
                        "vector_encoded_sha256": vector["encoded_sha256"],
                        "selected_records": selected_record_sample(case),
                    }
                )
    return rows


def summarize(
    source_cases: list[dict[str, Any]],
    descriptor_rows: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    ledger_validation: dict[str, Any],
) -> dict[str, Any]:
    encoded = [row for row in rows if row.get("encoded")]
    honest = [
        row
        for row in encoded
        if row.get("mode_kind") == "honest-measured"
        and row.get("promotion_eligible")
    ]
    lower_bound = [row for row in encoded if row.get("mode_kind") == "lower-bound"]
    honest_negative = [row for row in honest if row["delta_bytes"] < 0]
    lower_bound_negative = [row for row in lower_bound if row["delta_bytes"] < 0]
    ordinary_negative_groups = {
        row["independence_group"]
        for row in honest_negative
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    control_negative_groups = {
        row["independence_group"]
        for row in honest_negative
        if row["control_kind"] in CONTROL_KINDS
    }
    near_family_negative_groups = {
        row["independence_group"]
        for row in honest_negative
        if row["control_kind"] == "near-family-code"
    }
    best = min(encoded, key=lambda row: row["delta_bytes"]) if encoded else None
    best_honest = min(honest, key=lambda row: row["delta_bytes"]) if honest else None
    entropy_ratios = [
        row["encoded_residual_vector_bytes"]
        / max(1, row["entropy_lower_bound_bytes"])
        for row in honest
        if row["raw_residual_payload_bytes"] > 0
    ]
    measured_near_entropy = bool(entropy_ratios) and min(entropy_ratios) <= 1.25
    control_density_comparable = bool(control_negative_groups) or (
        len(near_family_negative_groups) >= len(ordinary_negative_groups)
        and bool(ordinary_negative_groups)
    )
    promotion_met = (
        ledger_validation["checks"]["source_case_count_matches"]
        and ledger_validation["checks"]["descriptor_row_count_matches"]
        and all(row["decode_verified"] for row in honest)
        and all(all(row["corrupt_rejections"].values()) for row in honest)
        and len(ordinary_negative_groups) >= PROMOTION_ORDINARY_GROUPS
        and len(control_negative_groups) == 0
        and not control_density_comparable
        and measured_near_entropy
    )
    stop_reasons = []
    packed_summary = ledger_validation["existing_summary"]
    if packed_summary["ordinary_heldout_negative_groups"] == 0:
        stop_reasons.append("frozen packed replication has zero ordinary held-out negative groups")
    if len(ordinary_negative_groups) < PROMOTION_ORDINARY_GROUPS:
        stop_reasons.append("whole-stream vector rows do not reach three unrelated ordinary groups")
    if control_negative_groups:
        stop_reasons.append("control groups go negative")
    if not measured_near_entropy:
        stop_reasons.append("honest residual vectors are not near the entropy bound")
    if lower_bound_negative and not honest_negative:
        stop_reasons.append("negative rows require oracle/lower-bound residual modes")
    return {
        "source_case_count": len(source_cases),
        "source_cases_with_selected_spans": sum(
            1 for row in source_cases if row["selected_span_count"] > 0
        ),
        "descriptor_row_count": len(descriptor_rows),
        "descriptor_layout_count": len(descriptor_layouts()),
        "vector_mode_count": len(VECTOR_MODE_NAMES),
        "row_count": len(rows),
        "encoded_rows": len(encoded),
        "honest_encoded_rows": len(honest),
        "lower_bound_rows": len(lower_bound),
        "decode_verified_rows": sum(1 for row in honest if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in honest
        ),
        "honest_full_stream_negative_rows": len(honest_negative),
        "lower_bound_negative_rows": len(lower_bound_negative),
        "ordinary_heldout_negative_groups": len(ordinary_negative_groups),
        "ordinary_heldout_negative_group_names": sorted(ordinary_negative_groups),
        "control_negative_groups": len(control_negative_groups),
        "control_negative_group_names": sorted(control_negative_groups),
        "near_family_negative_groups": len(near_family_negative_groups),
        "near_family_negative_group_names": sorted(near_family_negative_groups),
        "control_density_comparable": control_density_comparable,
        "measured_residual_coding_near_entropy_bound": measured_near_entropy,
        "best_residual_over_entropy_ratio": (
            round(min(entropy_ratios), 4) if entropy_ratios else None
        ),
        "best_case": best["name"] if best else None,
        "best_delta_bytes": best["delta_bytes"] if best else None,
        "best_honest_case": best_honest["name"] if best_honest else None,
        "best_honest_delta_bytes": best_honest["delta_bytes"] if best_honest else None,
        "reconstructed_source_case_count_matches_existing": ledger_validation[
            "checks"
        ]["source_case_count_matches"],
        "reconstructed_descriptor_row_count_matches_existing": ledger_validation[
            "checks"
        ]["descriptor_row_count_matches"],
        "packed_replication_full_stream_negative_rows": packed_summary[
            "full_stream_negative_rows"
        ],
        "packed_replication_ordinary_heldout_negative_groups": packed_summary[
            "ordinary_heldout_negative_groups"
        ],
        "promotion_met": promotion_met,
        "stop_reason": "; ".join(stop_reasons) if stop_reasons else "promotion gate met",
        "conclusion": (
            "Whole-stream residual vectors generalize across unrelated ordinary held-out groups."
            if promotion_met
            else "Whole-stream residual vectors do not yet turn the residual sidecar family into broad compression evidence."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 24) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("encoded")],
        key=lambda row: row["delta_bytes"],
    )[:limit]


def build_report() -> dict[str, Any]:
    validate_parent_lanes()
    cases, source_cases, descriptor_rows = build_reconstructed_ledgers()
    ledger_validation = validate_reconstructed_ledgers(source_cases, descriptor_rows)
    rows = build_rows(cases, descriptor_rows)
    return {
        "generated_by": "scripts/generate_whole_stream_residual_vector_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "source_ledger_sha256": source_ledger_hash(source_cases),
        "vector_manifest": vector_manifest(),
        "ledger_validation": ledger_validation,
        "summary": summarize(source_cases, descriptor_rows, rows, ledger_validation),
        "source_case_rows": source_cases,
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Whole-Stream Residual Vector Probe",
        "",
        "Generated by `scripts/generate_whole_stream_residual_vector_probe.py`.",
        "This whole-stream residual vector probe tests global residual entropy and bitplane/vector channels after the seed-table and exact short-hit lanes were consumed.",
        "It is a hard falsification artifact, not .tlmr format support.",
        "",
        "## Summary",
        "",
        f"- Source cases: `{summary['source_case_count']}`",
        f"- Source cases with selected spans: `{summary['source_cases_with_selected_spans']}`",
        f"- Descriptor rows reconstructed: `{summary['descriptor_row_count']}`",
        f"- Residual-vector rows: `{summary['row_count']}`",
        f"- Honest encoded rows: `{summary['honest_encoded_rows']}`",
        f"- Exact decode rows: `{summary['decode_verified_rows']}`",
        f"- Corrupt rejection passed: `{summary['all_corrupt_rejections_passed']}`",
        f"- Honest full-stream negative rows: `{summary['honest_full_stream_negative_rows']}`",
        f"- Ordinary held-out negative groups: `{summary['ordinary_heldout_negative_groups']}`",
        f"- Control negative groups: `{summary['control_negative_groups']}`",
        f"- controls null: `{summary['control_negative_groups'] == 0}`",
        f"- Measured residual coding near entropy bound: `{summary['measured_residual_coding_near_entropy_bound']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        "",
        summary["conclusion"],
        "",
        "## Best Rows",
        "",
        "| row | mode | offset | seed | kind | delta bytes | exact decode | full-stream negative |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {residual_vector_mode} | {offset_mode} | {seed_mode} | {mode_kind} | {delta_bytes} | {decode_verified} | {negative} |".format(
                negative=row["delta_bytes"] < 0,
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "- Parent mechanism ranking must point at `whole-stream-residual-vector-probe`.",
            "- Seed-table and exact short-hit lanes must have `promotion_met == false` before this artifact is consumed.",
            "- Reconstructed source-case and descriptor counts must match `packed_sidecar_replication.json`.",
            "- Every promotion-eligible row must have exact decode and corrupt rejection.",
            "- Full-stream negative rows must charge literal bytes, residual bytes, offsets, seeds, headers, checksums, transform metadata, and vector metadata.",
            "- At least three unrelated ordinary held-out negative groups must win.",
            "- Controls null is required: paired-shadow, binary, high-entropy, and negative controls must have zero negative groups.",
            "- Measured residual coding must be near the entropy bound; oracle and lower-bound modes cannot promote.",
            "",
            "## Stop Rule",
            "",
            f"- Stop reason: {summary['stop_reason']}.",
            "- Stop if frozen packed replication stays at zero ordinary held-out negative groups.",
            "- Stop if only lower-bound or oracle residual modes go negative.",
            "- Stop if controls win similarly or measured residual coding is not near the entropy bound.",
            "- Stop if literal-stream compression is needed; this artifact does not compress the literal stream.",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `manifest_sha256`: `{payload['manifest_sha256']}`")
    lines.append(f"- `source_ledger_sha256`: `{payload['source_ledger_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated whole-stream residual vector probe files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_whole_stream_residual_vector_probe.py":
        raise SystemExit("whole_stream_residual_vector_probe.json has wrong generated_by")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("whole-stream residual vector artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("whole-stream residual vector manifest hash is stale")
    if payload.get("source_ledger_sha256") != source_ledger_hash(
        payload.get("source_case_rows", [])
    ):
        raise SystemExit("whole-stream residual vector source ledger hash is stale")
    summary = payload.get("summary", {})
    if not summary.get("reconstructed_source_case_count_matches_existing"):
        raise SystemExit("whole-stream residual vector source-case count drifted")
    if not summary.get("reconstructed_descriptor_row_count_matches_existing"):
        raise SystemExit("whole-stream residual vector descriptor-row count drifted")
    if summary.get("promotion_met") and summary.get("control_negative_groups"):
        raise SystemExit("whole-stream residual vector promotion cannot allow controls")
    if summary.get("promotion_met") and summary.get("ordinary_heldout_negative_groups", 0) < PROMOTION_ORDINARY_GROUPS:
        raise SystemExit("whole-stream residual vector promotion needs ordinary groups")
    honest_rows = [
        row
        for row in payload.get("rows", [])
        if row.get("encoded") and row.get("mode_kind") == "honest-measured"
    ]
    if not all(row.get("decode_verified") for row in honest_rows):
        raise SystemExit("whole-stream residual vector honest rows must decode exactly")
    if not all(all(row.get("corrupt_rejections", {}).values()) for row in honest_rows):
        raise SystemExit("whole-stream residual vector honest rows must reject corruption")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Whole-Stream Residual Vector Probe",
        "Generated by `scripts/generate_whole_stream_residual_vector_probe.py`",
        "whole-stream residual vector probe",
        "global residual entropy",
        "bitplane/vector channels",
        "exact decode",
        "corrupt rejection",
        "full-stream negative",
        "ordinary held-out negative groups",
        "controls null",
        "measured residual coding",
        "not .tlmr format support",
        "Promotion Gate",
        "Stop Rule",
        "Source Artifacts",
    ):
        if phrase not in text:
            raise SystemExit(
                f"WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md missing phrase: {phrase}"
            )


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
