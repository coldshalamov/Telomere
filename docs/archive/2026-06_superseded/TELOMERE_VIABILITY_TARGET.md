# Telomere Viability Target

**Current primary class: `math_candidate`, decode pending one named proof**
(the bundle stride-inference induction — maintainer handoff v2, obligation
1). Single empirical assumption: uniform hash law `P(match) = 2^-S`. Full
result table and the two correction notices:
`docs/TELOMERE_RESULT_LEDGER.md`. Machine-readable:
`model_analysis/proof_kernel/audited_primary.json`.

## Primary target

Audited kernel (`entry_state.py`; harness reproduces the prior reference to
five decimals), block 8:

- **constant** alphabet, all passes: single `00` (2 bits), a1 `01` (2),
  a2 `100` (3, a +1 tax charged and netted in the ledger's alphabet-tax
  table), a3–a5 3 bits — Kraft = 1, parse needs no epochs
- **J2D1** seed fields (per-file profile constant; min record 6 bits),
  depth 29 ≈ the J2 payload cap (= the depth ceiling D*)
- permutation + neutral swaps refresh, 3 charged bits/pass,
  **content-only expansion** (dice carry no pass key)
- greedy; superposition delta 16 / cap 4 (earned)

| metric | value |
| --- | ---: |
| ten-effective-pass minimum | **+0.2023 %/pass** |
| ten-effective-pass average | +0.2470 %/pass |
| pass-1 wrap | **1.2369** |
| raw payback pass | **76** |
| final/raw @ 50 / 100 | 1.079 / 0.935 |
| final/raw @ 200 / 500 | **0.7420 / 0.4785** |
| refresh metadata | 3 bits/pass (permutation selector) |

Previous audited target (J3 canonical): 0.1328 %/pass, payback 126, 0.832 @
200, 0.486 @ 500 — beaten on every axis.

## The one load-bearing dependency

Un-permuting the evolving stream at decode requires identifying which
BUNDLES were born in each pass. Supporting lemma (new this revision):
arity-1 replacements preserve sequence length, so arity-1 birth times are
irrelevant to the unwind — only bundles matter, and bundles carry the
affine-stride fingerprint (children adjacent at birth sit at the birth
pass's stride in base order). Required proof: the bottom-up induction is
well-founded + the exact escape ledger (~T/N per bundle). This is
obligation 1 of the maintainer's handoff and the program's next milestone.
Charging epochs explicitly instead (~Lotus(T) ≥ 5 bits/bundle vs ~2–4 bit
bundle gains) is priced and negative — inference is the only path.

## Conditional and upper-bound lanes (label, do not headline)

- Pass-1-only 2-bit single (alphabet schedule): 0.309 %/pass, payback 53,
  0.382 @ 500 — CONDITIONAL on a singles-epoch channel; none is known
  (singles have no stride).
- Layer-masked expansion (fresh = 1, zero metadata): 0.397 %/pass on the
  v-next kernel — UPPER BOUND; needs pass-varying dice keys for everything
  including arity-1; impossibility sketch in the ledger. Law-validated as a
  law; undecodable as charged.

## Compute story (separate from size)

Content-only expansion keeps the audited compute story: one shared prefix
table to D* (2^29 ≈ 6–8 GB at J2 depth), built once; per-pass work is
lookups over fresh windows. Decode adds the stride tests (≤ T per bundle,
reported as decode compute, not size).

## Reproduction

```powershell
python model_analysis/proof_kernel/_audited_chunk2.py 2 29 500 33   # primary (chunked; rerun to resume)
python model_analysis/proof_kernel/_audited_chunk.py 3 96 3 500 33  # reference reproduction
python model_analysis/proof_kernel/freshness_law_validation.py
```
