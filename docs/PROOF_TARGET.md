# PROOF_TARGET — the active mathematical goal

**Status: definition only. This document makes no claim in either direction.**

## The goal

Fix a Telomere profile

```
P = ( block_size b,
      arity cap A in 1..5 (canonical alphabet),
      seed-depth schedule D (payload-bit bound per pass, may be unbounded),
      pass count T,
      Lotus/J3D1 record costs (canonical: docs/FORMAT_CANONICAL.md),
      replacement rule (strict record < span; optional tolerated-bloat variant),
      superposition rule (prune delta, retention, conversion),
      optional refresh rule (with its decode construction and any cost it implies) )
```

For input drawn from a stated source model, **prove or bound**

```
E[ final_bits / raw_bits ]  <  1        for sufficiently large N,
```

and, for whichever side of 1 the expectation falls on, derive a
**concentration bound**: P( |final/raw − E| > ε ) ≤ f(N, ε), so that the
expectation statement becomes a statement about every large file, not just
the average one.

The deliverable is the **drift surface**: E[final/raw] as a function of
(b, A, D, T, Δ, rule choices), with explicit lower and upper selection bounds
bracketing it, and the concentration radius at each point. Where the surface
crosses 1 — if anywhere, under whatever assumptions — is then a coordinate to
be read off, not argued about.

## Evidence ladder (what each artifact class can and cannot say)

1. **Implementation tests** (`cargo test`, golden round-trips) — prove the
   codec encodes/decodes what the spec says. Say nothing about compression.
2. **Toy validators** (`model_analysis/telomere_toy_validator.py`,
   `telomere_exact_toy_model.py`) — exhaustive tiny universes whose only job
   is to confirm the probability formulas match exact enumeration at matched
   settings. Laptop-scale nulls and toy percentages are **not thesis evidence
   in either direction**.
3. **Probability model** (`model_analysis/telomere_math_model.py` and the
   interactive `telomere_model.html`) — exact canonical costs, full gain
   distributions, depth as a free parameter. Exploratory: maps the landscape,
   flags sensitive assumptions.
4. **Proof kernel** (`model_analysis/proof_kernel/`) — the rigorous core:
   exact cost functions, exact hit-count combinatorics, recurrence with
   *provable* lower/upper selection bounds instead of approximations, and
   concentration. This is the layer allowed to support theorem-grade
   statements about the drift surface.
5. **Thesis-scale claims** — statements about real corpora at datacenter
   scale. Allowed only when derived from level 4 plus a stated source model,
   or from a powered experiment. No artifact below this line licenses them.

## Assumptions any surface statement must carry

- the uniform match law for the expander (P(prefix hit) = 2^-S per seed);
- the source model of the input (uniform / planted density ρ / family-specific);
- the selection rule actually bounded (disjoint-window lower bound vs oracle
  interval-scheduling upper bound);
- the refresh rule's decode construction and its cost, if refresh is enabled;
- canonical costs only — arity 1..5 alphabet, 3-bit literal, J3D1 seed field.
  Wide-arity extrapolations are out of scope for the kernel.

## Non-goals

No dictionary, rank-table, entropy-coding, or foreign-mechanism components.
No laptop search as thesis evidence. No verdict language anywhere in kernel
output: the kernel emits surfaces, bounds, and the assumptions they ride on.
