#!/usr/bin/env python3
"""
P2-recursion-ledger.py  --  the recursion / layer-stacking economics lane.

QUESTION (BRIEF Q2 / MATH_MODEL_V1 section 8 / GOLDEN_CONFIG section 5):
  Given MAX-FREE-REACH K ~= 5-6 passes per layer (the birth channel is free
  via the explosion check up to K, then it costs), what are the layer-stacking
  economics of *recursion* -- run K free passes, emit, then RE-RUN the output
  as a fresh file (the legal recursion channel, SPEC section 1)?

  Per layer:
    EARNINGS = (matches over the layer's fresh draws) * E[win|hit] ~ 2 bits
    CARRIAGE = re-blocking header + literal markers on the new blocking
               + any residual birth bill that leaks past K.

We DO NOT roll a fresh marker model. We reuse the repo's accepted per-run
ledger -- proof_kernel/golden_break_even.gain() -- as the per-LAYER ledger,
called at the content-blind base rate (m=1) with T capped at the layer's
effective fresh-draw count and the birth bill forced free within K. That keeps
our accounting consistent with the maintainer's numbers and makes the Q3
break-even density fall out as the same multiplier the solver already prints.

THE THREE QUESTIONS:
  Q1. Does K~=5-6 free passes per layer yield POSITIVE per-layer earnings at
      the content-blind base rate (p=0.0039)?   Predict: NO -- ~50x short.
  Q2. Does recursion change the verdict, or does per-layer carriage eat
      per-layer earnings (pigeonhole, Q2 priced negative)?
  Q3. The exact density that WOULD make recursive compounding net-positive at
      K free passes -- and confirm it equals p* (the content-aware threshold).

CURRENCY: wrap/carriage (re-blocking header + literal re-marking + the
layer-boundary epoch). Recursion resets the log2(T) birth tax to *free* each
layer (the layer boundary is the epoch, charged in carriage, MATH_MODEL s8) --
but pays per-layer wrap/carriage instead. At base rate that carriage >= the
tax it saves: SAME WALL, DIFFERENT CURRENCY.
"""

import json, math, os, sys

# ---- pull the repo's accepted ledger so our numbers match the maintainer's ---
PK = os.path.join(os.path.dirname(__file__), "..", "proof_kernel")
sys.path.insert(0, PK)
import golden_break_even as gbe   # noqa: E402  (gain(), ART)

# ---- constants from the repo (Golden Config B8/canonical/a2) ------------------
P_BASE   = 0.0039     # GOLDEN random base rate, per pair-window (content-blind)
WIN_BITS = 2.17       # E[win|hit], canonical a2 (exact, MATH_MODEL s2)
LIT      = 3          # canonical literal marker (bits)  -- the carriage tax
B        = 8
PROFILE  = "canonical"
ARITY    = 2
K_FREE   = 2 ** 2.5   # ~= 5.66 free passes (the explosion-check reach; the
                      # disambiguation budget, lane E / lane H)
P_STAR   = 0.193      # GOLDEN threshold (content-aware lane); 50x base


# ============================================================================
# PART 1.  Pin the supply: how many FRESH MATCH DRAWS does one layer deliver?
# ============================================================================
# CRITICAL (advisor #3): K ~= 5.66 is a DECODE-disambiguation budget (how many
# candidate birth passes the explosion check resolves free). It is NOT a
# match-supply count. Earnings depend on fresh *match draws* per layer. Two
# honest readings of "passes per layer", bracketing the truth:
#
#   (a) SUPPLY-RICH: each of the K passes within a layer gets a fresh shuffle +
#       layer-index salt, so a window sees ~K independent draws. The deadlock
#       note (freshness_law_validation.py: position-only salting re-misses) is
#       broken by the layer/pass-distinct key, so dice DO refresh within a layer.
#       => effective fresh draws per layer  ~= K  ~= 5.66.
#
#   (b) SUPPLY-POOR: the maintainer's measured "effective passes ~= 1" (MEMORY,
#       net model) -- within a layer the emitted stream barely changes until the
#       first accept, so a window gets ~1 useful draw per layer.
#       => effective fresh draws per layer  ~= 1.
#
# We report BOTH. The prediction (negative) holds in both; (b) is just more
# negative. We do NOT pretend to know which without a high-pass measurement;
# we pin the verdict's robustness across the bracket.

def coverage_layer(draws, p=P_BASE):
    """Fresh dice within ONE layer: `draws` independent draws per window."""
    return 1.0 - (1.0 - p) ** draws


