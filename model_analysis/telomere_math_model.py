#!/usr/bin/env python3
"""
TELOMERE MATH MODEL — primary artifact. Pure formulas. No hashing anywhere.

Core objects (correction spec §3/§11):
  record_cost(a,p)        = arity_cost(a) + jumpstarter(3) + len_field(p) + p
  M_{a,D}(r)              = # seeds with payload <= D and record_cost <= r
  P_D(min_record<=r|S,a)  = 1 - exp(-M_{a,D}(r) / 2^S)
  gain distribution       = P(gain >= g | S,a,D) = P_D(min_record <= S-g)
  state                   = histogram H_t[L] of current entry lengths (never a mean)
  span distribution       = exact a-fold convolution of H_t's pmf
  pass recurrence         = spec §5 (candidates -> selection -> replacement -> H_{t+1})
  superposition           = retained-state mass per prune delta (lower/upper/approx)
  shuffle                 = refresh-rate parameter + separate decodability pricing

Seed depth D (payload bits) is a free symbolic parameter: D = 8 .. 24000+.
Language: all outputs are "under this model and these assumptions".
"""
import csv, math
from collections import defaultdict

GMAX = 288                    # gain tail carried to 288 bits (covers A*marker amortization at A=64)

# ---------- canonical + swept codec families ----------
def arity_cost(a, fam='ext1'):
    if a <= 2: return 2
    if a <= 5: return 3
    if fam == 'ext1': return max(3, a.bit_length() + 1)        # assumption family 1
    if fam == 'ext2': return 4 if a <= 13 else max(5, a.bit_length())  # flat extra-bit tier
    if fam == 'lb':   return max(1, a.bit_length())             # LOWER BOUND (not prefix-free)
    raise ValueError(fam)

def j3d1_cost(p):
    p = max(1, p); return 3 + max(1, p.bit_length()) + p

def record_cost(a, p, fam='ext1'):
    return arity_cost(a, fam) + j3d1_cost(p)

_PS = {}
def pstar(r, a, fam='ext1'):
    """Largest payload p with record_cost(a,p) <= r. -1 if none. O(1) analytic."""
    key = (r, a, fam)
    v = _PS.get(key)
    if v is not None: return v
    base = arity_cost(a, fam) + 3
    best = -1
    for w in range(20, 0, -1):                 # w = bitlen(p); p <= 2^20 covers r ~ 1e6
        p = r - base - w
        if p >= 1 and max(1, p.bit_length()) <= w:
            best = max(best, p)
    # exactness guard: record_cost(best) may still exceed r if bitlen(best)<w used
    while best >= 1 and record_cost(a, best, fam) > r: best -= 1
    if best < 1: best = -1
    _PS[key] = best
    return best

def log2_M(r, a, D, fam='ext1'):
    """log2 of M_{a,D}(r): seeds with payload<=min(pstar,D); count = 2^min(pstar,D)."""
    ps = pstar(r, a, fam)
    if ps < 1: return None
    return min(ps, D)

def P_le(r, S, a, D, fam='ext1'):
    """P_D(min_record_cost <= r | S,a) = 1 - exp(-M/2^S)."""
    m = log2_M(r, a, D, fam)
    if m is None: return 0.0
    x = m - S
    if x >= 6: return 1.0
    return 1.0 - math.exp(-(2.0 ** x))

_GT = {}
def gain_tail(S, a, D, fam='ext1'):
    """[P(gain>=1), P(gain>=2), ...]: gain>=g <=> min_record <= S-g."""
    key = (S, a, D, fam)
    t = _GT.get(key)
    if t is None:
        p1 = P_le(S - 1, S, a, D, fam)
        if p1 < 1e-18:
            t = [0.0] * GMAX
        else:
            t = [p1] + [P_le(S - g, S, a, D, fam) for g in range(2, GMAX + 1)]
        _GT[key] = t
    return t

# ---------- span distribution: exact a-fold convolution ----------
def convolve(p1, p2, prune=1e-9, cap=400):
    out = defaultdict(float)
    for L1, q1 in p1.items():
        for L2, q2 in p2.items():
            out[L1 + L2] += q1 * q2
    items = [(L, q) for L, q in out.items() if q > prune]
    if len(items) > cap:                      # keep top mass (approximation, mass-conserving to 1e-6)
        items = sorted(items, key=lambda x: -x[1])[:cap]
    return dict(items)

def span_dists(pmf, A):
    d = {1: dict(pmf)}
    for a in range(2, A + 1):
        d[a] = convolve(d[a - 1], pmf)
    return d

