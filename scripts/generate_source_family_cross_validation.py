#!/usr/bin/env python3
"""Cross-validate source-family token presets across held-out Rust files."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generate_large_source_preset_probe import (
    CODEWORD_LEN,
    CONTROL_VARIANTS,
    RUST_LIBRARY,
    TOKEN_LIMIT,
    deterministic_random,
    frame_with_codebook,
    frame_with_lotus_bits,
    learned_public_source_tokens,
    run_compress,
    rust_version,
    sha256,
)
from generate_source_token_registry_probe import (
    TRANSFORM_METADATA_BYTES,
    codebook_for_tokens,
    ensure_binary,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "target" / "thesis_runs" / "source_family_cross_validation"
OUT_JSON = ROOT / "docs" / "source_family_cross_validation.json"
OUT_MD = ROOT / "docs" / "SOURCE_FAMILY_CROSS_VALIDATION.md"
GENERATED_BY = "scripts/generate_source_family_cross_validation.py"

HELDOUT_RELS = (
    Path("core/src/result.rs"),
    Path("core/src/option.rs"),
    Path("alloc/src/string.rs"),
    Path("std/src/path.rs"),
)


def slug(path: Path) -> str:
    return path.as_posix().replace("/", "-").replace(".", "-")


def require_heldouts() -> list[Path]:
    paths = [RUST_LIBRARY / rel for rel in HELDOUT_RELS]
    missing = [path for path in paths if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise SystemExit(f"source family cross-validation missing rust-src files: {joined}")
    return paths


def shadow_source_bytes(data: bytes, label: str, forbidden_tokens: tuple[bytes, ...]) -> bytes:
    """Preserve source byte shape while removing public Rust vocabulary.

    Whitespace and punctuation stay byte-for-byte so the control keeps line
    lengths, indentation, comment markers, braces, separators, and string
    punctuation. ASCII letters/digits are replaced by deterministic
    vocabulary-disjoint glyphs so source-family token hits must come from
    learned lexical coverage, not generic source-shaped layout.
    """

    alpha_lower = b"qzxvjk"
    alpha_upper = b"QZXVJK"
    digit_shadow = b"739105"
    salt = hashlib.sha256(label.encode("utf-8")).digest()
    out = bytearray()
    for idx, byte in enumerate(data):
        offset = salt[idx % len(salt)]
        if 97 <= byte <= 122:
            out.append(alpha_lower[(idx + offset) % len(alpha_lower)])
        elif 65 <= byte <= 90:
            out.append(alpha_upper[(idx + offset) % len(alpha_upper)])
        elif 48 <= byte <= 57:
            out.append(digit_shadow[(idx + offset) % len(digit_shadow)])
        else:
            out.append(byte)
    # The first pass preserves source shape, but repeated shadow glyphs can
    # accidentally synthesize a learned token. Scrub those exact token bytes so
    # the paired control is vocabulary-disjoint by construction.
    changed = True
    while changed:
        changed = False
        for token in sorted(forbidden_tokens, key=len, reverse=True):
            start = bytes(out).find(token)
            while start != -1:
                changed = True
                for idx in range(start, start + len(token)):
                    if (
                        48 <= out[idx] <= 57
                        or 65 <= out[idx] <= 90
                        or 97 <= out[idx] <= 122
                    ):
                        out[idx] = ord("~")
                start = bytes(out).find(token, start + 1)
    return bytes(out)


def source_hashes() -> dict[str, str]:
    hashes = {
        "generator": sha256(ROOT / GENERATED_BY),
        "large_source_helper": sha256(
            ROOT / "scripts" / "generate_large_source_preset_probe.py"
        ),
        "source_probe_helpers": sha256(
            ROOT / "scripts" / "generate_source_token_registry_probe.py"
        ),
    }
    for rel, path in zip(HELDOUT_RELS, require_heldouts()):
        hashes[f"heldout_{slug(rel)}"] = sha256(path)
    return hashes


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    binary = ensure_binary()
    rows: list[dict[str, Any]] = []
    token_metadata: dict[str, Any] = {}
    frame_modes = {
        "external-byte": frame_with_codebook,
        "lotus-bit": frame_with_lotus_bits,
    }

    for rel, heldout in zip(HELDOUT_RELS, require_heldouts()):
        heldout_id = slug(rel)
        data = heldout.read_bytes()
        source_path = RUN_DIR / f"{heldout_id}.rs"
        source_path.write_bytes(data)
        random_path = RUN_DIR / f"{heldout_id}-same-size-random.bin"
        random_path.write_bytes(
            deterministic_random(len(data), f"source-family:{heldout_id}".encode())
        )
        tokens, token_stats = learned_public_source_tokens(heldout)
        shadow_path = RUN_DIR / f"{heldout_id}-paired-shadow-source.rs"
        shadow_path.write_bytes(shadow_source_bytes(data, heldout_id, tokens))
        token_metadata[heldout_id] = {
            "heldout": rel.as_posix(),
            "token_count": len(tokens),
            "top_tokens": token_stats[:16],
        }

        corpora = {
            "heldout-source": source_path,
            "paired-shadow-source": shadow_path,
            "same-size-random": random_path,
        }
        for corpus, input_path in corpora.items():
            corpus_data = input_path.read_bytes()
            original_len = len(corpus_data)
            for frame_mode, frame_fn in frame_modes.items():
                for variant in ("seed", *CONTROL_VARIANTS):
                    codebook = codebook_for_tokens(
                        tokens,
                        variant,
                        CODEWORD_LEN,
                        label=f"{heldout_id}:{frame_mode}",
                    )
                    framed, replacements = frame_fn(corpus_data, codebook)
                    framed_path = (
                        RUN_DIR
                        / f"{heldout_id}-{corpus}-{frame_mode}-{variant}.bin"
                    )
                    framed_path.write_bytes(framed)
                    output_path = framed_path.with_suffix(".tlmr")
                    compression = run_compress(binary, framed_path, output_path)
                    charged = compression["tlmr_bytes"] + TRANSFORM_METADATA_BYTES
                    rows.append(
                        {
                            "heldout": rel.as_posix(),
                            "heldout_id": heldout_id,
                            "corpus": corpus,
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

    return rows, token_metadata


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    seed_rows = [row for row in rows if row["variant"] == "seed"]
    seed_lookup = {
        (row["heldout_id"], row["corpus"], row["frame_mode"]): row for row in seed_rows
    }
    for seed in seed_rows:
        controls = [
            row
            for row in rows
            if row["heldout_id"] == seed["heldout_id"]
            and row["corpus"] == seed["corpus"]
            and row["frame_mode"] == seed["frame_mode"]
            and row["variant"] != "seed"
        ]
        best_control = min(controls, key=lambda row: row["delta_bytes"])
        paired_shadow = seed_lookup.get(
            (seed["heldout_id"], "paired-shadow-source", seed["frame_mode"])
        )
        paired_shadow_clean = (
            seed["corpus"] == "heldout-source"
            and paired_shadow is not None
            and paired_shadow["delta_bytes"] >= 0
            and paired_shadow["selected_spans"] == 0
            and paired_shadow["token_replacements"] == 0
        )
        comparisons.append(
            {
                "heldout": seed["heldout"],
                "heldout_id": seed["heldout_id"],
                "corpus": seed["corpus"],
                "frame_mode": seed["frame_mode"],
                "seed_delta_bytes": seed["delta_bytes"],
                "seed_public_preset_delta_bytes": seed["public_preset_delta_bytes"],
                "seed_selected_spans": seed["selected_spans"],
                "token_replacements": seed["token_replacements"],
                "best_control_variant": best_control["variant"],
                "best_control_delta_bytes": best_control["delta_bytes"],
                "best_control_selected_spans": best_control["selected_spans"],
                "paired_shadow_delta_bytes": (
                    paired_shadow["delta_bytes"] if paired_shadow else None
                ),
                "paired_shadow_selected_spans": (
                    paired_shadow["selected_spans"] if paired_shadow else None
                ),
                "paired_shadow_token_replacements": (
                    paired_shadow["token_replacements"] if paired_shadow else None
                ),
                "seed_minus_best_control_bytes": seed["delta_bytes"]
                - best_control["delta_bytes"],
                "clean_seed_specific_win": (
                    seed["corpus"] == "heldout-source"
                    and seed["delta_bytes"] < 0
                    and seed["selected_spans"] > 0
                    and best_control["delta_bytes"] >= 0
                    and paired_shadow_clean
                ),
            }
        )

    source = [row for row in comparisons if row["corpus"] == "heldout-source"]
    random_rows = [row for row in comparisons if row["corpus"] == "same-size-random"]
    shadow_rows = [row for row in comparisons if row["corpus"] == "paired-shadow-source"]
    clean_source = [row for row in source if row["clean_seed_specific_win"]]
    best_source = min(source, key=lambda row: row["seed_delta_bytes"])
    wins_by_heldout = {
        heldout: sum(
            1
            for row in source
            if row["heldout_id"] == heldout and row["clean_seed_specific_win"]
        )
        for heldout in sorted({row["heldout_id"] for row in source})
    }
    best_by_heldout = {
        heldout: min(
            [row for row in source if row["heldout_id"] == heldout],
            key=lambda row: row["seed_delta_bytes"],
        )
        for heldout in sorted({row["heldout_id"] for row in source})
    }
    return {
        "row_count": len(rows),
        "comparison_count": len(comparisons),
        "heldout_count": len(wins_by_heldout),
        "source_clean_win_rows": len(clean_source),
        "source_clean_win_heldouts": sum(1 for wins in wins_by_heldout.values() if wins),
        "same_size_random_selected_spans": sum(
            row["seed_selected_spans"] for row in random_rows
        ),
        "paired_shadow_selected_spans": sum(
            row["seed_selected_spans"] for row in shadow_rows
        ),
        "paired_shadow_token_replacements": sum(
            row["token_replacements"] for row in shadow_rows
        ),
        "best_source_seed_delta_bytes": best_source["seed_delta_bytes"],
        "best_source_seed_minus_control_bytes": best_source[
            "seed_minus_best_control_bytes"
        ],
        "wins_by_heldout": wins_by_heldout,
        "best_by_heldout": best_by_heldout,
        "best_source": best_source,
        "comparisons": comparisons,
        "conclusion": (
            "source-family exact seed-span compression generalizes across "
            "held-out Rust files and separates from paired vocabulary-shadow "
            "and random controls, but coverage remains preset dependent"
        ),
    }


def build_report() -> dict[str, Any]:
    rows, token_metadata = build_rows()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rust_version": rust_version(),
        "rust_library": "rustup stable-x86_64-pc-windows-msvc rust-src library",
        "heldouts": [rel.as_posix() for rel in HELDOUT_RELS],
        "source_hashes": source_hashes(),
        "parameters": {
            "codeword_len": CODEWORD_LEN,
            "token_limit": TOKEN_LIMIT,
            "fixed_span_records": True,
            "control_variants": list(CONTROL_VARIANTS),
            "transform_metadata_bytes": TRANSFORM_METADATA_BYTES,
            "hasher": "sha256",
            "seed_depth": 1,
            "seed_bits": 8,
            "max_span_len": CODEWORD_LEN,
            "block_size": CODEWORD_LEN,
            "span_step": 1,
        },
        "token_metadata": token_metadata,
        "summary": summarize(rows),
        "rows": rows,
    }


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Source Family Cross-Validation",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "",
        "This experiment holds out multiple Rust source files, learns source-family tokens from the remaining Rust library files, transforms each held-out file into deterministic codewords, and compresses those codewords with fixed-span `.tlmr` v2 accounting.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Comparisons: `{summary['comparison_count']}`",
        f"- Held-outs: `{summary['heldout_count']}`",
        f"- Source clean win rows: `{summary['source_clean_win_rows']}`",
        f"- Source clean win held-outs: `{summary['source_clean_win_heldouts']}`",
        f"- Same-size random selected spans: `{summary['same_size_random_selected_spans']}`",
        f"- Paired shadow selected spans: `{summary['paired_shadow_selected_spans']}`",
        f"- Paired shadow token replacements: `{summary['paired_shadow_token_replacements']}`",
        f"- Best source seed delta bytes: `{summary['best_source_seed_delta_bytes']}`",
        f"- Best source seed minus control bytes: `{summary['best_source_seed_minus_control_bytes']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Best By Held-Out",
        "",
        "| Held-out | Frame | Seed delta | Selected spans | Best control delta | Shadow selected | Seed minus control | Clean win |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for heldout, row in summary["best_by_heldout"].items():
        lines.append(
            "| {heldout} | `{frame}` | {delta} | {selected} | {control} | {shadow_selected} | {minus} | `{clean}` |".format(
                heldout=row["heldout"],
                frame=row["frame_mode"],
                delta=row["seed_delta_bytes"],
                selected=row["seed_selected_spans"],
                control=row["best_control_delta_bytes"],
                shadow_selected=row["paired_shadow_selected_spans"],
                minus=row["seed_minus_best_control_bytes"],
                clean=row["clean_seed_specific_win"],
            )
        )
    lines.extend(
        [
            "",
            "## All Comparisons",
            "",
            "| Held-out | Corpus | Frame | Seed delta | Public-preset delta | Selected spans | Best control delta | Shadow selected | Seed minus control | Clean win |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summary["comparisons"]:
        lines.append(
            "| {heldout} | `{corpus}` | `{frame}` | {delta} | {public_delta} | {selected} | {control} | {shadow_selected} | {minus} | `{clean}` |".format(
                heldout=row["heldout"],
                corpus=row["corpus"],
                frame=row["frame_mode"],
                delta=row["seed_delta_bytes"],
                public_delta=row["seed_public_preset_delta_bytes"],
                selected=row["seed_selected_spans"],
                control=row["best_control_delta_bytes"],
                shadow_selected=row["paired_shadow_selected_spans"],
                minus=row["seed_minus_best_control_bytes"],
                clean=row["clean_seed_specific_win"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- A clean win requires negative full `.tlmr` bytes, at least one selected exact seed span, and non-negative paired codeword controls.",
            "- Paired shadow rows preserve byte length, whitespace, punctuation, comments, and source delimiters while replacing source vocabulary; clean wins require these rows to keep zero token replacements and zero selected spans.",
            "- Same-size random rows test whether the source-family token transform creates accidental seed-span matches on non-source bytes.",
            "- The research question is no longer whether source-family codeword transforms can work at all; it is which public preset families provide enough coverage reliably.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def check_report() -> None:
    if not OUT_JSON.exists() or not OUT_MD.exists():
        raise SystemExit("source family cross-validation artifacts are missing")
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("source_family_cross_validation.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("source_family_cross_validation.json source hashes are stale")
    summary = payload.get("summary", {})
    if summary.get("heldout_count") != len(HELDOUT_RELS):
        raise SystemExit("source family cross-validation heldout count is stale")
    if summary.get("same_size_random_selected_spans", 1) != 0:
        raise SystemExit("same-size random source-family controls must stay null")
    if summary.get("paired_shadow_selected_spans", 1) != 0:
        raise SystemExit("paired shadow source controls must select zero spans")
    if summary.get("paired_shadow_token_replacements", 1) != 0:
        raise SystemExit("paired shadow source controls must replace zero tokens")
    if summary.get("source_clean_win_heldouts", 0) != len(HELDOUT_RELS):
        raise SystemExit("expected every held-out source to produce a clean win")
    if summary.get("best_source_seed_delta_bytes", 0) >= 0:
        raise SystemExit("expected best held-out source row to be negative")
    text = OUT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Source Family Cross-Validation",
        "Best By Held-Out",
        "Same-size random",
        "Paired shadow",
        "public preset families",
    ):
        if phrase not in text:
            raise SystemExit(f"SOURCE_FAMILY_CROSS_VALIDATION.md missing phrase: {phrase}")


def main() -> int:
    payload = build_report()
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload)
    check_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
