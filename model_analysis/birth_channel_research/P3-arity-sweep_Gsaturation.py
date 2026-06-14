#!/usr/bin/env python3
"""
P3-arity-sweep_Gsaturation.py  (ADVERSARIAL SKEPTIC 3 — bundle-lane refutation attempt)

THE ONE UNTESTED ASSERTION in the bundle lane (findings/P2-bundle.md NEXT:):
    "arity-3+ raises E (bigger K) but the slope log2(T)-E is unchanged."
This was ASSERTED, never measured. The toy P2-bundle_survivor.py hardcodes A=2
for every survivor run. The decisive quantity is the GEOMETRIC candidate count:

    G_epochs(a, T) = # distinct epochs k in 1..T that the content-blind
                     affine-stride filter admits for an arity-a bundle.

  * If G_epochs(a,T) keeps GROWING with T  -> mechanism (a): base=1+(G-1)q>1,
    survivors base^R exponential, slope log2(T)-E -> the lane is RIGHT.
  * If G_epochs(a,T) SATURATES at O(1) for some arity -> mechanism (b): a hard
    arithmetic pin -> survivors polynomial -> a REAL free channel candidate that
    must then face the counting gate.

HYPOTHESIS (before running): The binding geometric constraint is
min(F)==slot over an a-wide forward-walked block, with `a` candidate offsets j0
per epoch. Higher arity gives MORE offsets per epoch (looser) but a LARGER block
footprint that must land its minimum exactly on `slot` (tighter). I expect the
net effect to LEAVE G ~ O(T) (still linear-ish in T), so the lane's assertion
holds and the verdict is confirms-impossibility. I run it because it is the one
thing the lane did not actually measure.

This reuses the EXACT geom_candidates / orbit-table machinery from
P2-bundle_survivor.py — content-blind, reads only positions/N/a. Real shuffle.
"""
import sys, importlib.util, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "bundle", str(HERE / "P2-bundle_survivor.py"))
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)

geom_candidates = bundle.geom_candidates
orbit_tables = bundle.orbit_tables
avalid = bundle.avalid


def q_for_arity(a):
    L = a * bundle.B
    av = avalid(a, L)
    q = av / (1 << L)
    E = L - math.log2(av) if av else float('inf')
    return q, E, av, L


def section(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def G_epochs_for(a, T, N, slot):
    """Distinct epochs the content-blind geometric filter admits for an arity-a
    bundle whose seed sits at wire `slot`, on an N-slot board with T passes.
    filled={} (isolated bundle channel — same isolation the lane uses)."""
    FWD, BWD, _f, _b = orbit_tables(N, T)
    cands = geom_candidates(slot, N, T, FWD, BWD, set(), a)
    epochs = sorted(set(k for (k, q, F) in cands))
    return len(epochs), len(cands)


def main():
    section("P3 ARITY SWEEP — does G_epochs(a,T) GROW or SATURATE?")
    print("  q_bundle / E / knee K=2^E per arity (the lane's intercept claim):")
    print(f"  {'a':>2} {'avalid(a,aB)':>13} {'q':>12} {'E (bits)':>10} {'K=2^E':>14}")
    for a in (1, 2, 3, 4, 5):
        q, E, av, L = q_for_arity(a)
        K = (1.0 / q) if q > 0 else float('inf')
        print(f"  {a:>2} {av:>13} {q:>12.3e} {E:>10.4f} {K:>14.1f}")

    section("(1) G_epochs(a, T) vs T — the saturation test")
    print("  For each arity, sweep T. Seed sits at a fixed wire slot. The")
    print("  question: does the # of admitted epochs keep climbing with T?")
    print("  If it FLATTENS for some arity -> mechanism (b) candidate.")
    Ts = [50, 100, 200, 400, 800, 1600, 3200]
    for a in (2, 3, 4, 5):
        print(f"\n  --- arity a={a} ---")
        print(f"  {'T':>6} {'N':>5} {'slot':>5} {'G_epochs':>10} "
              f"{'#cands':>8} {'G/T':>7}")
        for T in Ts:
            # Board must hold an a-wide block with room; use the lane's sizing
            # plus headroom so the geometry is not artificially clipped.
            N = max(16, a + 12)
            slot = 0  # worst case: leftmost slot (most reverse-walks land valid)
            G, nc = G_epochs_for(a, T, N, slot)
            print(f"  {T:>6} {N:>5} {slot:>5} {G:>10} {nc:>8} {G/T:>7.3f}")

    section("(2) SLOT DEPENDENCE — is G small only for a special slot?")
    print("  Check several seed slots at fixed T to rule out a slot-artifact.")
    T = 800
    for a in (2, 4):
        print(f"\n  --- arity a={a}, T={T} ---")
        N = max(16, a + 12)
        print(f"  {'slot':>5} {'G_epochs':>10} {'#cands':>8}")
        for slot in range(0, min(N, 10)):
            G, nc = G_epochs_for(a, T, N, slot)
            print(f"  {slot:>5} {G:>10} {nc:>8}")

    section("(3) BOARD-SIZE DEPENDENCE — does a bigger board change G(T)?")
    print("  If G tracks board size rather than T, the 'pin' would be a board")
    print("  artifact, not an epoch pin. Vary N at fixed (a,T).")
    a, T = 3, 800
    print(f"  arity a={a}, T={T}")
    print(f"  {'N':>5} {'G_epochs':>10} {'#cands':>8}")
    for N in (16, 24, 40, 80, 160):
        G, nc = G_epochs_for(a, T, N, 0)
        print(f"  {N:>5} {G:>10} {nc:>8}")

    section("VERDICT READOUT")
    print("  Read column G/T in (1):")
    print("   * G/T roughly CONSTANT (G grows linearly in T)  -> mechanism (a),")
    print("     lane CONFIRMED, slope log2(T)-E stands for all arity.")
    print("   * G/T -> 0 with G flattening to a constant        -> mechanism (b)")
    print("     candidate; escalate to the counting gate (does it saturate on")
    print("     RANDOM data? if yes, name the currency or it's a pigeonhole leak).")


if __name__ == "__main__":
    main()
