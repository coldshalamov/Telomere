#!/usr/bin/env python3
"""
C-crt-clock_odometer.py  -- Avenue C: CRT / residue clocks on a fixed board.

HYPOTHESIS UNDER TEST
---------------------
Board size Q = prod(primes). By CRT a slot index s in [0,Q) <-> residue vector
(s mod p_1, ..., s mod p_m). Proposal: make a pass advance ONE residue
coordinate (an odometer digit). Then -- the hope -- the value of that digit,
READ FROM a record's final position, tells the decoder how many passes have
elapsed since the record was born = its birth-pass register, derived not stored.

Two things must be true for that hope to pay off:
  (H1) the odometer digit at a record's FINAL slot must be a function of the
       record's BIRTH PASS (otherwise it carries no birth info), AND
  (H2) it must do so for every record simultaneously on ONE fixed board, within
       the log2(Q) total bits the board physically holds.

PREDICTION (from the mechanics, before running):
  The odometer is a DETERMINISTIC PUBLIC permutation. Apply it (T - k) times to
  a record born at pass k. The decoder, at the final state, sees only the slot.
  The slot's odometer digits are a function of the slot, identical for any record
  that lands there -- they encode the slot's ABSOLUTE phase, not the record's
  birth pass. Two records that end at the SAME slot but were born at DIFFERENT
  passes are indistinguishable from position. And the board holds log2(Q) bits
  total; N records need N*log2(T) birth bits, which exceeds log2(Q) the instant
  N*log2(T) > log2(Q), i.e. essentially always. So the register cannot fit
  without growing the board -- which IS PCTB.

This script DEMONSTRATES the collision by construction (no luck, exact).
"""
from math import log2, prod, gcd


def crt_residues(s, primes):
    return tuple(s % p for p in primes)


def odometer_step(s, primes):
    """Advance the residue 'odometer' by one tick on a fixed board Q=prod(primes).
    This is the cleanest residue-clock: add 1 to slot index mod Q. By CRT that
    increments every coordinate by 1 (mod p_j) -- a single, reversible,
    PUBLIC permutation of the Q slots. (Any per-pass affine map a*s+b mod Q with
    gcd(a,Q)=1 is an equally-public bijection; +1 is the simplest and the one
    that most cleanly 'advances a clock'.)"""
    Q = prod(primes)
    return (s + 1) % Q


def odometer_step_inv(s, primes):
    Q = prod(primes)
    return (s - 1) % Q


def fwd_pow(s, t, primes):
    for _ in range(t):
        s = odometer_step(s, primes)
    return s


def bwd_pow(s, t, primes):
    for _ in range(t):
        s = odometer_step_inv(s, primes)
    return s


def demo_collision():
    print("== (A) THE COLLISION: same final slot, different birth pass ==")
    primes = [2, 3, 5, 7]          # Q = 210
    Q = prod(primes)
    T = 64                         # passes
    print(f"  board primes={primes}  Q={Q}  passes T={T}")
    print(f"  board capacity = log2(Q) = {log2(Q):.2f} bits  (TOTAL, all slots)\n")

    # Record A born at pass k_A at original slot x_A; record B born at pass k_B
    # at slot x_B. After encoding, both have been carried by the public odometer
    # (T - k) times. The decoder sees only their FINAL slots.
    # We deliberately choose (x_A,k_A) and (x_B,k_B) that land on the SAME final
    # slot to expose the indistinguishability.
    final_slot = 123
    print(f"  pick a final slot f = {final_slot}; its residue vector "
          f"{crt_residues(final_slot, primes)}")
    print("  every record that ENDS at f shows these SAME residues, regardless")
    print("  of when it was born. Enumerate (birth_pass k, birth_position p_k)")
    print("  pairs that all land on f (p_k = slot it occupied when born at k):\n")
    rows = []
    for k in range(1, T + 1):
        shifts = T - k               # odometer applications AFTER birth at pass k
        p_k = bwd_pow(final_slot, shifts, primes)  # the slot it sat at when born
        rows.append((k, p_k))
    for (k, p_k) in rows[:8]:
        print(f"    born pass k={k:2d}  =>  birth position p_k={p_k:3d}  "
              f"=> ends at f={final_slot} with residues {crt_residues(final_slot, primes)}")
    print("    ...")
    # The point: the residue vector at f is FIXED (it's f's). It is the SAME for
    # all k. Reading it tells you f, not k. k is free to be anything in 1..T;
    # the birth position p_k just absorbs the difference (p_k = f - shifts mod Q).
    # (The pass-0 slot sigma^{-T}(f) is the same for all k; what differs is which
    #  pass the record was BORN on, and position at f cannot distinguish that.)
    distinct_residue_vectors = len({crt_residues(bwd_pow(final_slot, T - k, primes), primes)
                                    for k in range(1, T + 1)})
    same_residue_at_f = len({crt_residues(final_slot, primes)})
    print(f"\n  distinct residue vectors AT THE FINAL SLOT f over all k: {same_residue_at_f}")
    print("  -> position at f carries ZERO bits about birth pass k. (H1 FALSE)\n")


