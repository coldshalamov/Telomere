# proof_kernel — the rigorous core (evidence level 4)

Goal: compute the drift surface `E[final_bits/raw_bits]` over Telomere
profiles with **provable brackets** instead of heuristics, plus concentration
bounds, per `docs/PROOF_TARGET.md`. Canonical costs only
(`docs/FORMAT_CANONICAL.md`): arity alphabet 1..5 (`00,01,100,101,110`,
literal `111` = 3 bits), J3D1 seed field, 7-bit minimum record, marker
charged once.

| module | provides |
| --- | --- |
| `costs.py` | exact `C(a,p) = arity_cost(a) + J3D1_cost(p)`, `pstar`, Kraft self-check |
| `hit_distribution.py` | exact `M(a,r,D)`, `P(min_record ≤ r \| S,a)` (exact + stable forms), full `P(gain ≥ g)` tails |
| `selection_bounds.py` | conservative disjoint-window LOWER bound; oracle interval-scheduling UPPER bound |
| `state_recurrence.py` | `H_t[L]` histogram recurrence; pass 1 (wrapped bar) + passes 2+ (strict bar); every state is a (lower, upper) bracket |
| `superposition.py` | retained-mass per prune Δ, alternate overhead, off/approx/oracle bracket |
| `concentration.py` | bounded-differences bound: deviation probability and ε(N, α) radius |
| `run_surface.py` | grid runner → `surface.csv` (lower %, upper %, ε per point) |

Discipline:

- No hashing, no laptop search, no dictionaries/rank tables/foreign mechanisms.
- No verdict strings in any output. Surfaces, brackets, assumptions only.
- Every number is conditional on the assumptions listed in
  `docs/PROOF_TARGET.md` (uniform match law; stated source model; the bound
  actually used). The exact toy (`../telomere_exact_toy_model.py`) and
  validator (`../telomere_toy_validator.py`) are the unit tests for these
  formulas — toy percentages are never thesis evidence.

Status: scaffolding complete; surface runner functional on the default grid.
Next obligations (not yet implemented by design — see the alignment task):
source models beyond uniform (planted density ρ as a parameter), tightened
selection brackets, refresh-rule pricing hooks, kernel-vs-toy matched-settings
regression test.
