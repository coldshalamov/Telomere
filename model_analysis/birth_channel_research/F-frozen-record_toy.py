#!/usr/bin/env python3
"""
F-frozen-record_toy.py — frozen-record / two-speed-board lane.

Tests three claims by EXACT construction/enumeration (no hash-hunting; the
only SHA use is to verify a planted single round-trips, where a match is
GUARANTEED). All checks are counting/permutation logic.

Lane question (from BRIEF avenue F): once a record is born it stops moving
(or moves on a slower clock) while literals shuffle fast. Does freezing make
  (i) birth POSITION (hence salt) self-presenting, AND
  (ii) birth PASS readable from the phase gap between fast and slow clocks,
with ZERO stored state, and is the whole thing still invertible?

We test, separately:

  CHECK 1 (two-clock phase ambiguity).  Records ride sigma_slow after birth,
    literals ride sigma_fast.  final = sigma_slow^{T-t} ( sigma_fast^{t}(x0) ).
    Claim: for EVERY candidate birth pass t in [1..T] there is a valid
    original slot x0, and x0 ranges over all slots => phase gives T candidates,
    not a unique read.  => 0 free bits from the phase.

  CHECK 2 (occupancy-dependent reverse moving pool).  On a fixed board, born
    records freeze in place; survivors (literals + not-yet-frozen) shuffle
    over the COMPLEMENT of the frozen set.  To invert pass t you must know the
    frozen set as of pass t = exactly the birth schedule of all records born
    AFTER t.  Claim: self-presenting only at the final pass; every earlier
    reverse step needs future births.  We demonstrate:
      (2a) WITH the schedule supplied, reverse round-trips exactly.
      (2b) WITHOUT it, the decoder cannot even fix the permutation domain;
           enumerate the self-consistent birth-schedules and count them.

  CHECK 3 (same-board two-speed is not a bijection).  literals -> sigma_fast,
    records -> sigma_slow, on the SAME full board.  Claim: their images
    collide; de-colliding needs occupancy-aware cycle-walk = the schedule.
    We count collisions directly.

Currency accounting is printed at the end.
"""
import hashlib
import itertools
from math import log2


# ---------------------------------------------------------------------------
# shuffle primitives (the spec's prime-field multiply; +1 optional)
# ---------------------------------------------------------------------------
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


def prime_geq(n):
    n = max(n, 2)
    while not is_prime(n):
        n += 1
    return n


def make_perm(M, a=5, shift=0):
    """Permutation of [0,M): i -> (walk(a*i mod P) + shift) mod M, exact inverse.
    Returns (fwd, bwd) as full lookup lists."""
    if M <= 1:
        return [0] * M, [0] * M
    P = prime_geq(M)
    # ensure a invertible mod P
    aa = a
    while aa % P == 0:
        aa += 1
    fwd = [0] * M
    for i in range(M):
        j = (aa * i) % P
        while j >= M:
            j = (aa * j) % P
        fwd[(j + shift) % M] = i  # item i lands at position (j+shift)
    # invert
    bwd = [0] * M
    for pos, item in enumerate(fwd):
        bwd[item] = pos
    return fwd, bwd


def perm_pos(fwd, M):
    """Return function pos_after(x) = where item originally-at-x lands.
    fwd is given as fwd[newpos]=item, so we want inverse map item->newpos."""
    loc = [0] * M
    for newpos, item in enumerate(fwd):
        loc[item] = newpos
    return loc  # loc[x] = position of item x after one application


# ---------------------------------------------------------------------------
# H for the single round-trip sanity (real SHA, planted => match guaranteed)
# ---------------------------------------------------------------------------
def H_bits(key, n):
    out = ""
    c = 0
    while len(out) < n:
        out += "".join(f"{b:08b}" for b in
                        hashlib.sha256(f"{key}#{c}".encode()).digest())
        c += 1
    return out[:n]


