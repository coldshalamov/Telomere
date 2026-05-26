#!/usr/bin/env python3
"""Run a focused Telomere thesis-attack experiment.

This script is intentionally not a broad search. It quantifies the random-hit
baseline, then tests whether small reversible mechanism changes increase
profitable exact seed-span density on non-planted structured data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "thesis_attack_experiment.json"
REPORT_MD = DOCS / "THESIS_ATTACK_EXPERIMENT.md"
GENERATED_BY = "scripts/run_thesis_attack_experiment.py"
ARTIFACT_INPUT_SUFFIXES = {".bin", ".txt", ".json", ".rs", ".csv", ".md"}
ARTIFACT_EXCLUDE_SUFFIXES = {".tlmr", ".decoded", ".exe", ".dll", ".pdb"}

HASHER = "sha256"
BLOCK_SIZE = 4
MAX_SPAN_LEN = 16
SPAN_STEP = 1
SEED_DEPTH = 1
PASSES = 1
TRANSFORM_METADATA_BYTES = 8
PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN = 13


PUBLIC_PRESET_TOKENS = [
    b'"event":',
    b'"id":',
    b'"sku":',
    b'"status":',
    b'"amount_cents":',
    b'"order_update"',
    b'"queued"',
    b'"paid"',
    b'"fulfilled"',
    b'"$schema":',
    b'"properties":',
    b'"required":',
    b'"type":',
    b'"object"',
    b'"integer"',
    b'"boolean"',
    b"city,region,country,population\n",
    b",United States,",
    b"Create an HTTP",
    b"Request::builder()",
    b"Response::builder()",
    b".header(",
    b".body(())",
    b"Some(",
    b"None",
    b"Option",
]
PUBLIC_PRESET_CODEWORD_VARIANTS = ("seed", "random-codeword", "out-of-budget-codeword")
LEARNED_PUBLIC_MIN_TOKEN_LEN = 13
LEARNED_PUBLIC_MAX_TOKEN_LEN = MAX_SPAN_LEN
LEARNED_PUBLIC_TOKEN_LIMIT = 32
EXTERNAL_CORPUS_FAMILIES = {
    "external-json-schema": "schema-and-config",
    "external-csv": "records-and-ledgers",
    "external-http": "standards-protocol-text",
    "external-source": "source-code",
}
EXTERNAL_ORDINARY_PATHS = {
    "schema-and-config": ROOT
    / "corpora/external/schema-and-config/schemars-main-schema-excerpt.json",
    "records-and-ledgers": ROOT
    / "corpora/external/records-and-ledgers/csv-smallpop-excerpt.csv",
    "standards-protocol-text": ROOT
    / "corpora/external/standards-protocol-text/http-request-response-excerpt.md",
    "source-code": ROOT / "corpora/external/source-code/rust-option-excerpt.rs",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_slug(value: str, max_len: int = 96) -> str:
    cleaned = "".join(
        c if c.isalnum() or c in ("-", "_", ".") else "-" for c in value
    ).strip("-")
    if not cleaned:
        cleaned = "artifact"
    digest = sha256_bytes(value.encode("utf-8"))[:12]
    return f"{cleaned[:max_len]}-{digest}"


def validate_external_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = []
    entries = manifest.get("entries", [])
    for entry in entries:
        rel_path = Path(entry["path"])
        path = ROOT / rel_path
        if not path.exists():
            mismatches.append(
                {
                    "entry_id": entry.get("entry_id"),
                    "path": rel_path.as_posix(),
                    "reason": "missing file",
                }
            )
            continue
        data = path.read_bytes()
        actual_sha = sha256_bytes(data)
        actual_bytes = len(data)
        if actual_sha != entry.get("sha256") or actual_bytes != entry.get("bytes"):
            mismatches.append(
                {
                    "entry_id": entry.get("entry_id"),
                    "path": rel_path.as_posix(),
                    "expected_sha256": entry.get("sha256"),
                    "actual_sha256": actual_sha,
                    "expected_bytes": entry.get("bytes"),
                    "actual_bytes": actual_bytes,
                }
            )
    if mismatches:
        preview = "; ".join(
            f"{item['entry_id']} {item['path']}" for item in mismatches[:5]
        )
        raise SystemExit(
            "external manifest validation failed; checkout bytes do not match "
            f"{manifest_path}: {preview}"
        )
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "entry_count": len(entries),
        "validated": True,
    }


def deterministic_bytes(label: str, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(f"{label}:{counter}".encode("utf-8")).digest())
        counter += 1
    return bytes(out[:length])


def unique_deterministic_bytes(
    label: str,
    length: int,
    used: set[bytes],
    forbidden: set[bytes] | None = None,
) -> bytes:
    counter = 0
    forbidden = forbidden or set()
    while True:
        value = deterministic_bytes(f"{label}:{counter}", length)
        if value not in used and value not in forbidden:
            used.add(value)
            return value
        counter += 1


def canonical_seed_from_index(index: int) -> bytes:
    if index < 0:
        raise ValueError("seed index must be non-negative")
    remaining = index
    length = 1
    while True:
        bucket = 1 << (8 * length)
        if remaining < bucket:
            return remaining.to_bytes(length, "big")
        remaining -= bucket
        length += 1


def seed_span(seed: bytes, span_len: int = MAX_SPAN_LEN) -> bytes:
    return hashlib.sha256(seed).digest()[:span_len]


def planted_positive() -> bytes:
    out = bytearray()
    for idx in range(128):
        out.extend(seed_span(bytes([idx % 64])))
    return bytes(out)


def load_artifact_inputs(paths: list[Path]) -> dict[str, bytes]:
    corpora: dict[str, bytes] = {}
    for source in paths:
        source = source.resolve()
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for path in candidates:
            if not path.is_file():
                continue
            if path.suffix.lower() in ARTIFACT_EXCLUDE_SUFFIXES:
                continue
            if path.suffix.lower() not in ARTIFACT_INPUT_SUFFIXES:
                continue
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            name = safe_slug(f"target-{rel.as_posix()}", max_len=80)
            corpora[name] = path.read_bytes()
    return corpora


def load_corpora(include_target_inputs: list[Path] | None = None) -> dict[str, bytes]:
    structured = generate_results.structured_json_bytes()
    corpora = {
        "planted-positive": planted_positive(),
        "structured-json": structured,
        "external-json-schema": (
            ROOT / "corpora/external/schema-and-config/schemars-main-schema-excerpt.json"
        ).read_bytes(),
        "external-csv": (
            ROOT / "corpora/external/records-and-ledgers/csv-smallpop-excerpt.csv"
        ).read_bytes(),
        "external-http": (
            ROOT / "corpora/external/standards-protocol-text/http-request-response-excerpt.md"
        ).read_bytes(),
        "external-source": (
            ROOT / "corpora/external/source-code/rust-option-excerpt.rs"
        ).read_bytes(),
    }
    corpora["random-null-structured-len"] = deterministic_bytes(
        "thesis-null-structured", len(structured)
    )
    if include_target_inputs:
        corpora.update(load_artifact_inputs(include_target_inputs))
    return corpora


def xor_delta(data: bytes) -> tuple[bytes, dict[str, Any]]:
    if not data:
        return b"", {"transform_metadata_bytes": 1}
    out = bytearray([data[0]])
    for prev, cur in zip(data, data[1:]):
        out.append(prev ^ cur)
    return bytes(out), {"transform_metadata_bytes": 1}


def invert_xor_delta(encoded: bytes) -> bytes:
    if not encoded:
        return b""
    out = bytearray([encoded[0]])
    for byte in encoded[1:]:
        out.append(out[-1] ^ byte)
    return bytes(out)


def public_preset_codebook(variant: str = "seed") -> dict[bytes, bytes]:
    if variant not in PUBLIC_PRESET_CODEWORD_VARIANTS:
        raise ValueError(f"unknown public preset codeword variant: {variant}")
    seed_codewords = {
        seed_span(bytes([idx])) for idx in range(1 << (8 * SEED_DEPTH))
    }
    used: set[bytes] = set()
    codebook: dict[bytes, bytes] = {}
    for idx, token in enumerate(PUBLIC_PRESET_TOKENS):
        if variant == "seed":
            codeword = seed_span(bytes([idx]))
        elif variant == "out-of-budget-codeword":
            seed_index = (1 << (8 * SEED_DEPTH)) + idx
            while True:
                codeword = seed_span(canonical_seed_from_index(seed_index))
                if codeword not in seed_codewords and codeword not in used:
                    break
                seed_index += len(PUBLIC_PRESET_TOKENS)
        else:
            codeword = unique_deterministic_bytes(
                f"thesis-public-preset-control:{variant}:{idx}",
                MAX_SPAN_LEN,
                used,
                seed_codewords,
            )
        used.add(codeword)
        codebook[token] = codeword
    return codebook


def codewords_for_tokens(
    tokens: list[bytes],
    variant: str = "seed",
    label: str = "learned-public",
) -> dict[bytes, bytes]:
    if variant not in PUBLIC_PRESET_CODEWORD_VARIANTS:
        raise ValueError(f"unknown public preset codeword variant: {variant}")
    seed_codewords = {
        seed_span(bytes([idx])) for idx in range(1 << (8 * SEED_DEPTH))
    }
    used: set[bytes] = set()
    codebook: dict[bytes, bytes] = {}
    for idx, token in enumerate(tokens):
        if variant == "seed":
            codeword = seed_span(bytes([idx]))
        elif variant == "out-of-budget-codeword":
            seed_index = (1 << (8 * SEED_DEPTH)) + idx
            while True:
                codeword = seed_span(canonical_seed_from_index(seed_index))
                if codeword not in seed_codewords and codeword not in used:
                    break
                seed_index += max(len(tokens), 1)
        else:
            codeword = unique_deterministic_bytes(
                f"thesis-{label}-control:{variant}:{idx}",
                MAX_SPAN_LEN,
                used,
                seed_codewords,
            )
        used.add(codeword)
        codebook[token] = codeword
    return codebook


def is_learnable_public_token(token: bytes) -> bool:
    if len(token) < LEARNED_PUBLIC_MIN_TOKEN_LEN:
        return False
    has_alnum = False
    for byte in token:
        if 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122:
            has_alnum = True
            continue
        if byte in (9, 10, 13) or 32 <= byte <= 126:
            continue
        return False
    return has_alnum


def learned_public_tokens(training_blobs: list[bytes]) -> list[bytes]:
    counts: dict[bytes, int] = {}
    for data in training_blobs:
        upper = min(LEARNED_PUBLIC_MAX_TOKEN_LEN, len(data))
        for span_len in range(LEARNED_PUBLIC_MIN_TOKEN_LEN, upper + 1):
            for start in range(0, len(data) - span_len + 1):
                token = data[start : start + span_len]
                if is_learnable_public_token(token):
                    counts[token] = counts.get(token, 0) + 1
    ranked = [
        {
            "token": token,
            "count": count,
            "score": count * (len(token) - LEARNED_PUBLIC_MIN_TOKEN_LEN + 1),
        }
        for token, count in counts.items()
        if count >= 2
    ]
    ranked.sort(
        key=lambda row: (
            -row["score"],
            -row["count"],
            -len(row["token"]),
            row["token"],
        )
    )

    selected: list[bytes] = []
    for row in ranked:
        token = row["token"]
        if any(token in existing or existing in token for existing in selected):
            continue
        selected.append(token)
        if len(selected) >= LEARNED_PUBLIC_TOKEN_LIMIT:
            break
    return selected


def external_ordinary_blobs(exclude_family: str | None = None) -> list[bytes]:
    return [
        path.read_bytes()
        for family, path in sorted(EXTERNAL_ORDINARY_PATHS.items())
        if family != exclude_family
    ]


def learned_public_codebook(
    mode: str,
    corpus_name: str,
    codeword_variant: str = "seed",
) -> tuple[dict[bytes, bytes], dict[str, Any]]:
    exclude_family = None
    if mode == "lfo":
        exclude_family = EXTERNAL_CORPUS_FAMILIES.get(corpus_name)
        if exclude_family is None:
            raise ValueError(f"leave-family-out codebook has no family for {corpus_name}")
    elif mode != "global":
        raise ValueError(f"unknown learned public codebook mode: {mode}")

    training_families = [
        family for family in sorted(EXTERNAL_ORDINARY_PATHS) if family != exclude_family
    ]
    tokens = learned_public_tokens(external_ordinary_blobs(exclude_family))
    metadata = {
        "learned_public_codebook_mode": mode,
        "learned_public_training_families": training_families,
        "learned_public_excluded_family": exclude_family,
        "learned_public_token_count": len(tokens),
        "learned_public_min_token_len": LEARNED_PUBLIC_MIN_TOKEN_LEN,
        "learned_public_max_token_len": LEARNED_PUBLIC_MAX_TOKEN_LEN,
        "learned_public_token_limit": LEARNED_PUBLIC_TOKEN_LIMIT,
        "learned_public_tokens_hex": [token.hex() for token in tokens],
    }
    return (
        codewords_for_tokens(
            tokens,
            codeword_variant,
            label=f"learned-public-{mode}-{corpus_name}",
        ),
        metadata,
    )


def codebook_framed(
    data: bytes,
    codebook: dict[bytes, bytes],
    metadata: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    token_order = sorted(codebook, key=len, reverse=True)
    out = bytearray()
    literal = bytearray()
    replacements = 0

    def flush_literal() -> None:
        nonlocal literal
        while literal:
            chunk = bytes(literal[:65535])
            del literal[: len(chunk)]
            out.append(0)
            out.extend(len(chunk).to_bytes(2, "big"))
            out.extend(chunk)

    pos = 0
    while pos < len(data):
        matched = None
        for token in token_order:
            if data.startswith(token, pos):
                matched = token
                break
        if matched is None:
            literal.append(data[pos])
            pos += 1
            continue
        flush_literal()
        out.append(1)
        out.extend(codebook[matched])
        replacements += 1
        pos += len(matched)
    flush_literal()

    return (
        bytes(out),
        {
            **metadata,
            "transform_metadata_bytes": TRANSFORM_METADATA_BYTES,
            "token_replacements": replacements,
            "token_code_span_len": MAX_SPAN_LEN,
        },
    )


def invert_codebook_framed(encoded: bytes, codebook: dict[bytes, bytes]) -> bytes:
    reverse = {span: token for token, span in codebook.items()}
    out = bytearray()
    pos = 0
    while pos < len(encoded):
        tag = encoded[pos]
        pos += 1
        if tag == 0:
            if pos + 2 > len(encoded):
                raise ValueError("truncated literal frame")
            length = int.from_bytes(encoded[pos : pos + 2], "big")
            pos += 2
            out.extend(encoded[pos : pos + length])
            pos += length
        elif tag == 1:
            span = encoded[pos : pos + MAX_SPAN_LEN]
            pos += MAX_SPAN_LEN
            out.extend(reverse[span])
        else:
            raise ValueError(f"unknown frame tag {tag}")
    return bytes(out)


def public_preset_framed(
    data: bytes,
    min_token_len: int = 0,
    codeword_variant: str = "seed",
) -> tuple[bytes, dict[str, Any]]:
    codebook = public_preset_codebook(codeword_variant)
    token_order = sorted(
        [token for token in PUBLIC_PRESET_TOKENS if len(token) >= min_token_len],
        key=len,
        reverse=True,
    )
    out = bytearray()
    literal = bytearray()
    replacements = 0

    def flush_literal() -> None:
        nonlocal literal
        while literal:
            chunk = bytes(literal[:65535])
            del literal[: len(chunk)]
            out.append(0)
            out.extend(len(chunk).to_bytes(2, "big"))
            out.extend(chunk)

    pos = 0
    while pos < len(data):
        matched = None
        for token in token_order:
            if data.startswith(token, pos):
                matched = token
                break
        if matched is None:
            literal.append(data[pos])
            pos += 1
            continue
        flush_literal()
        out.append(1)
        out.extend(codebook[matched])
        replacements += 1
        pos += len(matched)
    flush_literal()
    metadata = {
        "transform_metadata_bytes": TRANSFORM_METADATA_BYTES,
        "public_preset_token_count": len(token_order),
        "public_preset_min_token_len": min_token_len,
        "public_preset_codeword_variant": codeword_variant,
        "token_replacements": replacements,
        "token_code_span_len": MAX_SPAN_LEN,
    }
    return bytes(out), metadata


def invert_public_preset_framed(encoded: bytes, codeword_variant: str = "seed") -> bytes:
    reverse = {
        span: token for token, span in public_preset_codebook(codeword_variant).items()
    }
    out = bytearray()
    pos = 0
    while pos < len(encoded):
        tag = encoded[pos]
        pos += 1
        if tag == 0:
            if pos + 2 > len(encoded):
                raise ValueError("truncated literal frame")
            length = int.from_bytes(encoded[pos : pos + 2], "big")
            pos += 2
            out.extend(encoded[pos : pos + length])
            pos += length
        elif tag == 1:
            span = encoded[pos : pos + MAX_SPAN_LEN]
            pos += MAX_SPAN_LEN
            out.extend(reverse[span])
        else:
            raise ValueError(f"unknown frame tag {tag}")
    return bytes(out)


def transform_variants(name: str, data: bytes) -> list[dict[str, Any]]:
    variants = [
        {
            "transform": "identity",
            "data": data,
            "metadata": {"transform_metadata_bytes": 0},
            "roundtrip_ok": True,
        }
    ]

    delta, delta_meta = xor_delta(data)
    variants.append(
        {
            "transform": "xor-delta1",
            "data": delta,
            "metadata": delta_meta,
            "roundtrip_ok": invert_xor_delta(delta) == data,
        }
    )

    seed_selective_meta: dict[str, Any] | None = None
    seed_selective_len: int | None = None
    for codeword_variant in PUBLIC_PRESET_CODEWORD_VARIANTS:
        suffix = "" if codeword_variant == "seed" else f"-{codeword_variant}"
        framed, framed_meta = public_preset_framed(
            data,
            codeword_variant=codeword_variant,
        )
        variants.append(
            {
                "transform": f"public-preset-framed{suffix}-v0",
                "data": framed,
                "metadata": framed_meta,
                "roundtrip_ok": invert_public_preset_framed(
                    framed,
                    codeword_variant,
                )
                == data,
            }
        )
        selective, selective_meta = public_preset_framed(
            data,
            min_token_len=PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
            codeword_variant=codeword_variant,
        )
        if codeword_variant == "seed":
            seed_selective_meta = selective_meta
            seed_selective_len = len(selective)
        variants.append(
            {
                "transform": f"public-preset-selective{suffix}-v0",
                "data": selective,
                "metadata": selective_meta,
                "roundtrip_ok": invert_public_preset_framed(
                    selective,
                    codeword_variant,
                )
                == data,
            }
        )
    if seed_selective_meta is None or seed_selective_len is None:
        raise AssertionError("seed public preset variant was not generated")
    native_meta = {
        **seed_selective_meta,
        "transform_metadata_bytes": 0,
        "format_native_transform": True,
        "native_transform_transformed_bytes": seed_selective_len,
        "cli_extra_args": ["--transform", "public-preset-selective"],
    }
    variants.append(
        {
            "transform": "public-preset-selective-native-v0",
            "data": data,
            "metadata": native_meta,
            "roundtrip_ok": True,
        }
    )

    for codeword_variant in PUBLIC_PRESET_CODEWORD_VARIANTS:
        suffix = "" if codeword_variant == "seed" else f"-{codeword_variant}"
        global_codebook, global_meta = learned_public_codebook(
            "global",
            name,
            codeword_variant,
        )
        global_framed, global_framed_meta = codebook_framed(
            data,
            global_codebook,
            global_meta,
        )
        variants.append(
            {
                "transform": f"public-learned-global{suffix}-v0",
                "data": global_framed,
                "metadata": {
                    **global_framed_meta,
                    "public_preset_codeword_variant": codeword_variant,
                },
                "roundtrip_ok": invert_codebook_framed(
                    global_framed,
                    global_codebook,
                )
                == data,
            }
        )

        if name in EXTERNAL_CORPUS_FAMILIES:
            lfo_codebook, lfo_meta = learned_public_codebook(
                "lfo",
                name,
                codeword_variant,
            )
            lfo_framed, lfo_framed_meta = codebook_framed(
                data,
                lfo_codebook,
                lfo_meta,
            )
            variants.append(
                {
                    "transform": f"public-learned-lfo{suffix}-v0",
                    "data": lfo_framed,
                    "metadata": {
                        **lfo_framed_meta,
                        "public_preset_codeword_variant": codeword_variant,
                    },
                    "roundtrip_ok": invert_codebook_framed(
                        lfo_framed,
                        lfo_codebook,
                    )
                    == data,
                }
            )
    return variants


def run_telomere(
    data: bytes,
    tmp: Path,
    name: str,
    transform: str,
    extra_args: list[str] | None = None,
    decode_artifact: bool = False,
    literal_probe: bool = False,
) -> dict[str, Any]:
    probe_suffix = "-literal-probe" if literal_probe else ""
    basename = safe_slug(f"{name}-{transform}{probe_suffix}")
    input_path = tmp / f"{basename}.input.bin"
    output_path = tmp / f"{basename}.tlmr"
    decoded_path = tmp / f"{basename}.decoded.bin"
    input_path.write_bytes(data)
    block_size = 1 if literal_probe else BLOCK_SIZE
    max_span_len = 1 if literal_probe else MAX_SPAN_LEN
    cmd = [
        "cargo",
        "run",
        "--quiet",
        "--",
        "compress",
        str(input_path),
        str(output_path),
        "--engine",
        "streaming",
        "--format",
        "v2",
        "--hasher",
        HASHER,
        "--block-size",
        str(block_size),
        "--max-span-len",
        str(max_span_len),
        "--span-step",
        str(SPAN_STEP),
        "--seed-depth",
        str(SEED_DEPTH),
        "--passes",
        str(PASSES),
        "--memory-limit",
        "100%",
        "--telemetry-limit",
        "512",
        "--verify",
        "--json",
        "--force",
    ]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout)
    telemetry = payload.get("engine_telemetry", {})
    result = {
        "command": " ".join(cmd),
        "input_bytes": len(data),
        "tlmr_bytes": output_path.stat().st_size,
        "json_final_bytes": payload["final_bytes"],
        "selected_spans_total": telemetry.get("selected_spans_total", 0),
        "candidate_count": telemetry.get("candidate_count", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "seed_expansions": telemetry.get("seed_expansions", 0),
        "transform_telemetry": telemetry.get("transform"),
        "tiers": telemetry.get("tiers", []),
        "selected_spans": telemetry.get("selected_spans", []),
    }
    if decode_artifact:
        decompress_cmd = [
            "cargo",
            "run",
            "--quiet",
            "--",
            "decompress",
            str(output_path),
            str(decoded_path),
            "--force",
        ]
        subprocess.run(
            decompress_cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        decoded = decoded_path.read_bytes()
        roundtrip_current_binary = decoded == data
        if not roundtrip_current_binary:
            raise RuntimeError(
                f"current binary decompression mismatch for {name}/{transform}"
            )
        result.update(
            {
                "input_path": str(input_path),
                "tlmr_path": str(output_path),
                "decoded_path": str(decoded_path),
                "input_sha256": sha256_bytes(data),
                "tlmr_sha256": sha256(output_path),
                "tlmr_stat_bytes": output_path.stat().st_size,
                "decompress_command": " ".join(decompress_cmd),
                "decoded_sha256": sha256_bytes(decoded),
                "decoded_bytes": len(decoded),
                "roundtrip_current_binary": roundtrip_current_binary,
            }
        )
    return result


def windows_for(input_len: int, span_len: int, span_step: int = SPAN_STEP) -> int:
    if input_len < span_len:
        return 0
    return ((input_len - span_len) // span_step) + 1


def seed_space(max_seed_len: int) -> int:
    return sum(1 << (8 * length) for length in range(1, max_seed_len + 1))


def expected_hit_rows(input_len: int = 1024) -> list[dict[str, Any]]:
    rows = []
    for span_len in (4, 6, 7, 8, 9, 12, 16, 20):
        windows = windows_for(input_len, span_len)
        for depth in (1, 2, 3):
            seeds = seed_space(depth)
            expected_hits = (windows * seeds) / float(1 << (8 * span_len))
            seed_expansions_for_one = (1 << (8 * span_len)) / max(windows, 1)
            arity_grid_reachable = span_len % BLOCK_SIZE == 0
            rows.append(
                {
                    "input_bytes": input_len,
                    "span_len": span_len,
                    "seed_depth": depth,
                    "seed_space": seeds,
                    "target_windows": windows,
                    "arity_grid_reachable_at_block_size": arity_grid_reachable,
                    "expected_exact_hits": expected_hits,
                    "seed_expansions_for_one_expected_hit": seed_expansions_for_one,
                    "depth_space_fraction_for_one_hit": seed_expansions_for_one
                    / seeds,
                }
            )
    return rows


def codeword_control_comparisons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {
        (row["corpus"], row["transform"], row.get("public_preset_codeword_variant")): row
        for row in rows
    }
    comparisons = []
    for row in rows:
        if row.get("public_preset_codeword_variant") != "seed":
            continue
        transform = row["transform"]
        if not transform.startswith("public-") or "native" in transform:
            continue
        controls = []
        for variant in ("random-codeword", "out-of-budget-codeword"):
            control_transform = transform.replace("-v0", f"-{variant}-v0")
            control = by_key.get((row["corpus"], control_transform, variant))
            if control is None:
                continue
            controls.append(
                {
                    "variant": variant,
                    "control_delta_bytes": control["delta_bytes"],
                    "control_selected_spans": control["selected_spans_total"],
                    "real_minus_control_charged_bytes": row["charged_output_bytes"]
                    - control["charged_output_bytes"],
                    "real_minus_control_selected_spans": row["selected_spans_total"]
                    - control["selected_spans_total"],
                }
            )
        if controls:
            comparisons.append(
                {
                    "corpus": row["corpus"],
                    "transform": transform,
                    "real_delta_bytes": row["delta_bytes"],
                    "real_selected_spans": row["selected_spans_total"],
                    "controls": controls,
                    "beats_all_controls": all(
                        control["real_minus_control_charged_bytes"] < 0
                        for control in controls
                    ),
                    "controls_are_span_null": all(
                        control["control_selected_spans"] == 0 for control in controls
                    ),
                }
            )
    return comparisons


def build_rows(corpora: dict[str, bytes], tmp: Path, decode_artifacts: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for corpus_name, original in corpora.items():
        for variant in transform_variants(corpus_name, original):
            result = run_telomere(
                variant["data"],
                tmp,
                corpus_name,
                variant["transform"],
                variant["metadata"].get("cli_extra_args"),
                decode_artifact=decode_artifacts,
            )
            metadata_bytes = int(variant["metadata"].get("transform_metadata_bytes", 0))
            charged_bytes = result["tlmr_bytes"] + metadata_bytes
            literal_probe = run_telomere(
                variant["data"],
                tmp,
                corpus_name,
                variant["transform"],
                variant["metadata"].get("cli_extra_args"),
                literal_probe=True,
            )
            literal_only_charged_bytes = int(
                literal_probe["tlmr_bytes"] + metadata_bytes
            )
            rows.append(
                {
                    "corpus": corpus_name,
                    "transform": variant["transform"],
                    "original_bytes": len(original),
                    "transformed_bytes": len(variant["data"]),
                    "transform_metadata_bytes": metadata_bytes,
                    "literal_only_charged_bytes": literal_only_charged_bytes,
                    "seed_span_benefit_bytes": literal_only_charged_bytes - charged_bytes,
                    "charged_output_bytes": charged_bytes,
                    "literal_probe_tlmr_bytes": literal_probe["tlmr_bytes"],
                    "literal_probe_json_final_bytes": literal_probe["json_final_bytes"],
                    "delta_bytes": charged_bytes - len(original),
                    "delta_pct": (charged_bytes - len(original)) * 100.0 / max(len(original), 1),
                    "roundtrip_ok": variant["roundtrip_ok"],
                    "roundtrip_to_original": variant["roundtrip_ok"]
                    and result.get("roundtrip_current_binary", True),
                    **variant["metadata"],
                    **result,
                }
            )
    return rows


def build_report(
    artifact_dir: Path | None = None,
    include_target_inputs: list[Path] | None = None,
    manifest_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    corpora = load_corpora(include_target_inputs)
    if artifact_dir is None:
        with tempfile.TemporaryDirectory(prefix="telomere-thesis-") as tmp_dir:
            rows = build_rows(corpora, Path(tmp_dir), decode_artifacts=False)
    else:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        rows = build_rows(corpora, artifact_dir, decode_artifacts=True)

    non_planted = [
        row
        for row in rows
        if row["corpus"] != "planted-positive"
        and row["transform"] != "identity"
    ]
    exact_non_planted = [
        row for row in non_planted if row["selected_spans_total"] > 0
    ]
    profitable_non_planted = [
        row for row in non_planted if row["delta_bytes"] < 0
    ]
    control_comparisons = codeword_control_comparisons(rows)
    codeword_control_rows = [
        row
        for row in non_planted
        if row.get("public_preset_codeword_variant")
        in ("random-codeword", "out-of-budget-codeword")
    ]
    learned_public_seed_rows = [
        row
        for row in non_planted
        if row.get("public_preset_codeword_variant") == "seed"
        and row["transform"].startswith("public-learned-")
    ]
    learned_public_profitable_seed_rows = [
        row for row in learned_public_seed_rows if row["delta_bytes"] < 0
    ]
    learned_public_lfo_seed_rows = [
        row
        for row in learned_public_seed_rows
        if row.get("learned_public_codebook_mode") == "lfo"
    ]
    learned_public_control_wins = [
        row
        for row in control_comparisons
        if row["transform"].startswith("public-learned-")
        and row["beats_all_controls"]
        and row["controls_are_span_null"]
    ]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "kind": "thesis attack experiment",
            "broad_depth_search": False,
            "seed_depth": SEED_DEPTH,
            "records_new_measurement": True,
            "claims_current_architecture_viable": False,
        },
        "source_hashes": {
            "script_sha256": sha256(Path(__file__)),
            "generate_results_sha256": sha256(ROOT / "scripts/generate_results.py"),
            "streaming_rs_sha256": sha256(ROOT / "src/streaming.rs"),
            "tlmr_v2_rs_sha256": sha256(ROOT / "src/tlmr_v2.rs"),
            "external_manifest_sha256": sha256(ROOT / "corpora/external/manifest.json"),
        },
        "artifact_mode": {
            "enabled": artifact_dir is not None,
            "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
            "manifest_validation": manifest_validation,
            "included_target_input_paths": [
                str(path) for path in (include_target_inputs or [])
            ],
        },
        "math": {
            "formula": "expected_hits = target_windows * seed_space / 2^(8 * span_len)",
            "literal_baseline": "measured with the current CLI encoder using block_size=1 and max_span_len=1 so no seed-span can be profitable",
            "v2_seed_span_record_bytes": "variable Lotus bit length; exact output bytes come from the current encoder",
            "rows": expected_hit_rows(),
        },
        "experiment_config": {
            "engine": "streaming",
            "format": "v2",
            "hasher": HASHER,
            "block_size": BLOCK_SIZE,
            "max_span_len": MAX_SPAN_LEN,
            "span_step": SPAN_STEP,
            "seed_depth": SEED_DEPTH,
            "passes": PASSES,
            "cli_tier_policy": "arity-grid",
            "research_profit_window_policy": "library-only exact scanner for spans 6..=max_span_len",
            "transform_metadata_bytes_for_public_preset": TRANSFORM_METADATA_BYTES,
            "public_preset_token_count": len(PUBLIC_PRESET_TOKENS),
            "public_preset_selective_min_token_len": PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
            "learned_public_min_token_len": LEARNED_PUBLIC_MIN_TOKEN_LEN,
            "learned_public_max_token_len": LEARNED_PUBLIC_MAX_TOKEN_LEN,
            "learned_public_token_limit": LEARNED_PUBLIC_TOKEN_LIMIT,
        },
        "summary": {
            "row_count": len(rows),
            "planted_positive_rows": len([row for row in rows if row["corpus"] == "planted-positive"]),
            "non_planted_rows": len([row for row in rows if row["corpus"] != "planted-positive"]),
            "non_planted_exact_span_rows": len(exact_non_planted),
            "non_planted_profitable_rows": len(profitable_non_planted),
            "codeword_control_rows": len(codeword_control_rows),
            "codeword_control_exact_span_rows": len(
                [
                    row
                    for row in codeword_control_rows
                    if row["selected_spans_total"] > 0
                ]
            ),
            "codeword_control_profitable_rows": len(
                [row for row in codeword_control_rows if row["delta_bytes"] < 0]
            ),
            "seed_rows_beating_all_codeword_controls": len(
                [
                    row
                    for row in control_comparisons
                    if row["beats_all_controls"] and row["controls_are_span_null"]
                ]
            ),
            "learned_public_seed_rows": len(learned_public_seed_rows),
            "learned_public_profitable_seed_rows": len(
                learned_public_profitable_seed_rows
            ),
            "learned_public_exact_span_seed_rows": len(
                [
                    row
                    for row in learned_public_seed_rows
                    if row["selected_spans_total"] > 0
                ]
            ),
            "learned_public_lfo_exact_span_seed_rows": len(
                [
                    row
                    for row in learned_public_lfo_seed_rows
                    if row["selected_spans_total"] > 0
                ]
            ),
            "learned_public_rows_beating_all_codeword_controls": len(
                learned_public_control_wins
            ),
            "best_non_planted_delta_bytes": min(
                (row["delta_bytes"] for row in non_planted), default=None
            ),
            "best_non_planted_row": min(
                non_planted,
                key=lambda row: row["delta_bytes"],
                default=None,
            ),
            "conclusion": (
                "public preset and learned public codebook produced seed-specific profitable non-planted rows"
                if learned_public_control_wins
                else "public-preset transform produced profitable non-planted rows"
                if profitable_non_planted
                else "current hash-only and tested transforms did not produce profitable non-planted rows"
            ),
        },
        "codeword_control_comparisons": control_comparisons,
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Thesis Attack Experiment",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "This records a focused mechanism experiment, not a production or natural-corpus proof claim.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Non-planted rows with exact selected spans: `{summary['non_planted_exact_span_rows']}`",
        f"- Non-planted profitable rows after charged `.tlmr` accounting: `{summary['non_planted_profitable_rows']}`",
        f"- Non-seed codeword control rows with exact selected spans: `{summary['codeword_control_exact_span_rows']}`",
        f"- Non-seed codeword control rows profitable after charged accounting: `{summary['codeword_control_profitable_rows']}`",
        f"- Seed rows beating all same-token codeword controls: `{summary['seed_rows_beating_all_codeword_controls']}`",
        f"- Learned public seed rows with exact selected spans: `{summary['learned_public_exact_span_seed_rows']}`",
        f"- Learned public seed rows profitable after charged accounting: `{summary['learned_public_profitable_seed_rows']}`",
        f"- Learned leave-family-out seed rows with exact selected spans: `{summary['learned_public_lfo_exact_span_seed_rows']}`",
        f"- Learned public rows beating all same-token codeword controls: `{summary['learned_public_rows_beating_all_codeword_controls']}`",
        f"- Best non-planted delta bytes: `{summary['best_non_planted_delta_bytes']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Bottleneck Math",
        "",
        "- Expected exact hits: `target_windows * seed_space / 2^(8 * span_len)`.",
        "- v2 seed-span record bytes are variable Lotus bit lengths; actual row output bytes come from the current encoder.",
        "- Literal-only charged bytes are measured by a real CLI probe using `block_size=1` and `max_span_len=1`, so no seed-span can be profitable.",
        "- This table is probability-only; profitability is decided by actual `.tlmr` rows and same-token controls.",
        "",
        "| span | depth | seed space | windows @1KiB | expected hits | seed expansions for one expected hit | arity grid reachable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["math"]["rows"]:
        lines.append(
            "| {span_len} | {seed_depth} | {seed_space} | {target_windows} | {expected_exact_hits:.3e} | {seed_expansions_for_one_expected_hit:.3e} | `{arity_grid_reachable_at_block_size}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Experiment Rows",
            "",
            "| corpus | transform | original | transformed | selected spans | candidates | literal-only charged | charged bytes | seed-span benefit | delta | token replacements |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["rows"]:
        rendered = dict(row)
        rendered.setdefault("token_replacements", 0)
        lines.append(
            "| `{corpus}` | `{transform}` | {original_bytes} | {transformed_bytes} | {selected_spans_total} | {candidate_count} | {literal_only_charged_bytes} | {charged_output_bytes} | {seed_span_benefit_bytes} | {delta_bytes} | {token_replacements} |".format(
                **rendered,
            )
        )
    lines.extend(
        [
            "",
            "## Codeword Control Comparisons",
            "",
            "| corpus | transform | seed delta | selected spans | random control delta | out-of-budget control delta | best seed-vs-control bytes | controls span-null |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["codeword_control_comparisons"]:
        control_by_variant = {control["variant"]: control for control in row["controls"]}
        random_control = control_by_variant.get("random-codeword", {})
        out_of_budget = control_by_variant.get("out-of-budget-codeword", {})
        best_delta = min(
            (
                control["real_minus_control_charged_bytes"]
                for control in row["controls"]
            ),
            default=0,
        )
        lines.append(
            "| {corpus} | `{transform}` | {real_delta_bytes} | {real_selected_spans} | {random_delta} | {out_delta} | {best_delta} | `{span_null}` |".format(
                corpus=row["corpus"],
                transform=row["transform"],
                real_delta_bytes=row["real_delta_bytes"],
                real_selected_spans=row["real_selected_spans"],
                random_delta=random_control.get("control_delta_bytes"),
                out_delta=out_of_budget.get("control_delta_bytes"),
                best_delta=best_delta,
                span_null=row["controls_are_span_null"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Identity and xor-delta rows test whether current hash-only search or a simple reversible bijection beats random chance.",
            "- `public-preset-framed-v0` is a next-architecture probe: it intentionally maps public grammar tokens to SHA-256 seed spans, charges a small transform descriptor, then lets `.tlmr` v2 account for the generated spans.",
            f"- `public-preset-selective-v0` keeps that mechanism but only replaces tokens with length at least `{PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN}` so each replacement has positive framing margin.",
            "- `public-preset-selective-native-v0` uses the Rust v2 transform layer; `telomere decompress` returns the original bytes without the Python harness.",
            "- `public-learned-global-v0` learns a deterministic public codebook from external ordinary corpora, then maps those learned spans to in-budget seed expansions.",
            "- `public-learned-lfo-v0` repeats that learned-codebook test while leaving the current external corpus family out of the training set, so it measures cross-family generalization instead of same-family memorization.",
            f"- Learned public tokens are capped at `{LEARNED_PUBLIC_MAX_TOKEN_LEN}` bytes so same-token non-seed controls cannot win merely by replacing long source tokens with shorter opaque codewords.",
            "- `seed-span benefit` compares the actual `.tlmr` bytes against a literal-only v2 container for the same transformed representation.",
            "- Same-token `random-codeword` and `out-of-budget-codeword` rows are codeword controls: they preserve transform opportunities while removing in-budget seed-generated spans.",
            "- If random/null rows become profitable under the public preset, the dictionary is too broad or the accounting is broken.",
            "- If only structured rows improve, the viable thesis shifts from raw hash coincidence to public preset/grammar transforms that manufacture decoder-known seed-span density.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Persist experiment inputs, .tlmr outputs, decoded outputs, and hashes here.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Fail closed unless every external-corpus manifest entry matches checkout bytes.",
    )
    parser.add_argument(
        "--include-target-inputs",
        type=Path,
        action="append",
        default=[],
        help="Also run supported input files from this file or directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the full JSON payload to this path instead of only docs/default summary output.",
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Do not rewrite docs/thesis_attack_experiment.*.",
    )
    args = parser.parse_args()

    manifest_validation = None
    if args.manifest is not None:
        manifest_validation = validate_external_manifest(args.manifest)
    payload = build_report(
        artifact_dir=args.artifact_dir,
        include_target_inputs=args.include_target_inputs,
        manifest_validation=manifest_validation,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not args.no_docs and not args.json_only:
        write_report(payload)
    if args.json_only:
        print(json.dumps(payload["summary"], indent=2))
    else:
        outputs = []
        if not args.no_docs:
            outputs.append(str(REPORT_JSON.relative_to(ROOT)))
            outputs.append(str(REPORT_MD.relative_to(ROOT)))
        if args.output is not None:
            outputs.append(str(args.output))
        if args.artifact_dir is not None:
            outputs.append(str(args.artifact_dir))
        print("Thesis attack experiment wrote " + ", ".join(outputs))


if __name__ == "__main__":
    main()
