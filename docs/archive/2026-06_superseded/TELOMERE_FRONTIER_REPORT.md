# Telomere Frontier Report

What is not reached, and the dependency map that now organizes the program.
Companion to `TELOMERE_VIABILITY_TARGET.md` and the ledger (two correction
notices; the second restructured the architecture).

## The dependency map (the real frontier)

Every refreshed lane in the evolving-stream model needs per-record
birth-epoch knowledge at decode, in increasing order of demand:

| epoch channel needed | lanes unlocked | rate (audited kernel unless noted) | status |
| --- | --- | ---: | --- |
| none (content-only dice, no refresh) | none — staleness kills all | ~0 by pass 4 | dead (dice-validated) |
| **bundles only** (affine-stride fingerprint; arity-1 length-preserving lemma) | **primary: const cheap-single + J2 + permutation** | **0.202 %/pass, pb 76, 0.478@500** | math_candidate pending the stride-induction proof (v2 obligation 1) |
| bundles + singles (no channel known) | pass-1-only alphabet schedules | 0.309 %/pass, pb 53, 0.382@500 | conditional |
| everything incl. arity-1 dice (no channel known; impossibility sketch in ledger) | layer-masked fresh=1 | 0.397 %/pass (v-next kernel), pb 76, 0.545@500 | upper_bound |

The distance between rows is the value of each missing channel — the
frontier is now a channel-discovery problem, not a parameter search.

## Open bars

- Breakthrough ≥ 0.5 %/pass: not met (0.202 unconditional-architecture;
  0.397 at the masked upper bound).
- Crossover < 50: not met unconditionally (76; the conditional schedule
  row reaches 53).
- The stride-induction proof itself: THE milestone. Sketch status: the
  unwind processes passes top-down; at each level, bundles born at that
  level must be identified before inverting that pass's permutation;
  candidate discriminator = child strides in base coordinates;
  well-foundedness of the bottom-up coordinate recovery is the open part,
  plus the exact escape ledger (~T/N per bundle, structurally small).

## Dead, bounded, dominated (do not relearn)

- Strict layer-stack: decodes trivially, pays ~10:1 re-wrap carriage
  (maintainer's pricing, confirmed independently). Dead.
- Position-only salting: emission-replication deadlock (measured).
- Junction-density grid states: accounting artifact (ledger notice 1).
- Fixed-length runs: length field pays for itself; the codeword mint also
  costs a split either way (alphabet-tax table).
- Explicit epoch charging: ~Lotus(T) ≥ 5 bits/bundle vs ~2–4 bit gains —
  negative; inference is the only path.
- k=2 XOR at B=8, charged rechunk lanes, uncharged anything: as before.

## Reproduction

```powershell
python model_analysis/proof_kernel/_audited_chunk2.py 2 29 500 33
python model_analysis/proof_kernel/_audited_chunk.py 2 29 2 500 33
```
