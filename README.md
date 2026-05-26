# Telomere

Telomere is an experimental, lossless, stateless generative compression
prototype. It splits input into fixed-size blocks, searches deterministic seed
space, and replaces a block span with a shorter Lotus-encoded `(arity, seed)`
record only when the record is smaller than the original span. Blocks that do
not have a compressive seed are emitted as literal records.

Telomere is not a universal compressor. Random or ordinary data usually gets
larger, especially at seed depth 1. Negative delta is expected only on data that
contains planted or naturally recurring spans that are reproduced by short hash
seeds.

The serious research path is the `.tlmr` v2 engine. It supports reusable
exact-prefix seed indexes and a CPU streaming matcher that builds equal-length
target span tiers, enumerates seeds once, and checks each generated prefix
against every active tier before encoding recursive layers.

## Install

```powershell
cargo build --release
```

The main binary is `telomere`.

## CLI

```text
telomere compress [OPTIONS] <INPUT> <OUTPUT>
telomere decompress [OPTIONS] <INPUT.tlmr> <OUTPUT>
telomere index build --output <DIR> --max-span-len <N> [OPTIONS]
telomere index info <DIR>
telomere index verify <DIR>
```

Compression options:

```text
--seed-depth <N>       Maximum seed length in bytes, default 1
--passes <N>           Accepted for compatibility, default 1
--checkpoint-every <N> Parsed but checkpointing is not implemented
--memory-limit <LIMIT> Limit syntax: 100%, 4GB, 512MB, 64KB
--hasher <KIND>        blake3 or sha256, default blake3
--verify               Decompress after writing the in-memory result
--json                 Print RunSummary JSON to stdout
--block-size <N>       Block size in bytes, default 4, valid 1..=16
--force                Overwrite an existing output file
--engine <KIND>        brute, indexed, or streaming; default brute
--format <KIND>        v1 or v2, default v1
--index <DIR>          Required for indexed/v2 compression
--max-span-len <N>     Maximum indexed/streaming span length in bytes
--span-step <N>        v2 candidate-start step, default block-size
--telemetry-limit <N>  Bound selected_span records in --json telemetry
--target-chunk-bytes <LIMIT>
                       Experimental indexed/streaming v2 target-table byte
                       budget per chunk; lowers peak table memory by redoing
                       chunk-local lookup work
```

Decompression options:

```text
--force                Overwrite an existing output file
--hasher <KIND>        Legacy compatibility flag; .tlmr v1 uses the file header
--memory-limit <LIMIT> Limit decompressed output and v2 intermediate layer
                       allocation, default 80%; this is an allocation guard,
                       not full RSS containment proof
```

Examples:

```powershell
cargo run --bin telomere -- compress input.bin output.tlmr --block-size 4 --seed-depth 1 --json --verify
cargo run --bin telomere -- decompress output.tlmr restored.bin --force
cargo run --bin telomere -- compress planted.bin planted.tlmr --hasher sha256 --block-size 2 --seed-depth 1 --force
cargo run --bin telomere -- index build --output sha.idx --hasher sha256 --max-seed-len 1 --max-span-len 8 --block-size 4
cargo run --bin telomere -- compress planted.bin planted-v2.tlmr --engine indexed --format v2 --index sha.idx --hasher sha256 --seed-depth 1 --max-span-len 8
cargo run --bin telomere -- compress planted.bin planted-stream.tlmr --engine streaming --format v2 --hasher sha256 --seed-depth 1 --max-span-len 8
cargo run --bin telomere -- compress offset.bin offset-stream.tlmr --engine streaming --format v2 --hasher sha256 --seed-depth 1 --max-span-len 8 --span-step 1
```

`telomere index verify` is a structural index check: it validates the manifest,
tier file lengths, and sorted lookup keys. Compression still re-expands every
returned seed before accepting a hit, so decode correctness does not depend on
trusting the index.

## File Format

The canonical format reference is [docs/FORMAT.md](docs/FORMAT.md).
The research operating plan is
[docs/RESEARCH_PROGRAM.md](docs/RESEARCH_PROGRAM.md).

