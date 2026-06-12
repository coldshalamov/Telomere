# Why these documents are archived (June 2026)

These five reports were written mid-research and headline configurations
that were later falsified or superseded:

- They cite the J2D1 evolving-stream primary (+0.202 %/pass, payback 76).
  J2D1 was Monte-Carlo falsified (28-bit payload cap → ossification), and
  the evolving-stream state model was superseded by the constant-N
  block-state model when multi-pass decode was proven by construction.
- Their open-problem framing ("epoch channel is the load-bearing risk")
  predates `v1_roundtrip_proof.py` (36/36 exact round trips, zero
  decode metadata).

Current truth surface: `docs/SPEC_V1.md`, `docs/MATH_MODEL_V1.md`,
`docs/STATE_MODEL_COMPARISON.md`, `docs/TELOMERE_RESULT_LEDGER.md`.
These archives are kept for the correction-history audit trail; nothing
in them should be cited as current.
