"""proof_kernel.hit_distribution — exact seed counts and hit/gain distributions.

Core objects (PROOF_TARGET.md):
    M(a, r, D)                exact count of seeds with record_cost <= r, payload <= D
    P(min_record <= r | S,a)  exact finite form and stable exponential form
    P(gain >= g | S,a,D)      full tail, never collapsed to a mean

Assumption carried by every probability here: the uniform match law —
each seed's expansion prefix equals a given S-bit value with probability 2^-S,
independently. (PROOF_TARGET 'Assumptions'.)
"""
import math

from costs import pstar


def M(a: int, r: int, D: int) -> int:
    """Exact number of seed indices with record_cost(a, bitlen(idx)) <= r and
    payload width <= D. Indices of width <= pm number exactly 2^pm."""
    pm = pstar(r, a)
    if pm < 1:
        return 0
    return 1 << min(pm, D)


def p_min_record_le(r: int, S: int, a: int, D: int, exact: bool = False) -> float:
    """P(min over all admissible seeds of record cost <= r | span of S bits)."""
    m = M(a, r, D)
    if m == 0:
        return 0.0
    log2x = (m.bit_length() - 1) - S          # log2(M / 2^S), integer-accurate
    if log2x >= 7:
        return 1.0
    x = m / (2.0 ** S) if S < 1000 else 2.0 ** log2x
    if exact and S < 64:
        return 1.0 - (1.0 - 2.0 ** -S) ** m   # exact finite form, small universes
    return 1.0 - math.exp(-x)                  # stable form, any size


def gain_tail(S: int, a: int, D: int, gmax: int = 288) -> list:
    """[P(gain>=1), ..., P(gain>=gmax)]; gain>=g  <=>  min_record <= S-g."""
    return [p_min_record_le(S - g, S, a, D) for g in range(1, gmax + 1)]


def e_gain_given_hit(S: int, a: int, D: int) -> float:
    """E[gain | gain>=1], from the full tail. Reported, never assumed."""
    t = gain_tail(S, a, D)
    return (sum(t) / t[0]) if t[0] > 0 else 0.0


if __name__ == "__main__":
    # validator anchor: P(headroom>=d) = 1 - exp(-2^-d), content-size invariant
    for d in (1, 4, 8):
        law = 1 - math.exp(-(2.0 ** -d))
        print(f"  P(gain-law >= {d}) = {law:.4f}  (measured toy: d=1 .40-.44, d=4 .062, d=8 .0040)")
