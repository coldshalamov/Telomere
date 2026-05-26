# Production Release Checklist

Telomere is not production-ready until every item below is true for the release
candidate.

## Format Support

- Supported file format is documented in `docs/FORMAT.md`.
- `format_version` is fixed for the release.
- `lotus_preset` is fixed for the release.
- Seed enumeration order is unchanged.
- Golden byte-vector tests pass for the file header, Lotus arity/literal fields,
  and seed index boundaries.

## Compatibility Guarantees

- The release states whether it can read previous `.tlmr` versions.
- The release states whether files written by this version are guaranteed to be
  readable by future versions.
- Any incompatible change bumps `format_version`.
- Any Lotus record change bumps `lotus_preset`.
- Any hasher semantic change gets a new `hasher_kind` id.
- Any transform/preconditioner support requires a versioned transform descriptor
  or a new file format version; external transform experiments are not release
  format support.

## Current Compatibility Policy

- `.tlmr` v1 is the only production-supported format for the current release
  candidate.
- `.tlmr` v2 is experimental: it can be decoded by the current repo, but it is
  not a long-term compatibility promise.
- Pre-v1 experimental headers are unsupported unless a standalone migration
  tool explicitly recognizes and rewrites them.
- Future production releases must keep v1 decode support or provide a
  standalone migration tool before removing it.

## Known Limitations

- `.tlmr` v1 is one-layer-decodable only.
- Recursive multi-pass output is supported only for indexed/streaming `.tlmr`
  v2 files.
- Random data is expected to bloat.
- Seed depth 3 is expensive and not used in normal tests.
- GPU is research-only and not a production acceleration path.
- v2 index building is CPU/RAM oriented; GPU/ASIC streaming lookup remains
  research-only.
- Transform/preconditioner sweeps are research-only unless a release explicitly
  documents transform metadata, inverse decoding, and dictionary identity.

## Migration Rules

- Do not silently reinterpret old headers.
- Pre-v1 experimental headers are unsupported by the production decoder unless
  a standalone migration tool explicitly recognizes and rewrites them.
- Reject newer unsupported `format_version` values.
- Reject unsupported `lotus_preset` values.
- Preserve hasher metadata during any rewrite.
- Provide a standalone migration tool before changing existing file semantics.

## Verification Gates

Run all of these before a release tag:

```powershell
cargo fmt --all -- --check
cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
cargo check --manifest-path src-tauri/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml
python scripts/doc_lint.py
python scripts/generate_candidate_runtime_verification.py
python scripts/generate_candidate_runtime_verification.py --check
python scripts/generate_evidence_regimen.py --check
python scripts/generate_research_ledgers.py --check
python scripts/generate_results.py --check
python scripts/generate_sweeps.py --check
python scripts/generate_deep_sweeps.py --check
python scripts/generate_transform_sweeps.py --check
python scripts/generate_transform_probe.py --check
python scripts/generate_transform_validation.py --check
python scripts/generate_periodic_transform_probe.py --check
python scripts/generate_composed_transform_probe.py --check
python scripts/generate_corpus_matrix.py --check
python scripts/generate_corpus_generalization_probe.py --check
python scripts/generate_structural_transform_search.py --check
python scripts/generate_byte_permutation_transform_search.py --check
python scripts/generate_bwt_mtf_transform_probe.py --check
python scripts/generate_grammar_channel_match_discovery.py --check
python scripts/generate_numeric_value_channel_match_discovery.py --check
python scripts/generate_record_context_transform_search.py --check
python scripts/generate_token_dictionary_transform_search.py --check
python scripts/generate_affine_transform_search.py --check
python scripts/generate_seed_manifold_residual_steering.py --check
python scripts/generate_sidecar_break_even.py --check
python scripts/generate_residual_payload_compressibility.py --check
python scripts/generate_experimental_sidecar_descriptor.py --check
python scripts/generate_sidecar_record_overhead.py --check
python scripts/generate_packed_sidecar_descriptor.py --check
python scripts/generate_packed_sidecar_controls.py --check
python scripts/generate_generalized_packed_sidecar.py --check
python scripts/generate_packed_sidecar_replication.py --check
python scripts/generate_heldout_corpus_expansion.py --check
python scripts/generate_match_discovery.py --check
python scripts/generate_alignment_arity_discovery.py --check
python scripts/generate_transformed_match_discovery.py --check
python scripts/generate_lead_exact_discovery.py --check
python scripts/generate_lead_depth3_prefix_probe.py --check
python scripts/generate_lead_depth3_compression_followup.py --check
python scripts/generate_depth3_frontier_exact_discovery.py --check
python scripts/generate_depth4_shard_plan.py --check
python scripts/generate_depth4_pilot_shard.py --check
python scripts/generate_search_frontier_gate.py --check
python scripts/generate_long_span_bundle_gate.py --check
python scripts/generate_mechanism_experiment_ranking.py --check
python scripts/generate_seed_table_preset_probe.py --check
python scripts/generate_public_preset_promotion_gate.py --check
python scripts/generate_public_preset_control_audit.py --check
python scripts/generate_public_preset_control_ablation.py --check
python scripts/generate_public_preset_ablation_projection.py --check
python scripts/generate_public_preset_control_rerun.py --check
python scripts/generate_exact_short_hit_bundle_economics.py --check
python scripts/generate_whole_stream_residual_vector_probe.py --check
python scripts/generate_expander_salt_ensemble.py --check
python scripts/generate_schema_native_public_dictionaries.py --check
python scripts/generate_schema_native_public_dictionary_replication.py --check
python scripts/generate_superposition_telemetry.py --check
python scripts/generate_lattice_selection_heldout_probe.py --check
python scripts/generate_recursive_structured_fixtures.py --check
python scripts/generate_scale_performance_report.py --check
python scripts/generate_bounded_streaming_memory_gate.py --check
python scripts/generate_streaming_economics_gate.py --check
python scripts/generate_ui_workflow_smoke.py --check
python scripts/generate_acceleration_report.py --check
python scripts/generate_theory_report.py --check
python scripts/generate_manifold_report.py --check
python scripts/generate_nearmiss_forecast.py --check
python scripts/generate_prefix_ladder.py --check
python scripts/generate_depth3_prefix_probe.py --check
python scripts/generate_depth3_compression_followup.py --check
python scripts/generate_fifth_byte_residual.py --check
python scripts/generate_fifth_byte_steering.py --check
python scripts/generate_contextual_fifth_byte_steering.py --check
python scripts/generate_viability.py --check
python scripts/generate_research_scorecard.py --check
python scripts/generate_goal_audit.py --check
python scripts/generate_experiment_queue.py --check
python scripts/generate_research_decision.py --check
python scripts/generate_research_frontier.py --check
python scripts/generate_natural_corpus_proof_matrix.py --check
python scripts/generate_natural_corpus_reopen_manifest.py --check
python scripts/generate_frozen_rank_source_candidates.py --check
python scripts/generate_external_corpus_accession.py --check
python scripts/generate_frozen_rank_coded_span_generator.py --check
python scripts/generate_candidate_runtime_verification.py --check
python scripts/generate_production_proof_matrix.py --check
python scripts/generate_research_team_protocol.py --check
python scripts/generate_goal_completion_audit.py --check
python scripts/generate_blocked_requirement_dispatch.py --check
python scripts/generate_research_hypotheses.py --check
python scripts/generate_research_team_packet.py --check
python scripts/generate_research_agent_prompts.py --check
python scripts/generate_research_agent_result_intake.py --check
python scripts/generate_claim_boundary_audit.py --check
```

