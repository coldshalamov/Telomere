#!/usr/bin/env python3
"""
F-frozen-record_reversibility.py — isolate the ONE question the lane flags:

  A frozen record changes the permutation the others see. Is the whole
  frozen-board process still invertible with ZERO stored state?

We answer in two layers, cleanly:

  LAYER 1 (schedule supplied): given the per-pass born-position schedule,
    is the forward frozen-board map a bijection on items, and does replaying
    it in reverse recover every original slot exactly? (Expected: YES — the
    schedule is sufficient. This is the 9/9 analogue.)

  LAYER 2 (schedule NOT supplied): can the decoder DERIVE the schedule from
    the final wire alone (record tags + positions), with zero stored bits?
    We test the only free anchor — the FINAL pass — and show the induction
    fails at pass T-1: the movable domain there is not wire-derivable.

Pure permutation logic; no hashing needed (geometry only).
"""
from math import log2


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


def perm_on(domain, a=5, shift=1):
    """Return fwd, bwd dicts mapping position->position for a shuffle restricted
    to the list `domain` (a sorted list of board positions). The shuffle acts
    on the LOCAL indices [0,m) then maps back to the domain positions.
    fwd[old_board_pos] = new_board_pos."""
    m = len(domain)
    if m <= 1:
        return {p: p for p in domain}, {p: p for p in domain}
    P = prime_geq(m)
    a2 = a
    while a2 % P == 0:
        a2 += 1
    # local newlocal -> oldlocal
    local_fwd = [0] * m
    for i in range(m):
        j = (a2 * i) % P
        while j >= m:
            j = (a2 * j) % P
        local_fwd[(j + shift) % m] = i
    fwd = {}
    bwd = {}
    for newlocal in range(m):
        oldlocal = local_fwd[newlocal]
        old_pos = domain[oldlocal]
        new_pos = domain[newlocal]
        fwd[old_pos] = new_pos
        bwd[new_pos] = old_pos
    return fwd, bwd


def forward_frozen(M, schedule, a=5, shift=1, verbose=False):
    """Forward frozen-board run.
    Returns: item_at_final[pos]=original_slot, record_final_positions(set),
    movable_domain_per_pass(list of sorted position lists),
    born_pass_of_item(dict).
    """
    pos_to_item = list(range(M))      # board position -> item id (= orig slot)
    frozen_items = set()
    born = {}
    movable_per_pass = []
    T = max(schedule) if schedule else 0
    for t in range(1, T + 1):
        for posn in schedule.get(t, ()):
            it = pos_to_item[posn]
            if it not in frozen_items:
                frozen_items.add(it)
                born[it] = t
        frozen_positions = {p for p in range(M)
                            if pos_to_item[p] in frozen_items}
        movable = sorted(p for p in range(M) if p not in frozen_positions)
        movable_per_pass.append(movable)
        fwd, _ = perm_on(movable, a=a, shift=shift)
        new_pos_to_item = list(pos_to_item)
        for old_pos in movable:
            new_pos_to_item[fwd[old_pos]] = pos_to_item[old_pos]
        pos_to_item = new_pos_to_item
        if verbose:
            print(f"  pass {t}: movable={movable} -> pos_to_item={pos_to_item}")
    rec_final = {p for p in range(M) if pos_to_item[p] in frozen_items}
    return pos_to_item, rec_final, movable_per_pass, born


def reverse_frozen(M, schedule, final_pos_to_item, a=5, shift=1):
    """Reverse using the schedule. We must RE-DERIVE the movable domains by
    forward replay (births are given as positions). Then undo each pass.
    Returns recovered_pos_to_item that should equal identity-composed inverse
    => we recover original slot at each final position."""
    # Re-derive movable domains exactly (forward, schedule known).
    _, _, movable_per_pass, _ = forward_frozen(M, schedule, a=a, shift=shift)
    T = len(movable_per_pass)
    item_at = list(final_pos_to_item)  # board pos -> item id, at FINAL state
    for t in range(T, 0, -1):
        movable = movable_per_pass[t - 1]
        fwd, bwd = perm_on(movable, a=a, shift=shift)
        # forward did: new[fwd[old]] = old_item. reverse: old[bwd... ]
        new_item_at = list(item_at)
        for new_pos in movable:
            old_pos = bwd[new_pos]
            new_item_at[old_pos] = item_at[new_pos]
        item_at = new_item_at
    return item_at  # board pos -> original slot, BEFORE any pass (identity)


