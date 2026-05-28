# Telomere - Agent Conventions

## Project Overview

Telomere is an experimental stateless lossless generative compression prototype.
The `.tlmr` v1 writer emits one-layer-decodable files only. The indexed
`.tlmr` v2 writer supports recursive layers with explicit descriptors. Each
compressed record stores a seed span whose selected hasher expansion reproduces
the original bytes; unmatched bytes are literal records.

This repo is unusual. Treat it as a first-principles probability and systems
research project, not as a normal compression library. The interesting claim is
not "structured data compresses" and not "a laptop found a lucky match." The
interesting claim is that a very large deterministic seed-addressed universe can
be searched, amortized, indexed, transformed, and encoded so that some spans are
represented by shorter self-describing seed records while lossless decode stays
cheap.

Canonical docs:

- `docs/ARCHITECTURE.md`
- `docs/FORMAT.md`
- `docs/RESEARCH_PROGRAM.md`
- `docs/THEORY.md`
- `docs/RESULTS.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/Telomere Whitepaper V2.md` (historical thesis and motivation; current
  architecture/format docs override it)

## First-Principles Model

Use this model before importing assumptions from ordinary compressors:

- Compression happens only when a compact record names bytes that can be
  regenerated exactly.
- The core predicate is byte equality:
  `expand(seed)[0..span_len] == target_span`.
- A seed is a compact address into a deterministic byte universe. Compression
  is the win from storing that address plus Lotus metadata instead of the raw
  span.
- Literal fallback is mandatory. Telomere does not and cannot compress every
  possible input.
- Search cost can be enormous. The intended high-end economics are closer to
  archival/datacenter search with cheap decode than to interactive desktop
  compression.
- Decode does not redo the search. Decode reads the selected seed records,
  expands those seeds once, copies literals, and verifies hashes/lengths.
- The central engineering question is whether search, indexing, arity,
  recursive layer outputs, public presets, or transforms can make profitable
  exact spans dense enough after metadata.

What makes Telomere different from ordinary compression:

- Entropy coders exploit observed symbol frequencies inside the file.
- Dictionary coders store or infer repeated local substrings.
- Telomere searches an external deterministic generative space and stores seed
  addresses only when exact regeneration beats literal cost.
- Therefore, generic shorthand like "structured data is compressible" is not
  enough. Structure helps Telomere only if a concrete mechanism maps that
  structure into seed-addressable spans with honest decode metadata.

## Common Wrong Inferences

Avoid these recurring mistakes:

- Wrong: "This tiny laptop run found no natural matches, so Telomere is not
  viable."
  Correct: "This run was underpowered unless expected profitable hits were high
  enough that zero hits would be surprising."
- Wrong: "Rust/JSON/logs are structured, so raw hash expansion should match them
  more often."
  Correct: "Raw cryptographic expansion is structure-blind. Structure only
  matters through an explicit transform, public preset, grammar channel, source
  family table, or other non-uniform mechanism."
- Wrong: "Random data bloated, so the compressor failed."
  Correct: "Random data should bloat; this is a negative control and a guard
  against false compression claims."
- Wrong: "A planted-data win proves natural-corpus compression."
  Correct: "A planted-data win proves codec/search/accounting behavior."
- Wrong: "A transform made bytes smaller, so Telomere compressed it."
  Correct: "A transform-only win is not a Telomere seed-span win unless the
  format records the transform and selected exact generated spans beat full
  `.tlmr` accounting."
- Wrong: "GPU/ASIC work is the next step because search is slow."
  Correct: "Acceleration matters after there is a repeatable profitable workload
  worth accelerating and CPU/GPU parity exists."
- Wrong: "Hash the target span and compare that to hashed seeds."
  Correct: "Compare generated seed prefixes to raw target bytes, then verify by
  regeneration."

## Required Three-Pass Thinking

Before making a research claim, do this three-pass check:

1. Mechanism pass: identify the exact bytes, seed order, hasher, Lotus record
   cost, span length, arity, transform/preset status, and decode metadata.