`.tlmr` v1 files begin with the four magic bytes `TLMR` and a single version
byte. Everything after that is a Lotus bit stream — there is no fixed-width
byte-tagged header any more. The header records:

- format version (currently `2`; `1` was the legacy fixed 40-byte layout and
  is no longer accepted)
- Lotus preset version `2`
- hasher kind, `blake3` or `sha256`
- block size and final block size
- maximum seed length and arity limits
- hash bit width
- layer count, currently always `1`
- original length, payload bit length, and truncated output hash

After the header, the payload is a single Lotus bit stream of records packed
back-to-back. There is no per-record byte padding; the only intra-payload
padding is the 0..7 zero pad bits inside each literal record so its raw
bytes start at a byte boundary. Compressed records encode arity through a
Lotus J1D1 value (`0..=4` = arities 1..=5, `5` = literal escape) followed by
a Lotus J3D2 canonical seed index. A record with arity 1 and seed index 0 is
9 bits total.

`.tlmr` v2 follows the same strategy: a 5-byte raw magic+version prefix
followed by a Lotus bit stream that carries the header, all layer
descriptors, and the outer payload. Each layer's payload is a flat bit-packed
stream of seed-span and literal records (no per-record byte tags or raw
`u16 span_len` fields). Decompression does not need an index; the index is
only a compression-time search accelerator.

The old 3-byte `TlmrHeader` and the legacy 40-byte fixed v1 header are gone
from the active file formats because they could not record hasher kind, Lotus
preset, or enough metadata to decode multi-pass output unambiguously.

## Lotus In This Repository

Telomere uses the Lotus tiered integer codec from the sibling crate at
`../lotus/src/lib.rs` for every header field, arity discriminator, and seed
index — there is no local Lotus reimplementation and no byte-tagged framing.
Two presets are used:

