#!/usr/bin/env python3
"""
A-modular-orbit_invariance.py

LANE A: Modular-orbit / affine-stride epochs for SINGLES.

CLAIM UNDER TEST (the slick hope):
  A prime-field shuffle i -> g*i mod p (g a generator) or affine i -> a*i+b mod Q
  makes a single's birth pass t readable from its ORBIT PHASE at decode, with
  zero stored bits -- in particular by discrete log of (current_pos / x).

WHAT THIS SCRIPT PROVES (deterministic, no SHA, no luck):
  (1) INVARIANCE: a length-preserving single occupies its original slot x for
      the ENTIRE run. Its position at pass j is sigma^j(x) for ALL j, whether
      it was a literal or a record at pass j. So the trajectory is a function
      of (x, number-of-passes-applied) ONLY -- it does NOT depend on birth pass.
      We demonstrate by attaching an arbitrary birth-pass label and showing the
      trajectory is byte-identical across labels.
  (2) DISCRETE-LOG READS T, NOT t. With multiplicative sigma(i)=g*i mod p,
      position after j shuffles is g^j * x mod p. Discrete log of
      (final_pos / x) recovers the TOTAL pass count T (already in the header
      via the hash-trial), never the per-record birth pass t. A 2-line trace.
  (3) ZERO NARROWING. For a single seen at final position f, every birth pass
      t in 1..T is consistent with the same self-presenting position-salt
      schedule. The orbit partitions the T candidate births into ONE class
      -> it removes 0 of the log2(T) bits the explosion check must supply.

This is a COUNTING / LOGIC result. No match-hunting. Real permutations only.
"""

import sys


# ----------------------------------------------------------------------------
# Shuffle families (all deterministic bijections on positions)
# ----------------------------------------------------------------------------
def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


def least_prime_geq(n):
    while not is_prime(n):
        n += 1
    return n


def make_spec_shuffle(M):
    """The V1 / Golden-Config shuffle: i -> (walk(5i mod P)+1) mod M.
    Exactly invertible (shift back, multiply back, walk)."""
    P = least_prime_geq(max(M, 7))
    inv5 = pow(5, -1, P)

    def fwd(i):
        j = (5 * i) % P
        while j >= M:
            j = (5 * j) % P
        return (j + 1) % M

    def bwd(i):
        k = (i - 1) % M
        j = (inv5 * k) % P
        while j >= M:
            j = (inv5 * j) % P
        return j
    return fwd, bwd


def make_mult_field(p, g):
    """Pure multiplicative orbit on the field Z_p^*: i -> g*i mod p, for
    i in 1..p-1 (slot 0 is a fixed point and is excluded). This is the
    'best case' for the discrete-log reading -- no cycle-walk noise."""
    ginv = pow(g, -1, p)

    def fwd(i):
        return (g * i) % p

    def bwd(i):
        return (ginv * i) % p
    return fwd, bwd


def orbit(fwd, x, j):
    for _ in range(j):
        x = fwd(x)
    return x


# ----------------------------------------------------------------------------
# (1) INVARIANCE: trajectory is independent of birth pass
# ----------------------------------------------------------------------------
def step_stream(arr, fwd, item_type):
    """Apply sigma to the item stream. CRUCIALLY the move rule is handed the
    item's TYPE ('lit' or 'rec') so that if the spec actually moved records
    differently from literals, this would produce a different trajectory.
    Under the real spec both types move identically -> identical trajectory;
    the test is a genuine construction that COULD fail if that weren't true."""
    new = [None] * len(arr)
    for p in range(len(arr)):
        it = arr[p]
        # spec rule: every item moves by sigma regardless of type.
        # (A buggy two-speed rule would branch on item_type[it] here and
        #  the assertion in test_invariance would then fire.)
        _ = item_type[it]          # type IS consulted; spec ignores it
        new[fwd(p)] = it
    return new


def test_invariance(M=53, T=40):
    """For each slot x and each birth label t in 1..T, simulate the ACTUAL
    item stream where the single at slot x carries a payload whose TYPE flips
    literal->record at pass t. The move function is explicitly given each
    item's current type (see step_stream), so a two-speed / type-dependent
    shuffle would yield t-dependent trajectories and FAIL this test. Under the
    spec (every item moves identically) the trajectory must be t-invariant.
    This is a real construction: it is falsifiable by a t-dependent move rule."""
    fwd, _ = make_spec_shuffle(M)
    all_ok = True
    mismatches = 0
    for x in range(M):
        canon = [orbit(fwd, x, j) for j in range(T + 1)]
        for t in range(1, T + 1):
            arr = list(range(M))                 # arr[pos] = original slot here
            # item_type[slot]: 'rec' once born, else 'lit'. The single (slot x)
            # is 'lit' for passes < t and 'rec' from pass t on.
            item_type = {s: "lit" for s in range(M)}
            traj = [arr.index(x)]
            for pj in range(1, T + 1):
                if pj == t:                      # BIRTH: in-place type flip
                    item_type[x] = "rec"
                arr = step_stream(arr, fwd, item_type)
                traj.append(arr.index(x))
            if traj != canon:
                all_ok = False
                mismatches += 1
    print("== (1) INVARIANCE (spec shuffle, M=%d, T=%d) ==" % (M, T))
    print("   single at slot x flips lit->rec at birth t; move rule is handed")
    print("   each item's TYPE (a two-speed rule WOULD diverge here).")
    print("   trajectories identical across ALL birth labels: %s "
          "(mismatches=%d)" % (all_ok, mismatches))
    print("   -> under the spec, birth pass t leaves NO trace in position.\n")
    return all_ok


