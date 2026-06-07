"""proof_kernel.concentration — from expectation to every-large-file statements.

Goal (PROOF_TARGET): given E[final/raw] for profile P, bound the probability
that a single file deviates: P( |final/raw − E| > ε ) ≤ f(N, ε).

Instrument: bounded differences (McDiarmid/Hoeffding). Changing one input
block changes the final size by at most c bits, where c is bounded by the
worst per-block swing the format allows (one wrapped literal vs the largest
record share a block can carry):

    c  ≤  (b + LITERAL_BITS)  +  max over a<=A of record_cost(a, a*b)/a

Then for X = final_bits over N blocks:

    P( |X − E[X]| ≥ t )  ≤  2 · exp( −2 t² / (N · c²) )

Setting t = ε·N·b gives the ratio form. The bound is crude but PROVABLE; the
kernel reports it alongside every surface point so that "the average file"
becomes "all but an exp(−Θ(N))-fraction of files".
"""
import math

from costs import LITERAL_BITS, record_cost


def per_block_swing(b: int, A: int) -> float:
    """Provable bound c on how much one block can move the final size (bits)."""
    wrap = b + LITERAL_BITS
    widest = max(record_cost(a, a * b) / a for a in range(1, A + 1))
    return wrap + widest


def deviation_bound(N: int, b: int, A: int, eps_ratio: float) -> float:
    """P( |final/raw − E| > eps_ratio ) ≤ this value (two-sided)."""
    c = per_block_swing(b, A)
    t = eps_ratio * N * b
    return min(1.0, 2.0 * math.exp(-2.0 * t * t / (N * c * c)))


def eps_for_confidence(N: int, b: int, A: int, alpha: float = 1e-9) -> float:
    """Smallest ratio-deviation ε guaranteed except with probability alpha."""
    c = per_block_swing(b, A)
    return c * math.sqrt(math.log(2.0 / alpha) / (2.0 * N)) / b


if __name__ == "__main__":
    for N in (10**6, 10**9, 10**12):
        print(f"  N={N:>14,}: ε(α=1e-9) = ±{100*eps_for_confidence(N, 24, 5):.6f} %-points")
