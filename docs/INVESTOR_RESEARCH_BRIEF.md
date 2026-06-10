# Telomere — Research Brief for Technical Reviewers

*June 2026. Sober summary of what is proven, what is modeled, what has
failed, and what it would take to make this commercially real. All numbers
carry evidence-class labels; the canonical result table is
`docs/TELOMERE_RESULT_LEDGER.md`.*

## What Telomere is

Telomere is content-agnostic recursive seed-search compression. A span of
the current layer is replaced by a short record naming a seed whose
deterministic hash expansion reproduces that span exactly; everything else
is carried under charged literal records. The emitted layer is itself a
bitstream, and later passes operate on it recursively. There are no
dictionaries, no entropy coding, no source modeling: the only structure
exploited is the existence of short seeds that happen to regenerate target
bits, and the only empirical assumption in the model is the uniform hash
law `P(match) = 2^-S` per (seed, content, position) trial.

It is not ZIP/zstd/LZ: those exploit within-file statistical redundancy and
saturate on their own output. Telomere's modeled mechanism is blind to
content statistics — its rate on already-compressed or encrypted-looking
bytes is modeled identical to its rate on text. That property, if it
survives implementation, is the product thesis: a second-stage compressor
for data where classical compression is already exhausted.

## Current best audited result (the headline, with its label)

The proof kernel identifies a fully charged recursive compression path
under stated assumptions — `math_candidate`: every literal and header bit
charged in its emitting layer, zero refresh metadata, greedy deterministic
selection, no oracle, no passthrough; constituent primitives decode-proven
at toy scale; the full configuration not yet wire-proven.

**Primary** (`vnext_best.json`): block 8, J2D1 seed fields, mixed
literal-run/single layer (φ=0.5, S0=262k), layer-masked expansion:

| metric | value |
| --- | ---: |
| sustained rate (ten-effective-pass min) | **+0.908 %/pass** |
| raw payback | pass **81** |
| final/raw at 200 / 500 passes | **0.810 / 0.541** |
| refresh metadata | 0 bits |
| oracle bound on the same config | +0.910 %/pass (greedy ≈ oracle) |

Reference floor (previous target, independent kernel): 0.1328 %/pass,
payback 126, 0.486 @ 500. Two independently built kernels agree within
~25%, the newer reading lower (conservative).

## What is proven vs modeled vs falsified

**Wire-proven at toy scale** (exact round trip, self-delimiting, charged
bits == wire bits): BIT_LITERAL; LITERAL_RUN (length-prefixed literal
grouping, adversarial payloads, odd tails); layer-masked / position-salted
expansion including nested two-layer decode with zero metadata; k=2 XOR
records including the salted-seed-#1 + shared-table search demonstrating
the square-root pair-space property.

