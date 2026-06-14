#!/usr/bin/env python3
"""
E-explosion-amp_supply_ledger.py

LANE E: explosion-check amplification with a period-P salt schedule.

The idea under test
-------------------
The free explosion check (Result-Ledger row 7 / PLAIN_STATUS row 7) supplies
~2.5 bits/record: at decode you can TRIAL-open a record at each candidate
reverse-step and detect the right one by *non-explosion* (a wrong-salt
expansion fails to parse / leaves dangling garbage / fails the checksum).
2.5 bits distinguishes 2^2.5 ~= 5.66 candidate births for free.

To reach past ~6 passes, narrow the candidate set with STRUCTURE: a salt
schedule of period P, so the salt-key depends only on t mod P. Then (so the
story goes) the explosion check covers the residue r = t mod P (log2 P bits),
and the schedule covers the quotient q = t // P. Reach extends to ... how far?

THE LEAK (the whole point of this lane)
---------------------------------------
A period-P salt schedule REUSES the lottery every P passes. A window that
missed on pass t with salt-key (t mod P) faces the IDENTICAL dice on pass
t+P: same seed enumeration, same salt, same content -> same SHA digest ->
guaranteed miss again. So a window gets only P *distinct* dice draws total,
no matter how many passes T you run. The match supply is CAPPED at P.

This file does the exact counting:
  (1) Fresh-dice baseline: coverage after T passes with T independent draws.
  (2) Period-P schedule: coverage capped at P distinct draws -> a HARD ceiling.
  (3) The net ledger: bits earned (coverage * win) MINUS bits lost to supply
      starvation, vs. the free explosion reach with NO schedule.

We compare three configs head to head:
  A. No schedule, explosion check alone: reach K_free ~ 5-6 passes of *useful*
     disambiguation, but fresh dice the whole way (no supply loss).
  B. Period-P schedule: explosion covers residue, schedule "covers" quotient,
     but supply is capped at P draws/window.
  C. The honest question: does B ever beat A on NET earned bits?

All exact counting against the uniform-hash law P(match)=p per (seed,salt,
content) trial; no luck, no real SHA needed (the leak is a counting fact:
identical inputs to a deterministic hash give identical outputs).
"""

from math import log2, isclose

# ---- parameters from the repo (Golden Config B8/canonical/a2) ----------------
# Per-(window,pass,key) compressive-hit probability at the frontier.
# GOLDEN_CONFIG row: p_random = 0.0039 per pair-window. Use that as the base.
P_HIT = 0.0039
WIN_BITS = 2.17           # E[win|hit], canonical a2 (GOLDEN_CONFIG / MATH_MODEL 2)
EXPLOSION_BITS = 2.5      # free disambiguation budget (row 7, MEASURED)

def coverage_fresh(T, p=P_HIT):
    """Fresh dice every pass: T independent draws per window.
    P(window matched by pass T) = 1 - (1-p)^T."""
    return 1.0 - (1.0 - p) ** T

def coverage_periodic(T, P, p=P_HIT):
    """Period-P salt schedule: a window sees only min(T,P) DISTINCT draws.
    Replays of a missed draw miss again (deterministic hash). So coverage
    saturates at the P-draw ceiling no matter how large T is."""
    distinct = min(T, P)
    return 1.0 - (1.0 - p) ** distinct

def explosion_reach_residue(P):
    """Can the free explosion check (2.5 bits) disambiguate P residues?
    It distinguishes up to 2^EXPLOSION_BITS ~= 5.66 candidates for free.
    Returns the per-record EXTRA stored bits needed if P exceeds that."""
    free_candidates = 2 ** EXPLOSION_BITS
    if P <= free_candidates:
        return 0.0
    # must store the overflow: log2(P) - 2.5 bits per record
    return log2(P) - EXPLOSION_BITS

def net_per_window(T, P=None, p=P_HIT):
    """Net bits earned per ORIGINAL window over a run.
    earned = coverage * win_bits ; charged = residue overflow (if any)
    paid PER MATCHED record (only matched records need a birth pass)."""
    if P is None:
        cov = coverage_fresh(T, p)
        overflow = 0.0
    else:
        cov = coverage_periodic(T, P, p)
        overflow = explosion_reach_residue(P)
    earned = cov * WIN_BITS
    charged = cov * overflow      # only matched records carry birth info
    return earned - charged, cov, earned, charged