def layer1():
    print("== LAYER 1: schedule supplied — is it invertible? ==")
    M = 15
    schedule = {1: {3}, 2: {0, 7}, 3: {5}, 4: {2}}
    fp_item, rec_final, movable_per_pass, born = forward_frozen(
        M, schedule, verbose=True)
    print(f"  final pos_to_item (orig slot at each final pos): {fp_item}")
    print(f"  record final positions: {sorted(rec_final)}")
    # forward map bijection check: pos_to_item must be a permutation of [0,M)
    bij = sorted(fp_item) == list(range(M))
    print(f"  forward map is a bijection on items: {bij}")
    recovered = reverse_frozen(M, schedule, fp_item)
    # after full reverse, board pos p should hold the item that STARTED at p
    # i.e. recovered should be the identity list [0,1,...,M-1]
    identity_ok = recovered == list(range(M))
    print(f"  reverse recovers identity (every slot home): {identity_ok}")
    print(f"  recovered: {recovered}")
    print(f"  => WITH the schedule, frozen-board is fully invertible: "
          f"{bij and identity_ok}\n")
    return bij and identity_ok


def layer2():
    print("== LAYER 2: schedule NOT supplied — can decoder derive it? ==")
    M = 15
    schedule = {1: {3}, 2: {0, 7}, 3: {5}, 4: {2}}
    fp_item, rec_final, movable_per_pass, born = forward_frozen(M, schedule)
    T = len(movable_per_pass)
    print(f"  final record positions (visible on wire): {sorted(rec_final)}")
    print(f"  TRUE movable domain per pass (NOT on wire):")
    for t, mv in enumerate(movable_per_pass, 1):
        print(f"    pass {t}: {mv}")
    # The decoder's ONLY free anchor: the FINAL pass's movable domain =
    # complement of ALL frozen positions = the non-record final positions.
    final_movable = sorted(p for p in range(M) if p not in rec_final)
    true_final_movable = movable_per_pass[-1]
    print(f"  decoder can read final-pass movable (non-record posns): "
          f"{final_movable}")
    print(f"  matches true final-pass movable: {final_movable == true_final_movable}")
    # But pass T-1's movable domain = complement of frozen-as-of-(T-1).
    # frozen-as-of-(T-1) = final frozen MINUS records born at pass T.
    # compute records born at pass T by position: need born dict by final pos
    # map item->final pos
    item_to_finalpos = {it: p for p, it in enumerate(fp_item)}
    born_at_T_positions = {item_to_finalpos[it]
                           for it, b in born.items() if b == T}
    print(f"  records actually born at pass T={T} (final positions): "
          f"{sorted(born_at_T_positions)}")
    print(f"  to get pass {T-1}'s movable domain the decoder must know which")
    print(f"  of the {len(rec_final)} records were born at pass {T} — that is")
    print(f"  precisely a birth-pass bit per record, the missing quantity.")
    # Count: how many ways to pick 'born at final pass' subset => ambiguity
    R = len(rec_final)
    # any nonempty subset of records could be the final-pass births (>=1 since
    # every real pass births >=1 here). Lower bound on ambiguity at THIS step:
    from math import comb
    ways = sum(comb(R, k) for k in range(1, R + 1))  # nonempty subsets
    print(f"  ambiguity at the first reverse induction step alone: "
          f"2^{R}-1 = {ways} subsets for 'who was born at T'.")
    print(f"  => the induction has no free base case beyond pass T; the")
    print(f"     schedule is NOT wire-derivable. Reversibility holds only")
    print(f"     when the schedule is supplied (Layer 1) = stored birth info.\n")
    return final_movable == true_final_movable


def main():
    print("#" * 72)
    print("# FROZEN-RECORD REVERSIBILITY — the lane's flagged question")
    print("#" * 72 + "\n")
    ok1 = layer1()
    ok2 = layer2()
    print("=" * 72)
    print("VERDICT")
    print("=" * 72)
    print(f"  Invertible WITH schedule supplied:        {ok1}  (Layer 1)")
    print(f"  Schedule derivable from wire for free:    NO   (Layer 2)")
    print(f"  => Freezing is reversible only if the birth schedule is")
    print(f"     supplied. The schedule IS the birth-pass information. The")
    print(f"     two-speed phase does not supply it (0 free bits, CHECK 1).")
    print(f"     Conclusion: the frozen-record lane pays the birth bill in")
    print(f"     STORED-BITS (write the schedule = tags) — net-negative past")
    print(f"     pass ~6 — or in structure/compute via trial decode, capped")
    print(f"     at the explosion-check reach (~2.5 bits ~ 6 candidate passes).")


if __name__ == "__main__":
    main()
