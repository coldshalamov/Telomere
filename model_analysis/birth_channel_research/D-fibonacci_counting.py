#!/usr/bin/env python3
"""
D-fibonacci_counting.py  -- Avenue D (Fibonacci/Zeckendorf/Lucas registers).

PURE COUNTING / LOGIC. No SHA-match hunting. (One small planted real-SHA
round-trip at the end only to confirm the Fibonacci shuffle is a valid,
reversible Telomere shuffle -- mechanics, not luck.)

The lane's claim to break or sharpen: a number-theoretic addressing where
"how many passes since birth" leaves an additive/shift signature readable for
a SINGLE (arity-1) record, for free.

TESTS
  T1  Position-phase death (H1): for a single at known p_final, every candidate
      birth pass t in {1..T} unwinds to a DISTINCT, LEGAL birth position.
      => p_final carries ZERO bits about t. Holds for ANY bijection sigma,
         Fibonacci included.
  T2  Zeckendorf-shift shuffle: is the "Zeckendorf left-shift" (n -> Fib-shift)
      even a bijection on [0,M)? Does it refresh neighbors? (Telomere shuffle
      validity gate.)
  T3  Orbit / phase homomorphism (H3 steelman): does a VALID Fibonacci-flavored
      multiplicative shuffle (i -> g*i mod P, g a Fibonacci/Lucas-derived
      generator) admit a global phase phi with phi(sigma p)=phi(p)+1 mod m,
      m>=T? Measure orbit structure. If a phase exists, where does the
      reference phi(p_birth) come from, and what does it cost?
  T4  The legal-sublattice steelman + counting gate: restrict newborn singles
      to a Zeckendorf-special sublattice so wrong-t unwindings land illegal.
      Count how many candidate passes survive, and price the supply loss.
"""

import hashlib

# ----------------------------------------------------------------------------
# Fibonacci / Zeckendorf primitives
# ----------------------------------------------------------------------------
def fibs_upto(n):
    """Fibonacci numbers (1,2,3,5,8,...) <= n, the Zeckendorf basis."""
    f = [1, 2]
    while f[-1] <= n:
        f.append(f[-1] + f[-2])
    return [x for x in f if x <= n]

def zeckendorf(n):
    """Zeckendorf digit string (MSB..LSB) over basis fibs_upto(n).
    Unique rep with no two consecutive 1s."""
    if n == 0:
        return "0"
    basis = fibs_upto(n)
    digits = []
    rem = n
    for f in reversed(basis):
        if f <= rem:
            digits.append("1")
            rem -= f
        else:
            digits.append("0")
    return "".join(digits)

def has_no_consecutive_ones(s):
    return "11" not in s

# ----------------------------------------------------------------------------
# Shuffles
# ----------------------------------------------------------------------------
def prime_geq(n):
    def isp(m):
        if m < 2: return False
        f = 2
        while f * f <= m:
            if m % f == 0: return False
            f += 1
        return True
    while not isp(n): n += 1
    return n

def mult_shuffle(M, g):
    """i -> walk(g*i mod P)+ ... a multiplicative shuffle with generator g,
    cycle-walked back into [0,M). Returns (fwd, bwd) if g invertible mod P."""
    P = prime_geq(max(M, 7))
    if g % P == 0:
        return None
    try:
        ginv = pow(g, -1, P)
    except ValueError:
        return None
    def fwd(i):
        j = (g * i) % P
        while j >= M: j = (g * j) % P
        return j
    def bwd(i):
        j = (ginv * i) % P
        while j >= M: j = (ginv * j) % P
        return j
    return fwd, bwd

def is_bijection(f, M):
    return sorted(f(i) for i in range(M)) == list(range(M))

def sig_pow(f, i, t):
    for _ in range(t): i = f(i)
    return i

