#!/usr/bin/env python3
"""Generate the Telomere research-agent result-intake report.

This is the return path for `docs/RESEARCH_AGENT_PROMPTS.md`. It validates a
repository-local manifest of future subagent reports before any parallel lane
can be treated as integration-ready. It launches no agents, runs no seed search,
and makes no compression claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PROMPT_DIR = DOCS / "agent_prompts"
REPORT_DIR = DOCS / "agent_reports"
SOURCE_PROMPTS = DOCS / "research_agent_prompts.json"
SOURCE_CLAIMS = DOCS / "claim_boundary_audit.json"
SOURCE_GOAL_AUDIT = DOCS / "goal_completion_audit.json"
SOURCE_MANIFEST = REPORT_DIR / "manifest.json"
REPORT_JSON = DOCS / "research_agent_result_intake.json"
REPORT_MD = DOCS / "RESEARCH_AGENT_RESULT_INTAKE.md"
TEMPLATE_JSON = REPORT_DIR / "report_templates.json"
TEMPLATE_MD = REPORT_DIR / "REPORT_TEMPLATES.md"
GENERATED_BY = "scripts/generate_research_agent_result_intake.py"

REQUIRED_REPORT_FIELDS = (
    "report_id",
    "agent_id",
    "parallel_group",
    "prompt_path",
    "prompt_sha256",
    "status",
    "source_artifacts",
    "changed_files",
    "verification_commands",
    "claim_changes",
    "promotion_triggers",
    "stop_rules_checked",
    "summary",
    "submitted_at",
)

ALLOWED_REPORT_STATUSES = {
    "findings-only",
    "proposed-change",
    "blocked",
    "no-change",
}

PROHIBITED_CLAIM_PATTERNS = (
    (
        "natural-corpus-proof",
        r"\bnatural[- ]corpus (compression )?(is )?proven\b|\bnatural_corpus_proven\s*[:=]\s*true\b",
    ),
    (
        "production-proof",
        r"\b(is|are|now|currently|already)\s+production[- ]ready\b|\bproduction_proven\s*[:=]\s*true\b",
    ),
    (
        "broad-depth-search",
        r"\bbroad depth search allowed:\s*`?true`?\b|\bbroad_depth_search_allowed\s*[:=]\s*true\b|\bungated broad depth search\b",
    ),
    (
        "format-promotion",
        r"\bformat promotion allowed:\s*`?true`?\b|\bformat_promotion_allowed\s*[:=]\s*true\b|\bv2 is production[- ]supported\b",
    ),
    (
        "external-corpus-compute",
        r"\bexternal compute allowed:\s*`?true`?\b|\bcompute_allowed\s*[:=]\s*true\b",
    ),
    (
        "random-data-compresses",
        r"\brandom data should compress\b|\brandom data is expected to compress\b|\brandom data will compress\b",
    ),
    (
        "universal-compressor",
        r"\btelomere is a universal compressor\b|\buniversal lossless compressor\b",
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def require_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def prompt_records(prompt_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        prompt["agent_id"]: prompt
        for prompt in prompt_payload.get("agent_prompts", [])
        if isinstance(prompt, dict)
    }


def build_report_templates(prompts: dict[str, Any]) -> dict[str, Any]:
    templates = []
    for prompt in prompts.get("agent_prompts", []):
        prompt_path = ROOT / prompt["prompt_path"]
        templates.append(
            {
                "report_id": f"{prompt['agent_id']}-YYYY-MM-DD-readonly",
                "agent_id": prompt["agent_id"],
                "parallel_group": prompt["parallel_group"],
                "prompt_path": prompt["prompt_path"],
                "prompt_sha256": sha256(prompt_path),
                "status": "findings-only",
                "source_artifacts": prompt["source_artifacts"],
                "changed_files": [],
                "verification_commands": [],
                "claim_changes": [],
                "promotion_triggers": prompt["integration_gates"],
                "stop_rules_checked": [
                    "No Seed Search",
                    "not natural-corpus proof",
                    "not production proof",
                    "not a compression claim",
                    "do not launch broad compute",
                ],
                "summary": "Replace this with findings-first lane summary before registering the report.",
                "submitted_at": "YYYY-MM-DDTHH:MM:SSZ",
            }
        )
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "research-agent report templates",
            "launches_agents": False,
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "allows_compute": False,
        },
        "template_count": len(templates),
        "templates": templates,
    }


def source_hashes(manifest: dict[str, Any], prompts: dict[str, Any]) -> dict[str, str]:
    hashes = {
        "research_agent_prompts_sha256": sha256(SOURCE_PROMPTS),
        "goal_completion_audit_sha256": sha256(SOURCE_GOAL_AUDIT),
        "agent_reports_manifest_sha256": sha256(SOURCE_MANIFEST),
    }
    for prompt in prompts.get("agent_prompts", []):
        prompt_path = ROOT / prompt["prompt_path"]
        hashes[f"prompt_{prompt['agent_id']}_sha256"] = sha256(prompt_path)
    for report in manifest.get("reports", []):
        for artifact in report.get("source_artifacts", []):
            artifact_path = ROOT / artifact
            if artifact_path.is_file():
                hashes[f"report_source_{artifact}_sha256"] = sha256(artifact_path)
    return hashes


def claim_gate_state(claims: dict[str, Any]) -> dict[str, bool]:
    state = claims.get("evidence_state", {})
    return {
        "natural_corpus_proven": require_bool(state.get("natural_corpus_proven")),
        "production_proven": require_bool(state.get("production_proven")),
        "broad_depth_search_allowed": require_bool(
            state.get("broad_depth_search_allowed")
        ),
        "format_promotion_allowed": require_bool(state.get("format_promotion_allowed")),
        "external_compute_allowed": require_bool(state.get("external_compute_allowed")),
        "random_data_should_compress": require_bool(
            state.get("random_data_should_compress")
        ),
        "universal_compressor": require_bool(state.get("universal_compressor")),
    }


def claim_rule_allowed(rule_id: str, gates: dict[str, bool]) -> bool:
    return {
        "natural-corpus-proof": gates["natural_corpus_proven"],
        "production-proof": gates["production_proven"],
        "broad-depth-search": gates["broad_depth_search_allowed"],
        "format-promotion": gates["format_promotion_allowed"],
        "external-corpus-compute": gates["external_compute_allowed"],
        "random-data-compresses": gates["random_data_should_compress"],
        "universal-compressor": gates["universal_compressor"],
    }[rule_id]


def report_text(report: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in ("summary", "claim_changes", "promotion_triggers"):
        value = report.get(field)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return "\n".join(parts)


def validate_report(
    report: dict[str, Any],
    prompt_by_agent: dict[str, dict[str, Any]],
    gates: dict[str, bool],
    seen_report_ids: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    report_id = str(report.get("report_id", "<missing>"))

    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            findings.append(
                {
                    "report_id": report_id,
                    "rule": "missing-field",
                    "detail": f"missing required field: {field}",
                }
            )

    if report_id in seen_report_ids:
        findings.append(
            {
                "report_id": report_id,
                "rule": "duplicate-report-id",
                "detail": "report_id values must be unique",
            }
        )
    seen_report_ids.add(report_id)

    status = report.get("status")
    if status not in ALLOWED_REPORT_STATUSES:
        findings.append(
            {
                "report_id": report_id,
                "rule": "invalid-status",
                "detail": f"status must be one of {sorted(ALLOWED_REPORT_STATUSES)}",
            }
        )

    agent_id = report.get("agent_id")
    prompt_record = prompt_by_agent.get(agent_id)
    if prompt_record is None:
        findings.append(
            {
                "report_id": report_id,
                "rule": "unknown-agent",
                "detail": f"agent_id is not in docs/research_agent_prompts.json: {agent_id}",
            }
        )
        return findings

    if report.get("parallel_group") != prompt_record.get("parallel_group"):
        findings.append(
            {
                "report_id": report_id,
                "rule": "parallel-group-mismatch",
                "detail": "parallel_group must match the prompt pack",
            }
        )

    if report.get("prompt_path") != prompt_record.get("prompt_path"):
        findings.append(
            {
                "report_id": report_id,
                "rule": "prompt-path-mismatch",
                "detail": "prompt_path must match the prompt pack",
            }
        )

    prompt_path = ROOT / prompt_record["prompt_path"]
    expected_digest = sha256(prompt_path)
    if report.get("prompt_sha256") != expected_digest:
        findings.append(
            {
                "report_id": report_id,
                "rule": "prompt-hash-mismatch",
                "detail": "prompt_sha256 must match the standalone prompt file",
            }
        )

    for field in (
        "source_artifacts",
        "changed_files",
        "verification_commands",
        "claim_changes",
        "promotion_triggers",
        "stop_rules_checked",
    ):
        if field in report and not isinstance(report[field], list):
            findings.append(
                {
                    "report_id": report_id,
                    "rule": "non-list-field",
                    "detail": f"{field} must be a list",
                }
            )

    for artifact in report.get("source_artifacts", []):
        if not (ROOT / artifact).exists():
            findings.append(
                {
                    "report_id": report_id,
                    "rule": "missing-source-artifact",
                    "detail": f"source artifact does not exist: {artifact}",
                }
            )

    text = report_text(report)
    for rule_id, pattern in PROHIBITED_CLAIM_PATTERNS:
        if claim_rule_allowed(rule_id, gates):
            continue
        if re.search(pattern, text, flags=re.IGNORECASE):
            findings.append(
                {
                    "report_id": report_id,
                    "rule": f"unsupported-claim:{rule_id}",
                    "detail": "report text attempts to move a claim whose generated gate is still false",
                }
            )

    return findings


def validate_manifest(
    manifest: dict[str, Any],
    prompt_by_agent: dict[str, dict[str, Any]],
    gates: dict[str, bool],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if manifest.get("manifest_version") != 1:
        findings.append(
            {
                "report_id": "<manifest>",
                "rule": "manifest-version",
                "detail": "manifest_version must be 1",
            }
        )
    if not isinstance(manifest.get("reports"), list):
        findings.append(
            {
                "report_id": "<manifest>",
                "rule": "manifest-reports-list",
                "detail": "reports must be a list",
            }
        )
        return findings

    seen_report_ids: set[str] = set()
    for report in manifest["reports"]:
        if not isinstance(report, dict):
            findings.append(
                {
                    "report_id": "<manifest>",
                    "rule": "report-object",
                    "detail": "every reports entry must be an object",
                }
            )
            continue
        findings.extend(validate_report(report, prompt_by_agent, gates, seen_report_ids))
    return findings


def build_report() -> dict[str, Any]:
    prompts = load_json(SOURCE_PROMPTS)
    claims = load_json(SOURCE_CLAIMS)
    goal_audit = load_json(SOURCE_GOAL_AUDIT)
    manifest = load_json(SOURCE_MANIFEST)
    prompt_by_agent = prompt_records(prompts)
    gates = claim_gate_state(claims)
    findings = validate_manifest(manifest, prompt_by_agent, gates)
    reports = manifest.get("reports", []) if isinstance(manifest.get("reports"), list) else []
    report_count = len(reports)
    all_reports_valid = report_count > 0 and not findings
    claim_boundary_clean = (
        claims.get("summary", {}).get("claim_boundary_status") == "clean"
        and claims.get("summary", {}).get("finding_count") == 0
    )
    goal_complete = goal_audit.get("summary", {}).get("goal_complete") is True

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "research-agent result intake",
            "dispatching_parallel_agents": True,
            "launches_agents": False,
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "allows_compute": False,
            "integrates_reports": False,
        },
        "source_hashes": source_hashes(manifest, prompts),
        "required_report_fields": list(REQUIRED_REPORT_FIELDS),
        "allowed_report_statuses": sorted(ALLOWED_REPORT_STATUSES),
        "report_template_path": "docs/agent_reports/report_templates.json",
        "claim_gate_state": gates,
        "summary": {
            "manifest_status": manifest.get("status", "unknown"),
            "report_count": report_count,
            "finding_count": len(findings),
            "valid_report_count": report_count if not findings else 0,
            "all_reports_valid": all_reports_valid,
            "claim_boundary_status": claims.get("summary", {}).get(
                "claim_boundary_status"
            ),
            "claim_boundary_clean": claim_boundary_clean,
            "ready_for_human_review": all_reports_valid and claim_boundary_clean,
            "ready_for_integration": all_reports_valid and claim_boundary_clean,
            "integration_allowed": False,
            "completion_recommendation": (
                "goal_complete"
                if goal_complete
                else "keep_goal_active_until validated reports and proof gates move"
            ),
            "claim_boundary": (
                "No Seed Search; not natural-corpus proof; not production proof; "
                "not a compression claim; result intake does not launch agents."
            ),
        },
        "reports": reports,
        "findings": findings,
        "integration_gates": [
            "python scripts/generate_research_agent_prompts.py --check",
            "python scripts/generate_research_agent_result_intake.py --check",
            "python scripts/generate_claim_boundary_audit.py --check",
            "python scripts/generate_evidence_regimen.py --start-at research-agent-result-intake --check",
            "python scripts/doc_lint.py",
        ],
        "intake_rules": [
            "Every report must point to one generated prompt and its current SHA-256.",
            "Every report must list source artifacts, changed files, checks run, claim changes, promotion triggers, and stop rules checked.",
            "Unsupported natural-corpus, production, broad-compute, format-promotion, random-data, or universal-compressor claims are rejected while their generated gates remain false.",
            "An empty manifest is valid but not integration-ready.",
            "This artifact validates returns only; it does not launch agents, authorize compute, or integrate patches.",
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    prompts = load_json(SOURCE_PROMPTS)
    templates = build_report_templates(prompts)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_JSON.write_text(json.dumps(templates, indent=2) + "\n", encoding="utf-8")
    template_lines = [
        "# Research Agent Report Templates",
        "",
        f"Generated by `{GENERATED_BY}` from `docs/research_agent_prompts.json`.",
        "These templates are a No Seed Search convenience artifact. They launch no agents, perform no seed search, are not natural-corpus proof, are not production proof, and make no compression claim.",
        "",
        "## Summary",
        "",
        f"- Templates: `{templates['template_count']}`",
        "- JSON template path: `docs/agent_reports/report_templates.json`",
        "- Registration manifest: `docs/agent_reports/manifest.json`",
        "",
        "## Template Index",
        "",
        "| agent | group | report id template | prompt sha256 |",
        "| --- | --- | --- | --- |",
    ]
    for template in templates["templates"]:
        template_lines.append(
            f"| `{cell(template['agent_id'])}` | `{cell(template['parallel_group'])}` | "
            f"`{cell(template['report_id'])}` | `{cell(template['prompt_sha256'])}` |"
        )
    template_lines.extend(
        [
            "",
            "Copy one template object into `docs/agent_reports/manifest.json`, replace the placeholder report id and timestamp, then rerun `python scripts/generate_research_agent_result_intake.py --check`.",
        ]
    )
    TEMPLATE_MD.write_text("\n".join(template_lines) + "\n", encoding="utf-8")

    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Research Agent Result Intake",
        "",
        f"Generated by `{GENERATED_BY}` from `docs/agent_reports/manifest.json` and the current research-agent prompt pack.",
        "This is a dispatching-parallel-agents result-intake protocol. It is a No Seed Search artifact: it launches no agents, performs no seed search, is not natural-corpus proof, is not production proof, and makes no compression claim.",
        "",
        "## Summary",
        "",
        f"- Manifest status: `{summary['manifest_status']}`",
        f"- Reports: `{summary['report_count']}`",
        f"- Findings: `{summary['finding_count']}`",
        f"- Valid reports: `{summary['valid_report_count']}`",
        f"- All reports valid: `{summary['all_reports_valid']}`",
        f"- Claim boundary status: `{summary['claim_boundary_status']}`",
        f"- Claim boundary clean: `{summary['claim_boundary_clean']}`",
        f"- Ready for human review: `{summary['ready_for_human_review']}`",
        f"- Ready for integration: `{summary['ready_for_integration']}`",
        f"- Integration allowed: `{summary['integration_allowed']}`",
        f"- Completion recommendation: `{summary['completion_recommendation']}`",
        "",
        "## Required Report Schema",
        "",
        f"Template source: `{payload['report_template_path']}`",
        "",
        "| field | required |",
        "| --- | --- |",
    ]
    for field in payload["required_report_fields"]:
        lines.append(f"| `{field}` | `true` |")

    lines.extend(
        [
            "",
            "Allowed status values: "
            + ", ".join(f"`{status}`" for status in payload["allowed_report_statuses"])
            + ".",
            "",
            "## Intake Rules",
            "",
        ]
    )
    for rule in payload["intake_rules"]:
        lines.append(f"- {rule}")

    lines.extend(["", "## Current Reports", ""])
    if payload["reports"]:
        lines.extend(
            [
                "| report | agent | group | status | changed files | checks |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for report in payload["reports"]:
            lines.append(
                f"| `{cell(report.get('report_id', '<missing>'))}` | "
                f"`{cell(report.get('agent_id', '<missing>'))}` | "
                f"`{cell(report.get('parallel_group', '<missing>'))}` | "
                f"`{cell(report.get('status', '<missing>'))}` | "
                f"{len(report.get('changed_files', []))} | "
                f"{len(report.get('verification_commands', []))} |"
            )
    else:
        lines.append("- None. The result inbox is intentionally empty.")

    lines.extend(["", "## Findings", ""])
    if payload["findings"]:
        lines.extend(
            [
                "| report | rule | detail |",
                "| --- | --- | --- |",
            ]
        )
        for finding in payload["findings"]:
            lines.append(
                f"| `{cell(finding['report_id'])}` | `{cell(finding['rule'])}` | "
                f"{cell(finding['detail'])} |"
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Integration Gates",
            "",
        ]
    )
    for gate in payload["integration_gates"]:
        lines.append(f"- `{gate}`")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this intake report to the current prompt pack, goal-completion audit, manifest, and prompt files. Claim gates are read from the claim-boundary audit without hash-pinning it here so the final audit can scan this document without a generated-hash cycle.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research agent result-intake files are missing")
    if not TEMPLATE_JSON.exists() or not TEMPLATE_MD.exists():
        raise SystemExit("generated research agent report template files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_agent_result_intake.json has wrong generated_by marker")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_agent_result_intake.json is stale; regenerate it")
    if payload.get("source_hashes") != build_report().get("source_hashes"):
        raise SystemExit("research_agent_result_intake.json source hashes are stale")
    templates = load_json(TEMPLATE_JSON)
    expected_templates = stable_projection(build_report_templates(load_json(SOURCE_PROMPTS)))
    if stable_projection(templates) != expected_templates:
        raise SystemExit("research agent report templates are stale; regenerate them")
    if templates.get("template_count") != len(templates.get("templates", [])):
        raise SystemExit("research agent report template count is stale")
    expected_agents = {
        prompt["agent_id"] for prompt in load_json(SOURCE_PROMPTS).get("agent_prompts", [])
    }
    actual_agents = {template["agent_id"] for template in templates.get("templates", [])}
    if actual_agents != expected_agents:
        raise SystemExit("research agent report templates do not cover every prompt")
    if payload["summary"]["finding_count"] != len(payload["findings"]):
        raise SystemExit("research agent result-intake finding count is stale")
    if payload["summary"]["report_count"] != len(payload["reports"]):
        raise SystemExit("research agent result-intake report count is stale")
    if payload["summary"]["report_count"] == 0:
        if payload["summary"]["ready_for_integration"] is not False:
            raise SystemExit("empty result inbox cannot be integration-ready")
        if payload["summary"]["integration_allowed"] is not False:
            raise SystemExit("empty result inbox cannot allow integration")
    scope = payload.get("scope", {})
    for field in (
        "launches_agents",
        "performs_seed_search",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "is_production_proof",
        "allows_compute",
        "integrates_reports",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"research agent result intake scope field must be false: {field}")
    for field in REQUIRED_REPORT_FIELDS:
        if field not in payload.get("required_report_fields", []):
            raise SystemExit(f"research agent result intake schema missing field: {field}")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Research Agent Result Intake",
        "dispatching-parallel-agents result-intake protocol",
        "Required Report Schema",
        "Intake Rules",
        "Current Reports",
        "Integration Gates",
        "source_hashes",
        "Template source",
        "No Seed Search",
        "not natural-corpus proof",
        "not production proof",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_AGENT_RESULT_INTAKE.md missing phrase: {phrase}")
    template_text = TEMPLATE_MD.read_text(encoding="utf-8")
    for phrase in (
        "Research Agent Report Templates",
        "No Seed Search",
        "not natural-corpus proof",
        "not production proof",
        "docs/agent_reports/report_templates.json",
        "docs/agent_reports/manifest.json",
    ):
        if phrase not in template_text:
            raise SystemExit(f"REPORT_TEMPLATES.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated research-agent result-intake files",
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
