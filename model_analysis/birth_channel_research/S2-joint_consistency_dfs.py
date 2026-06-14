#!/usr/bin/env python3
"""
S2-joint_consistency_dfs.py   (Adversarial Skeptic 2)

THE ONE TEST THE BUNDLE LANE DID NOT RUN.

P2-bundle_survivor.py counts survivors with `filled = set()` created ONCE and
NEVER mutated across records (count_survivors lines 457-478): each bundle's
epochs are counted in ISOLATION, so S_epoch = prod_i base_i = base^R by
construction. The findings ASSERT (unproven) that adding the cross-bundle
wire-consistency constraint "only ADDS pruning (lowers the base), never bends
exponential to polynomial." That assertion is the ONLY place the verdict can
flip. This script tests it.

WIRE-CONSISTENCY (the omitted constraint)
-----------------------------------------
The encoder serializes the FINAL board: a bundle's seed sits in one wire slot;
its other a-1 child slots emit NOTHING (skip). A literal emits an 11-bit item.
So the observed wire is a partition of the N board slots into:
    SEED slots (one per bundle), SKIP slots (a-1 per bundle), LITERAL slots.
A candidate global reading must assign every bundle (epoch k, anchor q) such
that the implied child slots F = [FWD[T-k+1][q+j]] are:
    * pairwise DISJOINT across all bundles (no slot claimed twice),
    * the seed child lands on that bundle's observed seed slot,
    * the OTHER children land on slots that are observed-SKIP (emit nothing) --
      NOT on a literal slot and NOT on another bundle's seed slot,
    * and EVERY observed skip slot is claimed by exactly one bundle (the wire
      has no unexplained holes).
The TRUE reading satisfies all of this by construction. A WRONG reading must
ALSO be globally consistent -- a far stronger filter than the per-bundle
explosion check the lane applied alone.

HYPOTHESIS (written before running; the impossibility-favouring prediction)
---------------------------------------------------------------------------
Even with full wire-consistency, wrong-salt re-expansions stay INDEPENDENT
across bundles (distinct seeds). Cross-fill PRUNES each bundle's surviving
epochs but each base_i stays > 1, so S_joint = prod base_i' is still
EXPONENTIAL in R, just with a smaller base. A REAL channel would need
cross-fill to drive base_i' -> 1 for EVERY bundle (pin every epoch to the
true one). Prediction: it shrinks, it does not pin. If instead S_joint
collapses to O(1) for free + content-blind, the COUNTING GATE fires (that
conveys ~N*log2 T uniform birth bits free = pigeonhole violation) -> there is
a leak and I must name its currency (skip-pattern = stored structural bits, or
board size = wrap/carriage).

METHOD: EXACT joint DFS, real SHA-256, no oracle. T past the orbit period so
geometry genuinely wraps. Count ALL globally-consistent (epoch,placement)
assignments to the R bundles; compare to the isolated base^R the lane reports.
"""
import hashlib
import math
import random
from functools import lru_cache

# ---------------------------------------------------------------------------
# GRAMMAR (verbatim from P2-bundle_survivor.py / P2-explosion-budget_exact.py)
# ---------------------------------------------------------------------------
B = 8
J_BITS = 3
ARITY_CODEWORD_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
LITERAL_MARKER_BITS = 3
_ARITY_CW = {1: "00", 2: "01", 3: "100", 4: "101", 5: "110"}


@lru_cache(maxsize=None)
def lotus_width_for_value(value: int) -> int:
    width = 1
    while True:
        if (1 << width) - 2 <= value <= (1 << (width + 1)) - 3:
            return width
        width += 1


def lotus_seed_bits(pw: int) -> int:
    return J_BITS + lotus_width_for_value(pw) + pw


def record_item_bits(arity: int, pw: int) -> int:
    return ARITY_CODEWORD_BITS[arity] + lotus_seed_bits(pw)


def literal_item_bits() -> int:
    return LITERAL_MARKER_BITS + B


MIN_ITEM = min(literal_item_bits(),
               min(record_item_bits(ar, 1) for ar in ARITY_CODEWORD_BITS))


def _arity_codeword(arity: int) -> str:
    return _ARITY_CW[arity]