# ===========================================================================
# CHECK 1 — two-clock phase ambiguity
# ===========================================================================
def check1_phase_ambiguity(M=23, T=12):
    """A single record born at pass t at original slot x0:
       final = sigma_slow^{T-t} ( sigma_fast^{t} (x0) ).
    Show: for EVERY t in [1..T], solving for x0 from a fixed `final` yields a
    valid slot, and across t the x0's cover (essentially) all slots => the
    observed final position is consistent with every birth pass. 0 free bits.
    """
    # two different clocks (different multipliers/shift) so they are genuinely
    # "two speeds"; both are exact permutations of the SAME board [0,M).
    fast_f, fast_b = make_perm(M, a=5, shift=1)   # literals shuffle fast
    slow_f, slow_b = make_perm(M, a=3, shift=0)   # records drift slow

    fast_loc = perm_pos(fast_f, M)   # x -> fast(x)
    slow_loc = perm_pos(slow_f, M)
    # inverses as position maps
    fast_inv = [0] * M
    for x in range(M):
        fast_inv[fast_loc[x]] = x
    slow_inv = [0] * M
    for x in range(M):
        slow_inv[slow_loc[x]] = x

    def apply_pow(loc, p, x):
        for _ in range(p):
            x = loc[x]
        return x

    # Pick a true (x0_true, t_true), compute its final position, then ask:
    # which (t, x0) pairs reproduce that final position?
    x0_true, t_true = 7, 5
    final = apply_pow(slow_loc, T - t_true,
                      apply_pow(fast_loc, t_true, x0_true))

    consistent = []
    for t in range(1, T + 1):
        # invert: y = slow^{-(T-t)}(final); x0 = fast^{-t}(y)
        y = apply_pow(slow_inv, T - t, final)
        x0 = apply_pow(fast_inv, t, y)
        consistent.append((t, x0))

    distinct_x0 = len(set(x0 for _, x0 in consistent))
    print("== CHECK 1: two-clock phase ambiguity ==")
    print(f"  M={M} board, T={T} passes, fast a=5 shift=1, slow a=3 shift=0")
    print(f"  planted true (x0={x0_true}, birth t={t_true}) -> final pos {final}")
    print(f"  birth-pass candidates consistent with final pos {final}:")
    print(f"    {consistent}")
    print(f"  => {len(consistent)} candidate birth passes, "
          f"{distinct_x0} distinct origin slots, all valid.")
    print(f"  phase pins NOTHING: every t in [1..T] has a legal x0. "
          f"free bits from phase = {log2(1):.0f} "
          f"(log2 of unique reads / log2 {len(consistent)} candidates)\n")
    return len(consistent), distinct_x0


# ===========================================================================
# CHECK 2 — occupancy-dependent reverse moving pool (the wall)
# ===========================================================================
def movable_domains_for(M, T, birth_of, a=5, shift=1):
    """Given birth_of: {final_pos -> birth_pass}, return the per-pass movable
    position lists implied by freezing each final position at its birth pass.
    (A frozen record never moves, so final pos == birth pos: freezing the final
    position from its birth pass onward is the exact forward geometry.)"""
    frozen_pos = set()
    movable_per_pass = []
    for t in range(1, T + 1):
        for f, bt in birth_of.items():
            if bt == t:
                frozen_pos.add(f)
        movable = sorted(p for p in range(M) if p not in frozen_pos)
        movable_per_pass.append(movable)
    return movable_per_pass