**Law-validated with real SHA-256 dice** (laptop validates laws, never
viability): deterministic-search staleness (no refresh ⇒ measured zero
matches by pass 3–4, exactly as predicted); layer-masked expansion
sustains its pass-2 rate indefinitely (measured 0.13–0.18 %/pass at toy
scale vs permutation's 0.05–0.08 %; kernel conservative at every point).

**Modeled only** (`math_candidate`): every multi-pass viability number,
including the primary above.

**Falsified this revision**: position-only salted refresh (deadlocks —
pre-first-accept emission replicates the previous layer, so every query
repeats; measured dead at pass 3; the layer-indexed mask is the corrected
mechanism). Previously falsified and kept as bounds: uncharged rechunk
(the old 0.53 %/pass headline), explicit-flag rechunk (−24.7 %/pass),
decode-by-replay rechunk (Kraft-dominated, analytic).

## Why the new mechanisms matter

- **Layer-masked expansion** removes the refresh tax entirely (zero
  metadata, fresh dice for every window every pass) while keeping the seed
  table shared — this simultaneously answered the staleness problem and the
  compute-feasibility problem, which were the two weakest points of the
  prior pitch. MitM/k-XOR records, the previous compute answer, are now a
  niche (they cost ~9× in rate at small spans).
- **LITERAL_RUN** makes initial bloat a dial instead of a tax (1.0027× at
  the ε end), and re-segmentation is the legal form of rechunking (charged
  boundary headers; no discrimination channel needed).
- **J2D1** (6-bit minimum records) roughly doubles sustained rate over
  J3D1 at block-8 budgets.

## Compute and business model (separate from size accounting)

Model-derived; implemented throughput is a 60-day milestone. Masked targets
keep one shared prefix table (2^28 expansions ≈ 3 GB, built once per
profile, shared across files/passes/positions); encoding is lookup-bound at
~10M window probes per pass per raw MB. Decode is asymmetrically cheap
(~one expansion per record; ms/MB).

| machine tier | est. lookup throughput | s/pass/MB | to 1.0× (81 passes) | to 0.84× (~180) | to 0.60× (~420) | interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 CPU core (model) | 2e7/s | 0.5 | 1.5 core-yr/TB | 3.3 | 7.7 | research only |
| 64-core workstation | 1.3e9/s | 0.008 | ~9 days/TB (~$500) | ~$1.1k/TB | ~$2.6k/TB | pilots, not economics |
| GPU cluster node | ~1e9–1e10/s eff. | — | $150–500/TB | $0.3–1.1k | $0.8–2.6k | demo scale |
| ASIC/FPGA concept (HBM-backed) | ~1e11/s | — | ~$2–6/TB | ~$4–13 | ~$10–30 | **the economic regime** |

Cold-archive storage runs $12–50/TB-year; a 46% size reduction returns
$5–23/TB-year recurring against a one-time ASIC-tier compression cost of
order $10–30/TB. The business gates are therefore: (1) the uniform law
survives scaled validation, (2) an implemented pass matches the model
within ~2×, (3) ASIC-tier throughput lands within ~10× of projection.
These are exactly risks 1, 3, 9 in `TELOMERE_RISK_REGISTER.md`, each with a
kill condition.

## Post-compression product lane (context, not core proof)

Because the model is content-blind, the modeled rate on zstd/zip output
equals the modeled rate on raw bytes — while zstd(zstd(x)) gains ~0 by
construction. The 90-day pilot runs implemented passes on compressed
corpora plus random/encrypted controls to test exactly this. No classical
mechanism is used inside Telomere; zstd appears only as upstream
preprocessing in the product scenario.

## Charts and artifacts

`model_analysis/proof_kernel/charts/`: `raw_crossover.png`,
`per_pass_drift.png`, `bloat_payback_frontier.png`, `mechanism_ladder.png`.
Machine-readable: `vnext_best.json`, `vnext_sweep.json`,
`vnext_top_profiles.csv`, `bit_literal_target.json`, `cost_pin_report.json`.

## Reproduction (exact)

```powershell
python model_analysis/proof_kernel/vnext_search.py --stage rank
python model_analysis/proof_kernel/vnext_search.py --stage final
python model_analysis/proof_kernel/bit_literal_decode_proof.py
python model_analysis/proof_kernel/literal_run_decode_proof.py
python model_analysis/proof_kernel/position_salt_decode_proof.py
python model_analysis/proof_kernel/mitm_xor_decode_proof.py
python model_analysis/proof_kernel/freshness_law_validation.py
cargo run --quiet --bin v1_cost_table && python model_analysis/proof_kernel/cost_pin.py
```

## Risk register and roadmap

`docs/TELOMERE_RISK_REGISTER.md` (13 risks, each with severity, next test,
kill condition); `docs/TELOMERE_R_AND_D_ROADMAP.md` (30/60/90). Next
milestones: Lotus wire pin and long-horizon dice test (30d); v-next
reference codec with measured pass ledger vs model (60d); post-compression
pilot and ASIC go/no-go memo (90d).
