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
import math
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_bytes(label: str, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(f"{label}:{counter}".encode("utf-8")).digest())
        counter += 1
    return bytes(out[:length])


def seed_span(seed: bytes, span_len: int = MAX_SPAN_LEN) -> bytes:
    return hashlib.sha256(seed).digest()[:span_len]


def planted_positive() -> bytes:
    out = bytearray()
    for idx in range(128):
        out.extend(seed_span(bytes([idx % 64])))
    return bytes(out)


def load_corpora() -> dict[str, bytes]:
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


def public_preset_codebook() -> dict[bytes, bytes]:
    return {
        token: seed_span(bytes([idx]))
        for idx, token in enumerate(PUBLIC_PRESET_TOKENS)
    }


def public_preset_framed(
    data: bytes,
    min_token_len: int = 0,
) -> tuple[bytes, dict[str, Any]]:
    codebook = public_preset_codebook()
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
        "token_replacements": replacements,
        "token_code_span_len": MAX_SPAN_LEN,
    }
    return bytes(out), metadata


def v2_literal_only_bytes(payload_len: int, layer_count: int) -> int:
    if payload_len == 0:
        literal_records = 0
    else:
        literal_records = math.ceil(payload_len / 65535)
    return 48 + (32 * layer_count) + payload_len + (3 * literal_records)


def invert_public_preset_framed(encoded: bytes) -> bytes:
    reverse = {span: token for token, span in public_preset_codebook().items()}
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

    framed, framed_meta = public_preset_framed(data)
    variants.append(
        {
            "transform": "public-preset-framed-v0",
            "data": framed,
            "metadata": framed_meta,
            "roundtrip_ok": invert_public_preset_framed(framed) == data,
        }
    )
    selective, selective_meta = public_preset_framed(
        data,
        min_token_len=PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
    )
    variants.append(
        {
            "transform": "public-preset-selective-v0",
            "data": selective,
            "metadata": selective_meta,
            "roundtrip_ok": invert_public_preset_framed(selective) == data,
        }
    )
    native_meta = {
        **selective_meta,
        "transform_metadata_bytes": 0,
        "format_native_transform": True,
        "native_transform_transformed_bytes": len(selective),
        "native_transform_literal_only_bytes": v2_literal_only_bytes(len(selective), 2),
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
    return variants


def run_telomere(
    data: bytes,
    tmp: Path,
    name: str,
    transform: str,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    input_path = tmp / f"{name}-{transform}.bin"
    output_path = tmp / f"{name}-{transform}.tlmr"
    input_path.write_bytes(data)
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
        str(BLOCK_SIZE),
        "--max-span-len",
        str(MAX_SPAN_LEN),
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
    return {
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
                    "v2_seed_record_bytes_for_longest_seed": 4 + depth,
                    "local_profitable_for_longest_seed": span_len > 4 + depth,
                    "expected_exact_hits": expected_hits,
                    "seed_expansions_for_one_expected_hit": seed_expansions_for_one,
                    "depth_space_fraction_for_one_hit": seed_expansions_for_one
                    / seeds,
                }
            )
    return rows


def build_report() -> dict[str, Any]:
    corpora = load_corpora()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="telomere-thesis-") as tmp_dir:
        tmp = Path(tmp_dir)
        for corpus_name, original in corpora.items():
            for variant in transform_variants(corpus_name, original):
                result = run_telomere(
                    variant["data"],
                    tmp,
                    corpus_name,
                    variant["transform"],
                    variant["metadata"].get("cli_extra_args"),
                )
                metadata_bytes = int(variant["metadata"].get("transform_metadata_bytes", 0))
                charged_bytes = result["tlmr_bytes"] + metadata_bytes
                literal_only_charged_bytes = int(
                    variant["metadata"].get(
                        "native_transform_literal_only_bytes",
                        v2_literal_only_bytes(len(variant["data"]), 1) + metadata_bytes,
                    )
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
                        "delta_bytes": charged_bytes - len(original),
                        "delta_pct": (charged_bytes - len(original)) * 100.0 / max(len(original), 1),
                        "roundtrip_ok": variant["roundtrip_ok"],
                        **variant["metadata"],
                        **result,
                    }
                )

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
        "math": {
            "formula": "expected_hits = target_windows * seed_space / 2^(8 * span_len)",
            "v2_seed_span_record_bytes": "4 + seed_len",
            "v2_container_bytes_one_layer": 80,
            "literal_record_overhead_bytes": 3,
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
        },
        "summary": {
            "row_count": len(rows),
            "planted_positive_rows": len([row for row in rows if row["corpus"] == "planted-positive"]),
            "non_planted_rows": len([row for row in rows if row["corpus"] != "planted-positive"]),
            "non_planted_exact_span_rows": len(exact_non_planted),
            "non_planted_profitable_rows": len(profitable_non_planted),
            "best_non_planted_delta_bytes": min(
                (row["delta_bytes"] for row in non_planted), default=None
            ),
            "best_non_planted_row": min(
                non_planted,
                key=lambda row: row["delta_bytes"],
                default=None,
            ),
            "conclusion": (
                "public-preset transform produced profitable non-planted rows"
                if profitable_non_planted
                else "current hash-only and tested transforms did not produce profitable non-planted rows"
            ),
        },
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
        f"- Best non-planted delta bytes: `{summary['best_non_planted_delta_bytes']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Bottleneck Math",
        "",
        "- Expected exact hits: `target_windows * seed_space / 2^(8 * span_len)`.",
        "- v2 seed-span record bytes: `4 + seed_len`.",
        "- A one-layer v2 container costs `80` bytes before payload.",
        "- Literal records cost `3` bytes plus literal payload.",
        "- `span=6` and `span=7` are shortest profitable windows for 1-byte and 2-byte seeds, but are skipped by the default `block_size=4` arity grid.",
        "",
        "| span | depth | seed space | windows @1KiB | expected hits | seed expansions for one expected hit | arity grid reachable | locally profitable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["math"]["rows"]:
        lines.append(
            "| {span_len} | {seed_depth} | {seed_space} | {target_windows} | {expected_exact_hits:.3e} | {seed_expansions_for_one_expected_hit:.3e} | `{arity_grid_reachable_at_block_size}` | `{local_profitable_for_longest_seed}` |".format(
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
            "## Interpretation",
            "",
            "- Identity and xor-delta rows test whether current hash-only search or a simple reversible bijection beats random chance.",
            "- `public-preset-framed-v0` is a next-architecture probe: it intentionally maps public grammar tokens to SHA-256 seed spans, charges a small transform descriptor, then lets `.tlmr` v2 account for the generated spans.",
            f"- `public-preset-selective-v0` keeps that mechanism but only replaces tokens with length at least `{PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN}` so each replacement has positive framing margin.",
            "- `public-preset-selective-native-v0` uses the Rust v2 transform layer; `telomere decompress` returns the original bytes without the Python harness.",
            "- `seed-span benefit` compares the actual `.tlmr` bytes against a literal-only v2 container for the same transformed representation.",
            "- If random/null rows become profitable under the public preset, the dictionary is too broad or the accounting is broken.",
            "- If only structured rows improve, the viable thesis shifts from raw hash coincidence to public preset/grammar transforms that manufacture decoder-known seed-span density.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()
    payload = build_report()
    write_report(payload)
    if args.json_only:
        print(json.dumps(payload["summary"], indent=2))
    else:
        print(
            "Thesis attack experiment wrote "
            f"{REPORT_JSON.relative_to(ROOT)} and {REPORT_MD.relative_to(ROOT)}"
        )


if __name__ == "__main__":
    main()
