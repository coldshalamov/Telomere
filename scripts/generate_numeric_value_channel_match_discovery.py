#!/usr/bin/env python3
"""Search reversible numeric value-channel transforms as independent match leads."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "numeric_value_channel_match_discovery.json"
REPORT_MD = DOCS / "NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md"
CORPUS_MATRIX_JSON = DOCS / "corpus_matrix.json"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6, 8)
SEED_RECORD_OVERHEAD_BYTES = 4
CHANNEL_DESCRIPTOR_BYTES = 10
TOP_LIMIT = 32

INTEGER_RE = re.compile(rb"[+-]?\d+")
DECIMAL_RE = re.compile(rb"[+-]?(?:(?:\d+\.\d*)|(?:\.\d+)|(?:\d+))(?:[eE][+-]?\d+)?")

NUMERIC_CORPORA = (
    "json",
    "csv",
    "rust-like",
    "python-like",
    "sql",
    "toml",
    "xml",
    "log",
    "yaml",
    "svg",
    "http-headers",
    "shadow-json",
    "binary-tlv",
    "binary-varint",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {"corpus_matrix_sha256": sha256(CORPUS_MATRIX_JSON)}


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint cannot encode negative values")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def zigzag(value: int) -> int:
    return (value << 1) if value >= 0 else ((-value << 1) - 1)


def encode_signed_varint(value: int) -> bytes:
    return encode_varint(zigzag(value))


def seed_len_offset(seed_len: int) -> int:
    return sum(256**length for length in range(1, seed_len))


def iter_seeds(max_seed_len: int = MAX_SEED_LEN):
    for seed_len in range(1, max_seed_len + 1):
        offset = seed_len_offset(seed_len)
        for value in range(256**seed_len):
            seed = value.to_bytes(seed_len, "big")
            yield offset + value, seed


def seed_maps() -> dict[str, Any]:
    prefix_sets: dict[int, set[bytes]] = {prefix_len: set() for prefix_len in PREFIX_LADDER}
    exact_by_span: dict[bytes, dict[str, Any]] = {}
    for seed_index, seed in iter_seeds():
        span = hashlib.sha256(seed).digest()[:SPAN_LEN]
        for prefix_len in PREFIX_LADDER:
            prefix_sets[prefix_len].add(span[:prefix_len])
        exact_by_span.setdefault(
            span,
            {
                "seed_index": seed_index,
                "seed_len": len(seed),
                "seed_hex": seed.hex(),
            },
        )
    return {"prefix_sets": prefix_sets, "exact_by_span": exact_by_span}


def corpus_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in generate_corpus_matrix.CORPUS_MATRIX:
        if case["corpus"] not in NUMERIC_CORPORA:
            continue
        cases.append(
            {
                "name": case["corpus"],
                "matrix_name": case["name"],
                "control_kind": case["control_kind"],
                "encoding_kind": case["encoding_kind"],
                "vocabulary_group": case["vocabulary_group"],
            }
        )
    return cases


def corpus_manifest_hash() -> str:
    payload = json.dumps(corpus_cases(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def channel_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": "identity",
            "family": "identity",
            "description": "No value-channel transform baseline.",
        },
        {
            "name": "integer-be64-stream",
            "family": "canonical-integer",
            "description": "Parse signed decimal integer tokens and emit fixed 8-byte big-endian signed values.",
        },
        {
            "name": "integer-zigzag-varint-stream",
            "family": "canonical-integer",
            "description": "Parse signed decimal integer tokens and emit zigzag-varint values.",
        },
        {
            "name": "integer-delta-varint-stream",
            "family": "sequential-delta",
            "description": "Emit zigzag-varint deltas between consecutive parsed integer values.",
        },
        {
            "name": "record-field-delta-varint-stream",
            "family": "record-field-delta",
            "description": "Emit zigzag-varint deltas against the previous record's value at the same numeric field position.",
        },
        {
            "name": "digit-residual-stream",
            "family": "digit-residual",
            "description": "Emit digit residuals modulo 10 by token position while sidecar metadata carries token widths and signs.",
        },
        {
            "name": "decimal-mantissa-exp-varint-stream",
            "family": "decimal-value",
            "description": "Parse decimal/scientific numeric tokens into signed mantissa and base-10 exponent varints.",
        },
    ]


def channel_manifest_hash() -> str:
    payload = json.dumps(channel_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def search_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte seeds, each bucket big-endian",
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "channel_descriptor_bytes": CHANNEL_DESCRIPTOR_BYTES,
        "target_block_hashing": False,
        "match_rule": "generated seed prefixes are compared directly against reversible numeric value-channel bytes",
        "metadata_policy": "gaps, token widths, signs, decimal formatting sidecars, and channel descriptors are charged before promotion",
        "scope": "numeric value-channel research artifact only; not .tlmr format support",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def token_gaps(data: bytes, tokens: list[dict[str, Any]]) -> list[bytes]:
    gaps: list[bytes] = []
    cursor = 0
    for token in tokens:
        gaps.append(data[cursor : token["start"]])
        cursor = token["end"]
    gaps.append(data[cursor:])
    return gaps


def integer_tokens(data: bytes) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for match in INTEGER_RE.finditer(data):
        lexeme = match.group(0)
        sign_char = ""
        digits = lexeme
        if digits[:1] in (b"+", b"-"):
            sign_char = digits[:1].decode("ascii")
            digits = digits[1:]
        if not digits:
            continue
        value = int(lexeme.decode("ascii"))
        tokens.append(
            {
                "start": match.start(),
                "end": match.end(),
                "lexeme": lexeme,
                "value": value,
                "sign_char": sign_char,
                "width": len(digits),
            }
        )
    return tokens


def decimal_tokens(data: bytes) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for match in DECIMAL_RE.finditer(data):
        lexeme = match.group(0)
        try:
            mantissa, exponent = decimal_mantissa_exponent(lexeme)
        except ValueError:
            continue
        tokens.append(
            {
                "start": match.start(),
                "end": match.end(),
                "lexeme": lexeme,
                "mantissa": mantissa,
                "exponent": exponent,
            }
        )
    return tokens


def decimal_mantissa_exponent(lexeme: bytes) -> tuple[int, int]:
    text = lexeme.decode("ascii")
    sign = -1 if text.startswith("-") else 1
    if text[:1] in ("+", "-"):
        text = text[1:]
    exponent = 0
    lower = text.lower()
    if "e" in lower:
        base, exp_text = lower.split("e", 1)
        exponent += int(exp_text)
    else:
        base = lower
    if "." in base:
        left, right = base.split(".", 1)
        exponent -= len(right)
        digits = left + right
    else:
        digits = base
    if not digits or not digits.isdigit():
        raise ValueError("not a decimal token")
    mantissa = int(digits) * sign
    return mantissa, exponent


def restore_integer_tokens(
    gaps: list[bytes], tokens: list[dict[str, Any]], values: list[int]
) -> bytes:
    if len(tokens) != len(values):
        raise RuntimeError("integer value count mismatch")
    out = bytearray()
    for gap, token, value in zip(gaps[:-1], tokens, values, strict=True):
        out.extend(gap)
        sign_char = token["sign_char"]
        digits = str(abs(value)).zfill(token["width"]).encode("ascii")
        if sign_char:
            out.extend(sign_char.encode("ascii"))
        elif value < 0:
            out.extend(b"-")
        out.extend(digits)
    out.extend(gaps[-1])
    return bytes(out)


def integer_metadata_bytes(gaps: list[bytes], tokens: list[dict[str, Any]]) -> int:
    return (
        sum(len(gap) for gap in gaps)
        + sum(1 + len(encode_varint(token["width"])) for token in tokens)
        + CHANNEL_DESCRIPTOR_BYTES
    )


def numeric_accounting(channel: dict[str, Any], data: bytes) -> dict[str, int]:
    name = channel["name"]
    if name == "identity":
        return {
            "numeric_bytes": 0,
            "parsed_value_count": 0,
            "parse_reject_count": 0,
            "gap_sidecar_bytes": 0,
            "format_sidecar_bytes": 0,
            "descriptor_bytes": 0,
        }
    if name == "decimal-mantissa-exp-varint-stream":
        tokens = decimal_tokens(data)
        gaps = token_gaps(data, tokens)
        return {
            "numeric_bytes": sum(len(token["lexeme"]) for token in tokens),
            "parsed_value_count": len(tokens),
            "parse_reject_count": 0,
            "gap_sidecar_bytes": sum(len(gap) for gap in gaps),
            "format_sidecar_bytes": sum(len(token["lexeme"]) + 1 for token in tokens),
            "descriptor_bytes": CHANNEL_DESCRIPTOR_BYTES,
        }

    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    format_bytes = sum(1 + len(encode_varint(token["width"])) for token in tokens)
    if name == "record-field-delta-varint-stream":
        max_fields = 0
        for record in data.splitlines(keepends=True):
            max_fields = max(max_fields, len(list(INTEGER_RE.finditer(record))))
        format_bytes += max_fields
    elif name == "digit-residual-stream":
        max_width = max((token["width"] for token in tokens), default=0)
        format_bytes += max_width

    return {
        "numeric_bytes": sum(len(token["lexeme"]) for token in tokens),
        "parsed_value_count": len(tokens),
        "parse_reject_count": 0,
        "gap_sidecar_bytes": sum(len(gap) for gap in gaps),
        "format_sidecar_bytes": format_bytes,
        "descriptor_bytes": CHANNEL_DESCRIPTOR_BYTES,
    }


def sidecar_hash(gaps: list[bytes], values: list[bytes]) -> str:
    h = hashlib.sha256()
    for gap in gaps:
        h.update(len(gap).to_bytes(4, "big"))
        h.update(gap)
    for value in values:
        h.update(len(value).to_bytes(4, "big"))
        h.update(value)
    return h.hexdigest()


def integer_be64_stream(data: bytes) -> tuple[bytes, bytes, int, str, int]:
    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    values = [token["value"] for token in tokens]
    primary = b"".join(value.to_bytes(8, "big", signed=True) for value in values)
    restored = restore_integer_tokens(gaps, tokens, values)
    metadata = integer_metadata_bytes(gaps, tokens)
    return (
        primary,
        restored,
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def integer_zigzag_varint_stream(data: bytes) -> tuple[bytes, bytes, int, str, int]:
    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    values = [token["value"] for token in tokens]
    primary = b"".join(encode_signed_varint(value) for value in values)
    restored = restore_integer_tokens(gaps, tokens, values)
    metadata = integer_metadata_bytes(gaps, tokens)
    return (
        primary,
        restored,
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def integer_delta_varint_stream(data: bytes) -> tuple[bytes, bytes, int, str, int]:
    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    values = [token["value"] for token in tokens]
    primary = bytearray()
    previous = 0
    for value in values:
        primary.extend(encode_signed_varint(value - previous))
        previous = value
    restored = restore_integer_tokens(gaps, tokens, values)
    metadata = integer_metadata_bytes(gaps, tokens)
    return (
        bytes(primary),
        restored,
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def record_field_delta_varint_stream(data: bytes) -> tuple[bytes, bytes, int, str, int]:
    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    values = [token["value"] for token in tokens]
    previous_by_field: dict[int, int] = {}
    primary = bytearray()
    token_index = 0
    for record in data.splitlines(keepends=True):
        field_index = 0
        for _match in INTEGER_RE.finditer(record):
            if token_index >= len(values):
                break
            value = values[token_index]
            previous = previous_by_field.get(field_index, 0)
            primary.extend(encode_signed_varint(value - previous))
            previous_by_field[field_index] = value
            field_index += 1
            token_index += 1
    if token_index != len(values):
        raise RuntimeError("record-field numeric token accounting mismatch")
    restored = restore_integer_tokens(gaps, tokens, values)
    metadata = integer_metadata_bytes(gaps, tokens) + len(previous_by_field)
    return (
        bytes(primary),
        restored,
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def digit_residual_stream(data: bytes) -> tuple[bytes, bytes, int, str, int]:
    tokens = integer_tokens(data)
    gaps = token_gaps(data, tokens)
    previous_by_position: dict[int, int] = {}
    primary = bytearray()
    restored_lexemes: list[bytes] = []
    for token in tokens:
        digits = token["lexeme"]
        if digits[:1] in (b"+", b"-"):
            digits = digits[1:]
        rebuilt_digits = bytearray()
        for position, byte in enumerate(digits):
            digit = byte - ord("0")
            previous = previous_by_position.get(position, 0)
            residual = (digit - previous) % 10
            primary.append(residual)
            decoded = (previous + residual) % 10
            previous_by_position[position] = decoded
            rebuilt_digits.append(ord("0") + decoded)
        rebuilt = token["sign_char"].encode("ascii") + bytes(rebuilt_digits)
        restored_lexemes.append(rebuilt)
    restored = bytearray()
    for gap, lexeme in zip(gaps[:-1], restored_lexemes, strict=True):
        restored.extend(gap)
        restored.extend(lexeme)
    restored.extend(gaps[-1])
    metadata = integer_metadata_bytes(gaps, tokens) + len(previous_by_position)
    return (
        bytes(primary),
        bytes(restored),
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def decimal_mantissa_exp_varint_stream(
    data: bytes,
) -> tuple[bytes, bytes, int, str, int]:
    tokens = decimal_tokens(data)
    gaps = token_gaps(data, tokens)
    primary = bytearray()
    for token in tokens:
        primary.extend(encode_signed_varint(token["mantissa"]))
        primary.extend(encode_signed_varint(token["exponent"]))
    restored = bytearray()
    for gap, token in zip(gaps[:-1], tokens, strict=True):
        restored.extend(gap)
        restored.extend(token["lexeme"])
    restored.extend(gaps[-1])
    metadata = (
        sum(len(gap) for gap in gaps)
        + sum(len(token["lexeme"]) + 1 for token in tokens)
        + CHANNEL_DESCRIPTOR_BYTES
    )
    return (
        bytes(primary),
        bytes(restored),
        metadata,
        sidecar_hash(gaps, [token["lexeme"] for token in tokens]),
        len(tokens),
    )


def apply_channel(channel: dict[str, Any], data: bytes) -> tuple[bytes, int, str, int]:
    name = channel["name"]
    if name == "identity":
        primary = data
        restored = data
        metadata_bytes = 0
        sidecar_sha256 = hashlib.sha256(b"").hexdigest()
        token_count = 0
    elif name == "integer-be64-stream":
        primary, restored, metadata_bytes, sidecar_sha256, token_count = integer_be64_stream(
            data
        )
    elif name == "integer-zigzag-varint-stream":
        (
            primary,
            restored,
            metadata_bytes,
            sidecar_sha256,
            token_count,
        ) = integer_zigzag_varint_stream(data)
    elif name == "integer-delta-varint-stream":
        (
            primary,
            restored,
            metadata_bytes,
            sidecar_sha256,
            token_count,
        ) = integer_delta_varint_stream(data)
    elif name == "record-field-delta-varint-stream":
        (
            primary,
            restored,
            metadata_bytes,
            sidecar_sha256,
            token_count,
        ) = record_field_delta_varint_stream(data)
    elif name == "digit-residual-stream":
        primary, restored, metadata_bytes, sidecar_sha256, token_count = (
            digit_residual_stream(data)
        )
    elif name == "decimal-mantissa-exp-varint-stream":
        (
            primary,
            restored,
            metadata_bytes,
            sidecar_sha256,
            token_count,
        ) = decimal_mantissa_exp_varint_stream(data)
    else:
        raise ValueError(f"unknown numeric value channel {name}")
    if restored != data:
        raise RuntimeError(f"{name} numeric value channel failed reversibility proof")
    return primary, metadata_bytes, sidecar_sha256, token_count


def candidate_span_count(data_len: int) -> int:
    if data_len < SPAN_LEN:
        return 0
    return ((data_len - SPAN_LEN) // SPAN_STEP) + 1


def weighted_interval_selection(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in opportunities
        if row["savings_bytes"] > 0 and row["start_offset"] < row["end_offset"]
    ]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
        )
    )
    ends = [row["end_offset"] for row in candidates]
    previous = [
        bisect.bisect_right(ends, row["start_offset"]) - 1 for row in candidates
    ]
    dp = [0] * (len(candidates) + 1)
    take = [False] * len(candidates)
    for index, row in enumerate(candidates):
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        skip_value = dp[index]
        if take_value > skip_value:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = skip_value
    selected: list[dict[str, Any]] = []
    index = len(candidates) - 1
    while index >= 0:
        row = candidates[index]
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        if take[index] and take_value > dp[index]:
            selected.append(row)
            index = previous[index]
        else:
            index -= 1
    return sorted(selected, key=lambda row: (row["start_offset"], row["end_offset"]))


def analyze_case(
    corpus: dict[str, Any], channel: dict[str, Any], maps: dict[str, Any]
) -> dict[str, Any]:
    original = generate_corpus_matrix.corpus_bytes(corpus["name"])
    primary, metadata_bytes, sidecar_sha256, token_count = apply_channel(channel, original)
    accounting = numeric_accounting(channel, original)
    accounted_metadata = (
        accounting["gap_sidecar_bytes"]
        + accounting["format_sidecar_bytes"]
        + accounting["descriptor_bytes"]
    )
    if accounted_metadata != metadata_bytes:
        raise RuntimeError(
            f"{channel['name']} metadata accounting mismatch: "
            f"{accounted_metadata} != {metadata_bytes}"
        )
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []

    for start in range(0, max(0, len(primary) - SPAN_LEN + 1), SPAN_STEP):
        span = primary[start : start + SPAN_LEN]
        dedup_spans.add(span)
        for prefix_len in PREFIX_LADDER:
            if span[:prefix_len] in maps["prefix_sets"][prefix_len]:
                prefix_counts[prefix_len] += 1
                max_prefix = max(max_prefix, prefix_len)
        hit = maps["exact_by_span"].get(span)
        if hit is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(hit["seed_hex"])).digest()[:SPAN_LEN]
        if regenerated != span:
            raise RuntimeError("exact numeric value-channel hit failed regeneration")
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
        exact_hits.append(
            {
                "start_offset": start,
                "end_offset": start + SPAN_LEN,
                "span_len": SPAN_LEN,
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": SPAN_LEN - encoded_len,
                "regeneration_verified": True,
            }
        )

    selected = weighted_interval_selection(exact_hits)
    selected_seed_bytes = sum(row["encoded_len"] for row in selected)
    selected_literal_bytes = sum(row["span_len"] for row in selected)
    selected_delta = selected_seed_bytes - selected_literal_bytes
    representation_bytes = len(primary) + metadata_bytes
    net_with_metadata = representation_bytes + selected_delta - len(original)
    return {
        "corpus": corpus["name"],
        "matrix_name": corpus["matrix_name"],
        "control_kind": corpus["control_kind"],
        "encoding_kind": corpus["encoding_kind"],
        "vocabulary_group": corpus["vocabulary_group"],
        "channel": channel["name"],
        "channel_family": channel["family"],
        "input_bytes": len(original),
        "numeric_token_count": token_count,
        "numeric_bytes": accounting["numeric_bytes"],
        "parsed_value_count": accounting["parsed_value_count"],
        "parse_reject_count": accounting["parse_reject_count"],
        "primary_channel_bytes": len(primary),
        "gap_sidecar_bytes": accounting["gap_sidecar_bytes"],
        "format_sidecar_bytes": accounting["format_sidecar_bytes"],
        "descriptor_bytes": accounting["descriptor_bytes"],
        "metadata_bytes": metadata_bytes,
        "representation_bytes": representation_bytes,
        "representation_delta_before_seed": representation_bytes - len(original),
        "input_sha256": hashlib.sha256(original).hexdigest(),
        "primary_channel_sha256": hashlib.sha256(primary).hexdigest(),
        "sidecar_sha256": sidecar_sha256,
        "target_span_count": candidate_span_count(len(primary)),
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
        "prefix_ge_8_count": prefix_counts[8],
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(
            1 for row in exact_hits if row["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": selected_literal_bytes,
        "encoded_seed_bytes": selected_seed_bytes,
        "net_seed_delta_bytes": selected_delta,
        "net_with_metadata_bytes": net_with_metadata,
        "reversibility_verified": True,
        "selected_records": selected[:8],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    exact = [row for row in rows if row["exact_hit_count"] > 0]
    selected = [row for row in rows if row["selected_span_count"] > 0]
    negative_after_metadata = [
        row
        for row in rows
        if row["selected_span_count"] > 0 and row["net_with_metadata_bytes"] < 0
    ]
    ordinary_prefix5_groups = {
        row["corpus"]
        for row in prefix5
        if row["control_kind"] == "ordinary-structured"
    }
    control_prefix5_groups = {
        row["corpus"]
        for row in prefix5
        if row["control_kind"] != "ordinary-structured"
    }
    ordinary_negative_groups = {
        row["corpus"]
        for row in negative_after_metadata
        if row["control_kind"] == "ordinary-structured"
    }
    control_kinds = sorted({row["control_kind"] for row in rows})
    best = min(
        rows,
        key=lambda row: (
            row["net_with_metadata_bytes"],
            -row["selected_span_count"],
            -row["max_prefix_observed"],
            row["corpus"],
            row["channel"],
        ),
    )
    best_prefix = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["corpus"],
            row["channel"],
        ),
    )
    promotion_ready = (
        len(ordinary_negative_groups) >= 2
        or (len(ordinary_prefix5_groups) >= 2 and len(control_prefix5_groups) == 0)
    )
    if promotion_ready:
        conclusion = "Numeric value channels produced a promotable independent lead."
    elif prefix5 or exact or selected:
        conclusion = (
            "Numeric value channels produced signal, but it does not yet satisfy "
            "the held-out/control promotion gate."
        )
    else:
        conclusion = (
            "Numeric value channels did not produce prefix>=5, exact, selected, "
            "or metadata-profitable rows."
        )
    return {
        "corpus_count": len(corpus_cases()),
        "channel_count": len(channel_manifest()),
        "row_count": len(rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "numeric_token_count": sum(row["numeric_token_count"] for row in rows),
        "numeric_bytes": sum(row["numeric_bytes"] for row in rows),
        "parsed_value_count": sum(row["parsed_value_count"] for row in rows),
        "parse_reject_count": sum(row["parse_reject_count"] for row in rows),
        "rows_with_prefix_ge_5_by_control_kind": {
            kind: sum(
                1
                for row in prefix5
                if row["control_kind"] == kind
            )
            for kind in control_kinds
        },
        "rows_negative_after_metadata_by_control_kind": {
            kind: sum(
                1
                for row in negative_after_metadata
                if row["control_kind"] == kind
            )
            for kind in control_kinds
        },
        "rows_with_prefix_ge_5": len(prefix5),
        "rows_with_exact_hits": len(exact),
        "rows_with_selected_spans": len(selected),
        "rows_negative_after_metadata": len(negative_after_metadata),
        "ordinary_prefix5_group_count": len(ordinary_prefix5_groups),
        "control_prefix5_group_count": len(control_prefix5_groups),
        "ordinary_negative_group_count": len(ordinary_negative_groups),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_net_case": f"{best['corpus']}::{best['channel']}",
        "best_net_delta_bytes": best["net_with_metadata_bytes"],
        "best_prefix_case": f"{best_prefix['corpus']}::{best_prefix['channel']}",
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_prefix_ge_5_count": best_prefix["prefix_ge_5_count"],
        "promotion_ready": promotion_ready,
        "conclusion": conclusion,
    }


def top_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["net_with_metadata_bytes"],
            -row["selected_span_count"],
            -row["exact_hit_count"],
            -row["max_prefix_observed"],
            -row["prefix_ge_5_count"],
            row["corpus"],
            row["channel"],
        ),
    )[:TOP_LIMIT]


def build_report() -> dict[str, Any]:
    maps = seed_maps()
    channels = channel_manifest()
    corpora = corpus_cases()
    rows = [
        analyze_case(corpus, channel, maps)
        for corpus in corpora
        for channel in channels
    ]
    return {
        "generated_by": "scripts/generate_numeric_value_channel_match_discovery.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "channel_manifest_sha256": channel_manifest_hash(),
        "search_manifest_sha256": search_manifest_hash(),
        "search_manifest": search_manifest(),
        "corpora": corpora,
        "channels": channels,
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Numeric Value-Channel Match Discovery",
        "",
        "Generated by `scripts/generate_numeric_value_channel_match_discovery.py`.",
        "This is a reversible numeric value-channel research artifact, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Channels: `{summary['channel_count']}`.",
        f"Rows: `{summary['row_count']}`.",
        f"Numeric tokens parsed: `{summary['numeric_token_count']}`.",
        f"Numeric bytes parsed: `{summary['numeric_bytes']}`.",
        f"Parsed values: `{summary['parsed_value_count']}`.",
        f"Parse rejects: `{summary['parse_reject_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Rows negative after metadata: `{summary['rows_negative_after_metadata']}`.",
        f"Ordinary prefix>=5 groups: `{summary['ordinary_prefix5_group_count']}`.",
        f"Control prefix>=5 groups: `{summary['control_prefix5_group_count']}`.",
        f"Promotion ready: `{summary['promotion_ready']}`.",
        f"Best net case: `{summary['best_net_case']}`.",
        f"Best net delta bytes: `{summary['best_net_delta_bytes']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        "",
        "## Search Contract",
        "",
        f"- Hasher: `{HASHER}`.",
        f"- Max seed length: `{MAX_SEED_LEN}`.",
        f"- Span length: `{SPAN_LEN}`.",
        f"- Span step: `{SPAN_STEP}`.",
        "- Target block hashing: `false`.",
        "- Generated seed prefixes are compared directly against reversible numeric value-channel bytes.",
        "- Every value channel proves lossless reconstruction before search metrics are accepted.",
        "- Gaps, token widths, signs, decimal formatting sidecars, and channel descriptors are charged before promotion.",
        "- Promotion gate: metadata-profitable selected spans in at least two ordinary groups, or prefix>=5 in at least two ordinary groups while controls stay null.",
        "- Stop rule: if prefix>=5, exact, selected, and profitable rows are all zero, do not add another byte transform before widening corpus or theory gates.",
        "",
        "## Top Rows",
        "",
        "| corpus | channel | family | values | primary bytes | gaps | format | descriptor | pre-seed delta | p4 | p5 | p6 | exact | selected | net+metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {corpus} | {channel} | {channel_family} | {parsed_value_count} | "
            "{primary_channel_bytes} | {gap_sidecar_bytes} | {format_sidecar_bytes} | "
            "{descriptor_bytes} | {representation_delta_before_seed} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_hit_count} | {selected_span_count} | {net_with_metadata_bytes} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Numeric value channels parse numbers as values, not as lexeme tokens or digit-shaped syntax.",
            "- Integer streams charge enough sidecar metadata to reconstruct gaps, signs, and token widths exactly.",
            "- Decimal mantissa/exponent streams are intentionally conservative: original decimal lexemes are charged as formatting sidecar metadata.",
            "- A channel only becomes interesting if selected seed replacements beat the primary stream and charged reconstruction metadata.",
            "- Null or control-only signal blocks promotion; it means the next step is better corpus/theory evidence, not blind compute.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated numeric value-channel discovery files are missing")
    payload = load_json(REPORT_JSON)
    if (
        payload.get("generated_by")
        != "scripts/generate_numeric_value_channel_match_discovery.py"
    ):
        raise SystemExit(
            "numeric_value_channel_match_discovery.json has wrong generated_by marker"
        )
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("numeric value-channel discovery artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("numeric value-channel discovery corpus manifest hash is stale")
    if payload.get("channel_manifest_sha256") != channel_manifest_hash():
        raise SystemExit("numeric value-channel discovery channel manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("numeric value-channel discovery search manifest hash is stale")
    if len(payload.get("rows", [])) != len(corpus_cases()) * len(channel_manifest()):
        raise SystemExit("numeric value-channel discovery row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Numeric Value-Channel Match Discovery",
        "reversible numeric value-channel research artifact",
        "Target block hashing: `false`",
        "lossless reconstruction",
        "Numeric bytes parsed",
        "Promotion gate",
        "Stop rule",
    ):
        if phrase not in text:
            raise SystemExit(
                f"NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md missing phrase: {phrase}"
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
