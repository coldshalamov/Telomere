# Telomere Generated Evidence Pipelines

Large low-level JSON row matrices are build artifacts, not the source of truth
for the repo. Keep generator scripts, canonical Markdown summaries, and compact
evidence snapshots in git. The current UI reads
`docs/research_artifacts_snapshot.json`, not the raw generated ledgers.
Regenerate bulky matrices on demand when auditing a lane instead of checking
them in and forcing every future agent to maintain stale hashes.

Telomere now has two generated-artifact pipelines:

- `scripts/generate_evidence_regimen.py` is the full experiment/evidence
  regimen. It regenerates low-level result, transform, sidecar, search,
  economic, production, rollup, final hypothesis-registry, and research-team
  operating-packet artifacts in dependency order.
- `scripts/generate_research_ledgers.py` is the lightweight top-level rollup.
  It assumes the low-level artifacts are already current and only regenerates
  the research ledgers that consume them.

Use the full evidence regimen after changing a generator, generated source
artifact, format policy, search/sidecar/corpus logic, benchmark corpus,
transform lane, production proof input, or anything that can change artifact
hashes across multiple families.

Use the lightweight rollup after changing only the UI evidence panel, Tauri
research artifact DTO, research scorecard inputs, goal audit inputs, or blocked
requirement dispatch logic.

## Commands

- Regenerate the full evidence graph: `python scripts/generate_evidence_regimen.py`
- Check the full evidence graph: `python scripts/generate_evidence_regimen.py --check`
- Print the full evidence order: `python scripts/generate_evidence_regimen.py --print-plan`
- Resume a failed full run: `python scripts/generate_evidence_regimen.py --start-at <key>`
- Regenerate rollup ledgers only: `python scripts/generate_research_ledgers.py`
- Check rollup ledgers only: `python scripts/generate_research_ledgers.py --check`
- Print rollup order only: `python scripts/generate_research_ledgers.py --print-plan`
- Check the final hypothesis registry: `python scripts/generate_research_hypotheses.py --check`
- Check the public preset promotion gate: `python scripts/generate_public_preset_promotion_gate.py --check`
- Check the public preset control audit: `python scripts/generate_public_preset_control_audit.py --check`
- Check the public preset control ablation: `python scripts/generate_public_preset_control_ablation.py --check`
- Check the public preset ablation projection: `python scripts/generate_public_preset_ablation_projection.py --check`
- Check the public preset control rerun: `python scripts/generate_public_preset_control_rerun.py --check`
- Check the seed-table FASTA ablation: `python scripts/generate_seed_table_fasta_ablation.py --check`
- Check the mechanism closure audit: `python scripts/generate_mechanism_closure_audit.py --check`
- Check the next mechanism design registry: `python scripts/generate_next_mechanism_designs.py --check`
- Check the lattice selection held-out probe: `python scripts/generate_lattice_selection_heldout_probe.py --check`
- Check the natural corpus reopen manifest: `python scripts/generate_natural_corpus_reopen_manifest.py --check`
- Check the frozen rank source candidate matrix: `python scripts/generate_frozen_rank_source_candidates.py --check`
- Check the external corpus accession gate: `python scripts/generate_external_corpus_accession.py --check`
- Check the frozen rank-coded span generator contract: `python scripts/generate_frozen_rank_coded_span_generator.py --check`
- Check the bounded streaming memory gate: `python scripts/generate_bounded_streaming_memory_gate.py --check`
- Check the streaming economics gate: `python scripts/generate_streaming_economics_gate.py --check`
- Check the final research team packet: `python scripts/generate_research_team_packet.py --check`
- Check the research agent prompt pack: `python scripts/generate_research_agent_prompts.py --check`
- Check the research agent result intake: `python scripts/generate_research_agent_result_intake.py --check`
- Check the claim-boundary audit: `python scripts/generate_claim_boundary_audit.py --check`
- Full documentation gate: `python scripts/doc_lint.py`

## Full Evidence Regimen Order

Run `python scripts/generate_evidence_regimen.py --print-plan` for the
authoritative list. The order deliberately avoids stale-hash cycles by placing
shared prerequisites before the gates that hash them:

- baseline result and sweep artifacts
- transform probes and held-out validation
- corpus, sidecar, match-discovery, and selected-lead search artifacts
- theory, manifold, near-miss, prefix-ladder, depth-3, and fifth-byte artifacts
- depth-4, search-frontier, mechanism-ranking, preset/replay/FASTA-ablation/economics, dictionary,
  public-preset gate/control audit/ablation/projection/rerun, superposition,
  lattice-heldout, recursive, scale, bounded streaming memory, streaming economics, UI, acceleration, long-span gate, mechanism-closure,
  and next-mechanism design artifacts
- top-level research ledgers, the natural-corpus reopen manifest, the frozen
  rank source candidate matrix, the external corpus accession gate, the frozen
  rank-coded span generator contract, the final research hypothesis registry,
  and the research-team operating packet
- dispatch-ready research-agent prompt pack derived from the operating packet
- research-agent result-intake protocol derived from the prompt pack and empty
  report inbox, plus checked per-lane report templates with current prompt
  hashes
- final claim-boundary audit over public research docs and proof gates

`--start-at <key>` is intended for long runs. If a generator fails or is
interrupted, fix the issue and resume from the failed step's key rather than
rerunning the whole pipeline.

## Rollup Order

1. `scripts/generate_ui_workflow_smoke.py`
2. `scripts/generate_viability.py`
3. `scripts/generate_research_scorecard.py`
4. `scripts/generate_goal_audit.py`
5. `scripts/generate_experiment_queue.py`
6. `scripts/generate_research_decision.py`
7. `scripts/generate_research_frontier.py`
8. `scripts/generate_natural_corpus_proof_matrix.py`
9. `scripts/generate_production_proof_matrix.py`
10. `scripts/generate_research_team_protocol.py`
11. `scripts/generate_goal_completion_audit.py`
12. `scripts/generate_blocked_requirement_dispatch.py`

## Boundary

Neither pipeline promotes production claims. Both only rewrite or check
deterministic generated artifacts from checked-in source data. The full regimen
may run bounded deterministic evidence probes, including the slower fifth-byte,
whole-stream, and schema/preset lanes, but it does not authorize broad ungated
compute, recursive production claims, GPU trust, or natural-corpus viability
claims. The final hypothesis registry and team packet are No Seed Search
coordination artifacts: they launch no agents and only record bounded,
falsifiable research lanes, handoff contracts, and integration gates.
The result-intake protocol is the No Seed Search return path for future
subagent reports: it validates prompt hashes, source artifacts, stop rules, and
claim changes, and emits checked report templates with current prompt hashes,
but it does not integrate reports or authorize compute. The claim-boundary
audit is also No Seed Search: it authorizes no compute and only fails
unsupported positive claims while proof gates remain false.