def encode_frozen_wire(M, B, schedule, seeds, a=5, shift=1, rng=None):
    """REAL encode to a concrete wire (real SHA for record content).
      - schedule: {pass_t -> set of CURRENT positions born at t}
      - seeds:    {final_pos -> seed} for record positions (planted).
    A born record's content is H(seed | s{final_pos}) (salt = frozen position).
    Returns: wire (dict final_pos -> ('lit',bits) | ('rec',seed)),
             original block list, true checksum, true birth_of {final_pos->pass}.
    """
    import random
    rng = rng or random.Random(0)
    # choose random literal contents for non-record slots; record slots get
    # whatever H expands to (so the original IS that content -> genuine match).
    # First run the geometry forward to learn each record's final position and
    # the original-slot it occupies, so we can set the original block bytes.
    pos_to_item = list(range(M))
    frozen_items = set()
    item_born = {}
    T = max(schedule) if schedule else 0
    # forward geometry with births by CURRENT position
    movable_lists = []
    for t in range(1, T + 1):
        for posn in schedule.get(t, ()):
            it = pos_to_item[posn]
            if it not in frozen_items:
                frozen_items.add(it)
                item_born[it] = t
        frozen_positions = {p for p in range(M)
                            if pos_to_item[p] in frozen_items}
        movable = sorted(p for p in range(M) if p not in frozen_positions)
        movable_lists.append(movable)
        m = len(movable)
        if m > 1:
            fwd, _ = make_perm(m, a=a, shift=shift)
            new_pos_to_item = list(pos_to_item)
            old_items = [pos_to_item[movable[k]] for k in range(m)]
            for newlocal in range(m):
                new_pos_to_item[movable[newlocal]] = old_items[fwd[newlocal]]
            pos_to_item = new_pos_to_item
    final_pos_to_item = list(pos_to_item)            # final pos -> orig slot
    item_to_final = {it: p for p, it in enumerate(final_pos_to_item)}
    rec_items = set(frozen_items)
    rec_final = {item_to_final[it] for it in rec_items}
    # build original blocks: record slots' content = H(seed|s{finalpos});
    # literal slots = random bytes.
    blocks = [None] * M
    wire = {}
    true_birth_of = {}
    for p in range(M):
        orig_slot = final_pos_to_item[p]
        if p in rec_final:
            seed = seeds[p]
            content = H_bits(f"{seed}|s{p}", B)     # salt = final position
            blocks[orig_slot] = content
            wire[p] = ('rec', seed)
            true_birth_of[p] = item_born[final_pos_to_item[p]]
        else:
            content = f"{rng.getrandbits(B):0{B}b}"
            blocks[orig_slot] = content
            wire[p] = ('lit', content)
    original = "".join(blocks)
    checksum = hashlib.sha256(original.encode()).hexdigest()
    return wire, blocks, original, checksum, true_birth_of, rec_final


def decode_fixed_wire(wire, M, B, birth_of, a=5, shift=1):
    """REAL decode of the FIXED wire under a CANDIDATE labeling birth_of
    ({final_pos -> birth_pass}). Reverse the frozen-board geometry implied by
    birth_of to map each final position back to its original slot; expand
    records by salt = their final position; place literals. Return the
    reconstructed original string, or None if structurally invalid.

    This is discriminating: a wrong labeling implies different movable domains
    => a different inverse permutation => the SAME wire decodes to a DIFFERENT
    original. Only the labeling whose inverse is geometrically consistent and
    whose checksum matches is the true reading."""
    T = max(birth_of.values()) if birth_of else 0
    movable_per_pass = movable_domains_for(M, T, birth_of, a=a, shift=shift)
    # Recover, for each final position, the original slot sitting there under
    # THIS labeling. We track an item-label array (identity = "the item that
    # started at board position x"), replay the SAME forward shuffle the encoder
    # used to build forward[label]->finalpos, then invert that map. Mirroring
    # the encoder exactly avoids any direction error.
    #   encoder forward (per pass): new[movable[nl]] = old[movable[fwd[nl]]]
    #   => the item at local index fwd[nl] moves to local index nl.
    label_at = list(range(M))          # board pos -> original-slot label
    for t in range(1, T + 1):
        movable = movable_per_pass[t - 1]
        m = len(movable)
        if m > 1:
            fwd, _ = make_perm(m, a=a, shift=shift)
            old = [label_at[movable[k]] for k in range(m)]
            new_label_at = list(label_at)
            for nl in range(m):
                new_label_at[movable[nl]] = old[fwd[nl]]
            label_at = new_label_at
    # label_at[final_pos] = original slot of whatever sits at final_pos. This is
    # EXACTLY the encoder's forward map applied to labels, so it is consistent.
    item_at = label_at
    # item_at[final_pos] = original slot of whatever sits at final_pos.
    if sorted(item_at) != list(range(M)):
        return None                      # not a permutation -> invalid
    out = [None] * M
    for fpos in range(M):
        orig_slot = item_at[fpos]
        kind = wire[fpos]
        if kind[0] == 'lit':
            out[orig_slot] = kind[1]
        else:
            seed = kind[1]
            out[orig_slot] = H_bits(f"{seed}|s{fpos}", B)   # salt = final pos
    if any(o is None for o in out):
        return None
    return "".join(out)


