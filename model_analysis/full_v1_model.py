#!/usr/bin/env python3
"""
Telomere V1 Full Probability Model
===================================
Exact first-principles model of V1 seed-search compression.
Uses actual Lotus bit costs from header.rs / telomere_power_model.py.
Verified against FINDINGS.md and POWER_MODEL.md known values.

Key insight this model tracks: matches come in two classes:
  1. Beats-raw:     record < raw_bits  → helps compress below raw
  2. Beats-lit-only: raw <= record < lit → reduces file but stays above raw
Only beats-raw matches contribute to net compression.
"""
import math

def lotus_width_for_value(v):
    w = 1
    while True:
        if (1 << w) - 2 <= v <= (1 << (w + 1)) - 3: return w
        w += 1

def j3d2(v):
    pv = v + 1; pw = lotus_width_for_value(pv)
    t = 0; cw = pw
    for _ in range(2): tw = lotus_width_for_value(cw); t += tw; cw = tw
    return 3 + t + pw

def j1d1(v):
    pv = v + 1; pw = lotus_width_for_value(pv)
    return 1 + lotus_width_for_value(pw) + pw

def j3d2_table(max_budget=200):
    t = []; pw = 1
    while True:
        fv = 0 if pw == 1 else (1 << pw) - 3
        cnt = 1 if pw == 1 else 1 << pw
        cost = j3d2(fv)
        if cost >= max_budget: break
        t.append((cost, cnt)); pw += 1
    return t

class Fmt:
    def __init__(s, name, ab, lb, pad):
        s.name, s.arity_bits, s.literal_bits, s.pad = name, ab, lb, pad
    def hdr(s, a): return s.arity_bits.get(a, max(s.arity_bits.values()))
    def lit(s, bs):
        r = bs * 8
        return s.literal_bits + ((8 - s.literal_bits % 8) % 8 if s.pad else 0) + r

V1 = Fmt("V1-Current (J1D1)", {1:3,2:5,3:5,4:5,5:5}, 6, True)
PROP = Fmt("Proposed (3-bit lit)", {1:2,2:2,3:3,4:3,5:3}, 3, False)
MIN = Fmt("Minimal (1-bit flag)", {1:1}, 1, False)

def analyze(fmt, bs, arity):
    span = arity * bs * 8; raw = span; lit = arity * fmt.lit(bs); h = fmt.hdr(arity)
    n_raw = n_lo = 0; sr_raw = sr_lo = 0  # lo = lit-only (between raw and lit)
    for cost, cnt in j3d2_table(max(lit - h + 5, 200)):
        rec = h + cost
        if rec >= lit: break
        if rec < raw:
            n_raw += cnt; sr_raw += cnt * rec
        else:
            n_lo += cnt; sr_lo += cnt * rec
    n_lit = n_raw + n_lo
    p_raw = n_raw / 2.0**span if span < 1024 and n_raw else 0
    p_lo = n_lo / 2.0**span if span < 1024 and n_lo else 0
    p_lit = p_raw + p_lo
    ar_raw = sr_raw / n_raw if n_raw else 0
    ar_lo = sr_lo / n_lo if n_lo else 0
    ar_lit = (sr_raw + sr_lo) / n_lit if n_lit else 0
    return dict(a=arity, span=span, raw=raw, lit=lit, h=h,
                n_raw=n_raw, n_lo=n_lo, n_lit=n_lit,
                p_raw=p_raw, p_lo=p_lo, p_lit=p_lit,
                ar_raw=ar_raw, ar_lo=ar_lo, ar_lit=ar_lit,
                gap=span - math.log2(n_raw) if n_raw else float('inf'),
                save_raw=raw - ar_raw if n_raw else 0,
                save_lit=lit - ar_lit if n_lit else 0)

