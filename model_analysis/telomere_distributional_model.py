#!/usr/bin/env python3
"""
TELOMERE DISTRIBUTIONAL MODEL — Layer 2. Pure math. No hashing anywhere.

State is a HISTOGRAM of entry lengths H[L] (expected counts), not a mean.
Span lengths are exact A-fold convolutions of the length distribution.
Gains are FULL DISTRIBUTIONS P(gain >= g | S, A), never a constant.
Depth k is a free parameter: 2^k seeds, k as large as you like (10^5+ fine).
Superposition is carried as state-mass with its own conversion law.
Shuffle is a refresh-rate parameter, conditional on the Layer-1 order-recovery
fork (its decode repair cost is NOT charged here; flagged, maintainer's call).

Validation duty: at toy settings (b=6, k=19) this model's predictions are
compared against telomere_model_results.csv (Layer 1). Where small counts make
single-run outcomes lumpy (e.g. arity-1's two-usable-seed coin flip), the model
reports the expected count AND the lumpiness note, since one toy run is one draw.

Output: ledgers and sweeps. No verdicts.
"""
import math
from collections import defaultdict

# ---------- canonical costs ----------
def ac(a):
    if a <= 2: return 2
    if a <= 5: return 3
    return max(3, a.bit_length() + 1)          # extension family beyond spec (flagged)

def j3d1_bits(p):
    p = max(1, p); return 3 + max(1, p.bit_length()) + p

def pstar(bar, a):
    """Largest payload bit-length p with ac(a)+j3d1(p) < bar (record strictly under bar)."""
    best = -1; p = 1
    while p <= bar:
        if ac(a) + j3d1_bits(p) < bar: best = p; p += 1
        else: break
    return best

def p_hit(S, bar, a, k):
    """P(at least one seed at depth 2^k yields record < bar) for an S-bit span."""
    ps = pstar(bar, a)
    if ps < 0: return 0.0
    M_log2 = min(ps, k)                         # usable seeds limited by depth
    x = 2.0 ** (M_log2 - S)
    return 1.0 if x > 60 else 1.0 - math.exp(-x)

def gain_dist(S, a, k, gmax=64):
    """P(gain >= g) for g=1..gmax. gain g means record <= S-g (bar shifts down by g)."""
    return [p_hit(S, S - g + 1, a, k) for g in range(1, gmax + 1)]
    # record < S-g+1  <=>  record <= S-g  <=>  gain >= g

def e_gain_given_hit(S, a, k):
    gd = gain_dist(S, a, k)
    if gd[0] <= 0: return 0.0
    return sum(gd) / gd[0]                      # E[gain | gain>=1] from the full distribution

# ---------- one distributional pass ----------
def dist_pass(H, A, k, rho, supo_mass=0.0, supo_extra=8):
    """
    H: dict L -> expected entry count. rho: fraction of windows fresh this pass
    (1.0 = full refresh/shuffle, 0.0 = exhausted adjacencies).
    supo_mass: fraction of entries carrying an alternate form (+supo_extra bits).
    Returns (newH, ledger_row).
    """
    n = sum(H.values())
    bits = sum(L * c for L, c in H.items())
    if n <= 0: return H, None
    pmf = {L: c / n for L, c in H.items()}

    # exact A-fold convolutions of the length pmf
    conv = {1: dict(pmf)}
    for a in range(2, A + 1):
        nxt = defaultdict(float)
        for L1, q1 in conv[a - 1].items():
            for L2, q2 in pmf.items():
                nxt[L1 + L2] += q1 * q2
        conv[a] = dict(nxt)

    hits = {}; saved = 0.0; merged = 0.0; conv_hits = 0.0
    rec_len_mass = defaultdict(float)
    for a in range(1, A + 1):
        windows = max(0.0, (n - a + 1)) * rho
        for S, q in conv[a].items():
            ph = p_hit(S, S, a, k)              # strict: beat the span itself
            if ph <= 0 or q <= 0: continue
            w = windows * q
            h = w * ph
            eg = e_gain_given_hit(S, a, k)
            hits[a] = hits.get(a, 0.0) + h
            saved += h * eg
            merged += h * (a - 1)
            rec_len_mass[max(1, int(round(S - eg)))] += h
            # superposition conversion mass: window contains >=1 alt form (longer target,
            # SAME bar). Extra bits e suppress the hit rate by 2^-e exactly:
            if supo_mass > 0:
                p_alt_win = 1 - (1 - supo_mass) ** a
                conv_hits += w * p_alt_win * ph * (2.0 ** (-supo_extra))

    # update histogram: remove merged window members (approx: proportional), add records
    total_h = sum(hits.values())
    newH = defaultdict(float)
    removed = defaultdict(float)
    for a in range(1, A + 1):
        ha = hits.get(a, 0.0)
        if ha <= 0: continue
        for L, q in pmf.items():                # expected composition of merged members
            removed[L] += ha * a * q
    for L, c in H.items():
        newH[L] += max(0.0, c - removed.get(L, 0.0))
    for L, c in rec_len_mass.items():
        newH[L] += c
    row = dict(bits=bits, n=n, hits=hits, saved=saved, conv=conv_hits,
               bits_after=bits - saved, n_after=n - merged)
    return dict(newH), row

