"""proof_kernel.superposition — retained-candidate state, bracketed.

Superposition is STATE, not deeper search (PROOF_TARGET assumptions). For a
prune delta Δ at depth D this module computes, per entry length L:

  retained(L, Δ, D) = P( min_record in [L, L+Δ] )      noncompressive match kept
  e_extra(L, Δ, D)  = E[ record − L | retained ]        the alternate's overhead

and brackets superposition's contribution per pass:

  LOWER bound: superposition off (contributes 0).
  UPPER bound: oracle superposition — every entry carries a free alternate of
               zero extra bits (e_extra = 0), so alternate-bearing windows hit
               at the unsuppressed rate. No retention policy can beat this.
  Approximation: conversion rate = window hit rate × 2^-e_extra (the alternate
               lengthens the target by e_extra bits while the bar stays at the
               main span).
"""
from hit_distribution import p_min_record_le


def retained(L: int, delta: int, D: int) -> float:
    hi = p_min_record_le(L + delta, L, 1, D)
    lo = p_min_record_le(L - 1, L, 1, D)
    return max(0.0, hi - lo)


def e_extra(L: int, delta: int, D: int) -> float:
    """Mass-weighted expected extra bits of the retained record over L."""
    lo = p_min_record_le(L - 1, L, 1, D)
    num = den = 0.0
    prev = lo
    for e in range(0, delta + 1):
        pe = p_min_record_le(L + e, L, 1, D)
        num += max(0.0, pe - prev) * e
        den += max(0.0, pe - prev)
        prev = pe
    return (num / den) if den > 0 else float(delta)


def conversion_factor(mode: str, ebar: float) -> float:
    """Multiplier on the window hit rate for alternate-bearing windows."""
    if mode == "off":
        return 0.0
    if mode == "oracle":
        return 1.0                      # upper bound: alternates cost nothing
    return 2.0 ** (-ebar)               # approximation: length suppression