def file_at_mult(r, fmt, bs, N, M):
    """Compute file bytes at density multiplier M."""
    raw_b = bs * 8; lit_b = fmt.lit(bs)
    pr = min(1.0, M * r['p_raw'])
    pl = min(1.0, M * r['p_lit'])
    plo = pl - pr; pu = 1 - pl
    bits = pr * r['ar_raw'] + plo * (r['ar_lo'] if r['ar_lo'] else lit_b) + pu * lit_b
    return N * bits / 8

def model(fmt, bs, inp=1_000_000):
    rb = bs * 8; lb = fmt.lit(bs); oh = lb - rb
    N = inp // bs; best = fmt.hdr(1) + j3d2(0)
    print(f"\n{'='*78}")
    print(f"  {fmt.name}  |  bs={bs}  |  {inp:,} bytes")
    print(f"{'='*78}")
    print(f"  Raw: {rb}b  Literal: {lb}b (OH {oh}b = {100*oh/rb:.0f}%)  Best: {best}b  Blocks: {N:,}")
    print(f"  All-literal: {N*lb/8:,.0f}B    Best-case: {N*best/8:,.0f}B ({100*(1-best/rb):.0f}% comp)")

    print(f"\n  A  Span  Hdr  {'Nraw':>10} {'Praw':>10} {'Gap':>5}  AvgR  SaveR  {'Nlit':>10} {'Plit':>10} AvgLit SaveLit")
    results = []
    for a in range(1, 13):
        try: r = analyze(fmt, bs, a)
        except: break
        if r['n_lit'] == 0 and a > 5: continue
        results.append(r)
        if r['n_raw'] > 0 and a <= 8:
            print(f"  {a}  {r['span']:>4}  {r['h']:>3}  {r['n_raw']:>10,} {r['p_raw']:>10.2e} {r['gap']:>5.1f}"
                  f"  {r['ar_raw']:>4.1f}  {r['save_raw']:>4.1f}b  {r['n_lit']:>10,} {r['p_lit']:>10.2e}"
                  f"  {r['ar_lit']:>4.1f}  {r['save_lit']:>4.1f}b")

    r1 = next((r for r in results if r['a'] == 1), None)
    if not r1 or r1['n_raw'] == 0:
        print("  No beats-raw seeds."); return

    # Break-even using FINDINGS.md formula:
    # P_raw × (save_raw + overhead) > overhead
    # P_raw > overhead / (save_raw + overhead)
    sr = r1['save_raw']; p_need = oh / (sr + oh)
    M_be = p_need / r1['p_raw']
    print(f"\n  BREAK-EVEN (arity 1, beats-raw matches)")
    print(f"    Avg beats-raw record: {r1['ar_raw']:.1f}b (saves {sr:.1f}b vs raw)")
    print(f"    Overhead per literal:  {oh}b")
    print(f"    P needed:              {p_need:.4f} ({100*p_need:.1f}%)")
    print(f"    P_base:                {r1['p_raw']:.3e}")
    print(f"    ► BREAK-EVEN:          {M_be:.0f}x density multiplier")

    # Can it compress at 100% raw match?
    full_raw = N * r1['ar_raw'] / 8
    if full_raw < inp:
        print(f"    100% raw-match file:   {full_raw:,.0f}B = {100*(1-full_raw/inp):.1f}% compression ✓")
    else:
        print(f"    100% raw-match file:   {full_raw:,.0f}B — avg record {r1['ar_raw']:.1f} > raw {rb} ✗")

    # Conditional replacement
    print(f"\n  CONDITIONAL REPLACEMENT")
    print(f"    Floor: {N*lb/8:,.0f}B (all-literal, never worse)")
    f0 = file_at_mult(r1, fmt, bs, N, 1)
    print(f"    At base rates: {f0:,.0f}B (saves {N*lb/8 - f0:,.0f}B vs all-literal, still +{f0-inp:,.0f} vs raw)")

    # Multi-pass
    print(f"\n  MULTI-PASS (conditional commit, base rates)")
    cur = N * lb / 8
    for p in range(1, 6):
        cb = int(cur / bs)
        m = cb * r1['p_lit']; sv = m * r1['save_lit'] / 8
        if sv < 0.5: print(f"    Pass {p}: <1B save, stop"); break
        cur -= sv
        if p <= 3 or p == 5:
            print(f"    Pass {p}: {m:.0f} matches, save {sv:.0f}B → {cur:,.0f}B")
    print(f"    Final: +{cur-inp:,.0f} vs raw")

    # Superposition
    srb = math.ceil(lb / 8) * 8; sb = srb - r1['h']
    sn = sum(c for cost, c in j3d2_table(sb + 5) if r1['h'] + cost < srb)
    ps = sn / 2**srb if srb < 1024 else 0
    print(f"\n  SUPERPOSITION: P(2nd-level) = {ps:.2e} vs P_raw = {r1['p_raw']:.2e} — same order")

    # Density sweep (CORRECT two-class model)
    print(f"\n  DENSITY MULTIPLIER SWEEP (two-class matches)")
    print(f"  {'M':>8}  {'Praw':>8}  {'Plit':>8}  {'File':>12}  {'vs raw':>12}  {'comp':>8}")
    for m in [1, 10, 50, 100, 200, 500, 1000, 2000, 3000, 5000, 10000]:
        fb = file_at_mult(r1, fmt, bs, N, m)
        d = fb - inp
        tag = f" {-100*d/inp:.1f}%◄" if d < 0 else ""
        pr = min(1, m * r1['p_raw']); pl = min(1, m * r1['p_lit'])
        print(f"  {m:>7}x  {pr:>8.4f}  {pl:>8.4f}  {fb:>12,.0f}  {d:>+12,.0f}{tag}")

    return r1

