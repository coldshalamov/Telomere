"""proof_kernel.break_even_surface — WHERE the machine crosses 100%.

The drift surface has one free axis the format cannot set by itself: the
fraction rho of input blocks that actually ARE seed-derived (reachable by a
short seed, the planted-fixture mechanism the repo has already proven end to
end). At rho=0 (uniform input) the surface sits above 1. This module computes
THE TARGET: rho*(b, A, D, k, a_pl) — the seed-derived fraction at which
E[final/raw] crosses 1.0 — via the canonical recurrence on a mixed population.

planted unit: ONE k-bit seed expands a_pl consecutive blocks (the repo's
planted-sha256-arity2 fixture is k=8..16, a_pl=2). planted record cost =
arity_cost(a_pl) + J3D1(k), covering a_pl*b raw bits.

Also computes the maintainer's four mechanism quantities exactly.
No verdicts. The output IS the target.
"""
import functools

import costs
costs.pstar = functools.lru_cache(maxsize=None)(costs.pstar)        # speed: pure functions
import hit_distribution
hit_distribution.pstar = costs.pstar
hit_distribution.p_min_record_le = functools.lru_cache(maxsize=None)(hit_distribution.p_min_record_le)
hit_distribution.gain_tail = functools.lru_cache(maxsize=None)(hit_distribution.gain_tail)
hit_distribution.e_gain_given_hit = functools.lru_cache(maxsize=None)(hit_distribution.e_gain_given_hit)
from costs import LITERAL_BITS, arity_cost, j3d1_cost
from hit_distribution import M, p_min_record_le
from state_recurrence import pass1_bracket, pass_update
import state_recurrence
state_recurrence.p_min_record_le = hit_distribution.p_min_record_le
state_recurrence.gain_tail = hit_distribution.gain_tail
state_recurrence.e_gain_given_hit = hit_distribution.e_gain_given_hit

_P1 = {}
def unit_pass1(b, A, D, bound):
    key = (b, A, D, bound)
    if key not in _P1:
        lo, up = pass1_bracket(1_000_000, b, A, D)
        H = lo if bound == "lower" else up
        _P1[key] = {L: c / 1_000_000 for L, c in H.items()}
    return _P1[key]

def final_ratio(rho, N, b, A, D, T, k, a_pl, bound):
    rec = arity_cost(a_pl) + j3d1_cost(k)
    h1 = unit_pass1(b, A, D, bound)
    n_u = (1.0 - rho) * N
    H = {L: c * n_u for L, c in h1.items()}
    H[rec] = H.get(rec, 0.0) + rho * N / a_pl          # planted: 1 record per a_pl blocks
    bits = sum(L * c for L, c in H.items())
    for _t in range(2, T + 1):
        H, row = pass_update(H, A, D, bound)
        nxt = row.get("bits_after", bits)
        if abs(nxt - bits) < 1e-9 * max(bits, 1.0):
            bits = nxt; break
        bits = nxt
    return bits / (N * b)

def rho_star(N, b, A, D, T, k, a_pl, bound):
    if final_ratio(1.0, N, b, A, D, T, k, a_pl, bound) > 1.0:
        return float("nan")
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if final_ratio(mid, N, b, A, D, T, k, a_pl, bound) > 1.0:
            lo = mid
        else:
            hi = mid
    return hi

if __name__ == "__main__":
    N, T, D = 200_000, 4, 127
    print("=" * 80)
    print("THE TARGET: rho* = seed-derived fraction of input at which final/raw = 1.0")
    print("planted unit: one k-bit seed -> a_pl blocks (repo fixture = k<=16, a_pl=2)")
    print("bracket = [oracle selection, conservative selection]; canonical costs; D at 2^127 cap")
    print("=" * 80)
    print(f"{'b':>4} {'a_pl':>4} {'seed k':>7} | {'planted rec':>11} | {'rho* bracket':>20}")
    for b in (16, 24, 32):
        for (a_pl, k) in ((1, 8), (2, 8), (2, 16)):
            rec = arity_cost(a_pl) + j3d1_cost(k)
            up = rho_star(N, b, 5, D, T, k, a_pl, "upper")
            lo = rho_star(N, b, 5, D, T, k, a_pl, "lower")
            tag = f"[{100*up:6.2f}%, {100*lo:6.2f}%]" if up == up else "  never (rec >= raw)"
            print(f"{b:>4} {a_pl:>4} {k:>6}b | {rec:>4}b / {a_pl*b:>3}b raw | {tag:>20}")

    print()
    print("MECHANISM QUANTITIES (b=24 design point, D at format cap):")
    L = 24 + LITERAL_BITS
    m_comp = M(1, L - 1, 127); m_eq = M(1, L, 127) - m_comp
    print(f"  1. neutral(=) vs compressive(<) encodings at L={L}: {m_eq:,} vs {m_comp:,}"
          f"  (ratio {m_eq/m_comp:.2f}:1)")
    p_eq = p_min_record_le(L, L, 1, 127) - p_min_record_le(L - 1, L, 1, 127)
    p_lt = p_min_record_le(L - 1, L, 1, 127)
    print(f"  2. neutral-swap refresh rate: P(min_record == L) = {p_eq:.5f} per entry/pass"
          f"  (compressive rate {p_lt:.5f})")
    print(f"     zero-metadata and fully decodable: a neutral record is a legal record.")
    print(f"  3. Lotus J3D1 efficiency payload/field: "
          + ", ".join(f"p={p}: {100*p/j3d1_cost(p):.1f}%" for p in (8, 32, 64, 127)))
    ret8 = p_min_record_le(L + 8, L, 1, 127) - p_min_record_le(L - 1, L, 1, 127)
    print(f"  4. superposition delta=8 (235A/235B): retained mass = {ret8:.4f} per entry;"
          f"  conversion = window rate x 2^-E[extra]; oracle bound x1")