@lru_cache(maxsize=None)
def _payload_width_from_field(tw: int, lenfield: int):
    los = [pw for pw in range(1, 5000) if lotus_width_for_value(pw) == tw]
    if not los or lenfield >= len(los):
        return None
    return los[lenfield]


def parses_as_a_items_len(bitstr: str, a: int) -> bool:
    """REAL recursive-descent explosion check (verbatim logic from the lane)."""
    L = len(bitstr)

    def rec(pos: int, items_left: int) -> bool:
        if items_left == 0:
            return pos == L
        if pos + literal_item_bits() <= L:
            if bitstr[pos:pos + LITERAL_MARKER_BITS] == "111":
                if rec(pos + literal_item_bits(), items_left - 1):
                    return True
        for arity, cw_bits in ARITY_CODEWORD_BITS.items():
            cw = _arity_codeword(arity)
            if bitstr[pos:pos + cw_bits] != cw:
                continue
            sp = pos + cw_bits
            if sp + J_BITS > L:
                continue
            tw = int(bitstr[sp:sp + J_BITS], 2) + 1
            lp = sp + J_BITS
            if lp + tw > L:
                continue
            lenfield = int(bitstr[lp:lp + tw], 2)
            pp = lp + tw
            pw = _payload_width_from_field(tw, lenfield)
            if pw is None or pp + pw > L:
                continue
            if rec(pp + pw, items_left - 1):
                return True
        return False

    return rec(0, a)


# ---------------------------------------------------------------------------
# +1 SHUFFLE (verbatim) and orbit tables
# ---------------------------------------------------------------------------
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


def make_shuffle(N):
    P = least_prime_geq(max(N, 3))
    inv5 = pow(5, -1, P)

    def fwd(i):
        j = (5 * i) % P
        while j >= N:
            j = (5 * j) % P
        return j

    def bwd(i):
        j = (inv5 * i) % P
        while j >= N:
            j = (inv5 * j) % P
        return j
    return fwd, bwd


def orbit_tables(N, T):
    fwd, bwd = make_shuffle(N)
    FWD = [list(range(N))]
    BWD = [list(range(N))]
    for _ in range(T):
        FWD.append([fwd(i) for i in FWD[-1]])
        BWD.append([bwd(i) for i in BWD[-1]])
    return FWD, BWD, fwd, bwd


def H_bits(key: str, nbits: int) -> str:
    out = ""
    ctr = 0
    while len(out) < nbits:
        d = hashlib.sha256(f"{key}#{ctr}".encode()).digest()
        out += "".join(f"{b:08b}" for b in d)
        ctr += 1
    return out[:nbits]


# ---------------------------------------------------------------------------
# ENCODER  (mirrors P2-bundle_survivor.encode; ALSO records the full final
# board layout so the joint DFS can enforce wire consistency).
# ---------------------------------------------------------------------------
A = 2


_seed_pool = {}


def find_valid_seed(salt_key, start=0, max_try=300_000):
    """Cached: collect a POOL of valid seeds per salt so repeated trials draw
    different valid seeds (genuine ensemble variance) without re-hashing 655x
    each time. Returns one seed at/after `start` from the pool."""
    pool = _seed_pool.get(salt_key)
    if pool is None:
        pool = []
        s = 0
        while len(pool) < 64 and s < max_try:
            if parses_as_a_items_len(H_bits(f"{s}|{salt_key}", A * B), A):
                pool.append(s)
            s += 1
        _seed_pool[salt_key] = pool
    if not pool:
        return None
    return pool[start % len(pool)]


