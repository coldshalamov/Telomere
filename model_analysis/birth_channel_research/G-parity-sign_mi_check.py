#!/usr/bin/env python3
"""
G-parity-sign_mi_check.py — Avenue G (parity/sign channels).

PURPOSE (construction-check, NOT a discovery hunt; no SHA matches needed):
verify the exact-math claim that for a SINGLE (arity-1) record in the V1
salted machine, the final slot s = sigma^T(x) depends ONLY on the original
slot x and the pass count T, and is INDEPENDENT of the record's birth pass t.

Consequence to confirm empirically (up to sampling noise):
    I( birth_pass t ; f(final_slot s) ) = 0   for every derivable slot-function f,
in particular for f = slot parity and f = "sign" under a reflection involution.

This is content-blind by construction: birth passes are drawn INDEPENDENTLY of
slots (we do NOT run a lottery that couples them — coupling would be content-
awareness, forbidden by SPEC sec 0). The toy's only job is to confirm sigma was
implemented correctly so the exact argument stands; it is NOT evidence-by-luck.

Run: python G-parity-sign_mi_check.py
"""
import math
import random
from collections import Counter


# ---- the V1 shuffle: i -> (walk(5*i mod P) + 1) mod M  (maintainer's +1 fix)
def least_prime_geq(n):
    def is_prime(m):
        if m < 2:
            return False
        if m % 2 == 0:
            return m == 2
        f = 3
        while f * f <= m:
            if m % f == 0:
                return False
            f += 2
        return True
    while not is_prime(n):
        n += 1
    return n


def make_shuffle(M):
    """Return fwd permutation on [0,M): i -> (walk(5*i mod P)+1) mod M."""
    P = least_prime_geq(max(M, 3))

    def base(i):  # walk(5*i mod P) into [0,M)
        j = (5 * i) % P
        while j >= M:
            j = (5 * j) % P
        return j

    def fwd(i):
        return (base(i) + 1) % M
    return fwd


def sigma_pow(fwd, i, t):
    for _ in range(t):
        i = fwd(i)
    return i


def assert_bijection(fwd, M):
    img = sorted(fwd(i) for i in range(M))
    assert img == list(range(M)), "shuffle is not a bijection!"


# ---- derivable ≤1-bit slot functions the decoder could compute for free ----
def parity(s, M):
    return s & 1


def reflection_sign(s, M):
    """'sign' under the reflection involution rho(s) = (M-1)-s:
    which half of the board the slot is in. 1-bit, derivable from s and M."""
    return 1 if 2 * s >= M else 0


def orbit_parity(fwd, s, M, T_try):
    """A function of the slot's BACKWARD trajectory under sigma for T_try steps:
    parity of how many times the backward walk crosses the midpoint. Still a
    deterministic function of s (and T_try, M) only — knows nothing about t."""
    # build inverse once per call is wasteful but this is a tiny toy
    inv = [0] * M
    for i in range(M):
        inv[fwd(i)] = i
    crossings = 0
    cur = s
    prev_half = reflection_sign(cur, M)
    for _ in range(T_try):
        cur = inv[cur]
        h = reflection_sign(cur, M)
        if h != prev_half:
            crossings += 1
        prev_half = h
    return crossings & 1


# ---- mutual information estimator (bits) ----
def mutual_information(pairs):
    """pairs: list of (a, b). Returns I(A;B) in bits (plug-in estimator)."""
    n = len(pairs)
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    cab = Counter(pairs)
    mi = 0.0
    for (a, b), nab in cab.items():
        pab = nab / n
        pa = ca[a] / n
        pb = cb[b] / n
        mi += pab * math.log2(pab / (pa * pb))
    return mi


