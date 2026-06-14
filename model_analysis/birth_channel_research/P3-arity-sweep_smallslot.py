#!/usr/bin/env python3
"""
P3-arity-sweep_smallslot.py

CORRECTION to P3-arity-sweep_Gsaturation.py: section (1) there was run at slot=0,
which is DEGENERATE — at slot 0 the j0=0 geometric candidate gives F[0]=slot for
every epoch k and the left-prune any(f<slot)=any(f<0) never fires, so G=T is an
IDENTITY, not a measurement. The threatening case (mechanism b) is the slot with
the SMALLEST G. Section (2) of the prior toy showed a=4,T=800,slot8 -> G=106
(G/T~0.13) but never swept T.

THIS toy sweeps T at the small-G slots. The discriminating question:
  * G grows with T (even slope < 1)  -> O(T) survivors -> mechanism (a), lane CONFIRMED.
  * G stays flat / O(1)              -> a hard pin -> mechanism (b) candidate ->
                                        escalate to the counting gate.

HYPOTHESIS: the binding constraint at slot>0 is the left-prune (no child may
forward-walk to a position left of the seed slot). It removes a constant FRACTION
of epochs, and a constant fraction of T is still O(T). So I expect G to keep
growing — e.g. a=4 slot8 ~106 at T=800 -> ~hundreds at T=3200, not flat.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bundle", str(HERE / "P2-bundle_survivor.py"))
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
geom_candidates = bundle.geom_candidates
orbit_tables = bundle.orbit_tables


def G_at(a, T, N, slot):
    FWD, BWD, _f, _b = orbit_tables(N, T)
    cands = geom_candidates(slot, N, T, FWD, BWD, set(), a)
    return len(set(k for (k, q, F) in cands)), len(cands)


def section(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def main():
    Ts = [50, 100, 200, 400, 800, 1600, 3200, 6400]
    section("G_epochs(a, T) at SMALL-G slots — the real saturation test")
    # find, per arity, the slot with the smallest G at a reference T, then sweep T there.
    for a in (2, 3, 4, 5):
        N = max(16, a + 12)
        Tref = 800
        FWD, BWD, _f, _b = orbit_tables(N, Tref)
        gslot = []
        for slot in range(N - a):  # seed slot must leave room for the block
            cands = geom_candidates(slot, N, Tref, FWD, BWD, set(), a)
            gslot.append((len(set(k for (k, q, F) in cands)), slot))
        gslot.sort()
        small_slots = [s for (_g, s) in gslot[:3]]  # 3 smallest-G slots at Tref
        print(f"\n  --- arity a={a}, N={N}; smallest-G slots at T={Tref}: "
              f"{[(g,s) for g,s in gslot[:3]]} ---")
        print(f"  {'slot':>5} | " + " ".join(f"T={T:>5}" for T in Ts))
        for slot in small_slots:
            row = []
            for T in Ts:
                G, nc = G_at(a, T, N, slot)
                row.append(f"{G:>7}")
            print(f"  {slot:>5} | " + " ".join(row))
        # growth ratio: G(T=6400)/G(T=800) — ~8 if linear-in-T, ~1 if O(1) pin
        print(f"  growth G(6400)/G(800) per slot (8x => linear in T; ~1 => O(1) pin):")
        for slot in small_slots:
            g800, _ = G_at(a, 800, N, slot)
            g6400, _ = G_at(a, 6400, N, slot)
            ratio = g6400 / g800 if g800 else float('nan')
            print(f"    slot {slot:>2}: G(800)={g800:>5}  G(6400)={g6400:>6}  "
                  f"ratio={ratio:>5.2f}")

    section("VERDICT")
    print("  If ratio ~ 8 (= 6400/800) at every small slot: G is LINEAR in T,")
    print("  survivors O(T) -> base=1+(G-1)q>1 -> exponential -> mechanism (a),")
    print("  lane CONFIRMED even at the worst (smallest-G) slot.")
    print("  If ratio ~ 1 (G flat): O(1) pin -> mechanism (b) -> counting gate.")


if __name__ == "__main__":
    main()
