#!/usr/bin/env python3
"""Exact per-arity format arithmetic for the Golden Config sweep.
No simulation here: pure counting against pinned J3D1 Lotus widths.
Outputs golden_format_arithmetic.json consumed by the MC.
"""
import json, math
from costs import payload_width_count_exact, j3d1_cost_for_payload_width, \
    max_payload_width_for_j_bits

PROFILES = {
    # arity codeword bits; literal marker bits
    "payback":   {"lit": 2, "cw": {1: 2, 2: 3, 3: 3, 4: 3, 5: 3}},
    "canonical": {"lit": 3, "cw": {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}},
}
MAX_PW = 200  # payload widths to enumerate (covers every window here)

def arity_stats(B, a, cw_bits, c_max):
    """Exact: count + win-sum of seeds with record cost <= c_max (< W)."""
    W = a * B
    S = 0; win_sum = 0.0; tail_sum = 0.0
    by_cost = {}
    for pw in range(1, MAX_PW + 1):
        cost = cw_bits + j3d1_cost_for_payload_width(pw)
        if cost > c_max: continue
        n = payload_width_count_exact(pw)
        if n <= 0: continue
        win = W - cost
        S += n; win_sum += n * win
        if win >= 8: tail_sum += n * win
        by_cost[cost] = by_cost.get(cost, 0) + n
    if S == 0: return None
    p = S * (2.0 ** (-W))
    return dict(W=W, S=S, gap=W - math.log2(S), p=p,
                E_win=win_sum / S, tail_share=(tail_sum / win_sum) if win_sum else 0.0,
                by_cost={str(k): v for k, v in sorted(by_cost.items())})

out = {}
for B in (4, 8, 16, 24, 32):
    for prof, pdef in PROFILES.items():
        for a in (1, 2, 3, 4, 5):
            W = a * B
            for label, c_max in (("full", W - 1), ("greedy8", min(W - 1, pdef["cw"][a] + 12)),):
                st = arity_stats(B, a, pdef["cw"][a], c_max)
                if st is None: continue
                key = f"B{B}|{prof}|a{a}|{label}"
                st["c_max"] = c_max
                out[key] = st

json.dump(out, open("golden_format_arithmetic.json", "w"), indent=1)
# human table: full-depth rows
print(f"{'cfg':28s} {'W':>3} {'S(compressive)':>16} {'gap':>6} {'p/window/pass':>13} {'E[win|hit]':>10} {'tail>=8b':>8}")
for k, v in out.items():
    if k.endswith("full"):
        print(f"{k:28s} {v['W']:>3} {v['S']:>16,} {v['gap']:>6.2f} {v['p']:>13.3e} {v['E_win']:>10.3f} {v['tail_share']:>8.3f}")
