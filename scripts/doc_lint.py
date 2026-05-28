#!/usr/bin/env python3
"""Lightweight documentation and artifact-policy checks for Telomere.

This gate intentionally does not re-run the generated evidence graph. Its job is
to keep canonical docs honest, keep source-control bloat out of the repo, and
preserve the claim boundaries that matter for publication.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/FORMAT.md",
    "docs/RESEARCH_PROGRAM.md",
    "docs/THEORY.md",
    "docs/POWER_MODEL.md",
    "docs/RESULTS.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/PRODUCTION_READINESS_PLAN.md",
    "docs/SOURCE_FAMILY_CROSS_VALIDATION.md",
    "docs/source_family_cross_validation.json",
    "src/hasher.rs",
    "src/seed.rs",
    "src/seed_index.rs",
    "src/header.rs",
    "src/tlmr.rs",
    "src/tlmr_v2.rs",
    "src/public_preset.rs",
    "src/indexed.rs",
    "src/streaming.rs",
    "src/lib.rs",
    "src/main.rs",
]


# These direct docs/*.json files are compact source artifacts. The Tauri
# research panel reads the compact snapshot; the source-family artifact preserves
# the current narrow native public-preset evidence. Everything else under
# docs/*.json should be generated on demand, not checked in as source.
ALLOWED_DOC_JSON = {
    "docs/research_artifacts_snapshot.json",
    "docs/source_family_cross_validation.json",
}


REQUIRED_SNIPPETS = {
    "AGENTS.md": [
        "Required Three-Pass Thinking",
        "Raw cryptographic/hash expansion is structure-blind",
        "expected_hits = seed_count * target_span_count / 2^(8 * span_len)",
    ],
    "docs/FORMAT.md": [
        "arity 2",
        ".tlmr",
        "public preset",
    ],
    "docs/THEORY.md": [
        "expected_hits",
        "Minimum Profitable Frontier",
    ],
    "docs/POWER_MODEL.md": [
        "expected_hits = seed_count * target_span_count / 2^(8 * span_len)",
        "Counting Boundary",
        "Native V2 Record Cost Frontier",
        "Laptop Null Versus Powered Regime",
        "Match Table Costs",
        "Selection, Overlap, Bundling, And Superposition",
        "Hardware Scaling Model",
        "Multi-Pass Recurrence",
        "Public Preset / Transform Separation",
        "Powered Toy Regime",
        "Scaling Direction",
    ],
    "docs/PRODUCTION_READINESS_PLAN.md": [
        "Not Production-Ready Yet",
        "Publishable Research Claim",
        "Rebuttal Register",
    ],
    "docs/SOURCE_FAMILY_CROSS_VALIDATION.md": [
        "Native public-preset total: `420422 -> 415847` bytes (`-4575` delta)",
        "Native public-preset selected spans: `4597`",
        "Same-size random selected spans: `0`",
        "Paired shadow selected spans: `0`",
        "Paired shadow token replacements: `0`",
    ],
}


FORBIDDEN_SNIPPETS = {
    "AGENTS.md": [
        "arity 2 is reserved",
        "structured data should compress better under raw seed search",
    ],
    "docs/PRODUCTION_READINESS_PLAN.md": [
        "production-ready today",
        "universal compressor",
    ],
    "docs/POWER_MODEL.md": [
        "structured data helps raw hash expansion",
        "depth/laptop null shows",
    ],
}


def fail(message: str) -> None:
    print(f"doc_lint failed: {message}")
    sys.exit(1)


def read(path: str) -> str:
    full_path = ROOT / path
    if not full_path.exists():
        fail(f"missing required file {path}")
    return full_path.read_text(encoding="utf-8")


def git_ls_files(pathspec: str) -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", pathspec],
            cwd=ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"git ls-files {pathspec} failed: {exc.output.strip()}")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def check_required_files() -> dict[str, str]:
    return {path: read(path) for path in REQUIRED_FILES}


def check_snippets(texts: dict[str, str]) -> None:
    for path, snippets in REQUIRED_SNIPPETS.items():
        text = texts.get(path) or read(path)
        for snippet in snippets:
            if snippet not in text:
                fail(f"{path} missing required snippet: {snippet}")

    for path, snippets in FORBIDDEN_SNIPPETS.items():
        text = texts.get(path) or read(path)
        lower_text = text.lower()
        for snippet in snippets:
            if snippet.lower() in lower_text:
                fail(f"{path} contains forbidden snippet: {snippet}")


def check_direct_docs_json_allowlist() -> None:
    tracked = {
        path.as_posix()
        for path in (ROOT / "docs").glob("*.json")
        if path.is_file()
        for path in [path.relative_to(ROOT)]
    }
    unexpected = sorted(path for path in tracked if path not in ALLOWED_DOC_JSON)
    missing = sorted(path for path in ALLOWED_DOC_JSON if path not in tracked)

    if unexpected:
        fail(
            "unexpected tracked direct docs JSON artifacts; keep large row "
            f"matrices generated-on-demand instead: {', '.join(unexpected)}"
        )
    if missing:
        fail(f"missing allowed docs JSON consumed by current evidence surfaces: {', '.join(missing)}")


def check_source_family_artifact() -> None:
    payload = json.loads(read("docs/source_family_cross_validation.json"))
    if payload.get("generated_by") != "scripts/generate_source_family_cross_validation.py":
        fail("docs/source_family_cross_validation.json has the wrong generated_by marker")

    summary = payload.get("summary", {})
    expected = {
        "native_public_preset_total_input_bytes": 420422,
        "native_public_preset_total_tlmr_bytes": 415847,
        "native_public_preset_total_delta_bytes": -4575,
        "native_public_preset_selected_spans": 4597,
        "same_size_random_selected_spans": 0,
        "paired_shadow_selected_spans": 0,
        "paired_shadow_token_replacements": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            fail(f"source family summary {key} changed from expected {value!r}")


def check_no_ignored_tests() -> None:
    for test_file in (ROOT / "tests").rglob("*.rs"):
        if "#[ignore" in test_file.read_text(encoding="utf-8"):
            fail(f"{test_file.relative_to(ROOT)} contains #[ignore]")


def check_power_model() -> None:
    try:
        subprocess.check_output(
            [sys.executable, "scripts/telomere_power_model.py", "--check"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"power model check failed: {exc.output.strip()}")

    try:
        output = subprocess.check_output(
            [sys.executable, "scripts/telomere_power_model.py", "--json"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"power model JSON failed: {exc.output.strip()}")

    if len(output) > 200_000:
        fail("power model JSON is too large for a compact source artifact")
    payload = json.loads(output)
    for key in [
        "config",
        "minimum_profitable_frontier",
        "span_tiers_at_max_depth",
        "hardware_rows",
        "pass_rows",
    ]:
        if key not in payload:
            fail(f"power model JSON missing {key}")


def main() -> None:
    texts = check_required_files()
    check_snippets(texts)
    check_direct_docs_json_allowlist()
    check_source_family_artifact()
    check_power_model()
    check_no_ignored_tests()

    if (ROOT / "error.log").exists():
        fail("tracked junk artifact error.log still exists")

    print("Doc lint passed")


if __name__ == "__main__":
    main()