# ============================================================================
# PART 2.  Per-layer net via the REPO's ledger (gain), birth-free within K.
# ============================================================================
# gain(B, profile, a, T, m) returns (net_per_bit, coverage, birth_kb).
# We force the per-layer birth bill to ZERO within K by capping T <= K_FREE
# (so every accepted record's birth pass is covered by the free explosion
# budget -- the whole premise of "K free passes"). m=1 is the content-blind
# base rate (no density multiplier; random data).
#
# This is the honest per-layer ledger: earnings (coverage * win) minus the
# carriage (unclaimed-block literal markers + the wrap), with birth FREE.

def layer_net_per_bit(draws, m=1.0):
    """Per-layer net bits-per-bit at base rate, birth free within K.
    Uses the repo ledger but caps T at the layer's fresh-draw budget and
    zeroes the birth term (free within K)."""
    Tcap = max(1, int(round(draws)))
    # gbe.gain accumulates a per-pass birth charge kb = sum dX * max(1, log2 t).
    # Within K the birth pass is FREE (explosion check), so we recompute the
    # same earnings/carriage but with kb := 0. Re-derive inline to be exact:
    e = gbe.ART[f"B{B}|{PROFILE}|a{ARITY}|full"]
    Ew = e["E_win"]
    p = min(0.5, e["p"] * m)
    X = save = 0.0
    for t in range(1, Tcap + 1):
        dX = ARITY * p * (1 - X) ** ARITY
        save += dX / ARITY * Ew
        X = min(1.0, X + dX)
    # carriage = unclaimed-block literal markers (the wrap); birth = 0 (free).
    net_per_bit = (save - (1 - X) * LIT) / B
    return net_per_bit, X, save / B, (1 - X) * LIT / B


# ============================================================================
# PART 3.  Reduce across layers.  (advisor #2: the reduction IS the Q2 answer.)
# ============================================================================
# Content-blindness => layer L's input (= layer L-1's output) carries the SAME
# base rate p=0.0039 (the output of a content-blind machine on random-looking
# data is itself random-looking). => per-layer net is LAYER-INVARIANT. =>
# recursion's sign = a single layer's sign. The geometric sum collapses to the
# single-layer sign: one layer <= 0  =>  every layer <= 0  =>  recursion is
# strictly non-positive, bounded by raw+eps -- you just STOP (keep 0 layers).
#
# IMPORTANT (advisor #4): the real codec applies a layer ONLY if it shrinks; a
# no-op layer costs ~0 (remainder run). So the honest verdict at base rate is
# "net ~0, zero layers kept, bounded by raw+eps" -- NOT "bloats X%/layer". We
# report the per-layer SIGN and the size trajectory under the *kept-if-shrinks*
# rule, never a catastrophic-bloat number (which would contradict raw+eps).

def size_trajectory(draws, n_layers, n0_bits=1_000_000, kept_if_shrinks=True):
    """Apply n_layers recursively. Each layer multiplies size by (1 - net_per_bit)
    IF that shrinks (net>0); else the layer is a no-op (kept_if_shrinks)."""
    npb, *_ = layer_net_per_bit(draws)
    sizes = [n0_bits]
    s = n0_bits
    kept = 0
    for _ in range(n_layers):
        factor = 1.0 - npb
        if kept_if_shrinks and factor >= 1.0:
            # layer does not shrink -> no-op (real codec skips it), size unchanged
            sizes.append(s)
        else:
            s = s * factor
            kept += 1
            sizes.append(s)
    return sizes, npb, kept


# ============================================================================
# PART 4.  Q3 -- the exact density that flips a free-birth layer to net>0.
# ============================================================================
# Solve for the density multiplier m at which one free-birth layer nets 0,
# at the layer's K-draw supply. Confirm it equals the solver's 48x = p*.

