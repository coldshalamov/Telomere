#!/usr/bin/env python3
"""
P3-arity-slope_and_supply.py

Two closing checks on the arity-escape route (the only way the bundle lane could
have a hole), given P3-arity-sweep showed G_epochs(a,T)=T (no O(1) pin):

(A) RESIDUAL SLOPE per arity: with G=T (measured), the per-bundle birth residual
    is log2(base) = log2(1+(T-1)q_a). Does raising arity (raising E_a) ever make
    this BOUNDED in T? Claim to test: log2(base) -> log2(T) - E_a, which grows
    without bound for EVERY finite E_a. So arity shifts the intercept, never the
    slope. (Lane's NEXT assertion — now checked at the residual level, not asserted.)

(B) SUPPLY CURRENCY: the advisor's point. A real arity-a match needs a seed whose
    hash equals a*B SPECIFIC content bits, hit-density 2^-(a*B). The free budget
    E_a = a*B - log2(avalid(a,aB)) grows only ~linearly in a, so K=2^E_a rises —
    but the match SUPPLY collapses as 2^-(a*B), which outruns K. Quantify: even at
    the knee where birth is "free", the EXPECTED COUNT of arity-a bundles you can
    actually plant from a finite stream collapses. The arity route does not pay in
    stored-bits (the lane's slope) — it is blocked EARLIER, in hit-density.
"""
import math, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bundle", str(HERE / "P2-bundle_survivor.py"))
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
avalid = bundle.avalid
B = bundle.B


def q_E(a):
    L = a * B
    av = avalid(a, L)
    return av / (1 << L), L - math.log2(av), av, L


def section(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def main():
    section("(A) RESIDUAL SLOPE per arity (G=T measured) — log2(1+(T-1)q_a)")
    print("  Per-bundle birth residual the checksum must store. Asymptote = log2(T)-E_a.")
    arities = [2, 3, 4, 5]
    qE = {a: q_E(a) for a in arities}
    print("  E_a (bits): " + "  ".join(f"a={a}:{qE[a][1]:.2f}" for a in arities))
    hdr = "  " + f"{'T':>9} | " + " | ".join(f"a={a:>1} resid (asy)" for a in arities)
    print(hdr)
    for T in (100, 655, 6186, 32198, 1_000_000, 10**9):
        cells = []
        for a in arities:
            q, E, *_ = qE[a]
            base = 1 + (T - 1) * q
            resid = math.log2(base)
            asy = max(0.0, math.log2(T) - E)
            cells.append(f"{resid:6.3f}({asy:5.2f})")
        print(f"  {T:>9} | " + " | ".join(cells))
    print()
    print("  Every arity column GROWS without bound in T; resid -> log2(T)-E_a.")
    print("  Raising arity 2->5 lifts E from 9.36 to 18.20 bits = shifts the knee")
    print("  K=2^E from 655 to 302029 passes, but the SLOPE in log2(T) is 1 for")
    print("  EVERY arity. No arity makes the residual bounded. Lane NEXT confirmed.")

    section("(B) SUPPLY CURRENCY — the arity escape pays in HIT-DENSITY, not stored-bits")
    print("  A real arity-a bundle match: a seed whose H(seed|salt) equals the a*B")
    print("  SPECIFIC content bits being replaced. Hit density = 2^-(a*B).")
    print("  Free birth budget E_a buys knee K_a = 2^E_a passes of ~free epoch.")
    print("  But to FILL one arity-a bundle you must find a matching seed: expected")
    print("  search 2^(a*B); and a length-L stream offers ~L/(a*B) candidate spans,")
    print("  each matching w.p. 2^-(a*B). Expected planted bundles ~ L*2^-(a*B)/(aB).")
    print()
    print(f"  {'a':>2} {'a*B':>4} {'E_a':>7} {'K=2^E_a':>11} {'hit dens 2^-aB':>15} "
          f"{'K * hitdens':>12}")
    for a in arities:
        q, E, av, L = qE[a]
        K = 2 ** E
        hd = 2.0 ** (-(a * B))
        print(f"  {a:>2} {a*B:>4} {E:>7.3f} {K:>11.1f} {hd:>15.3e} {K*hd:>12.3e}")
    print()
    print("  K*hitdens column: the free-reach knee times the per-span match prob.")
    print("  It collapses toward 0 as arity rises (E_a grows ~linearly in a, but")
    print("  a*B grows linearly too and dominates: K*2^-aB = 2^(E_a - aB) =")
    print("  2^(-log2 avalid(a,aB)) = 1/avalid -> 0). So the bigger free knee is")
    print("  paid for in match SUPPLY: you can reach more passes free per bundle,")
    print("  but there are exponentially FEWER arity-a bundles to plant.")
    print()
    print("  E_a - a*B = -log2(avalid(a,aB)):")
    for a in arities:
        q, E, av, L = qE[a]
        print(f"    a={a}: E_a - a*B = {E - a*B:+.3f} bits  (= -log2 {av})")
    print()
    print("  CONCLUSION: arity raises the free intercept K but at hit-density cost")
    print("  2^-(aB) that outruns it. Same wall, a DIFFERENT currency than the")
    print("  stored-bits slope. No free unbounded bundle channel from higher arity.")


if __name__ == "__main__":
    main()