## Artifact Regeneration

If any generated artifact is stale, regenerate in dependency order, inspect the
diffs, then rerun the verification gates above. Prefer the full evidence
regimen unless you know only top-level rollup artifacts changed:

```powershell
python scripts/generate_evidence_regimen.py
```

If a long run fails after several slow probes, resume from the failing key
printed in the error:

```powershell
python scripts/generate_evidence_regimen.py --start-at <key>
```

Print the authoritative order before manual review or partial reruns:

```powershell
python scripts/generate_evidence_regimen.py --print-plan
```

`scripts/generate_evidence_regimen.py` is the authoritative full generated
evidence order. It runs low-level result, transform, corpus, sidecar, search,
economics, production, and rollup generators in dependency order.

`scripts/generate_research_ledgers.py` is the authoritative top-level rollup
order for `ui_workflow_smoke`, `viability`, `research_scorecard`, `goal_audit`,
`experiment_queue`, `research_decision`, `research_frontier`,
`natural_corpus_proof_matrix`, `production_proof_matrix`,
`research_team_protocol`, `goal_completion_audit`, and
`blocked_requirement_dispatch`. The full evidence regimen also emits
`frozen_rank_source_candidates` as the no-payload rank-table acquisition
matrix,
`external_corpus_accession` as the checked external natural-corpus ingress gate,
`frozen_rank_coded_span_generator` as the top next-mechanism
manifest/spec/golden-vector contract,
`public_preset_promotion_gate` as the consolidated public-preset go/no-go gate,
`public_preset_control_audit` as the paired-shadow/control-separation audit,
`public_preset_control_ablation` as the pre-registered public-preset control
ablation matrix,
`public_preset_ablation_projection` as the read-only pre-rerun projection,
`research_hypotheses` as a final whitepaper/evidence hypothesis registry, and
`research_team_packet` as the final operating roster. It then emits
`research_agent_prompts` as the dispatch-ready prompt pack,
`research_agent_result_intake` as the checked return path for future subagent
reports plus per-lane report templates with current prompt hashes, and finishes
with `claim_boundary_audit` as the documentation safety rail for unsupported
natural-corpus, production, broad-compute, format-promotion, random-data, and
universal-compressor claims.

`scripts/generate_candidate_runtime_verification.py` is deliberately outside
the generated evidence regimen because it runs the release commands and stores
their logs. Run it after generated artifacts are current and before treating
`docs/PRODUCTION_PROOF_MATRIX.md` as release-candidate evidence.

After regenerating, inspect all generated artifact diffs, especially
`docs/RESULTS.md`, `docs/results.json`, generated research ledgers, and any
hash-only changes before committing them.
