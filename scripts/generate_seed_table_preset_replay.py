#!/usr/bin/env python3
"""Generate a bounded seed-table preset replay artifact.

This replay tests the current top mechanism lane under a stricter
leave-corpus-out rule on a tiny predeclared set of structured corpora and
controls. It reuses the bounded seed-table preset machinery and performs no
broad seed search, no depth-3/depth-4 search, and no format promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_seed_table_preset_probe as preset_probe


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "seed_table_preset_replay.json"
REPORT_MD = DOCS / "SEED_TABLE_PRESET_REPLAY.md"
GENERATED_BY = "scripts/generate_seed_table_preset_replay.py"

SOURCE_PATHS = {
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "seed_table_preset_probe_generator_sha256": ROOT
    / "scripts"
    / "generate_seed_table_preset_probe.py",
    "corpus_matrix_sha256": DOCS / "corpus_matrix.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
}

REPLAY_CASES = [
    {
        "name": "yaml-leaveout-replay",
        "corpus": "yaml",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "configuration-yaml",
        "paired_with": None,
    },
    {
        "name": "ini-leaveout-replay",
        "corpus": "ini",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "configuration-ini",
        "paired_with": None,
    },
    {
        "name": "python-like-leaveout-replay",
        "corpus": "python-like",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "source-python-like",
        "paired_with": None,
    },
    {
        "name": "markdown-leaveout-replay",
        "corpus": "markdown",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "prose-markdown",
        "paired_with": None,
    },
    {
        "name": "log-leaveout-replay",
        "corpus": "log",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "record-log",
        "paired_with": None,
    },
    {
        "name": "fasta-leaveout-replay",
        "corpus": "fasta",
        "role": "ordinary",
        "control_kind": "ordinary-structured",
        "independence_group": "sequence-fasta",
        "paired_with": None,
    },
    {
        "name": "shadow-json-control-replay",
        "corpus": "shadow-json",
        "role": "control",
        "control_kind": "paired-shadow-control",
        "independence_group": "shadow-json",
        "paired_with": "json",
    },
    {
        "name": "binary-tlv-control-replay",
        "corpus": "binary-tlv",
        "role": "control",
        "control_kind": "binary-control",
        "independence_group": "binary-tlv",
        "paired_with": None,
    },
    {
        "name": "binary-varint-control-replay",
        "corpus": "binary-varint",
        "role": "control",
        "control_kind": "binary-control",
        "independence_group": "binary-varint",
        "paired_with": None,
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def replay_manifest() -> dict[str, Any]:
    return {
        "preset_name": "canonical-table-v0-leave-corpus-out-replay",
        "scope": "bounded seed-table preset replay",
        "not_tlmr_format_support": True,
        "not_natural_corpus_proof": True,
        "max_seed_len": preset_probe.MAX_SEED_LEN,
        "table_entry_count": preset_probe.TABLE_ENTRY_COUNT,
        "span_lens": list(preset_probe.SPAN_LENS),
        "span_step": preset_probe.SPAN_STEP,
        "ordinary_replay_case_count": sum(
            1 for row in REPLAY_CASES if row["role"] == "ordinary"
        ),
        "control_replay_case_count": sum(
            1 for row in REPLAY_CASES if row["role"] == "control"
        ),
        "ordinary_training_rule": "train on ordinary corpus-matrix rows excluding the target corpus",
        "control_training_rule": "train on all ordinary corpus-matrix rows",
        "promotion_rule": "ordinary negative groups >= 3, control negative groups == 0, and canonical selected spans beat sha256 baseline",
    }


def replay_manifest_hash() -> str:
    payload = json.dumps(replay_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def case_manifest_hash() -> str:
    payload = json.dumps(REPLAY_CASES, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def discovery_rows(exclude_corpus: str | None) -> list[dict[str, Any]]:
    return [
        row
        for row in preset_probe.corpus_manifest()
        if row["can_train"] and (exclude_corpus is None or row["corpus"] != exclude_corpus)
    ]


def replay_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": case["name"],
        "family": "corpus-matrix",
        "corpus": case["corpus"],
        "split": "bounded-replay",
        "role": case["role"],
        "control_kind": case["control_kind"],
        "paired_with": case["paired_with"],
        "independence_group": case["independence_group"],
        "can_train": False,
        "promotion_eligible": case["role"] == "ordinary",
    }


def analyze_case(row_id: int, case: dict[str, Any]) -> list[dict[str, Any]]:
    row = replay_row(case)
    exclude = case["corpus"] if case["role"] == "ordinary" else None
    canonical_entries = preset_probe.ranked_span_entries(discovery_rows(exclude))
    sha_entries = preset_probe.sha256_baseline_table()
    return [
        preset_probe.analyze_with_table(
            row_id,
            row,
            "leave-corpus-out-canonical"
            if case["role"] == "ordinary"
            else "canonical-control-replay",
            canonical_entries,
            0,
        ),
        preset_probe.analyze_with_table(
            row_id,
            row,
            "sha256-baseline",
            sha_entries,
            0,
        ),
    ]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)

    canonical_rows = [
        *by_mode["leave-corpus-out-canonical"],
        *by_mode["canonical-control-replay"],
    ]
    ordinary_negative_groups = {
        row["independence_group"]
        for row in by_mode["leave-corpus-out-canonical"]
        if row["delta_bytes"] < 0
    }
    control_negative_groups = {
        row["independence_group"]
        for row in by_mode["canonical-control-replay"]
        if row["delta_bytes"] < 0
    }
    sha_selected = sum(row["selected_span_count"] for row in by_mode["sha256-baseline"])
    canonical_selected = sum(row["selected_span_count"] for row in canonical_rows)
    sha_best_delta = min(row["delta_bytes"] for row in by_mode["sha256-baseline"])
    canonical_best = min(canonical_rows, key=lambda row: row["delta_bytes"])
    beats_sha = canonical_selected > sha_selected and canonical_best["delta_bytes"] < sha_best_delta
    promotion_candidate = (
        len(ordinary_negative_groups) >= 3
        and not control_negative_groups
        and canonical_selected > 0
        and beats_sha
    )
    return {
        "replay_status": "bounded_replay_complete",
        "row_count": len(rows),
        "case_count": len(REPLAY_CASES),
        "ordinary_case_count": sum(1 for row in REPLAY_CASES if row["role"] == "ordinary"),
        "control_case_count": sum(1 for row in REPLAY_CASES if row["role"] == "control"),
        "canonical_selected_spans": canonical_selected,
        "sha256_selected_spans": sha_selected,
        "canonical_negative_rows": sum(1 for row in canonical_rows if row["delta_bytes"] < 0),
        "ordinary_negative_groups": len(ordinary_negative_groups),
        "ordinary_negative_group_names": sorted(ordinary_negative_groups),
        "control_negative_groups": len(control_negative_groups),
        "control_negative_group_names": sorted(control_negative_groups),
        "best_canonical_case": canonical_best["name"],
        "best_canonical_delta_bytes": canonical_best["delta_bytes"],
        "beats_sha256_baseline": beats_sha,
        "promotion_candidate": promotion_candidate,
        "natural_corpus_proven": False,
        "format_promotion_allowed": False,
        "claim_boundary": (
            "No Seed Search; bounded preset replay only; not natural-corpus proof; "
            "not production proof; not .tlmr format support."
        ),
        "conclusion": (
            "Replay can reopen the seed-table lane only if unrelated ordinary "
            "negative groups appear while controls remain null. The artifact is "
            "evidence for mechanism triage, not a compression or format claim."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["delta_bytes"],
            -row["selected_span_count"],
            row["mode"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    parent = load_json(DOCS / "seed_table_preset_probe.json")
    if parent["summary"]["promotion_met"]:
        raise RuntimeError("parent seed-table probe unexpectedly promotes")
    rows: list[dict[str, Any]] = []
    for row_id, case in enumerate(REPLAY_CASES):
        rows.extend(analyze_case(row_id, case))
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "bounded seed-table preset replay",
            "performs_seed_search": False,
            "performs_preset_lookup": True,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
        },
        "source_hashes": source_hashes(),
        "replay_manifest_sha256": replay_manifest_hash(),
        "replay_manifest": replay_manifest(),
        "case_manifest_sha256": case_manifest_hash(),
        "case_manifest": REPLAY_CASES,
        "summary": summarize(rows),
        "top_rows": top_rows(rows),
        "rows": rows,
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Seed Table Preset Replay",
        "",
        f"Generated by `{GENERATED_BY}` from the current bounded seed-table preset probe.",
        "This is a No Seed Search replay artifact. It launches no agents, performs no broad seed search, is not natural-corpus proof, is not production proof, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Replay status: `{summary['replay_status']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Ordinary cases: `{summary['ordinary_case_count']}`",
        f"- Control cases: `{summary['control_case_count']}`",
        f"- Canonical selected spans: `{summary['canonical_selected_spans']}`",
        f"- SHA256 selected spans: `{summary['sha256_selected_spans']}`",
        f"- Canonical negative rows: `{summary['canonical_negative_rows']}`",
        f"- Ordinary negative groups: `{summary['ordinary_negative_groups']}`",
        f"- Control negative groups: `{summary['control_negative_groups']}`",
        f"- Best canonical case: `{summary['best_canonical_case']}` (`{summary['best_canonical_delta_bytes']}` bytes)",
        f"- Beats SHA256 baseline: `{summary['beats_sha256_baseline']}`",
        f"- Promotion candidate: `{summary['promotion_candidate']}`",
        f"- Natural corpus proven: `{summary['natural_corpus_proven']}`",
        "",
        summary["conclusion"],
        "",
        "## Replay Design",
        "",
        "- Ordinary rows use leave-corpus-out tables trained on other ordinary corpus-matrix rows.",
        "- Control rows use the same canonical table policy but cannot count toward promotion.",
        "- `sha256-baseline` rows remain the same-size random-trial control.",
        "- This artifact intentionally does not add preset metadata to `.tlmr`.",
        "",
        "## Top Rows",
        "",
        "| case | mode | kind | selected spans | delta bytes | exact decode | corrupt rejection |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in payload["top_rows"]:
        lines.append(
            f"| `{cell(row['name'])}` | `{cell(row['mode'])}` | "
            f"`{cell(row['control_kind'])}` | {row['selected_span_count']} | "
            f"{row['delta_bytes']} | `{row['exact_decode']}` | `{row['corrupt_rejection']}` |"
        )
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "- `ordinary_negative_groups >= 3`",
            "- `control_negative_groups == 0`",
            "- canonical selected spans are nonzero",
            "- canonical replay beats the SHA256 baseline",
            "- downstream proof matrices remain responsible for any natural-corpus or format promotion",
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this replay to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.append(f"- `replay_manifest_sha256`: `{payload['replay_manifest_sha256']}`")
    lines.append(f"- `case_manifest_sha256`: `{payload['case_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated seed table preset replay files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("seed_table_preset_replay.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("seed table preset replay source hashes are stale")
    if payload.get("replay_manifest_sha256") != replay_manifest_hash():
        raise SystemExit("seed table preset replay manifest hash is stale")
    if payload.get("case_manifest_sha256") != case_manifest_hash():
        raise SystemExit("seed table preset replay case manifest hash is stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("seed_table_preset_replay.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "allows_broad_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"seed table replay scope field must be false: {field}")
    if payload["summary"]["natural_corpus_proven"] is not False:
        raise SystemExit("seed table replay must not claim natural-corpus proof")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Seed Table Preset Replay",
        "No Seed Search",
        "not natural-corpus proof",
        "not `.tlmr` format support",
        "leave-corpus-out",
        "Promotion Gate",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"SEED_TABLE_PRESET_REPLAY.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated replay files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
