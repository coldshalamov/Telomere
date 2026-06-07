"""proof_kernel.state_recurrence — entry-length histogram recurrence H_t[L].

State is a histogram (never a mean). Span lengths are exact a-fold
convolutions. Each pass produces TWO successor states: one under the
conservative lower selection bound, one under the oracle upper bound
(selection_bounds.py), so every multi-pass figure is a bracket, not a guess.

Pass 1 (raw spans vs the wrapped-literal bar) and passes 2+ (current-entry
targets, strict bar, marker charged once at init only) follow
docs/FORMAT_CANONICAL.md semantics.
"""
from collections import defaultdict

from costs import LITERAL_BITS, record_cost, arity_cost  # noqa: F401
from hit_distribution import p_min_record_le, gain_tail, e_gain_given_hit
from selection_bounds import accepted_bounds


def convolve(p1: dict, p2: dict, prune: float = 1e-12) -> dict:
    out = defaultdict(float)
    for L1, q1 in p1.items():
        for L2, q2 in p2.items():
            out[L1 + L2] += q1 * q2
    return {L: q for L, q in out.items() if q > prune}


def span_dists(pmf: dict, A: int) -> dict:
    d = {1: dict(pmf)}
    for a in range(2, A + 1):
        d[a] = convolve(d[a - 1], pmf)
    return d


def pass1_bracket(N: int, b: int, A: int, D: int):
    """Initial state: raw arity-a spans against the wrapped bar a*(b+3);
    unmatched blocks wrap ONCE. Returns (H_lower, H_upper)."""
    out = []
    for bound in ("lower", "upper"):
        H = defaultdict(float)
        remaining = float(N)
        for a in range(A, 0, -1):                       # prefer wide tiles
            S, bar = a * b, a * (b + LITERAL_BITS)
            ph = p_min_record_le(bar - 1, S, a, D)
            if ph <= 0 or remaining < a:
                continue
            lo, up = accepted_bounds(remaining, a, ph)
            take = min((lo if bound == "lower" else up), remaining / a)
            eg = e_gain_given_hit(S, a, D)              # vs the wrapped bar
            H[max(1, round(bar - eg))] += take
            remaining -= take * a
        H[b + LITERAL_BITS] += remaining
        out.append(dict(H))
    return out[0], out[1]


def pass_update(H: dict, A: int, D: int, bound: str) -> tuple:
    """One recursive pass on current entries (strict bar = span itself).
    bound: 'lower' (disjoint windows) or 'upper' (oracle sliding windows)."""
    n = sum(H.values())
    bits = sum(L * c for L, c in H.items())
    if n < 2:
        return H, dict(bits=bits, n=n, acc=0.0, saved=0.0)
    pmf = {L: c / n for L, c in H.items()}
    spans = span_dists(pmf, A)
    acc = saved = merged = 0.0
    rec_mass = defaultdict(float)
    for a in range(1, A + 1):
        for S, q in spans[a].items():
            Sr = int(round(S))
            ph = p_min_record_le(Sr - 1, Sr, a, D)
            if ph <= 0:
                continue
            lo, up = accepted_bounds(n, a, ph)
            h = (lo if bound == "lower" else up) * q
            eg = e_gain_given_hit(Sr, a, D)
            acc += h
            saved += h * eg
            merged += h * (a - 1)
            rec_mass[max(1, round(S - eg))] += h
    taken = acc + merged
    newH = {L: max(0.0, c - taken * pmf[L]) for L, c in H.items()}
    for L, c in rec_mass.items():
        newH[L] = newH.get(L, 0.0) + c
    return newH, dict(bits=bits, n=n, acc=acc, saved=saved,
                      bits_after=bits - saved, n_after=n - merged)
