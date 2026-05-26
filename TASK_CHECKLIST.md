# Telomere Checklist

This checklist is a compatibility snapshot. The canonical details live in
`docs/`, especially `docs/RESEARCH_PROGRAM.md` for active research work.

## Done In Current v1 Direction

- [x] Replace active 3-byte file header with 40-byte `.tlmr` v1 header.
- [x] Record hasher kind in the file format.
- [x] Record Lotus preset/version in the file format.
- [x] Record layer count and lengths so v1 decoding is unambiguous.
- [x] Make v1 output one-layer-decodable only.
- [x] Keep arity `2` as a valid compressed arity.
- [x] Encode compressed-record seed indices through the Lotus J3D2 tiered
      integer codec (`LOTUS_J_BITS = 3`, `LOTUS_TIERS = 2`) from the sibling
      `lotus` crate; small indices encode in fewer bits (e.g. arity 1, index 0
      is 8 bits).
- [x] Add config validation for core format limits.
- [x] Remove slow max-seed-len-3 defaults from normal test paths.
- [x] Delete broken fuzz crate targets.
- [x] Mark GPU as research-only while keeping `--features gpu` buildable.
- [x] Remove gloss and bloom stubs.
- [x] Remove disabled gloss binaries.
- [x] Delete `error.log` and ignore future logs.
- [x] Generate `docs/RESULTS.md` and `docs/results.json` from a script.
- [x] Add experimental `.tlmr` v2 recursive descriptors and index-free decode.
- [x] Add indexed and streaming v2 exact generated-prefix engines.
- [x] Add CLI `index build/info/verify` and v2 engine selection.
- [x] Export indexed/streaming telemetry into CLI JSON and generated benchmark
      artifacts.
- [x] Add generated matrix rows for random, planted-density, offset,
      structured, Kolyma, and recursive v2 pass-2 controls.
- [x] Add generated arity/span threshold rows for v2 span lengths 4, 8, and
      12.
- [x] Add generated sweep artifacts for span-length, planted-density, and
      recursive offset/pass curves.
- [x] Expand recursive offset/pass sweeps through pass counts `1..=4`.
- [x] Add experimental v2 `--span-step` support plus generated offset-alignment
      sweep evidence.
- [x] Add generated structured-search sweeps for block-step, byte-step,
      longer-span, and recursive seed-depth-1 controls.
- [x] Add generated seed-depth-2 economics sweeps covering a controlled
      two-byte planted seed and structured JSON control.
- [x] Add opt-in generated seed-depth-3 sweeps covering a controlled
      three-byte planted seed and structured JSON control.
- [x] Add generated reversible-transform sweeps separating generic transform
      misses from static dictionary transform-only gains.
- [x] Add generated reversible-transform manifold probes that test whether
      shallow prefix proximity can be lifted toward exact seed-span hits.
- [x] Extend transform probes with structural reversible transforms such as
      bit-reverse, nibble-swap, even/odd deinterleave, and chunk reversal.
- [x] Extend transform probes with lagged reversible residual transforms.
- [x] Add generated held-out validation for the top transform-probe leads.
- [x] Add generated bounded periodic-mask transform probes for longer prefix
      ladder search.
- [x] Add generated composed context+periodic transform probes to test whether
      residual/structural transforms and selected masks work better together.
- [x] Add generated structured-corpus matrix across JSON, Markdown, CSV,
      Rust-like source, HTML, Python-like source, SQL, TOML, XML, and log
      controls.
- [x] Extend held-out corpus validation with YAML, CSS, JavaScript-like,
      GraphQL, and Nginx-style config controls.
- [x] Add vocabulary-disjoint shadow and binary TLV/varint corpus controls to
      separate literal-token artifacts from syntax or binary-structure effects.
- [x] Add cheap corpus generalization controls for shadow CSV/YAML, natural
      prose, zlib-compressed JSON, shuffled records, and length-matched random
      bytes outside the expensive hash chain.
- [x] Add generated acceleration readiness report and ADR keeping GPU
      research-only until real kernel parity and benchmark gates exist.
- [x] Add generated hit-probability and v2 overhead theory report tied to
      observed structured-corpus and seed-depth controls.
- [x] Add generated seed-output manifold proximity diagnostics for raw,
      transformed, random, and planted controls.
- [x] Add generated near-miss forecasts that convert prefix matches into
      expected exact-hit scale.
- [x] Add generated prefix-ladder diagnostics that identify where held-out
      near misses stall before exact hits.
- [x] Add generated depth-3 prefix-frontier diagnostics that distinguish
      held-out prefix movement from exact compression wins.
