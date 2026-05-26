#!/usr/bin/env python3
"""Generate the external natural-corpus accession ledger.

This is the manifest-only gate before any natural-corpus compute. It validates
`corpora/external/manifest.json` for provenance, hashes, independence groups,
and paired controls, but it never reads corpus payload bytes unless entries are
present and referenced paths are already checked in.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SOURCE_MANIFEST = ROOT / "corpora" / "external" / "manifest.json"
REPORT_JSON = DOCS / "external_corpus_accession.json"
REPORT_MD = DOCS / "EXTERNAL_CORPUS_ACCESSION.md"
GENERATED_BY = "scripts/generate_external_corpus_accession.py"

SOURCE_PATHS = {
    "external_manifest_sha256": SOURCE_MANIFEST,
    "frozen_rank_source_candidates_sha256": DOCS / "frozen_rank_source_candidates.json",
    "natural_corpus_reopen_manifest_sha256": DOCS / "natural_corpus_reopen_manifest.json",
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
}

ALLOWED_FAMILIES = {
    "standards-protocol-text",
    "schema-and-config",
    "records-and-ledgers",
    "source-code",
}
CONTROL_KINDS = {
    "paired-shadow-control",
    "wrong-family-control",
    "binary-control",
    "random-control",
    "near-family-control",
}
ORDINARY_CONTROL_KIND = "ordinary-structured"
REQUIRED_FIELDS = {
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


def manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("corpora/external/manifest.json entries must be a list")
    return entries


def safe_relative_path(path_text: str) -> Path | None:
    path = Path(path_text)
    if path.is_absolute():
        return None
    if any(part == ".." for part in path.parts):
        return None
    if path.parts[:2] != ("corpora", "external"):
        return None
    if path == Path("corpora/external/manifest.json"):
        return None
    return ROOT / path


def validate_entry(row: dict[str, Any], ids: set[str]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    entry_id = str(row.get("entry_id", "<missing>"))
    missing = sorted(REQUIRED_FIELDS.difference(row))
    for field in missing:
        errors.append(
            {
                "entry_id": entry_id,
                "field": field,
                "error": "missing required field",
            }
        )
    if missing:
        return errors

    if entry_id in ids:
        errors.append({"entry_id": entry_id, "field": "entry_id", "error": "duplicate id"})
    ids.add(entry_id)

    if row["family_id"] not in ALLOWED_FAMILIES:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "family_id",
                "error": "unknown target family",
            }
        )
    if row["role"] not in {"ordinary", "control"}:
        errors.append({"entry_id": entry_id, "field": "role", "error": "invalid role"})
    if row["role"] == "ordinary" and row["control_kind"] != ORDINARY_CONTROL_KIND:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "control_kind",
                "error": "ordinary rows must use ordinary-structured",
            }
        )
    if row["role"] == "control" and row["control_kind"] not in CONTROL_KINDS:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "control_kind",
                "error": "control rows must use an allowed control kind",
            }
        )
    if row["role"] == "control" and not row["paired_with"]:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "paired_with",
                "error": "control rows must identify paired ordinary entry",
            }
        )
    if not row["license"] or str(row["license"]).lower() in {"unknown", "todo"}:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "license",
                "error": "license/provenance must be explicit",
            }
        )
    if not row["source_uri"] or str(row["source_uri"]).lower() in {"unknown", "todo"}:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "source_uri",
                "error": "source URI or local provenance must be explicit",
            }
        )
    if not isinstance(row["bytes"], int) or row["bytes"] <= 0:
        errors.append({"entry_id": entry_id, "field": "bytes", "error": "bytes must be positive"})
    if not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "sha256",
                "error": "sha256 must be a 64-character hex digest",
            }
        )
    else:
        try:
            bytes.fromhex(row["sha256"])
        except ValueError:
            errors.append(
                {
                    "entry_id": entry_id,
                    "field": "sha256",
                    "error": "sha256 contains non-hex characters",
                }
            )

    full_path = safe_relative_path(str(row["path"]))
    if full_path is None:
        errors.append(
            {
                "entry_id": entry_id,
                "field": "path",
                "error": "path must be repository-relative under corpora/external/ and may not contain ..",
            }
        )
    elif not full_path.exists():
        errors.append(
            {
                "entry_id": entry_id,
                "field": "path",
                "error": "referenced corpus file does not exist",
            }
        )
    else:
        data = full_path.read_bytes()
        if len(data) != row["bytes"]:
            errors.append(
                {
                    "entry_id": entry_id,
                    "field": "bytes",
                    "error": "declared byte count does not match file",
                }
            )
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            errors.append(
                {
                    "entry_id": entry_id,
                    "field": "sha256",
                    "error": "declared sha256 does not match file",
                }
            )
    return errors


def validate_pairing(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    by_id = {str(row.get("entry_id")): row for row in entries if "entry_id" in row}
    controls_by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ordinary_ids = {
        str(row.get("entry_id"))
        for row in entries
        if row.get("role") == "ordinary"
    }
    for row in entries:
        if row.get("role") == "control":
            paired = str(row.get("paired_with", ""))
            controls_by_pair[paired].append(row)
            if paired not in ordinary_ids:
                errors.append(
                    {
                        "entry_id": str(row.get("entry_id", "<missing>")),
                        "field": "paired_with",
                        "error": "paired ordinary entry is missing",
                    }
                )
    for ordinary_id in sorted(ordinary_ids):
        control_kinds = {
            row.get("control_kind") for row in controls_by_pair.get(ordinary_id, [])
        }
        if "paired-shadow-control" not in control_kinds:
            errors.append(
                {
                    "entry_id": ordinary_id,
                    "field": "paired_controls",
                    "error": "ordinary row needs a paired-shadow-control",
                }
            )
        if not ({"binary-control", "random-control"} & control_kinds):
            errors.append(
                {
                    "entry_id": ordinary_id,
                    "field": "paired_controls",
                    "error": "ordinary row needs binary or random null control",
                }
            )
        if "wrong-family-control" not in control_kinds:
            errors.append(
                {
                    "entry_id": ordinary_id,
                    "field": "paired_controls",
                    "error": "ordinary row needs a wrong-family-control",
                }
            )
        if by_id[ordinary_id].get("independence_group") in {"", None}:
            errors.append(
                {
                    "entry_id": ordinary_id,
                    "field": "independence_group",
                    "error": "ordinary row needs an independence group",
                }
            )
    return errors


def build_report() -> dict[str, Any]:
    manifest = load_json(SOURCE_MANIFEST)
    source_candidates = load_json(DOCS / "frozen_rank_source_candidates.json")
    reopen = load_json(DOCS / "natural_corpus_reopen_manifest.json")
    proof = load_json(DOCS / "natural_corpus_proof_matrix.json")
    search = load_json(DOCS / "search_frontier_gate.json")
    entries = manifest_entries(manifest)
    ids: set[str] = set()
    validation_errors = [
        error
        for row in entries
        for error in validate_entry(row, ids)
    ]
    if not validation_errors:
        validation_errors.extend(validate_pairing(entries))
    role_counts = Counter(str(row.get("role", "<missing>")) for row in entries)
    family_counts = Counter(str(row.get("family_id", "<missing>")) for row in entries)
    control_counts = Counter(str(row.get("control_kind", "<missing>")) for row in entries)
    ordinary_count = role_counts.get("ordinary", 0)
    control_count = role_counts.get("control", 0)
    required_rows_before_replay = summary(source_candidates)[
        "required_external_manifest_row_count"
    ]
    paired_ready = ordinary_count > 0 and not validation_errors
    manifest_complete = (
        paired_ready
        and len(entries) >= required_rows_before_replay
        and len({row.get("family_id") for row in entries if row.get("family_id")})
        >= len(ALLOWED_FAMILIES)
    )
    accession_status = (
        "empty_manifest_waiting_for_external_corpora"
        if not entries
        else "valid_manifest_only_ready_for_human_review"
        if manifest_complete
        else "valid_partial_manifest_only_needs_more_families"
        if paired_ready
        else "invalid_manifest_requires_fix"
    )
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "external natural-corpus accession ledger",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "overrides_search_frontier_gate": False,
            "allows_compute": False,
        },
        "source_hashes": source_hashes(),
        "schema": {
            "source_manifest": "corpora/external/manifest.json",
            "required_fields": sorted(REQUIRED_FIELDS),
            "allowed_families": sorted(ALLOWED_FAMILIES),
            "allowed_control_kinds": sorted(CONTROL_KINDS | {ORDINARY_CONTROL_KIND}),
            "pairing_rule": "Every ordinary row needs at least one paired-shadow-control, one wrong-family-control, and one binary or random null control before any prefix audit.",
        },
        "summary": {
            "accession_status": accession_status,
            "source_manifest_status": manifest.get("status", "unknown"),
            "entry_count": len(entries),
            "ordinary_entry_count": ordinary_count,
            "control_entry_count": control_count,
            "independence_group_count": len(
                {row.get("independence_group") for row in entries if row.get("independence_group")}
            ),
            "family_count": len({row.get("family_id") for row in entries if row.get("family_id")}),
            "validation_error_count": len(validation_errors),
            "paired_manifest_ready": paired_ready,
            "manifest_complete": manifest_complete,
            "frozen_rank_source_candidate_status": summary(source_candidates)[
                "candidate_status"
            ],
            "frozen_rank_required_manifest_rows_before_replay": required_rows_before_replay,
            "frozen_rank_source_candidates_ready_for_replay": summary(
                source_candidates
            )["ready_for_replay_count"],
            "compute_allowed": False,
            "natural_corpus_proven": summary(proof)["natural_corpus_proven"],
            "first_allowed_stage": summary(reopen)["first_allowed_stage"],
            "reopen_first_allowed_stage": summary(reopen)["first_allowed_stage"],
            "broad_depth_search_allowed": summary(search)["broad_depth_search_allowed"],
            "next_allowed_action": (
                "add external ordinary corpora with explicit paired controls"
                if not entries
                else "fix accession validation errors"
                if validation_errors
                else "add remaining frozen-rank families and required controls before any prefix audit"
                if not manifest_complete
                else "human review may decide whether prefix-audit stage should be proposed"
            ),
            "claim_boundary": (
                "No Seed Search; accession validation only; not a compression claim; "
                "not natural-corpus proof; does not override SEARCH_FRONTIER_GATE."
            ),
        },
        "role_counts": dict(sorted(role_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "control_kind_counts": dict(sorted(control_counts.items())),
        "validation_errors": validation_errors,
        "entries": entries,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    schema = payload["schema"]
    lines = [
        "# External Corpus Accession",
        "",
        f"Generated by `{GENERATED_BY}` from `corpora/external/manifest.json`, frozen-rank source candidates, and natural-corpus gate ledgers.",
        "This is a No Seed Search accession validator. It launches no agents, performs no compression, is not natural-corpus proof, and does not override `SEARCH_FRONTIER_GATE`.",
        "",
        "## Summary",
        "",
        f"- Accession status: `{summary_payload['accession_status']}`",
        f"- Source manifest status: `{summary_payload['source_manifest_status']}`",
        f"- Entries: `{summary_payload['entry_count']}`",
        f"- Ordinary entries: `{summary_payload['ordinary_entry_count']}`",
        f"- Control entries: `{summary_payload['control_entry_count']}`",
        f"- Independence groups: `{summary_payload['independence_group_count']}`",
        f"- Families: `{summary_payload['family_count']}`",
        f"- Validation errors: `{summary_payload['validation_error_count']}`",
        f"- Paired manifest ready: `{summary_payload['paired_manifest_ready']}`",
        f"- Manifest complete: `{summary_payload['manifest_complete']}`",
        f"- Frozen rank source candidate status: `{summary_payload['frozen_rank_source_candidate_status']}`",
        f"- Frozen rank required manifest rows before replay: `{summary_payload['frozen_rank_required_manifest_rows_before_replay']}`",
        f"- Frozen rank source candidates ready for replay: `{summary_payload['frozen_rank_source_candidates_ready_for_replay']}`",
        f"- Compute allowed: `{summary_payload['compute_allowed']}`",
        f"- First allowed stage: `{summary_payload['first_allowed_stage']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Next allowed action: `{summary_payload['next_allowed_action']}`",
        "",
        (
            "The current external corpus manifest is intentionally empty. This keeps the natural-corpus path honest: future corpus additions must pass provenance, hash, independence-group, and paired-control validation before any prefix audit or seed search is considered."
            if summary_payload["entry_count"] == 0
            else "The current external corpus manifest has validated manifest-only entries. This is accession evidence only: it records provenance, hashes, independence groups, and controls, but it does not run prefix audit, seed search, compression, or natural-corpus promotion."
        ),
        "",
        "## Required Schema",
        "",
        f"- Source manifest: `{schema['source_manifest']}`",
        f"- Required fields: {', '.join(f'`{field}`' for field in schema['required_fields'])}",
        f"- Allowed families: {', '.join(f'`{family}`' for family in schema['allowed_families'])}",
        f"- Allowed control kinds: {', '.join(f'`{kind}`' for kind in schema['allowed_control_kinds'])}",
        f"- Pairing rule: {schema['pairing_rule']}",
        "",
        "## Validation Errors",
        "",
    ]
    if payload["validation_errors"]:
        lines.extend(
            [
                "| entry | field | error |",
                "| --- | --- | --- |",
            ]
        )
        for error in payload["validation_errors"]:
            lines.append(
                f"| `{cell(error['entry_id'])}` | `{cell(error['field'])}` | {cell(error['error'])} |"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Manifest Entries", ""])
    if payload["entries"]:
        lines.extend(
            [
                "| entry | role | family | control kind | pair | bytes |",
                "| --- | --- | --- | --- | --- | ---: |",
            ]
        )
        for row in payload["entries"]:
            lines.append(
                f"| `{cell(row['entry_id'])}` | `{cell(row['role'])}` | `{cell(row['family_id'])}` | `{cell(row['control_kind'])}` | `{cell(row['paired_with'])}` | {cell(row['bytes'])} |"
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Accession Rules",
            "",
            "- Add corpus bytes only after license/provenance and source URI are explicit.",
            "- Store SHA-256 and byte count in the manifest before any generated prefix audit.",
            "- Pair every ordinary row with at least one vocabulary-disjoint shadow control and one binary or random null control.",
            "- Keep manifest-only work separate from canonical corpus matrices until a human accepts the regeneration budget.",
            "- Do not claim natural-corpus viability from this ledger; it is only the accession gate.",
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this accession ledger to exact upstream files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated external corpus accession files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("external_corpus_accession.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("external corpus accession source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("external_corpus_accession.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "overrides_search_frontier_gate",
        "allows_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"external corpus accession scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["natural_corpus_proven"]:
        raise SystemExit("external corpus accession cannot claim natural-corpus proof")
    if summary_payload["broad_depth_search_allowed"]:
        raise SystemExit("external corpus accession cannot allow broad depth search")
    if summary_payload["compute_allowed"]:
        raise SystemExit("external corpus accession cannot allow compute")
    if summary_payload["manifest_complete"] and not summary_payload["paired_manifest_ready"]:
        raise SystemExit("external corpus accession manifest cannot be complete unless paired-ready")
    if not payload["entries"] and (
        summary_payload["manifest_complete"]
        or summary_payload["compute_allowed"]
        or summary_payload["paired_manifest_ready"]
    ):
        raise SystemExit("empty external corpus accession manifest cannot be ready")
    if summary_payload["validation_error_count"] != len(payload["validation_errors"]):
        raise SystemExit("external corpus accession validation error count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "External Corpus Accession",
        "No Seed Search",
        "not natural-corpus proof",
        "SEARCH_FRONTIER_GATE",
        "Required Schema",
        "Validation Errors",
        "Manifest Entries",
        "Accession Rules",
        "manifest",
        "Compute allowed",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"EXTERNAL_CORPUS_ACCESSION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated external corpus accession ledger"
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
