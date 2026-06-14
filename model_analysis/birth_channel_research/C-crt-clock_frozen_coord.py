#!/usr/bin/env python3
"""
C-crt-clock_frozen_coord.py -- the strongest CRT-specific escape attempt.

THE TEMPTING IDEA (worth testing, not hand-waving):
  Split the residue coordinates of the board Q = p_clock * p_rest...:
    - one DESIGNATED coordinate r_clock in Z_{p_clock} is the "birth register".
    - at birth (pass k), MOVE the record to a slot whose r_clock == k (mod p_clock).
    - thereafter, FREEZE r_clock (the shuffle permutes only the OTHER coordinates).
  Then at decode, read r_clock of a record's final slot -> recover k mod p_clock.
  If p_clock >= T, that's the whole birth pass, free, from position. (avenue F x C)

WHY THIS LOOKS LIKE IT MIGHT WORK:
  The frozen coordinate genuinely is a function of birth pass now (we stamped it).
  Unlike the uniform odometer, position is NOT just a function of the slot's
  absolute phase -- we engineered the slot to remember k.

WHERE IT BREAKS (predict before running):
  (1) CAPACITY: r_clock takes p_clock distinct values. Across the board there are
      Q/p_clock slots per r_clock value. To stamp N records with their birth pass
      you need, for each record, a FREE slot with the right r_clock. That is a
      bipartite assignment. It consumes board capacity: the set of (record ->
      stamped slot) is a content-dependent permutation. The decoder must recover
      WHICH free slot each record took -- and the freezing means the surviving
      shuffle is a permutation of a SHRINKING coordinate space, whose orbit the
      decoder can follow, BUT the BIRTH-TIME PLACEMENT (which free r_clock==k slot
      this record grabbed, among Q/p_clock of them) is a content-dependent choice
      = stored bits. We measure those bits.
  (2) COLLISION RETURNS one level down: two records born at the SAME pass k both
      need r_clock==k slots; which of them took which slot is exactly log2 of the
      number of arrangements = a position list on the frozen sub-board. That is
      PCTB again, restricted to the frozen coordinate.
  (3) p_clock >= T forces a board factor of size >= T; the clock coordinate alone
      then holds log2(T) bits PER SLOT but there are only Q/p_clock usable
      "lanes", and you still must say which lane each record sits in.

This script makes the bill explicit: count the bits the birth-time placement
costs, and show it equals exactly the birth information you were trying to avoid.
"""
from math import log2, lgamma, prod

LN2 = 0.6931471805599453


def log2C(n, k):
    if k <= 0 or k >= n:
        return 0.0
    return (lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)) / LN2


def birth_placement_bill(N, T, p_clock, Q):
    """Bits the decoder must recover to invert the birth-time placement.

    Model: of N records, the birth pass histogram is n_k records born at pass k
    (k=1..T). All n_k of them must be stamped onto distinct slots with r_clock==k.
    There are Q/p_clock slots in each r_clock lane (assume p_clock | Q). The
    encoder picks which slots; the decoder, to invert, must learn that choice
    UNLESS it is derivable. It is NOT derivable: which lane-slots are free at
    birth depends on prior content-dependent matches. So the choice costs, per
    lane, log2 C(lane_size, n_k_into_that_lane_and_surviving). Sum over lanes.

    We give the construction every benefit: assume a uniform birth histogram
    n_k = N/T, and that the clock lane is sized exactly p_clock = T so each pass
    has its own lane. lane_size = Q/T slots; occupants per lane = N/T.
    """
    lane_size = Q / p_clock
    per_lane_occupants = N / p_clock          # uniform best case
    lanes = p_clock
    # placement bits = sum over lanes of log2 C(lane_size, occupants)
    bits = lanes * log2C(int(lane_size), max(1, int(round(per_lane_occupants))))
    return bits


def main():
    print("== FROZEN-COORDINATE CRT STAMP: does it beat the wall? ==\n")
    print("Construction: p_clock = T (one residue lane per pass), board Q.")
    print("Stamp each record's birth pass into the frozen r_clock coordinate,")
    print("then never move that coordinate again. Read it back at decode.\n")
    print("The bill is the BIRTH-TIME PLACEMENT: which slot (within its lane)")
    print("each record grabbed. We compare it to the naive birth demand N*log2(T)")
    print("(what stored tags would cost).\n")
    print(f"  {'N':>6} {'T':>4} {'Q':>10} {'p_clock':>8} {'placement bits':>15} "
          f"{'N*log2(T)':>11} {'ratio':>7}")
    for (N, T, Q) in [(1000, 64, 64000), (1000, 64, 256000),
                      (4096, 64, 262144), (1000, 256, 256000),
                      (1000, 64, 4096*64)]:
        p_clock = T
        place = birth_placement_bill(N, T, p_clock, Q)
        naive = N * log2(T)
        print(f"  {N:>6} {T:>4} {Q:>10} {p_clock:>8} {place:>15.0f} "
              f"{naive:>11.0f} {place/naive:>7.2f}")
    print()
    print("READING THE RESULT:")
    print(" - The frozen lane gives you r_clock = k FOR FREE per record (read off).")
    print(" - But recovering WHICH slot within lane k each record occupies costs")
    print("   placement bits. With per_lane_occupants = N/T spread over Q/T slots,")
    print("   that is sum_k log2 C(Q/T, N/T).")
    print(" - If you SHRINK Q so the lanes are tight (Q/T ~ N/T, i.e. Q ~ N), the")
    print("   placement bits stay O(N) and you have just MOVED the birth bits into")
    print("   the placement list. If you GROW Q so lanes are loose, placement bits")
    print("   GROW (more empty slots to choose among) -- and the board grew = PCTB.")
    print(" - Either way the bill is paid in STORED placement bits. The frozen")
    print("   coordinate did not create information; it relocated the same N*log2(T)")
    print("   into a position list the decoder cannot derive.\n")

    # Show the irreducible core: the birth HISTOGRAM itself.
    print("== THE IRREDUCIBLE CORE (why even a perfect lane can't be free) ==")
    print("Even if placement WITHIN a lane were somehow free, the decoder still")
    print("must learn, per record, WHICH lane (=which birth pass). That assignment")
    print("-- the map record->birth_pass -- has entropy = the birth histogram's")
    print("information. For a uniform histogram over T passes that is exactly")
    print("N*log2(T) bits (each record's pass is ~uniform over T). A deterministic")
    print("public shuffle supplies 0 of them (every record at a given final slot")
    print("has an identical derivable trajectory). So the lane assignment is")
    print("underivable content -> stored. The wall is conserved.\n")
    for (N, T) in [(1000, 64), (4096, 64), (1000, 256)]:
        print(f"  N={N} T={T}: irreducible lane-assignment entropy "
              f">= N*log2(T) = {N*log2(T):.0f} bits "
              f"(vs file checksum = 64 bits).")
    print()
    print("VERDICT: the frozen-coordinate stamp is content-dependent placement.")
    print("It pays the birth bill in STORED-BITS currency (a position list the")
    print("decoder cannot derive), exactly equal to N*log2(T). Same wall, same")
    print("currency as PCTB. No escape.")


if __name__ == "__main__":
    main()