2. Probability pass: estimate expected exact hits and expected profitable hits
   for the actual search budget. If the run is underpowered, say so plainly.
3. Claim-boundary pass: classify the result as implementation proof,
   accounting proof, throughput calibration, positive control, negative control,
   mechanism telemetry, or thesis-scale evidence.

If any pass is missing, do not write a sweeping conclusion.

## Agent Operating Contract

This repo punishes shallow analogy. When continuing work here, act like an
underdog research collaborator, not a generic compression-library maintainer.

- Recover the actual state before acting: inspect the dirty tree, recent
  generated artifacts, canonical docs, and relevant source code before telling
  the user what happened.
- Do not answer "what did the last run prove?" by launching another run. First
  summarize the exact changed files, measurements, hypotheses, and claim
  boundaries already present in the repo.
- Treat handoff summaries and generated ledgers as evidence to audit, not as
  truth. Cross-check any important claim against source, format docs, and the
  artifact that generated it.
- Before proposing an experiment, write the experiment contract in your own
  head: falsifiable hypothesis, expected-hit math, metadata cost, required
  compute, expected null probability, and what conclusion would be allowed.
- If the run would be underpowered and is not a correctness/accounting/control
  check, do not run it. Explain the model and the scale gap instead.
- If a result sounds exciting, try to break it before promoting it: check
  controls, held-out status, transform/preset metadata, native `.tlmr`
  accounting, decode verification, and whether the claim is raw-search or
  domain-shaped.
- If a result sounds disappointing, check whether disappointment was actually
  predicted by probability. Expected nulls are calibration, not failure.
- When the user asks for progress, report movement in proof obligations:
  stronger math, better format invariants, native decode support, cleaner
  controls, reproduced negative delta, or a specific powered falsification.
  Do not equate "more generated files" or "more unpowered searches" with
  progress.
- When committing a large research tree, first identify which changes are real
  implementation/spec changes and which are generated ledger fallout. Verify
  the gates that match the touched surface before committing.

## Progress Definition

Useful progress in Telomere is one of:

- a tighter first-principles probability or byte-accounting model
- a codec/format invariant made explicit in code, docs, or tests
- a planted/control result that proves implementation behavior without claiming
  natural prevalence
- a native `.tlmr` result that decodes without a Python sidecar and beats full
  on-disk accounting
- a held-out, non-planted, controlled result whose mechanism is explicit
- a falsifier for a specific powered hypothesis or mechanism lane
- a reproducible throughput/memory calibration needed by the model

Not useful by itself:

- running a larger laptop search whose expected profitable hits are still near
  zero
- treating a null result as a broad conclusion without power math
- adding generated reports that only restate stale evidence
- promoting transform-only byte reduction as Telomere compression
- claiming general compression from a domain-shaped public preset result

## Math-First Research Workflow

Default to probability modeling before empirical search. This project is expected
to need datacenter-scale search for thesis-level evidence, so laptop runs are
usually the wrong tool for answering big questions.

When asked for research judgment, do this in order:

1. Build the expected-hit and byte-accounting model from first principles.
2. State what scale of compute would be needed for the hypothesis to be powered.
3. Use existing artifacts only as calibration points for throughput, memory,
   implementation correctness, and false-positive behavior.
4. Propose the smallest experiment that would change the model, if any exists.

Do not run more Python experiments, seed searches, generated ledgers, or broad
regeneration loops just because a question is open. A run is allowed only when
it is one of:

- a direct implementation correctness check
- a byte-accounting or format-regression check
- a throughput/memory calibration needed by the model
- a positive/negative control that should be small by design
- an explicitly powered search whose expected-hit math predicts meaningful
  evidence at the requested scale
- an explicit user request to regenerate artifacts

If an experiment is not powered and not one of those categories, do not run it.
Write the model instead.

Generated research artifacts are not a substitute for thinking. Do not chase
stale generated hashes or run a cascade of Python generators during conceptual
research unless the user explicitly asked for artifact regeneration or release
verification.