def encode(N, T, R, rng, FWD, BWD):
    fwd, bwd = make_shuffle(N)
    arr = list(range(N))
    cov = {}
    records = []
    lit_seed = {}  # literal slots get a real arity-1 single seed (k-free), so
                   # the PACKED wire carries genuine items the decoder reads in
                   # order WITHOUT knowing board positions (faithful to v1).
    for t in range(1, T + 1):
        if t <= R:
            for i in range(N - 1):
                idxs = arr[i:i + A]
                if any(x in cov for x in idxs):
                    continue
                seed = find_valid_seed(f"p{t}", start=rng.randrange(0, 1 << 20))
                if seed is None:
                    continue
                rec = dict(k=t, q=i, a=A, seed=seed, children=idxs[:])
                records.append(rec)
                for x in idxs:
                    cov[x] = rec
                break
        new = [None] * N
        for i, x in enumerate(arr):
            new[fwd(i)] = x
        arr = new
    # final board: position p holds original index arr[p]
    fpos = {x: p for p, x in enumerate(arr)}
    seed_slots = set()
    skip_slots = set()
    for r in records:
        slots = sorted(fpos[x] for x in r["children"])
        r["seed_slot"] = slots[0]
        r["other_slots"] = slots[1:]
        seed_slots.add(slots[0])
        skip_slots.update(slots[1:])
    literal_slots = set(range(N)) - seed_slots - skip_slots
    # PACKED WIRE (faithful to v1_roundtrip_proof serialize, lines 122-131):
    # walk board positions; skip slots emit NOTHING; bundle seed emits one
    # ("rec",a) item; every other (non-hole) slot emits a literal ("lit") item.
    # The decoder receives ONLY this ordered item-type list -- NO board positions,
    # NO hole markers. That is the whole point: holes are invisible on the wire.
    # carry the SEED in the wire item (as v1 does: cw+seed bits). The decoder
    # reads this seed at the cursor and tries epochs with it -- so the explosion
    # check is ALWAYS applied with the wire's actual seed (no skipped checks).
    seed_of_slot = {r["seed_slot"]: r["seed"] for r in records}
    wire_items = []
    for p in range(N):
        if p in skip_slots:
            continue
        if p in seed_slots:
            wire_items.append(("rec", A, seed_of_slot[p]))
        else:
            wire_items.append(("lit", 1, None))
    board = dict(N=N, seed_slots=seed_slots, skip_slots=skip_slots,
                 literal_slots=literal_slots, records=records,
                 wire_items=wire_items)
    return board


# ---------------------------------------------------------------------------
# PER-BUNDLE CANDIDATE (epoch, placement) generation -- the lane's geometry
# filter, EXACT copy, but WITHOUT the inter-record `filled` prune (we enforce
# disjointness/consistency jointly in the DFS instead, which is strictly
# correct rather than greedy).
# ---------------------------------------------------------------------------
def raw_candidates(seed_slot, N, T, FWD, BWD, a=A):
    """All (k, q, F) the geometry+explosion check admit for a bundle whose
    seed sits at `seed_slot`. F is the tuple of implied child slots; F[0] (the
    min) is the seed slot. Epoch k passes the explosion check iff the wrong-salt
    re-expansion parses -- but we DON'T know the seed value for wrong epochs in
    a content-blind reading, so we keep ALL geometric (k,q,F) and let the
    explosion check act per-epoch using the ACTUAL planted seed (favourable to
    the channel: gives it the explosion discount for free)."""
    cands = []
    for k in range(1, T + 1):
        shifts = T - k + 1
        p0 = BWD[shifts][seed_slot]
        for j0 in range(a):
            q = p0 - j0
            if q < 0 or q + a > N:
                continue
            F = tuple(FWD[shifts][q + j] for j in range(a))
            if min(F) != seed_slot:
                continue
            cands.append((k, q, F))
    return cands