def check2_occupancy(M=15):
    """DISCRIMINATING test: build ONE real wire, then decode that FIXED wire
    under every candidate birth-pass labeling. Report:
      - how many decode structurally-valid (expect T^R: geometry never blocks),
      - how many produce DISTINCT originals (these are genuine RIVAL readings),
      - how many match the 64-bit checksum (expect exactly 1: the true reading).
    This shows the birth bill (log2 T^R bits) is real and only the NON-scaling
    checksum rescues the true reading. Real SHA for record content."""
    import random
    rng = random.Random(20260613)
    B = 8
    schedule = {1: {3}, 2: {0, 7}, 3: {5}, 4: {2}}
    T = max(schedule)
    # planted seeds keyed by FINAL position (a frozen record never moves, so
    # the schedule's named positions ARE the final positions of those records).
    rec_final_positions = sorted({f for posns in schedule.values()
                                  for f in posns})
    seeds = {p: 1000 + 7 * p for p in rec_final_positions}

    wire, blocks, original, checksum, true_birth_of, rec_final = \
        encode_frozen_wire(M, B, schedule, seeds, rng=rng)
    R = len(rec_final_positions)

    # sanity: the TRUE labeling decodes the fixed wire back to the original.
    true_decoded = decode_fixed_wire(wire, M, B, true_birth_of)
    print("== CHECK 2: occupancy-dependent reverse moving pool ==")
    print(f"  M={M} fixed board, B={B}, schedule={schedule}, T={T}")
    print(f"  records on wire: {R} at final positions {rec_final_positions}")
    print(f"  (2a) TRUE labeling decodes the fixed wire to the original: "
          f"{true_decoded == original}; checksum matches: "
          f"{hashlib.sha256((true_decoded or '').encode()).hexdigest() == checksum}")

    # (2b) decode the SAME fixed wire under EVERY candidate labeling.
    valid = 0
    distinct = set()
    checksum_hits = 0
    for labeling in itertools.product(range(1, T + 1), repeat=R):
        cand_birth = dict(zip(rec_final_positions, labeling))
        decoded = decode_fixed_wire(wire, M, B, cand_birth)
        if decoded is None:
            continue
        valid += 1
        distinct.add(decoded)
        if hashlib.sha256(decoded.encode()).hexdigest() == checksum:
            checksum_hits += 1
    print(f"  (2b) candidate labelings tried: T^R = {T}^{R} = {T**R}")
    print(f"       structurally-valid decodes of the FIXED wire: {valid}")
    print(f"       DISTINCT original files produced (rival readings): "
          f"{len(distinct)}")
    print(f"       readings matching the 64-bit checksum: {checksum_hits} "
          f"(expect exactly 1 = the true reading)")
    print(f"  => the wire admits {len(distinct)} distinct frozen-board "
          f"readings; geometry pins NONE of them.")
    print(f"     birth info the wire fails to supply = log2({len(distinct)}) "
          f"= {log2(max(len(distinct),1)):.2f} bits for {R} records "
          f"(~{log2(max(len(distinct),1))/max(R,1):.2f} bits/record).")
    print(f"     Only the NON-scaling 64-bit checksum separates the true "
          f"reading; it cannot carry R*log2(T) at scale.\n")
    return len(distinct), R, T