- [x] Add generated bounded depth-3 compression follow-up proving the current
      prefix-frontier movement does not yet emit selected spans.
- [x] Add generated fifth-byte residual diagnostics for prefix-4 near misses.
- [x] Add generated fifth-byte steering diagnostics to test whether
      residual-derived phase masks generalize across corpora.
- [x] Add generated contextual fifth-byte steering diagnostics with null
      controls for context-conditioned masks.
- [x] Add generated bounded structural-transform search across held-out,
      vocabulary-disjoint, and binary controls.
- [x] Add generated byte-permutation transform search for finite seed-output
      byte-distribution alignment with metadata charged before promotion.
- [x] Add generated BWT/MTF/RLE transform probe showing classic
      preconditioner shortening is not counted as Lotus seed-span evidence.
- [x] Add generated grammar/channel match-discovery search for reversible
      structural streams with literal sidecars charged before promotion.
- [x] Add generated numeric value-channel match-discovery search for parsed
      integer, delta, digit-residual, and decimal streams with exact
      reconstruction metadata charged before promotion.
- [x] Add generated record/context-aware transform search for line transposes,
      field-column grouping, fixed-width columns, and record deltas with
      metadata charged before promotion.
- [x] Add generated token/dictionary transform search for lexeme replacement
      and token-order streams with dictionary metadata charged before
      promotion.
- [x] Add generated affine byte-remap search showing broad prefix-4 uplift
      still stalls before prefix-5 or exact seed-span hits.
- [x] Add generated seed-manifold residual-sidecar steering economics showing
      forced exact spans still fail net-delta promotion at span 8.
- [x] Add generated sidecar break-even math showing current held-out forced
      prefixes do not reach the raw-suffix strict-gain threshold.
- [x] Add generated residual payload compressibility bounds showing zlib/LZMA
      produce one narrow held-out sidecar signal while simpler payload models
      still miss the gate.
- [x] Add an experimental sidecar descriptor prototype proving that the narrow
      payload signal decodes but still bloats after full-stream overhead.
- [x] Add generated sidecar record-overhead budgets showing packed offset and
      seed-index tables can make the promoted row full-stream negative on
      paper.
- [x] Add a packed sidecar descriptor prototype proving one promoted held-out
      row can decode, reject corruption, and remain full-stream negative.
- [x] Add packed sidecar controls showing the packed descriptor signal remains
      narrow: one ordinary held-out negative case under strict u8-delta
      assumptions.
- [x] Add generalized packed sidecar controls showing wider offset modes encode
      every selected source row but do not improve ordinary held-out diversity.
- [x] Add frozen packed sidecar replication controls showing descriptor packing
      alone does not replicate full-stream negative rows across unrelated
      held-out corpora.
- [x] Add pre-sidecar match discovery controls showing arity 1..5 exact hits
      and selected spans are still absent across validation and replication
      corpora.
- [x] Add alignment and arity discovery controls showing block size, phase,
      span step, and arity tuning finds only unprofitable short-span exact
      hits under the current seed-depth-2 search.
- [x] Add transformed match-discovery controls showing the frozen reversible
      transform-validation matrix does not produce span-8 exact hits, selected
      spans, or metadata-profitable rows.
- [x] Add selected-lead exact discovery showing affine, periodic, and composed
      prefix-4 leads do not produce span-8 exact hits, selected spans, or
      metadata-profitable rows.
- [x] Add selected-lead depth-3 prefix and compression follow-ups showing the
      current selected-lead prefix movement still does not produce selected
      spans or negative delta.
- [x] Add bounded depth-3 frontier exact discovery over frozen depth-2
      frontier/null rows as the gate before any broad depth-3 or depth-4
      search.
- [x] Add a generated depth-4 shard plan with seed-range manifests, expected
      hit math, promotion gates, and stop rules without running depth 4 by
      default.
- [x] Add a generated search-frontier gate that blocks broad raw depth search
      and full depth-4 execution until prefix>=6, exact, selected-span, or
      sub-1-GiB forecast evidence appears.
- [x] Add a bounded generated depth-4 pilot shard so one opt-in shard can
      measure prefix movement and exact-hit evidence without promoting the
      full depth-4 bucket.
- [x] Add generated experiment queue with promotion gates, stop rules, and
      parallel research lanes.
- [x] Add generated research scorecard that consolidates proved, qualified,
      and open claims across all artifact families.
- [x] Add generated goal audit that maps the optimization architecture plan and
      research goals to concrete evidence, gaps, and release gates.
- [x] Record throughput, peak working-set memory, and configured memory limit
      in generated sweep rows.
- [x] Add Tauri host smoke tests for streaming/v2 telemetry serialization and
      indexed/v2 index-backed compression.
