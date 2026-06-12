# Telomere Research Program

This document is the operating plan for evaluating Telomere as a compression
research project. It is deliberately stricter than the whitepaper: every claim
must become a generated result, a passing test, a reproducible benchmark, or a
clearly labeled hypothesis.

## Core Thesis To Test

Best-case Telomere is an on-demand deterministic codebook search. A short seed
plus a Lotus record can replace a longer target span when the selected hasher
expansion reproduces the target bytes exactly. Arity lets one seed cover more
than one block. Recursive v2 layers let the next pass search a changed byte
landscape after selected replacements and literals are encoded.

The important idea is not that every input gets smaller. The important idea is
that the engine can search a larger deterministic generative space than ordinary
local pattern coders, while preserving lossless verification and literal
fallback. Viability depends on whether real or transformed corpora contain
enough short-seed spans to beat record overhead at an acceptable compute cost.

## Non-Negotiable Constraints

- Telomere is lossless and must always decode without compression-time indexes.
- Random controls are expected to bloat.
- Negative delta claims require generated artifacts, not prose.
- The header-selected hasher is authoritative.
- Seed enumeration order is consensus-critical.
- v1 remains one-layer-decodable.
- v2 is the only recursive format surface.
- A match is valid only when `expand(seed)[0..span_len] == target_span`.
- Digest-prefix matching of `hash(target_span)` to `hash(seed)` is not the
  architecture.

## Evidence Ladder

| Level | Question | Required artifact |
| --- | --- | --- |
| 0 | Does the codec roundtrip safely? | Golden vectors, corrupt-input tests, cross-hasher tests |
| 1 | Can the mechanism shrink planted data? | Generated planted corpus results with negative delta |
| 2 | Does indexed lookup equal brute semantics on small fixtures? | Parity tests and generated result rows |
| 3 | Does streaming amortize seed expansion across span tiers? | Streaming telemetry, candidate counts, seeds/sec |
| 4 | Do arity and span length improve selected savings? | Arity and `max_span_len` sweeps |
| 5 | Do recursive v2 passes help beyond first-pass wins? | Pass-count sweeps with layer descriptors and hashes |
| 6 | Do structured real corpora produce repeatable wins? | Corpus matrix with random and compressed controls |
| 7 | Is the cost curve useful for archival workloads? | CPU time, memory, energy estimate, throughput envelope |

Do not claim a higher level until the lower levels are green and reproducible.

## Research Lanes

| Lane | Objective | Main artifacts | Acceptance criteria |
| --- | --- | --- | --- |
| Theory | Model hit probability, record overhead, and recursion limits | `docs/RESEARCH_PROGRAM.md`, formulas, falsification notes | Claims are phrased as hypotheses unless measured |
| Format | Keep `.tlmr` v1/v2 decode unambiguous | `docs/FORMAT.md`, golden vectors, corrupt tests | Files decode without indexes and reject stale metadata |
| Engine | Build indexed and streaming search correctly | `src/indexed.rs`, `src/streaming.rs`, tests | Streaming/indexed hits verify exact bytes |
| Candidate selection | Preserve valid alternatives until deterministic selection | selector tests, telemetry | Weighted interval selection beats greedy overlaps on fixtures |
| Benchmark science | Generate all results from scripts | `scripts/generate_results.py`, `docs/results.json` | No hand-written benchmark claims |
| Recursion | Measure whether layer transforms create new opportunities | `scripts/generate_sweeps.py`, `docs/sweeps.json` | Later recursive layers are smaller than their inputs and every layer is independently verified |
| Systems | Decide CPU/GPU/ASIC feasibility honestly | CPU baseline, GPU parity tests if GPU stays | GPU is not trusted without CPU parity |
| Operator UX | Make experiments visible and repeatable | Tauri commands, telemetry views | UI exposes real engine data, not mock claims |

## Experiment Matrix