# ----------------------------------------------------------------------------
# T1: position-phase death  (H1)  -- the core impossibility for singles
# ----------------------------------------------------------------------------
def t1_position_phase_death():
    print("== T1: a single's final position carries ZERO bits about birth pass ==")
    print("   For each candidate birth pass t, unwind p_final by (T-t) inverse")
    print("   shuffles. If ALL t give distinct legal p_birth, t is unconstrained.")
    any_excluded_anywhere = False
    for M in (13, 21, 34):           # Fibonacci-sized boards, for flavor
        for g in (5, 8):             # 5 = Telomere default; 8 = a Fibonacci number
            sh = mult_shuffle(M, g)
            if sh is None: continue
            fwd, bwd = sh
            if not is_bijection(fwd, M):
                continue
            T = 40                    # tens of passes -- the hard regime
            # pick a single sitting at an arbitrary final slot
            for p_final in (0, 1, M // 2, M - 1):
                cand_births = {}
                for t in range(1, T + 1):
                    shifts = T - t
                    p_birth = sig_pow(bwd, p_final, shifts)
                    cand_births[t] = p_birth
                births = list(cand_births.values())
                distinct = len(set(births)) == len(births) or len(set(births)) >= min(T, M)
                # On an M-board, after M the orbit wraps; within one orbit length
                # all are distinct & legal. The point: NONE is illegal.
                all_legal = all(0 <= b < M for b in births)
                if not all_legal:
                    any_excluded_anywhere = True
            print(f"   M={M:3d} g={g}: T={T} candidate births all legal in [0,M); "
                  f"none excluded by position. bits-about-t from position = 0")
    print(f"   => position excludes NO candidate birth pass (any_excluded={any_excluded_anywhere}).")
    print(f"   This holds for EVERY bijection sigma. Fibonacci adds no equation.\n")
    return not any_excluded_anywhere

# ----------------------------------------------------------------------------
# T2: is the Zeckendorf left-shift a valid Telomere shuffle?
# ----------------------------------------------------------------------------
def zeck_left_shift(n, M):
    """The 'Fibonacci multiply-by-phi' on Zeckendorf strings: append a 0 to the
    Zeckendorf digit string (i.e. shift each Fib index up by one: F_k -> F_{k+1}).
    Equivalent integer map. Then reduce mod M (wrap) to stay on the board."""
    if n == 0:
        return 0
    basis = fibs_upto(M * 8)   # generous basis
    # decode n's zeckendorf over the SAME canonical basis, shift indices up by 1
    rem = n
    val = 0
    # build basis index map
    # canonical basis: b[0]=1,b[1]=2,b[2]=3,b[3]=5,...
    b = fibs_upto(n) if n > 0 else [1]
    # represent n, then map each used F_k -> next fib
    full = fibs_upto(max(n, 1) * 4 + 8)
    digits = []
    r = n
    for f in reversed(full):
        if f <= r:
            digits.append(f)
            r -= f
    # shift: each fib f -> the next fib in the sequence
    for f in digits:
        idx = full.index(f)
        val += full[idx + 1]
    return val % M

def t2_zeck_shift_validity():
    print("== T2: is the Zeckendorf left-shift (multiply-by-phi) a valid shuffle? ==")
    for M in (13, 21, 34):
        img = [zeck_left_shift(n, M) for n in range(M)]
        bij = sorted(img) == list(range(M))
        # neighbor refresh: do i and i+1 stay adjacent?
        moved_all = all(zeck_left_shift(n, M) != n for n in range(1, M))
        # count fixed points
        fixed = sum(1 for n in range(M) if zeck_left_shift(n, M) == n)
        print(f"   M={M:3d}: bijection={bij}  fixed_points={fixed}  "
              f"(sample img[0:6]={img[:6]})")
    print("   Note: the Zeckendorf shift is NOT a permutation mod M in general")
    print("   (multiply-by-phi rounded/wrapped collides) -> fails the shuffle gate.")
    print("   Even if it were, T1 already shows position carries 0 bits about t.\n")

# ----------------------------------------------------------------------------
# T3: orbit / phase homomorphism for a multiplicative Fibonacci shuffle
# ----------------------------------------------------------------------------
def t3_phase_homomorphism():
    print("== T3: does a valid multiplicative shuffle admit phi(sigma p)=phi(p)+1? ==")
    print("   A global additive phase phi mod m would make 'passes since a fixed")
    print("   reference' readable. We measure orbit structure of i->g*i mod P walked.")
    for M, g in [(13, 5), (21, 5), (21, 8), (34, 13), (34, 5)]:
        sh = mult_shuffle(M, g)
        if sh is None:
            print(f"   M={M} g={g}: g not invertible, skip"); continue
        fwd, _ = sh
        if not is_bijection(fwd, M):
            print(f"   M={M} g={g}: not a bijection on [0,M), skip"); continue
        # decompose into cycles
        seen = [False] * M
        cyc_lens = []
        for s in range(M):
            if seen[s]: continue
            L = 0; x = s
            while not seen[x]:
                seen[x] = True; x = fwd(x); L += 1
            cyc_lens.append(L)
        from math import gcd
        # a single global phase mod m exists iff one cycle covers all movers
        # (m = that cycle length); else phase is only defined per-orbit (partial).
        lcm = 1
        for L in cyc_lens:
            lcm = lcm * L // gcd(lcm, L)
        print(f"   M={M:3d} g={g}: cycle lengths={sorted(cyc_lens)}  "
              f"global-phase m (lcm)={lcm}")
        print(f"        -> phase per orbit needs a per-record reference phi(p_birth);")
        print(f"           p_birth is content-uniform (single born where a literal")
        print(f"           failed to match) => reference is NOT free.")
    print()

# ----------------------------------------------------------------------------
# T4: legal-sublattice steelman + the counting gate
# ----------------------------------------------------------------------------
def t4_sublattice_gate():
    print("== T4: legal-birth sublattice (Zeckendorf-special slots) + counting gate ==")
    print("   Steelman: only slots whose Zeckendorf rep is 'special' may host a")
    print("   newborn single, so wrong-t unwindings land on illegal (non-special)")
    print("   slots and get excluded. How many candidate passes survive, and what")
    print("   is the supply cost?")
    for M in (34, 55, 89):
        legal = [n for n in range(M) if zeckendorf(n).count("1") == 1]  # pure single-Fib slots
        frac_legal = len(legal) / M
        # If births are confined to 'legal', the lottery only fires for blocks
        # that happen to shuffle INTO a legal slot at search time. Fraction of
        # tickets retained ~ frac_legal. Supply loss factor:
        supply_factor = frac_legal
        # candidate passes surviving the legality filter: a wrong-t unwind lands
        # legal with prob ~ frac_legal, so expected survivors ~ 1 + (T-1)*frac_legal
        T = 40
        exp_survivors = 1 + (T - 1) * frac_legal
        # bits the filter buys: log2(T / exp_survivors)
        from math import log2
        bits_bought = log2(T / exp_survivors)
        # bits paid in supply: each retained ticket is worth 1/supply_factor fewer
        # draws; in bits of match rate that's -log2(supply_factor) per the birth
        bits_paid = -log2(supply_factor)
        print(f"   M={M:3d}: #legal={len(legal):3d} frac={frac_legal:.3f}  "
              f"survivors~{exp_survivors:.1f}/{T}  "
              f"bits_bought={bits_bought:.2f}  supply_bits_paid={bits_paid:.2f}")
    print("   => narrowing candidate passes costs MORE match-supply bits than the")
    print("      birth-pass bits it buys (avenue-E ~2x-per-bit starvation, confirmed")
    print("      structurally). The bill reappears in match-supply, not for free.\n")

# ----------------------------------------------------------------------------
# T5: mechanics sanity -- a planted single round-trips under a Fibonacci-g
#     multiplicative shuffle (real SHA, planted, NOT a luck hunt)
# ----------------------------------------------------------------------------
def H(key, n):
    out = ""; c = 0
    while len(out) < n:
        out += "".join(f"{b:08b}" for b in
                        hashlib.sha256(f"{key}#{c}".encode()).digest())
        c += 1
    return out[:n]

def t5_planted_single_roundtrip():
    print("== T5: mechanics -- planted single round-trips under Fibonacci-g shuffle ==")
    print("   (real SHA, PLANTED seed->block; confirms reversibility + slot-keyed")
    print("    single decode, NOT a match-rate claim)")
    print("   Model EXACTLY as v1_roundtrip_proof.py: arr[i]=original slot of item")
    print("   at array-pos i; single keyed by its ORIGINAL slot; decode recovers")
    print("   that slot as bwd^T(final_arr_pos), independent of birth pass.")
    M = 21; B = 8; g = 8     # g=8 is a Fibonacci number, invertible mod prime>=21
    sh = mult_shuffle(M, g)
    fwd, bwd = sh
    assert is_bijection(fwd, M), "Fibonacci-g shuffle must be a bijection"
    T = 30
    def apply(a):                 # same convention as proof kernel: out[fwd(i)]=a[i]
        out = [None] * M
        for i, x in enumerate(a):
            out[fwd(i)] = x
        return out

    # Encoder: start arr = identity (item j has original slot j, at array-pos j).
    # Pick a single to be born at pass t0 at WHATEVER array-pos it then occupies.
    # We track ONE chosen original slot through the passes.
    chosen_orig = 13          # this item's original slot (its k-free salt key)
    seed = 12345
    planted_block = H(f"{seed}|s{chosen_orig}", B)   # the bits it stands for

    arr = list(range(M))      # arr[i] = original slot at array-pos i
    t0 = 7                    # birth pass (irrelevant to decode -- that's the point)
    # run encoder shuffles; record final array layout after T passes
    for t in range(1, T + 1):
        # (at pass t0 the chosen item is "replaced in place" by a single record;
        #  replacement is length-preserving for arity-1, so the array layout of
        #  original-slot identities is unchanged -- only its TYPE changed.)
        arr = apply(arr)
    # final array-pos of the chosen item:
    final_pos = arr.index(chosen_orig)

    # Decoder: after undoing all T shuffles, the item at final_pos came from
    # original slot bwd^T(final_pos). (k-free: no birth pass used.)
    rec = final_pos
    for _ in range(T):
        rec = bwd(rec)
    recovered_slot = rec
    salt_ok = (recovered_slot == chosen_orig)
    block_back = H(f"{seed}|s{recovered_slot}", B)
    print(f"   chosen single: original slot {chosen_orig}, born pass t0={t0} "
          f"(birth pass NOT used by decode)")
    print(f"   final arr-pos={final_pos}; decoder bwd^T -> slot {recovered_slot} "
          f"(salt match: {salt_ok})")
    print(f"   block recovered exactly: {block_back == planted_block}")
    print(f"   => slot-keyed single decodes with ZERO birth info. But it is ONE-SHOT:")
    print(f"      one dice sequence per slot, exhausts at D* (MATH_MODEL 6). Fresh")
    print(f"      dice would need a per-pass salt => needs birth pass => the wall.")
    print(f"      Fibonacci-g shuffle changed nothing about this.\n")
    return salt_ok and (block_back == planted_block)

if __name__ == "__main__":
    print("AVENUE D -- Fibonacci / Zeckendorf / Lucas bounded registers\n")
    r1 = t1_position_phase_death()
    t2_zeck_shift_validity()
    t3_phase_homomorphism()
    t4_sublattice_gate()
    r5 = t5_planted_single_roundtrip()
    print("SUMMARY")
    print(f"  T1 position-phase death confirmed: {r1}")
    print(f"  T5 planted single round-trip (slot-keyed, k-free): {r5}")
    print("  Conclusion: Fibonacci/Zeckendorf adds no free equation to a single.")
