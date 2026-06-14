#!/usr/bin/env python3
"""
H-impossibility_residual_ledger.py

LANE H — exact residual accounting for the birth channel. NO luck, NO hashing:
pure counting (BRIEF protocol rule 3). It computes the per-record unpaid birth
bill after subtracting the two FINITE free subsidies the wire actually supplies:

  (1) structural explosion non-blowup: ~2.5 bits/record  (Result-Ledger row 7,
      MEASURED elsewhere; taken as a parameter S_struct here),
  (2) the per-file checksum referee: c bits TOTAL (c~64), amortized over N
      records as c/N bits/record (proven-by-math: a c-bit hash distinguishes at
      most 2^c global decode hypotheses).

It also folds in the ORBIT subsidy discovered by H-impossibility_birth_coordinate.py:
the position-salt sequence under i->(5i mod P)+1 has period = ord, the
multiplicative order of 5 in the cycle-walk group, so the number of DISTINCT
candidate birth salts a record can have is min(T, ord), capping per-record birth
entropy at log2(min(T, ord)) rather than log2(T).

The output is the max-free-reach K: the largest T at which residual <= 0
(channel still free), and the bill in bits/record beyond it. This is the sharp
impossibility's quantitative face.
"""
from math import log2, ceil


def per_record_birth_entropy(T, orbit):
    """Worst-case bits to name a record's birth pass, given the orbit subsidy.
    A record born anywhere in 1..T, but salts repeat with period `orbit`, so the
    bytes only distinguish among min(T, orbit) classes. The FULL birth pass
    still needs log2(T) to locate the reverse step (you must open at the right
    pass even if two passes share a salt), BUT salt-collisions mean the decoder
    cannot use the bytes to separate same-salt passes — that ambiguity must be
    resolved by the referee. We report both:
      H_locate  = log2(T)            (reverse-step location, the hard quantity)
      H_salt    = log2(min(T,orbit)) (distinct byte-outcomes; what explosion can see)
    The unpayable remainder is driven by H_locate; the explosion check only ever
    sees H_salt-worth of structure. So the residual uses H_locate for the bill
    and S_struct (<=~2.5) for the free part."""
    H_locate = log2(T) if T > 1 else 0.0
    H_salt = log2(min(T, orbit)) if min(T, orbit) > 1 else 0.0
    return H_locate, H_salt


def residual_per_record(T, N, orbit, S_struct=2.5, c_checksum=64):
    H_locate, H_salt = per_record_birth_entropy(T, orbit)
    free_struct = min(S_struct, H_salt)     # explosion can only cover what the
                                            # bytes actually distinguish (H_salt)
    free_checksum = c_checksum / N          # amortized referee capacity / record
    free_total = free_struct + free_checksum
    residual = max(0.0, H_locate - free_total)
    return dict(H_locate=H_locate, H_salt=H_salt, free_struct=free_struct,
                free_checksum=free_checksum, residual=residual)


def main():
    print("== H residual ledger: unpaid birth bits/record vs T ==")
    print("   free subsidies: structural explosion S<=2.5 b/rec (measured row 7)")
    print("                   + checksum 64 b/file amortized (c/N b/rec).")
    print("   orbit subsidy: salts repeat with period `orbit` (measured by")
    print("   H-impossibility_birth_coordinate.py; small for small boards).\n")

    for (N, orbit) in [(1000, 1000), (1000, 64), (10000, 10000), (10000, 64)]:
        print(f"  --- N={N} records, orbit(salt-period)={orbit} ---")
        print(f"   {'T':>5} {'H_locate':>9} {'H_salt':>7} {'free_str':>9} "
              f"{'free_cks':>9} {'residual':>9}")
        K = None
        for T in [2, 4, 5, 6, 8, 16, 32, 64, 128, 256]:
            r = residual_per_record(T, N, orbit)
            if r["residual"] <= 1e-9:
                K = T
            flag = "  <- free" if r["residual"] <= 1e-9 else ""
            print(f"   {T:>5} {r['H_locate']:>9.3f} {r['H_salt']:>7.3f} "
                  f"{r['free_struct']:>9.3f} {r['free_checksum']:>9.5f} "
                  f"{r['residual']:>9.3f}{flag}")
        print(f"   => MAX-FREE-REACH K (residual still 0) = {K} passes\n")

    print("  Interpretation:")
    print("   - While T <= ~6 the structural 2.5 bits covers H_locate -> FREE.")
    print("   - The 64-bit checksum is a per-FILE constant: at N=1000 it adds")
    print("     only 0.064 b/rec; it cannot scale the channel (THE_OPEN_QUESTION")
    print("     'global pass counter: 16 bits total cannot carry per-record').")
    print("   - Past K, residual = log2(T) - 2.5 - 64/N > 0 grows like log2(T):")
    print("     the UNPAYABLE remainder. At T=64,N=1000: ~3.4 bits/record,")
    print("     swamping the ~2-bit win => net negative (MATH_MODEL §7b).")
    print("   - A LARGER orbit does NOT help: H_locate uses log2(T) regardless")
    print("     of orbit (you still must open at the right reverse step). The")
    print("     orbit only caps what the explosion check can SEE (H_salt), it")
    print("     never reduces the location bill. This is why avenue A (orbit")
    print("     phase) cannot by itself free the singles channel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
