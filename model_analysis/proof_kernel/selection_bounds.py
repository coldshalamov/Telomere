"""Selection-policy brackets for non-overlapping Telomere replacements."""

from __future__ import annotations

from dataclasses import dataclass


POLICIES = ("left_to_right", "greedy_largest_gain", "oracle_weighted_interval")


@dataclass(frozen=True)
class SelectionEstimate:
    policy: str
    candidate_windows: float
    accepted_windows: float
    conflict_loss: float
    proof_role: str


def disjoint_windows(entry_count: float, arity: int) -> float:
    return max(0.0, entry_count / arity)


def sliding_windows(entry_count: float, arity: int) -> float:
    return max(0.0, entry_count - arity + 1.0)


def estimate_selection(entry_count: float, arity: int, hit_probability: float, policy: str) -> SelectionEstimate:
    """Expected accepted windows for the requested selection policy.

    The left-to-right policy is a conservative lower bound because it partitions
    the stream into disjoint arity-a windows. The oracle policy is an upper
    bound because it credits every positive window before overlap conflicts.
    Greedy is the deterministic middle estimate used for candidate configs.
    """

    if policy not in POLICIES:
        raise ValueError(f"unknown selection policy: {policy}")
    hit_probability = max(0.0, min(1.0, hit_probability))
    if entry_count <= 0 or arity <= 0:
        return SelectionEstimate(policy, 0.0, 0.0, 0.0, "empty")

    if policy == "left_to_right":
        candidates = disjoint_windows(entry_count, arity)
        accepted = candidates * hit_probability
        return SelectionEstimate(policy, candidates, accepted, 0.0, "lower_bound")

    candidates = sliding_windows(entry_count, arity)
    raw_hits = candidates * hit_probability
    if policy == "oracle_weighted_interval":
        return SelectionEstimate(policy, candidates, raw_hits, 0.0, "upper_bound")

    density = raw_hits / max(entry_count, 1.0)
    conflict_factor = 1.0 / (1.0 + max(0, arity - 1) * density)
    lower = disjoint_windows(entry_count, arity) * hit_probability
    accepted = max(lower, min(disjoint_windows(entry_count, arity), raw_hits * conflict_factor))
    return SelectionEstimate(
        policy,
        candidates,
        accepted,
        max(0.0, raw_hits - accepted),
        "deterministic_estimate",
    )


def validate_selection_order() -> None:
    for n in (10, 1000):
        for arity in range(1, 6):
            for p in (0.001, 0.1, 0.9):
                lo = estimate_selection(n, arity, p, "left_to_right").accepted_windows
                mid = estimate_selection(n, arity, p, "greedy_largest_gain").accepted_windows
                up = estimate_selection(n, arity, p, "oracle_weighted_interval").accepted_windows
                if not (lo <= mid + 1e-12 and mid <= up + 1e-12):
                    raise AssertionError((n, arity, p, lo, mid, up))


if __name__ == "__main__":
    validate_selection_order()
    print("selection bounds OK")