| Experiment | Corpus | Sweep | Expected interpretation |
| --- | --- | --- | --- |
| Random null | Deterministic pseudorandom bytes | size, hasher, block size | Should bloat; any shrink needs investigation |
| Planted arity | Repeated generated spans from known seeds | arity `1..=5`, seed depth 1 | Proves mechanism and selector behavior |
| Planted offset | Generated spans shifted across block boundaries | block size, offset | Shows how rigid block alignment hurts or helps |
| Span-step alignment | Offset planted spans under finer candidate grids | `span_step`, offset | Measures whether sub-block search recovers first-pass opportunities |
| Seed-depth economics | Two-byte planted spans and structured controls | seed depth `1..=2` now, later `3` | Separates "more compute finds more" from natural-corpus usefulness |
| Indexed parity | Small planted fixtures | brute vs indexed | Indexed must match exact generated-prefix semantics |
| Streaming parity | Small planted fixtures | brute/indexed/streaming | Streaming must not hash target spans before lookup |
| Selector stress | Overlapping candidates | greedy vs weighted | Weighted selector should pick higher total savings |
| Recursive v2 | Planted and structured corpora | passes `1..=N` | Measures whether layer outputs create new wins |
| Structured text | Markdown, JSON, source code, configs, logs, markup | seed depth, arity, block size | Tests non-planted but structured inputs |
| Binary controls | PDF, images, already-compressed archives | seed depth 1, streaming | Establishes honest bloat or tiny-control behavior |
| Kolyma symbolic | `kolyma.pdf` | streaming control, later bounded sweeps | Treated as a ceremony/control corpus, not a spec |
| Hasher separation | Same file under BLAKE3 and SHA-256 | decode with header metadata | Cross-hasher files are not interchangeable |
| Memory limits | Large and small inputs | `--memory-limit` values | Reject impossible runs before work begins |

## Required Metrics

Every generated benchmark row should include:

- input bytes, output bytes, delta bytes, and delta percent
- engine, format version, hasher, Lotus preset, block size, seed depth, arity
  limit, span limit, pass count
- index build time, lookup/compress time, and decompression verification time
- candidate hits, selected spans, literal bytes, layer count, and per-layer bytes
- selected span records: pass, start offset, span length, seed index, seed
  length, seed bytes as hex, encoded length, and savings
- seed length distribution
- target tier count, target span count, deduplicated span count, and seeds/sec
- peak memory or configured memory limit
- output hash and verification result

## Generated Artifacts

- `docs/RESULTS.md` / `docs/results.json`: fast release sanity matrix with
  planted, random, structured, binary, indexed, streaming, and recursive
  controls.
- `docs/SWEEPS.md` / `docs/sweeps.json`: curve-finding matrix for span-length
  overhead, planted-density break-even, memory scaling, span-step alignment,
  seed-depth economics, structured-search controls, and recursive offset/pass
  behavior.
- `docs/DEEP_SWEEPS.md` / `docs/deep_sweeps.json`: opt-in depth-3 mechanism
  and structured-control runs kept outside the default sweep path.
- `docs/TRANSFORM_SWEEPS.md` / `docs/transform_sweeps.json`: reversible
  preconditioner experiments that separate transform-only gains from seed-span
  gains.
- `docs/TRANSFORM_PROBE.md` / `docs/transform_probe.json`: simple reversible
  transform probes, including lagged residual transforms, that test whether
  shallow manifold proximity can be lifted.
- `docs/TRANSFORM_VALIDATION.md` / `docs/transform_validation.json`: held-out
  validation of the top transform-probe leads across structured corpora.
- `docs/STRUCTURAL_TRANSFORM_SEARCH.md` /
  `docs/structural_transform_search.json`: bounded reversible structural
  search across held-out, vocabulary-disjoint, and binary controls.
- `docs/BYTE_PERMUTATION_TRANSFORM_SEARCH.md` /
  `docs/byte_permutation_transform_search.json`: reversible byte-permutation
  search that tests whether global and phase-local byte maps can align
  structured corpora with finite seed-output byte distributions.
- `docs/BWT_MTF_TRANSFORM_PROBE.md` / `docs/bwt_mtf_transform_probe.json`:
  bounded BWT/MTF/RLE classic-preconditioner probe that reports transform-only
  shortening separately from Lotus seed-span evidence.
- `docs/GRAMMAR_CHANNEL_MATCH_DISCOVERY.md` /
  `docs/grammar_channel_match_discovery.json`: reversible grammar/channel
  discovery that splits structural streams from charged literal sidecars before
  accepting any seed-match signal.
- `docs/NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md` /
  `docs/numeric_value_channel_match_discovery.json`: reversible parsed numeric
  value-channel discovery that emits canonical integer, delta, digit-residual,
  and decimal mantissa/exponent streams while charging exact reconstruction
  metadata.
- `docs/RECORD_CONTEXT_TRANSFORM_SEARCH.md` /
  `docs/record_context_transform_search.json`: record/context-aware reversible
  transform search over line transposes, field-column grouping, fixed-width
  columns, and record deltas with metadata charged before promotion.
