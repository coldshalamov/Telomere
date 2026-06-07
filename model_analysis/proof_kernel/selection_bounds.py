"""proof_kernel.selection_bounds — provable brackets around replacement selection.

The recurrence never uses a heuristic selection estimate. Every pass's accepted
mass is BRACKETED:

  LOWER (conservative disjoint windows): partition the n entries into
  floor(n/a) disjoint arity-a windows. Each is an independent trial; accepting
  every disjoint hit is always feasible (no overlaps by construction), so this
  undercounts what any real selector can do. Provable lower bound.

  UPPER (oracle interval scheduling): count every hit among all (n-a+1) sliding
  windows and credit each its full gain, ignoring overlap conflicts entirely.
  No selector can accept more than everything. Provable upper bound.

The true machine (greedy / left-to-right / weighted lattice) lies between.
"""


def disjoint_windows(n: float, a: int) -> float:
    """Number of disjoint arity-a windows available (lower-bound trial count)."""
    return max(0.0, n // a if isinstance(n, int) else n / a)


def sliding_windows(n: float, a: int) -> float:
    """Number of sliding arity-a windows (upper-bound trial count)."""
    return max(0.0, n - a + 1)


def accepted_bounds(n: float, a: int, p_hit: float):
    """(lower, upper) expected accepted replacements for one arity tier."""
    return disjoint_windows(n, a) * p_hit, sliding_windows(n, a) * p_hit