- [x] Add Tauri research-artifact summary command and operator ledger panel
      wiring from generated docs JSON.
- [x] Wire Tauri operator controls to real index build/info/verify commands.
- [x] Formalize the active v2 candidate model as flat verified candidates plus
      deterministic weighted interval selection.
- [x] Replace selector state cloning with score/backpointer dynamic programming
      and add a many-span regression test.
- [x] Add large-input memory scaling sweeps beyond 1 KiB fixtures.
- [x] Document and test the pre-v1 compatibility policy: unsupported unless
      explicitly migrated.
- [x] Replace full in-memory disk index construction with chunked external
      sort/merge tier writing and seed-depth-2 mmap regression coverage.
- [x] Extend generated memory-scaling sweeps through a 16 MiB planted-density
      run with measured peak working set.
- [x] Add generated viability ledger separating proved mechanism claims from
      open natural-corpus/GPU/production claims.
- [x] Formalize candidate-lattice/superposition research outside the v2 wire
      contract in `docs/CANDIDATE_LATTICE.md`.
- [x] Add held-out corpus expansion artifact for the frozen replication corpus
      bank before mutating expensive corpus/transform-validation matrices.
- [x] Add generated mechanism-experiment ranking that makes seed-table/Lotus
      preset probing the next non-depth research lane before raw depth or
      format promotion.
- [x] Add generated seed-table/Lotus preset probe with frozen splits,
      metadata accounting, exact decode proof, and promotion gates.
- [x] Add generated exact short-hit bundle economics probe with reconstructed
      verified hits, full-stream accounting, control-density gates, and stop
      rules.
- [x] Add generated whole-stream residual vector probe with frozen sidecar
      replication reconstruction, exact decode checks, corrupt rejection
      accounting, and a null promotion verdict.
- [x] Add generated expander salt ensemble probe with predeclared salted
      expanders, random-trial comparison, full-stream accounting, and a null
      promotion verdict.
- [x] Add generated schema-native public dictionary preset probe with frozen
      public entries, selector/version accounting, exact decode checks, and
      SHA-256, generic, wrong-schema, same-size random, and shadow controls.
- [x] Add generated schema-native public dictionary replication probe with
      frozen expansion corpora, paired shadow/binary controls, leakage flags,
      and a promotion-blocking control-failure verdict.
- [x] Add generated superposition telemetry with deterministic overlap
      fixtures, retained alternatives, weighted-vs-greedy comparison, and
      explained discarded candidates.
- [x] Add generated recursive structured-fixture gate with real CLI v2
      compression/decompression runs, planted offset controls, ordinary
      structured fixtures, and a promotion-blocking verdict.
- [x] Add generated scale-performance report that interprets planted-density
      memory scaling, peak/table ratio, and next-double memory estimate before
      extending bounded scale runs.
- [x] Add generated UI workflow smoke coverage for the Tauri research-artifact
      bridge, evidence DTO, preview mock, and ledger cards.
- [x] Add generated long-span bundle gate that blocks broad long-span sweeps
      until search frontier, raw-suffix, selected-span, and control gates pass.
- [x] Add generated research decision ledger that records no ready ungated
      experiment lanes, blocked actions, and evidence-based reopen triggers.
- [x] Add generated research frontier trigger board that maps unresolved gates
      to canonical artifacts, forbidden actions, subagent work packages, and
      exact reopen evidence without launching seed search.
- [x] Add generated research-team protocol that turns the frontier into
      constrained `dispatching-parallel-agents` briefs with output contracts,
      stop rules, forbidden actions, and write scopes.
- [x] Add generated active-goal completion audit that maps the objective to
      authoritative evidence and keeps the goal open while natural-corpus and
      production claims remain unproved.
- [x] Add generated blocked-requirement dispatch plan that turns the completion
      blockers into maintenance-only subagent briefs with promotion triggers
      and stop rules.

## Still Research, Not Production Claims

- [ ] Real GPU/OpenCL acceleration.
- [x] Bounded scale-performance artifacts beyond the earlier 8 MiB sweep.
- [ ] Production-scale performance artifacts beyond the current bounded
      planted-density sweeps.

## Required Smoke Gates

- [x] `cargo fmt --all -- --check`
- [x] `cargo clippy --all-targets -- -D warnings`
- [x] `cargo test --all-targets`
- [x] `cargo check --features gpu --all-targets`
- [x] `python scripts/doc_lint.py`

The full release gate, including generated artifact `--check` commands and
Tauri `cargo fmt/check/test --manifest-path src-tauri/Cargo.toml`, lives in
`docs/RELEASE_CHECKLIST.md`.