Do not check in massive low-level generated JSON row matrices as if they were
source. Keep code, canonical docs, compact evidence summaries, and runtime UI
inputs in git; treat bulky experiment matrices as reproducible build artifacts
unless the user explicitly asks to preserve one for audit.

## Architecture Map

| Module | Purpose |
| --- | --- |
| `src/hasher.rs` | `SeedExpander` trait plus BLAKE3/SHA-256 implementations |
| `src/seed.rs` | rayon-parallel brute-force seed search |
| `src/seed_index.rs` | canonical index-to-seed bijection |
| `src/header.rs` | Lotus record codec, arity 1-5 plus literal (J1D1 value 5 on the wire) |
| `src/tlmr.rs` | `.tlmr` v1 header: 5-byte `TLMR` magic + version prefix followed by a Lotus bit stream that carries header fields and records |
| `src/tlmr_v2.rs` | `.tlmr` v2 recursive header, descriptors, and records |
| `src/seed_expansion_index.rs` | exact generated-prefix seed expansion index |
| `src/indexed.rs` | indexed v2 compression and span selection |
| `src/streaming.rs` | CPU stratified target-span streaming matcher |
| `src/compress.rs` | one-layer compression and run summaries |
| `src/config.rs` | runtime config and validation |
| `src/lib.rs` | public API and decompression |
| `src/main.rs` | supported `telomere` CLI |

## Critical Constraints

- Seed enumeration order is consensus-critical: 1-byte seeds first, then 2-byte,
  then 3-byte, each bucket in big-endian order.
- Lotus arity 2 is valid. It is not reserved.
- The literal marker on the wire is Lotus J1D1 value `5` (6 bits in J1D1's
  largest tier). `0xFF` is an internal in-memory `DecodedHeader.arity` sentinel
  only; it never appears on the wire.
- `.tlmr` v1 is a 5-byte raw `TLMR` magic + version prefix followed by a single
  Lotus bit stream. The bit stream carries hasher kind, Lotus preset, layer
  count, lengths, and output hash, then the records payload. The total
  on-disk size is variable, not a fixed 40-byte header.
