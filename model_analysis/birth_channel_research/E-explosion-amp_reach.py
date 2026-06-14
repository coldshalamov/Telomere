#!/usr/bin/env python3
"""
E-explosion-amp_reach.py

The honest MAX-FREE-REACH K for lane E, and the proof that a period-P salt
schedule cannot extend it (it only converts free reach into supply loss).

TWO independent accountings:

(I)  EXPLOSION-ONLY REACH (no schedule, fresh dice the whole way).
     The free budget E ~= 2.5 bits/record is a per-record FALSE-NON-EXPLOSION
     rate: a wrong-salt trial-open survives (fails to explode) with prob
     q = 2^-E ~= 0.177. On a reverse walk, each still-encoded record is
     trial-opened at each candidate step; a record born on pass t becomes
     ambiguous if some WRONG step also survives the explosion check.
     Expected false survivors per record over a window of C candidate steps:
        E[false] = (C-1) * q .
     Deterministic (unique) decode needs E[false] < 1 over the whole file:
        R_live * (C-1) * q < 1
     where R_live is the number of simultaneously-ambiguous records and C is
     the candidate-step window. This sets the reach.

(II) PERIOD-P SCHEDULE LEDGER. A period-P refresh key gives only P distinct
     deadlock-breaking keys (freshness_law_validation.py: position-only
     salting deadlocks -> zero accepts from pass 3; a pass-distinct key is
     REQUIRED, and period-P supplies only P of them). So match supply is
     capped at ~P distinct draws/window. We show the "2x supply loss per bit
     gained" law and that net is monotonically worse than explosion-only.
"""

from math import log2, exp

P_HIT = 0.0039
WIN_BITS = 2.17
E_BITS = 2.5                 # free explosion budget (MEASURED, row 7)
Q_FALSE = 2 ** (-E_BITS)     # per-trial false-non-explosion prob ~= 0.177

# ============================================================================
# (I) EXPLOSION-ONLY REACH  -- the real free reach, no schedule
# ============================================================================
def expected_false_survivors(R_live, C_candidates, q=Q_FALSE):
    """Expected wrong-step openings that survive the explosion check.
    Each of R_live ambiguous records has (C_candidates-1) wrong steps, each
    surviving with prob q (independent under the uniform-hash law)."""
    return R_live * max(0, C_candidates - 1) * q

def reach_for_unique_decode(R_live, q=Q_FALSE, target=1.0):
    """Largest candidate-step window C such that expected false survivors < target.
       R_live*(C-1)*q < target  ->  C < 1 + target/(R_live*q)."""
    C = 1.0 + target / (R_live * q)
    return C  # candidate steps a record can stay ambiguous and still resolve uniquely

# ============================================================================
# (II) PERIOD-P SCHEDULE: supply cap and the 2x-per-bit law
# ============================================================================
def coverage(distinct_draws, p=P_HIT):
    return 1.0 - (1.0 - p) ** distinct_draws

def supply_loss_per_bit():
    """The 'geometric starvation ~2x per bit' law (PLAIN_STATUS row 9).
    A convention that buys b bits of birth disambiguation by shrinking the
    distinct-draw pool from full to a 2^-b fraction multiplies match supply
    by ~2^-b: each bit gained HALVES supply. Demonstrate with the schedule:
    period P uses log2(P) bits of 'schedule structure' to label passes, and
    caps distinct draws at P -- relate the two."""
    print("  schedule  log2(P)bits  distinct_draws  cov_ceiling  cov/cov_fresh@1024")
    cov_fresh = coverage(1024)
    for P in [2, 4, 5, 6, 8, 16, 32, 64]:
        cov = coverage(P)
        ratio = cov / cov_fresh
        print(f"   P={P:>3}    {log2(P):>6.2f}      {P:>6}        {cov:>9.5f}   {ratio:>8.4f}")
    print("  -> each doubling of P (one more bit of schedule labels) only ~doubles")
    print("     distinct draws; but reaching the FRESH ceiling needs ~1024 draws,")
    print("     so the schedule is supply-starved by the ratio above. Conversely,")
    print("     to make residue free you need P<=2^E=5.66 -> P<=5 -> <=5 draws,")
    print(f"     coverage ceiling {coverage(5):.5f} vs fresh {cov_fresh:.5f}"
          f" ({coverage(5)/cov_fresh*100:.2f}% of fresh).")

def main():
    print("=" * 78)
    print("(I) EXPLOSION-ONLY REACH  (no schedule; fresh dice; the real free prize)")
    print("=" * 78)
    print(f"  free budget E = {E_BITS} bits -> false-non-explosion prob q = {Q_FALSE:.4f}")
    print()
    print("  Reach = how many candidate reverse-steps a record can stay ambiguous")
    print("  before a wrong step coincidentally survives the explosion check.")
    print()
    print(f"  {'R_live':>8} {'unique-decode C (steps)':>26} {'interpretation':>10}")
    for R in [1, 8, 64, 512, 4096, 100000]:
        C = reach_for_unique_decode(R)
        print(f"  {R:>8} {C:>26.3f}")
    print()
    print("  KEY READING: with R_live simultaneously-ambiguous records, the free")
    print("  reach in candidate-steps is C ~= 1 + 1/(R_live*q). For a single")
    print(f"  ambiguous record (R=1): C ~= {reach_for_unique_decode(1):.2f} steps")
    print(f"  -- matching the '~5-6 passes' folklore (2^E = {2**E_BITS:.2f}).")
    print("  But the file has MANY records ambiguous at once; the budget is SHARED.")
    print("  At R_live=4096, C-1 < {:.2e}: less than ONE step of slack -- the free"
          .format(1/(4096*Q_FALSE)))
    print("  reach for DETERMINISTIC whole-file decode collapses below 1 pass once")
    print("  the live-record count is large. The 2.5 bits is PER RECORD but the")
    print("  ambiguity is PER (record x step x other-record); it does not tile.")
    print()
    print("=" * 78)
    print("(II) PERIOD-P SALT SCHEDULE  (the proposed amplifier) -- the leak")
    print("=" * 78)
    supply_loss_per_bit()
    print()
    print("  NET verdict: the schedule's residue is free only for P<=5, where it")
    print("  caps distinct draws at 5 (coverage ~{:.4f}, vs fresh-at-T climbing to"
          .format(coverage(5)))
    print("  1.0). It buys NO new disambiguation the explosion check didn't already")
    print("  give (the explosion check distinguishes 5.66 candidates directly), and")
    print("  it PAYS for the relabeling in capped supply. Gross reach unchanged;")
    print("  net reach strictly worse. The schedule is a pure loss.")
    print()
    print("=" * 78)
    print("COUNTING GATE")
    print("=" * 78)
    print("  If the explosion check were free + content-blind + UNBOUNDED, random")
    print("  data would net-compress without bound -> pigeonhole violation. It is")
    print("  NOT unbounded: the free budget E is FINITE (~2.5 bits) because a")
    print("  wrong-salt expansion still parses cleanly with prob q=2^-E (the hash")
    print("  is content-blind: a wrong salt yields a uniform digest that parses as")
    print("  valid items with the same probability a right one does, minus the")
    print("  checksum/self-delimiting filter). The finite resource is the")
    print("  STRUCTURE currency: ~2.5 bits/record of distinguishing power, SHARED")
    print("  across all simultaneously-ambiguous records. It cannot grow with T.")

if __name__ == "__main__":
    main()
