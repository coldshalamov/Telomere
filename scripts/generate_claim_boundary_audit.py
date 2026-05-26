#!/usr/bin/env python3
"""Generate the Telomere claim-boundary audit.

This is a documentation safety rail. It reads the generated proof/gate ledgers,
then scans the public research docs for positive claims that would contradict
the current evidence state. It performs no seed search and makes no compression
claim of its own.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "claim_boundary_audit.json"
REPORT_MD = DOCS / "CLAIM_BOUNDARY_AUDIT.md"
GENERATED_BY = "scripts/generate_claim_boundary_audit.py"
PROMPT_DIR = DOCS / "agent_prompts"

SOURCE_LEDGER_PATHS = {
    "research_decision_sha256": DOCS / "research_decision.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "production_proof_matrix_sha256": DOCS / "production_proof_matrix.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "external_corpus_accession_sha256": DOCS / "external_corpus_accession.json",
    "goal_completion_audit_sha256": DOCS / "goal_completion_audit.json",
    "research_hypotheses_sha256": DOCS / "research_hypotheses.json",
    "research_team_packet_sha256": DOCS / "research_team_packet.json",
}

SCAN_PATHS = [
    Path("README.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/FORMAT.md"),
    Path("docs/RESULTS.md"),
    Path("docs/RESEARCH_PROGRAM.md"),
    Path("docs/RESEARCH_DECISION.md"),
    Path("docs/RESEARCH_FRONTIER.md"),
    Path("docs/RESEARCH_HYPOTHESES.md"),
    Path("docs/RESEARCH_TEAM_PACKET.md"),
    Path("docs/RESEARCH_AGENT_PROMPTS.md"),
    Path("docs/agent_reports/REPORT_TEMPLATES.md"),
    Path("docs/RESEARCH_AGENT_RESULT_INTAKE.md"),
    Path("docs/EXPERIMENT_QUEUE.md"),
    Path("docs/VIABILITY.md"),
    Path("docs/NATURAL_CORPUS_PROOF_MATRIX.md"),
    Path("docs/PRODUCTION_PROOF_MATRIX.md"),
    Path("docs/SEARCH_FRONTIER_GATE.md"),
    Path("docs/BOUNDED_STREAMING_MEMORY_GATE.md"),
    Path("docs/STREAMING_ECONOMICS_GATE.md"),
    Path("docs/LONG_SPAN_BUNDLE_GATE.md"),
    Path("docs/MECHANISM_CLOSURE_AUDIT.md"),
    Path("docs/NEXT_MECHANISM_DESIGNS.md"),
    Path("docs/FROZEN_RANK_CODED_SPAN_GENERATOR.md"),
    Path("docs/FROZEN_RANK_SOURCE_CANDIDATES.md"),
    Path("docs/EXTERNAL_CORPUS_ACCESSION.md"),
    Path("docs/SEED_TABLE_PRESET_REPLAY.md"),
    Path("docs/SEED_TABLE_FASTA_ABLATION.md"),
    Path("docs/RELEASE_CHECKLIST.md"),
    Path("docs/GENERATED_LEDGER_PIPELINE.md"),
]

CONDITIONAL_CONTEXT = (
    "promotion trigger",
    "promotion_gate",
    "only when",
    "until",
    "before",
    "stop rule",
    "reports zero",
    "would reopen",
    "requires",
    "future",
    "if ",
    "unless",
    "do not",
    "cannot",
    "not ",
    "false",
    "blocked",
)


@dataclass(frozen=True)
class ClaimRule:
    rule_id: str
    gate_field: str
    expected_value: bool
    patterns: tuple[str, ...]
    description: str


CLAIM_RULES = [
    ClaimRule(
        "natural-corpus-proof",
        "natural_corpus_proven",
        False,
        (
            r"\bnatural[- ]corpus (compression )?(is )?proven\b",
            r"\bnatural[- ]corpus viability (is )?proven\b",
            r"\bnatural_corpus_proven\s*[:=]\s*true\b",
            r"\bnatural[- ]corpus proven:\s*`?true`?\b",
        ),
        "Natural-corpus proof is not established.",
    ),
    ClaimRule(
        "production-proof",
        "production_proven",
        False,
        (
            r"\b(is|are|now|currently|already)\s+production[- ]ready\b",
            r"\bproduction_proven\s*[:=]\s*true\b",
            r"\bproduction proven:\s*`?true`?\b",
            r"\bproduction ready:\s*(\*\*)?true(\*\*)?\b",
        ),
        "Production readiness is not established.",
    ),
    ClaimRule(
        "broad-depth-search",
        "broad_depth_search_allowed",
        False,
        (
            r"\bbroad depth search allowed:\s*`?true`?\b",
            r"\bbroad_depth_search_allowed\s*[:=]\s*true\b",
            r"\bungated broad depth search\b",
        ),
        "Broad depth search remains gated.",
    ),
    ClaimRule(
        "format-promotion",
        "format_promotion_allowed",
        False,
        (
            r"\bformat promotion allowed:\s*`?true`?\b",
            r"\bformat_promotion_allowed\s*[:=]\s*true\b",
            r"\bv2 is production[- ]supported\b",
        ),
        "Format promotion remains blocked.",
    ),
    ClaimRule(
        "external-corpus-compute",
        "external_compute_allowed",
        False,
        (
            r"\bexternal compute allowed:\s*`?true`?\b",
            r"\bcompute allowed:\s*`?true`?\b",
            r"\bcompute_allowed\s*[:=]\s*true\b",
        ),
        "External corpus compute remains disallowed by the accession gate.",
    ),
    ClaimRule(
        "random-data-compresses",
        "random_data_should_compress",
        False,
        (
            r"\brandom data should compress\b",
            r"\brandom data is expected to compress\b",
            r"\brandom data will compress\b",
        ),
        "Random data is expected to bloat, not compress.",
    ),
    ClaimRule(
        "universal-compressor",
        "universal_compressor",
        False,
        (
            r"\btelomere is a universal compressor\b",
            r"\buniversal lossless compressor\b",
        ),
        "Telomere is not a universal compressor.",
    ),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def source_hashes() -> dict[str, str]:
    hashes = {name: sha256(path) for name, path in SOURCE_LEDGER_PATHS.items()}
    for path in scan_paths():
        hashes[f"scan_{path.as_posix()}_sha256"] = sha256(ROOT / path)
    return hashes


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def scan_paths() -> list[Path]:
    prompt_paths: list[Path] = []
    if PROMPT_DIR.exists():
        prompt_paths = [
            path.relative_to(ROOT) for path in sorted(PROMPT_DIR.glob("*.prompt.txt"))
        ]
    return SCAN_PATHS + prompt_paths


def evidence_state() -> dict[str, Any]:
    decision = summary(load_json(DOCS / "research_decision.json"))
    frontier = summary(load_json(DOCS / "research_frontier.json"))
    natural = summary(load_json(DOCS / "natural_corpus_proof_matrix.json"))
    production = summary(load_json(DOCS / "production_proof_matrix.json"))
    search = summary(load_json(DOCS / "search_frontier_gate.json"))
    accession = summary(load_json(DOCS / "external_corpus_accession.json"))
    return {
        "natural_corpus_proven": bool(natural.get("natural_corpus_proven", False)),
        "production_proven": bool(production.get("production_proven", False)),
        "broad_depth_search_allowed": bool(
            search.get("broad_depth_search_allowed", False)
            or frontier.get("broad_depth_search_allowed", False)
        ),
        "format_promotion_allowed": bool(search.get("format_promotion_allowed", False)),
        "external_compute_allowed": bool(accession.get("compute_allowed", False)),
        "random_data_should_compress": False,
        "universal_compressor": False,
        "decision": decision.get("decision"),
        "verdict": decision.get("verdict"),
        "ready_count": decision.get("ready_count"),
        "blocked_by_evidence_count": decision.get("blocked_by_evidence_count"),
        "external_accession_status": accession.get("accession_status"),
    }


def line_is_conditional(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in CONDITIONAL_CONTEXT)


def scan_docs(state: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in scan_paths():
        full_path = ROOT / path
        for line_number, line in enumerate(full_path.read_text(encoding="utf-8").splitlines(), 1):
            if line_is_conditional(line):
                continue
            for rule in CLAIM_RULES:
                if state.get(rule.gate_field) != rule.expected_value:
                    continue
                for pattern in rule.patterns:
                    if re.search(pattern, line, flags=re.IGNORECASE):
                        findings.append(
                            {
                                "rule_id": rule.rule_id,
                                "path": path.as_posix(),
                                "line": line_number,
                                "pattern": pattern,
                                "text": line.strip(),
                                "description": rule.description,
                            }
                        )
    return findings


def build_report() -> dict[str, Any]:
    state = evidence_state()
    findings = scan_docs(state)
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "claim-boundary audit",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "allows_compute": False,
        },
        "source_hashes": source_hashes(),
        "evidence_state": state,
        "rules": [
            {
                "rule_id": rule.rule_id,
                "gate_field": rule.gate_field,
                "expected_value": rule.expected_value,
                "description": rule.description,
            }
            for rule in CLAIM_RULES
        ],
        "summary": {
            "claim_boundary_status": "clean" if not findings else "overclaim_detected",
            "finding_count": len(findings),
            "scanned_file_count": len(scan_paths()),
            "rule_count": len(CLAIM_RULES),
            "decision": state["decision"],
            "verdict": state["verdict"],
            "natural_corpus_proven": state["natural_corpus_proven"],
            "production_proven": state["production_proven"],
            "broad_depth_search_allowed": state["broad_depth_search_allowed"],
            "format_promotion_allowed": state["format_promotion_allowed"],
            "external_compute_allowed": state["external_compute_allowed"],
            "claim_boundary": (
                "No Seed Search; not natural-corpus proof; not production proof; "
                "not a compression claim; broad compute remains gated."
            ),
        },
        "findings": findings,
        "scanned_paths": [path.as_posix() for path in scan_paths()],
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Claim Boundary Audit",
        "",
        f"Generated by `{GENERATED_BY}` from current proof/gate ledgers and public research docs.",
        "This is a No Seed Search documentation audit. It launches no agents, performs no compression, is not natural-corpus proof, is not production proof, and does not authorize compute.",
        "",
        "## Summary",
        "",
        f"- Claim boundary status: `{summary_payload['claim_boundary_status']}`",
        f"- Findings: `{summary_payload['finding_count']}`",
        f"- Scanned files: `{summary_payload['scanned_file_count']}`",
        f"- Rules: `{summary_payload['rule_count']}`",
        f"- Decision: `{summary_payload['decision']}`",
        f"- Verdict: `{summary_payload['verdict']}`",
        f"- Natural-corpus proven: `{summary_payload['natural_corpus_proven']}`",
        f"- Production proven: `{summary_payload['production_proven']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Format promotion allowed: `{summary_payload['format_promotion_allowed']}`",
        f"- External compute allowed: `{summary_payload['external_compute_allowed']}`",
        "",
        "## Findings",
        "",
    ]
    if payload["findings"]:
        lines.extend(
            [
                "| rule | path | line | text |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for finding in payload["findings"]:
            lines.append(
                f"| `{cell(finding['rule_id'])}` | `{cell(finding['path'])}` | "
                f"{finding['line']} | {cell(finding['text'])} |"
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Rules",
            "",
            "| rule | gate field | expected | description |",
            "| --- | --- | --- | --- |",
        ]
    )
    for rule in payload["rules"]:
        lines.append(
            f"| `{cell(rule['rule_id'])}` | `{cell(rule['gate_field'])}` | "
            f"`{cell(rule['expected_value'])}` | {cell(rule['description'])} |"
        )

    lines.extend(
        [
            "",
            "## Scanned Paths",
            "",
        ]
    )
    for path in payload["scanned_paths"]:
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this audit to the exact upstream evidence and scanned text.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated claim boundary audit files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("claim_boundary_audit.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("claim_boundary_audit.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("claim_boundary_audit.json is stale; regenerate it")
    if payload["summary"]["finding_count"] != len(payload["findings"]):
        raise SystemExit("claim boundary audit finding count is stale")
    if payload["summary"]["finding_count"] != 0:
        raise SystemExit("claim boundary audit found unsupported claims")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "is_production_proof",
        "allows_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"claim boundary audit scope field must be false: {field}")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Claim Boundary Audit",
        "No Seed Search",
        "not natural-corpus proof",
        "not production proof",
        "does not authorize compute",
        "Findings",
        "Rules",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"CLAIM_BOUNDARY_AUDIT.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated claim-boundary audit"
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