- **J3D2** (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`) — seed indices, sizes,
  counts, and every other Lotus integer in both v1 and v2. Three-bit
  jumpstarter, two levels of sliding-window tier framing, sliding-window
  payload.
- **J1D1** (`LOTUS_ARITY_J_BITS = 1`, `LOTUS_ARITY_TIERS = 1`) — only for
  the v1 arity discriminator. Six codepoints (`0..=5`) cover arities 1..=5
  plus the literal escape. J1D1 is the smallest preset that admits six
  values, so the arity field costs exactly the bits the alphabet requires.

A compressed v1 record packs as

```text
Lotus J1D1(arity_value)  Lotus J3D2(seed_index)
```

back-to-back inside the layer's bit stream. Arity values `1..=5` are valid
compressed spans (arity `2` is valid and is not reserved); the literal marker
is the J1D1 value `5`. The decoder uses the lotus crate's streaming
`BitReader` to recover both fields and `index_to_seed` to map the seed index
back to its canonical seed bytes.

## Multi-Pass Semantics

`.tlmr` v1 emits one-layer-decodable files only. The CLI still accepts
`--passes` for compatibility, but the v1 writer caps output to one layer and
records `layer_count = 1`.

`.tlmr` v2 supports recursive indexed and streaming layers. The first layer
establishes the v2 container payload; later recursive layers are committed only
when the encoded layer is smaller than its input, and every decoded layer hash
is verified during decompression.

## Performance Expectations

- Seed depth 1 checks 256 seeds per span and is fast enough for tests.
- Seed depth 2 checks 65,536 additional seeds per span and is slow-ish.
- Seed depth 3 checks 16,777,216 additional seeds per span and is expensive.
- Unit and integration tests should use `max_seed_len = 1`.
- Random data should not be expected to compress.
- Indexed compression amortizes repeated local runs with reusable exact-prefix
  seed tiers. The index builder writes mmap-ready sorted tier files through
  chunked external sorting instead of requiring one full in-memory map.
- Streaming compression builds equal-length target span tables and enumerates
  each seed once across all active tiers. This is the whitepaper-aligned CPU
  research path and is still archival, not real-time.
- `--target-chunk-bytes` on indexed/v2 or streaming/v2 bounds each
  experimental target-table chunk. Indexed chunking repeats index lookups over
  chunk-local target spans; streaming chunking rescans canonical seeds per
  chunk. This is fixture-tested table-memory evidence, not full RSS proof.
- `--span-step 1` on indexed/v2 or streaming/v2 enables experimental
  sub-block candidate starts. The default remains `block-size`, which is faster
  and preserves the block-grid search used by normal v2 runs.
- `--json` on indexed/v2 and streaming/v2 includes `engine_telemetry` with
  candidate counts, selected span records, literals, bundles, tier hits, tier
  work accounting (`target_windows`, `lookup_count`, raw/profitable hits,
  estimated target-table bytes), per-layer payload bytes, and the final
  container byte count. Streaming telemetry also records `seeds_scanned` and
  `seed_expansions`.
- `--telemetry-limit N` preserves telemetry counts while truncating
  `selected_spans` arrays for larger benchmark runs.

See [docs/RESULTS.md](docs/RESULTS.md) for generated local results and
[scripts/generate_results.py](scripts/generate_results.py) for the reproduction
script. See [docs/RESEARCH_PROGRAM.md](docs/RESEARCH_PROGRAM.md) for the
experiment ladder and falsification criteria. See [docs/SWEEPS.md](docs/SWEEPS.md)
for generated span-length, planted-density, memory-scaling, and recursive
offset sweeps plus structured-search and seed-depth controls. See
[docs/GENERATED_LEDGER_PIPELINE.md](docs/GENERATED_LEDGER_PIPELINE.md) for the
top-level research-ledger regeneration order and
[docs/NATURAL_CORPUS_PROOF_MATRIX.md](docs/NATURAL_CORPUS_PROOF_MATRIX.md) for
the non-planted viability evidence gates,
[docs/NATURAL_CORPUS_REOPEN_MANIFEST.md](docs/NATURAL_CORPUS_REOPEN_MANIFEST.md)
for the manifest-only path that could reopen natural-corpus work without broad
seed search, and
[docs/EXTERNAL_CORPUS_ACCESSION.md](docs/EXTERNAL_CORPUS_ACCESSION.md) for the
checked external-corpus accession gate that requires provenance, SHA-256,
independence groups, and paired controls before any future natural-corpus
compute, and
[docs/PRODUCTION_PROOF_MATRIX.md](docs/PRODUCTION_PROOF_MATRIX.md) for the
release-readiness evidence matrix. See
[docs/DEEP_SWEEPS.md](docs/DEEP_SWEEPS.md) for opt-in depth-3 controls and
[docs/TRANSFORM_SWEEPS.md](docs/TRANSFORM_SWEEPS.md) for reversible
preconditioner experiments. See
[docs/TRANSFORM_PROBE.md](docs/TRANSFORM_PROBE.md) for simple reversible
transform probes against the seed-output manifold, and
[docs/TRANSFORM_VALIDATION.md](docs/TRANSFORM_VALIDATION.md) for held-out
validation of those probe leads. See
[docs/CORPUS_MATRIX.md](docs/CORPUS_MATRIX.md) for the structured-corpus
matrix, [docs/CORPUS_GENERALIZATION_PROBE.md](docs/CORPUS_GENERALIZATION_PROBE.md)
for cheap overfitting controls, and
[docs/HELDOUT_CORPUS_EXPANSION.md](docs/HELDOUT_CORPUS_EXPANSION.md)
for the frozen replication-corpus frontier audit before expensive matrix
promotion, and
[docs/BYTE_PERMUTATION_TRANSFORM_SEARCH.md](docs/BYTE_PERMUTATION_TRANSFORM_SEARCH.md)
for seed-manifold byte-permutation alignment probes,
[docs/BWT_MTF_TRANSFORM_PROBE.md](docs/BWT_MTF_TRANSFORM_PROBE.md)
for bounded BWT/MTF/RLE preconditioner probes,
[docs/GRAMMAR_CHANNEL_MATCH_DISCOVERY.md](docs/GRAMMAR_CHANNEL_MATCH_DISCOVERY.md)
for reversible grammar/channel discovery probes,
[docs/NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md](docs/NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md)
for parsed numeric value-channel probes,
[docs/RECORD_CONTEXT_TRANSFORM_SEARCH.md](docs/RECORD_CONTEXT_TRANSFORM_SEARCH.md)
for record/context-aware reversible transform probes, and
[docs/TOKEN_DICTIONARY_TRANSFORM_SEARCH.md](docs/TOKEN_DICTIONARY_TRANSFORM_SEARCH.md)
for token/dictionary transform probes.
[docs/VIABILITY.md](docs/VIABILITY.md) is the generated evidence ledger, and
[docs/RESEARCH_SCORECARD.md](docs/RESEARCH_SCORECARD.md) for the consolidated
proof map that separates proved mechanism claims from open research.
[docs/RECURSIVE_STRUCTURED_FIXTURES.md](docs/RECURSIVE_STRUCTURED_FIXTURES.md)
is the generated recursive-v2 gate: planted offset controls improve on pass 2,
but ordinary structured fixture families currently do not promote recursive
convergence claims.
[docs/SCALE_PERFORMANCE.md](docs/SCALE_PERFORMANCE.md) interprets the bounded
planted-density memory-scaling sweep: the current 16 MiB run is explainable but
memory-heavy, not production-scale proof.
[docs/UI_WORKFLOW_SMOKE.md](docs/UI_WORKFLOW_SMOKE.md) statically checks that
the Tauri research-artifact bridge and the UI evidence ledger panel stay aligned.
Acceleration status is tracked in [docs/ACCELERATION.md](docs/ACCELERATION.md).
Hit-rate economics are generated in [docs/THEORY.md](docs/THEORY.md), and
seed-output manifold proximity is tracked in [docs/MANIFOLD.md](docs/MANIFOLD.md).
Near-miss exact-hit forecasts are generated in
[docs/NEARMISS_FORECAST.md](docs/NEARMISS_FORECAST.md). The next-action
research queue is generated in [docs/EXPERIMENT_QUEUE.md](docs/EXPERIMENT_QUEUE.md).
[docs/RESEARCH_DECISION.md](docs/RESEARCH_DECISION.md) is the downstream
no-go/reopen ledger: it records when no ready ungated experiment remains, what
is blocked, and which evidence would reopen compute-heavy work.
[docs/RESEARCH_FRONTIER.md](docs/RESEARCH_FRONTIER.md) is the compact trigger
board for unresolved gates, forbidden actions, subagent work packages, and exact
reopen evidence; it performs no seed search and makes no compression claim.
[docs/RESEARCH_TEAM_PROTOCOL.md](docs/RESEARCH_TEAM_PROTOCOL.md) turns that
frontier into constrained `dispatching-parallel-agents` briefs with explicit
allowed actions, forbidden actions, output contracts, stop rules, and write
scopes.
[docs/GOAL_COMPLETION_AUDIT.md](docs/GOAL_COMPLETION_AUDIT.md) maps the active
research objective to authoritative evidence and keeps the completion boundary
explicit while the verdict remains research-viable, not production-proven.
[docs/BLOCKED_REQUIREMENT_DISPATCH.md](docs/BLOCKED_REQUIREMENT_DISPATCH.md)
turns the completion audit's blocked requirements into maintenance-only
`dispatching-parallel-agents` briefs with stop rules and promotion triggers.
[docs/RESEARCH_HYPOTHESES.md](docs/RESEARCH_HYPOTHESES.md) is the generated
whitepaper/evidence hypothesis registry: it makes the strongest bounded case
for each research lane, then pins falsification tests, promotion triggers, and
No Seed Search stop rules to current artifacts.
[docs/RESEARCH_TEAM_PACKET.md](docs/RESEARCH_TEAM_PACKET.md) joins the
hypothesis registry, team briefs, and blocked-requirement dispatch into a
six-agent operating roster with handoff contracts, integration gates, conflict
rules, and work-board items.
[docs/RESEARCH_AGENT_PROMPTS.md](docs/RESEARCH_AGENT_PROMPTS.md) turns that
roster into dispatch-ready, self-contained prompts for each parallel research
lane, with standalone files under `docs/agent_prompts/`, without launching
agents or weakening the No Seed Search boundary.
[docs/RESEARCH_AGENT_RESULT_INTAKE.md](docs/RESEARCH_AGENT_RESULT_INTAKE.md)
is the generated return path for those lanes; its companion
`docs/agent_reports/report_templates.json` carries current prompt hashes so
future reports can be registered without hand-computing them.
[docs/CLAIM_BOUNDARY_AUDIT.md](docs/CLAIM_BOUNDARY_AUDIT.md) is the generated
documentation safety rail that scans public research docs for unsupported
natural-corpus, production, broad-compute, format-promotion, random-data, and
universal-compressor claims.
Alignment and arity controls are generated in
[docs/ALIGNMENT_ARITY_DISCOVERY.md](docs/ALIGNMENT_ARITY_DISCOVERY.md), and
transformed exact-match controls are generated in
[docs/TRANSFORMED_MATCH_DISCOVERY.md](docs/TRANSFORMED_MATCH_DISCOVERY.md).
Selected transform-lead exact checks are generated in
[docs/LEAD_EXACT_DISCOVERY.md](docs/LEAD_EXACT_DISCOVERY.md). Lead depth-3
prefix and compression follow-ups are generated in
[docs/LEAD_DEPTH3_PREFIX_PROBE.md](docs/LEAD_DEPTH3_PREFIX_PROBE.md) and
[docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md](docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md).
The broader depth-3 go/no-go gate is
[docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md](docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md).
Depth-4 compute remains gated by the generated shard plan in
[docs/DEPTH4_SHARD_PLAN.md](docs/DEPTH4_SHARD_PLAN.md), plus the bounded
pilot-shard evidence in
[docs/DEPTH4_PILOT_SHARD.md](docs/DEPTH4_PILOT_SHARD.md).
[docs/SEARCH_FRONTIER_GATE.md](docs/SEARCH_FRONTIER_GATE.md) is the generated
go/no-go gate for broad raw depth search and full depth-4 execution.
[docs/MECHANISM_EXPERIMENT_RANKING.md](docs/MECHANISM_EXPERIMENT_RANKING.md)
ranks the next non-depth mechanism experiments without reopening broad raw
depth search.
[docs/LONG_SPAN_BUNDLE_GATE.md](docs/LONG_SPAN_BUNDLE_GATE.md) is the
generated go/no-go gate for broad long-span bundle sweeps; the current evidence
keeps them blocked until search frontier, raw-suffix, selected-span, and
control gates improve.
[docs/SEED_TABLE_PRESET_PROBE.md](docs/SEED_TABLE_PRESET_PROBE.md) executes
that research-only probe and keeps it out of `.tlmr` format support unless the
generated promotion gates move.
[docs/PUBLIC_PRESET_PROMOTION_GATE.md](docs/PUBLIC_PRESET_PROMOTION_GATE.md)
consolidates seed-table, public dictionary, salted-expander, control, and
format-boundary evidence into the explicit gate for any future public preset
registry.
[docs/PUBLIC_PRESET_CONTROL_AUDIT.md](docs/PUBLIC_PRESET_CONTROL_AUDIT.md)
then explains the paired-shadow/generic-baseline control failure and
pre-registers bounded ablations before public presets can advance.
[docs/PUBLIC_PRESET_CONTROL_ABLATION.md](docs/PUBLIC_PRESET_CONTROL_ABLATION.md)
turns that audit into the concrete ablation matrix: paired-shadow expansion,
dictionary-size equalization, project-token removal, leave-family-out policy,
and density normalization.
[docs/PUBLIC_PRESET_ABLATION_PROJECTION.md](docs/PUBLIC_PRESET_ABLATION_PROJECTION.md)
then projects project-token and leave-family-out removals over existing rows;
it is not decode proof, but it identifies the exact bounded rerun worth doing.
[docs/PUBLIC_PRESET_CONTROL_RERUN.md](docs/PUBLIC_PRESET_CONTROL_RERUN.md)
then performs that exact bounded rerun over filtered decoder-public preset
variants. The current rerun blocks promotion: project-token removal leaves
paired-shadow controls negative, while leave-family-out clears controls only by
dropping below the three-group ordinary win floor.
[docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md](docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md)
then tests whether the existing verified short hits survive full-stream bundle
accounting; controls currently block promotion.
[docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md](docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md)
then treats the residual sidecar family as a hard falsification lane: the
generated run reconstructs the frozen replication ledger, charges residual
vector, offset, seed, checksum, and literal bytes, and currently finds zero
honest full-stream negative rows.
[docs/EXPANDER_SALT_ENSEMBLE.md](docs/EXPANDER_SALT_ENSEMBLE.md) then tests
predeclared salted expanders against the equivalent random-trial multiplier;
the current run finds zero salted exact hits and zero selected-span rows.
[docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md](docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md)
then tests frozen public schema dictionaries as decoder-public Lotus presets;
the current run finds a narrow schema-shaped dictionary-preset positive while
keeping SHA-256, wrong-schema, same-size random, and shadow controls null. This
is not current `.tlmr` format support and not proof of hash-manifold
compression.
[docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md](docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md)
then hardens that result on the frozen expansion corpus bank; the current run
finds broader standards-dictionary wins, but paired shadow OpenAPI/proto
controls also shrink, so registry or format promotion stays blocked.
[docs/SUPERPOSITION_TELEMETRY.md](docs/SUPERPOSITION_TELEMETRY.md) now records
the candidate-lattice selector audit: weighted selection beats greedy overlap
selection on a deterministic fixture, retained alternatives are visible, and
every discarded candidate has an explanation. This is selector correctness,
not a new compression claim.
[docs/LATTICE_SELECTION_HELDOUT_PROBE.md](docs/LATTICE_SELECTION_HELDOUT_PROBE.md)
then replays current non-planted held-out candidate sets against weighted and
greedy selectors. It finds zero selected-byte improvement from the lattice, so
superposition remains selector/audit machinery rather than compression utility
evidence.

## Supported And Removed Pieces

Supported:

- main `telomere compress` and `telomere decompress` CLI
- `telomere index build/info/verify`
- `.tlmr` v1 one-layer decode
- `.tlmr` v2 indexed recursive decode
- BLAKE3 and SHA-256 seed expansion
- Lotus arity `1..=5`, including arity `2`
- literal fallback records

Research-only:

- `--features gpu`, which currently builds a deterministic CPU fallback under
  the GPU API
- standalone diagnostics such as `block_summary` and `seed_table`

Removed:

- gloss tables and gloss binaries
- bloom filter stubs
- broken fuzz crate targets
- old digest-prefix hash-table tools
- old placeholder `lotus_core` exports
- code comments that treated `kolyma.pdf` as a protocol spec
- old speculative whitepaper docs that claimed recursive convergence or random
  data compression as current behavior

## Verification

Common local smoke gates:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/generate_evidence_regimen.py --check
python scripts/generate_research_ledgers.py --check
python scripts/generate_public_preset_promotion_gate.py --check
python scripts/generate_public_preset_control_audit.py --check
python scripts/generate_public_preset_control_ablation.py --check
python scripts/generate_public_preset_ablation_projection.py --check
python scripts/generate_public_preset_control_rerun.py --check
python scripts/generate_lattice_selection_heldout_probe.py --check
python scripts/generate_natural_corpus_reopen_manifest.py --check
python scripts/generate_external_corpus_accession.py --check
python scripts/generate_research_hypotheses.py --check
python scripts/generate_research_team_packet.py --check
python scripts/generate_research_agent_prompts.py --check
python scripts/generate_research_agent_result_intake.py --check
python scripts/generate_claim_boundary_audit.py --check
python scripts/doc_lint.py
```

The full release gate, including generated artifact `--check` commands and
Tauri checks, is [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).
