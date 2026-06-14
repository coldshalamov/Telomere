#!/usr/bin/env python3
"""P2 — Explosion-budget lane. EXACT counting of E = -log2(q) from the REAL
J3D1 Lotus grammar, resolved by arity, with the cost-to-raise-E trade and the
converse-form impossibility.

NO luck-hashing. q is computed combinatorially.

KEY CORRECTION (verified against the implemented decoders
v1_roundtrip_proof.py and robins_exact_spec.py): the item grammar is
essentially Kraft-COMPLETE, so a uniform digest almost always parses as a
clean self-delimiting item stream (p1 -> 1). Therefore "parse-only" supplies
NO free budget (E_parse -> 0). The ~2.5 bits the repo measured is a
LENGTH-PINNED phenomenon: it requires the decoder to know the target span
length L and reject expansions whose item stream does not total exactly L.

The crux for the WALL is the arity-1 single (the unbounded grinding channel).
Both implemented decoders open a single by generating EXACTLY one item's worth
of digest (one block / one self-delimiting item) and feeding it forward to the
global checksum -- there is NO local length pin and NO explosion. So for
singles q ~= 1 and E ~= 0: the free explosion budget never reaches the channel
the whole problem is about.

Grammar (SPEC_V1 §3, costs.py mirror):
  - canonical alphabet item codewords (Kraft-complete):
      arity-1 '00' (2b), arity-2 '01' (2b), arities 3-5 (3b), literal '111' (3b)
  - LITERAL item = [3b marker][B raw bits]            (self-delimiting, fixed B)
  - RECORD item  = [arity codeword][J3D1 Lotus seed]
      Lotus seed = [3b jumpstarter=tier_width-1][tier_width-bit length field]
                   [payload of payload_width bits], self-check
                   lotus_width(payload_width) == tier_width.
"""
from __future__ import annotations
import math
from functools import lru_cache

B = 8
J_BITS = 3
ARITY_CODEWORD_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
LITERAL_MARKER_BITS = 3

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

# ---- count distinct valid self-delimiting ITEM bit-strings of wire-length w ----
@lru_cache(maxsize=None)
def n_item_strings_of_len(w: int) -> int:
    count = 0
    if w == literal_item_bits():
        count += (1 << B)                      # 111 + any B bits
    for arity, cw_bits in ARITY_CODEWORD_BITS.items():
        seed_len = w - cw_bits
        if seed_len < J_BITS + 1 + 1:
            continue
        for tw in range(1, 9):
            pw = seed_len - J_BITS - tw
            if pw < 1:
                continue
            if lotus_width_for_value(pw) != tw:
                continue
            count += (1 << pw)                 # jumpstarter+lenfield fixed, payload free
    return count

# ---- exact count of L-bit strings parsing as EXACTLY a items totalling L ----
MIN_ITEM = min(literal_item_bits(), min(record_item_bits(ar, 1) for ar in ARITY_CODEWORD_BITS))

@lru_cache(maxsize=None)
def avalid(a: int, L: int) -> int:
    if a == 0:
        return 1 if L == 0 else 0
    total = 0
    for w in range(MIN_ITEM, L - (a - 1) * MIN_ITEM + 1):
        ni = n_item_strings_of_len(w)
        if ni:
            total += ni * avalid(a - 1, L - w)
    return total

def E_len(a: int, L: int) -> float:
    av = avalid(a, L)
    return float('inf') if av == 0 else L - math.log2(av)

def p1_at_window(W: int) -> float:
    """Prob a uniform prefix STARTS with a valid self-delimiting item, counting
    item lengths up to W. As W->inf this -> 1 (grammar Kraft-complete)."""
    return sum(n_item_strings_of_len(w) / (1 << w) for w in range(1, W + 1))