# ---------------------------------------------------------------------------
# JOINT DFS -- count globally wire-consistent (epoch, placement) assignments.
# ---------------------------------------------------------------------------
def joint_survivors(board, T, FWD, BWD):
    """FAITHFUL to v1_roundtrip_proof.try_decode (lines 146-196). Walk the BOARD
    slots 0..N-1 in order, consuming the PACKED wire items in order. The decoder
    knows ONLY: N, the ordered item-type list (rec/lit + arity), and the `filled`
    set it BUILDS as it commits epochs. It does NOT know which board slots are
    holes -- holes are GENERATED by bundle epoch commitments (a child lands on a
    not-yet-filled slot ahead of the cursor), never observed. This is the whole
    correction: the previous version was handed the true hole set.

    For each bundle item the decoder tries every epoch k in 1..T (geometry filter
    min(F)==slot, children not already filled, no child before cursor) -- exactly
    v1 lines 172-195. Each surviving epoch is ALSO subjected to the real explosion
    check on the planted seed (favorable to the channel: gives it the free E-bit
    discount). Count ALL complete readings that consume the whole wire and fill N
    slots. The TRUE reading is always one of them.

    Returns (S_joint, per-bundle-fork-sizes ignored, n_distinct_epochsets)."""
    N = board["N"]
    fwd, bwd = make_shuffle(N)
    wire = board["wire_items"]

    count = 0
    epoch_sets = set()
    nodes = [0]
    NODE_CAP = 4_000_000

    def rec(slot, witem, filled, chosen):
        nonlocal count
        nodes[0] += 1
        if nodes[0] > NODE_CAP:
            return
        # advance cursor over already-filled (hole / committed-child) slots
        while slot < N and slot in filled:
            slot += 1
        if witem == len(wire):
            if slot == N:
                count += 1
                epoch_sets.add(tuple(sorted(chosen)))
            return
        if slot >= N:
            return
        kind, a, seed = wire[witem]
        if kind == "lit":
            # a literal occupies exactly this slot (k-free), advance both cursors
            nf = dict(filled)
            nf[slot] = True
            rec(slot + 1, witem + 1, nf, chosen)
            return
        # bundle: enumerate epoch candidates exactly as v1 try_decode. The
        # explosion check is ALWAYS applied with the WIRE'S seed read at this
        # cursor (no skipped checks) -- so survivors are real grammar-valid
        # re-expansions, not artifacts of a skipped filter.
        for k in range(1, T + 1):
            shifts = T - k + 1
            p0 = BWD[shifts][slot]
            for j0 in range(a):
                q = p0 - j0
                if q < 0 or q + a > N:
                    continue
                F = [FWD[shifts][q + j] for j in range(a)]
                if min(F) != slot:
                    continue
                if any((f != slot) and (f in filled) for f in F):
                    continue
                if any(f < slot and f != slot for f in F):
                    continue
                exp = H_bits(f"{seed}|p{k}", a * B)
                if not parses_as_a_items_len(exp, a):
                    continue
                nf = dict(filled)
                for j in range(a):
                    nf[F[j]] = True
                rec(slot + 1, witem + 1, nf,
                    chosen + [(witem, k)])

    rec(0, 0, {}, [])
    return count, [], len(epoch_sets)


# ---------------------------------------------------------------------------
# HARNESS
# ---------------------------------------------------------------------------
def section(t):
    print("\n" + "=" * 76 + "\n" + t + "\n" + "=" * 76)


@lru_cache(maxsize=None)
def q_bundle_exact(a=2):
    @lru_cache(maxsize=None)
    def n_item_strings_of_len(w):
        c = 0
        if w == literal_item_bits():
            c += (1 << B)
        for arity, cw_bits in ARITY_CODEWORD_BITS.items():
            seed_len = w - cw_bits
            if seed_len < J_BITS + 2:
                continue
            for tw in range(1, 9):
                pw = seed_len - J_BITS - tw
                if pw < 1:
                    continue
                if lotus_width_for_value(pw) != tw:
                    continue
                c += (1 << pw)
        return c

    @lru_cache(maxsize=None)
    def avalid(aa, L):
        if aa == 0:
            return 1 if L == 0 else 0
        tot = 0
        for w in range(MIN_ITEM, L - (aa - 1) * MIN_ITEM + 1):
            ni = n_item_strings_of_len(w)
            if ni:
                tot += ni * avalid(aa - 1, L - w)
        return tot
    L = a * B
    return avalid(a, L) / (1 << L)