# ---------- superposition state (per prune delta) ----------
def supo_state(pmf, D, delta, fam='ext1'):
    """Per entry of length L: P(retained alt) = P(min_record in [L, L+delta]);
       E[extra bits | retained] for the conversion suppression."""
    ret_mass, e_extra = 0.0, 0.0
    for L, q in pmf.items():
        p_hi = P_le(L + delta, L, 1, D, fam)
        p_lo = P_le(L - 1, L, 1, D, fam)
        pr = max(0.0, p_hi - p_lo)
        if pr <= 0: continue
        # expected extra bits of the retained record over L (coarse: mass-weighted shells)
        num = den = 0.0
        prev = p_lo
        for e in range(0, delta + 1):
            pe = P_le(L + e, L, 1, D, fam)
            num += max(0.0, pe - prev) * e
            den += max(0.0, pe - prev)
            prev = pe
        ret_mass += q * pr
        e_extra += q * pr * (num / den if den > 0 else delta)
    e_bar = e_extra / ret_mass if ret_mass > 0 else 0.0
    return ret_mass, e_bar

# ---------- one pass of the recurrence ----------
def pass_update(H, cfg, refresh):
    A, D, fam, delta, mode = cfg['A'], cfg['D'], cfg['fam'], cfg['delta'], cfg['supo']
    n = sum(H.values()); bits = sum(L * c for L, c in H.items())
    if n < 2: return H, None
    pmf = {L: c / n for L, c in H.items()}
    spans = span_dists(pmf, A)
    ret_mass, e_bar = supo_state(pmf, D, delta, fam) if mode != 'off' else (0.0, 0.0)
    if mode == 'oracle': e_bar = 0.0                    # upper bound: free alternates

    acc = saved = merged = conv = 0.0
    gw = defaultdict(float)                              # accepted-gain distribution
    rec_mass = defaultdict(float)
    for a in range(1, A + 1):
        windows = max(0.0, n - a + 1) * refresh
        for S, q in spans[a].items():
            gt = gain_tail(S, a, D, fam)
            P1 = gt[0]
            if P1 <= 0 or q <= 0: continue
            w = windows * q
            h = w * P1 / (1 + P1 * (a - 1))              # renewal overlap correction (small-P)
            eg = sum(gt) / P1
            acc += h; saved += h * eg; merged += h * (a - 1)
            rec_mass[max(1, round(S - eg))] += h
            for g in range(GMAX):                        # propagate the FULL tail
                pg = gt[g] - (gt[g + 1] if g + 1 < GMAX else 0.0)
                if pg > 0: gw[g + 1] += h * pg / P1
            if ret_mass > 0:
                p_alt = 1 - (1 - ret_mass) ** a          # window holds >=1 alternate
                conv += w * p_alt * P1 * (2.0 ** (-e_bar))
    saved += conv * 1.0                                  # converted routes: ~1 expected bit each (bounded)
    newH = defaultdict(float)
    rm = defaultdict(float)
    for a in range(1, A + 1):
        pass                                             # removal mass below, composition-weighted
    if acc > 0:
        for L, q in pmf.items(): rm[L] = (saved and 0) or 0  # placeholder no-op
    # removal: merged windows take (acc * avg_arity) entries of pmf composition
    taken = acc + merged
    for L, c in H.items():
        newH[L] = max(0.0, c - taken * pmf[L])
    for L, c in rec_mass.items():
        newH[L] += c
    # gain percentiles
    tot = sum(gw.values()); p50 = p90 = p99 = mx = 0
    if tot > 0:
        run = 0.0
        for g in sorted(gw):
            run += gw[g]
            if not p50 and run >= 0.50 * tot: p50 = g
            if not p90 and run >= 0.90 * tot: p90 = g
            if not p99 and run >= 0.99 * tot: p99 = g
            if gw[g] > 1e-6: mx = g
    row = dict(bits=bits, n=n, acc=acc, saved=saved, conv=conv,
               ret=ret_mass * n, p50=p50, p90=p90, p99=p99, mx=mx,
               bits_after=bits - saved, n_after=n - merged)
    return dict(newH), row

# ---------- pass 1 (raw spans vs wrapped bar) ----------
def pass1(N, b, cfg, marker=3):
    A, D, fam = cfg['A'], cfg['D'], cfg['fam']
    H = defaultdict(float); remaining = float(N)
    order = sorted(range(1, A + 1), key=lambda a: -(a * marker - (record_cost(a, a * b, fam) - a * b)))
    for a in order:
        S, bar = a * b, a * (b + marker)
        P1 = P_le(bar - 1, S, a, D, fam)
        if P1 <= 0 or remaining < a: continue
        gt = [P_le(bar - g, S, a, D, fam) for g in range(1, GMAX + 1)]
        eg = sum(gt) / P1
        starts = (remaining * P1) / (a * P1 + (1 - P1))   # renewal occupancy
        take = min(starts, remaining / a)
        H[max(1, round(bar - eg))] += take
        remaining -= take * a
    H[b + marker] += remaining
    return dict(H)

