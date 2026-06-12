# Telomere

Telomere is an early-stage research project in **generative seed-search
compression**: spans of a file are replaced by short seed records whose
hash expansions reproduce them exactly; everything else rides under
literal markers; a fixed public shuffle re-pairs the stream between
passes; decoding is stateless (no pass counts, no per-block metadata —
see the metadata contract). It is a research bet aimed at
datacenter/ASIC scale, not a zip replacement, and it is
pigeonhole-compliant by construction (worst case ~ raw + 3 bits).

## Read these, in order

1. `docs/SPEC_V1.md` — THE specification. V1 is the only spec.
2. `docs/GOLDEN_CONFIG.md` — the parameter study: what works, what
   fails, the recommended build config, and the honest viability math.
3. `docs/MATH_MODEL_V1.md` — the probability/economics model.
4. `docs/TELOMERE_RESULT_LEDGER.md` — result history with evidence classes.
5. `IMPLEMENTATION_MAP.md` — where the real codec goes when built.

Plain-language status for the maintainer: `docs/PLAIN_STATUS.md`.
Proof scripts (decode proofs, exact arithmetic, Monte Carlo):
`model_analysis/proof_kernel/`. Archived history: `docs/archive/`.

## Status (June 2026)

- Stateless multi-pass decode: **proven by construction** in the
  maintainer's exact architecture by his keep-what-decodes rule
  (`robins_opening_rules.py`, 12/12; plus 36/36 in an equivalent
  analysis model). Zero decode metadata.
- Golden Config: B=8, canonical alphabet, arity-2 engine, J3D1 Lotus,
  frontier-depth search, 16–64 passes per run.
- Honest viability: files whose reachable-span density clears the
  threshold compress; random data does not clear it unaided (counting
  law). The open research lane is the density mechanism
  (`docs/GOLDEN_CONFIG.md` §7).

## Legacy CLI

The Rust CLI (`cargo build --release`, binary `telomere`) implements an
older wire format and is kept as scaffolding reference only. The V1
codec is not yet built (`IMPLEMENTATION_MAP.md`).