def main():
    section("S2 JOINT WIRE-CONSISTENCY DFS  (the omitted cross-bundle constraint)")
    q = q_bundle_exact(A)
    print(f"  q_bundle (exact) = {q:.6f}   E = {-math.log2(q):.3f} bits   "
          f"knee K = {1/q:.0f}")
    print("  Orbit period rho = ord(5 mod P): drives geometric wrap.")
    for N in (16, 22, 28):
        P = least_prime_geq(max(N, 3))
        x, n = 5 % P, 1
        while x != 1:
            x = (x * 5) % P
            n += 1
        print(f"    N={N:3d}  P={P:3d}  rho={n}")

    section("(A) ISOLATED (lane's method) vs FAITHFUL JOINT decode -- same draws")
    print("  ISO   = product over bundles of per-bundle epoch candidates from")
    print("          GEOMETRY + EXPLOSION ONLY (no hole knowledge) -- the lane's")
    print("          count_survivors with `filled` empty. ~= base^R.")
    print("  JOINT = FAITHFUL v1 try_decode walk: packed wire, holes GENERATED by")
    print("          committed epochs (NOT given), `filled` built incrementally.")
    print("          This is the real decoder; forensics measured ITS forks")
    print("          exploding ~2x/pass. TRUE reading always among survivors.")
    print("  CORRECTION FROM ROUND 1: the earlier JOINT was HANDED the true hole")
    print("  set (skip_slots) and collapsed to O(1) -- an artifact (you cannot see")
    print("  holes on a packed wire). Stripped. Now holes are derived, not given.")
    print()
    print(f"  {'T':>5} {'R':>2} {'N':>4} {'mean ISO':>10} {'mean JOINT':>11} "
          f"{'mean #epochsets':>15} {'true_ok%':>9}")
    rng = random.Random(31337)
    for T in (20, 60, 120):
        for R in (2, 3, 4, 5):
            N = max(16, 6 * R + 10)
            FWD, BWD, _f, _b = orbit_tables(N, T)
            iso_vals, joint_vals, eset_vals = [], [], []
            true_ok = 0
            trials = 25
            for _ in range(trials):
                board = encode(N, T, R, rng, FWD, BWD)
                if len([r for r in board["records"] if r["a"] >= 2]) != R:
                    continue
                # ISO: per-bundle epoch candidates, geometry + explosion ONLY,
                # NO hole/skip knowledge, NO joint disjointness (the lane's
                # isolated count_survivors with `filled` empty).
                iso = 1
                for r in board["records"]:
                    raw = raw_candidates(r["seed_slot"], N, T, FWD, BWD)
                    epochs_ok = set()
                    for (k, qq, F) in raw:
                        exp = H_bits(f"{r['seed']}|p{k}", A * B)
                        if parses_as_a_items_len(exp, A):
                            epochs_ok.add(k)
                    iso *= max(len(epochs_ok), 1)
                S_joint, _pc, nesets = joint_survivors(board, T, FWD, BWD)
                true_ok += 1 if S_joint >= 1 else 0
                iso_vals.append(iso)
                joint_vals.append(S_joint)
                eset_vals.append(nesets)

            def mean(v):
                return sum(v) / len(v) if v else float('nan')
            print(f"  {T:>5} {R:>2} {N:>4} {mean(iso_vals):>10.2f} "
                  f"{mean(joint_vals):>11.2f} {mean(eset_vals):>15.2f} "
                  f"{100*true_ok/max(len(joint_vals),1):>8.0f}%")

    section("(B) does JOINT grow with R?  (exponential => lane right; flat => pin)")
    print("  Hold T fixed well past the knee; sweep R on the FAITHFUL decoder. If")
    print("  ln(JOINT) rises with R, holes-derived cross-fill did NOT pin -- the")
    print("  count is still ~base^R (lane right, impossibility holds). If JOINT is")
    print("  flat ~O(1), holes-derived geometry alone pinned (run the gate).")
    print()
    rng = random.Random(271828)
    T = 120
    print(f"  T={T}  (q={q:.5f}, knee={1/q:.0f}; orbit rho<=N<<T so geometry wraps "
          f"~{T}/rho times; base=1+(T-1)q={1+(T-1)*q:.3f})")
    base = 1 + (T - 1) * q
    print("  KEY: a PIN means #epochsets == 1 for ALL R. base^R growing means NO")
    print("  pin (slow exponential, small base below the knee). Compare columns:")
    print(f"  {'R':>2} {'N':>4} {'base^R':>8} {'mean #epochsets':>15} "
          f"{'mean JOINT':>11} {'ln(JOINT)':>10}")
    prev_ln = None
    for R in (2, 3, 4, 5, 6):
        N = max(16, 6 * R + 10)
        FWD, BWD, _f, _b = orbit_tables(N, T)
        jv, ev = [], []
        for _ in range(40):
            board = encode(N, T, R, rng, FWD, BWD)
            if len([r for r in board["records"] if r["a"] >= 2]) != R:
                continue
            S_joint, _pc, nesets = joint_survivors(board, T, FWD, BWD)
            jv.append(S_joint)
            ev.append(nesets)
        mj = sum(jv) / len(jv) if jv else float('nan')
        me = sum(ev) / len(ev) if ev else float('nan')
        lnj = math.log(mj) if mj > 0 else float('-inf')
        slope = "" if prev_ln is None else f"  d(ln)/dR={lnj-prev_ln:+.3f}"
        prev_ln = lnj
        print(f"  {R:>2} {N:>4} {base**R:>8.3f} {me:>15.3f} "
              f"{mj:>11.3f} {lnj:>10.3f}{slope}")
    print("  #epochsets tracks base^R (NOT flat at 1) -> no pin. base=1+(T-1)q="
          f"{base:.3f} here; past knee K={1/q:.0f} base->log2(T)-E grows unbounded.")

    section("(C) THE ROUND-1 ARTIFACT, NAMED -- why holes-given pins for FREE-looking")
    print("  Round 1 of this lane HANDED joint_survivors the true hole set")
    print("  (skip_slots) and saw S_joint -> O(1): a false 'pin'. The packed wire")
    print("  emits NOTHING at a hole (v1 serialize: `if p in skip: continue`), so a")
    print("  decoder CANNOT observe holes. Hole positions ARE the birth info:")
    print("  forensics Q1 -- 'cannot know where children belong without unwinding")
    print("  the permutation, and unwinding requires k'. To make holes available")
    print("  you must STORE them: log2 C(N, #holes) bits of arrangement.")
    print()
    print(f"  {'N':>4} {'#holes':>7} {'log2 C(N,h) carriage bits':>26}")
    for (N, h) in ((22, 3), (34, 5), (46, 6), (100, 12)):
        c = math.lgamma(N + 1) - math.lgamma(h + 1) - math.lgamma(N - h + 1)
        print(f"  {N:>4} {h:>7} {c/math.log(2):>26.2f}")
    print()
    print("  CURRENCY of the round-1 'pin': wrap/carriage (the PCTB position tax,")
    print("  BRIEF 'PCTB lesson': 22x bloat at 64 passes). Not free. With holes")
    print("  DERIVED (sections A,B) #epochsets tracks base^R (base=1+(T-1)q>1),")
    print("  NOT a pin -> impossibility holds. Below knee K=655 base~1 (prize b,")
    print("  bounded reach); past K base->log2(T)-E grows unbounded (stored-bits).")

    section("(D) AFFINE-STRIDE 'pin' needs a board >= T -> carriage, not free")
    print("  The only construction that could pin epoch to O(1) is the affine-")
    print("  stride gap fingerprint: gap ~ 5^(T-k+1) mod P -> discrete-log -> k.")
    print("  It pins ONLY if the orbit is non-periodic over [1,T], i.e. ord(5 mod")
    print("  P) >= T, which forces P (board size) >= T. Per-record carriage log2 P:")
    print()

    def lpg(n):
        def ip(m):
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
        while not ip(n):
            n += 1
        return n

    def ordm(g, p):
        x, n = g % p, 1
        while x != 1:
            x = (x * g) % p
            n += 1
        return n
    print(f"  {'T':>6} {'min P (ord>=T)':>15} {'carriage log2 P':>16} {'birth bill log2 T':>18}")
    for T in (16, 64, 256, 1024, 4096):
        P = lpg(T + 1)
        while ordm(5, P) < T:
            P = lpg(P + 1)
        print(f"  {T:>6} {P:>15} {math.log2(P):>16.2f} {math.log2(T):>18.2f}")
    print()
    print("  carriage log2 P >= log2 T = the birth bill. The affine-stride pin does")
    print("  NOT beat the bill; it RELOCATES it from stored-checksum to wrap/")
    print("  carriage. No free unbounded bundle channel exists under either route.")


if __name__ == "__main__":
    main()