- `docs/TOKEN_DICTIONARY_TRANSFORM_SEARCH.md` /
  `docs/token_dictionary_transform_search.json`: token/dictionary reversible
  transform search over lexeme replacement and token-order streams, with
  dictionary, separator, unknown-token, and row metadata charged.
- `docs/AFFINE_TRANSFORM_SEARCH.md` / `docs/affine_transform_search.json`:
  reversible affine and phase-affine byte-remap search that tests whether
  alphabet alignment can move held-out prefix ladders toward exact spans.
- `docs/SEED_MANIFOLD_RESIDUAL_STEERING.md` /
  `docs/seed_manifold_residual_steering.json`: residual sidecar economics
  probe that counts seed-record savings against sidecar bytes and metadata.
- `docs/SIDECAR_BREAK_EVEN.md` / `docs/sidecar_break_even.json`:
  residual-sidecar break-even report that derives required prefix lengths
  before spending compute on more steering variants.
- `docs/RESIDUAL_PAYLOAD_COMPRESSIBILITY.md` /
  `docs/residual_payload_compressibility.json`: residual payload coder bounds
  for selected sidecar rows, separating measured zlib/LZMA signals from
  theoretical zero-payload and entropy lower bounds.
- `docs/EXPERIMENTAL_SIDECAR_DESCRIPTOR.md` /
  `docs/experimental_sidecar_descriptor.json`: research-only descriptor
  prototype for promoted residual payload rows, including exact decode proof,
  corrupt-input rejection, and full-stream overhead accounting.
- `docs/SIDECAR_RECORD_OVERHEAD.md` / `docs/sidecar_record_overhead.json`:
  record-layout budget that tests whether packed offsets, seed indexes, and
  larger bundles can close the full-stream sidecar overhead gap.
- `docs/PACKED_SIDECAR_DESCRIPTOR.md` / `docs/packed_sidecar_descriptor.json`:
  research-only packed offset/seed-index descriptor prototype with exact decode
  proof, corruption rejection, and full-stream negative delta on one promoted
  held-out row.
- `docs/PACKED_SIDECAR_CONTROLS.md` / `docs/packed_sidecar_controls.json`:
  packed descriptor control matrix across selected discovery, held-out, shadow,
  and binary rows, reporting encodability, decode proof, and negative cases.
- `docs/GENERALIZED_PACKED_SIDECAR.md` /
  `docs/generalized_packed_sidecar.json`: generalized packed descriptor matrix
  comparing fixed, variable, and tiered offset modes plus seed dictionary
  modes to separate descriptor packing gains from held-out negative-case
  diversity.
- `docs/PACKED_SIDECAR_REPLICATION.md` /
  `docs/packed_sidecar_replication.json`: frozen held-out replication matrix
  for the packed sidecar descriptor, with predeclared ordinary, near-family,
  shadow, binary, and negative-control corpora.
- `docs/MATCH_DISCOVERY.md` / `docs/match_discovery.json`: pre-sidecar
  exact match-discovery ledger across validation and replication corpora,
  reporting prefix ladders, exact hits, and selected seed spans before any
  sidecar packing.
- `docs/ALIGNMENT_ARITY_DISCOVERY.md` /
  `docs/alignment_arity_discovery.json`: pre-sidecar alignment and arity
  matrix that varies block size, span step, phase, and arity while comparing
  generated seed prefixes directly against raw target bytes.
- `docs/TRANSFORMED_MATCH_DISCOVERY.md` /
  `docs/transformed_match_discovery.json`: pre-sidecar exact match-discovery
  ledger after the frozen reversible transform-validation matrix, with
  transform metadata charged in the row economics.
- `docs/LEAD_EXACT_DISCOVERY.md` / `docs/lead_exact_discovery.json`:
  selected-lead exact-discovery ledger for affine, periodic, and composed
  prefix-4 leads, again charging transform metadata before promotion.
- `docs/LEAD_DEPTH3_PREFIX_PROBE.md` /
  `docs/lead_depth3_prefix_probe.json`: selected-lead depth-3 prefix probe
  that promotes only prefix movement into a bounded compression follow-up.
- `docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md` /
  `docs/lead_depth3_compression_followup.json`: CLI compression follow-up for
  the selected-lead depth-3 promoted rows, deduplicated by transformed
  SHA-256.
