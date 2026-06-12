#!/usr/bin/env python3
"""Golden Config break-even solver. Exact format arithmetic + honest
birth-information ledger. Bundles (a>=2): per-pass fresh dice, charged
log2(t) bits/record birth-info lower bound. Singles (a=1): slot-keyed,
ZERO birth bits, but ONE lifetime compressive search (no per-pass fresh
dice) -- modeled one-shot. Solves the minimal density multiplier m for
net-positive gain, and the best T. Run: python3 golden_break_even.py"""
import json, math, os
ART = json.load(open(os.path.join(os.path.dirname(__file__), "golden_format_arithmetic.json")))

def gain(B, profile, a, T, m):
    e = ART[f"B{B}|{profile}|a{a}|full"]
    lit = {"payback": 2, "canonical": 3}[profile]
    Ew = e["E_win"]
    if a == 1:                       # one-shot, epoch-free
        X = min(1.0, e["p"] * m)
        return (X * Ew - (1 - X) * lit) / B, X, 0.0
    p = min(0.5, e["p"] * m)
    X = kb = save = 0.0
    for t in range(1, T + 1):
        dX = a * p * (1 - X) ** a
        save += dX / a * Ew
        kb += dX / a * max(1.0, math.log2(max(t, 2)))
        X = min(1.0, X + dX)
    return (save - (1 - X) * lit - kb) / B, X, kb

if __name__ == "__main__":
    rows = [(8,"canonical",2),(8,"payback",2),(16,"canonical",2),(8,"canonical",3),
            (16,"payback",1),(16,"canonical",1),(24,"payback",1),(32,"payback",1)]
    print(f"{'config':20s} {'min mult':>9} {'T*':>4} {'gain/bit':>9} {'coverage':>9}")
    for B, prof, a in rows:
        found = None
        for m in [1,2,4,8,16,24,32,48,64,96,128,192,256,384,512,1024]:
            for T in ((1,) if a == 1 else (2,4,8,16,32,64,128)):
                g, X, kb = gain(B, prof, a, T, m)
                if g > 0: found = (m, T, g, X); break
            if found: break
        s = f"B{B}/{prof}/a{a}"
        if found:
            print(f"{s:20s} {found[0]:>8}x {found[1]:>4} {found[2]:>+9.4f} {found[3]:>9.3f}")
        else:
            print(f"{s:20s} {'>1024x':>9}")
