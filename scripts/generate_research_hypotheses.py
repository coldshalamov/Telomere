#!/usr/bin/env python3
"""Generate Telomere's falsifiable research hypothesis registry.

This is a no-compute coordination artifact. It turns the whitepaper thesis and
the current generated evidence into bounded hypothesis lanes for future
dispatching-parallel-agents work. It launches no agents and performs no seed
search.
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
REPORT_JSON = DOCS / "research_hypotheses.json"
REPORT_MD = DOCS / "RESEARCH_HYPOTHESES.md"
GENERATED_BY = "scripts/generate_research_hypotheses.py"

SOURCE_PATHS = {
    "whitepaper_sha256": DOCS / "Telomere Whitepaper V2.md",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "experiment_queue_sha256": DOCS / "experiment_queue.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "natural_corpus_reopen_manifest_sha256": DOCS / "natural_corpus_reopen_manifest.json",
    "external_corpus_accession_sha256": DOCS / "external_corpus_accession.json",
    "production_proof_matrix_sha256": DOCS / "production_proof_matrix.json",
    "goal_completion_audit_sha256": DOCS / "goal_completion_audit.json",
    "research_team_protocol_sha256": DOCS / "research_team_protocol.json",
    "blocked_requirement_dispatch_sha256": DOCS / "blocked_requirement_dispatch.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "mechanism_closure_audit_sha256": DOCS / "mechanism_closure_audit.json",
    "next_mechanism_designs_sha256": DOCS / "next_mechanism_designs.json",
    "frozen_rank_coded_span_generator_sha256": DOCS
    / "frozen_rank_coded_span_generator.json",
    "frozen_rank_source_candidates_sha256": DOCS
    / "frozen_rank_source_candidates.json",
    "superposition_telemetry_sha256": DOCS / "superposition_telemetry.json",
    "lattice_selection_heldout_probe_sha256": DOCS
    / "lattice_selection_heldout_probe.json",
    "recursive_structured_fixtures_sha256": DOCS / "recursive_structured_fixtures.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "seed_table_preset_replay_sha256": DOCS / "seed_table_preset_replay.json",
    "seed_table_fasta_ablation_sha256": DOCS / "seed_table_fasta_ablation.json",
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "public_preset_control_audit_sha256": DOCS / "public_preset_control_audit.json",
    "public_preset_control_ablation_sha256": DOCS / "public_preset_control_ablation.json",
    "public_preset_ablation_projection_sha256": DOCS / "public_preset_ablation_projection.json",
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "whole_stream_residual_vector_probe_sha256": DOCS
    / "whole_stream_residual_vector_probe.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "bounded_streaming_memory_gate_sha256": DOCS / "bounded_streaming_memory_gate.json",
    "streaming_economics_gate_sha256": DOCS / "streaming_economics_gate.json",
    "ui_workflow_smoke_sha256": DOCS / "ui_workflow_smoke.json",
    "acceleration_report_sha256": DOCS / "acceleration_report.json",
}

VALID_STATUSES = {
    "blocked-by-evidence",
    "maintenance-only",
    "pre-registered-design",
    "ready-if-triggered",
}

COMMON_FORBIDDEN_ACTIONS = [
    "No Seed Search: do not start new depth-3, depth-4, or long-span sweeps",
    "do not claim natural-corpus compression is proven",
    "do not claim production readiness",
    "do not promote .tlmr v2, transform metadata, or dictionary presets to stable format support",
    "do not weaken random, shadow, binary, or same-size control requirements",
    "do not edit generated markdown or JSON by hand",
]

OUTPUT_CONTRACT = [
    "findings first with source artifacts and generated status",
    "state whether the falsification test currently fails, passes, or is not yet runnable",
    "state the exact promotion trigger that would reopen more work",
    "list any proposed artifact, check command, and compute budget",
    "preserve No Seed Search and not production proof language unless generated gates change",
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


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def source_key(name: str) -> str:
    return name.removesuffix("_sha256")


def source_inputs() -> dict[str, dict[str, Any]]:
    inputs = {}
    for name, path in SOURCE_PATHS.items():
        key = source_key(name)
        if path.suffix == ".json":
            inputs[key] = load_json(path)
    return inputs


def source_summaries(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {key: summary(value) for key, value in sorted(inputs.items())}


def build_prompt(hypothesis: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Hypothesis {hypothesis['hypothesis_id']}: use dispatching-parallel-agents as the operating model.",
            f"Best case: {hypothesis['best_case_argument']}",
            f"Whitepaper concept: {hypothesis['whitepaper_concept']}",
            f"Current evidence: {hypothesis['current_evidence']}",
            "Scope: No Seed Search, not a compression claim, not natural-corpus proof, and not production proof.",
            f"Falsification test: {hypothesis['falsification_test']}",
            f"Promotion trigger: {hypothesis['promotion_trigger']}",
            f"Stop rule: {hypothesis['stop_rule']}",
            f"Source artifacts: {', '.join(hypothesis['source_artifacts'])}.",
            f"forbidden_actions: {'; '.join(hypothesis['forbidden_actions'])}.",
            f"output_contract: {'; '.join(hypothesis['output_contract'])}.",
            "Return a bounded findings-first design or audit; do not launch broad compute.",
        ]
    )


def build_hypotheses(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    frontier = summary(inputs["research_frontier"])
    mechanism = summary(inputs["mechanism_experiment_ranking"])
    natural = summary(inputs["natural_corpus_proof_matrix"])
    natural_reopen = summary(inputs["natural_corpus_reopen_manifest"])
    external_accession = summary(inputs["external_corpus_accession"])
    production = summary(inputs["production_proof_matrix"])
    completion = summary(inputs["goal_completion_audit"])
    search = summary(inputs["search_frontier_gate"])
    long_span = summary(inputs["long_span_bundle_gate"])
    mechanism_closure = summary(inputs["mechanism_closure_audit"])
    next_designs = summary(inputs["next_mechanism_designs"])
    frozen_rank = summary(inputs["frozen_rank_coded_span_generator"])
    frozen_rank_sources = summary(inputs["frozen_rank_source_candidates"])
    superposition = summary(inputs["superposition_telemetry"])
    lattice_heldout = summary(inputs["lattice_selection_heldout_probe"])
    recursive = summary(inputs["recursive_structured_fixtures"])
    seed_table = summary(inputs["seed_table_preset_probe"])
    seed_table_replay = summary(inputs["seed_table_preset_replay"])
    seed_table_fasta = summary(inputs["seed_table_fasta_ablation"])
    public_preset = summary(inputs["public_preset_promotion_gate"])
    public_control = summary(inputs["public_preset_control_audit"])
    public_ablation = summary(inputs["public_preset_control_ablation"])
    public_projection = summary(inputs["public_preset_ablation_projection"])
    public_rerun = summary(inputs["public_preset_control_rerun"])
    residual = summary(inputs["whole_stream_residual_vector_probe"])
    schema = summary(inputs["schema_native_public_dictionary_replication"])
    scale = summary(inputs["scale_performance_report"])
    bounded_memory = summary(inputs["bounded_streaming_memory_gate"])
    streaming_gate = summary(inputs["streaming_economics_gate"])
    ui = summary(inputs["ui_workflow_smoke"])
    acceleration = summary(inputs["acceleration_report"])

    common = {
        "output_contract": OUTPUT_CONTRACT,
        "forbidden_actions": COMMON_FORBIDDEN_ACTIONS,
    }

    hypotheses = [
        {
            "hypothesis_id": "seed-table-public-preset",
            "title": "Public seed-table presets can reshape the byte-to-seed distribution",
            "status": "blocked-by-evidence",
            "parallel_groups": ["corpus-transform", "format-policy"],
            "whitepaper_concept": "table lookup from a seed table / public Lotus preset",
            "best_case_argument": (
                "A frozen decoder-public codebook could make the generative space less "
                "cryptographically random for structured corpora while staying lossless "
                "and avoiding file-local training leakage."
            ),
            "current_evidence": (
                f"canonical selected spans={seed_table.get('canonical_selected_spans')}, "
                f"public gate qualified={public_preset.get('qualified_count')}/"
                f"{public_preset.get('gate_count')}, blocked gates="
                f"{public_preset.get('blocked_gate_ids')}; control audit status="
                f"{public_control.get('audit_status')} with strongest control "
                f"{public_control.get('strongest_control_case')}; ablations required="
                f"{public_ablation.get('required_ablation_count')}; projected leave-family-out "
                f"ordinary groups={public_projection.get('same_family_removed_ordinary_negative_groups')} "
                f"and control groups={public_projection.get('same_family_removed_control_negative_groups')}; "
                f"exact rerun status={public_rerun.get('rerun_status')} with no-project "
                f"control groups={public_rerun.get('no_project_control_negative_groups')}, "
                f"leave-family-out ordinary groups={public_rerun.get('leave_family_out_ordinary_negative_groups')}, "
                f"and clean no-project leave-family-out ordinary groups="
                f"{public_rerun.get('leave_family_out_no_project_ordinary_negative_groups')}. "
                f"bounded replay found ordinary negative groups="
                f"{seed_table_replay.get('ordinary_negative_groups')}, control negative groups="
                f"{seed_table_replay.get('control_negative_groups')}, selected spans="
                f"{seed_table_replay.get('canonical_selected_spans')}, promotion candidate="
                f"{seed_table_replay.get('promotion_candidate')}. FASTA ablation "
                f"header artifact likely={seed_table_fasta.get('header_artifact_likely')}, "
                f"sequence lane reopen candidate="
                f"{seed_table_fasta.get('sequence_lane_reopen_candidate')}, "
                f"total header-selected spans="
                f"{seed_table_fasta.get('total_header_selected_spans')}, "
                f"total sequence-selected spans="
                f"{seed_table_fasta.get('total_sequence_selected_spans')}, stop reasons="
                f"{seed_table_fasta.get('stop_reasons')}. Mechanism closure status="
                f"{mechanism_closure.get('closure_status')} with ready compute lanes="
                f"{mechanism_closure.get('ready_compute_lane_count')} and top blocked lane="
                f"{mechanism_closure.get('top_blocked_lane')}."
            ),
            "falsification_test": (
                "The current standards preset is falsified by exact rerun; any successor "
                "must freeze discovery/held-out splits and show ordinary held-out "
                "negative groups survive while controls stay zero."
            ),
            "promotion_trigger": (
                "At least three ordinary held-out negative groups, zero control negative "
                "groups, exact decode from preset/version metadata only, and improvement "
                "beyond equivalent random-trial scaling."
            ),
            "stop_rule": (
                "Do not add seed-table preset metadata to .tlmr until generated promotion "
                "gates pass and shadow controls stay null."
            ),
            "source_artifacts": [
                "docs/SEED_TABLE_PRESET_PROBE.md",
                "docs/SEED_TABLE_PRESET_REPLAY.md",
                "docs/SEED_TABLE_FASTA_ABLATION.md",
                "docs/MECHANISM_CLOSURE_AUDIT.md",
                "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
                "docs/PUBLIC_PRESET_CONTROL_AUDIT.md",
                "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
                "docs/PUBLIC_PRESET_ABLATION_PROJECTION.md",
                "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
                "docs/MECHANISM_EXPERIMENT_RANKING.md",
                "docs/FORMAT.md",
            ],
            "suggested_artifact": "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
            **common,
        },
        {
            "hypothesis_id": "frozen-rank-coded-span-generator",
            "title": "Frozen rank-coded span generation can make seed expansion corpus-shaped",
            "status": "pre-registered-design",
            "parallel_groups": ["corpus-transform", "format-policy", "meta-research"],
            "whitepaper_concept": "table lookup from a seed table, but rank-coded and external-provenance first",
            "best_case_argument": (
                "A decoder-public rank table could make seed bytes name common external "
                "spans directly, giving the compressor a non-uniform generative prior "
                "without storing per-file raw data or widening raw hash depth."
            ),
            "current_evidence": (
                f"contract status={frozen_rank.get('contract_status')}; "
                f"golden vectors={frozen_rank.get('golden_vector_count')}; "
                f"external manifest ready={frozen_rank.get('external_manifest_ready')}; "
                f"paired manifest ready={frozen_rank.get('paired_manifest_ready')}; "
                f"compute allowed={frozen_rank.get('compute_allowed')}; "
                f"replay allowed={frozen_rank.get('replay_allowed')}; "
                f"promotion ready={frozen_rank.get('promotion_ready')}. "
                f"source candidate status={frozen_rank_sources.get('candidate_status')}; "
                f"candidate families={frozen_rank_sources.get('candidate_family_count')}; "
                f"required manifest rows before replay="
                f"{frozen_rank_sources.get('required_external_manifest_row_count')}; "
                f"source candidates ready for manifest="
                f"{frozen_rank_sources.get('ready_for_external_manifest_count')}; "
                f"source candidates ready for replay="
                f"{frozen_rank_sources.get('ready_for_replay_count')}."
            ),
            "falsification_test": (
                "The rank table cannot be frozen from external provenance, controls go "
                "negative, or held-out gains are no better than same-size random rank "
                "tables and flat dictionary baselines."
            ),
            "promotion_trigger": (
                "An external rank-table manifest is complete, at least three unrelated "
                "ordinary held-out groups produce selected exact spans and full-stream "
                "negative rows after selector/version metadata, and paired shadow, "
                "same-size random, wrong-family, binary, and high-entropy controls stay "
                "non-negative."
            ),
            "stop_rule": (
                "Keep the fixture table out of .tlmr and do not run held-out replay "
                "until external accession and paired controls are ready."
            ),
            "source_artifacts": [
                "docs/NEXT_MECHANISM_DESIGNS.md",
                "docs/FROZEN_RANK_CODED_SPAN_GENERATOR.md",
                "docs/FROZEN_RANK_SOURCE_CANDIDATES.md",
                "docs/EXTERNAL_CORPUS_ACCESSION.md",
                "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
            ],
            "suggested_artifact": "docs/FROZEN_RANK_CODED_SPAN_GENERATOR.md",
            **common,
        },
        {
            "hypothesis_id": "stratified-streaming-scale",
            "title": "Streaming stratified target tiers can make wider search economically testable",
            "status": "maintenance-only",
            "parallel_groups": ["compute-economics", "acceleration"],
            "whitepaper_concept": "stratified block tables plus one seed expansion checked across many tiers",
            "best_case_argument": (
                "The serious engine should expand each seed once, compare generated "
                "prefixes against multiple equal-length target tiers, and verify hits "
                "without hashing target spans."
            ),
            "current_evidence": (
                f"streaming gate status={streaming_gate.get('gate_status')}, "
                f"bounded memory status={bounded_memory.get('gate_status')}, "
                f"target-table preflight={bounded_memory.get('target_table_preflight_present')}, "
                f"full RSS containment={bounded_memory.get('full_rss_containment')}, "
                f"indexed/streaming parity={streaming_gate.get('indexed_streaming_span8_parity')}, "
                f"streaming control negatives={streaming_gate.get('streaming_control_negative_case_count')}, "
                f"ordinary non-planted streaming negatives="
                f"{streaming_gate.get('streaming_ordinary_non_planted_negative_case_count')}, "
                f"compute reopen allowed={streaming_gate.get('compute_reopen_allowed')}; "
                f"search frontier selected spans={search.get('selected_span_total')}, "
                f"broad_depth_search_allowed={search.get('broad_depth_search_allowed')}, "
                f"16 MiB planted scale peak memory={scale.get('largest_peak_memory_mib')} MiB."
            ),
            "falsification_test": (
                "Show streaming/indexed parity on fixtures while target-table memory or "
                "seed-expansion throughput fails to improve enough to justify larger runs."
            ),
            "promotion_trigger": (
                "A generated scale artifact shows bounded memory growth, exact parity, "
                "and repeatable non-planted selected spans before raw-depth expansion."
            ),
            "stop_rule": (
                "Do not widen search solely because streaming exists; reopen compute only "
                "when search-frontier gates move."
            ),
            "source_artifacts": [
                "docs/SEARCH_FRONTIER_GATE.md",
                "docs/BOUNDED_STREAMING_MEMORY_GATE.md",
                "docs/STREAMING_ECONOMICS_GATE.md",
                "docs/SCALE_PERFORMANCE.md",
                "docs/RESULTS.md",
            ],
            "suggested_artifact": "docs/STREAMING_ECONOMICS_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "alignment-arity-frontier",
            "title": "Arity and phase search may expose longer profitable spans",
            "status": "blocked-by-evidence",
            "parallel_groups": ["compute-economics", "corpus-transform"],
            "whitepaper_concept": "continue to search farther and match higher-arity blocks",
            "best_case_argument": (
                "Arity gives each discovered seed more bites at the apple by letting one "
                "record cover longer spans, especially if candidate starts are not locked "
                "to an arbitrary block grid."
            ),
            "current_evidence": (
                f"long-span gate met {long_span.get('gate_met_count')}/"
                f"{long_span.get('gate_count')}; positive alignment exact hits="
                f"{search.get('positive_alignment_exact_hits')}; selected spans="
                f"{search.get('selected_span_total')}."
            ),
            "falsification_test": (
                "Phase/arity controls continue to show no prefix>=5, exact-hit, or "
                "selected-span movement after metadata and controls are charged."
            ),
            "promotion_trigger": (
                "Generated alignment/arity artifacts show repeatable exact selected spans "
                "on ordinary held-out corpora while random and binary controls stay null."
            ),
            "stop_rule": (
                "Do not run broad long-span bundle sweeps while the long-span bundle gate "
                "and search frontier remain closed."
            ),
            "source_artifacts": [
                "docs/ALIGNMENT_ARITY_DISCOVERY.md",
                "docs/LONG_SPAN_BUNDLE_GATE.md",
                "docs/SEARCH_FRONTIER_GATE.md",
            ],
            "suggested_artifact": "docs/ARITY_PHASE_REOPEN_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "candidate-lattice-superposition",
            "title": "A deterministic candidate lattice can preserve useful alternatives before selection",
            "status": "blocked-by-evidence",
            "parallel_groups": ["compute-economics", "meta-research"],
            "whitepaper_concept": "superposition of possible replacements before collapse to selected records",
            "best_case_argument": (
                "Keeping near-best candidates temporarily can prevent greedy local choices "
                "from destroying a better global bundle, while decompression still sees "
                "only ordinary selected v1/v2 records."
            ),
            "current_evidence": (
                f"weighted beats greedy fixtures={superposition.get('weighted_beats_greedy_fixture_count')}, "
                f"weighted extra savings={superposition.get('weighted_extra_savings')}, "
                f"promotion_met={superposition.get('promotion_met')}; held-out replay rows="
                f"{lattice_heldout.get('row_count')}, weighted extra positive rows="
                f"{lattice_heldout.get('weighted_extra_positive_row_count')}, "
                f"ordinary extra groups={lattice_heldout.get('ordinary_weighted_extra_groups')}, "
                f"promotion_met={lattice_heldout.get('promotion_met')}. This is selector "
                "correctness, not compression utility proof."
            ),
            "falsification_test": (
                "Current held-out candidate replay found zero weighted-extra rows; "
                "future retained alternatives must improve selected savings on held-out "
                "ordinary rows after literal and metadata overhead."
            ),
            "promotion_trigger": (
                "Candidate-lattice telemetry improves selected bytes on non-planted "
                "held-out rows without requiring recursive superposition or decoder state."
            ),
            "stop_rule": (
                "Disallow recursive superposition; recursive passes operate only on "
                "already selected layer outputs."
            ),
            "source_artifacts": [
                "docs/SUPERPOSITION_TELEMETRY.md",
                "docs/LATTICE_SELECTION_HELDOUT_PROBE.md",
                "docs/CANDIDATE_LATTICE.md",
                "docs/FORMAT.md",
            ],
            "suggested_artifact": "docs/LATTICE_SELECTION_HELDOUT_PROBE.md",
            **common,
        },
        {
            "hypothesis_id": "reversible-transform-preconditioners",
            "title": "Reversible preconditioners may move near misses into exact seed spans",
            "status": "blocked-by-evidence",
            "parallel_groups": ["corpus-transform", "format-policy"],
            "whitepaper_concept": "transform the byte landscape so later seed search has new opportunities",
            "best_case_argument": (
                "A reversible transform could expose a corpus channel that finite seed "
                "outputs cover better than raw bytes, as long as metadata and inverse "
                "decode are charged honestly."
            ),
            "current_evidence": (
                f"natural held-out prefix5 rows={natural.get('heldout_prefix5_rows')}, "
                f"exact hits={natural.get('heldout_exact_hit_rows')}, selected spans="
                f"{natural.get('heldout_selected_span_rows')}; prefix-4 movement has "
                "not promoted."
            ),
            "falsification_test": (
                "Transforms keep producing prefix-only movement or transform-only byte "
                "shortening without exact seed-span wins after metadata."
            ),
            "promotion_trigger": (
                "A generated transform artifact reports exact selected seed spans on "
                "held-out ordinary corpora with transform metadata charged."
            ),
            "stop_rule": (
                "Keep transform descriptors outside .tlmr v1/v2 until exact decode and "
                "promotion gates pass."
            ),
            "source_artifacts": [
                "docs/TRANSFORM_VALIDATION.md",
                "docs/MECHANISM_EXPERIMENT_RANKING.md",
                "docs/adr/0001-transform-preconditioners.md",
            ],
            "suggested_artifact": "docs/TRANSFORM_EXACT_SPAN_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "residual-sidecar-channel",
            "title": "Residual sidecars might turn near matches into profitable exact records",
            "status": "blocked-by-evidence",
            "parallel_groups": ["corpus-transform", "compute-economics"],
            "whitepaper_concept": "store only residual correction data around seed-generated spans",
            "best_case_argument": (
                "If generated bytes are close enough, a compact residual channel could "
                "charge correction bytes yet still beat raw literals for structured data."
            ),
            "current_evidence": (
                "whole-stream ordinary held-out negative groups="
                f"{residual.get('ordinary_heldout_negative_groups')}, "
                f"control negative groups={residual.get('control_negative_groups')}, "
                "and current residual lanes do not prove honest full-stream savings."
            ),
            "falsification_test": (
                "Residual vector, offset, seed, checksum, and literal bytes erase every "
                "ordinary whole-stream win or controls win similarly."
            ),
            "promotion_trigger": (
                "At least three ordinary whole-stream negative groups with zero comparable "
                "control wins and exact reconstruction from charged sidecar bytes."
            ),
            "stop_rule": (
                "Do not count residual proximity as compression unless full-stream "
                "charged records are negative and controls stay null."
            ),
            "source_artifacts": [
                "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md",
                "docs/SIDECAR_BREAK_EVEN.md",
                "docs/PACKED_SIDECAR_REPLICATION.md",
            ],
            "suggested_artifact": "docs/RESIDUAL_SIDECAR_PROMOTION_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "schema-native-public-dictionaries",
            "title": "Public schema dictionaries can act as decoder-public generative presets",
            "status": "blocked-by-evidence",
            "parallel_groups": ["corpus-transform", "format-policy"],
            "whitepaper_concept": "decoder-public lookup tables instead of file-local raw payloads",
            "best_case_argument": (
                "For structured domains, a public dictionary can be treated like a "
                "versioned preset: the file names the preset, not the raw table."
            ),
            "current_evidence": (
                f"schema claim level={schema.get('claim_level')}; control negative groups="
                f"{schema.get('standards_control_negative_groups')}; controls currently block "
                "registry or format promotion."
            ),
            "falsification_test": (
                "Paired shadow schemas, wrong-schema dictionaries, or same-size random "
                "controls shrink with comparable density."
            ),
            "promotion_trigger": (
                "Frozen public dictionaries produce held-out ordinary wins while paired "
                "shadow and binary controls remain null."
            ),
            "stop_rule": (
                "Do not add dictionary registry semantics to .tlmr until decoder-public "
                "identity and control separation are proven."
            ),
            "source_artifacts": [
                "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
                "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
                "docs/FORMAT.md",
            ],
            "suggested_artifact": "docs/PUBLIC_DICTIONARY_CONTROL_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "recursive-v2-layer-dynamics",
            "title": "Recursive v2 passes may expose second-layer wins after selected replacements",
            "status": "blocked-by-evidence",
            "parallel_groups": ["format-policy", "corpus-transform"],
            "whitepaper_concept": "recursive passes operate on transformed layer outputs",
            "best_case_argument": (
                "Once selected records replace spans, the next byte landscape is different; "
                "v2 can test that idea while keeping layer hashes and descriptors explicit."
            ),
            "current_evidence": (
                f"ordinary later-win families={recursive.get('ordinary_later_win_families')}, "
                f"planted offset later-win families={recursive.get('planted_offset_later_win_families')}, "
                f"promotion_met={recursive.get('promotion_met')}."
            ),
            "falsification_test": (
                "Later-layer gains remain isolated to planted offset controls and ordinary "
                "structured fixture families do not improve."
            ),
            "promotion_trigger": (
                "At least two ordinary structured fixture families show later-layer wins "
                "with exact recursive decode and no index requirement."
            ),
            "stop_rule": (
                "Keep v2 experimental; do not reinterpret v1 layer_count or emit recursive "
                "v1 outputs."
            ),
            "source_artifacts": [
                "docs/RECURSIVE_STRUCTURED_FIXTURES.md",
                "docs/FORMAT.md",
                "docs/PRODUCTION_PROOF_MATRIX.md",
            ],
            "suggested_artifact": "docs/RECURSIVE_LAYER_PROMOTION_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "gpu-asic-acceleration-path",
            "title": "Hardware acceleration matters only after CPU evidence identifies a promoted workload",
            "status": "blocked-by-evidence",
            "parallel_groups": ["acceleration", "compute-economics"],
            "whitepaper_concept": "specialized hardware makes wider seed search practical",
            "best_case_argument": (
                "If CPU streaming finds a profitable workload, GPUs or ASICs could turn "
                "archival search from theoretically possible into economically testable."
            ),
            "current_evidence": (
                f"acceleration status={production.get('acceleration_status')}, "
                f"real GPU kernel detected={acceleration.get('real_kernel_detected')}, "
                f"production blocked gates={production.get('blocked_by_evidence_count')}."
            ),
            "falsification_test": (
                "No real kernel, no CPU/GPU parity, or no CPU workload with evidence worth "
                "accelerating."
            ),
            "promotion_trigger": (
                "A real kernel-backed matcher passes CPU/GPU parity on promoted workloads "
                "and improves wall-clock or energy enough to change the scale gate."
            ),
            "stop_rule": (
                "Do not trust GPU output or market acceleration while the GPU feature is "
                "research-only CPU semantics."
            ),
            "source_artifacts": [
                "docs/ACCELERATION.md",
                "docs/adr/0002-gpu-acceleration-status.md",
                "docs/SCALE_PERFORMANCE.md",
            ],
            "suggested_artifact": "docs/HARDWARE_ACCELERATION_PROMOTION_GATE.md",
            **common,
        },
        {
            "hypothesis_id": "natural-corpus-proof-campaign",
            "title": "Natural-corpus viability needs repeatable non-planted selected spans",
            "status": "blocked-by-evidence",
            "parallel_groups": ["corpus-transform", "meta-research"],
            "whitepaper_concept": "structured real corpora may contain enough generative spans to beat overhead",
            "best_case_argument": (
                "Telomere becomes interesting only if ordinary or transformed corpora show "
                "repeatable selected spans that controls do not reproduce."
            ),
            "current_evidence": (
                f"natural proof status={natural.get('natural_corpus_status')}, blocked gates="
                f"{natural.get('blocked_by_evidence_count')}, held-out selected spans="
                f"{natural.get('heldout_selected_span_rows')}, best forecast="
                f"{natural.get('best_non_planted_gib_for_one_expected_hit')} GiB; "
                f"reopen manifest status={natural_reopen.get('manifest_status')}, "
                f"first allowed stage={natural_reopen.get('first_allowed_stage')}, "
                f"next compute stage={natural_reopen.get('next_compute_stage_status')}; "
                f"external accession status={external_accession.get('accession_status')}, "
                f"entries={external_accession.get('entry_count')}, manifest_complete="
                f"{external_accession.get('manifest_complete')}, compute_allowed="
                f"{external_accession.get('compute_allowed')}."
            ),
            "falsification_test": (
                "Held-out prefix>=5, exact-hit, selected-span, and negative-delta gates "
                "remain null or require hundreds of GiB per expected hit."
            ),
            "promotion_trigger": (
                "NATURAL_CORPUS_PROOF_MATRIX reports qualified natural-corpus proof with "
                "ordinary selected spans or negative delta and controls still null."
            ),
            "stop_rule": (
                "Do not claim natural-corpus viability while any natural proof blocker "
                "remains."
            ),
            "source_artifacts": [
                "docs/NATURAL_CORPUS_PROOF_MATRIX.md",
                "docs/NATURAL_CORPUS_REOPEN_MANIFEST.md",
                "docs/EXTERNAL_CORPUS_ACCESSION.md",
                "docs/RESEARCH_SCORECARD.md",
                "docs/SEARCH_FRONTIER_GATE.md",
            ],
            "suggested_artifact": "docs/EXTERNAL_CORPUS_ACCESSION.md",
            **common,
        },
        {
            "hypothesis_id": "production-release-proof",
            "title": "Production readiness requires format, workload, acceleration, and UI proof together",
            "status": "maintenance-only",
            "parallel_groups": ["format-policy", "acceleration", "operator-ui"],
            "whitepaper_concept": "turn the research engine into a supported archival tool",
            "best_case_argument": (
                "A release can be trustworthy only if decode compatibility, workload "
                "evidence, operator visibility, and acceleration boundaries all agree."
            ),
            "current_evidence": (
                f"production status={production.get('production_status')}, "
                f"blocked gates={production.get('blocked_by_evidence_count')}, "
                f"runtime-required gates={production.get('runtime_required_count')}, "
                f"UI promotion met={ui.get('promotion_met')}."
            ),
            "falsification_test": (
                "Any release candidate lacks supported compatibility guarantees, real "
                "workload evidence, acceleration value, or runtime verification."
            ),
            "promotion_trigger": (
                "PRODUCTION_PROOF_MATRIX reports production_proven=true, with zero blocked "
                "requirements and clean release gates."
            ),
            "stop_rule": (
                "Do not promote v2 or acceleration to production while production proof "
                "matrix remains not_production_ready."
            ),
            "source_artifacts": [
                "docs/PRODUCTION_PROOF_MATRIX.md",
                "docs/RELEASE_CHECKLIST.md",
                "docs/UI_WORKFLOW_SMOKE.md",
            ],
            "suggested_artifact": "docs/RELEASE_CANDIDATE_PROOF_PACKET.md",
            **common,
        },
        {
            "hypothesis_id": "completion-boundary-integrity",
            "title": "The active goal remains open until blockers are erased by generated evidence",
            "status": "maintenance-only",
            "parallel_groups": ["meta-research"],
            "whitepaper_concept": "separate thesis, implementation, evidence, and production proof",
            "best_case_argument": (
                "The project can keep exploring a radical idea without fooling itself if "
                "completion requires generated proof rather than enthusiasm or prose."
            ),
            "current_evidence": (
                f"objective status={completion.get('objective_status')}, "
                f"blocking requirements={completion.get('blocking_requirement_ids')}, "
                f"unresolved gates={completion.get('unresolved_evidence_gates')}."
            ),
            "falsification_test": (
                "A summary, UI card, or dispatch brief removes blockers without the "
                "underlying generated proof matrices moving."
            ),
            "promotion_trigger": (
                "GOAL_COMPLETION_AUDIT reports zero blocked requirements, zero unresolved "
                "evidence gates, and production_proven=true."
            ),
            "stop_rule": (
                "Keep the goal active while natural-corpus viability, production proof, "
                "or completion-boundary blockers remain."
            ),
            "source_artifacts": [
                "docs/GOAL_COMPLETION_AUDIT.md",
                "docs/BLOCKED_REQUIREMENT_DISPATCH.md",
                "docs/GENERATED_LEDGER_PIPELINE.md",
            ],
            "suggested_artifact": "docs/GOAL_COMPLETION_AUDIT.md",
            **common,
        },
        {
            "hypothesis_id": "cross-agent-brainstorming-discipline",
            "title": "Parallel brainstorming is useful only when every lane is bounded and falsifiable",
            "status": "maintenance-only",
            "parallel_groups": ["meta-research", "operator-ui"],
            "whitepaper_concept": "many independent ways to search the generative mechanism space",
            "best_case_argument": (
                "Multiple research agents can explore different mechanism families at once "
                "if they share stop rules, source hashes, and artifact contracts."
            ),
            "current_evidence": (
                f"team protocol status={frontier.get('frontier_status')}; "
                f"queue ready count={summary(inputs['experiment_queue']).get('ready_count')}; "
                f"mechanism top lane={mechanism.get('top_lane_id')}; "
                f"closure ready compute lanes="
                f"{mechanism_closure.get('ready_compute_lane_count')}; "
                f"pre-registered next designs="
                f"{next_designs.get('pre_registered_design_count')}; "
                f"top design={next_designs.get('top_design_id')}."
            ),
            "falsification_test": (
                "Brainstorming produces unbounded compute requests, duplicated artifacts, "
                "or unsupported compression/prod claims."
            ),
            "promotion_trigger": (
                "New briefs propose bounded checked artifacts that improve a blocked gate "
                "without bypassing SEARCH_FRONTIER_GATE."
            ),
            "stop_rule": (
                "Use subagents for bounded audits/designs; do not launch agents that edit "
                "the same files blindly or run broad search."
            ),
            "source_artifacts": [
                "docs/RESEARCH_TEAM_PROTOCOL.md",
                "docs/BLOCKED_REQUIREMENT_DISPATCH.md",
                "docs/MECHANISM_EXPERIMENT_RANKING.md",
                "docs/MECHANISM_CLOSURE_AUDIT.md",
                "docs/NEXT_MECHANISM_DESIGNS.md",
            ],
            "suggested_artifact": "docs/RESEARCH_HYPOTHESES.md",
            **common,
        },
    ]

    for hypothesis in hypotheses:
        hypothesis["dispatch_prompt"] = build_prompt(hypothesis)

    return hypotheses


def dispatch_matrix(hypotheses: list[dict[str, Any]]) -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = defaultdict(list)
    for hypothesis in hypotheses:
        for group in hypothesis["parallel_groups"]:
            matrix[group].append(hypothesis["hypothesis_id"])
    return dict(sorted(matrix.items()))


def build_report() -> dict[str, Any]:
    inputs = source_inputs()
    hypotheses = build_hypotheses(inputs)
    status_counts = Counter(item["status"] for item in hypotheses)
    groups = sorted({group for item in hypotheses for group in item["parallel_groups"]})
    natural = summary(inputs["natural_corpus_proof_matrix"])
    external_accession = summary(inputs["external_corpus_accession"])
    production = summary(inputs["production_proof_matrix"])
    frontier = summary(inputs["research_frontier"])
    search = summary(inputs["search_frontier_gate"])
    mechanism = summary(inputs["mechanism_experiment_ranking"])
    mechanism_closure = summary(inputs["mechanism_closure_audit"])
    next_designs = summary(inputs["next_mechanism_designs"])
    frozen_rank = summary(inputs["frozen_rank_coded_span_generator"])
    frozen_rank_sources = summary(inputs["frozen_rank_source_candidates"])
    bounded_memory = summary(inputs["bounded_streaming_memory_gate"])
    streaming_gate = summary(inputs["streaming_economics_gate"])
    completion = summary(inputs["goal_completion_audit"])

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "research hypothesis registry",
            "dispatching_parallel_agents": True,
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "source_summaries": source_summaries(inputs),
        "summary": {
            "hypothesis_count": len(hypotheses),
            "parallel_group_count": len(groups),
            "parallel_groups": groups,
            "status_counts": dict(sorted(status_counts.items())),
            "pre_registered_design_count": status_counts["pre-registered-design"],
            "blocked_by_evidence_count": status_counts["blocked-by-evidence"],
            "maintenance_only_count": status_counts["maintenance-only"],
            "ready_if_triggered_count": status_counts["ready-if-triggered"],
            "natural_corpus_proven": bool(natural.get("natural_corpus_proven", False)),
            "external_accession_status": external_accession.get("accession_status"),
            "external_manifest_complete": bool(
                external_accession.get("manifest_complete", False)
            ),
            "external_compute_allowed": bool(external_accession.get("compute_allowed", False)),
            "production_proven": bool(production.get("production_proven", False)),
            "ungated_compute_allowed": bool(frontier.get("ungated_compute_allowed", False)),
            "broad_depth_search_allowed": bool(
                search.get("broad_depth_search_allowed", False)
            ),
            "format_promotion_allowed": bool(search.get("format_promotion_allowed", False)),
            "top_mechanism_lane": mechanism.get("top_lane_id"),
            "mechanism_closure_ready_compute_lanes": mechanism_closure.get(
                "ready_compute_lane_count"
            ),
            "mechanism_closure_top_blocked_lane": mechanism_closure.get(
                "top_blocked_lane"
            ),
            "next_mechanism_design_count": next_designs.get("design_count"),
            "next_mechanism_top_design": next_designs.get("top_design_id"),
            "frozen_rank_contract_status": frozen_rank.get("contract_status"),
            "frozen_rank_promotion_ready": frozen_rank.get("promotion_ready"),
            "frozen_rank_replay_allowed": frozen_rank.get("replay_allowed"),
            "frozen_rank_source_candidate_status": frozen_rank_sources.get(
                "candidate_status"
            ),
            "frozen_rank_source_candidates_ready_for_replay": frozen_rank_sources.get(
                "ready_for_replay_count"
            ),
            "streaming_economics_gate_status": streaming_gate.get("gate_status"),
            "streaming_economics_compute_reopen_allowed": streaming_gate.get(
                "compute_reopen_allowed"
            ),
            "bounded_streaming_memory_gate_status": bounded_memory.get("gate_status"),
            "bounded_streaming_memory_target_table_preflight": bounded_memory.get(
                "target_table_preflight_present"
            ),
            "objective_status": completion.get("objective_status"),
            "blocking_requirement_ids": completion.get("blocking_requirement_ids", []),
            "claim_boundary": (
                "No Seed Search; not natural-corpus proof; not production proof; "
                "not a compression claim."
            ),
            "conclusion": (
                "Keep exploring bounded mechanism hypotheses, but do not reopen broad "
                "compute or production promotion until generated gates move."
            ),
        },
        "dispatch_matrix": dispatch_matrix(hypotheses),
        "hypotheses": hypotheses,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Telomere Research Hypotheses",
        "",
        f"Generated by `{GENERATED_BY}` from the whitepaper, proof matrices, frontier gates, and dispatch ledgers.",
        "This is a No Seed Search hypothesis registry for dispatching-parallel-agents. It launches no agents, performs no seed search, is not natural-corpus proof, is not production proof, and is not a compression claim.",
        "",
        "## Summary",
        "",
        "Hypothesis Registry status: bounded, falsifiable, and evidence-pinned.",
        "",
        f"- Hypotheses: `{summary_payload['hypothesis_count']}`",
        f"- Parallel groups: `{summary_payload['parallel_group_count']}`",
        f"- Status counts: `{json.dumps(summary_payload['status_counts'], sort_keys=True)}`",
        f"- Top mechanism lane: `{summary_payload['top_mechanism_lane']}`",
        f"- Mechanism closure ready compute lanes: `{summary_payload['mechanism_closure_ready_compute_lanes']}`",
        f"- Mechanism closure top blocked lane: `{summary_payload['mechanism_closure_top_blocked_lane']}`",
        f"- Next mechanism designs: `{summary_payload['next_mechanism_design_count']}`",
        f"- Next mechanism top design: `{summary_payload['next_mechanism_top_design']}`",
        f"- Frozen rank contract status: `{summary_payload['frozen_rank_contract_status']}`",
        f"- Frozen rank promotion ready: `{summary_payload['frozen_rank_promotion_ready']}`",
        f"- Frozen rank replay allowed: `{summary_payload['frozen_rank_replay_allowed']}`",
        f"- Frozen rank source candidate status: `{summary_payload['frozen_rank_source_candidate_status']}`",
        f"- Frozen rank source candidates ready for replay: `{summary_payload['frozen_rank_source_candidates_ready_for_replay']}`",
        f"- Streaming economics gate status: `{summary_payload['streaming_economics_gate_status']}`",
        f"- Streaming economics compute reopen allowed: `{summary_payload['streaming_economics_compute_reopen_allowed']}`",
        f"- Bounded streaming memory gate status: `{summary_payload['bounded_streaming_memory_gate_status']}`",
        f"- Bounded streaming target-table preflight: `{summary_payload['bounded_streaming_memory_target_table_preflight']}`",
        f"- Natural-corpus proven: `{summary_payload['natural_corpus_proven']}`",
        f"- External accession status: `{summary_payload['external_accession_status']}`",
        f"- External manifest complete: `{summary_payload['external_manifest_complete']}`",
        f"- External compute allowed: `{summary_payload['external_compute_allowed']}`",
        f"- Production proven: `{summary_payload['production_proven']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Format promotion allowed: `{summary_payload['format_promotion_allowed']}`",
        f"- Blocking requirements: `{', '.join(summary_payload['blocking_requirement_ids'])}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Falsification Matrix",
        "",
        "| hypothesis | status | groups | falsification test | promotion trigger |",
        "| --- | --- | --- | --- | --- |",
    ]
    for hypothesis in payload["hypotheses"]:
        lines.append(
            f"| `{cell(hypothesis['hypothesis_id'])}` | `{cell(hypothesis['status'])}` | "
            f"{cell(', '.join(hypothesis['parallel_groups']))} | "
            f"{cell(hypothesis['falsification_test'])} | "
            f"{cell(hypothesis['promotion_trigger'])} |"
        )

    lines.extend(["", "## Promotion Triggers", ""])
    for hypothesis in payload["hypotheses"]:
        lines.append(
            f"- `{hypothesis['hypothesis_id']}`: {hypothesis['promotion_trigger']}"
        )

    lines.extend(["", "## Hypothesis Details", ""])
    for hypothesis in payload["hypotheses"]:
        lines.extend(
            [
                f"### {hypothesis['hypothesis_id']}",
                "",
                f"- Title: {hypothesis['title']}",
                f"- Status: `{hypothesis['status']}`",
                f"- Parallel groups: {', '.join(f'`{group}`' for group in hypothesis['parallel_groups'])}",
                f"- Whitepaper concept: {hypothesis['whitepaper_concept']}",
                f"- Best-case argument: {hypothesis['best_case_argument']}",
                f"- Current evidence: {hypothesis['current_evidence']}",
                f"- Falsification test: {hypothesis['falsification_test']}",
                f"- Promotion trigger: {hypothesis['promotion_trigger']}",
                f"- Stop rule: {hypothesis['stop_rule']}",
                f"- Suggested artifact: `{hypothesis['suggested_artifact']}`",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in hypothesis['source_artifacts'])}",
                "",
                "Dispatch prompt:",
                "",
                "```text",
                hypothesis["dispatch_prompt"],
                "```",
                "",
            ]
        )

    lines.extend(["## Dispatch Matrix", ""])
    for group, hypothesis_ids in payload["dispatch_matrix"].items():
        lines.append(f"- `{group}`: {', '.join(f'`{item}`' for item in hypothesis_ids)}")

    lines.extend(["", "## Global Forbidden Actions", ""])
    for action in COMMON_FORBIDDEN_ACTIONS:
        lines.append(f"- {action}")

    lines.extend(["", "## Output Contract", ""])
    for item in OUTPUT_CONTRACT:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this registry to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research hypothesis files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_hypotheses.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("research_hypotheses.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_hypotheses.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "is_production_proof",
        "overrides_search_frontier_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"research_hypotheses.json scope field must be false: {field}")
    hypotheses = payload.get("hypotheses", [])
    if len(hypotheses) < 12:
        raise SystemExit("research_hypotheses.json must contain at least 12 hypotheses")
    ids = [item.get("hypothesis_id") for item in hypotheses]
    if len(ids) != len(set(ids)):
        raise SystemExit("research_hypotheses.json hypothesis ids are not unique")
    if payload["summary"].get("external_compute_allowed"):
        raise SystemExit("research_hypotheses.json cannot allow external corpus compute")
    required_fields = {
        "hypothesis_id",
        "title",
        "status",
        "parallel_groups",
        "whitepaper_concept",
        "best_case_argument",
        "current_evidence",
        "falsification_test",
        "promotion_trigger",
        "stop_rule",
        "source_artifacts",
        "suggested_artifact",
        "forbidden_actions",
        "output_contract",
        "dispatch_prompt",
    }
    for hypothesis in hypotheses:
        if hypothesis.get("status") not in VALID_STATUSES:
            raise SystemExit(f"invalid hypothesis status: {hypothesis.get('status')}")
        missing = sorted(required_fields - set(hypothesis))
        if missing:
            raise SystemExit(f"{hypothesis.get('hypothesis_id')} missing fields: {missing}")
        prompt = hypothesis["dispatch_prompt"]
        for phrase in (
            "dispatching-parallel-agents",
            "No Seed Search",
            "not a compression claim",
            "not natural-corpus proof",
            "not production proof",
            "Falsification test",
            "Promotion trigger",
            "forbidden_actions",
            "output_contract",
        ):
            if phrase not in prompt:
                raise SystemExit(
                    f"hypothesis {hypothesis['hypothesis_id']} prompt missing phrase: {phrase}"
                )

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Research Hypotheses",
        "Hypothesis Registry",
        "dispatching-parallel-agents",
        "No Seed Search",
        "not natural-corpus proof",
        "not production proof",
        "Falsification Matrix",
        "Promotion Triggers",
        "Global Forbidden Actions",
        "Output Contract",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_HYPOTHESES.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated research hypotheses"
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
