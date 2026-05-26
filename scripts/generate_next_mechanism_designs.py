#!/usr/bin/env python3
"""Generate pre-registered next mechanism designs.

The current closure audit says all bounded mechanism lanes are closed, blocked,
or maintenance-only. This artifact does not run compute. It turns the next
whitepaper-level move into falsifiable design briefs: new byte-to-seed
mechanisms or stronger reversible frontier generators that could be implemented
later without bypassing current gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "next_mechanism_designs.json"
REPORT_MD = DOCS / "NEXT_MECHANISM_DESIGNS.md"
GENERATED_BY = "scripts/generate_next_mechanism_designs.py"

SOURCE_PATHS = {
    "whitepaper_sha256": DOCS / "Telomere Whitepaper V2.md",
    "mechanism_closure_audit_sha256": DOCS / "mechanism_closure_audit.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "seed_table_fasta_ablation_sha256": DOCS / "seed_table_fasta_ablation.json",
    "next_mechanism_designs_generator_sha256": ROOT
    / "scripts"
    / "generate_next_mechanism_designs.py",
}

VALID_STATUSES = {"pre-registered-design", "blocked-by-evidence"}

DESIGNS = [
    {
        "rank": 1,
        "design_id": "frozen-rank-coded-span-generator",
        "title": "Frozen rank-coded span generator",
        "status": "pre-registered-design",
        "mechanism_family": "byte-to-seed-generator",
        "whitepaper_link": "table lookup from a seed table, but rank-coded and external-provenance first",
        "core_idea": (
            "Use seed bytes to index a frozen external span model: phrase ranks, "
            "byte-pair paths, and n-gram continuation ranks trained only from "
            "public external corpora before any Telomere held-out scan."
        ),
        "why_materially_new": (
            "It attacks cryptographic-uniformity directly by making seed expansion "
            "rank-coded and corpus-shaped while preserving decoder-public "
            "reproducibility."
        ),
        "first_artifact": "docs/FROZEN_RANK_CODED_SPAN_GENERATOR.md",
        "implementation_slice": (
            "Create an external-source manifest, freeze rank tables/checksums, and "
            "run a tiny no-leakage replay only after provenance is complete."
        ),
        "control_suite": [
            "paired shadow vocabulary",
            "same-size random rank table",
            "wrong-family rank model",
            "generic token dictionary",
            "binary and high-entropy controls",
        ],
        "falsification_test": (
            "Held-out gains are explainable by equivalent random-trial scaling, "
            "flat dictionary lookup, or wrong-family/shadow controls."
        ),
        "promotion_trigger": (
            "At least three unrelated ordinary held-out groups produce selected "
            "exact spans and full-stream negative rows after selector/version "
            "metadata, while paired shadow, random, wrong-family, binary, and "
            "high-entropy controls stay non-negative."
        ),
        "stop_rule": (
            "Stop if any control goes negative, if ordinary wins stay below three "
            "groups, or if the rank table cannot be frozen from external provenance."
        ),
        "blocked_by": ["external-corpus-accession", "control-separation"],
        "compute_budget": "manifest-only now; later bounded replay only, no raw-depth escalation",
    },
    {
        "rank": 2,
        "design_id": "reversible-boundary-chimera-frontier",
        "title": "Reversible boundary/chimera span frontier",
        "status": "pre-registered-design",
        "mechanism_family": "reversible-frontier-generator",
        "whitepaper_link": "stronger frontier generator before exact seed-span search",
        "core_idea": (
            "Replace fixed/phase span candidates with reversible span proposals from "
            "grammar delimiters, rolling-min content-defined boundaries, repeated "
            "anchors, and safe chimera combinations of adjacent structural regions."
        ),
        "why_materially_new": (
            "It changes which spans become eligible before exact matching, measuring "
            "frontier lift per scanned span instead of spending broader raw depth."
        ),
        "first_artifact": "docs/BOUNDARY_CHIMERA_FRONTIER_PROBE.md",
        "implementation_slice": (
            "Implement a deterministic boundary manifest and compare fixed-phase, "
            "random-boundary, delimiter-shuffled, and content-defined frontiers on "
            "the same shallow generator budget."
        ),
        "control_suite": [
            "random boundary schedule with same length histogram",
            "phase-shifted boundaries",
            "delimiter-shuffled corpora",
            "binary controls",
            "high-entropy controls",
        ],
        "falsification_test": (
            "Held-out max prefix stays at 4, selected spans stay zero, or boundary "
            "controls produce comparable prefix/exact density."
        ),
        "promotion_trigger": (
            "With the same shallow generator budget, held-out ordinary corpora reach "
            "prefix>=5 or exact selected spans that fixed-phase and random-boundary "
            "controls do not produce."
        ),
        "stop_rule": (
            "Stop if frontier lift is not better than random-boundary controls or "
            "requires raw-depth escalation."
        ),
        "blocked_by": ["search-frontier-gate", "boundary-control-separation"],
        "compute_budget": "design and manifest first; shallow replay only after controls are frozen",
    },
    {
        "rank": 3,
        "design_id": "decoder-public-grammar-expander",
        "title": "Decoder-public grammar expander",
        "status": "pre-registered-design",
        "mechanism_family": "byte-to-seed-generator",
        "whitepaper_link": "Lotus preset / seed table, but generator-first instead of table-first",
        "core_idea": (
            "Replace uniform hash expansion with a versioned public generator whose "
            "seed space emits grammar productions, record delimiters, and common "
            "byte motifs for a declared family. The file stores only seed-span "
            "records plus the public preset/version."
        ),
        "why_materially_new": (
            "It changes the seed-to-byte distribution itself instead of searching "
            "deeper through BLAKE3/SHA-256 or replaying fixed observed spans."
        ),
        "first_artifact": "docs/GRAMMAR_EXPANDER_DESIGN_PROBE.md",
        "implementation_slice": (
            "Implement a tiny decoder-public generator for one grammar family, a "
            "v2 experimental preset id, and a replay-only probe over held-out and "
            "shadow corpora."
        ),
        "control_suite": [
            "same-length shadow vocabulary",
            "binary TLV and varint controls",
            "wrong-family grammar preset",
            "random-trial-equivalent uniform expander",
            "project-token scrubbed held-outs",
        ],
        "falsification_test": (
            "Header/token wins vanish after project-token scrubbing or paired "
            "shadow corpora shrink comparably."
        ),
        "promotion_trigger": (
            "At least three unrelated ordinary held-out groups produce selected "
            "exact spans and full-stream negative delta after preset metadata; "
            "all shadow/binary/wrong-family controls remain non-negative."
        ),
        "stop_rule": (
            "Stop if wins are dominated by project names, headers, fixed labels, "
            "or if the generator behaves like a static dictionary with the same "
            "control failures already observed."
        ),
        "blocked_by": ["external-corpus-provenance", "control-separation"],
        "compute_budget": "design-only now; later probe capped to frozen held-out matrix, no raw-depth escalation",
    },
    {
        "rank": 4,
        "design_id": "typed-record-frontier-generator",
        "title": "Typed record frontier generator",
        "status": "pre-registered-design",
        "mechanism_family": "reversible-frontier-generator",
        "whitepaper_link": "stronger reversible frontier before exact seed-span search",
        "core_idea": (
            "Convert structured records into a canonical typed stream where seed "
            "spans target field tags, separators, lengths, and low-entropy value "
            "channels separately, then recompose bytes exactly."
        ),
        "why_materially_new": (
            "It attempts to move natural data from prefix-4 steering evidence to "
            "prefix>=6 or selected exact spans by changing the reversible frontier, "
            "not by adding raw depth."
        ),
        "first_artifact": "docs/TYPED_RECORD_FRONTIER_PROBE.md",
        "implementation_slice": (
            "Prototype a decode-verified typed-record normalizer for JSONL/CSV/log "
            "fixtures with explicit metadata accounting and wrong-schema controls."
        ),
        "control_suite": [
            "same-schema shadow values",
            "wrong-schema replay",
            "field-order permutation",
            "binary fixed-record control",
            "identity transform baseline",
        ],
        "falsification_test": (
            "Any negative delta disappears after field names are shadowed or when "
            "wrong-schema controls select comparable spans."
        ),
        "promotion_trigger": (
            "Held-out ordinary rows reach prefix>=6 or selected exact spans after "
            "all transform metadata, with controls and wrong-schema rows null."
        ),
        "stop_rule": (
            "Do not add transform metadata to .tlmr if the frontier only moves "
            "prefix-4 near misses or requires per-file schema training."
        ),
        "blocked_by": ["search-frontier-gate", "transform-control-separation"],
        "compute_budget": "manifest and tiny deterministic fixtures first; no depth-3/depth-4 escalation",
    },
    {
        "rank": 5,
        "design_id": "motif-prng-expander-family",
        "title": "Motif-biased PRNG expander family",
        "status": "pre-registered-design",
        "mechanism_family": "byte-to-seed-generator",
        "whitepaper_link": "search farther by arity, but through a non-uniform public expander",
        "core_idea": (
            "Define a small family of deterministic non-cryptographic expanders "
            "whose seeds emit byte motifs, delimiters, counters, and repeated "
            "micro-structures before falling back to uniform bytes."
        ),
        "why_materially_new": (
            "It tests whether a decoder-public generative prior can beat the "
            "equivalent random-trial multiplier without storing a file-local table."
        ),
        "first_artifact": "docs/MOTIF_PRNG_EXPANDER_PROBE.md",
        "implementation_slice": (
            "Implement three frozen motif expanders with preset ids and compare "
            "against an equal-number-of-draws SHA-256 baseline on held-out corpora."
        ),
        "control_suite": [
            "equivalent random-trial SHA-256 baseline",
            "binary controls",
            "shadow vocabulary controls",
            "wrong-motif-family controls",
            "salt-count ablation",
        ],
        "falsification_test": (
            "Selected spans scale no better than the random-trial multiplier or "
            "controls select comparable motifs."
        ),
        "promotion_trigger": (
            "The motif family produces full-stream negative rows in at least three "
            "ordinary groups, zero control negative groups, and beats equivalent "
            "random draws."
        ),
        "stop_rule": (
            "Stop if gains appear only from extra trials, fixed headers, or "
            "project-specific strings."
        ),
        "blocked_by": ["expander-salt-null-result", "control-separation"],
        "compute_budget": "predeclared motif set only; seed depth unchanged",
    },
    {
        "rank": 6,
        "design_id": "external-public-corpus-distillation",
        "title": "External public-corpus preset distillation",
        "status": "pre-registered-design",
        "mechanism_family": "public-preset-distillation",
        "whitepaper_link": "table lookup from a seed table, but with external provenance and leakage control",
        "core_idea": (
            "Distill public corpus spans into a decoder-public preset using only "
            "externally accessioned data, then test on repository-local held-outs "
            "with strict family and project-token exclusion."
        ),
        "why_materially_new": (
            "It addresses the previous public-preset failure mode directly: project "
            "token leakage and paired-shadow controls."
        ),
        "first_artifact": "docs/EXTERNAL_PRESET_DISTILLATION_MANIFEST.md",
        "implementation_slice": (
            "Create an accession manifest, freeze source corpora/checksums, remove "
            "project tokens, and generate a no-compute preset manifest before any "
            "compression probe."
        ),
        "control_suite": [
            "leave-family-out",
            "no-project-token",
            "paired shadow controls",
            "external/internal provenance split",
            "random table of equal size",
        ],
        "falsification_test": (
            "Leave-family-out plus project-token removal removes ordinary negative "
            "groups, or paired controls remain negative."
        ),
        "promotion_trigger": (
            "External-only preset produces at least three ordinary held-out negative "
            "groups after project-token removal and zero paired-control negatives."
        ),
        "stop_rule": (
            "Do not build or ship a preset registry until accession and paired-control "
            "gates are green."
        ),
        "blocked_by": ["external-corpus-accession", "public-preset-controls"],
        "compute_budget": "manifest-only until external corpus accession is complete",
    },
    {
        "rank": 7,
        "design_id": "constraint-synthesis-seed-compiler",
        "title": "Constraint-synthesis seed compiler",
        "status": "pre-registered-design",
        "mechanism_family": "byte-to-seed-compiler",
        "whitepaper_link": "arity lets seeds name structured higher-order blocks",
        "core_idea": (
            "Let a seed name a small deterministic constraint program that emits "
            "length fields, counters, checksums, delimiters, and payload templates, "
            "then verifies exact bytes before record emission."
        ),
        "why_materially_new": (
            "It searches a compact program space over structured blocks rather than "
            "raw byte strings, potentially creating longer exact spans without "
            "broad raw depth."
        ),
        "first_artifact": "docs/CONSTRAINT_SYNTHESIS_COMPILER_DESIGN.md",
        "implementation_slice": (
            "Specify a tiny decoder-public instruction set, golden vectors, and "
            "a verifier that rejects any non-exact synthesized span."
        ),
        "control_suite": [
            "random payload with valid lengths",
            "shuffled field order",
            "checksum-mismatched controls",
            "wrong instruction-family controls",
            "literal-only baseline",
        ],
        "falsification_test": (
            "The instruction set needs too much metadata, fails exact decode, or "
            "finds matches only in synthetic controls."
        ),
        "promotion_trigger": (
            "Golden vectors, corrupt rejection, and at least two unrelated ordinary "
            "fixture families produce later selected spans after all instruction "
            "metadata is charged."
        ),
        "stop_rule": (
            "Keep it out of .tlmr until instruction metadata, compatibility, and "
            "control gates are explicitly proven."
        ),
        "blocked_by": ["format-promotion-boundary", "golden-vector-design"],
        "compute_budget": "spec/golden-vector only before any corpus probe",
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


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def design_manifest_hash() -> str:
    payload = json.dumps(DESIGNS, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_report() -> dict[str, Any]:
    closure = summary(load_json(DOCS / "mechanism_closure_audit.json"))
    search = summary(load_json(DOCS / "search_frontier_gate.json"))
    if closure.get("ready_compute_lane_count") != 0:
        raise RuntimeError("next mechanism designs require closed current mechanism lanes")
    if search.get("broad_depth_search_allowed") is not False:
        raise RuntimeError("next mechanism designs assume broad raw search remains closed")
    status_counts = Counter(row["status"] for row in DESIGNS)
    top_design = DESIGNS[0]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "pre-registered next mechanism designs",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
            "ready_compute_lane_count": 0,
        },
        "source_hashes": source_hashes(),
        "design_manifest_sha256": design_manifest_hash(),
        "summary": {
            "design_status": "pre_registered_designs_only",
            "design_count": len(DESIGNS),
            "status_counts": dict(sorted(status_counts.items())),
            "pre_registered_design_count": status_counts["pre-registered-design"],
            "ready_compute_count": 0,
            "top_design_id": top_design["design_id"],
            "top_design_status": top_design["status"],
            "closure_status": closure.get("closure_status"),
            "closure_ready_compute_lane_count": closure.get("ready_compute_lane_count"),
            "closure_top_blocked_lane": closure.get("top_blocked_lane"),
            "broad_depth_search_allowed": search.get("broad_depth_search_allowed", False),
            "format_promotion_allowed": search.get("format_promotion_allowed", False),
            "natural_corpus_proven": False,
            "production_proven": False,
            "allowed_next_work": (
                "design review, manifest work, golden vectors, and tiny deterministic "
                "proof harnesses only"
            ),
            "forbidden_next_work": (
                "No broad seed search, no long-span sweep, no format promotion, no "
                "public preset registry, and no production acceleration claim."
            ),
            "conclusion": (
                "The next viable research move is not compute; it is to choose and "
                "specify one materially new byte-to-seed mechanism with controls "
                "strong enough to reopen generated gates."
            ),
        },
        "designs": DESIGNS,
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Next Mechanism Designs",
        "",
        f"Generated by `{GENERATED_BY}` after the mechanism closure audit.",
        "This is a No Seed Search design artifact. It launches no agents, performs no broad seed search, is not natural-corpus proof, is not production proof, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Design status: `{data['design_status']}`",
        f"- Designs: `{data['design_count']}`",
        f"- Pre-registered designs: `{data['pre_registered_design_count']}`",
        f"- Ready compute count: `{data['ready_compute_count']}`",
        f"- Top design: `{data['top_design_id']}`",
        f"- Closure status: `{data['closure_status']}`",
        f"- Closure ready compute lanes: `{data['closure_ready_compute_lane_count']}`",
        f"- Closure top blocked lane: `{data['closure_top_blocked_lane']}`",
        f"- Broad depth search allowed: `{data['broad_depth_search_allowed']}`",
        f"- Format promotion allowed: `{data['format_promotion_allowed']}`",
        f"- Allowed next work: `{data['allowed_next_work']}`",
        f"- Forbidden next work: `{data['forbidden_next_work']}`",
        "",
        data["conclusion"],
        "",
        "## Design Matrix",
        "",
        "| rank | design | family | status | first artifact |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in payload["designs"]:
        lines.append(
            f"| {row['rank']} | `{cell(row['design_id'])}` | "
            f"`{cell(row['mechanism_family'])}` | `{cell(row['status'])}` | "
            f"`{cell(row['first_artifact'])}` |"
        )
    lines.extend(["", "## Design Details", ""])
    for row in payload["designs"]:
        lines.extend(
            [
                f"### {row['design_id']}",
                "",
                f"- Title: {row['title']}",
                f"- Status: `{row['status']}`",
                f"- Whitepaper link: {row['whitepaper_link']}",
                f"- Core idea: {row['core_idea']}",
                f"- Why materially new: {row['why_materially_new']}",
                f"- Implementation slice: {row['implementation_slice']}",
                f"- Falsification test: {row['falsification_test']}",
                f"- Promotion trigger: {row['promotion_trigger']}",
                f"- Stop rule: {row['stop_rule']}",
                f"- Compute budget: {row['compute_budget']}",
                f"- Blocked by: {', '.join(f'`{item}`' for item in row['blocked_by'])}",
                f"- Controls: {', '.join(f'`{item}`' for item in row['control_suite'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this design registry to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.append(f"- `design_manifest_sha256`: `{payload['design_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated next mechanism design files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("next_mechanism_designs.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("next mechanism design source hashes are stale")
    if payload.get("design_manifest_sha256") != design_manifest_hash():
        raise SystemExit("next mechanism design manifest hash is stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("next_mechanism_designs.json is stale; regenerate it")
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
            raise SystemExit(f"next mechanism design scope field must be false: {field}")
    if payload["summary"]["ready_compute_count"] != 0:
        raise SystemExit("next mechanism designs must not report ready compute")
    for row in payload.get("designs", []):
        if row.get("status") not in VALID_STATUSES:
            raise SystemExit(f"invalid next mechanism design status: {row.get('status')}")
        if "broad seed search" in row.get("compute_budget", "").lower():
            raise SystemExit(f"design compute budget cannot allow broad seed search: {row['design_id']}")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Next Mechanism Designs",
        "No Seed Search",
        "Ready compute count",
        "Falsification test",
        "Promotion trigger",
        "Stop rule",
        "source_hashes",
        "not natural-corpus proof",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"NEXT_MECHANISM_DESIGNS.md missing phrase: {phrase}")


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
