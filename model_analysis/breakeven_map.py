# ANALYTIC model. No hashing, no search cap, no laptop limit. Pure probability,
# using your exact format: 2-3 bit arity codes, J3D1 seed records, 3-bit literal
# marker, once-wrapped. Answers: at each block size, how far from break-even are we,
# and which lever moves it most?
def arity_bits(a): return 2 if a <= 2 else 3
def j3d1_bits(i):                      # 3-bit jumpstarter + length field + payload
    p = max(1, i.bit_length()); w = max(1, p.bit_length()); return 3 + w + p

def model(block_bits, a):
    s = a * block_bits
    p_max = 0
    for p in range(1, s + 1):
        rec = arity_bits(a) + 3 + max(1, p.bit_length()) + p   # cheapest record at payload-width p
        if rec < s: p_max = p
        else: break
    overhead = s - p_max                 # the "gap": record bits beyond the seed's own info
    pwin = 2.0 ** (-overhead)            # P(a random s-bit span has a compressive seed) — UNCAPPED
    return overhead, pwin

MARKER = 3   # literal marker bits (your format)
SAVE   = 2   # avg bits saved per win (measured ~2.17 earlier; uncapped distribution mean)

print("ANALYTIC BREAK-EVEN MAP  (no hashing, no cap)")
print("="*78)
print(f"{'block':>6} | {'span':>5} | {'gap':>4} | {'base P(win)':>12} | {'init wrap':>9} | {'break-even density':>18}")
print("-"*78)
for B in (2,3,4,5):           # bytes
    ov, p0 = model(B*8, 1)
    M = MARKER / (p0 * (SAVE + MARKER))         # density multiplier to reach net zero (arity-1)
    M_multi = M / 1.2                            # arities 1-5 give ~1.2x more bites
    print(f"{B:>5}B | {B*8:>4}b | {ov:>3}b | {p0:>12.2e} | {300/(B*8):>7.1f}% | "
          f"x{M:>7,.0f}  (~x{M_multi:,.0f} w/ arity)")

print("\nWHICH LEVER MOVES BREAK-EVEN MOST  (at 3-byte blocks, gap=10):")
ov,p0 = model(24,1)
base = MARKER/(p0*(SAVE+MARKER))
print(f"  baseline                         : x{base:,.0f}")
print(f"  marker 3b -> 1b (format design)  : x{1/(p0*(SAVE+1)):,.0f}   ({base/(1/(p0*(SAVE+1))):.1f}x easier)")
print(f"  savings 2b -> 6b (bias low seeds): x{MARKER/(p0*(6+MARKER)):,.0f}   ({base/(MARKER/(p0*(6+MARKER))):.1f}x easier)")
print(f"  density itself (transforms/etc.) : each x10 in hit-rate = x10 closer, directly")
print("\nNote: 'break-even density' = how many times denser than uniform-random the")
print("compressive hits must be for net delta to cross 0. It is the target number.")
print("It does not say whether a mechanism can reach it — that's the open question.")
