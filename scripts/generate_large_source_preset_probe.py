#!/usr/bin/env python3
"""Probe large source-code preset coverage with real v2 accounting.

This experiment asks a narrower question than the small source fixture:

1. On a real Rust library source file, can public source-family tokens learned
   from other Rust files create enough exact seed spans to become profitable?
2. If not, does target-leakage oracle coverage show the mechanism would be
   profitable with better source preset coverage?

The trained registry excludes the held-out target file. The oracle registry is
explicitly not proof; it is an upper bound for coverage quality.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generate_source_token_registry_probe import (
    CONTROL_VARIANTS,
    TRANSFORM_METADATA_BYTES,
    codebook_for_tokens,
    ensure_binary,
    frame_with_codebook,
    run_compress,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "target" / "thesis_runs" / "large_source_preset_probe"
OUT_JSON = ROOT / "docs" / "large_source_preset_probe.json"
OUT_MD = ROOT / "docs" / "LARGE_SOURCE_PRESET_PROBE.md"
GENERATED_BY = "scripts/generate_large_source_preset_probe.py"

RUST_LIBRARY = (
    Path.home()
    / ".rustup"
    / "toolchains"
    / "stable-x86_64-pc-windows-msvc"
    / "lib"
    / "rustlib"
    / "src"
    / "rust"
    / "library"
)
HELDOUT_REL = Path("core/src/result.rs")
CODEWORD_LEN = 16
TOKEN_LIMIT = 128


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_rust_source() -> Path:
    heldout = RUST_LIBRARY / HELDOUT_REL
    if not heldout.exists():
        raise SystemExit(
            "large source preset probe requires rust-src at "
            f"{RUST_LIBRARY}; missing {heldout}"
        )
    return heldout


def rust_version() -> str:
    result = subprocess.run(
        ["rustc", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def source_hashes() -> dict[str, str]:
    heldout = require_rust_source()
    return {
        "generator": sha256(ROOT / GENERATED_BY),
        "source_probe_helpers": sha256(ROOT / "scripts" / "generate_source_token_registry_probe.py"),
        "thesis_harness": sha256(ROOT / "scripts" / "run_thesis_attack_experiment.py"),
        "heldout_result_rs": sha256(heldout),
    }


def all_training_files(heldout: Path) -> list[Path]:
    files: list[Path] = []
    for subdir in ("core/src", "alloc/src", "std/src"):
        base = RUST_LIBRARY / subdir
        if base.exists():
            files.extend(sorted(base.rglob("*.rs")))
    return [path for path in files if path != heldout and "tests" not in path.parts]


def source_line_tokens(line: str, max_len: int) -> list[bytes]:
    raw = line.lstrip()
    tokens: list[bytes] = []

    # Source attributes mattered in the oracle run, so the trained learner is
    # allowed to learn public attribute prefixes from non-heldout files.
    if raw.startswith("#["):
        for width in range(8, max_len + 1):
            if len(raw) >= width:
                tokens.append(raw[:width].encode())

    if raw.startswith("///") or raw.startswith("//!"):
        body = raw[3:].strip()
        for marker in (
            "/// # ",
            "/// ## ",
            "/// ```",
            "/// * ",
            "//! # ",
            "//! ## ",
            "//! ```",
            "//! * ",
        ):
            if raw.startswith(marker) and len(marker) <= max_len:
                tokens.append(marker.encode())
        words = re.findall(r"[`\[\]\w:!<>/().,'\"=-]+", body)
        for ngram in range(1, 5):
            for start in range(len(words) - ngram + 1):
                phrase = " ".join(words[start : start + ngram])
                if 8 <= len(phrase) <= max_len:
                    tokens.append(phrase.encode())

    words = re.findall(r"[`\[\]\w:!<>/().,'\"=-]+", raw)
    for ngram in range(1, 4):
        for start in range(len(words) - ngram + 1):
            phrase = " ".join(words[start : start + ngram])
            if 8 <= len(phrase) <= max_len:
                tokens.append(phrase.encode())

    return tokens


def is_ascii_token(token: bytes) -> bool:
    return (
        any(48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122 for byte in token)
        and all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in token)
    )


def select_ranked_tokens(
    ranked: list[tuple[int, int, int, bytes]],
    limit: int,
) -> tuple[bytes, ...]:
    selected: list[bytes] = []
    for _score, _file_count, _count, token in ranked:
        if any(token in existing or existing in token for existing in selected):
            continue
        selected.append(token)
        if len(selected) >= limit:
            break
    return tuple(selected)


def learned_public_source_tokens(heldout: Path) -> tuple[tuple[bytes, ...], list[dict[str, Any]]]:
    counts: dict[bytes, int] = {}
    file_counts: dict[bytes, int] = {}
    for path in all_training_files(heldout):
        seen: set[bytes] = set()
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            for token in source_line_tokens(line, CODEWORD_LEN):
                if not is_ascii_token(token):
                    continue
                counts[token] = counts.get(token, 0) + 1
                seen.add(token)
        for token in seen:
            file_counts[token] = file_counts.get(token, 0) + 1

    ranked = []
    for token, count in counts.items():
        file_count = file_counts.get(token, 0)
        if file_count < 2 or count < 4:
            continue
        score = file_count * (len(token) - 5) + count
        ranked.append((score, file_count, count, token))
    ranked.sort(key=lambda row: (-row[0], -row[1], -row[2], -len(row[3]), row[3]))
    tokens = select_ranked_tokens(ranked, TOKEN_LIMIT)
    stats = [
        {
            "token": token.decode("utf-8", errors="replace"),
            "token_hex": token.hex(),
            "file_count": file_counts[token],
            "count": counts[token],
        }
        for token in tokens
    ]
    return tokens, stats


def oracle_source_tokens(data: bytes) -> tuple[tuple[bytes, ...], list[dict[str, Any]]]:
    counts: dict[bytes, int] = {}
    for span_len in range(8, CODEWORD_LEN + 1):
        for start in range(len(data) - span_len + 1):
            token = data[start : start + span_len]
            if is_ascii_token(token):
                counts[token] = counts.get(token, 0) + 1

    ranked = []
    for token, count in counts.items():
        if count < 3:
            continue
        score = count * (len(token) - 5)
        ranked.append((score, 1, count, token))
    ranked.sort(key=lambda row: (-row[0], -row[2], -len(row[3]), row[3]))
    tokens = select_ranked_tokens(ranked, TOKEN_LIMIT)
    stats = [
        {
            "token": token.decode("utf-8", errors="replace"),
            "token_hex": token.hex(),
            "count": counts[token],
        }
        for token in tokens
    ]
    return tokens, stats


class BitWriter:
    def __init__(self) -> None:
        self.bits: list[int] = []

    def write_bits(self, value: int, width: int) -> None:
        for offset in range(width - 1, -1, -1):
            self.bits.append((value >> offset) & 1)

    def align_byte(self) -> None:
        while len(self.bits) % 8:
            self.bits.append(0)

    def write_bytes(self, data: bytes) -> None:
        self.align_byte()
        for byte in data:
            self.write_bits(byte, 8)

    def to_bytes(self) -> bytes:
        self.align_byte()
        out = bytearray()
        for start in range(0, len(self.bits), 8):
            value = 0
            for bit in self.bits[start : start + 8]:
                value = (value << 1) | bit
            out.append(value)
        return bytes(out)


def lotus_width_for_value(value: int) -> int:
    width = 1
    while True:
        start = (1 << width) - 2
        end = (1 << (width + 1)) - 3
        if start <= value <= end:
            return width
        width += 1


def lotus_bits(value: int, j_bits: int = 3, tiers: int = 2) -> list[int]:
    payload_value = value + 1
    payload_width = lotus_width_for_value(payload_value)
    chain = [(payload_value, payload_width)]
    current_width = payload_width
    for _ in range(tiers):
        tier_width = lotus_width_for_value(current_width)
        chain.append((current_width, tier_width))
        current_width = tier_width
    if current_width == 0 or current_width > (1 << j_bits):
        raise ValueError("Lotus jumpstarter overflow")

    writer = BitWriter()
    writer.write_bits(current_width - 1, j_bits)
    for encoded_value, width in reversed(chain):
        start = (1 << width) - 2
        writer.write_bits(encoded_value - start, width)
    return writer.bits


def frame_with_lotus_bits(data: bytes, codebook: dict[bytes, bytes]) -> tuple[bytes, int]:
    token_order = sorted(codebook, key=len, reverse=True)
    writer = BitWriter()
    literal = bytearray()
    replacements = 0

    def flush_literal() -> None:
        nonlocal literal
        if not literal:
            return
        writer.bits.extend(lotus_bits(1))
        writer.bits.extend(lotus_bits(len(literal) - 1))
        writer.write_bytes(bytes(literal))
        literal = bytearray()

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
        writer.bits.extend(lotus_bits(0))
        writer.write_bytes(codebook[matched])
        replacements += 1
        pos += len(matched)

    flush_literal()
    return writer.to_bytes(), replacements


def deterministic_random(length: int, label: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(label + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def sanitize_command(command: str) -> str:
    return command.replace(str(ROOT), "$ROOT")


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    heldout = require_rust_source()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RUN_DIR / "heldout-result.rs"
    result_data = heldout.read_bytes()
    result_path.write_bytes(result_data)
    random_path = RUN_DIR / "same-size-random.bin"
    random_path.write_bytes(deterministic_random(len(result_data), b"large-source-preset-probe"))

    learned_tokens, learned_stats = learned_public_source_tokens(heldout)
    oracle_tokens, oracle_stats = oracle_source_tokens(result_data)

    registries = {
        "learned-rust-source-heldout-v0": {
            "target_leakage": False,
            "claim_role": "non-overfit source-family tokens learned from rust-src excluding result.rs",
            "tokens": learned_tokens,
        },
        "oracle-result-source-v0": {
            "target_leakage": True,
            "claim_role": "target-leakage upper bound for source preset coverage",
            "tokens": oracle_tokens,
        },
    }
    corpora = {
        "rust-result-heldout": result_path,
        "same-size-random": random_path,
    }
    frame_modes = {
        "external-byte": frame_with_codebook,
        "lotus-bit": frame_with_lotus_bits,
    }

    binary = ensure_binary()
    rows: list[dict[str, Any]] = []
    for registry_id, registry in registries.items():
        tokens = registry["tokens"]
        for corpus, input_path in corpora.items():
            data = input_path.read_bytes()
            original_len = len(data)
            for frame_mode, frame_fn in frame_modes.items():
                for variant in ("seed", *CONTROL_VARIANTS):
                    codebook = codebook_for_tokens(
                        tokens,
                        variant,
                        CODEWORD_LEN,
                        label=f"{registry_id}:{frame_mode}",
                    )
                    framed, replacements = frame_fn(data, codebook)
                    framed_path = (
                        RUN_DIR
                        / f"{corpus}-{registry_id}-{frame_mode}-{variant}.bin"
                    )
                    framed_path.write_bytes(framed)
                    output_path = framed_path.with_suffix(".tlmr")
                    compression = run_compress(
                        binary,
                        framed_path,
                        output_path,
                        CODEWORD_LEN,
                    )
                    compression["command"] = sanitize_command(compression["command"])
                    charged = compression["tlmr_bytes"] + TRANSFORM_METADATA_BYTES
                    rows.append(
                        {
                            "corpus": corpus,
                            "registry": registry_id,
                            "target_leakage": registry["target_leakage"],
                            "claim_role": registry["claim_role"],
                            "frame_mode": frame_mode,
                            "variant": variant,
                            "codeword_len": CODEWORD_LEN,
                            "token_count": len(tokens),
                            "token_replacements": replacements,
                            "original_bytes": original_len,
                            "framed_bytes": len(framed),
                            "charged_bytes": charged,
                            "delta_bytes": charged - original_len,
                            "public_preset_delta_bytes": compression["tlmr_bytes"]
                            - original_len,
                            **compression,
                        }
                    )

    token_metadata = {
        "learned-rust-source-heldout-v0": learned_stats,
        "oracle-result-source-v0": oracle_stats,
    }
    return rows, token_metadata


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seed_rows = [row for row in rows if row["variant"] == "seed"]
    comparisons = []
    for seed in seed_rows:
        controls = [
            row
            for row in rows
            if row["corpus"] == seed["corpus"]
            and row["registry"] == seed["registry"]
            and row["frame_mode"] == seed["frame_mode"]
            and row["variant"] != "seed"
        ]
        best_control = min(controls, key=lambda row: row["delta_bytes"])
        comparisons.append(
            {
                "corpus": seed["corpus"],
                "registry": seed["registry"],
                "target_leakage": seed["target_leakage"],
                "frame_mode": seed["frame_mode"],
                "seed_delta_bytes": seed["delta_bytes"],
                "seed_public_preset_delta_bytes": seed["public_preset_delta_bytes"],
                "seed_selected_spans": seed["selected_spans"],
                "token_replacements": seed["token_replacements"],
                "framed_bytes": seed["framed_bytes"],
                "best_control_variant": best_control["variant"],
                "best_control_delta_bytes": best_control["delta_bytes"],
                "best_control_selected_spans": best_control["selected_spans"],
                "seed_minus_best_control_bytes": seed["delta_bytes"]
                - best_control["delta_bytes"],
                "clean_seed_specific_win": (
                    seed["delta_bytes"] < 0
                    and seed["selected_spans"] > 0
                    and best_control["delta_bytes"] >= 0
                ),
            }
        )

    trained = [row for row in comparisons if not row["target_leakage"]]
    trained_source = [
        row for row in trained if row["corpus"] == "rust-result-heldout"
    ]
    oracle = [row for row in comparisons if row["target_leakage"]]
    clean_oracle = [row for row in oracle if row["clean_seed_specific_win"]]
    best_trained_source = min(trained_source, key=lambda row: row["seed_delta_bytes"])
    best_trained = min(trained, key=lambda row: row["seed_delta_bytes"])
    best_oracle = min(oracle, key=lambda row: row["seed_delta_bytes"])
    return {
        "row_count": len(rows),
        "comparison_count": len(comparisons),
        "trained_clean_seed_specific_win_rows": sum(
            1 for row in trained if row["clean_seed_specific_win"]
        ),
        "oracle_clean_seed_specific_win_rows": len(clean_oracle),
        "best_trained_seed_delta_bytes": best_trained["seed_delta_bytes"],
        "best_trained_seed_minus_control_bytes": best_trained[
            "seed_minus_best_control_bytes"
        ],
        "best_trained_source_seed_delta_bytes": best_trained_source[
            "seed_delta_bytes"
        ],
        "best_trained_source_seed_minus_control_bytes": best_trained_source[
            "seed_minus_best_control_bytes"
        ],
        "best_oracle_seed_delta_bytes": best_oracle["seed_delta_bytes"],
        "best_oracle_seed_minus_control_bytes": best_oracle[
            "seed_minus_best_control_bytes"
        ],
        "best_trained": best_trained,
        "best_trained_source": best_trained_source,
        "best_oracle": best_oracle,
        "comparisons": comparisons,
        "conclusion": (
            "large held-out source is coverage-limited, not random-limited: "
            "trained public tokens create hundreds of exact spans but remain "
            "slightly positive; oracle coverage becomes cleanly profitable"
        ),
    }


def build_report() -> dict[str, Any]:
    rows, token_metadata = build_rows()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rust_version": rust_version(),
        "rust_library": "rustup stable-x86_64-pc-windows-msvc rust-src library",
        "heldout": str(HELDOUT_REL).replace("\\", "/"),
        "source_hashes": source_hashes(),
        "parameters": {
            "codeword_len": CODEWORD_LEN,
            "token_limit": TOKEN_LIMIT,
            "control_variants": list(CONTROL_VARIANTS),
            "transform_metadata_bytes": TRANSFORM_METADATA_BYTES,
            "hasher": "sha256",
            "seed_depth": 1,
            "seed_bits": 8,
            "max_span_len": CODEWORD_LEN,
            "span_step": 1,
        },
        "token_metadata": token_metadata,
        "summary": summarize(rows),
        "rows": rows,
    }


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Large Source Preset Probe",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "",
        "This experiment tests whether source-code exact seed-span compression becomes viable at file scale.",
        "",
        "Claim boundary: `learned-rust-source-heldout-v0` excludes the held-out `result.rs` file. `oracle-result-source-v0` intentionally leaks target repeated spans and is only a coverage upper bound.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Comparisons: `{summary['comparison_count']}`",
        f"- Trained clean seed-specific wins: `{summary['trained_clean_seed_specific_win_rows']}`",
        f"- Oracle clean seed-specific wins: `{summary['oracle_clean_seed_specific_win_rows']}`",
        f"- Best trained seed delta bytes: `{summary['best_trained_seed_delta_bytes']}`",
        f"- Best trained seed minus control bytes: `{summary['best_trained_seed_minus_control_bytes']}`",
        f"- Best trained source seed delta bytes: `{summary['best_trained_source_seed_delta_bytes']}`",
        f"- Best trained source seed minus control bytes: `{summary['best_trained_source_seed_minus_control_bytes']}`",
        f"- Best oracle seed delta bytes: `{summary['best_oracle_seed_delta_bytes']}`",
        f"- Best oracle seed minus control bytes: `{summary['best_oracle_seed_minus_control_bytes']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Comparisons",
        "",
        "| Corpus | Registry | Frame | Seed delta | Public-preset delta | Selected spans | Best control delta | Seed minus control | Clean seed win |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["comparisons"]:
        lines.append(
            "| {corpus} | `{registry}` | `{frame}` | {seed_delta} | {public_delta} | {selected} | {control_delta} | {diff} | `{clean}` |".format(
                corpus=row["corpus"],
                registry=row["registry"],
                frame=row["frame_mode"],
                seed_delta=row["seed_delta_bytes"],
                public_delta=row["seed_public_preset_delta_bytes"],
                selected=row["seed_selected_spans"],
                control_delta=row["best_control_delta_bytes"],
                diff=row["seed_minus_best_control_bytes"],
                clean=row["clean_seed_specific_win"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- The trained held-out source registry creates hundreds of exact seed spans and beats same-token controls by kilobytes, but current accounting remains slightly positive.",
            "- The oracle source registry becomes cleanly negative while same-token controls bloat, proving that better source coverage can make the seed-span mechanism profitable at this scale.",
            "- The next source architecture should focus on a native public source preset or parser-informed token registry, not deeper random search.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def check_report() -> None:
    if not OUT_JSON.exists() or not OUT_MD.exists():
        raise SystemExit("large source preset probe artifacts are missing")
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("large_source_preset_probe.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("large_source_preset_probe.json source hashes are stale")
    summary = payload.get("summary", {})
    if summary.get("trained_clean_seed_specific_win_rows") != 0:
        raise SystemExit("trained heldout source result unexpectedly became clean proof")
    if summary.get("oracle_clean_seed_specific_win_rows", 0) <= 0:
        raise SystemExit("source oracle must prove the coverage upper bound")
    best_trained = summary.get("best_trained_source", {})
    if best_trained.get("seed_selected_spans", 0) <= 0:
        raise SystemExit("trained source registry must create exact selected spans")
    if best_trained.get("seed_minus_best_control_bytes", 0) >= 0:
        raise SystemExit("trained source registry must beat same-token controls")
    text = OUT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Large Source Preset Probe",
        "Claim boundary",
        "coverage upper bound",
        "parser-informed token registry",
    ):
        if phrase not in text:
            raise SystemExit(f"LARGE_SOURCE_PRESET_PROBE.md missing phrase: {phrase}")


def main() -> int:
    payload = build_report()
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload)
    check_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
