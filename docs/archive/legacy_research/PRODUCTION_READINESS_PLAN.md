# Telomere Production And Publication Readiness Plan

Telomere is a research prototype with one narrow native positive signal. The
next useful work is not more unpowered laptop search. It is reducing the system
to a publishable core, making the probability model explicit, and proving every
claim boundary with reproducible tests.

## Not Production-Ready Yet

The current repo should not claim production-grade compression. It has working
codec machinery, v1/v2 format support, planted controls, accounting checks, and
a native Rust source-family public-preset result. It does not yet have a stable
compatibility promise for all v2 behavior, a production acceleration path,
multi-domain replication, or powered thesis-scale evidence for raw natural
corpus search.

## Publishable Research Claim

The defensible claim is narrower and more interesting:

Telomere stores compact deterministic seed records only when exact generated
bytes beat literal bytes after full metadata accounting. Laptop nulls mostly
calibrate the search regime. A frozen Rust source-family public preset produced
native `.tlmr` v2 files that decoded back to held-out Rust source and beat full
on-disk accounting, while same-size random and paired shadow controls selected
zero spans.

That is not a universal-compressor claim. It is evidence that a domain-shaped,
public, deterministic seed-addressed universe can create exact lossless spans
dense enough to matter in at least one controlled source-family lane.

## Rebuttal Register

Rebuttal: hash outputs are random, so source structure should not help.

Answer: correct for raw cryptographic expansion. Structure matters only through
an explicit mechanism such as a public preset or transform. Claims must name the
active mechanism and keep raw-search conclusions separate.

Rebuttal: small laptop searches found no natural matches.

Answer: expected nulls do not falsify the thesis. A null result is meaningful
only when the expected profitable-hit model said hits should appear with high
probability. The canonical scaling calculator is `docs/POWER_MODEL.md`.

Rebuttal: metadata overhead will eat the win.

Answer: often yes. Every positive claim must use complete `.tlmr` accounting,
including transform descriptors, records, literals, headers, and decode
metadata.

Rebuttal: public presets are just hidden dictionaries.

Answer: the preset must be frozen, public, versioned, decode-accounted, and
tested against held-out data and paired controls. The research question is
whether such public deterministic address spaces can beat their metadata
honestly.

Rebuttal: GPU or ASIC acceleration proves viability.

Answer: acceleration is secondary. First prove a repeatable profitable workload
and CPU/GPU semantic parity. Faster search over an unpowered or wrong
distribution is not research progress.

## Software Hardening Plan

1. Freeze the supported public API around `telomere compress`,
   `telomere decompress`, index inspection, and deterministic public-preset
   decode.
2. Add golden vectors for v1 headers, v2 descriptors, Lotus arity/literal
   records, seed enumeration, public-preset descriptors, and corrupted-input
   rejection.
3. Split release gates into core gates and generated-evidence gates. Core gates
   must not require giant generated row matrices, and the UI should read compact
   snapshots rather than raw ledgers.
4. Keep generated experiment matrices out of git by default. Store compact
   summaries and exact generator commands instead.
5. Build a small benchmark suite that reports the `docs/POWER_MODEL.md` model
   row/config, throughput, memory, metadata cost, expected hits, observed hits,
   and evidence class for each run.
6. Promote any new domain lane only after native `.tlmr` decode, full byte
   accounting, held-out data, same-size random controls, paired shadow controls,
   and an explicit falsifiable hypothesis.
7. Replace per-record-only profitability decisions with payload-aware selection
   that accounts for literal fragmentation, descriptor cost, and container delta.

## Next Proof Obligations

- Keep the layered power model first-class: every future raw-search experiment
  should include the exact model config, expected-hit math, metadata cost,
  hardware profile, and allowed conclusion before compute starts.
- Prove a payload-aware selector: selected spans must improve full layer payload
  accounting, not only beat their replaced spans in isolation.
- Fit block-size, direct-bundle, adjacent-hit, and near-profitable-carryover
  model rows against controlled telemetry before treating multi-pass gains as
  evidence rather than a hypothesis.
- Replicate the native public-preset result outside Rust source, preferably on
  TypeScript, JSON Schema, protocol buffers, or structured logs.
- Replace the Tauri evidence panel's direct dependency on large generated JSON
  files with a compact research snapshot.
- Define a compatibility line: which `.tlmr` v1/v2 files are promised to decode
  across releases, and what remains experimental.
- Produce a short paper-style evidence pack: mechanism, math, format,
  controlled positive, controls, negative boundaries, and reproduction commands.