- `.tlmr` v1 compressed records encode the canonical seed index via the Lotus
  J3D2 tiered integer codec (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`). The codec
  is provided by the sibling crate at `../lotus/src/lib.rs`.
- `.tlmr` v1 `layer_count` is always `1`; recursive output must use `.tlmr` v2.
- Indexed lookup must compare `expand(seed)[0..span_len]` to target spans, never
  `hash(target_span)` to `hash(seed)`.
- Indexed compression groups active spans into equal-length tiers before lookup.
- The header-selected hasher is authoritative during decompression.

## Standing Research Assumptions

Do not relitigate these points unless new math, new code, or new measurements
directly challenge them:

- Telomere is a large-compute research project. Laptop runs are not expected to
  exercise the full thesis unless the expected-hit math says they are powered.
- The purpose of small tests is usually to prove correctness, accounting,
  reproducibility, and controls, not to decide whether datacenter-scale search
  can work.
- A missing hit in a small search is normally the expected outcome. It is not
  inherently interesting and must not become a broad conclusion.
- The scientifically interesting question is not "did this tiny run find a
  miracle match?" but "how does hit probability, metadata cost, and throughput
  scale as search budget changes?"
- Compression claims must distinguish between raw seed search, transformed
  inputs, public presets, planted controls, and native `.tlmr` byte accounting.
- If an agent feels tempted to write a sweeping conclusion, it must first write
  the exact falsifiable hypothesis and the expected-hit calculation that would
  make that conclusion valid.
- Do not "summarize" Telomere by flattening it into normal compression
  categories. Explain the seed-addressed exact-regeneration mechanism first,
  then explain which evidence class is being discussed.

## Reasoning Discipline

Telomere is not a normal compression project. Do not reason from generic
compression folklore, keyword similarity, or pattern matching against unrelated
projects. Stop and think through the actual mechanism before making claims.

- The core event is exact byte equality:
  `expand(seed)[0..span_len] == target_span`.
- Raw cryptographic/hash expansion is structure-blind. Rust, JSON, logs, PDFs,
  and random bytes do not become easier to match under raw seed search merely
  because they are "structured".
- Structure matters only when an explicit Telomere mechanism uses it, such as a
  public preset, reversible transform, grammar/schema transform, source-family
  seed table, or protocol-specific representation.
- A laptop-scale null result is usually not evidence against the datacenter-scale
  thesis. It is evidence about that exact search budget, implementation path,
  and expected-hit regime.
- Do not say or imply that Telomere is disproven, blocked, non-viable, or
  naturally limited unless the experiment was powered to test that claim.
- Do not convert "not observed at this scale" into "does not work".
- Do not convert "not yet proven" into "probably false".
- Do not convert "structured corpus result" into a raw-hash conclusion unless an
  explicit structure-aware mechanism was active.

Before writing any research conclusion, ask:

1. What exact hypothesis was tested?
2. Was the experiment powered to test that hypothesis?
3. What did the expected-hit math predict before the run?
4. Is this result an implementation proof, accounting proof, throughput
   calibration, positive control, negative control, or thesis-scale experiment?
5. What conclusion is actually allowed by the evidence?

If those questions are not answered, report the result as preliminary telemetry,
not as research evidence.

## Experiment Interpretation Rules

Every search experiment must state or derive:

- seed count searched
- target span count
- span length in bits or bytes
- metadata cost and minimum profitable span
- expected exact hits
- expected profitable hits
- probability of zero hits under the model
- whether the run was powered for its stated hypothesis

Use this approximation for raw seed expansion unless a more exact model is
available:

```text
expected_hits = seed_count * target_span_count / 2^(8 * span_len)
```

Interpretation rules:

- If expected profitable hits are much less than `1`, then zero hits are
  expected. The correct conclusion is "underpowered for thesis evidence" or
  "calibration only".
- If expected profitable hits are large and zero hits occur, then investigate
  implementation bugs, model assumptions, corpus construction, and metadata
  accounting before drawing broader conclusions.
- Positive planted-data results prove codec/search/accounting behavior, not
  natural-corpus viability.
- Random-control bloat is expected and healthy. Do not treat it as a failure.
- Broad viability claims require thesis-scale evidence, not tiny fixture runs.
- Negative delta claims must include full `.tlmr` accounting, not only selected
  span savings.
- A laptop run can be valuable even when it finds no matches if it measures
  throughput, memory, candidate-table size, decode correctness, or false
  positive behavior. Describe that value precisely.
- A laptop run is not a datacenter-scale falsification unless the pre-run model
  predicted a high probability of profitable hits at laptop scale.

## Test And Performance Rules

- Use `max_seed_len = 1` in normal unit and integration tests.
- Do not add ignored tests to make `cargo test --all-targets` look green.
- Seed depth 2 is slow-ish; seed depth 3 is expensive.
- Random data is expected to bloat, not compress.
- Negative delta claims must come from generated artifacts with full accounting.
  If the win depends on planted data, a transform, public preset, dictionary,
  sidecar, or source-family mechanism, say so explicitly.
- Treat laptop experiments primarily as implementation checks, accounting checks,
  controls, and throughput calibration unless the expected-hit math says they are
  powered thesis tests.

## Removed From Active Architecture

- gloss tables and gloss binaries
- bloom filter stubs
- broken fuzz crate targets
- the old active 3-byte file header
- digest-prefix hash-table tools that implied `hash(block) == hash(seed)` matching
- placeholder `lotus_core` exports
- Kolyma-as-spec source prologues; `kolyma.pdf` is a symbolic corpus only

## Verification Before Completion

Run these gates after protocol or docs changes:

```powershell
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo check --features gpu --all-targets
python scripts/doc_lint.py
```