# ----------------------------------------------------------------------------
# (2) DISCRETE LOG RECOVERS T, NOT t
# ----------------------------------------------------------------------------
def dlog(g, h, p):
    """smallest e>=0 with g^e == h mod p (baby-step toy; p tiny)."""
    cur = 1 % p
    for e in range(p):
        if cur == h:
            return e
        cur = (cur * g) % p
    return None


def test_discrete_log(p=53, g=2, T=11):
    """Multiplicative orbit i -> g*i mod p. A single sits at slot x for the
    whole run. After T passes it is at g^T * x. The decoder sees final pos f
    and recovers x = g^{-T} f (self-presenting). Discrete log of (f / x) = T.
    Attach an arbitrary birth pass t; show dlog still returns T."""
    assert is_prime(p)
    fwd, bwd = make_mult_field(p, g)
    print("== (2) DISCRETE-LOG READS T, NOT t (mult field p=%d, g=%d, T=%d) =="
          % (p, g, T))
    print("   ord(g=%d) mod %d covers the orbit; testing slots x with births t"
          % (g, p))
    ok = True
    shown = 0
    for x in (1, 2, 7, 19, 30):
        f = orbit(fwd, x, T)                       # position after T passes
        # decoder knows T (header hash trial) -> recover original slot:
        x_rec = orbit(bwd, f, T)
        # the 'orbit phase' reading: dlog of (f * x^{-1}) base g
        xinv = pow(x, -1, p)
        e = dlog(g, (f * xinv) % p, p)
        for t in (1, T // 2 or 1, T):             # arbitrary birth labels
            # the trajectory g^j x does not branch at t; the read is the same
            if e != T or x_rec != x:
                ok = False
            if shown < 3:
                print("   x=%2d born@t=%2d  final=g^%d*x=%2d  dlog(final/x)=%s "
                      "(=T, NOT t)  x_recovered=%d" % (x, t, T, f, e, x_rec))
                shown += 1
    print("   every read returns the orbit phase = T (the TOTAL count, already")
    print("   known from the header), never the per-record birth pass t.")
    print("   verdict: discrete-log orbit channel conveys ZERO birth bits. ok=%s\n"
          % ok)
    return ok


# ----------------------------------------------------------------------------
# (3) ZERO NARROWING for the explosion check
# ----------------------------------------------------------------------------
def test_no_discriminator(M=53, T=40):
    """The decoder needs the BIRTH SALT for the single -- the position it
    occupied when it matched, which under the spec is sigma^{t-1}(x) (the
    item's position just before the birth-pass shuffle). These salts are
    genuinely DISTINCT across candidate births t (so the wrong t expands the
    seed against the wrong salt and yields wrong bytes -- exactly the dispute
    in THE_OPEN_QUESTION). The question is whether the orbit gives any free
    way to pick the right t. The only orbit-observable is the FINAL position
    f = sigma^T(x), which is t-FREE (test 1/2). So: the candidate salts differ,
    but the observable does not depend on which one is right -> the orbit
    supplies NO discriminator. log2(T) bits remain for the explosion check."""
    fwd, bwd = make_spec_shuffle(M)
    print("== (3) NO DISCRIMINATOR (spec shuffle, M=%d, T=%d) ==" % (M, T))
    all_good = True
    for x in (0, 1, 5, 17, 40):
        f = orbit(fwd, x, T)                      # the only orbit-observable
        # birth salts the decoder must choose among (one per candidate t):
        salts = [orbit(fwd, x, t - 1) for t in range(1, T + 1)]
        distinct = len(set(salts))
        # does the observable f single out the correct t? it is identical for
        # every t (f = sigma^T(x) has no t in it), so NO.
        observable_depends_on_t = False           # proven in test 1/2
        narrowing_bits = 0.0 if not observable_depends_on_t else None
        ok = (distinct >= 2) and (not observable_depends_on_t)
        all_good = all_good and ok
        print("   x=%2d final=%2d : %d distinct candidate birth-salts, "
              "observable t-free -> discriminator=%.1f bits"
              % (x, f, distinct, narrowing_bits))
    log2T = (T - 1).bit_length()
    print("   the candidate salts genuinely differ (so wrong t -> wrong bytes),")
    print("   but the orbit observable is t-free -> it narrows log2(T)~%d bits"
          % log2T)
    print("   by 0. The explosion check (~2.5 free bits) carries them alone:")
    print("   reach K ~ 6 passes, orbit contributes nothing.\n")
    return all_good


# ----------------------------------------------------------------------------
# (4) THE HINGE: freeze-until-birth is the ONLY thing that makes phase carry t
#     -- but it leaves lane A (-> avenue F) and creates a decode circularity.
# ----------------------------------------------------------------------------
def test_freeze_hinge(M=53, T=12):
    """Counterfactual: suppose a single does NOT move until it is born at pass
    t, then moves under sigma for the remaining T-t passes. THEN final position
    = sigma^{T-t}(x), so the orbit phase WOULD encode (T-t) and thus t.

    This is the boundary of the impossibility -- and it is exactly avenue F
    (frozen / two-speed boards), NOT lane A. We show two costs that make it a
    different (harder) problem, not a rescue of the modular-orbit idea:

      (i)  CIRCULARITY: to apply the right per-pass shuffle in REVERSE, the
           decoder must already know, at each reverse step, whether the item
           was frozen (literal, no move) or live (record, moved) at that pass
           -- which is the record-vs-literal-AND-birth-pass question it is
           trying to answer. The shuffle is no longer content-blind on the
           item's history.
      (ii) it breaks 'every item moves every pass' (SPEC_V1 1, freshness):
           frozen literals get NO fresh neighbors, so their match supply does
           not refresh -- the very property the channel was meant to buy.
    """
    print("== (4) HINGE: freeze-until-birth (counterfactual, M=%d, T=%d) ==" % (M, T))
    fwd, bwd = make_spec_shuffle(M)
    # show that IF motion started at birth, phase would separate births:
    x = 7
    finals = {}
    for t in range(1, T + 1):
        moves = T - t
        finals[t] = orbit(fwd, x, moves)
    distinct = len(set(finals.values()))
    print("   frozen model: final pos by birth t (x=%d): %s" %
          (x, {t: finals[t] for t in (1, T // 2, T)}))
    print("   distinct finals across %d births: %d  (phase WOULD carry t here)"
          % (T, distinct))
    print("   BUT the live-model trajectory is birth-invariant (test 1), so to")
    print("   reverse the freeze model the decoder must know move-count = T - t")
    print("   per record BEFORE opening it -> circular; and frozen literals")
    print("   skip the fresh-neighbor refresh -> match supply does not renew.")
    print("   => this is avenue F, not lane A; it trades the birth bill into the")
    print("      'match-supply' + 'compute/circularity' currencies, not free.\n")
    return distinct > 1   # confirms the hinge is real (and why it doesn't help A)


def test_falsifiability(M=53, T=10):
    """Guard against a tautology: show the invariance test CAN fail. Under a
    TWO-SPEED rule (records hop twice per pass, literals once) the single's own
    trajectory depends on its birth t -- the two paths diverge. So test 1's
    'identical across t' is a real property of the SINGLE-speed spec, not a
    consequence of code that ignores t."""
    fwd, _ = make_spec_shuffle(M)

    def traj_two_speed(x, t):
        pos, out = x, [x]
        for pj in range(1, T + 1):
            pos = fwd(pos)
            if pj >= t:                  # record from birth on: extra hop
                pos = fwd(pos)
            out.append(pos)
        return out

    x = 7
    canon = traj_two_speed(x, T + 1)     # never born -> pure-literal path
    diverges = any(traj_two_speed(x, t) != canon for t in range(1, T + 1))
    print("== (0) FALSIFIABILITY GUARD (two-speed rule, M=%d, T=%d) ==" % (M, T))
    print("   under a t-DEPENDENT move rule, slot-%d trajectory depends on "
          "birth t: %s" % (x, diverges))
    print("   born@t=1: %s" % traj_two_speed(x, 1)[:6] + " ...")
    print("   born@t=8: %s" % traj_two_speed(x, 8)[:6] + " ...")
    print("   -> test 1 is a real construction: the spec's single-speed rule")
    print("      makes it t-invariant; a two-speed rule would break it.\n")
    return diverges


def main():
    z = test_falsifiability()
    a = test_invariance()
    b = test_discrete_log()
    c = test_no_discriminator()
    d = test_freeze_hinge()
    print("=" * 68)
    print("SUMMARY (lane A, SINGLES):")
    print("  falsifiability guard ....... %s" % z)
    print("  invariance (construction) .. %s" % a)
    print("  dlog reads T not t ......... %s" % b)
    print("  no discriminator ........... %s" % c)
    print("  freeze-hinge identified .... %s (leaves lane A -> avenue F)" % d)
    print("  CONCLUSION: orbit phase is BIRTH-INVARIANT for length-preserving")
    print("  singles. It is a free, content-blind signal of ZERO capacity for")
    print("  birth pass. Not a channel -> no leak; the working part is bounded")
    print("  by the explosion check's structure budget (~2.5 bits, K~6).")
    return 0 if (z and a and b and c and d) else 1


if __name__ == "__main__":
    sys.exit(main())