- `docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md` /
  `docs/depth3_frontier_exact_discovery.json`: bounded full depth-3 exact
  discovery gate over frozen depth-2 frontier/null rows before any depth-4
  search is justified.
- `docs/DEPTH4_SHARD_PLAN.md` / `docs/depth4_shard_plan.json`: generated
  depth-4 compute/shard plan that records seed ranges, expected hit rates,
  promotion gates, and stop rules without running depth-4 by default.
- `docs/DEPTH4_PILOT_SHARD.md` / `docs/depth4_pilot_shard.json`: bounded
  one-shard depth-4 pilot that enumerates a deterministic four-byte seed shard
  against the frozen frontier and keeps full depth-4 gated unless evidence
  improves.
- `docs/SEARCH_FRONTIER_GATE.md` / `docs/search_frontier_gate.json`: generated
  go/no-go decision ledger for broad raw depth search, full depth-4 execution,
  corpus-matrix promotion, and format-transform promotion.
- `docs/MECHANISM_EXPERIMENT_RANKING.md` /
  `docs/mechanism_experiment_ranking.json`: generated evidence triage ranking
  for the next non-depth mechanism experiments before raw-depth escalation or
  format promotion.
- `docs/LONG_SPAN_BUNDLE_GATE.md` / `docs/long_span_bundle_gate.json`:
  generated go/no-go ledger for broad long-span bundle sweeps. It consolidates
  search-frontier, raw-suffix, selected-span, and control gates before any
  expensive long-span compute is allowed.
- `docs/SEED_TABLE_PRESET_PROBE.md` / `docs/seed_table_preset_probe.json`:
  generated research-only seed-table/Lotus preset probe that tests whether a
  frozen public corpus-shaped codebook creates held-out selected spans after
  metadata and controls.
- `docs/PUBLIC_PRESET_PROMOTION_GATE.md` /
  `docs/public_preset_promotion_gate.json`: generated public-preset go/no-go
  gate that consolidates seed-table, schema dictionary, salted-expander,
  control, exact-decode, and format-boundary evidence before any preset is
  treated as `.tlmr` support.
- `docs/PUBLIC_PRESET_CONTROL_AUDIT.md` /
  `docs/public_preset_control_audit.json`: generated control-separation audit
  that explains paired-shadow/generic-baseline preset failures and
  pre-registers bounded ablations before the public-preset lane can advance.
- `docs/PUBLIC_PRESET_CONTROL_ABLATION.md` /
  `docs/public_preset_control_ablation.json`: generated ablation manifest that
  converts the public-preset control audit into paired-shadow expansion,
  dictionary-size equalization, project-token removal, leave-family-out, and
  density-normalization tests.
- `docs/PUBLIC_PRESET_ABLATION_PROJECTION.md` /
  `docs/public_preset_ablation_projection.json`: generated read-only projection
  over existing public-preset rows that estimates project-token and
  leave-family-out sensitivity before any exact bounded rerun.
- `docs/PUBLIC_PRESET_CONTROL_RERUN.md` /
  `docs/public_preset_control_rerun.json`: generated exact bounded rerun over
  filtered decoder-public preset variants; it blocks current public-preset
  promotion because token removal keeps paired-shadow controls negative and
  leave-family-out does not keep enough ordinary groups.
- `docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md` /
  `docs/exact_short_hit_bundle_economics.json`: generated accounting probe
  that reconstructs existing verified short hits, charges full-stream bundle
  metadata, and blocks promotion when controls are comparable.
- `docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md` /
  `docs/whole_stream_residual_vector_probe.json`: generated whole-stream
  residual-vector falsification probe that rebuilds the frozen sidecar
  replication ledger, tests global residual entropy plus bitplane/vector
  channels, and blocks promotion when no honest full-stream negative rows
  survive charged metadata.
- `docs/EXPANDER_SALT_ENSEMBLE.md` / `docs/expander_salt_ensemble.json`:
  generated expander salt/preset ensemble probe that tests predeclared
  file/layer-level salted expanders against the matched random-trial
  multiplier and charges selector/preset metadata before any win can count.
- `docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md` /
  `docs/schema_native_public_dictionaries.json`: generated schema-native
  public dictionary/Lotus preset probe that freezes decoder-public entries,
  charges selector/version metadata, and compares schema-family wins against
  SHA-256, generic, wrong-schema, same-size random, and shadow controls.