def demo_capacity():
    print("== (B) CAPACITY LEDGER: board bits vs birth-bit demand ==")
    print("  A fixed board of Q slots distinguishes exactly Q positions.")
    print("  The ONLY positional channel for N records is WHICH N of Q cells are")
    print("  occupied: log2 C(Q,N) bits -- and that is exactly the PCTB position")
    print("  list, which is STORED, not free (pctb_ledger.py). Even granting it")
    print("  for free, compare it to the birth demand N*log2(T):\n")
    from math import lgamma
    LN2 = 0.6931471805599453
    def log2C(n, k):
        if k <= 0 or k >= n:
            return 0.0
        return (lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)) / LN2
    print(f"  {'N':>6} {'T':>5} {'Q':>9} {'birth demand':>14} {'log2C(Q,N)':>12} {'slack':>10}")
    for (N, T, Q) in [(1000, 64, 1024), (1000, 64, 4096), (4096, 64, 4096),
                      (1000, 256, 1000), (1000, 64, 1_000_000)]:
        demand = N * log2(T)
        cfg = log2C(Q, N)
        print(f"  {N:>6} {T:>5} {Q:>9} {demand:>14.0f} {cfg:>12.0f} {cfg - demand:>10.0f}")
    print()
    print("  To make log2C(Q,N) >= N*log2(T) you must blow Q up massively, AND")
    print("  the occupancy list must then be transmitted (it is underivable for")
    print("  a content-dependent match pattern). That growing, transmitted")
    print("  position list IS PCTB: log2 C(Q_P, N_P), the 22x bloat at 64 passes.")
    print("  Conclusion: a FIXED board cannot hold the register; a board grown to")
    print("  hold it has rebuilt PCTB. (H2 FALSE)\n")


def demo_affine_same_verdict():
    print("== (C) DOES A NON-TRIVIAL AFFINE CLOCK ESCAPE? (a*s+b mod Q) ==")
    # The hope: maybe +1 is too trivial; a multiplier clock s -> a*s mod Q with
    # a of high multiplicative order makes the orbit phase informative.
    primes = [3, 5, 7, 11]
    Q = prod(primes)               # 1155
    a = 2
    assert gcd(a, Q) == 1
    print(f"  primes={primes} Q={Q}, clock s -> {a}*s mod Q (a coprime to Q).")
    # Still a deterministic public bijection. A record born at pass k, ending at
    # final slot f, started at x = a^{-(T-k)} * f mod Q. The decoder sees f.
    # The orbit phase of f is a property of f, identical for all k. The same
    # collision: enumerate k, get x; residues/orbit-position at f are f's, fixed.
    T = 32
    ainv = pow(a, -1, Q)
    f = 400
    starts = []
    for k in range(1, T + 1):
        shifts = T - k
        x = (pow(ainv, shifts, Q) * f) % Q
        starts.append((k, x))
    # what the decoder can read at f is ONLY f's properties:
    print(f"  final slot f={f}: residues {crt_residues(f, primes)} -- FIXED across all k.")
    print(f"  birth pass k can be ANY of 1..{T}; birth position p_k just absorbs it.")
    print(f"  (k=1 -> p_k={starts[0][1]},  k={T} -> p_k={starts[-1][1]}).  Position")
    print("  reveals f, never k. High-order multiplier changes the orbit but not")
    print("  the verdict: a public map carries 0 history bits. SAME WALL.\n")


if __name__ == "__main__":
    demo_collision()
    demo_capacity()
    demo_affine_same_verdict()
    print("VERDICT: CRT/residue clocks are public deterministic permutations.")
    print("Position at the final slot is a function of the slot, not of birth")
    print("pass. A fixed board holds log2(Q) bits total << N*log2(T) needed.")
    print("Growing the board to fit = PCTB (stored, growing position list).")
    print("Avenue C is a sharp impossibility, not a channel.")