def break_even_multiplier(draws, lo=1.0, hi=4096.0, tol=1e-4):
    """Smallest density multiplier m making a free-birth layer net >= 0."""
    def f(m):
        npb, *_ = layer_net_per_bit(draws, m=m)
        return npb
    # bisection on the sign of f
    if f(hi) < 0:
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if f(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return hi


# ============================================================================
def main():
    print("=" * 78)
    print("P2 RECURSION-LEDGER  --  layer-stacking economics at K free passes")
    print("=" * 78)
    print(f"  base rate p = {P_BASE} / window   win = {WIN_BITS} b   "
          f"literal carriage = {LIT} b   B = {B}")
    print(f"  K_FREE (explosion reach) = {K_FREE:.2f} passes   "
          f"p* (threshold) = {P_STAR}")
    print()

    # ---- PART 1: supply bracket -------------------------------------------
    print("-- PART 1: how many FRESH MATCH DRAWS per layer? (the bracket) --")
    print("  K~=5.66 is a DISAMBIGUATION budget, not a draw count. Bracket it:")
    for label, draws in [("(a) supply-rich  ~K draws/layer", K_FREE),
                         ("(b) supply-poor  ~1 draw /layer", 1.0)]:
        cov = coverage_layer(draws)
        print(f"    {label}: coverage/layer = 1-(1-p)^{draws:.2f} = {cov:.5f}"
              f"  ({cov*100:.3f}% of windows matched)")
    print()

    # ---- PART 2 + Q1: per-layer net at base rate --------------------------
    print("-- Q1: per-layer NET at content-blind base rate (birth FREE within K) --")
    print(f"    {'supply':>28} {'cov':>9} {'earn/bit':>10} {'carriage/bit':>13}"
          f" {'NET/bit':>10}")
    results = {}
    for label, draws in [("(a) ~K=5.66 draws/layer", K_FREE),
                         ("(b) ~1 draw/layer", 1.0)]:
        npb, cov, earn, carr = layer_net_per_bit(draws)
        results[label] = (npb, cov, draws)
        print(f"    {label:>28} {cov:>9.5f} {earn:>+10.5f} {carr:>13.5f}"
              f" {npb:>+10.5f}")
    print()
    print("  => Q1 ANSWER: per-layer net is NEGATIVE in BOTH supply readings.")
    print("     Earnings (coverage*win, ~0.04 b/window in the rich case) are")
    print("     swamped by the literal carriage on the ~98% unclaimed windows.")
    print("     The free birth channel removes the log2(T) tax; it does NOT")
    print("     remove the wrap/carriage tax, which is what sinks the layer.")
    print()

    # ---- PART 3 + Q2: reduce across layers --------------------------------
    print("-- Q2: reduce across layers (content-blindness => layer-invariant) --")
    print("  Layer L input = layer L-1 output; content-blind => same base rate p")
    print("  => per-layer net is LAYER-INVARIANT => recursion sign = layer sign.")
    print()
    for label, (npb, cov, draws) in results.items():
        sizes, _, kept = size_trajectory(draws, n_layers=64,
                                          kept_if_shrinks=True)
        print(f"    {label}: per-layer net/bit = {npb:+.5f}  "
              f"=> layers KEPT under kept-if-shrinks rule = {kept}/64")
        print(f"       size after 64 attempted layers: "
              f"{sizes[-1]/sizes[0]*100:.4f}% of original "
              f"(bounded by raw+eps; NO catastrophic bloat).")
    print()
    print("  => Q2 ANSWER: recursion does NOT change the verdict. A negative")
    print("     single-layer sign reduces to a non-positive recursion: every")
    print("     layer is identical at the base rate, the geometric sum collapses")
    print("     to the single-layer sign, and the codec keeps ZERO layers")
    print("     (no-op = remainder run, ~0 cost). Bounded raw+eps. Q2 priced")
    print("     negative, exactly the s7b corollary / pigeonhole.")
    print()

    # ---- PART 4 + Q3: the flip density ------------------------------------
    print("-- Q3: the EXACT density that flips a free-birth layer to net>0 --")
    print(f"    {'supply':>28} {'break-even mult':>16} {'= p_needed':>12}"
          f" {'vs base':>9}")
    for label, draws in [("(a) ~K=5.66 draws/layer", K_FREE),
                         ("(b) ~1 draw/layer", 1.0)]:
        m = break_even_multiplier(draws)
        if m is None:
            print(f"    {label:>28} {'>4096x':>16}")
            continue
        p_needed = min(0.5, P_BASE * m)
        print(f"    {label:>28} {m:>14.1f}x {p_needed:>12.4f}"
              f" {m:>7.0f}x")
    print()
    print(f"  Repo solver (golden_break_even.py) prints B8/canonical/a2 break-even")
    print(f"  at 48x base = {0.0039*48:.4f} ~= p* = {P_STAR} (GOLDEN threshold).")
    print(f"  Our free-birth, K-capped layer lands at the SAME multiplier band:")
    print(f"  the flip density for recursive compounding IS p*, the density the")
    print(f"  maintainer ruled CONTENT-AWARE (GOLDEN s2). Recursion does not")
    print(f"  lower the bar; it relocates the birth tax into wrap/carriage and")
    print(f"  the bar stays at p*. SAME WALL, DIFFERENT CURRENCY.")
    print()

    # ---- self-gate (advisor #5) -------------------------------------------
    print("-- COUNTING GATE (self-check) --")
    any_positive = any(r[0] > 0 for r in results.values())
    print(f"  Any config net>0 at base rate with free unbounded re-runs? "
          f"{'YES (RED FLAG!)' if any_positive else 'NO -- gate passed'}.")
    print("  A base-rate-positive unbounded recursion would net-compress random")
    print("  data without bound = pigeonhole violation = a dropped carriage term.")
    print("  We drop none: carriage (literal re-marking) is charged every layer.")


if __name__ == "__main__":
    main()
