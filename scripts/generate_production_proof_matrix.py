#!/usr/bin/env python3
"""Generate the Telomere production-readiness proof matrix.

This is a no-compute release evidence ledger. It does not promote Telomere to
production; it records exactly which release-readiness gates are qualified,
which remain blocked by evidence, and which must be rerun for each candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_candidate_runtime_verification


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "production_proof_matrix.json"
REPORT_MD = DOCS / "PRODUCTION_PROOF_MATRIX.md"
GENERATED_BY = "scripts/generate_production_proof_matrix.py"

SOURCE_PATHS = {
    "format_sha256": DOCS / "FORMAT.md",
    "release_checklist_sha256": DOCS / "RELEASE_CHECKLIST.md",
    "architecture_sha256": DOCS / "ARCHITECTURE.md",
    "acceleration_md_sha256": DOCS / "ACCELERATION.md",
    "acceleration_report_sha256": DOCS / "acceleration_report.json",
    "scale_performance_md_sha256": DOCS / "SCALE_PERFORMANCE.md",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "bounded_streaming_memory_gate_md_sha256": DOCS / "BOUNDED_STREAMING_MEMORY_GATE.md",
    "bounded_streaming_memory_gate_json_sha256": DOCS / "bounded_streaming_memory_gate.json",
    "streaming_economics_gate_md_sha256": DOCS / "STREAMING_ECONOMICS_GATE.md",
    "streaming_economics_gate_json_sha256": DOCS / "streaming_economics_gate.json",
    "ui_workflow_smoke_md_sha256": DOCS / "UI_WORKFLOW_SMOKE.md",
    "ui_workflow_smoke_json_sha256": DOCS / "ui_workflow_smoke.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "ci_workflow_sha256": ROOT / ".github/workflows/ci.yml",
    "cargo_toml_sha256": ROOT / "Cargo.toml",
    "evidence_regimen_sha256": ROOT / "scripts/generate_evidence_regimen.py",
    "candidate_runtime_verification_script_sha256": ROOT
    / "scripts/generate_candidate_runtime_verification.py",
    "v1_header_sha256": ROOT / "src/tlmr.rs",
    "v2_format_sha256": ROOT / "src/tlmr_v2.rs",
    "tauri_host_sha256": ROOT / "src-tauri/src/main.rs",
    "ui_index_sha256": ROOT / "ui/index.html",
}

REQUIRED_RELEASE_COMMANDS = generate_candidate_runtime_verification.REQUIRED_RELEASE_COMMANDS
CANDIDATE_RUNTIME_CAPTURE_COMMAND = (
    "python scripts/generate_candidate_runtime_verification.py"
)
CANDIDATE_RUNTIME_CHECK_COMMAND = (
    "python scripts/generate_candidate_runtime_verification.py --check"
)


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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def release_command_coverage(release_text: str, ci_text: str) -> dict[str, Any]:
    release_commands = REQUIRED_RELEASE_COMMANDS + [
        CANDIDATE_RUNTIME_CAPTURE_COMMAND,
        CANDIDATE_RUNTIME_CHECK_COMMAND,
    ]
    missing_from_release = [command for command in release_commands if command not in release_text]
    missing_from_ci = [
        command
        for command in REQUIRED_RELEASE_COMMANDS
        if command.startswith("cargo ") and command not in ci_text
    ]
    return {
        "required_commands": REQUIRED_RELEASE_COMMANDS,
        "runtime_verification_commands": [
            CANDIDATE_RUNTIME_CAPTURE_COMMAND,
            CANDIDATE_RUNTIME_CHECK_COMMAND,
        ],
        "missing_from_release_checklist": missing_from_release,
        "missing_from_ci": missing_from_ci,
        "release_checklist_covers_required_commands": not missing_from_release,
        "ci_covers_required_cargo_commands": not missing_from_ci,
    }


def compatibility_policy_coverage(format_text: str, release_text: str) -> dict[str, Any]:
    combined = " ".join((format_text + "\n" + release_text).lower().split())
    required_phrases = [
        ".tlmr` v1 is the only production-supported",
        ".tlmr` v2 is experimental",
        "not a production compatibility target yet",
        "pre-v1 experimental headers are unsupported",
        "standalone migration tool",
        "future production releases must",
        "never silently reinterpret",
        "preserve hasher metadata",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in combined]
    return {
        "required_phrases": required_phrases,
        "missing_phrases": missing,
        "compatibility_policy_complete": not missing,
    }


def gate(
    gate_id: str,
    status: str,
    evidence: list[str],
    finding: str,
    promotion_requirement: str,
    owner_group: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "status": status,
        "owner_group": owner_group,
        "authoritative_evidence": evidence,
        "finding": finding,
        "promotion_requirement": promotion_requirement,
    }


def build_gates(
    release_coverage: dict[str, Any],
    compatibility_policy: dict[str, Any],
    acceleration: dict[str, Any],
    scale: dict[str, Any],
    bounded_memory: dict[str, Any],
    streaming_gate: dict[str, Any],
    ui_smoke: dict[str, Any],
    decision: dict[str, Any],
    frontier: dict[str, Any],
    runtime_verification: dict[str, Any],
) -> list[dict[str, Any]]:
    detected = acceleration["detected"]
    scale_summary = summary(scale) or scale
    bounded_summary = summary(bounded_memory)
    streaming_summary = summary(streaming_gate)
    ui_summary = summary(ui_smoke)
    decision_summary = summary(decision)
    frontier_summary = summary(frontier)
    runtime_current = bool(
        runtime_verification["runtime_verification_current"]
        and runtime_verification["all_required_commands_passed"]
    )

    return [
        gate(
            "v1-format-compatibility-contract",
            "qualified",
            ["docs/FORMAT.md", "src/tlmr.rs", "tests/tlmr_header.rs"],
            ".tlmr v1 has a documented 40-byte header, hasher metadata, Lotus preset, one layer, byte-aligned seed payloads, and output-hash validation.",
            "Keep v1 compatibility stable across a release candidate and publish migration rules before changing semantics.",
            "format-policy",
        ),
        gate(
            "v2-experimental-boundary",
            "blocked-by-evidence",
            ["docs/FORMAT.md", "src/tlmr_v2.rs", "tests/indexed_v2.rs"],
            ".tlmr v2 decodes recursive layers without an external index, but the format remains explicitly experimental.",
            "Do not promote v2 to stable until compatibility guarantees, migration rules, and non-planted workload wins are proven.",
            "format-policy",
        ),
        gate(
            "release-gate-definitions",
            (
                "qualified"
                if release_coverage["release_checklist_covers_required_commands"]
                and release_coverage["ci_covers_required_cargo_commands"]
                else "open"
            ),
            ["docs/RELEASE_CHECKLIST.md", ".github/workflows/ci.yml"],
            "Release checklist and CI cover the required cargo/doc gates recorded by this matrix.",
            "Each release candidate must rerun every gate on the exact candidate tree.",
            "meta-research",
        ),
        gate(
            "candidate-runtime-verification",
            "qualified" if runtime_current else "runtime-required",
            [
                "docs/RELEASE_CHECKLIST.md",
                "docs/CANDIDATE_RUNTIME_VERIFICATION.md",
                "docs/candidate_runtime_verification.json",
                "docs/candidate_runtime_verification/*.txt",
            ],
            (
                f"Fresh candidate runtime artifact is current and records {runtime_verification['runtime_verification_passed_count']} passed release commands."
                if runtime_current
                else f"Fresh candidate runtime artifact is not current: {runtime_verification['runtime_verification_reason']}."
            ),
            "Attach fresh command output for fmt, clippy, tests, GPU feature check, doc lint, ledger checks, and Tauri checks before release.",
            "meta-research",
        ),
        gate(
            "acceleration-value",
            "blocked-by-evidence",
            ["docs/ACCELERATION.md", "docs/acceleration_report.json"],
            f"Acceleration status is {detected['status']}; production_ready={detected['production_ready']}; real_kernel_detected={detected['real_kernel_detected']}.",
            "Show real CPU/GPU parity plus measured hardware speed or energy wins on a promoted workload before marketing acceleration.",
            "acceleration",
        ),
        gate(
            "scale-and-memory-envelope",
            "qualified" if scale_summary["promotion_met"] else "open",
            [
                "docs/SCALE_PERFORMANCE.md",
                "docs/scale_performance_report.json",
                "docs/BOUNDED_STREAMING_MEMORY_GATE.md",
                "docs/STREAMING_ECONOMICS_GATE.md",
            ],
            f"Current 16 MiB planted-density scale is interpretable, next-double peak memory is estimated at {scale_summary['next_double_peak_memory_mib_at_current_ratio']} MiB, bounded memory status is {bounded_summary['gate_status']}, and streaming gate status is {streaming_summary['gate_status']}.",
            "Replace target-table estimate preflight and planted-density memory evidence with full RSS containment or chunked target tables on real workload sizing.",
            "compute-economics",
        ),
        gate(
            "natural-workload-evidence",
            "blocked-by-evidence",
            [
                "docs/RESEARCH_DECISION.md",
                "docs/RESEARCH_FRONTIER.md",
                "docs/VIABILITY.md",
            ],
            f"Decision remains {decision_summary['decision']}; best non-planted expectation is {frontier_summary['best_non_planted_gib_for_one_expected_hit']} GiB for one expected hit; streaming compute reopen allowed={streaming_summary['compute_reopen_allowed']}.",
            "Prove repeatable non-planted selected spans or negative delta with controls intact.",
            "corpus-transform",
        ),
        gate(
            "operator-ui-evidence",
            "qualified" if ui_summary["promotion_met"] else "open",
            ["docs/UI_WORKFLOW_SMOKE.md", "src-tauri/src/main.rs", "ui/index.html"],
            f"Static UI/Tauri smoke covers {ui_summary['required_artifact_count']} artifacts and {ui_summary['required_card_count']} cards with no missing DTO/mock fields.",
            "Pair static smoke with a desktop runtime run before release.",
            "operator-ui",
        ),
        gate(
            "compatibility-and-migration-policy",
            (
                "qualified"
                if compatibility_policy["compatibility_policy_complete"]
                else "blocked-by-evidence"
            ),
            ["docs/FORMAT.md", "docs/RELEASE_CHECKLIST.md"],
            (
                "The current policy defines v1 as the only production-supported format, keeps v2 experimental, rejects pre-v1 headers, and requires a standalone migration tool before removing v1 support."
                if compatibility_policy["compatibility_policy_complete"]
                else "Pre-v1 headers are unsupported unless a standalone migration tool is added, and v2 stability is not guaranteed."
            ),
            (
                "Keep this policy attached to each release candidate and update the production matrix before promoting any new supported format."
                if compatibility_policy["compatibility_policy_complete"]
                else "Define supported format versions, migration policy, and compatibility guarantees for every production-supported format."
            ),
            "format-policy",
        ),
    ]


def build_report() -> dict[str, Any]:
    format_text = text(DOCS / "FORMAT.md")
    release_text = text(DOCS / "RELEASE_CHECKLIST.md")
    ci_text = text(ROOT / ".github/workflows/ci.yml")
    acceleration = load_json(DOCS / "acceleration_report.json")
    scale = load_json(DOCS / "scale_performance_report.json")
    bounded_memory = load_json(DOCS / "bounded_streaming_memory_gate.json")
    streaming_gate = load_json(DOCS / "streaming_economics_gate.json")
    ui_smoke = load_json(DOCS / "ui_workflow_smoke.json")
    decision = load_json(DOCS / "research_decision.json")
    frontier = load_json(DOCS / "research_frontier.json")
    runtime_verification = (
        generate_candidate_runtime_verification.runtime_summary_for_matrix()
    )
    release_coverage = release_command_coverage(release_text, ci_text)
    compatibility_policy = compatibility_policy_coverage(format_text, release_text)
    gates = build_gates(
        release_coverage,
        compatibility_policy,
        acceleration,
        scale,
        bounded_memory,
        streaming_gate,
        ui_smoke,
        decision,
        frontier,
        runtime_verification,
    )
    counts = Counter(gate["status"] for gate in gates)
    blocked = [gate for gate in gates if gate["status"] == "blocked-by-evidence"]
    runtime_required = [gate for gate in gates if gate["status"] == "runtime-required"]
    production_proven = (
        not blocked
        and not runtime_required
        and bool(summary(decision)["production_proven"])
        and release_coverage["release_checklist_covers_required_commands"]
        and release_coverage["ci_covers_required_cargo_commands"]
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "production proof matrix",
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "marks_production_ready": production_proven,
        },
        "source_hashes": source_hashes(),
        "release_command_coverage": release_coverage,
        "compatibility_policy_coverage": compatibility_policy,
        "summary": {
            "production_status": (
                "production_ready" if production_proven else "not_production_ready"
            ),
            "production_proven": production_proven,
            "production_recommendation": (
                "candidate_can_be_promoted"
                if production_proven
                else "do_not_promote_to_production"
            ),
            "gate_count": len(gates),
            "qualified_count": int(counts["qualified"]),
            "open_count": int(counts["open"]),
            "runtime_required_count": int(counts["runtime-required"]),
            "blocked_by_evidence_count": int(counts["blocked-by-evidence"]),
            "blocked_gate_ids": [gate["gate_id"] for gate in blocked],
            "runtime_required_gate_ids": [
                gate["gate_id"] for gate in runtime_required
            ],
            "release_checklist_covers_required_commands": release_coverage[
                "release_checklist_covers_required_commands"
            ],
            "compatibility_policy_complete": compatibility_policy[
                "compatibility_policy_complete"
            ],
            "ci_covers_required_cargo_commands": release_coverage[
                "ci_covers_required_cargo_commands"
            ],
            "acceleration_status": acceleration["detected"]["status"],
            "real_gpu_kernel_detected": bool(
                acceleration["detected"]["real_kernel_detected"]
            ),
            "scale_next_double_peak_memory_mib": (summary(scale) or scale)[
                "next_double_peak_memory_mib_at_current_ratio"
            ],
            "ui_smoke_promotion_met": bool(summary(ui_smoke)["promotion_met"]),
            "research_decision": summary(decision)["decision"],
            "runtime_verification_present": runtime_verification[
                "runtime_verification_present"
            ],
            "runtime_verification_current": runtime_verification[
                "runtime_verification_current"
            ],
            "runtime_verification_reason": runtime_verification[
                "runtime_verification_reason"
            ],
            "runtime_verification_command_count": runtime_verification[
                "runtime_verification_command_count"
            ],
            "runtime_verification_passed_count": runtime_verification[
                "runtime_verification_passed_count"
            ],
            "runtime_verification_failed_count": runtime_verification[
                "runtime_verification_failed_count"
            ],
        },
        "gates": gates,
        "promotion_rule": (
            "Do not promote Telomere to production until blocked_by_evidence_count "
            "and runtime_required_count are zero, production_proven is true, and "
            "fresh release-candidate command output is attached."
        ),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Production Proof Matrix",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in release evidence.",
        "This is a No Seed Search production-readiness audit: it performs no seed search, makes no compression claim, and does not promote Telomere to production.",
        "",
        "## Verdict",
        "",
        f"- Production status: `{data['production_status']}`",
        f"- Production proven: `{data['production_proven']}`",
        f"- Recommendation: `{data['production_recommendation']}`",
        f"- Gates: `{data['gate_count']}` total, `{data['qualified_count']}` qualified, `{data['open_count']}` open, `{data['runtime_required_count']}` runtime-required, `{data['blocked_by_evidence_count']}` blocked-by-evidence",
        f"- Release checklist covers required commands: `{data['release_checklist_covers_required_commands']}`",
        f"- Compatibility policy complete: `{data['compatibility_policy_complete']}`",
        f"- CI covers required cargo commands: `{data['ci_covers_required_cargo_commands']}`",
        f"- Acceleration status: `{data['acceleration_status']}`",
        f"- Real GPU kernel detected: `{data['real_gpu_kernel_detected']}`",
        f"- Next-double peak memory estimate: `{data['scale_next_double_peak_memory_mib']}` MiB",
        f"- UI smoke promotion met: `{data['ui_smoke_promotion_met']}`",
        f"- Research decision: `{data['research_decision']}`",
        f"- Candidate runtime verification current: `{data['runtime_verification_current']}`",
        f"- Candidate runtime verification commands: `{data['runtime_verification_passed_count']}` passed / `{data['runtime_verification_command_count']}` required",
        f"- Candidate runtime verification reason: `{data['runtime_verification_reason']}`",
        "",
        "Telomere is not production ready yet. The matrix keeps the release path explicit without weakening v1 compatibility, promoting experimental v2, or treating planted-density results as real workload proof.",
        "",
        "## Promotion Rule",
        "",
        payload["promotion_rule"],
        "",
        "## Gates",
        "",
        "| gate | status | group | finding | promotion requirement | evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["gates"]:
        evidence = ", ".join(f"`{path}`" for path in item["authoritative_evidence"])
        lines.append(
            f"| `{cell(item['gate_id'])}` | `{cell(item['status'])}` | `{cell(item['owner_group'])}` | {cell(item['finding'])} | {cell(item['promotion_requirement'])} | {evidence} |"
        )

    lines.extend(["", "## Required Release Commands", ""])
    coverage = payload["release_command_coverage"]
    for command in coverage["required_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "Runtime proof capture:", ""])
    for command in coverage["runtime_verification_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## Coverage Checks",
            "",
            f"- Missing from release checklist: `{coverage['missing_from_release_checklist']}`",
            f"- Missing from CI cargo gates: `{coverage['missing_from_ci']}`",
            f"- Missing compatibility policy phrases: `{payload['compatibility_policy_coverage']['missing_phrases']}`",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated production proof matrix files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("production_proof_matrix.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("production proof matrix source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("production_proof_matrix.json is stale; regenerate it")

    data = payload["summary"]
    if data["production_proven"] and data["blocked_by_evidence_count"]:
        raise SystemExit("production matrix marked proven with blocked gates")
    if data["production_proven"] and data["runtime_required_count"]:
        raise SystemExit("production matrix marked proven with runtime-required gates")
    if data["production_status"] == "production_ready" and not data["production_proven"]:
        raise SystemExit("production matrix status contradicts production_proven")
    if not data["release_checklist_covers_required_commands"]:
        raise SystemExit("release checklist is missing required commands")
    if not data["compatibility_policy_complete"]:
        raise SystemExit("compatibility policy coverage is incomplete")
    if not data["ci_covers_required_cargo_commands"]:
        raise SystemExit("CI is missing required cargo commands")
    if "do_not_promote_to_production" != data["production_recommendation"]:
        raise SystemExit("production matrix should not promote the current evidence")

    text_body = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Production Proof Matrix",
        "No Seed Search",
        "not production ready",
        "blocked-by-evidence",
        "candidate-runtime-verification",
        "supported format",
        "Compatibility policy complete",
        "real workload",
        "CPU/GPU parity",
        "fresh release-candidate command output",
        "Candidate runtime verification current",
        "Source Artifacts",
    ):
        if phrase not in text_body:
            raise SystemExit(f"PRODUCTION_PROOF_MATRIX.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated production proof matrix files",
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
