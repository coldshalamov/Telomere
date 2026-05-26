#!/usr/bin/env python3
"""Regenerate or check the full Telomere generated evidence regimen.

This is the source-of-truth order for generated experiment artifacts. It runs
the low-level evidence generators first, then the top-level research ledgers.
Use `scripts/generate_research_ledgers.py` only when low-level artifacts are
already current and only the rollup ledgers need to move.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EvidenceStep:
    key: str
    name: str
    group: str
    script: str
    reason: str


PIPELINE = [
    EvidenceStep(
        "results",
        "baseline result corpus",
        "baseline",
        "scripts/generate_results.py",
        "primary planted/random/repetitive result rows feed viability and theory",
    ),
    EvidenceStep(
        "sweeps",
        "depth-1/2 sweep matrix",
        "baseline",
        "scripts/generate_sweeps.py",
        "deep sweeps and theory consume the baseline sweep matrix",
    ),
    EvidenceStep(
        "deep-sweeps",
        "deep sweep matrix",
        "baseline",
        "scripts/generate_deep_sweeps.py",
        "theory and depth-frontier artifacts consume deeper sweep evidence",
    ),
    EvidenceStep(
        "transform-sweeps",
        "transform sweep matrix",
        "transform",
        "scripts/generate_transform_sweeps.py",
        "transform probes and manifold diagnostics consume transform sweep rows",
    ),
    EvidenceStep(
        "transform-probe",
        "bounded transform probe",
        "transform",
        "scripts/generate_transform_probe.py",
        "transform validation consumes the selected transform probe manifest",
    ),
    EvidenceStep(
        "transform-validation",
        "held-out transform validation",
        "transform",
        "scripts/generate_transform_validation.py",
        "periodic, composed, held-out, forecast, and proof matrices consume this validation ledger",
    ),
    EvidenceStep(
        "periodic-transform",
        "periodic transform probe",
        "transform",
        "scripts/generate_periodic_transform_probe.py",
        "composed transforms and near-miss forecast consume periodic candidates",
    ),
    EvidenceStep(
        "composed-transform",
        "composed transform probe",
        "transform",
        "scripts/generate_composed_transform_probe.py",
        "near-miss forecast and fifth-byte residual analysis consume composed candidates",
    ),
    EvidenceStep(
        "corpus-matrix",
        "corpus matrix",
        "corpus",
        "scripts/generate_corpus_matrix.py",
        "generalization, sidecar, preset, theory, and manifold lanes consume corpus rows",
    ),
    EvidenceStep(
        "corpus-generalization",
        "corpus generalization probe",
        "corpus",
        "scripts/generate_corpus_generalization_probe.py",
        "seed-table and scorecard lanes consume corpus generalization evidence",
    ),
    EvidenceStep(
        "structural-transform",
        "structural transform search",
        "transform",
        "scripts/generate_structural_transform_search.py",
        "mechanism ranking consumes bounded structural transform status",
    ),
    EvidenceStep(
        "byte-permutation",
        "byte permutation transform search",
        "transform",
        "scripts/generate_byte_permutation_transform_search.py",
        "mechanism ranking consumes byte-distribution alignment status",
    ),
    EvidenceStep(
        "bwt-mtf",
        "BWT/MTF transform probe",
        "transform",
        "scripts/generate_bwt_mtf_transform_probe.py",
        "mechanism ranking consumes classic preconditioner status",
    ),
    EvidenceStep(
        "grammar-channel",
        "grammar channel match discovery",
        "channel",
        "scripts/generate_grammar_channel_match_discovery.py",
        "goal audit and mechanism ranking consume grammar-channel exact-hit evidence",
    ),
    EvidenceStep(
        "numeric-channel",
        "numeric value channel match discovery",
        "channel",
        "scripts/generate_numeric_value_channel_match_discovery.py",
        "mechanism ranking consumes parsed numeric-channel evidence",
    ),
    EvidenceStep(
        "record-context",
        "record context transform search",
        "channel",
        "scripts/generate_record_context_transform_search.py",
        "mechanism ranking consumes record/context transform evidence",
    ),
    EvidenceStep(
        "token-dictionary",
        "token dictionary transform search",
        "channel",
        "scripts/generate_token_dictionary_transform_search.py",
        "mechanism ranking consumes token/dictionary transform evidence",
    ),
    EvidenceStep(
        "affine-transform",
        "affine transform search",
        "transform",
        "scripts/generate_affine_transform_search.py",
        "residual sidecar and mechanism ranking consume affine steering evidence",
    ),
    EvidenceStep(
        "seed-manifold-residual",
        "seed manifold residual steering",
        "sidecar",
        "scripts/generate_seed_manifold_residual_steering.py",
        "sidecar break-even and residual payload probes consume residual steering rows",
    ),
    EvidenceStep(
        "sidecar-break-even",
        "sidecar break-even rules",
        "sidecar",
        "scripts/generate_sidecar_break_even.py",
        "residual payload, packed sidecar, and long-span gates consume sidecar economics",
    ),
    EvidenceStep(
        "residual-payload",
        "residual payload compressibility",
        "sidecar",
        "scripts/generate_residual_payload_compressibility.py",
        "mechanism ranking consumes residual payload feasibility",
    ),
    EvidenceStep(
        "experimental-sidecar",
        "experimental sidecar descriptor",
        "sidecar",
        "scripts/generate_experimental_sidecar_descriptor.py",
        "packed sidecar descriptor consumes the experimental descriptor baseline",
    ),
    EvidenceStep(
        "sidecar-record-overhead",
        "sidecar record overhead",
        "sidecar",
        "scripts/generate_sidecar_record_overhead.py",
        "packed sidecar descriptor consumes explicit record overhead accounting",
    ),
    EvidenceStep(
        "packed-sidecar-descriptor",
        "packed sidecar descriptor",
        "sidecar",
        "scripts/generate_packed_sidecar_descriptor.py",
        "packed controls consume descriptor packing evidence",
    ),
    EvidenceStep(
        "packed-sidecar-controls",
        "packed sidecar controls",
        "sidecar",
        "scripts/generate_packed_sidecar_controls.py",
        "generalized and replication lanes consume sidecar control evidence",
    ),
    EvidenceStep(
        "generalized-packed-sidecar",
        "generalized packed sidecar",
        "sidecar",
        "scripts/generate_generalized_packed_sidecar.py",
        "replication consumes generalized descriptor evidence",
    ),
    EvidenceStep(
        "packed-sidecar-replication",
        "packed sidecar replication",
        "sidecar",
        "scripts/generate_packed_sidecar_replication.py",
        "held-out expansion and long-span gates consume replicated sidecar evidence",
    ),
    EvidenceStep(
        "heldout-expansion",
        "held-out corpus expansion",
        "corpus",
        "scripts/generate_heldout_corpus_expansion.py",
        "match discovery and natural-corpus proof consume held-out corpus coverage",
    ),
    EvidenceStep(
        "match-discovery",
        "raw match discovery",
        "search",
        "scripts/generate_match_discovery.py",
        "alignment, transformed match, search frontier, and proof matrices consume raw exact-match evidence",
    ),
    EvidenceStep(
        "alignment-arity",
        "alignment and arity discovery",
        "search",
        "scripts/generate_alignment_arity_discovery.py",
        "search frontier and long-span gates consume alignment sensitivity evidence",
    ),
    EvidenceStep(
        "transformed-match",
        "transformed match discovery",
        "search",
        "scripts/generate_transformed_match_discovery.py",
        "lead exact discovery consumes transformed exact-match evidence",
    ),
    EvidenceStep(
        "lead-exact",
        "selected-lead exact discovery",
        "search",
        "scripts/generate_lead_exact_discovery.py",
        "lead depth-3, search frontier, and long-span gates consume selected-lead evidence",
    ),
    EvidenceStep(
        "lead-depth3-prefix",
        "selected-lead depth-3 prefix probe",
        "search",
        "scripts/generate_lead_depth3_prefix_probe.py",
        "selected-lead compression follow-up consumes depth-3 prefix movement",
    ),
    EvidenceStep(
        "lead-depth3-followup",
        "selected-lead depth-3 compression follow-up",
        "search",
        "scripts/generate_lead_depth3_compression_followup.py",
        "search frontier consumes selected-lead depth-3 compression evidence",
    ),
    EvidenceStep(
        "depth3-frontier",
        "depth-3 frontier exact discovery",
        "search",
        "scripts/generate_depth3_frontier_exact_discovery.py",
        "depth-4 shard planning consumes full depth-3 frontier rates",
    ),
    EvidenceStep(
        "theory",
        "theory report",
        "analysis",
        "scripts/generate_theory_report.py",
        "depth-4 shard planning and scorecards consume expectation math",
    ),
    EvidenceStep(
        "manifold",
        "seed-output manifold diagnostics",
        "analysis",
        "scripts/generate_manifold_report.py",
        "near-miss forecast and fifth-byte residuals consume manifold proximity data",
    ),
    EvidenceStep(
        "nearmiss",
        "near-miss forecast",
        "analysis",
        "scripts/generate_nearmiss_forecast.py",
        "depth-4 shard planning, search frontier, and proof matrices consume forecast scale",
    ),
    EvidenceStep(
        "prefix-ladder",
        "prefix ladder",
        "analysis",
        "scripts/generate_prefix_ladder.py",
        "depth-3 prefix and fifth-byte residual probes consume prefix-ladder rows",
    ),
    EvidenceStep(
        "depth3-prefix",
        "depth-3 prefix probe",
        "search",
        "scripts/generate_depth3_prefix_probe.py",
        "depth-3 compression follow-up and search frontier consume prefix probe rows",
    ),
    EvidenceStep(
        "depth3-followup",
        "depth-3 compression follow-up",
        "search",
        "scripts/generate_depth3_compression_followup.py",
        "search frontier consumes depth-3 compression evidence",
    ),
    EvidenceStep(
        "fifth-byte-residual",
        "fifth-byte residual analysis",
        "analysis",
        "scripts/generate_fifth_byte_residual.py",
        "fifth-byte steering consumes prefix-4 residual diagnostics",
    ),
    EvidenceStep(
        "fifth-byte-steering",
        "fifth-byte steering",
        "analysis",
        "scripts/generate_fifth_byte_steering.py",
        "contextual steering and mechanism ranking consume fifth-byte masks",
    ),
    EvidenceStep(
        "contextual-fifth-byte",
        "contextual fifth-byte steering",
        "analysis",
        "scripts/generate_contextual_fifth_byte_steering.py",
        "mechanism ranking consumes contextual fifth-byte evidence",
    ),
    EvidenceStep(
        "depth4-shard-plan",
        "depth-4 shard plan",
        "search",
        "scripts/generate_depth4_shard_plan.py",
        "depth-4 pilot shard consumes the stable shard plan",
    ),
    EvidenceStep(
        "depth4-pilot",
        "depth-4 pilot shard",
        "search",
        "scripts/generate_depth4_pilot_shard.py",
        "search frontier consumes bounded depth-4 pilot evidence",
    ),
    EvidenceStep(
        "search-frontier",
        "search frontier gate",
        "gate",
        "scripts/generate_search_frontier_gate.py",
        "mechanism ranking, seed-table probe, and proof matrices consume broad-search go/no-go state",
    ),
    EvidenceStep(
        "mechanism-ranking",
        "mechanism experiment ranking",
        "gate",
        "scripts/generate_mechanism_experiment_ranking.py",
        "seed-table probe and scorecards consume ranked mechanism lanes",
    ),
    EvidenceStep(
        "seed-table-preset",
        "seed-table preset probe",
        "preset",
        "scripts/generate_seed_table_preset_probe.py",
        "short-hit economics and long-span gates consume preset evidence",
    ),
    EvidenceStep(
        "seed-table-preset-replay",
        "seed-table preset replay",
        "preset",
        "scripts/generate_seed_table_preset_replay.py",
        "hypotheses consume bounded leave-corpus-out preset replay evidence after the parent preset probe",
    ),
    EvidenceStep(
        "seed-table-fasta-ablation",
        "seed-table FASTA ablation",
        "preset",
        "scripts/generate_seed_table_fasta_ablation.py",
        "hypotheses consume FASTA header-vs-sequence attribution after replay finds the sequence-fasta signal",
    ),
    EvidenceStep(
        "exact-short-economics",
        "exact short-hit bundle economics",
        "economics",
        "scripts/generate_exact_short_hit_bundle_economics.py",
        "whole-stream residual and long-span gates consume short-hit economics",
    ),
    EvidenceStep(
        "whole-stream-residual",
        "whole-stream residual vector probe",
        "economics",
        "scripts/generate_whole_stream_residual_vector_probe.py",
        "salt, dictionary, scale, and long-span gates consume full-stream residual evidence",
    ),
    EvidenceStep(
        "expander-salt",
        "expander salt ensemble",
        "economics",
        "scripts/generate_expander_salt_ensemble.py",
        "scorecards consume salted-expander falsification evidence",
    ),
    EvidenceStep(
        "schema-native",
        "schema-native public dictionaries",
        "dictionary",
        "scripts/generate_schema_native_public_dictionaries.py",
        "replication consumes schema-native dictionary evidence",
    ),
    EvidenceStep(
        "schema-replication",
        "schema-native dictionary replication",
        "dictionary",
        "scripts/generate_schema_native_public_dictionary_replication.py",
        "superposition, scorecard, and long-span gates consume dictionary replication",
    ),
    EvidenceStep(
        "public-preset-gate",
        "public preset promotion gate",
        "dictionary",
        "scripts/generate_public_preset_promotion_gate.py",
        "hypotheses and team packets consume the consolidated public-preset go/no-go gate",
    ),
    EvidenceStep(
        "public-preset-control-audit",
        "public preset control audit",
        "dictionary",
        "scripts/generate_public_preset_control_audit.py",
        "hypotheses and team packets consume the paired-shadow/control-separation audit",
    ),
    EvidenceStep(
        "public-preset-control-ablation",
        "public preset control ablation",
        "dictionary",
        "scripts/generate_public_preset_control_ablation.py",
        "hypotheses and team packets consume the pre-registered public-preset control ablation manifest",
    ),
    EvidenceStep(
        "public-preset-ablation-projection",
        "public preset ablation projection",
        "dictionary",
        "scripts/generate_public_preset_ablation_projection.py",
        "hypotheses and team packets consume read-only public-preset ablation projections before exact reruns",
    ),
    EvidenceStep(
        "public-preset-control-rerun",
        "public preset control rerun",
        "dictionary",
        "scripts/generate_public_preset_control_rerun.py",
        "hypotheses and team packets consume exact bounded public-preset rerun results after projections",
    ),
    EvidenceStep(
        "superposition-telemetry",
        "superposition telemetry",
        "candidate-model",
        "scripts/generate_superposition_telemetry.py",
        "scorecards and UI consume candidate-lattice telemetry",
    ),
    EvidenceStep(
        "lattice-heldout-probe",
        "lattice selection held-out probe",
        "candidate-model",
        "scripts/generate_lattice_selection_heldout_probe.py",
        "hypotheses and team packets consume held-out candidate-lattice utility results",
    ),
    EvidenceStep(
        "recursive-structured",
        "recursive structured fixtures",
        "candidate-model",
        "scripts/generate_recursive_structured_fixtures.py",
        "scale, scorecard, and UI consume recursive v2 fixture evidence",
    ),
    EvidenceStep(
        "scale-performance",
        "scale performance",
        "production",
        "scripts/generate_scale_performance_report.py",
        "production proof consumes current memory-scale evidence",
    ),
    EvidenceStep(
        "bounded-streaming-memory-gate",
        "bounded streaming memory gate",
        "production",
        "scripts/generate_bounded_streaming_memory_gate.py",
        "streaming economics and production boundaries consume v2 memory-limit preflight status",
    ),
    EvidenceStep(
        "streaming-economics-gate",
        "streaming economics gate",
        "production",
        "scripts/generate_streaming_economics_gate.py",
        "hypotheses and production boundaries consume streaming parity, planted scale, and search-frontier status",
    ),
    EvidenceStep(
        "ui-workflow",
        "UI workflow smoke",
        "production",
        "scripts/generate_ui_workflow_smoke.py",
        "production proof and operator workflow consume UI/Tauri DTO coverage",
    ),
    EvidenceStep(
        "acceleration",
        "acceleration report",
        "production",
        "scripts/generate_acceleration_report.py",
        "production proof consumes CPU/GPU acceleration boundary evidence",
    ),
    EvidenceStep(
        "long-span-gate",
        "long-span bundle gate",
        "gate",
        "scripts/generate_long_span_bundle_gate.py",
        "research frontier and natural-corpus proof consume long-span go/no-go state",
    ),
    EvidenceStep(
        "mechanism-closure-audit",
        "mechanism closure audit",
        "gate",
        "scripts/generate_mechanism_closure_audit.py",
        "rollups consume post-experiment lane closure after all bounded mechanism artifacts have run",
    ),
    EvidenceStep(
        "next-mechanism-designs",
        "next mechanism designs",
        "design",
        "scripts/generate_next_mechanism_designs.py",
        "hypotheses consume pre-registered new byte-to-seed mechanism designs after closure",
    ),
    EvidenceStep(
        "research-ledgers",
        "top-level research ledgers",
        "rollup",
        "scripts/generate_research_ledgers.py",
        "final rollup produces viability, scorecard, queue, proof matrices, team protocol, and completion audit",
    ),
    EvidenceStep(
        "natural-corpus-reopen-manifest",
        "natural corpus reopen manifest",
        "rollup",
        "scripts/generate_natural_corpus_reopen_manifest.py",
        "hypotheses and team packets consume the pre-registered natural-corpus reopen rules after rollup ledgers",
    ),
    EvidenceStep(
        "frozen-rank-source-candidates",
        "frozen rank source candidate requirements",
        "design",
        "scripts/generate_frozen_rank_source_candidates.py",
        "external accession consumes the rank-table source acquisition matrix before any payload accession or replay",
    ),
    EvidenceStep(
        "external-corpus-accession",
        "external corpus accession ledger",
        "rollup",
        "scripts/generate_external_corpus_accession.py",
        "hypotheses and team packets consume checked external corpus provenance and paired-control readiness",
    ),
    EvidenceStep(
        "frozen-rank-coded-span-generator",
        "frozen rank-coded span generator contract",
        "design",
        "scripts/generate_frozen_rank_coded_span_generator.py",
        "hypotheses consume the top next-mechanism design's manifest/spec/golden-vector contract after accession gates",
    ),
    EvidenceStep(
        "research-hypotheses",
        "research hypothesis registry",
        "rollup",
        "scripts/generate_research_hypotheses.py",
        "final whitepaper/evidence hypothesis registry consumes proof matrices and dispatch ledgers",
    ),
    EvidenceStep(
        "research-team-packet",
        "research team operating packet",
        "rollup",
        "scripts/generate_research_team_packet.py",
        "final operating roster consumes hypotheses, team briefs, and blocked-requirement dispatch",
    ),
    EvidenceStep(
        "research-agent-prompts",
        "research agent prompt pack",
        "rollup",
        "scripts/generate_research_agent_prompts.py",
        "dispatch-ready prompt pack consumes the final operating roster without launching agents",
    ),
    EvidenceStep(
        "research-agent-result-intake",
        "research agent result intake",
        "rollup",
        "scripts/generate_research_agent_result_intake.py",
        "result intake consumes dispatch-ready prompts and keeps future agent returns auditable before integration",
    ),
    EvidenceStep(
        "claim-boundary-audit",
        "claim boundary audit",
        "rollup",
        "scripts/generate_claim_boundary_audit.py",
        "final documentation safety rail consumes proof gates and public research docs",
    ),
]


def selected_pipeline(start_at: str | None) -> list[EvidenceStep]:
    if start_at is None:
        return PIPELINE
    keys = {step.key for step in PIPELINE}
    if start_at not in keys:
        raise SystemExit(f"unknown --start-at key: {start_at}")
    start_index = next(index for index, step in enumerate(PIPELINE) if step.key == start_at)
    return PIPELINE[start_index:]


def run_step(step: EvidenceStep, check: bool) -> dict[str, object]:
    command = [sys.executable, str(ROOT / step.script)]
    if check:
        command.append("--check")
    started = datetime.now(timezone.utc)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    finished = datetime.now(timezone.utc)
    return {
        "key": step.key,
        "name": step.name,
        "group": step.group,
        "script": step.script,
        "mode": "check" if check else "generate",
        "returncode": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
    }


def print_plan(steps: list[EvidenceStep]) -> None:
    for index, step in enumerate(steps, start=1):
        print(f"{index}. [{step.group}] {step.key}: {step.script}")
        print(f"   {step.reason}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run every evidence generator in check mode instead of rewriting artifacts",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a JSON execution report",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="print the full dependency order without running commands",
    )
    parser.add_argument(
        "--start-at",
        metavar="KEY",
        help="start at a pipeline key printed by --print-plan; useful after a failed long run",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    steps = selected_pipeline(args.start_at)
    if args.print_plan:
        if args.json:
            print(json.dumps([asdict(step) for step in steps], indent=2))
        else:
            print_plan(steps)
        return

    report = []
    for step in steps:
        result = run_step(step, args.check)
        report.append(result)
        if result["returncode"] != 0:
            if args.json:
                print(json.dumps(report, indent=2))
            raise SystemExit(
                f"{step.script} failed in {result['mode']} mode "
                f"with exit code {result['returncode']}. "
                f"Resume with --start-at {step.key} after fixing the failure."
            )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "check" if args.check else "generate"
        print(f"Evidence regimen {mode} pipeline passed ({len(report)} steps).")


if __name__ == "__main__":
    main()