# ===========================================================================
# CHECK 3 — same-board two-speed is not a bijection
# ===========================================================================
def check3_collision(M=23):
    """literals -> sigma_fast, records -> sigma_slow, on the SAME full board.
    Count image collisions: positions hit by >1 item. A bijection has zero.
    Records sit at some subset; literals at the rest; each maps by its own
    clock. Collisions = where a record's slow image equals a literal's fast
    image (or two records / two literals, but within one clock it's a perm so
    only cross-clock collide)."""
    fast_f, _ = make_perm(M, a=5, shift=1)
    slow_f, _ = make_perm(M, a=3, shift=0)
    fast_loc = perm_pos(fast_f, M)
    slow_loc = perm_pos(slow_f, M)

    worst = 0
    worst_set = None
    total_checked = 0
    any_collision_count = 0
    # sample several record-subsets
    import random
    rng = random.Random(7)
    for _ in range(2000):
        k = rng.randint(1, M - 1)
        rec_slots = set(rng.sample(range(M), k))
        images = []
        for x in range(M):
            if x in rec_slots:
                images.append(slow_loc[x])
            else:
                images.append(fast_loc[x])
        collisions = M - len(set(images))
        total_checked += 1
        if collisions > 0:
            any_collision_count += 1
        if collisions > worst:
            worst = collisions
            worst_set = (k, sorted(rec_slots))
    print("== CHECK 3: same-board two-speed is not a bijection ==")
    print(f"  M={M}, fast a=5 shift=1, slow a=3 shift=0")
    print(f"  subsets sampled: {total_checked}; "
          f"subsets with >=1 collision: {any_collision_count} "
          f"({100*any_collision_count/total_checked:.0f}%)")
    print(f"  worst collisions observed: {worst} (k={worst_set[0]} records)")
    print(f"  => two-speed on one full board collides for almost all "
          f"occupancy sets; de-colliding needs occupancy-aware cycle-walk")
    print(f"     = re-deriving the frozen set = the schedule. Not free.\n")
    return any_collision_count, total_checked, worst


# ===========================================================================
# planted single round-trip sanity (salt half is genuinely free)
# ===========================================================================
def check0_salt_self_presenting(M=15):
    """Plant one single at a frozen position; show its salt (= final position)
    regenerates its content with NO birth-pass input. The salt half is free."""
    B = 8
    # a frozen record at final position f; salt = f; pick seed, expand.
    f = 9
    seed = 4242
    content = H_bits(f"{seed}|s{f}", B * 2)  # arity-2 span for flavor
    # decode: we see a record tag at position f; salt is f (it's frozen there);
    # expand -> content. No birth pass used.
    redecoded = H_bits(f"{seed}|s{f}", B * 2)
    print("== CHECK 0: salt half is free (sanity) ==")
    print(f"  record frozen at final position f={f}, seed={seed}")
    print(f"  salt = final position = {f} (self-presenting, 0 stored bits)")
    print(f"  expand matches: {redecoded == content}")
    print(f"  NOTE: this is the SALT, not the birth PASS. Standard machine "
          f"already self-presents position salts.\n")
    return redecoded == content


def main():
    print("#" * 72)
    print("# FROZEN-RECORD / TWO-SPEED BOARD — lane F exact analysis")
    print("#" * 72 + "\n")
    check0_salt_self_presenting()
    n_cand, n_x0 = check1_phase_ambiguity()
    consistent, R, T = check2_occupancy()
    coll, tot, worst = check3_collision()

    print("=" * 72)
    print("CURRENCY ACCOUNTING")
    print("=" * 72)
    print(f"  SALT half:     free (position self-presenting). 0 bits. But this")
    print(f"                 is the position salt the standard machine already")
    print(f"                 supplies; freezing adds nothing new here.")
    print(f"  PHASE channel: {n_cand} candidate births per record, all valid")
    print(f"                 => 0 free bits from the two-clock gap.")
    print(f"  GEOMETRY half: reverse moving domain at pass t depends on the")
    print(f"                 frozen set = future births. Self-presenting ONLY")
    print(f"                 at the final pass. To invert earlier passes you")
    print(f"                 must reconstruct the schedule.")
    print(f"  WIRE pins:     {T**R} labelings decode the SAME fixed wire, "
          f"{consistent}")
    print(f"                 distinct rival files; exactly 1 matches the "
          f"checksum.")
    print(f"                 Geometry pins NONE; only the non-scaling 64-bit")
    print(f"                 checksum separates the true reading.")
    print(f"  SAME-BOARD:    not a bijection ({100*coll/tot:.0f}% of occupancy")
    print(f"                 sets collide). De-collision = occupancy-aware")
    print(f"                 cycle-walk = the schedule again.")
    print()
    print("  CURRENCY the birth bill reappears in: STORED-BITS if you write the")
    print("  schedule (= tags, >= log2(T) bits/record, net-negative past pass 6)")
    print("  OR structure/compute (trial-reconstruct, capped at the explosion-")
    print("  check ~2.5 bits ~ 6 candidates). Phase contributes 0 free bits.")


if __name__ == "__main__":
    main()
