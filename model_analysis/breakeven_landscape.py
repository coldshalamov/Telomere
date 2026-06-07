import math
# ROBUST ANALYTIC MODEL. 3-byte blocks, J3D1 format, 3-bit marker, ~2-bit avg save.
# Extends seed-search depth k (in BITS, i.e. 2^k seeds) arbitrarily far. Pure
# probability -- nothing hashed, nothing capped. Two axes: depth, and hit-density.
B = 24            # span bits (3-byte block, arity 1)
OVERHEAD = 10     # J3D1 record gap for 24-bit span (computed in breakeven_map.py)
MARKER = 3
SAVE = 2
p_sat = 2.0**(-OVERHEAD)                 # saturated compressive-hit prob (depth >= B-OVERHEAD)

def ratio(P):                            # net stored size / raw, per block
    P = min(P, 1.0)
    return 1 + ((1-P)*MARKER - P*SAVE)/B

print("AXIS 1 -- EXTEND SEARCH DEPTH 'CRAZY FAR OUT' (k = bits of seed length searched):")
print(f"{'depth k':>10} | {'seeds = 2^k':>14} | {'P(any match)':>12} | {'P(compressive)':>14} | {'net size':>8}")
print("-"*70)
for k in (10, 14, 16, 20, 30, 50, 100, 1000, 100000):
    p_any  = 1 - math.exp(-2.0**(min(k,64)+1 - B)) if k < 64 else 1.0
    p_comp = 1 - math.exp(-2.0**(min(k, B-OVERHEAD)+1 - B))     # saturates at k = B-OVERHEAD = 14
    seeds = f"2^{k}"
    print(f"{k:>9}b | {seeds:>14} | {p_any:>12.4f} | {p_comp:>14.6f} | {100*ratio(p_comp):>6.1f}%")
print(f"  --> compressive prob saturates at k={B-OVERHEAD} bits and never moves again.")
print(f"      From 2^14 to 2^100000 seeds: net size frozen at {100*ratio(p_sat):.1f}%. Depth is FLAT.\n")

print("AXIS 2 -- HIT DENSITY (how many x denser than uniform-random the hits are):")
print(f"{'density':>10} | {'P(compressive)':>14} | {'net size':>9} | crosses 100%?")
print("-"*56)
cross=None
for M in (1, 10, 100, 300, 500, 614, 700, 1000, 2000):
    P = M * p_sat
    r = ratio(P)
    mark = "  <-- BREAK-EVEN" if (cross is None and r<=1.0) else ""
    if r<=1.0 and cross is None: cross=M
    print(f"x{M:>8,} | {min(P,1):>14.4f} | {100*r:>7.1f}% | {'YES'+mark if r<=1 else 'no'}")
print(f"\n  --> break-even is a line on the DENSITY axis at ~x{cross}, and it sits there")
print(f"      at EVERY depth past k=14. Depth doesn't reach it; density does.")
print(f"\nWHERE BREAK-EVEN IS: not at any search depth (flat), but at hit-density >= ~{cross}x random.")
print( "That is the whole map. The open question is what mechanism delivers that density.")
