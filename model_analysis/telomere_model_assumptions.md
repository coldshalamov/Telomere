# Exact toy model — every simplifying assumption and its likely bias direction

Companion to `telomere_exact_toy_model.py` / `telomere_model_report.md`.
"Bias direction" = which way the assumption likely moves the final %-of-raw,
relative to the design as specified, under the same universe.

| # | assumption | bias direction |
|---|---|---|
| 1 | **Finite seed depth 2^19** (stated bound; exact within it). Spans needing deeper first matches (≳19-bit targets and most multi-entry windows) are under-hit. | **Overstates** final % (misses deep wins). This is the toy/theory boundary; the distributional layer carries depth as a free parameter. |
| 2 | **b = 6-bit blocks**: the 3-bit once-only marker is 50% of a block; toy economics are dominated by it. | Overstates final % vs larger blocks. The toy grounds *mechanism*, not economics. |
| 3 | **MAX_W = 48-bit window cap** on span targets. At this depth, P(hit) for >48-bit spans ≤ 2^(19−48); skipped windows are counted nowhere. | Negligible at this depth; direction: overstates %. |
| 4 | **blake2b stand-in expander** (digest 8 B) rather than SHA-256. Under the uniform match law both behave identically; no deviation was observed (§5 of METHODS_APPENDIX matched the law). | None expected; unverified for SHA-256 specifically. |
| 5 | **Superposition state = at most one retained alternate per entry, harvested from arity-1 exact matches only** (the 236A/236B pattern). Multi-candidate sets and bundle-born alternates are not retained. | **Understates** superposition's state space; conversions found by richer state ≥ conversions found here. |
| 6 | **Alternate-form combinations** enumerated exhaustively per window (≤ 2^A combos); no cap was hit at N=3000. | None. |
| 7 | **Greedy largest-gain non-overlapping selection** (one policy). Left-to-right and oracle interval scheduling not yet compared (distributional layer). | Unknown sign; greedy ≤ oracle by definition. |
| 8 | **Literals at bit granularity** (no byte-alignment pad as in the wire format §3). | Understates final % slightly (favors the mechanism). |
| 9 | **Zero-bit deterministic shuffles assumed free**: the toy applies them and pays nothing. Decode verification then **fails on order recovery** in every shuffle mode (see report §4) — the assumption that zero-bit shuffles are decoder-invertible under in-place untagged recursion did not survive the round-trip test in this implementation. | Shuffle modes' sizes are **conditional** on solving order recovery (e.g., per-layer descriptors), which would add the descriptor cost not charged here. Understates %. |
| 10 | **N = 3000 blocks, one RNG stream (seed 42)**: single sample of the input universe; pass-level accept counts of 0–6 carry Poisson-level noise. | Either direction, small; rerun with other seeds to bound. |
| 11 | **Tolerated-bloat mode commits** worse-by-≤tol records permanently; no rollback if the hoped-for later harvest does not arrive. | As specified by the mode; F-mode results measure exactly this rule. |
| 12 | **No planted control in this run** (mechanism focus). The identical machine on planted input was shown to net-compress in `full_machine_sim.py`. | n/a. |
