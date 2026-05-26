#!/usr/bin/env python3
"""Generate the frozen rank-coded span generator contract.

This artifact is the first concrete slice for the top pre-registered next
mechanism design. It is manifest/spec/golden-vector only: it does not read
external corpus payloads, run replay, emit selected spans, or claim compression.
The point is to freeze the contract and controls before any held-out scan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXTERNAL_MANIFEST = ROOT / "corpora" / "external" / "manifest.json"
REPORT_JSON = DOCS / "frozen_rank_coded_span_generator.json"
REPORT_MD = DOCS / "FROZEN_RANK_CODED_SPAN_GENERATOR.md"
GENERATED_BY = "scripts/generate_frozen_rank_coded_span_generator.py"

SOURCE_PATHS = {
    "next_mechanism_designs_sha256": DOCS / "next_mechanism_designs.json",
    "external_corpus_accession_sha256": DOCS / "external_corpus_accession.json",
    "external_manifest_sha256": EXTERNAL_MANIFEST,
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "frozen_rank_generator_sha256": ROOT
    / "scripts"
    / "generate_frozen_rank_coded_span_generator.py",
}

DESIGN_ID = "frozen-rank-coded-span-generator"
PRESET_ID = "frozen-rank-coded-span-generator-v0-contract"
PRESET_SELECTOR_BYTES = 2
PRESET_VERSION_BYTES = 1
RANK_MODEL_ID_BYTES = 4
SPAN_RECORD_BASE_BYTES = 5
LITERAL_RECORD_BASE_BYTES = 3
RANK_SEED_BYTES = 2
MAX_TABLE_BYTES = 1_048_576
MAX_ENTRY_BYTES = 256
PROMOTION_ORDINARY_GROUPS = 3

SPEC_GOLDEN_ENTRIES = [
    {
        "rank": 0,
        "seed_hex": "0000",
        "family": "standards-protocol-text",
        "example_expansion": "content-type: application/json\r\n",
    },
    {
        "rank": 1,
        "seed_hex": "0001",
        "family": "standards-protocol-text",
        "example_expansion": "cache-control: no-cache\r\n",
    },
    {
        "rank": 2,
        "seed_hex": "0002",
        "family": "schema-and-config",
        "example_expansion": "\"type\":\"object\"",
    },
    {
        "rank": 3,
        "seed_hex": "0003",
        "family": "records-and-ledgers",
        "example_expansion": "timestamp,status,amount\n",
    },
]

REQUIRED_ACCESSION_FIELDS = [
    "entry_id",
    "family_id",
    "role",
    "control_kind",
    "independence_group",
    "paired_with",
    "path",
    "license",
    "provenance",
    "source_uri",
    "retrieved_at",
    "sha256",
    "bytes",
]

CONTROL_SUITE = [
    "paired shadow vocabulary",
    "same-size random rank table",
    "wrong-family rank model",
    "generic token dictionary",
    "binary controls",
    "high-entropy controls",
    "equivalent random-trial SHA-256 baseline",
    "leave-family-out replay",
    "project-token removal",
]

STOP_RULES = [
    "Stop if any paired, random, binary, high-entropy, or wrong-family control goes negative.",
    "Stop if ordinary held-out wins stay below three unrelated independence groups.",
    "Stop if the rank table cannot be frozen from external provenance before held-out replay.",
    "Stop if wins require target-file leakage, project-token leakage, or same-family training leakage.",
    "Stop if metadata accounting removes full-stream negative delta.",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def golden_vectors() -> list[dict[str, Any]]:
    vectors = []
    for row in SPEC_GOLDEN_ENTRIES:
        expansion = row["example_expansion"].encode("utf-8")
        vectors.append(
            {
                "rank": row["rank"],
                "seed_hex": row["seed_hex"],
                "family": row["family"],
                "example_expansion_len": len(expansion),
                "example_expansion_sha256": hashlib.sha256(expansion).hexdigest(),
            }
        )
    return vectors


def golden_manifest_hash() -> str:
    data = json.dumps(golden_vectors(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(data).hexdigest()


def build_report() -> dict[str, Any]:
    next_designs = load_json(DOCS / "next_mechanism_designs.json")
    external = summary(load_json(DOCS / "external_corpus_accession.json"))
    public_rerun = summary(load_json(DOCS / "public_preset_control_rerun.json"))
    search = summary(load_json(DOCS / "search_frontier_gate.json"))
    top_design = summary(next_designs).get("top_design_id")
    if top_design != DESIGN_ID:
        raise RuntimeError("frozen rank contract expects the frozen-rank design to be top ranked")
    external_manifest_ready = bool(external.get("manifest_complete", False))
    compute_allowed = False
    promotion_ready = False
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "frozen rank-coded span generator contract",
            "performs_seed_search": False,
            "performs_replay": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
            "overrides_search_frontier_gate": False,
            "uses_external_corpus_payloads": False,
        },
        "source_hashes": source_hashes(),
        "design": {
            "design_id": DESIGN_ID,
            "rank": 1,
            "mechanism_family": "byte-to-seed-generator",
            "status": "blocked_waiting_for_external_corpus_accession",
            "core_idea": (
                "Seed bytes index a frozen decoder-public rank table trained only from "
                "external provenance before any held-out replay."
            ),
            "blocked_by": ["external-corpus-accession", "control-separation"],
            "promotion_trigger": (
                "At least three unrelated ordinary held-out groups produce selected "
                "exact spans and full-stream negative rows after metadata while every "
                "paired, same-size random, wrong-family, binary, high-entropy, and "
                "generic-dictionary control stays non-negative."
            ),
            "stop_rule": STOP_RULES[0],
        },
        "rank_table_contract": {
            "preset_id": PRESET_ID,
            "external_only_provenance": True,
            "frozen_before_heldout_scan": True,
            "canonical_rank_ordering": "rank entries by frozen external training frequency, then source id, then bytewise value",
            "seed_to_rank_mapping": "big-endian seed integer selects exactly one rank entry; out-of-range seeds are invalid",
            "decoder_public_version_id": PRESET_ID,
            "checksum_policy": "manifest stores table sha256, per-entry sha256, source sha256, byte length, license, and provenance",
            "max_table_bytes": MAX_TABLE_BYTES,
            "max_entry_bytes": MAX_ENTRY_BYTES,
            "golden_manifest_sha256": golden_manifest_hash(),
        },
        "metadata_accounting": {
            "preset_selector_bytes": PRESET_SELECTOR_BYTES,
            "preset_version_bytes": PRESET_VERSION_BYTES,
            "rank_model_id_bytes": RANK_MODEL_ID_BYTES,
            "span_record_base_bytes": SPAN_RECORD_BASE_BYTES,
            "literal_record_base_bytes": LITERAL_RECORD_BASE_BYTES,
            "rank_seed_bytes": RANK_SEED_BYTES,
            "selected_span_record_bytes_formula": "span_record_base_bytes + rank_seed_bytes",
            "literal_record_bytes_formula": "literal_record_base_bytes + literal_payload_bytes",
            "full_stream_delta_formula": (
                "preset_selector_bytes + preset_version_bytes + rank_model_id_bytes + "
                "sum(selected_span_record_bytes) + sum(literal_record_bytes) - input_bytes"
            ),
        },
        "accession_gate": {
            "external_accession_status": external.get("accession_status"),
            "external_manifest_complete": external_manifest_ready,
            "paired_manifest_ready": bool(external.get("paired_manifest_ready", False)),
            "validation_error_count": external.get("validation_error_count"),
            "required_fields": REQUIRED_ACCESSION_FIELDS,
            "compute_allowed": compute_allowed,
        },
        "control_suite": CONTROL_SUITE,
        "promotion_gate": {
            "ordinary_negative_group_floor": PROMOTION_ORDINARY_GROUPS,
            "requires_selected_exact_spans": True,
            "requires_full_stream_negative_rows": True,
            "requires_all_controls_non_negative": True,
            "requires_equivalent_random_trial_baseline": True,
            "requires_leave_family_out": True,
            "requires_project_token_removal": True,
            "promotion_ready": promotion_ready,
        },
        "stop_rules": STOP_RULES,
        "golden_vectors": golden_vectors(),
        "summary": {
            "contract_status": "blocked_waiting_for_external_corpus_accession",
            "top_design_id": top_design,
            "golden_vector_count": len(SPEC_GOLDEN_ENTRIES),
            "external_manifest_ready": external_manifest_ready,
            "external_accession_status": external.get("accession_status"),
            "paired_manifest_ready": bool(external.get("paired_manifest_ready", False)),
            "public_preset_rerun_status": public_rerun.get("rerun_status"),
            "broad_depth_search_allowed": bool(
                search.get("broad_depth_search_allowed", False)
            ),
            "compute_allowed": compute_allowed,
            "replay_allowed": False,
            "promotion_ready": promotion_ready,
            "natural_corpus_proven": False,
            "claim_boundary": (
                "No Seed Search; manifest/spec/golden-vector only; not a compression "
                "claim; not natural-corpus proof; not `.tlmr` format support."
            ),
            "next_allowed_action": (
                "add externally sourced rank-table accession entries with paired controls, "
                "then request human review before any replay"
            ),
            "conclusion": (
                "The rank-coded lane now has a frozen contract and golden vectors, but "
                "it remains blocked because the external accession manifest is not ready "
                "and no replay is authorized."
            ),
        },
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    design = payload["design"]
    contract = payload["rank_table_contract"]
    accounting = payload["metadata_accounting"]
    gate = payload["accession_gate"]
    lines = [
        "# Frozen Rank-Coded Span Generator",
        "",
        f"Generated by `{GENERATED_BY}` from the next-mechanism registry and accession gates.",
        "This is a No Seed Search manifest/spec/golden-vector artifact. It launches no agents, reads no external corpus payloads, performs no replay, is not natural-corpus proof, is not a compression claim, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Contract status: `{data['contract_status']}`",
        f"- Top design: `{data['top_design_id']}`",
        f"- Golden vectors: `{data['golden_vector_count']}`",
        f"- External accession status: `{data['external_accession_status']}`",
        f"- External manifest ready: `{data['external_manifest_ready']}`",
        f"- Paired manifest ready: `{data['paired_manifest_ready']}`",
        f"- Public preset rerun status: `{data['public_preset_rerun_status']}`",
        f"- Broad depth search allowed: `{data['broad_depth_search_allowed']}`",
        f"- Compute allowed: `{data['compute_allowed']}`",
        f"- Replay allowed: `{data['replay_allowed']}`",
        f"- Promotion ready: `{data['promotion_ready']}`",
        "",
        data["conclusion"],
        "",
        "## Design",
        "",
        f"- Design id: `{design['design_id']}`",
        f"- Rank: `{design['rank']}`",
        f"- Mechanism family: `{design['mechanism_family']}`",
        f"- Status: `{design['status']}`",
        f"- Core idea: {design['core_idea']}",
        f"- Blocked by: {', '.join(f'`{item}`' for item in design['blocked_by'])}",
        f"- Promotion trigger: {design['promotion_trigger']}",
        f"- Stop rule: {design['stop_rule']}",
        "",
        "## Rank Table Contract",
        "",
        f"- Preset id: `{contract['preset_id']}`",
        f"- External-only provenance: `{contract['external_only_provenance']}`",
        f"- Frozen before held-out scan: `{contract['frozen_before_heldout_scan']}`",
        f"- Canonical rank ordering: {contract['canonical_rank_ordering']}",
        f"- Seed-to-rank mapping: {contract['seed_to_rank_mapping']}",
        f"- Decoder-public version id: `{contract['decoder_public_version_id']}`",
        f"- Checksum policy: {contract['checksum_policy']}",
        f"- Max table bytes: `{contract['max_table_bytes']}`",
        f"- Max entry bytes: `{contract['max_entry_bytes']}`",
        f"- Golden manifest SHA-256: `{contract['golden_manifest_sha256']}`",
        "",
        "## Metadata Accounting",
        "",
        f"- Preset selector bytes: `{accounting['preset_selector_bytes']}`",
        f"- Preset version bytes: `{accounting['preset_version_bytes']}`",
        f"- Rank model id bytes: `{accounting['rank_model_id_bytes']}`",
        f"- Span record base bytes: `{accounting['span_record_base_bytes']}`",
        f"- Literal record base bytes: `{accounting['literal_record_base_bytes']}`",
        f"- Rank seed bytes: `{accounting['rank_seed_bytes']}`",
        f"- Selected-span formula: `{accounting['selected_span_record_bytes_formula']}`",
        f"- Literal formula: `{accounting['literal_record_bytes_formula']}`",
        f"- Full-stream delta formula: `{accounting['full_stream_delta_formula']}`",
        "",
        "## Accession Gate",
        "",
        f"- External accession status: `{gate['external_accession_status']}`",
        f"- External manifest complete: `{gate['external_manifest_complete']}`",
        f"- Paired manifest ready: `{gate['paired_manifest_ready']}`",
        f"- Validation errors: `{gate['validation_error_count']}`",
        f"- Compute allowed: `{gate['compute_allowed']}`",
        f"- Required fields: {', '.join(f'`{field}`' for field in gate['required_fields'])}",
        "",
        "## Golden Vectors",
        "",
        "| rank | seed | family | expansion len | expansion sha256 |",
        "| ---: | --- | --- | ---: | --- |",
    ]
    for row in payload["golden_vectors"]:
        lines.append(
            f"| {row['rank']} | `{row['seed_hex']}` | `{cell(row['family'])}` | "
            f"{row['example_expansion_len']} | `{row['example_expansion_sha256']}` |"
        )
    lines.extend(["", "## Control Suite", ""])
    for control in payload["control_suite"]:
        lines.append(f"- `{control}`")
    lines.extend(["", "## Promotion Gate", ""])
    for key, value in payload["promotion_gate"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Stop Rules", ""])
    for rule in payload["stop_rules"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this contract to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated frozen rank-coded span files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("frozen_rank_coded_span_generator.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("frozen rank-coded span source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("frozen_rank_coded_span_generator.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "performs_replay",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "allows_broad_compute",
        "overrides_search_frontier_gate",
        "uses_external_corpus_payloads",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"frozen rank scope field must be false: {field}")
    data = payload["summary"]
    if data["promotion_ready"]:
        raise SystemExit("frozen rank contract cannot promote from a manifest-only artifact")
    if data["compute_allowed"] or data["replay_allowed"]:
        raise SystemExit("frozen rank contract cannot allow compute or replay")
    if data["external_manifest_ready"]:
        raise SystemExit("frozen rank contract must be reviewed before external-ready promotion")
    if data["natural_corpus_proven"]:
        raise SystemExit("frozen rank contract cannot claim natural-corpus proof")
    if data["broad_depth_search_allowed"]:
        raise SystemExit("frozen rank contract cannot override the search frontier gate")
    if payload["rank_table_contract"]["golden_manifest_sha256"] != golden_manifest_hash():
        raise SystemExit("frozen rank golden manifest hash is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Frozen Rank-Coded Span Generator",
        "No Seed Search",
        "manifest/spec/golden-vector",
        "performs no replay",
        "not natural-corpus proof",
        "not `.tlmr` format support",
        "External manifest ready",
        "Metadata Accounting",
        "Accession Gate",
        "Golden Vectors",
        "Control Suite",
        "Promotion Gate",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"FROZEN_RANK_CODED_SPAN_GENERATOR.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