# ---------- multi-pass runner ----------
def multi_pass(N, b, A, D, T, fam='ext1', supo='approx', delta=8, refresh=1.0,
               meta_bits_per_pass=16, ledger=None, tag=''):
    cfg = dict(A=A, D=D, fam=fam, delta=delta, supo=supo)
    raw = N * b
    H = pass1(N, b, cfg)
    bits = sum(L * c for L, c in H.items())
    meta = 0.0
    if ledger is not None:
        ledger.append([b, A, fam, 1, D, D, raw, round(bits), f"{100*bits/raw:.4f}",
                       '', '', '', '', '', '', '', refresh, 0])
    last = None
    for t in range(2, T + 1):
        H, row = pass_update(H, cfg, refresh)
        if row is None: break
        meta += meta_bits_per_pass if refresh > 0 else 0
        bits = row['bits_after']
        if ledger is not None:
            ledger.append([b, A, fam, t, D, D, round(row['bits']), round(bits),
                           f"{100*(bits+meta)/raw:.4f}", f"{row['acc']:.2f}",
                           row['p50'], row['p90'], row['p99'], row['mx'],
                           f"{row['ret']:.1f}", f"{row['conv']:.3e}", refresh,
                           round(meta)])
        if last is not None and abs(last - bits) < 1e-7 * bits: break
        last = bits
    return (bits + meta) / raw

# ============================ REPORTING RUNS ============================
if __name__ == "__main__":
    LED = []
    HDR = ["block_size_bits", "arity_cap", "codec_family", "pass", "seed_depth_bits",
           "log2_seed_count", "bits_before", "bits_after", "percent_raw",
           "accepted_replacements", "gain_p50", "gain_p90", "gain_p99", "max_gain",
           "superposed_retained", "superposed_converted", "shuffle_refresh",
           "metadata_bits"]
    N, T = 12000, 8

    print("=" * 86)
    print("KEY MAP: final % of raw  |  rows: (b, A)  |  cols: seed depth D (payload bits)")
    print("Under this model and stated assumptions; supo=approx(d=8); refresh=1.0 (layered);")
    print("metadata 16 b/pass charged; codec family ext1 above A=5.")
    print("=" * 86)
    DEPTHS = (8, 12, 16, 24, 32, 48, 64, 96, 128, 256, 512, 1024, 4096, 24000)
    print(f"{'b':>4} {'A':>4} | " + " ".join(f"{d:>8}" for d in (16, 32, 128, 1024, 24000)))
    for b in (16, 24, 32):
        for A in (5, 16, 64):
            row = []
            for D in (16, 32, 128, 1024, 24000):
                r = multi_pass(N, b, A, D, T, ledger=LED)
                row.append(f"{100*r:8.3f}")
            print(f"{b:>4} {A:>4} | " + " ".join(row))

    print("\nDEPTH SWEEP at b=24, A=5 (net % vs D — the 'as D grows' answer):")
    for D in DEPTHS:
        r = multi_pass(N, 24, 5, D, T)
        print(f"  D={D:>6} (2^{D} seeds, log2 hashes/span ~ {D}): {100*r:9.4f}%")

    print("\nSUPERPOSITION SWEEP at b=24, A=5, D=1024 (per prune delta):")
    print(f"{'delta':>6} | {'mode':>7} | {'final %':>9}")
    for mode in ('off', 'approx', 'oracle'):
        for dl in ((0, 1, 2, 4, 8, 16, 32, 64) if mode == 'approx' else (8,)):
            r = multi_pass(N, 24, 5, 1024, T, supo=mode, delta=dl)
            print(f"{dl:>6} | {mode:>7} | {100*r:9.4f}%")

    print("\nWIDE-ARITY CODEC FAMILIES at b=24, D=24000, A=64 (assumption sweep):")
    for fam in ('ext1', 'ext2', 'lb'):
        r = multi_pass(N, 24, 64, 24000, T, fam=fam)
        print(f"  family {fam:>5}: {100*r:9.4f}%   (lb = non-prefix-free lower bound)")

    print("\nSHUFFLE / REFRESH PRICING (format analysis, not a toy result):")
    print("  rule                        decodable   metadata        refresh")
    print("  none                        yes         0               0 after first sweep")
    print("  pairswap (in-place)         NO (order)  n/a             50% alternating")
    print("  rotate/affine/PRP in-place  NO (order)  n/a             ~100%")
    print("  layer-delimited (any rule)  yes         ~16 b/pass      rule's rate")
    print("  between expanded layers     yes         layer descr.    100%")
    print("  virtual (discovery only)    yes         0               0 shippable")
    for rho in (0.0, 0.5, 1.0):
        r = multi_pass(N, 24, 5, 1024, T, refresh=rho)
        print(f"  refresh={rho:3.1f}: final {100*r:9.4f}%  (metadata charged when refresh>0)")

    with open("telomere_depth_sweep.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(HDR); w.writerows(LED)
    print(f"\nCSV -> telomere_depth_sweep.csv  ({len(LED)} rows)")