- `docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md` /
  `docs/schema_native_public_dictionary_replication.json`: generated
  replication/hardening probe that replays the public-dictionary idea against
  the frozen expansion corpus bank and blocks promotion when paired shadow
  controls also shrink.
- `docs/SUPERPOSITION_TELEMETRY.md` / `docs/superposition_telemetry.json`:
  generated candidate-lattice telemetry that shows weighted selection beating
  greedy overlap selection on a deterministic fixture while explaining every
  discarded candidate.
- `docs/LATTICE_SELECTION_HELDOUT_PROBE.md` /
  `docs/lattice_selection_heldout_probe.json`: generated held-out replay of
  existing exact dictionary candidates; it finds zero weighted-selector byte
  improvement over greedy selection, so lattice promotion remains blocked as
  compression-utility evidence.
- `docs/RECURSIVE_STRUCTURED_FIXTURES.md` /
  `docs/recursive_structured_fixtures.json`: generated recursive-v2 fixture
  gate built from real CLI compression/decompression runs. It keeps planted
  offset wins diagnostic-only and blocks recursive convergence claims until
  ordinary non-offset structured families improve after v2 metadata is charged.
- `docs/SCALE_PERFORMANCE.md` / `docs/scale_performance_report.json`:
  generated scale-performance decision report over the current planted-density
  memory-scaling sweep. It treats the 16 MiB run as interpretable but
  memory-heavy, not production-scale evidence.
- `docs/UI_WORKFLOW_SMOKE.md` / `docs/ui_workflow_smoke.json`: generated
  static Tauri/UI workflow smoke report that keeps the research-artifact bridge,
  evidence DTO, preview mock, and ledger cards aligned.
- `docs/PERIODIC_TRANSFORM_PROBE.md` /
  `docs/periodic_transform_probe.json`: bounded periodic XOR/add mask probes
  that test whether low-metadata reversible masks create longer prefix ladders.
- `docs/COMPOSED_TRANSFORM_PROBE.md` /
  `docs/composed_transform_probe.json`: composed context+periodic probe that
  tests whether residual/structural transforms and selected periodic masks work
  better together than alone.
- `docs/CORPUS_MATRIX.md` / `docs/corpus_matrix.json`: deterministic
  structured-corpus controls across JSON, Markdown, CSV, Rust-like source,
  HTML, Python-like source, SQL, TOML, XML, logs, YAML, CSS,
  JavaScript-like source, GraphQL, and Nginx-style config.
- `docs/CORPUS_GENERALIZATION_PROBE.md` /
  `docs/corpus_generalization_probe.json`: cheap shadow/random/compressed
  controls that test literal-token overfit without staling the expensive
  corpus-matrix hash chain.
- `docs/HELDOUT_CORPUS_EXPANSION.md` /
  `docs/heldout_corpus_expansion.json`: frozen replication-corpus frontier
  audit that reports which deterministic held-out families are outside the
  canonical matrix and whether raw seed-prefix evidence changes before matrix
  promotion.
- `docs/ACCELERATION.md` / `docs/acceleration_report.json`: generated GPU and
  acceleration readiness report.
- `docs/THEORY.md` / `docs/theory.json`: generated hit-probability and record
  overhead model tied to observed corpus controls.
- `docs/MANIFOLD.md` / `docs/manifold.json`: generated seed-output manifold
  proximity diagnostic for raw, transformed, random, and planted controls.
- `docs/NEARMISS_FORECAST.md` / `docs/nearmiss_forecast.json`: generated
  random-suffix forecast that converts prefix near misses into expected exact
  hit scale.
- `docs/PREFIX_LADDER.md` / `docs/prefix_ladder.json`: generated diagnostic
  that tracks where held-out near misses stall between prefix lengths.
- `docs/DEPTH3_PREFIX_PROBE.md` / `docs/depth3_prefix_probe.json`: generated
  prefix-frontier diagnostic that enumerates depth-3 seeds for selected
  held-out near misses and treats prefix >=5 movement as a narrow follow-up
  signal, not a compression claim.
- `docs/DEPTH3_COMPRESSION_FOLLOWUP.md` /
  `docs/depth3_compression_followup.json`: generated bounded compression
  follow-up for the depth-3 prefix-frontier rows, deduplicated by physical
  input SHA-256.
- `docs/FIFTH_BYTE_RESIDUAL.md` / `docs/fifth_byte_residual.json`:
  generated diagnostic that compares prefix-4 near misses against the actual
  generated fifth-byte map.