# ----------------------------------------------------------------------------
def main():
    print("=" * 78)
    print("LANE E: explosion-check amplification with period-P salt schedule")
    print("=" * 78)
    print(f"  p_hit (per window,pass,key) = {P_HIT}   (GOLDEN random base rate)")
    print(f"  win = {WIN_BITS} bits ; free explosion budget = {EXPLOSION_BITS} bits"
          f" (~{2**EXPLOSION_BITS:.2f} candidate passes)")
    print()

    # ---- (1) the supply ceiling: coverage saturates at min(T,P) draws -------
    print("-- (1) COVERAGE: fresh dice vs period-P schedule --")
    print(f"  {'T':>5} {'fresh cov':>12} {'P=6 cov':>10} {'P=16 cov':>10}"
          f" {'P=64 cov':>10}")
    for T in [6, 16, 32, 64, 128, 256, 1024, 4096, 100000]:
        cf = coverage_fresh(T)
        c6 = coverage_periodic(T, 6)
        c16 = coverage_periodic(T, 16)
        c64 = coverage_periodic(T, 64)
        print(f"  {T:>5} {cf:>12.5f} {c6:>10.5f} {c16:>10.5f} {c64:>10.5f}")
    print("  -> period-P coverage is FROZEN at its min(T,P)=P value:")
    print(f"     P=6 ceiling  = {coverage_periodic(10**9,6):.5f}")
    print(f"     P=16 ceiling = {coverage_periodic(10**9,16):.5f}")
    print(f"     P=64 ceiling = {coverage_periodic(10**9,64):.5f}")
    print("     fresh dice keep climbing toward 1.0; the schedule does NOT.")
    print()

    # ---- (2) the supply loss in bits: how many draws did we forfeit? --------
    print("-- (2) SUPPLY LOSS: draws forfeited by the schedule --")
    print("  At large T, fresh dice -> coverage 1.0; schedule -> coverage(P).")
    print("  The forfeited coverage is pure lost earnings (win bits never won).")
    for P in [6, 16, 64]:
        cov_cap = coverage_periodic(10**9, P)
        forfeit = 1.0 - cov_cap
        print(f"  P={P:>3}: coverage ceiling {cov_cap:.5f}, "
              f"forfeited fraction {forfeit:.5f} "
              f"-> {forfeit*WIN_BITS:.4f} win-bits/window lost vs fresh-at-infinity")
    print()

    # ---- (3) THE NET LEDGER: does any schedule beat no-schedule? ------------
    print("-- (3) NET LEDGER: period-P schedule vs explosion-only (no schedule) --")
    print("  config A = NO schedule, explosion alone (fresh dice, reach ~K_free)")
    print("  config B = period-P schedule (residue free if P<=5.66, else taxed)")
    print()
    print(f"  {'T':>6} {'A:net/win(fresh)':>18} {'B P=6':>10} {'B P=16':>10}"
          f" {'B P=64':>10}  (net bits per window)")
    for T in [6, 16, 64, 256, 1024, 4096]:
        nA, *_ = net_per_window(T, None)
        nB6, *_ = net_per_window(T, 6)
        nB16, *_ = net_per_window(T, 16)
        nB64, *_ = net_per_window(T, 64)
        print(f"  {T:>6} {nA:>18.5f} {nB6:>10.5f} {nB16:>10.5f} {nB64:>10.5f}")
    print()

    # ---- (4) the crux: where does explosion-only's reach actually END? ------
    print("-- (4) THE REAL WALL for explosion-only (no schedule) --")
    print("  The explosion check distinguishes ~5.66 candidate OPEN-STEPS for a")
    print("  record. But in the maintainer's reverse walk the candidate set is")
    print("  the records still-encoded at that step; a record born on pass t can")
    print("  in principle be confused with any of the OTHER live records' birth")
    print("  steps. The free budget caps the per-record candidate count at ~5.66")
    print("  REGARDLESS of schedule. So the honest free reach is set by how many")
    print("  passes can elapse before a record's candidate-birth set exceeds 5.66")
    print("  -- which is ~5-6 passes of *simultaneously-ambiguous* records,")
    print("  NOT 5-6 total passes (older records resolve as the walk proceeds).")
    print()
    print("  The schedule does NOT raise this: it only renames the candidates by")
    print("  residue, and pays for it in supply. See (3): every B column is <= A.")

if __name__ == "__main__":
    main()
