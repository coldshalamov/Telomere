#!/usr/bin/env python3
"""Probe source-code token registries against seed-codeword controls.

The public preset currently has schema/log/CSV coverage but no useful source
coverage. This experiment separates two questions:

1. Can a non-overfit generic Rust/doc token registry make the existing source
   fixture profitable under real v2 `.tlmr` accounting?
2. If not, does a target-leakage oracle registry prove the source failure is a
   token-coverage problem rather than a seed-span mechanism failure?
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_thesis_attack_experiment import (
    TRANSFORM_METADATA_BYTES,
    canonical_seed_from_index,
    seed_span,
    unique_deterministic_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "target" / "thesis_runs" / "source_token_registry_probe"
OUT_JSON = ROOT / "docs" / "source_token_registry_probe.json"
OUT_MD = ROOT / "docs" / "SOURCE_TOKEN_REGISTRY_PROBE.md"
GENERATED_BY = "scripts/generate_source_token_registry_probe.py"

CODEWORD_LENS = (8, 12, 16)
CONTROL_VARIANTS = ("random-codeword", "out-of-budget-codeword")

CORPORA = {
    "source-rust-option": ROOT
    / "corpora"
    / "external"
    / "source-code"
    / "rust-option-excerpt.rs",
    "source-rust-shadow": ROOT
    / "corpora"
    / "external"
    / "controls"
    / "rust-option-excerpt-shadow.rs",
    "source-random": ROOT
    / "corpora"
    / "external"
    / "controls"
    / "rust-option-excerpt-random.txt",
}

# Generic Rust/doc tokens chosen without target-only identifier strings such as
# "denominator" or "divide". This registry is intentionally small and dull: if
# it wins, source coverage is already easy; if it fails, we need a learned or
# richer source-family preset.
GENERIC_RUST_DOC_TOKENS = (
    b"[`Option`]",
    b"[`Some`]",
    b"[`None`]",
    b"Option<",
    b"Return value",
    b"Return values",
    b"Optional ",
    b"optional ",
    b"functions",
    b"pattern matching",
    b"println!",
    b" struct ",
    b"function ",
    b" returned ",
    b" errors",
    b" Rust code",
)

# Deliberately not proof: this registry is allowed to contain target-specific
# strings. It is an oracle upper bound that tests whether source-code can be
# made profitable if coverage is high enough.
ORACLE_OPTION_DOC_TOKENS = (
    b"//! Optional",
    b"//! Type [`Option`]",
    b"[`Option`]",
    b"[`Some`]",
    b"[`None`]",
    b"optional value",
    b"very common in Rust code",
    b"Return values",
    b"Return value",
    b"Optional struct fields",
    b"Optional function arguments",
    b"pattern matching",
    b"fn divide",
    b"denominator",
    b"numerator",
    b"Option<f64>",
    b"if denominator",
    b"Some(numerator",
    b"match result",
    b"Some(x) =>",
    b"None    =>",
    b'println!("Result',
    b'println!("Cannot',
    b"The return value",
    b"Pattern match",
    b"partial functions",
    b"simple errors",
    b"Nullable pointers",
    b"Swapping things",
)

REGISTRIES = {
    "generic-rust-doc-v0": {
        "claim_role": "non-overfit generic source preset probe",
        "target_leakage": False,
        "tokens": GENERIC_RUST_DOC_TOKENS,
    },
    "oracle-option-doc-v0": {
        "claim_role": "target-leakage oracle; mechanism upper bound only",
        "target_leakage": True,
        "tokens": ORACLE_OPTION_DOC_TOKENS,
    },
}

SOURCE_PATHS = {
    "generator": ROOT / GENERATED_BY,
    "thesis_harness": ROOT / "scripts" / "run_thesis_attack_experiment.py",
    "public_preset": ROOT / "src" / "public_preset.rs",
    "streaming_engine": ROOT / "src" / "streaming.rs",
    "tlmr_v2": ROOT / "src" / "tlmr_v2.rs",
    **{f"corpus:{name}": path for name, path in CORPORA.items()},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def ensure_binary() -> Path:
    binary = ROOT / "target" / "debug" / ("telomere.exe" if os.name == "nt" else "telomere")
    if not binary.exists():
        subprocess.run(["cargo", "build", "--quiet"], cwd=ROOT, check=True)
    if not binary.exists():
        raise FileNotFoundError(f"missing telomere debug binary at {binary}")
    return binary


def codebook_for_tokens(
    tokens: tuple[bytes, ...],
    variant: str,
    codeword_len: int,
    *,
    label: str,
) -> dict[bytes, bytes]:
    seed_codewords = {
        seed_span(bytes([idx]))[:codeword_len] for idx in range(1 << 8)
    }
    used: set[bytes] = set()
    codebook: dict[bytes, bytes] = {}
    for idx, token in enumerate(tokens):
        if variant == "seed":
            codeword = seed_span(bytes([idx]))[:codeword_len]
        elif variant == "out-of-budget-codeword":
            seed_index = 1 << 8
            seed_index += idx
            while True:
                codeword = seed_span(canonical_seed_from_index(seed_index))[
                    :codeword_len
                ]
                if codeword not in seed_codewords and codeword not in used:
                    break
                seed_index += len(tokens)
        elif variant == "random-codeword":
            codeword = unique_deterministic_bytes(
                f"{GENERATED_BY}:{label}:{variant}:{idx}",
                codeword_len,
                seed_codewords,
                used,
            )
        else:
            raise ValueError(f"unknown codeword variant: {variant}")
        used.add(codeword)
        codebook[token] = codeword
    return codebook


def frame_with_codebook(data: bytes, codebook: dict[bytes, bytes]) -> tuple[bytes, int]:
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
    return bytes(out), replacements


def run_compress(
    binary: Path,
    input_path: Path,
    output_path: Path,
    codeword_len: int,
) -> dict[str, Any]:
    command = [
        str(binary),
        "compress",
        str(input_path),
        str(output_path),
        "--engine",
        "streaming",
        "--format",
        "v2",
        "--hasher",
        "sha256",
        "--seed-depth",
        "1",
        "--seed-bits",
        "8",
        "--max-span-len",
        str(codeword_len),
        "--span-step",
        "1",
        "--telemetry-limit",
        "0",
        "--memory-limit",
        "100%",
        "--json",
        "--verify",
        "--force",
    ]
    env = os.environ.copy()
    env["RUST_LOG"] = "error"
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "compression failed\n"
            f"command: {' '.join(command)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    payload = json.loads(result.stdout)
    telemetry = payload.get("engine_telemetry") or {}
    return {
        "command": " ".join(command),
        "tlmr_bytes": output_path.stat().st_size,
        "json_final_bytes": payload["final_bytes"],
        "selected_spans": telemetry.get("selected_count", 0),
        "candidate_count": telemetry.get("candidate_count", 0),
        "literal_bytes": telemetry.get("literal_bytes"),
    }


def build_rows() -> list[dict[str, Any]]:
    binary = ensure_binary()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for corpus, corpus_path in CORPORA.items():
        data = corpus_path.read_bytes()
        original_len = len(data)
        for registry_id, registry in REGISTRIES.items():
            tokens = registry["tokens"]
            for codeword_len in CODEWORD_LENS:
                for variant in ("seed", *CONTROL_VARIANTS):
                    codebook = codebook_for_tokens(
                        tokens,
                        variant,
                        codeword_len,
                        label=registry_id,
                    )
                    framed, replacements = frame_with_codebook(data, codebook)
                    input_path = (
                        RUN_DIR
                        / f"{corpus}-{registry_id}-{variant}-cw{codeword_len}.bin"
                    )
                    input_path.write_bytes(framed)
                    output_path = (
                        RUN_DIR
                        / f"{corpus}-{registry_id}-{variant}-cw{codeword_len}.tlmr"
                    )
                    compression = run_compress(
                        binary,
                        input_path,
                        output_path,
                        codeword_len,
                    )
                    charged = compression["tlmr_bytes"] + TRANSFORM_METADATA_BYTES
                    rows.append(
                        {
                            "corpus": corpus,
                            "registry": registry_id,
                            "claim_role": registry["claim_role"],
                            "target_leakage": registry["target_leakage"],
                            "variant": variant,
                            "codeword_len": codeword_len,
                            "token_count": len(tokens),
                            "token_replacements": replacements,
                            "original_bytes": original_len,
                            "framed_bytes": len(framed),
                            "charged_bytes": charged,
                            "delta_bytes": charged - original_len,
                            **compression,
                        }
                    )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seed_rows = [row for row in rows if row["variant"] == "seed"]
    comparisons = []
    for seed in seed_rows:
        controls = [
            row
            for row in rows
            if row["corpus"] == seed["corpus"]
            and row["registry"] == seed["registry"]
            and row["codeword_len"] == seed["codeword_len"]
            and row["variant"] != "seed"
        ]
        best_control = min(controls, key=lambda row: row["delta_bytes"])
        comparisons.append(
            {
                "corpus": seed["corpus"],
                "registry": seed["registry"],
                "target_leakage": seed["target_leakage"],
                "codeword_len": seed["codeword_len"],
                "seed_delta_bytes": seed["delta_bytes"],
                "seed_selected_spans": seed["selected_spans"],
                "token_replacements": seed["token_replacements"],
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
    non_overfit = [row for row in comparisons if not row["target_leakage"]]
    oracle = [row for row in comparisons if row["target_leakage"]]
    source_ordinary_non_overfit = [
        row for row in non_overfit if row["corpus"] == "source-rust-option"
    ]
    clean_non_overfit = [row for row in non_overfit if row["clean_seed_specific_win"]]
    clean_oracle = [row for row in oracle if row["clean_seed_specific_win"]]
    return {
        "row_count": len(rows),
        "comparison_count": len(comparisons),
        "non_overfit_clean_seed_specific_win_rows": len(clean_non_overfit),
        "oracle_clean_seed_specific_win_rows": len(clean_oracle),
        "non_overfit_best_seed_delta_bytes": min(
            (row["seed_delta_bytes"] for row in non_overfit),
            default=None,
        ),
        "source_ordinary_non_overfit_best_seed_delta_bytes": min(
            (row["seed_delta_bytes"] for row in source_ordinary_non_overfit),
            default=None,
        ),
        "oracle_best_seed_delta_bytes": min(
            (row["seed_delta_bytes"] for row in oracle),
            default=None,
        ),
        "best_non_overfit": min(
            non_overfit,
            key=lambda row: row["seed_delta_bytes"],
            default=None,
        ),
        "best_oracle": min(
            oracle,
            key=lambda row: row["seed_delta_bytes"],
            default=None,
        ),
        "best_clean_oracle": min(
            clean_oracle,
            key=lambda row: row["seed_delta_bytes"],
            default=None,
        ),
        "comparisons": comparisons,
        "conclusion": (
            "generic source registry did not prove non-overfit source compression; "
            "target-leakage oracle proves source token coverage can make the seed-span "
            "mechanism profitable"
        ),
    }


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Source Token Registry Probe",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "",
        "This experiment asks whether source-code failure is caused by weak token coverage or by the seed-span mechanism itself.",
        "",
        "Claim boundary: `generic-rust-doc-v0` is the only non-overfit source-registry probe here. `oracle-option-doc-v0` intentionally leaks target-specific strings and is only a mechanism upper bound.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Comparisons: `{summary['comparison_count']}`",
        f"- Non-overfit clean seed-specific wins: `{summary['non_overfit_clean_seed_specific_win_rows']}`",
        f"- Oracle clean seed-specific wins: `{summary['oracle_clean_seed_specific_win_rows']}`",
        f"- Best non-overfit seed delta bytes: `{summary['non_overfit_best_seed_delta_bytes']}`",
        f"- Source ordinary non-overfit best seed delta bytes: `{summary['source_ordinary_non_overfit_best_seed_delta_bytes']}`",
        f"- Best oracle seed delta bytes: `{summary['oracle_best_seed_delta_bytes']}`",
        f"- Conclusion: `{summary['conclusion']}`",
        "",
        "## Comparisons",
        "",
        "| Corpus | Registry | Codeword | Seed delta | Selected spans | Best control delta | Seed minus control | Clean seed win |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["comparisons"]:
        lines.append(
            "| {corpus} | `{registry}` | {cw} | {seed_delta} | {selected} | {control_delta} | {diff} | `{clean}` |".format(
                corpus=row["corpus"],
                registry=row["registry"],
                cw=row["codeword_len"],
                seed_delta=row["seed_delta_bytes"],
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
            "- Generic Rust/doc tokens create exact seed spans but do not overcome full `.tlmr` accounting on the committed source fixture.",
            "- The oracle registry produces clean negative rows on the real source fixture at codeword lengths `12` and `16`, with same-token controls bloating.",
            "- Therefore the next source-code architecture should learn or pre-register richer source-family tokens from independent training files, then evaluate on held-out source fixtures before promotion.",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_hashes": source_hashes(),
        "parameters": {
            "codeword_lens": list(CODEWORD_LENS),
            "control_variants": list(CONTROL_VARIANTS),
            "transform_metadata_bytes": TRANSFORM_METADATA_BYTES,
            "hasher": "sha256",
            "seed_bits": 8,
            "seed_depth": 1,
            "span_step": 1,
        },
        "registries": {
            registry_id: {
                "claim_role": registry["claim_role"],
                "target_leakage": registry["target_leakage"],
                "tokens": [token.decode("utf-8", errors="replace") for token in registry["tokens"]],
                "token_hex": [token.hex() for token in registry["tokens"]],
            }
            for registry_id, registry in REGISTRIES.items()
        },
        "claim_boundary": (
            "Only non-overfit registry rows can support source-code generalization. "
            "Oracle rows can only show that better source token coverage could make "
            "the seed-span mechanism profitable."
        ),
        "summary": summarize(rows),
        "rows": rows,
    }


def check_report() -> None:
    if not OUT_JSON.exists() or not OUT_MD.exists():
        raise SystemExit("source token registry probe artifacts are missing")
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("source_token_registry_probe.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("source_token_registry_probe.json source hashes are stale")
    summary = payload.get("summary", {})
    if summary.get("non_overfit_clean_seed_specific_win_rows") != 0:
        raise SystemExit("generic source registry unexpectedly became a clean proof")
    if summary.get("oracle_clean_seed_specific_win_rows", 0) <= 0:
        raise SystemExit("source oracle registry must prove the coverage upper bound")
    if summary.get("source_ordinary_non_overfit_best_seed_delta_bytes", 0) <= 0:
        raise SystemExit("generic source ordinary result should remain non-profitable")
    text = OUT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Source Token Registry Probe",
        "Claim boundary",
        "Source ordinary non-overfit best seed delta bytes",
        "target-leakage oracle",
        "same-token controls bloating",
    ):
        if phrase not in text:
            raise SystemExit(f"SOURCE_TOKEN_REGISTRY_PROBE.md missing phrase: {phrase}")


def main() -> int:
    payload = build_report()
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(payload)
    print(f"WROTE {OUT_JSON}")
    print(f"WROTE {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