- `docs/FIFTH_BYTE_STEERING.md` / `docs/fifth_byte_steering.json`: generated
  diagnostic that composes residual-derived period-4 correction masks after
  source transforms and validates them cross-corpus.
- `docs/CONTEXTUAL_FIFTH_BYTE_STEERING.md` /
  `docs/contextual_fifth_byte_steering.json`: generated diagnostic for
  context-conditioned fifth-byte masks with same-shape null controls.
- `docs/GOAL_AUDIT.md` / `docs/goal_audit.json`: generated
  requirement-to-evidence ledger for the optimization architecture plan and
  active research goals.
- `docs/VIABILITY.md` / `docs/viability.json`: generated evidence ledger that
  separates proved mechanism claims from open production claims.
- `docs/RESEARCH_SCORECARD.md` / `docs/research_scorecard.json`: generated
  top-level proof map and open-frontier summary assembled from all result
  artifacts.
- `docs/EXPERIMENT_QUEUE.md` / `docs/experiment_queue.json`: generated next
  experiment queue with promotion gates, stop rules, and parallel work lanes.
- `docs/RESEARCH_DECISION.md` / `docs/research_decision.json`: generated
  downstream no-go/reopen ledger that records when no ready ungated experiment
  remains, which lanes are blocked, and which evidence would reopen
  compute-heavy work.
- `docs/RESEARCH_FRONTIER.md` / `docs/research_frontier.json`: generated
  trigger board that maps unresolved gates to canonical artifacts, forbidden
  actions, subagent work packages, and exact evidence triggers without launching
  seed search or making compression claims.
- `docs/RESEARCH_TEAM_PROTOCOL.md` / `docs/research_team_protocol.json`:
  generated dispatching-parallel-agents protocol that converts the current
  frontier into bounded briefs with allowed actions, forbidden actions, output
  contracts, stop rules, and write scopes.
- `docs/GOAL_COMPLETION_AUDIT.md` / `docs/goal_completion_audit.json`:
  generated active-goal audit that maps the full research objective to
  authoritative evidence and keeps the completion boundary explicit while
  natural-corpus and production claims remain unproved.
- `docs/BLOCKED_REQUIREMENT_DISPATCH.md` /
  `docs/blocked_requirement_dispatch.json`: generated maintenance-only dispatch
  plan that turns blocked completion requirements into scoped
  dispatching-parallel-agents briefs with stop rules and promotion triggers.
- `docs/NATURAL_CORPUS_REOPEN_MANIFEST.md` /
  `docs/natural_corpus_reopen_manifest.json`: generated natural-corpus
  pre-registration manifest that allows only corpus provenance and paired-control
  registration while prefix/exact/selected-span evidence remains null.
- `docs/EXTERNAL_CORPUS_ACCESSION.md` /
  `docs/external_corpus_accession.json`: generated accession validator for
  future external natural corpora. It checks repository-local paths,
  provenance, license, SHA-256, byte count, independence group, and paired
  controls, but performs no seed search and authorizes no compute.
- `docs/RESEARCH_HYPOTHESES.md` / `docs/research_hypotheses.json`: generated
  whitepaper/evidence hypothesis registry that makes the best bounded case for
  each research lane, then records falsification tests, promotion triggers, and
  No Seed Search stop rules.
- `docs/RESEARCH_TEAM_PACKET.md` / `docs/research_team_packet.json`: generated
  operating packet that joins hypotheses, team briefs, and blocked requirements
  into a six-agent dispatching-parallel-agents roster with work-board items,
  handoff contracts, integration gates, and conflict rules.
- `docs/RESEARCH_AGENT_PROMPTS.md` / `docs/research_agent_prompts.json`:
  generated prompt pack that extracts one dispatch-ready, self-contained
  prompt per research lane from the operating packet, writes standalone
  `docs/agent_prompts/*.prompt.txt` files, and does not launch agents or
  authorize compute.
- `docs/RESEARCH_AGENT_RESULT_INTAKE.md` /
  `docs/research_agent_result_intake.json`: generated result-intake protocol
  that validates future `docs/agent_reports/manifest.json` entries against the
  prompt pack, prompt hashes, source artifacts, stop rules, and claim gates
  before any returned subagent work is treated as review-ready. It also writes
  `docs/agent_reports/report_templates.json` and
  `docs/agent_reports/REPORT_TEMPLATES.md` with current prompt hashes for each
  lane.