def verify():
    print("VERIFICATION"); ok = True
    for v, e in [(0,6),(1,9),(5,10),(13,11),(29,12),(61,14),(125,15),(253,16)]:
        g = j3d2(v); s = "✓" if g == e else "✗"
        if g != e: ok = False
        print(f"  J3D2({v})={g} exp {e} {s}")
    for v, e in [(0,3),(1,5),(4,5),(5,6)]:
        g = j1d1(v); s = "✓" if g == e else "✗"
        if g != e: ok = False
        print(f"  J1D1({v})={g} exp {e} {s}")
    assert V1.hdr(1) + j3d2(0) == 9, "arity=1 seed=0 check"
    r = analyze(V1, 4, 1)
    print(f"  bs=4 a=1: N={r['n_raw']:,} gap={r['gap']:.1f} P={r['p_raw']:.3e} (exp ~1,048,574 12.0 2.44e-4)")
    print(f"  {'PASS' if ok else 'FAIL'}\n")

if __name__ == "__main__":
    verify()
    for f in [V1, PROP, MIN]:
        for b in [2, 3, 4]:
            if f is MIN and b > 2: continue
            model(f, b)

    print(f"\n{'='*78}")
    print(f"  SUMMARY: BREAK-EVEN MULTIPLIERS")
    print(f"{'='*78}")
    print(f"  {'Format':<25} {'BS':>3} {'OH':>4} {'AvgRec':>7} {'SaveR':>6} {'Praw':>10} {'M':>8} {'100%comp':>9}")
    for f in [V1, PROP, MIN]:
        for b in [2, 3, 4]:
            if f is MIN and b > 2: continue
            r = analyze(f, b, 1); rb = b*8; lb = f.lit(b); oh = lb - rb
            if r['n_raw'] == 0:
                print(f"  {f.name:<25} {b:>3} {oh:>3}b {'—':>7} {'—':>6} {'—':>10} {'∞':>8} {'—':>9}")
                continue
            sr = r['save_raw']; pn = oh / (sr + oh); m = pn / r['p_raw']
            can = f"{'yes' if r['ar_raw'] < rb else 'no':>9}"
            print(f"  {f.name:<25} {b:>3} {oh:>3}b {r['ar_raw']:>6.1f}b {sr:>5.1f}b {r['p_raw']:>10.3e} {m:>7.0f}x {can}")
