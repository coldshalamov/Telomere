#!/usr/bin/env python3
"""
SKEPTIC1_arity_slope_check.py

Two adversarial closes:

(A) COUNTING-GATE CHAIN, verified as exact arithmetic (not a curve fit):
    base(T) = 1 + (G-1)*q  with G ~= rho*T (rho~=0.7 measured, but the chain
    holds for ANY rho>0). For ALL T >= 2:  (G-1)*q > 0  =>  base > 1 strictly
    =>  log2(base) > 0  =>  per-bundle birth residual is STRICTLY POSITIVE and
    GROWS as log2(T)-E for T >> K. S_epoch = base^R is exponential in R, so the
    deterministic-decode checksum must widen to R*log2(base) STORED bits. There
    is no T at which the residual is exactly 0 -> no free unbounded channel.
    A free unbounded channel would require base == 1 for all T (q==0, i.e. the
    explosion check rejecting EVERY wrong epoch with certainty) -- impossible
    for a uniform hash where q = avalid/2^L > 0.

(B) HIGHER-ARITY DISPATCH (the only remaining place a real channel could hide):
    does raising arity a pin the epoch to O(1)? It raises the length pin E(a) =
    -log2(avalid(a,aB)/2^(aB)), hence the free knee K=2^E. But the asymptotic
    per-bundle slope is log2(T) - E(a): a CONSTANT shift, never a slope change.
    For a real channel you'd need the slope to vanish, i.e. E(a) -> log2(T),
    i.e. E growing WITH T. A fixed grammar gives a CONSTANT E(a). So no arity
    pins the epoch; higher arity just moves the finite knee further out.
    (And the higher-arity geometry is STILL one observation -> a-1 skipped child
    slots -> cannot pin, same as a=2; verified structurally, not re-run.)
"""
import math
from functools import lru_cache

B = 8
J_BITS = 3
ARITY_CODEWORD_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
LITERAL_MARKER_BITS = 3


@lru_cache(maxsize=None)
def lotus_width_for_value(value: int) -> int:
    width = 1
    while True:
        if (1 << width) - 2 <= value <= (1 << (width + 1)) - 3:
            return width
        width += 1


def lotus_seed_bits(pw): return J_BITS + lotus_width_for_value(pw) + pw
def record_item_bits(a, pw): return ARITY_CODEWORD_BITS[a] + lotus_seed_bits(pw)
def literal_item_bits(): return LITERAL_MARKER_BITS + B


@lru_cache(maxsize=None)
def n_item_strings_of_len(w):
    count = 0
    if w == literal_item_bits():
        count += (1 << B)
    for arity, cw_bits in ARITY_CODEWORD_BITS.items():
        seed_len = w - cw_bits
        if seed_len < J_BITS + 1 + 1:
            continue
        for tw in range(1, 9):
            pw = seed_len - J_BITS - tw
            if pw < 1:
                continue
            if lotus_width_for_value(pw) != tw:
                continue
            count += (1 << pw)
    return count


MIN_ITEM = min(literal_item_bits(),
               min(record_item_bits(ar, 1) for ar in ARITY_CODEWORD_BITS))


@lru_cache(maxsize=None)
def avalid(a, L):
    if a == 0:
        return 1 if L == 0 else 0
    total = 0
    for w in range(MIN_ITEM, L - (a - 1) * MIN_ITEM + 1):
        ni = n_item_strings_of_len(w)
        if ni:
            total += ni * avalid(a - 1, L - w)
    return total


def E_for_arity(a):
    L = a * B
    av = avalid(a, L)
    if av == 0:
        return float('inf'), 0, L
    return L - math.log2(av), av, L


def section(t): print("\n" + "=" * 76 + "\n" + t + "\n" + "=" * 76)


def main():
    section("(A) COUNTING-GATE CHAIN: base>1 strictly for ALL T>=2 (exact)")
    E2, av2, L2 = E_for_arity(2)
    q2 = av2 / (1 << L2)
    print(f"  arity-2: avalid(2,16)={av2}  q={q2:.6f}  E={E2:.4f}  K=2^E={2**E2:.0f}")
    print(f"  rho used below = 0.7 (measured G/T in SKEPTIC1_G_scale_probe).")
    rho = 0.7
    print(f"\n  {'T':>9} {'G=rho*T':>9} {'(G-1)q':>10} {'base':>10} "
          f"{'log2 base':>10} {'>0?':>5}")
    for T in (2, 6, 100, 655, 1000, 4000, 1_000_000):
        G = max(1, rho * T)
        base = 1 + (G - 1) * q2
        lb = math.log2(base)
        print(f"  {T:>9} {G:>9.0f} {(G-1)*q2:>10.4f} {base:>10.4f} "
              f"{lb:>10.4f} {'YES' if lb > 0 else 'no':>5}")
    print("\n  base = 1 + (G-1)q with q>0 and G>=2 => base>1 STRICTLY => log2(base)>0")
    print("  for every T>=3 (G>=2). The ONLY way to free-unbounded is q==0 (the")
    print("  explosion check rejecting EVERY wrong epoch w.p. 1) -- impossible for a")
    print("  uniform hash (q = avalid/2^L > 0). NO T gives a zero residual.")
    print("  => S_epoch = base^R exponential; checksum widens R*log2(base) STORED")
    print("     bits. Currency = stored-bits. Random data does NOT net-compress.")

    section("(B) HIGHER-ARITY DISPATCH: raising a moves K, never the slope")
    print(f"  {'arity a':>7} {'L=aB':>6} {'avalid':>10} {'q':>12} "
          f"{'E (bits)':>9} {'K=2^E':>14}")
    for a in (1, 2, 3, 4, 5):
        E, av, L = E_for_arity(a)
        q = av / (1 << L) if av else 0.0
        Kstr = f"{2**E:.3e}" if E != float('inf') else "inf"
        print(f"  {a:>7} {L:>6} {av:>10} {q:>12.3e} {E:>9.4f} {Kstr:>14}")
    print("\n  E(a) GROWS with arity -> K=2^E grows -> the free intercept moves out.")
    print("  But the asymptotic per-bundle residual is log2(T) - E(a): a CONSTANT")
    print("  shift. For T >> K it is positive and grows in T at slope 1 (in log2 T)")
    print("  for EVERY arity. To kill the slope you'd need E(a) ~ log2(T), i.e. E")
    print("  growing WITH the pass count -- a fixed grammar cannot. So NO arity")
    print("  pins the epoch; higher arity = same wall, further out.")
    print()
    print("  Residual log2(T)-E(a) past the knee (>=0):")
    Es = {a: E_for_arity(a)[0] for a in (1, 2, 3, 4, 5)}
    hdr = "  " + f"{'T':>9}" + "".join(f"  a={a:<7}" for a in (1, 2, 3, 4, 5))
    print(hdr)
    for T in (64, 1024, 1_000_000, 10**12):
        lt = math.log2(T)
        row = "  " + f"{T:>9}"
        for a in (1, 2, 3, 4, 5):
            row += f"  {max(0.0, lt - Es[a]):>7.2f} "
        print(row)
    print("\n  Every column -> infinity in T at slope 1. The free budget E(a) is a")
    print("  finite intercept for every arity. NO free unbounded bundle channel.")


if __name__ == "__main__":
    main()