- `docs/CLAIM_BOUNDARY_AUDIT.md` / `docs/claim_boundary_audit.json`:
  generated documentation safety rail that scans public research docs for
  unsupported positive claims while natural-corpus proof, production proof,
  broad-depth search, format promotion, external compute, random-data
  compression, and universal-compressor gates remain false.
- `docs/CANDIDATE_LATTICE.md`: experimental superposition/lattice contract,
  intentionally outside the v2 wire format.

Generated JSON artifacts carry manifest hashes, and `scripts/doc_lint.py`
rejects stale checked-in artifacts.

## Immediate Patch Queue

1. Decide whether any transform/preconditioner should graduate into a versioned
   `.tlmr` format extension, or remain an external corpus transform.
2. Treat the generated recursive structured-fixtures report as the current
   recursion gate: ordinary non-offset later-layer wins are still absent, so
   recursive convergence claims stay blocked by evidence.
3. Treat the generated scale-performance report as the current scaling gate:
   extend planted-density size only after peak/table ratios stay explainable or
   chunked target tables reduce memory.
4. Use the generated vocabulary-disjoint shadow corpora plus binary TLV/varint
   controls to classify future transform leads as literal-token, syntax, or
   binary-structure effects.
5. Treat the bounded structural-transform search as current null evidence:
   successor transforms need held-out prefix>=5 uplift or exact seed-span hits.
6. Treat affine byte-remap prefix>=4 uplift as a shallow lead only; the next
   transform lane should not escalate unless sidecar economics or longer-span
   break-even math becomes favorable.
7. Treat seed-manifold residual sidecars as current null evidence at span 8:
   forced exact spans still bloat after residual bytes and metadata.
7. Apply the sidecar break-even gate before new residual experiments: current
   held-out forced prefixes stop at 4, raw suffix strict gain starts at 6+,
   and any sublinear residual model must be measured as real, invertible
   payload compression before it counts.
8. Treat residual payload compression as a narrow follow-up only: zlib/LZMA
   produce one held-out negative sidecar row, but this is not format support
   until an experimental descriptor proves exact decode and controls.
9. Treat the first experimental sidecar descriptor as a useful falsifier:
   selected-span payload accounting is negative, but full-stream descriptor
   overhead still bloats, so the next sidecar work is lower-overhead records or
   larger span bundles.
10. Prototype the packed offset/seed-index sidecar table before broader
   sidecar work: the budget model goes full-stream negative, but it still needs
   exact decode and corrupt-input tests.
11. Treat the packed sidecar descriptor as a real but narrow signal: it is
   full-stream negative on one promoted held-out row, so next work must test
   controls, generality, and format-neutral replication before changing
   `.tlmr`.
12. Treat the packed sidecar controls as promising but not general: they produce
   one ordinary held-out negative case under strict u8-delta assumptions, while
   most selected rows are skipped by the current packed-table shape.
13. Treat generalized packed sidecars as a mixed result: wider offsets encode
   every selected source row and seed dictionaries improve table economics, but
   ordinary held-out negative diversity is still stuck at one case.
14. Treat packed sidecar replication as current falsification evidence:
   predeclared held-out corpora produced zero full-stream negative rows under
   the frozen descriptor assumptions, so future sidecar work needs new match
   discovery rather than more descriptor packing.
15. Treat the pre-sidecar match-discovery ledger as current null evidence:
   arity 1..5 over validation and replication corpora found no prefix>=5 rows,
   exact hits, or selected spans at seed depth 2.
16. Treat alignment and arity tuning as current null evidence for profitable
   records: the generated matrix finds only unprofitable short-span exact hits,
   no prefix>=5 movement, and no selected spans.
17. Treat the frozen transform-validation matrix as current null evidence for
   exact record creation: transformed span-8 discovery produces no prefix>=5
   rows, exact hits, selected spans, or metadata-profitable rows.
18. Treat selected affine/periodic/composed prefix-4 leads as current null
   evidence for exact records: the selected-lead matrix produces no prefix>=5
   rows, exact hits, selected spans, or metadata-profitable rows.
19. Keep broad depth-3 sweeps gated until a new lead beats
   `docs/DEPTH3_COMPRESSION_FOLLOWUP.md` by producing selected spans, exact
   hits, or negative delta.
20. Add small structured corpora under `tests/fixtures/` or generated fixtures
   that avoid committing bulky data.
21. Add end-to-end Tauri/browser workflow tests once the frontend controls are
   stable enough to automate without a desktop window.
