#!/usr/bin/env python3
"""Search reversible grammar/channel transforms as independent match leads."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import generate_corpus_matrix


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "grammar_channel_match_discovery.json"
REPORT_MD = DOCS / "GRAMMAR_CHANNEL_MATCH_DISCOVERY.md"
CORPUS_MATRIX_JSON = DOCS / "corpus_matrix.json"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6, 8)
SEED_RECORD_OVERHEAD_BYTES = 4
CHANNEL_DESCRIPTOR_BYTES = 8
TOP_LIMIT = 32

STRUCTURAL_BYTES = set(b"{}[]()<>/:,=;.-_#\"'\\|&?+*")
FIELD_DELIMITER_BYTES = set(b",;:=|{}\n\r[]<>/")
WHITESPACE_BYTES = set(b" \t\r\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {"corpus_matrix_sha256": sha256(CORPUS_MATRIX_JSON)}


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
        digest = hashlib.sha256(seed).digest()
        span = digest[:SPAN_LEN]
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
    return [
        {
            "name": case["corpus"],
            "matrix_name": case["name"],
            "control_kind": case["control_kind"],
            "encoding_kind": case["encoding_kind"],
            "vocabulary_group": case["vocabulary_group"],
        }
        for case in generate_corpus_matrix.CORPUS_MATRIX
    ]


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
            "description": "No channelization baseline.",
        },
        {
            "name": "syntax-skeleton",
            "family": "generalized-bitmask",
            "description": "Preserve syntax punctuation while generalizing identifiers, digits, and whitespace.",
        },
        {
            "name": "identifier-shape",
            "family": "generalized-bitmask",
            "description": "Generalize ASCII identifiers and underscores, preserving other bytes.",
        },
        {
            "name": "number-shape",
            "family": "generalized-bitmask",
            "description": "Generalize decimal digits, preserving other bytes.",
        },
        {
            "name": "whitespace-shape",
            "family": "generalized-bitmask",
            "description": "Normalize whitespace classes, preserving non-whitespace bytes.",
        },
        {
            "name": "field-delimiter-skeleton",
            "family": "generalized-bitmask",
            "description": "Preserve line and field delimiters while generalizing payload bytes.",
        },
        {
            "name": "all-class-stream",
            "family": "literal-sidecar-channel",
            "description": "Emit one byte class per input byte and charge the whole literal sidecar.",
        },
        {
            "name": "class-run-stream",
            "family": "literal-sidecar-channel",
            "description": "Emit class/run-length pairs and charge the whole literal sidecar.",
        },
        {
            "name": "punctuation-gap-stream",
            "family": "gap-sidecar-channel",
            "description": "Emit only structural punctuation and charge non-structural bytes plus gap lengths.",
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
        "match_rule": "generated seed prefixes are compared directly against reversible channel bytes",
        "metadata_policy": "sidecars, bitmasks, gap streams, and channel descriptors are charged before promotion",
        "scope": "grammar/channel research artifact only; not .tlmr format support",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def is_alpha(byte: int) -> bool:
    return 65 <= byte <= 90 or 97 <= byte <= 122


def is_digit(byte: int) -> bool:
    return 48 <= byte <= 57


def is_identifier(byte: int) -> bool:
    return is_alpha(byte) or is_digit(byte) or byte == ord("_")


def class_byte(byte: int) -> int:
    if is_alpha(byte) or byte == ord("_"):
        return ord("A")
    if is_digit(byte):
        return ord("0")
    if byte in WHITESPACE_BYTES:
        return ord(" ")
    if byte in STRUCTURAL_BYTES:
        return byte
    if 32 <= byte <= 126:
        return ord("P")
    return ord("?")


def bit_is_set(bitmask: bytes, index: int) -> bool:
    return (bitmask[index // 8] & (1 << (index % 8))) != 0


def pack_bitmask(flags: list[bool]) -> bytes:
    mask = bytearray((len(flags) + 7) // 8)
    for index, flag in enumerate(flags):
        if flag:
            mask[index // 8] |= 1 << (index % 8)
    return bytes(mask)


def generalize_with_bitmask(
    data: bytes,
    should_generalize: Callable[[int], bool],
    mapper: Callable[[int], int],
) -> tuple[bytes, bytes, int, str]:
    primary = bytearray()
    sidecar = bytearray()
    flags: list[bool] = []
    for byte in data:
        generalized = should_generalize(byte)
        flags.append(generalized)
        if generalized:
            primary.append(mapper(byte))
            sidecar.append(byte)
        else:
            primary.append(byte)

    bitmask = pack_bitmask(flags)
    restored = bytearray()
    cursor = 0
    for index, value in enumerate(primary):
        if bit_is_set(bitmask, index):
            restored.append(sidecar[cursor])
            cursor += 1
        else:
            restored.append(value)
    if cursor != len(sidecar):
        raise RuntimeError("generalized channel sidecar was not fully consumed")
    return (
        bytes(primary),
        bytes(restored),
        len(sidecar) + len(bitmask) + CHANNEL_DESCRIPTOR_BYTES,
        hashlib.sha256(bytes(sidecar) + bitmask).hexdigest(),
    )


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


def all_class_stream(data: bytes) -> tuple[bytes, bytes, int, str]:
    primary = bytes(class_byte(byte) for byte in data)
    sidecar_hash = hashlib.sha256(data).hexdigest()
    return primary, data, len(data) + CHANNEL_DESCRIPTOR_BYTES, sidecar_hash


def class_run_stream(data: bytes) -> tuple[bytes, bytes, int, str]:
    if not data:
        return b"", b"", CHANNEL_DESCRIPTOR_BYTES, hashlib.sha256(b"").hexdigest()
    out = bytearray()
    last = class_byte(data[0])
    run_len = 1
    for byte in data[1:]:
        current = class_byte(byte)
        if current == last:
            run_len += 1
            continue
        out.append(last)
        out.extend(encode_varint(run_len))
        last = current
        run_len = 1
    out.append(last)
    out.extend(encode_varint(run_len))
    return bytes(out), data, len(data) + CHANNEL_DESCRIPTOR_BYTES, hashlib.sha256(data).hexdigest()


def punctuation_gap_stream(data: bytes) -> tuple[bytes, bytes, int, str]:
    primary = bytearray()
    sidecar = bytearray()
    gap_lengths: list[int] = []
    current_gap = 0
    for byte in data:
        if byte in STRUCTURAL_BYTES:
            gap_lengths.append(current_gap)
            current_gap = 0
            primary.append(byte)
        else:
            sidecar.append(byte)
            current_gap += 1
    gap_lengths.append(current_gap)
    gap_bytes = b"".join(encode_varint(gap) for gap in gap_lengths)

    restored = bytearray()
    sidecar_cursor = 0
    for gap, punct in zip(gap_lengths[:-1], primary, strict=True):
        restored.extend(sidecar[sidecar_cursor : sidecar_cursor + gap])
        sidecar_cursor += gap
        restored.append(punct)
    restored.extend(sidecar[sidecar_cursor : sidecar_cursor + gap_lengths[-1]])
    sidecar_cursor += gap_lengths[-1]
    if sidecar_cursor != len(sidecar):
        raise RuntimeError("punctuation gap sidecar was not fully consumed")
    metadata = len(sidecar) + len(gap_bytes) + CHANNEL_DESCRIPTOR_BYTES
    return (
        bytes(primary),
        bytes(restored),
        metadata,
        hashlib.sha256(bytes(sidecar) + gap_bytes).hexdigest(),
    )


def apply_channel(channel: dict[str, Any], data: bytes) -> tuple[bytes, int, str]:
    name = channel["name"]
    if name == "identity":
        primary = data
        restored = data
        metadata_bytes = 0
        sidecar_hash = hashlib.sha256(b"").hexdigest()
    elif name == "syntax-skeleton":
        primary, restored, metadata_bytes, sidecar_hash = generalize_with_bitmask(
            data,
            lambda byte: is_identifier(byte) or byte in WHITESPACE_BYTES,
            class_byte,
        )
    elif name == "identifier-shape":
        primary, restored, metadata_bytes, sidecar_hash = generalize_with_bitmask(
            data, lambda byte: is_alpha(byte) or byte == ord("_"), lambda _byte: ord("A")
        )
    elif name == "number-shape":
        primary, restored, metadata_bytes, sidecar_hash = generalize_with_bitmask(
            data, is_digit, lambda _byte: ord("0")
        )
    elif name == "whitespace-shape":
        primary, restored, metadata_bytes, sidecar_hash = generalize_with_bitmask(
            data, lambda byte: byte in WHITESPACE_BYTES, lambda _byte: ord(" ")
        )
    elif name == "field-delimiter-skeleton":
        primary, restored, metadata_bytes, sidecar_hash = generalize_with_bitmask(
            data,
            lambda byte: byte not in FIELD_DELIMITER_BYTES,
            class_byte,
        )
    elif name == "all-class-stream":
        primary, restored, metadata_bytes, sidecar_hash = all_class_stream(data)
    elif name == "class-run-stream":
        primary, restored, metadata_bytes, sidecar_hash = class_run_stream(data)
    elif name == "punctuation-gap-stream":
        primary, restored, metadata_bytes, sidecar_hash = punctuation_gap_stream(data)
    else:
        raise ValueError(f"unknown channel {name}")

    if restored != data:
        raise RuntimeError(f"{name} channel failed reversibility proof")
    return primary, metadata_bytes, sidecar_hash


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
    corpus: dict[str, Any],
    channel: dict[str, Any],
    maps: dict[str, Any],
) -> dict[str, Any]:
    original = generate_corpus_matrix.corpus_bytes(corpus["name"])
    primary, metadata_bytes, sidecar_sha256 = apply_channel(channel, original)
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
            raise RuntimeError("exact grammar-channel hit failed regeneration")
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
        "primary_channel_bytes": len(primary),
        "metadata_bytes": metadata_bytes,
        "representation_bytes": representation_bytes,
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
        conclusion = "Grammar channels produced a promotable independent lead."
    elif prefix5 or exact or selected:
        conclusion = (
            "Grammar channels produced signal, but it does not yet satisfy the "
            "held-out/control promotion gate."
        )
    else:
        conclusion = (
            "Grammar channels did not produce prefix>=5, exact, selected, or "
            "metadata-profitable rows."
        )
    return {
        "corpus_count": len(corpus_cases()),
        "channel_count": len(channel_manifest()),
        "row_count": len(rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
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
        "generated_by": "scripts/generate_grammar_channel_match_discovery.py",
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
        "# Telomere Grammar Channel Match Discovery",
        "",
        "Generated by `scripts/generate_grammar_channel_match_discovery.py`.",
        "This is a reversible grammar/channel research artifact, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Channels: `{summary['channel_count']}`.",
        f"Rows: `{summary['row_count']}`.",
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
        "- Generated seed prefixes are compared directly against reversible channel bytes.",
        "- Every channel proves lossless reconstruction before search metrics are accepted.",
        "- Sidecars, bitmasks, gap streams, and channel descriptors are charged before promotion.",
        "- Promotion gate: metadata-profitable selected spans in at least two ordinary groups, or prefix>=5 in at least two ordinary groups while controls stay null.",
        "- Stop rule: if prefix>=5, exact, selected, and profitable rows are all zero, design a new channel family before increasing compute.",
        "",
        "## Top Rows",
        "",
        "| corpus | channel | family | primary bytes | metadata | p4 | p5 | p6 | exact | selected | net+metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {corpus} | {channel} | {channel_family} | {primary_channel_bytes} | "
            "{metadata_bytes} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_hit_count} | {selected_span_count} | "
            "{net_with_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Grammar channels split an input into a primary structural stream plus enough charged sidecar metadata to make reconstruction lossless.",
            "- This lets us test the whitepaper superposition intuition without pretending a lossy syntax sketch is compressed data.",
            "- A channel only becomes interesting if the seed replacements beat both the primary stream and the charged sidecars.",
            "- Null or control-only signal blocks promotion; it means the next step is a better channel hypothesis, not a larger compute spend.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated grammar channel discovery files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_grammar_channel_match_discovery.py":
        raise SystemExit("grammar_channel_match_discovery.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("grammar channel discovery artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("grammar channel discovery corpus manifest hash is stale")
    if payload.get("channel_manifest_sha256") != channel_manifest_hash():
        raise SystemExit("grammar channel discovery channel manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("grammar channel discovery search manifest hash is stale")
    if len(payload.get("rows", [])) != len(corpus_cases()) * len(channel_manifest()):
        raise SystemExit("grammar channel discovery row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Grammar Channel Match Discovery",
        "reversible grammar/channel research artifact",
        "Target block hashing: `false`",
        "lossless reconstruction",
        "Promotion gate",
        "Stop rule",
    ):
        if phrase not in text:
            raise SystemExit(f"GRAMMAR_CHANNEL_MATCH_DISCOVERY.md missing phrase: {phrase}")


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