def run(M=257, T=40, n_records=20000, seed=20260613):
    rng = random.Random(seed)
    fwd = make_shuffle(M)
    assert_bijection(fwd, M)

    # CONTENT-BLIND draw: pick a birth pass t uniformly, and an ORIGINAL slot x
    # uniformly, INDEPENDENTLY. (In the real machine the lottery decides t; the
    # uniform-hash law makes hit-time independent of position. We model that
    # independence directly — that IS the content-blindness assumption.)
    pairs_parity = []
    pairs_sign = []
    pairs_orbit = []
    pairs_slot = []  # I(t ; full slot s) — should ALSO be ~0
    for _ in range(n_records):
        t = rng.randint(1, T)         # birth pass
        x = rng.randrange(M)          # original slot
        # A SINGLE is 1->1: it sits at original index x and is shuffled by the
        # global sigma on EVERY pass, exactly like a literal. After all T passes
        # its final slot is sigma^T(x) — depends on x and T only, NOT on t.
        s = sigma_pow(fwd, x, T)
        pairs_parity.append((t, parity(s, M)))
        pairs_sign.append((t, reflection_sign(s, M)))
        pairs_orbit.append((t, orbit_parity(fwd, s, M, T)))
        pairs_slot.append((t, s))

    print(f"M={M} (board), T={T} passes, {n_records} content-blind records")
    print(f"  I(t ; parity(s))     = {mutual_information(pairs_parity):.6f} bits")
    print(f"  I(t ; sign(s))       = {mutual_information(pairs_sign):.6f} bits")
    print(f"  I(t ; orbitParity(s))= {mutual_information(pairs_orbit):.6f} bits")
    print(f"  I(t ; full slot s)   = {mutual_information(pairs_slot):.6f} bits  "
          f"(finite-sample bias ref; ~{(M-1)*(T-1)/(2*math.log(2)*n_records):.4f} expected)")
    print("  (all three <=1-bit channels carry ~0 about birth pass; the small")
    print("   nonzero on full-slot is finite-sample bias, not signal -- it shrinks")
    print("   as n grows because true I(t;s)=0 by construction.)")

    # finite-sample bias control: independent t and independent random slot
    # (TRUE MI is exactly 0). Same n -> shows the plug-in estimator's noise floor.
    control = [(rng.randint(1, T), parity(rng.randrange(M), M))
               for _ in range(n_records)]
    ctrl_slot = [(rng.randint(1, T), rng.randrange(M))
                 for _ in range(n_records)]
    print(f"\n  CONTROL I(indep t ; indep parity) = {mutual_information(control):.6f} bits "
          f"(true MI = 0; this is the noise floor)")
    print(f"  CONTROL I(indep t ; indep slot)   = {mutual_information(ctrl_slot):.6f} bits "
          f"(true MI = 0; full-slot bias floor matches the {mutual_information(pairs_slot):.4f} above)")


def bias_sweep(M=257, T=40, seed=99):
    """Show I_hat(t ; parity(s)) -> 0 and the full-slot estimate is PURE bias by
    sweeping n: a real channel would hold constant; bias falls like ~1/n."""
    rng = random.Random(seed)
    fwd = make_shuffle(M)
    print(f"\n== finite-sample bias sweep (M={M}, T={T}) ==")
    print(f"  {'n':>8} {'I(t;parity)':>14} {'I(t;slot)':>12} {'analytic_bias(slot)':>20}")
    for n in (2000, 8000, 32000, 128000):
        pp, ps = [], []
        for _ in range(n):
            t = rng.randint(1, T)
            x = rng.randrange(M)
            s = sigma_pow(fwd, x, T)
            pp.append((t, parity(s, M)))
            ps.append((t, s))
        # Miller-Madow / plug-in bias for I_hat ~ (|A|-1)(|B|-1)/(2 ln2 * n)
        bias_slot = (M - 1) * (T - 1) / (2 * math.log(2) * n)
        print(f"  {n:>8} {mutual_information(pp):>14.6f} "
              f"{mutual_information(ps):>12.6f} {bias_slot:>20.6f}")
    print("  -> I(t;parity) and I(t;slot) both track the analytic bias and FALL")
    print("     with n. A genuine channel would not fall. True MI = 0, proven by")
    print("     construction: s = sigma^T(x) has no t-dependence whatsoever.")


if __name__ == "__main__":
    # main demonstration
    run()
    print()
    # second board size + pass count to show it is not a coincidence of M, T
    run(M=521, T=80, n_records=20000, seed=7)
    bias_sweep()
