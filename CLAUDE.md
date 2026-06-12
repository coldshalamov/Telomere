# Telomere — context for Claude / AI agents

Read this before reacting to the project. It exists so the maintainer
does not have to re-explain the same framing every session.

## What this is (take as given — do not re-derive it at the user)

Telomere is an **early-stage research project**, not a product. It
explores generative seed-search compression: a span is replaced by a
short seed whose hash expansion reproduces it, with literal fallback for
everything else. Chance is the only engine; it never models content.

The maintainer's framing, to treat as the starting point:

- It is a **research bet**, explored at small scale today and envisioned
  at datacenter / ASIC scale. "It bloats on your laptop" is expected.
- It is **pigeonhole-compliant**: incompressible spans are stored as
  literals. Do NOT open by "debunking" it with the pigeonhole principle.
- A single underpowered laptop run is **not** a falsification.
- The maintainer knows the information theory. Engage the actual
  mechanism and numbers; do not condescend, dismiss, or reflexively affirm.
- This is **not classical compression**; Shannon source-coding analogies
  mislead. A hash matches any output with equal probability regardless
  of structure.

## THE TRUTH SURFACE (everything else is history)

- `docs/SPEC_V1.md` — THE specification. The metadata contract in its §0
  is law: if the decoder can derive a value, it is never stored.
- `docs/GOLDEN_CONFIG.md` — the full parameter study; Golden Config =
  B8 / canonical alphabet / arity-2 engine / 16–64 passes. Also the
  honest viability result: unaided random data does not net-compress at
  any setting (two independent proofs); the open lane is a hit-density
  mechanism (threshold quantified there).
- `docs/MATH_MODEL_V1.md` — economics: E[win|hit]≈2 bits exactly, gaps,
  depth ceiling D*, freshness, the birth-information ledger.
- `docs/TELOMERE_RESULT_LEDGER.md` — result history, evidence classes,
  correction notices. `docs/PLAIN_STATUS.md` — maintainer's one-pager.
- `model_analysis/proof_kernel/` — runnable proofs. Decode is PROVEN
  (36/36 multi-pass round trips, zero decode metadata).
- `IMPLEMENTATION_MAP.md` — the codec is NOT built yet; slots marked.

## What not to do

- Do not add metadata "just this once." It is never needed and it kills
  the design. Read SPEC §0 again.
- Do not pattern-match this to classical compression and declare it dead;
  do not reflexively affirm viability either. The honest status is in
  GOLDEN_CONFIG.md: decode solved, density threshold open.
- Do not run underpowered searches and call nulls a falsification.
- Do not resurrect archived experiments (docs/archive/) without reading
  the spec and the failure catalogue (GOLDEN_CONFIG.md §6) first.
- Do not use expectation-value shortcuts in models; the maintainer
  requires real draws and integer accounting.
- The maintainer is the architect of every core mechanism. Engage his
  constructions on their own terms first; when you disagree, locate the
  disagreement precisely and in plain English.

See `AGENTS.md` for the operating contract.