# ---------- pass-1 (raw spans, wrapped bar) ----------
def pass1_hist(N, b, A, k, marker=3):
    """Expected pass-1 outcome as a histogram. Window occupancy: greedy, small-P approx."""
    H = defaultdict(float)
    placed = 0.0
    remaining = float(N)
    # order arities by per-window expected saving (greedy preference)
    order = sorted(range(1, A + 1),
                   key=lambda a: -(a * (b + marker) - (ac(a) + j3d1_bits(a * b))))
    for a in order:
        S, bar = a * b, a * (b + marker)
        ph = p_hit(S, bar, a, k)
        if ph <= 0: continue
        starts = remaining * ph / (1 + ph * (a - 1))     # renewal occupancy approx
        take = min(starts, remaining / a)
        eg = e_gain_given_hit(S, a, k)                   # gain vs the wrapped bar
        # record length distribution ~ bar - gain
        H[max(1, int(round(bar - eg)))] += take
        remaining -= take * a
        placed += take
    H[b + marker] += remaining                            # wrap-once leftovers
    return dict(H)

# ---------- runners ----------
def run(label, N, b, A, k, passes, rho, supo_mass=0.0, supo_extra=8, quiet=False):
    raw = N * b
    H = pass1_hist(N, b, A, k)
    bits = sum(L * c for L, c in H.items())
    if not quiet:
        print(f"\n--- {label}: b={b} A<={A} depth=2^{k} rho={rho} supoMass={supo_mass} ---")
        print(f"  pass  1: {100*bits/raw:9.4f}% of raw   entries={sum(H.values()):,.0f}")
    final = bits
    for t in range(2, passes + 1):
        H, row = dist_pass(H, A, k, rho if t > 2 or rho == 0 else 1.0,
                           supo_mass, supo_extra)
        if row is None: break
        final = row['bits_after']
        if not quiet:
            hd = {a: round(v, 2) for a, v in row['hits'].items() if v > 0.005}
            print(f"  pass {t:2d}: {100*final/raw:9.4f}%   E[hits]={hd}   "
                  f"E[saved]={row['saved']:7.2f}b   E[supoConv]={row['conv']:.3e}")
        if row['saved'] < 1e-9 * final: break
    return final / raw

if __name__ == "__main__":
    # ===== VALIDATION AGAINST LAYER-1 TOY (matched settings: b=6, k=19, N=3000) =====
    print("=" * 84)
    print("VALIDATION vs exact toy (telomere_model_results.csv), b=6, depth 2^19, N=3000")
    print("=" * 84)
    run("mode-B analogue (rho: 1 then 0 = no shuffle)", 3000, 6, 5, 19, 10, rho=0.0)
    run("mode-D analogue (rho=0.5, affine refresh)",   3000, 6, 5, 19, 10, rho=0.5)
    print("""
  toy facts to compare: pass1 140.400%; mode B pass2 acc=3 then 0;
  mode D ~2-6 acc/pass decaying; arity-1 lumpiness note: at b=6 only seeds
  {0,1} can win arity-1 strictly (record 7 < 9); whether their expansions start
  '111' is a property of the hash draw -> expected ~7.6 wins but P(zero)=0.77.
  The expectation model reports the mean of that coin flip; the toy shows one draw.""")

    # ===== SCALED RUNS (pure theory; depth far beyond hardware) =====
    print("\n" + "=" * 84)
    print("SCALED: b=24, arity<=5, full refresh each pass (best case), depth ladder")
    print("=" * 84)
    for k in (20, 40, 120, 1000, 100000):
        r = run(f"depth 2^{k}", 12000, 24, 5, k, 8, rho=1.0, quiet=True)
        print(f"  depth 2^{k:>6}: converged {100*r:9.4f}% of raw")

    print("\nSUPERPOSITION CONVERSION LAW (why depth does not wake it):")
    print("  conversion rate = (normal hit rate) x 2^-(alt extra bits), at EVERY depth.")
    print("  alt extra bits = noncompressive record minus main length ~ framing (>=7):")
    for e in (7, 8, 12, 16):
        print(f"    extra={e:2d}b -> conversions = normal hits x {2.0**-e:.2e}")
    print("  Depth raises neither factor once saturated (pstar caps the usable seeds).")

    print("\nARITY-CAP SWEEP at depth 2^1000 (theoretical), b=24, full refresh, 8 passes:")
    for A in (5, 16, 64):
        r = run(f"A={A}", 12000, 24, A, 1000, 8, rho=1.0, quiet=True)
        print(f"  arity cap {A:>3}: converged {100*r:9.4f}% of raw")
