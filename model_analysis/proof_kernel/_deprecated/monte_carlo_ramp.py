"""Monte Carlo of the RAMP spec — real draws, no permutation, no epochs.

Spec under test (decode-trivial: parse, expand recursively, strip):
  block 8; constant alphabet single=2b a1=2b a2..a5=3b; J3D1 seed fields
  (payload cap 508 — no reach ceiling in range); PUBLIC depth schedule
  D_t = D0 + r*t; freshness = ONLY (a) new content searched over the full
  range [0, D_t], (b) unchanged windows searched over the slice
  [D_{t-1}, D_t] — genuinely new seeds, content-only expansion, zero
  metadata, no refresh operator at all.

Window trials per pass (exact, sampled):
  changed window: p = M(budget, D_t) * 2^-span
  stale window:   p = (M(budget, D_t) - M(budget, D_{t-1})) * 2^-span
Cost given hit sampled from exact per-cost counts (within the active range).

Run: python monte_carlo_ramp.py --entries 50000 --passes 200 --d0 12 --rate 1
"""

from __future__ import annotations

import argparse
import json
import pickle
import random
import time
from pathlib import Path

import costs

costs.LOTUS_SEED_INDEX_J_BITS = 3  # J3D1: payload cap 508
ARITY_BITS = {1: 2, 2: 3, 3: 3, 4: 3, 5: 3}
SINGLE_BITS = 2
BLOCK_BITS = 8
for _n in dir(costs):
    _f = getattr(costs, _n)
    if hasattr(_f, "cache_clear"):
        _f.cache_clear()


def m_le(arity: int, budget: int, depth_bits: int) -> int:
    field_budget = budget - ARITY_BITS[arity]
    best = 0
    for pw in range(1, min(field_budget, 508) + 1):
        if costs.lotus_cost_for_payload_width(pw, 3) <= field_budget:
            best = pw
        else:
            break
    if best < 1:
        return 0
    return min(costs.payload_width_count_le(best), 1 << min(depth_bits, 120))


_samplers: dict = {}


def window_model(span: int, arity: int, d_now: int, d_prev: int, fresh: bool):
    key = (span, arity, d_now, d_prev, fresh)
    if key in _samplers:
        return _samplers[key]
    budget = span - 1
    m_hi = m_le(arity, budget, d_now)
    m_lo = 0 if fresh else m_le(arity, budget, d_prev)
    m = m_hi - m_lo
    if m <= 0:
        _samplers[key] = (0.0, None)
        return _samplers[key]
    p = m * (2.0 ** (-span)) if span > 40 else 1.0 - (1.0 - 2.0 ** (-span)) ** m
    p = min(1.0, p)
    floor = ARITY_BITS[arity] + 3 + 1 + 1
    weights = []
    for c in range(floor, budget + 1):
        cnt = (m_le(arity, c, d_now) - (0 if fresh else m_le(arity, c, d_prev))) - \
              (m_le(arity, c - 1, d_now) - (0 if fresh else m_le(arity, c - 1, d_prev)))
        if cnt > 0:
            weights.append((c, cnt))
    if not weights:
        _samplers[key] = (0.0, None)
        return _samplers[key]
    total = sum(w for _, w in weights)

    def sample(rng):
        x = rng.random() * total
        acc = 0.0
        for c, w in weights:
            acc += w
            if x <= acc:
                return c
        return weights[-1][0]

    _samplers[key] = (p, sample)
    return _samplers[key]


def run(seed: int, n: int, passes: int, d0: int, rate: float, budget_s: float = 32.0):
    tag = Path(f"_mcr_{seed}_{n}_{d0}_{rate}.pkl")
    if tag.exists():
        lengths, changed, rows = pickle.loads(tag.read_bytes())
    else:
        lengths = [SINGLE_BITS + BLOCK_BITS] * n
        changed = [True] * n
        rows = []
    raw = n * BLOCK_BITS
    rng = random.Random(seed * 99991 + len(rows))
    t0 = time.time()
    while len(rows) < passes and time.time() - t0 < budget_s:
        p_i = len(rows) + 1
        d_now = d0 + int(rate * p_i)
        d_prev = d0 + int(rate * (p_i - 1)) if p_i > 1 else 0
        bits_before = sum(lengths)
        new_len, new_chg = [], []
        accepted = 0
        i, L = 0, len(lengths)
        while i < L:
            done = False
            for arity in range(min(5, L - i), 0, -1):
                win_changed = any(changed[i : i + arity])
                span = sum(lengths[i : i + arity])
                p, sampler = window_model(span, arity, d_now, d_prev, win_changed)
                if sampler is None:
                    continue
                if rng.random() < p:
                    cost = sampler(rng)
                    if cost < span:
                        new_len.append(cost)
                        new_chg.append(True)
                        accepted += 1
                        i += arity
                        done = True
                        break
            if not done:
                new_len.append(lengths[i])
                new_chg.append(False)
                i += 1
        lengths, changed = new_len, new_chg
        bits_after = sum(lengths)
        rows.append({"pass": p_i, "d": d_now, "accepted": accepted,
                     "ratio": bits_after / raw,
                     "net_pct": 100.0 * (bits_before - bits_after) / max(bits_before, 1)})
    tag.write_bytes(pickle.dumps((lengths, changed, rows)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", type=int, default=50_000)
    ap.add_argument("--passes", type=int, default=200)
    ap.add_argument("--d0", type=int, default=12)
    ap.add_argument("--rate", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    rows = run(args.seed, args.entries, args.passes, args.d0, args.rate)
    import statistics
    nn = len(rows)
    out = {
        "spec": f"RAMP J3 d0={args.d0} +{args.rate}/pass, no refresh op, no metadata",
        "passes_done": nn, "ratio_now": round(rows[-1]["ratio"], 6),
        "accepts_last": rows[-1]["accepted"],
        "payback": next((r["pass"] for r in rows if r["ratio"] < 1.0), None),
        "rate_by_decade": {str(d): round(statistics.mean(r["net_pct"] for r in rows[d:d+10]), 5)
                           for d in range(0, nn - 9, 10)},
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