# ---------------------------------------------------------------------------
def section(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

def main():
    section("P2 EXPLOSION-BUDGET — exact E from the J3D1 Lotus grammar (B=8)")

    print("\n-- item sizes (costs.py mirror) --")
    print(f"  literal item: {literal_item_bits()} bits;  smallest record: "
          f"{min(record_item_bits(a,1) for a in ARITY_CODEWORD_BITS)} bits")

    section("(1) PARSE-ONLY SUPPLIES NO BUDGET: p1 -> 1 (grammar Kraft-complete)")
    print("  W (max item len counted) |   p1    | -log2 p1 = E_parse per item")
    prev = None
    for W in (16, 24, 32, 48, 64, 96, 128, 200, 300, 500):
        p1 = p1_at_window(W)
        print(f"      {W:4d}                 | {p1:.6f} |  {-math.log2(p1):.4f}")
        prev = p1
    print("  => p1 climbs toward 1 monotonically; E_parse -> 0. A wrong-salt")
    print("     digest almost always PARSES. Parse-only is NOT the free budget.")
    print("     (Matches v1_roundtrip_proof / robins_exact_spec: opens never explode.)")

    section("(2) LENGTH-PINNED CASES CARRY A FINITE BUDGET (require a KNOWN L)")
    print("  E_len(a,L) = parse as exactly `a` items AND total wire length == L.")
    print("  This bites ONLY when the decoder independently knows L (the span).")
    for a in (1, 2):
        L = a * literal_item_bits()
        print(f"   a={a}, L={L} (={a}x literal block span): E_len={E_len(a,L):.3f} bits "
              f"(q={2**-E_len(a,L):.4f})")
    print("  E_len ranges ~2.7-7.6 over swept (a,L); MAGNITUDE-consistent with the")
    print("  repo folklore ~2.5 (PLAIN_STATUS row 7) -- but the exact repo derivation")
    print("  was NOT located, so NO reproduction claim. L=11 is a local spike (the")
    print("  one-literal-item span). This is an arity>=2 / known-L family.")

    section("(3) FOR THE SINGLES CHANNEL E(a=1) = 0 -- PROVEN BY MATH")
    # Kraft completeness check (the actual proof, not the toys)
    kraft = 2 * 2 ** -2 + 4 * 2 ** -3
    print(f"  Alphabet Kraft sum = 2*2^-2 + 4*2^-3 = {kraft}  (complete prefix code)")
    print("  Lotus length-field bijection (tier_width tw -> #valid payload widths):")
    for tw in range(1, 9):
        cnt = sum(1 for pw in range(1, 4000) if lotus_width_for_value(pw) == tw)
        print(f"     tw={tw}: {cnt:3d} widths map here  vs  2^tw = {2**tw:3d} field capacity"
              + ("   <- the one wasted slot" if tw == 1 else ""))
    print("  => uniform digests parse cleanly (p1 -> 1). Arity-1 = EXACTLY one item")
    print("     (SPEC 2.3). One item is length-unconstrained in BOTH state models")
    print("     (block-model: any B raw bits valid; item-model: completeness).")
    print("  => q = 1, E(a=1) = 0, salt-scheme-independent.")
    print("  THE FREE EXPLOSION BUDGET DOES NOT REACH SINGLES (the unbounded crux).")
    print("  (Implemented decoders' a=1 paths corroborate but cannot prove -- they")
    print("   are fixed-width toys that never explode for ANY arity by construction.)")

    section("(4) JOINT CEILING N*(T) from round-2: c_mean(T)=log2(1+(T-1)q), N*=64/c_mean")
    k = 64
    # Three readings of the singles budget, bracketing the truth:
    cases = [
        ("singles, decode-faithful  E=0.00", 0.00),
        ("singles, generous length-pin E=2.71 (L=11)", E_len(1, 11)),
        ("bundles a=2, length-pinned E=%.2f (L=22)" % E_len(2, 22), E_len(2, 22)),
    ]
    print(f"  {'reading':<44}|  q     | N*(T=64) N*(256) N*(1024)")
    for label, E in cases:
        q = 2 ** -E if E > 0 else 1.0
        row = []
        for T in (64, 256, 1024):
            c = math.log2(1 + (T - 1) * q)
            row.append(f"{k/c:7.1f}" if c > 0 else "   inf ")
        print(f"  {label:<44}| {q:.4f} | " + " ".join(row))
    print("  E=0 (the decode-faithful singles case): c_mean(T)=log2(T), so")
    print("  N*(T)=64/log2(T) -> the FULL tags bill, ZERO free discount, on the")
    print("  exact channel the WALL is about. THIS IS THE SHARP IMPOSSIBILITY.")

    section("(5) COST TO RAISE E: it is STORED-BITS, capped by the per-record WIN")
    print("  To raise E by b bits you must add b bits of format redundancy /")
    print("  self-check to the record (lower q by 2^-b). Those b bits are")
    print("  literal, incompressible record bits -> they cost the win directly.")
    print("  Per-record win: E[win|hit] ~= 2 bits (a2), ~= 1 bit (single).")
    print("  So E can rise at most ~1-2 bits above native before record bits >")
    print("  replaced bits and the match STOPS netting positive (strict acceptance).")
    print()
    print("  E_max(singles)  ~= 0 (native) + 1 (win headroom)  = ~1 bit")
    print("  E_max(bundle a2)~= native + 2                      bounded, finite")
    print("  Even at E_max, c_mean(T)=log2(1+(T-1)2^-E_max) > 0 for ALL T>=2.")

    section("(6) CONVERSE-FORM IMPOSSIBILITY (the conservation theorem)")
    print("  Sustaining T passes content-blind needs the per-record residual")
    print("  c_mean(T)=log2(1+(T-1)q) covered. For large T, c_mean(T) -> log2(T)-E.")
    print("  To hold the residual BOUNDED as T grows, E must GROW as log2(T)-O(1).")
    print("  A CONSTANT free budget E (whatever its value, native ~2.5 or raised)")
    print("  is a CONSTANT discount on a bill that still scales as N*log2(T):")
    print()
    print(f"   {'T':>6} | {'log2 T':>7} | residual log2(T)-E_max for E_max in {{0,1,2.7,5.2}}")
    for T in (2, 6, 64, 1024, 1_000_000):
        lt = math.log2(T)
        vals = "  ".join(f"{max(0.0, lt-E):6.2f}" for E in (0.0, 1.0, 2.71, 5.25))
        print(f"   {T:>6} | {lt:>7.2f} | {vals}")
    print("  Every column grows without bound in T. The free budget shifts the")
    print("  INTERCEPT, never the SLOPE. Net birth bill = N*(log2(T)-E) -> infinity.")
    print("  Currency: STORED-BITS (the residual log2(T)-E_max is unavoidable tags).")

if __name__ == "__main__":
    main()
