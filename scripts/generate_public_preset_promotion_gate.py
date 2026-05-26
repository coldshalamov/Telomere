#!/usr/bin/env python3
"""Generate the public Lotus preset promotion gate.

This is a no-compute coordination artifact. It consolidates seed-table and
public-dictionary preset evidence into explicit promotion/falsification gates
before any preset is treated as `.tlmr` format support.
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
REPORT_JSON = DOCS / "public_preset_promotion_gate.json"
REPORT_MD = DOCS / "PUBLIC_PRESET_PROMOTION_GATE.md"
GENERATED_BY = "scripts/generate_public_preset_promotion_gate.py"

SOURCE_PATHS = {
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "expander_salt_ensemble_sha256": DOCS / "expander_salt_ensemble.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "format_doc_sha256": DOCS / "FORMAT.md",
}


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


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def status(met: bool) -> str:
    return "qualified" if met else "blocked-by-evidence"


def gate_rows(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    seed_table = summary(inputs["seed_table_preset_probe"])
    schema = summary(inputs["schema_native_public_dictionary_replication"])
    schema_discovery = summary(inputs["schema_native_public_dictionaries"])
    salt = summary(inputs["expander_salt_ensemble"])
    ranking = summary(inputs["mechanism_experiment_ranking"])
    search = summary(inputs["search_frontier_gate"])

    canonical_signal = (
        int(seed_table["canonical_selected_spans"]) > 0
        and bool(seed_table["beats_sha256_baseline"])
    )
    public_dictionary_signal = (
        int(schema["standards_selected_spans"]) > 0
        and bool(schema["beats_sha256_baseline"])
        and bool(schema["beats_generic_dictionary_baseline"])
    )
    ordinary_diversity_met = (
        int(schema["standards_ordinary_negative_groups"]) >= 3
        or int(seed_table["canonical_ordinary_heldout_negative_groups"]) >= 3
    )
    control_separation_met = (
        int(schema["standards_control_negative_groups"]) == 0
        and int(seed_table["canonical_control_negative_groups"]) == 0
    )
    sha_baseline_met = (
        int(seed_table["sha256_selected_spans"]) == 0
        and int(schema["sha256_selected_spans"]) == 0
        and int(salt["salted_selected_span_rows"]) == 0
    )
    exact_decode_met = bool(schema["all_exact_decode"]) and bool(schema["all_corrupt_rejections"])
    format_open = bool(search["format_promotion_allowed"])

    return [
        {
            "gate_id": "mechanism-ranking",
            "status": status(ranking["top_lane_id"] == "seed-table-preset-probe"),
            "requirement": "public preset work remains the top non-depth mechanism lane",
            "observed": (
                f"top lane {ranking['top_lane_id']}; top status {ranking['top_status']}"
            ),
            "promotion_rule": "mechanism ranking keeps a public preset lane ahead of raw-depth escalation",
        },
        {
            "gate_id": "canonical-seed-table-signal",
            "status": status(canonical_signal),
            "requirement": "canonical seed-table v0 changes the selected-span distribution",
            "observed": (
                f"{seed_table['canonical_selected_spans']} selected spans; "
                f"best delta {seed_table['best_canonical_delta_bytes']} bytes; "
                f"beats sha256 {seed_table['beats_sha256_baseline']}"
            ),
            "promotion_rule": "selected spans exist and beat the SHA-256 baseline",
        },
        {
            "gate_id": "public-dictionary-signal",
            "status": status(public_dictionary_signal),
            "requirement": "decoder-public dictionary presets improve held-out rows",
            "observed": (
                f"{schema['standards_selected_spans']} standards selected spans; "
                f"{schema['standards_ordinary_negative_groups']} ordinary negative groups; "
                f"best delta {schema['best_standards_delta_bytes']} bytes"
            ),
            "promotion_rule": "standards dictionary beats SHA-256 and generic dictionary baselines",
        },
        {
            "gate_id": "ordinary-heldout-diversity",
            "status": status(ordinary_diversity_met),
            "requirement": "wins are distributed across unrelated ordinary held-out families",
            "observed": (
                f"schema standards ordinary groups {schema['standards_ordinary_negative_groups']}; "
                f"canonical ordinary groups {seed_table['canonical_ordinary_heldout_negative_groups']}"
            ),
            "promotion_rule": "at least three ordinary held-out negative groups",
        },
        {
            "gate_id": "control-separation",
            "status": status(control_separation_met),
            "requirement": "paired shadow, binary, random, and control dictionaries remain null",
            "observed": (
                f"standards control groups {schema['standards_control_negative_groups']}; "
                f"canonical control groups {seed_table['canonical_control_negative_groups']}; "
                f"schema claim {schema['claim_level']}"
            ),
            "promotion_rule": "zero comparable control negative groups",
        },
        {
            "gate_id": "random-trial-baseline",
            "status": status(sha_baseline_met),
            "requirement": "preset signal is not explained by equivalent hash trials or salted expanders",
            "observed": (
                f"seed-table SHA-256 selected {seed_table['sha256_selected_spans']}; "
                f"schema SHA-256 selected {schema['sha256_selected_spans']}; "
                f"salt selected rows {salt['salted_selected_span_rows']}"
            ),
            "promotion_rule": "SHA-256 and salted-expander baselines remain null",
        },
        {
            "gate_id": "exact-decode-and-corruption",
            "status": status(exact_decode_met),
            "requirement": "public preset evidence decodes exactly and rejects corrupt inputs",
            "observed": (
                f"all exact decode {schema['all_exact_decode']}; "
                f"all corrupt rejections {schema['all_corrupt_rejections']}; "
                f"discovery exact decode {schema_discovery['all_exact_decode']}"
            ),
            "promotion_rule": "all promoted rows decode exactly and reject corruption",
        },
        {
            "gate_id": "format-promotion-boundary",
            "status": status(format_open),
            "requirement": "format metadata is allowed only after search-frontier promotion opens",
            "observed": (
                f"format promotion allowed {search['format_promotion_allowed']}; "
                f"broad depth search allowed {search['broad_depth_search_allowed']}"
            ),
            "promotion_rule": "SEARCH_FRONTIER_GATE explicitly allows format promotion",
        },
    ]


def build_report() -> dict[str, Any]:
    inputs = {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
        if path.suffix == ".json"
    }
    rows = gate_rows(inputs)
    qualified_count = sum(1 for row in rows if row["status"] == "qualified")
    blocked_rows = [row for row in rows if row["status"] != "qualified"]
    seed_table = summary(inputs["seed_table_preset_probe"])
    schema = summary(inputs["schema_native_public_dictionary_replication"])
    search = summary(inputs["search_frontier_gate"])

    candidate_profiles = [
        {
            "candidate_id": "canonical-seed-table-v0",
            "claim_level": "signal_without_ordinary_heldout_diversity",
            "selected_spans": seed_table["canonical_selected_spans"],
            "ordinary_negative_groups": seed_table[
                "canonical_ordinary_heldout_negative_groups"
            ],
            "control_negative_groups": seed_table["canonical_control_negative_groups"],
            "best_case": seed_table["best_canonical_case"],
            "best_delta_bytes": seed_table["best_canonical_delta_bytes"],
            "promotion_ready": False,
            "stop_reason": "ordinary held-out negative groups are zero",
        },
        {
            "candidate_id": "schema-standards-public-preset",
            "claim_level": schema["claim_level"],
            "selected_spans": schema["standards_selected_spans"],
            "ordinary_negative_groups": schema["standards_ordinary_negative_groups"],
            "control_negative_groups": schema["standards_control_negative_groups"],
            "best_case": schema["best_standards_case"],
            "best_delta_bytes": schema["best_standards_delta_bytes"],
            "promotion_ready": False,
            "stop_reason": schema["stop_reason"],
        },
    ]

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "public preset promotion gate",
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "gate_count": len(rows),
            "qualified_count": qualified_count,
            "blocked_by_evidence_count": len(blocked_rows),
            "blocked_gate_ids": [row["gate_id"] for row in blocked_rows],
            "promotion_met": len(blocked_rows) == 0,
            "claim_level": "public_preset_gate_blocked_by_controls",
            "top_candidate": "schema-standards-public-preset",
            "top_candidate_ordinary_negative_groups": schema[
                "standards_ordinary_negative_groups"
            ],
            "top_candidate_control_negative_groups": schema[
                "standards_control_negative_groups"
            ],
            "canonical_seed_table_selected_spans": seed_table["canonical_selected_spans"],
            "schema_standards_selected_spans": schema["standards_selected_spans"],
            "format_promotion_allowed": search["format_promotion_allowed"],
            "natural_corpus_compression_proven": False,
            "recommendation": "hold_public_preset_format_promotion",
            "stop_rule": (
                "Do not add a public preset registry or .tlmr preset metadata until "
                "ordinary held-out diversity, control separation, random-trial baseline, "
                "exact-decode, and SEARCH_FRONTIER_GATE format-promotion gates all pass."
            ),
            "conclusion": (
                "Public presets are the strongest non-depth mechanism signal, but "
                "current controls block promotion."
            ),
        },
        "candidate_profiles": candidate_profiles,
        "gates": rows,
        "agent_audit_briefs": [
            {
                "parallel_group": "corpus-transform",
                "mission": "design stronger paired controls and disjoint held-out families for public presets",
                "source_artifacts": [
                    "docs/SEED_TABLE_PRESET_PROBE.md",
                    "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
                    "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
                ],
                "forbidden_actions": [
                    "No Seed Search: do not run new broad seed sweeps",
                    "do not count shadow-control wins as natural-corpus proof",
                ],
            },
            {
                "parallel_group": "format-policy",
                "mission": "draft preset registry requirements only after promotion gates pass",
                "source_artifacts": [
                    "docs/FORMAT.md",
                    "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
                    "docs/RELEASE_CHECKLIST.md",
                ],
                "forbidden_actions": [
                    "do not add .tlmr format support while format-promotion-boundary is blocked",
                    "do not weaken v1/v2 compatibility guarantees",
                ],
            },
            {
                "parallel_group": "compute-economics",
                "mission": "compare preset wins against equivalent random-trial and metadata budgets",
                "source_artifacts": [
                    "docs/EXPANDER_SALT_ENSEMBLE.md",
                    "docs/MECHANISM_EXPERIMENT_RANKING.md",
                    "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
                ],
                "forbidden_actions": [
                    "do not reopen raw depth search from public-preset signal alone",
                    "do not ignore preset ID, registry, or compatibility bytes",
                ],
            },
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Public Preset Promotion Gate",
        "",
        f"Generated by `{GENERATED_BY}` from public preset, schema dictionary, salt ensemble, mechanism-ranking, and search-frontier artifacts.",
        "This is a No Seed Search promotion gate. It performs no seed search, is not `.tlmr` format support, is not natural-corpus proof, and is not a compression claim.",
        "",
        "## Summary",
        "",
        f"- Gate count: `{summary_payload['gate_count']}`",
        f"- Qualified: `{summary_payload['qualified_count']}`",
        f"- Blocked by evidence: `{summary_payload['blocked_by_evidence_count']}`",
        f"- Blocked gates: `{', '.join(summary_payload['blocked_gate_ids'])}`",
        f"- Promotion met: `{summary_payload['promotion_met']}`",
        f"- Claim level: `{summary_payload['claim_level']}`",
        f"- Top candidate: `{summary_payload['top_candidate']}`",
        f"- Top candidate ordinary groups: `{summary_payload['top_candidate_ordinary_negative_groups']}`",
        f"- Top candidate control groups: `{summary_payload['top_candidate_control_negative_groups']}`",
        f"- Format promotion allowed: `{summary_payload['format_promotion_allowed']}`",
        f"- Recommendation: `{summary_payload['recommendation']}`",
        "",
        summary_payload["conclusion"],
        "",
        "Stop rule: "
        + summary_payload["stop_rule"],
        "",
        "## Gate Matrix",
        "",
        "| gate | status | requirement | observed | promotion rule |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["gates"]:
        lines.append(
            f"| `{cell(row['gate_id'])}` | `{cell(row['status'])}` | "
            f"{cell(row['requirement'])} | {cell(row['observed'])} | "
            f"{cell(row['promotion_rule'])} |"
        )

    lines.extend(["", "## Candidate Profiles", ""])
    lines.extend(
        [
            "| candidate | claim level | selected spans | ordinary groups | control groups | best case | best delta | stop reason |",
            "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
        ]
    )
    for profile in payload["candidate_profiles"]:
        lines.append(
            f"| `{cell(profile['candidate_id'])}` | `{cell(profile['claim_level'])}` | "
            f"{profile['selected_spans']} | {profile['ordinary_negative_groups']} | "
            f"{profile['control_negative_groups']} | `{cell(profile['best_case'])}` | "
            f"{profile['best_delta_bytes']} | {cell(profile['stop_reason'])} |"
        )

    lines.extend(["", "## dispatching-parallel-agents Audit Briefs", ""])
    for brief in payload["agent_audit_briefs"]:
        lines.extend(
            [
                f"### {brief['parallel_group']}",
                "",
                f"- Mission: {brief['mission']}",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in brief['source_artifacts'])}",
                "- Forbidden actions:",
            ]
        )
        for action in brief["forbidden_actions"]:
            lines.append(f"- {action}")
        lines.append("")

    lines.extend(
        [
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this gate to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated public preset promotion gate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_promotion_gate.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_promotion_gate.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("public_preset_promotion_gate.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "overrides_search_frontier_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"public preset scope field must be false: {field}")
    if payload["summary"]["promotion_met"]:
        raise SystemExit("public preset promotion unexpectedly passed; review gates before promotion")
    gates = payload.get("gates", [])
    if len(gates) < 8:
        raise SystemExit("public preset promotion gate lost required rows")
    blocked = payload["summary"]["blocked_gate_ids"]
    for required in ("control-separation", "format-promotion-boundary"):
        if required not in blocked:
            raise SystemExit(f"public preset gate must remain blocked by {required}")

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Promotion Gate",
        "No Seed Search",
        "not `.tlmr` format support",
        "not natural-corpus proof",
        "Gate Matrix",
        "Candidate Profiles",
        "dispatching-parallel-agents Audit Briefs",
        "control-separation",
        "format-promotion-boundary",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_PROMOTION_GATE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated public preset gate"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
