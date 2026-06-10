"""Nested superposition: bounded beam search over alternate Telomere histories.

Models the maintainer's lineage spec (235B, 235BA, 235BB, ...) at expectation
level. A variant is characterized by (cumulative excess e over the best path,
generation k). Variants are EARNED: birth intensities come from exact record
counts and the uniform hash law, never from the cap.

Key dynamics per pass, per entry of best-path length L:

- Birth: each variant born last pass (fresh content, length L+e) draws
  alternates once: lambda(c) = cnt_exact_arity1(c) * 2^-(L+e), retained when
  0 <= c - L <= prune_delta, child generation k+1 <= nesting cap.
- Conversion: the same fresh content may match a record CHEAPER than the best
  path: P = sum_{c < L} cnt(c) * 2^-(L+e) — the 2^-e toll, charged honestly
  because the expansion must reproduce the bloated variant's bits.
- Staleness: a variant searched once is stale forever; only the birth flux
  creates new dice. Population growth is therefore a branching process whose
  long-run flux (births/pass) is what sustains both conversions and fresh
  window-combo trials.
- Pruning: cap C keeps the C lowest-excess variants (truncation in excess
  order). Dominance pruning removes identical-content duplicates (probability
  ~2^-(L+e), negligible at these lengths; modeled as an epsilon and reported).
  Marginal-value pruning drops a variant class when its expected per-pass
  future contribution (conversion + combo flux) falls below a penalty.

Outputs per (delta, cap, nesting): avg live variants, avg nesting depth,
excess distribution, fresh-flux fraction, combo multiplier (conservative and
optimistic), conversion gain bits/entry/pass, memory and compute growth.

Wire charge: zero. Everything here is encoder working state; only selected
records serialize. Memory/compute are reported separately, as required.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from costs import (
    j3d1_cost_for_payload_width,
    payload_width_count_exact,
    payload_width_count_le,
)

ARITY1_BITS = 2


@lru_cache(maxsize=None)
def _cnt_exact_arity1_cost(cost: int, depth_bits: int) -> int:
    """Seeds whose arity-1 record cost is exactly ``cost``, within depth."""

    total = 0
    cap = 1 << depth_bits
    for pw in range(1, cost + 1):
        c = ARITY1_BITS + j3d1_cost_for_payload_width(pw)
        if c == cost:
            le_w = min(payload_width_count_le(pw), cap)
            le_p = min(payload_width_count_le(pw - 1), cap)
            total += max(0, le_w - le_p)
        elif c > cost:
            break
    return total


@lru_cache(maxsize=None)
def _conversion_intensity(length_bits: int, content_bits: int, depth_bits: int) -> float:
    """Expected strict wins (< length_bits) for fresh content of content_bits."""

    lam = 0.0
    for c in range(7, length_bits):  # 7 = smallest arity-1 record
        cnt = _cnt_exact_arity1_cost(c, depth_bits)
        if cnt:
            lam += cnt * (2.0 ** -(content_bits))
    return lam


@lru_cache(maxsize=None)
def _conversion_gain(length_bits: int, content_bits: int, depth_bits: int) -> float:
    gain = 0.0
    for c in range(7, length_bits):
        cnt = _cnt_exact_arity1_cost(c, depth_bits)
        if cnt:
            gain += cnt * (2.0 ** -(content_bits)) * (length_bits - c)
    return gain


@dataclass(frozen=True)
class NestedResult:
    prune_delta: int
    cap: int
    nesting: int
    avg_variants: float
    avg_nesting_depth: float
    excess_distribution: dict[int, float]
    steady_flux_per_pass: float
    fresh_flux_fraction: float
    combo_multiplier_conservative_a5: float
    combo_multiplier_optimistic_a5: float
    conversion_gain_bits_per_entry_pass: float
    conversion_pct_of_entry: float
    memory_variants_per_entry: float
    compute_searches_per_entry_pass: float
    marginal_pruned_classes: int
    dominance_epsilon: float


def evolve(
    length_bits: int,
    depth_bits: int,
    prune_delta: int,
    cap: int,
    nesting: int,
    passes: int = 30,
    marginal_pruning: bool = False,
    marginal_penalty_bits: float = 1e-6,
) -> NestedResult:
    # population[(e, k)] = expected live variants; flux = born this pass.
    population: dict[tuple[int, int], float] = {}
    flux: dict[tuple[int, int], float] = {(0, 0): 1.0}  # the main path, fresh at pass 1
    total_conv_gain = 0.0
    total_searches = 0.0
    pruned_classes: set[tuple[int, int]] = set()

    conv_hist: list[float] = []
    search_hist: list[float] = []
    for _ in range(passes):
        new_flux: dict[tuple[int, int], float] = {}
        conv_gain = 0.0
        searches = 0.0
        for (e, k), born in flux.items():
            content = length_bits + e
            searches += born  # one alternate-search per fresh content
            conv_gain += born * _conversion_gain(length_bits, content, depth_bits)
            if k >= nesting:
                continue
            for e_child in range(0, prune_delta + 1):
                c = length_bits + e_child
                cnt = _cnt_exact_arity1_cost(c, depth_bits)
                if not cnt:
                    continue
                lam = cnt * (2.0 ** -content)
                key = (e_child, k + 1)
                if marginal_pruning:
                    contrib = _conversion_gain(length_bits, length_bits + e_child, depth_bits)
                    contrib += (2.0 ** -e_child) * 0.01
                    if contrib < marginal_penalty_bits:
                        pruned_classes.add(key)
                        continue
                new_flux[key] = new_flux.get(key, 0.0) + born * lam
        # Beam churn: candidates compete with incumbents by excess; the cap
        # evicts the worst, it does not block admissions. Admitted newcomers
        # are next pass's fresh parents (their contents get searched once).
        merged: dict[tuple[int, int], float] = dict(population)
        for key, count in new_flux.items():
            merged[key] = merged.get(key, 0.0) + count
        admitted: dict[tuple[int, int], float] = {}
        kept: dict[tuple[int, int], float] = {}
        total = 0.0
        for key, count in sorted(merged.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            room = max(0.0, cap - total)
            if room <= 1e-15:
                break
            take = min(count, room)
            total += take
            kept[key] = take
            born_here = new_flux.get(key, 0.0)
            if born_here > 1e-15:
                # fraction of this class's kept mass that is newly admitted
                admitted[key] = min(take, born_here)
        population = kept
        flux = admitted
        conv_hist.append(conv_gain)
        search_hist.append(searches)
    total_conv_gain = sum(conv_hist[-5:]) / max(1, len(conv_hist[-5:]))
    total_searches = sum(search_hist[-5:]) / max(1, len(search_hist[-5:]))
    n = sum(population.values())
    excess_dist: dict[int, float] = {}
    depth_sum = 0.0
    for (e, k), count in population.items():
        excess_dist[e] = excess_dist.get(e, 0.0) + count
        depth_sum += k * count
    steady_flux = sum(flux.values())
    fresh_fraction = steady_flux / n if n > 0 else 0.0
    # window combo multipliers for arity 5 (excess-tolled scores)
    score = 1.0 + sum(count * (2.0 ** -e) for (e, k), count in population.items() if k > 0)
    optimistic = score**5
    per_entry = score
    conservative = 1.0 + 5 * (per_entry - 1.0)
    dominance_eps = sum(
        count * (2.0 ** -(length_bits + e)) for (e, k), count in population.items()
    )
    return NestedResult(
        prune_delta=prune_delta,
        cap=cap,
        nesting=nesting,
        avg_variants=n,
        avg_nesting_depth=(depth_sum / n if n > 0 else 0.0),
        excess_distribution={e: round(c, 6) for e, c in sorted(excess_dist.items())},
        steady_flux_per_pass=steady_flux,
        fresh_flux_fraction=fresh_fraction,
        combo_multiplier_conservative_a5=conservative,
        combo_multiplier_optimistic_a5=optimistic,
        conversion_gain_bits_per_entry_pass=total_conv_gain,
        conversion_pct_of_entry=100.0 * total_conv_gain / length_bits,
        memory_variants_per_entry=n,
        compute_searches_per_entry_pass=total_searches,
        marginal_pruned_classes=len(pruned_classes),
        dominance_epsilon=dominance_eps,
    )


def sweep(length_bits: int = 11, depth_bits: int = 96) -> list[NestedResult]:
    out = []
    for delta in (0, 1, 2, 4, 8, 16, 32, 64):
        for cap in (1, 2, 3, 4, 8, 16, 32):
            for nesting in (1, 2, 3, 4, 8):
                if cap == 1 and (delta > 0 or nesting > 1):
                    continue
                out.append(evolve(length_bits, depth_bits, delta, cap, nesting))
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=11)
    parser.add_argument("--depth", type=int, default=96)
    args = parser.parse_args()
    results = sweep(args.length, args.depth)
    results.sort(key=lambda r: -(r.conversion_gain_bits_per_entry_pass))
    print(f"entry {args.length} bits, depth 2^{args.depth} | top by steady conversion gain/pass:")
    print("delta cap nest | variants nest_avg flux fresh% | conv bits/pass conv% | mult(cons) | searches/pass")
    for r in results[:10]:
        print(
            f"{r.prune_delta:5d} {r.cap:3d} {r.nesting:4d} | "
            f"{r.avg_variants:8.3f} {r.avg_nesting_depth:8.3f} {r.steady_flux_per_pass:6.3f} {100*r.fresh_flux_fraction:6.2f} | "
            f"{r.conversion_gain_bits_per_entry_pass:12.6f} {r.conversion_pct_of_entry:6.3f}% | "
            f"{r.combo_multiplier_conservative_a5:9.4f} | {r.compute_searches_per_entry_pass:10.3f}"
        )
    flat = [r for r in results if r.nesting == 1 and r.cap == 4 and r.prune_delta == 8]
    deep = [r for r in results if r.nesting == 8 and r.cap == 4 and r.prune_delta == 8]
    if flat and deep:
        f, d = flat[0], deep[0]
        print(f"\nnesting effect at delta=8 cap=4: flat conv {f.conversion_gain_bits_per_entry_pass:.6f} "
              f"vs nested {d.conversion_gain_bits_per_entry_pass:.6f} bits/entry/pass "
              f"({d.conversion_gain_bits_per_entry_pass/max(f.conversion_gain_bits_per_entry_pass,1e-300):.2f}x); "
              f"flux {f.steady_flux_per_pass:.4f} vs {d.steady_flux_per_pass:.4f}")