22. Measure whether a real GPU/OpenCL implementation can beat CPU streaming
   without breaking the existing CPU/GPU parity guard.
23. Extend memory scaling beyond the current 1 KiB through 16 MiB generated
   sweep rows once candidate storage and telemetry compaction are ready for
   larger local runs.
24. Stress the chunked index builder at seed depth 3 with bounded scratch space
   before treating multi-byte seed tables as practical local artifacts.
25. Regenerate `docs/GOAL_AUDIT.md` whenever a requirement moves between open,
   qualified, proved, and complete.
26. Treat `docs/MECHANISM_EXPERIMENT_RANKING.md` as the ranked next-mechanism
    source of truth, while `docs/EXPERIMENT_QUEUE.md` consumes completed null
    lanes and advances to the next ready mechanism.
27. Treat `docs/LONG_SPAN_BUNDLE_GATE.md` as the current long-span sweep
    source of truth: broad long-span bundle sweeps stay blocked while it reports
    unmet search-frontier, raw-suffix, selected-span, and control gates.
28. Treat `docs/SEED_TABLE_PRESET_PROBE.md` as current null/insufficient
    evidence for the first public corpus-shaped Lotus preset unless its
    promotion gates move in a generated rerun.
29. Treat `docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md` as current
    null/insufficient evidence for span-3 short-hit bundling unless future
    exact-hit artifacts produce clean ordinary wins with null controls.
30. Treat `docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md` as current
    null/falsification evidence for residual-sidecar promotion: whole-stream
    residual vectors currently produce zero honest full-stream negative rows
    on the frozen replication matrix, so the queue advances to a materially
    different mechanism rather than more sidecar packing.
31. Treat `docs/EXPANDER_SALT_ENSEMBLE.md` as current null evidence for
    salted expander presets: predeclared salts produced zero exact hits and
    zero selected-span rows against a matched random-trial expectation, so
    this lane should not become format work without new evidence.
32. Treat `docs/EXTERNAL_CORPUS_ACCESSION.md` as the external corpus ingress
    gate: future ordinary corpora must be checked in under
    `corpora/external/` with SHA-256, byte count, provenance, license,
    independence group, and paired shadow plus binary/random controls before
    any prefix audit or seed search is proposed.
33. Treat `docs/CLAIM_BOUNDARY_AUDIT.md` as the claim-boundary guardrail:
    public research docs must not drift into unsupported natural-corpus proof,
    production-readiness, broad-compute, format-promotion, random-data, or
    universal-compressor claims while the generated proof gates remain false.
34. Treat `docs/RESEARCH_AGENT_PROMPTS.md` as the handoff surface for
    dispatching-parallel-agents: future subagents should receive the generated
    prompt for their lane, then return findings against the listed source
    artifacts and integration gates rather than launching broad compute.
35. Treat `docs/RESEARCH_AGENT_RESULT_INTAKE.md` as the return-path guardrail:
    future subagent reports must be registered in
    `docs/agent_reports/manifest.json`, carry the current prompt SHA-256, list
    checks and claim changes, and pass the result-intake validator before
    integration review. Use `docs/agent_reports/report_templates.json` as the
    generated source for current prompt hashes when registering those reports.

## Falsification Criteria

Telomere's research thesis weakens sharply if:

- planted data shrinks but structured generated corpora never beat overhead
  after reasonable arity and span sweeps
- recursive v2 passes rarely find new selected spans beyond the first pass
- selected savings grow more slowly than record overhead and search cost
- search cost scales beyond archival budgets even for small positive deltas
- streaming/indexed engines diverge from brute reference semantics
- telemetry cannot explain why a claimed win happened

These outcomes would still leave Telomere as a useful codec/search experiment,
but they would argue against stronger archival-compression claims.

## Parallel Agent Roster

Use separate read-only explorers for:

- theory and information constraints
- engine implementation versus whitepaper architecture
- benchmark and corpus design
- Tauri/operator research workflow

Use workers only when the write sets are disjoint, such as one worker for
benchmark scripts and another for Tauri serialization tests. Every worker must
respect the dirty tree and must not revert edits it did not make.

## Working Rule

The phrase "with enough compute" is a hypothesis generator, not a conclusion.
For every larger search window, record the hit rate, selected savings, output
size, runtime, and memory. If the curve bends toward useful archival reduction,
Telomere earns the next experiment. If it does not, the result is still valuable
science.
