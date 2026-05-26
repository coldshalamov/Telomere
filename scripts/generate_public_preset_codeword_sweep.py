#!/usr/bin/env python3
"""Measure public-preset codeword length against same-token controls.

This is a thesis-facing experiment, not a promotion gate. It asks whether the
format-native public preset is winning because tokens map to in-budget seed
expansions, or merely because the transform behaves like a normal dictionary.
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
    public_preset_framed,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "target" / "thesis_runs" / "public_preset_codeword_sweep"
OUT_JSON = ROOT / "docs" / "public_preset_codeword_sweep.json"
OUT_MD = ROOT / "docs" / "PUBLIC_PRESET_CODEWORD_SWEEP.md"
GENERATED_BY = "scripts/generate_public_preset_codeword_sweep.py"

CODEWORD_LENS = (4, 8, 12, 16)
MIN_TOKEN_LEN = 7
CONTROL_VARIANTS = ("random-codeword", "out-of-budget-codeword")

CORPORA = {
    "schema-heldout": ROOT
    / "corpora"
    / "external"
    / "schema-and-config"
    / "schemars-validate-schema-heldout.json",
    "schema-ordinary": ROOT
    / "corpora"
    / "external"
    / "schema-and-config"
    / "schemars-main-schema-excerpt.json",
    "http-ordinary": ROOT
    / "corpora"
    / "external"
    / "standards-protocol-text"
    / "http-request-response-excerpt.md",
    "csv-heldout": ROOT
    / "corpora"
    / "external"
    / "records-and-ledgers"
    / "csv-smallpop-no-headers-heldout.csv",
    "source-rust": ROOT
    / "corpora"
    / "external"
    / "source-code"
    / "rust-option-excerpt.rs",
    "schema-shadow": ROOT
    / "corpora"
    / "external"
    / "controls"
    / "schemars-validate-schema-shadow.json",
    "schema-random": ROOT
    / "corpora"
    / "external"
    / "controls"
    / "schemars-validate-schema-random.txt",
}

SOURCE_PATHS = {
    "generator": ROOT / GENERATED_BY,
    "thesis_harness": ROOT / "scripts" / "run_thesis_attack_experiment.py",
    "public_preset": ROOT / "src" / "public_preset.rs",
    "cli": ROOT / "src" / "main.rs",
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


def run_compress(
    binary: Path,
    input_path: Path,
    output_path: Path,
    codeword_len: int,
    *,
    native_transform: bool,
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
    if native_transform:
        command.extend(
            [
                "--transform",
                "public-preset-selective",
                "--public-preset-min-token-len",
                str(MIN_TOKEN_LEN),
                "--public-preset-codeword-len",
                str(codeword_len),
            ]
        )
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
    transform = telemetry.get("transform") or {}
    return {
        "command": " ".join(command),
        "tlmr_bytes": output_path.stat().st_size,
        "json_final_bytes": payload["final_bytes"],
        "selected_spans": telemetry.get("selected_count", 0),
        "candidate_count": telemetry.get("candidate_count", 0),
        "literal_bytes": telemetry.get("literal_bytes"),
        "token_replacements": transform.get("token_replacements"),
        "native_transformed_bytes": transform.get("transformed_bytes"),
    }


def build_rows() -> list[dict[str, Any]]:
    binary = ensure_binary()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for corpus, input_path in CORPORA.items():
        original = input_path.read_bytes()
        original_len = len(original)
        for codeword_len in CODEWORD_LENS:
            native_out = RUN_DIR / f"{corpus}-native-cw{codeword_len}.tlmr"
            native = run_compress(
                binary,
                input_path,
                native_out,
                codeword_len,
                native_transform=True,
            )
            rows.append(
                {
                    "corpus": corpus,
                    "variant": "native-seed",
                    "codeword_len": codeword_len,
                    "original_bytes": original_len,
                    "charged_bytes": native["tlmr_bytes"],
                    "delta_bytes": native["tlmr_bytes"] - original_len,
                    **native,
                }
            )

            for variant in CONTROL_VARIANTS:
                framed, metadata = public_preset_framed(
                    original,
                    min_token_len=MIN_TOKEN_LEN,
                    codeword_variant=variant,
                    codeword_len=codeword_len,
                )
                framed_path = RUN_DIR / f"{corpus}-{variant}-cw{codeword_len}.bin"
                framed_path.write_bytes(framed)
                control_out = RUN_DIR / f"{corpus}-{variant}-cw{codeword_len}.tlmr"
                control = run_compress(
                    binary,
                    framed_path,
                    control_out,
                    codeword_len,
                    native_transform=False,
                )
                transform_metadata = int(
                    metadata.get("transform_metadata_bytes", TRANSFORM_METADATA_BYTES)
                )
                charged = control["tlmr_bytes"] + transform_metadata
                rows.append(
                    {
                        "corpus": corpus,
                        "variant": variant,
                        "codeword_len": codeword_len,
                        "original_bytes": original_len,
                        "charged_bytes": charged,
                        "delta_bytes": charged - original_len,
                        "control_transformed_bytes": len(framed),
                        "control_transform_metadata_bytes": transform_metadata,
                        "control_token_count": metadata.get("public_preset_token_count"),
                        **control,
                    }
                )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    native_rows = [row for row in rows if row["variant"] == "native-seed"]
    control_rows = [row for row in rows if row["variant"] != "native-seed"]
    comparisons = []
    for native in native_rows:
        controls = [
            row
            for row in control_rows
            if row["corpus"] == native["corpus"]
            and row["codeword_len"] == native["codeword_len"]
        ]
        best_control = min(controls, key=lambda row: row["delta_bytes"])
        comparisons.append(
            {
                "corpus": native["corpus"],
                "codeword_len": native["codeword_len"],
                "native_delta_bytes": native["delta_bytes"],
                "native_selected_spans": native["selected_spans"],
                "native_token_replacements": native.get("token_replacements"),
                "best_control_variant": best_control["variant"],
                "best_control_delta_bytes": best_control["delta_bytes"],
                "best_control_selected_spans": best_control["selected_spans"],
                "native_minus_best_control_bytes": native["delta_bytes"]
                - best_control["delta_bytes"],
                "clean_seed_specific_win": (
                    native["delta_bytes"] < 0
                    and native["selected_spans"] > 0
                    and best_control["delta_bytes"] >= 0
                ),
                "dictionary_contaminated": best_control["delta_bytes"] < 0,
            }
        )

    clean = [row for row in comparisons if row["clean_seed_specific_win"]]
    contaminated = [row for row in comparisons if row["dictionary_contaminated"]]
    return {
        "row_count": len(rows),
        "native_rows": len(native_rows),
        "control_rows": len(control_rows),
        "profitable_native_rows": sum(1 for row in native_rows if row["delta_bytes"] < 0),
        "profitable_control_rows": sum(1 for row in control_rows if row["delta_bytes"] < 0),
        "native_rows_beating_best_control": sum(
            1 for row in comparisons if row["native_minus_best_control_bytes"] < 0
        ),
        "clean_seed_specific_win_rows": len(clean),
        "dictionary_contaminated_comparisons": len(contaminated),
        "best_clean_seed_specific_win": min(
            clean,
            key=lambda row: row["native_delta_bytes"],
            default=None,
        ),
        "comparisons": comparisons,
    }


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Public Preset Codeword Sweep",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "",
        "This experiment sweeps public-preset codeword lengths and compares the native seed-codeword run against same-token non-seed controls.",
        "",
        "Claim boundary: a negative row is seed-specific evidence only when the native run is negative, selected exact seed spans are present, and the best same-token control is not negative.",
        "",
        "## Summary",
        "",
        f"- Native rows: `{summary['native_rows']}`",
        f"- Native profitable rows: `{summary['profitable_native_rows']}`",
        f"- Control profitable rows: `{summary['profitable_control_rows']}`",
        f"- Native rows beating best same-token control: `{summary['native_rows_beating_best_control']}`",
        f"- Clean seed-specific win rows: `{summary['clean_seed_specific_win_rows']}`",
        f"- Dictionary-contaminated comparisons: `{summary['dictionary_contaminated_comparisons']}`",
        "",
        "## Comparisons",
        "",
        "| Corpus | Codeword | Native delta | Selected spans | Best control delta | Native minus control | Clean seed win | Contaminated |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary["comparisons"]:
        lines.append(
            "| {corpus} | {cw} | {native_delta} | {selected} | {control_delta} | {diff} | `{clean}` | `{contaminated}` |".format(
                corpus=row["corpus"],
                cw=row["codeword_len"],
                native_delta=row["native_delta_bytes"],
                selected=row["native_selected_spans"],
                control_delta=row["best_control_delta_bytes"],
                diff=row["native_minus_best_control_bytes"],
                clean=row["clean_seed_specific_win"],
                contaminated=row["dictionary_contaminated"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- Codeword length `4` can be contaminated because replacing long tokens with short opaque codewords is already a dictionary compressor.",
            "- Codeword lengths `12` and `16` are stricter controls for schema-sized tokens: same-token controls bloat, so negative native rows isolate the seed-addressable span contribution.",
            "- HTTP/source rows still need broader token coverage; selected spans alone are not enough if the full `.tlmr` accounting stays positive.",
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
            "min_token_len": MIN_TOKEN_LEN,
            "control_variants": list(CONTROL_VARIANTS),
            "hasher": "sha256",
            "seed_bits": 8,
            "seed_depth": 1,
            "span_step": 1,
        },
        "claim_boundary": (
            "Counts as seed-specific evidence only when the native row is "
            "negative, selected exact seed spans exist, and same-token non-seed "
            "controls are non-negative."
        ),
        "summary": summarize(rows),
        "rows": rows,
    }


def check_report() -> None:
    if not OUT_JSON.exists() or not OUT_MD.exists():
        raise SystemExit("public preset codeword sweep artifacts are missing")
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_codeword_sweep.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_codeword_sweep.json source hashes are stale")
    summary = payload.get("summary", {})
    if summary.get("clean_seed_specific_win_rows", 0) <= 0:
        raise SystemExit("codeword sweep must contain at least one clean seed-specific win")
    if summary.get("profitable_control_rows", 0) <= 0:
        raise SystemExit("codeword sweep must retain contaminated control rows")
    text = OUT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Codeword Sweep",
        "Claim boundary",
        "Clean seed-specific win rows",
        "Dictionary-contaminated comparisons",
        "same-token controls bloat",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_CODEWORD_SWEEP.md missing phrase: {phrase}")


def main() -> int:
    payload = build_report()
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(payload)
    print(f"WROTE {OUT_JSON}")
    print(f"WROTE {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
