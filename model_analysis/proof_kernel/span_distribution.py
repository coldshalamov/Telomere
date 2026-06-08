"""Span distributions over the current Telomere entry layer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class SpanBucket:
    span_bits: int
    probability: float
    opportunity_multiplier: float


def _convolve(
    left: dict[int, tuple[float, float]],
    right: dict[int, tuple[float, float]],
    prune: float,
) -> dict[int, tuple[float, float]]:
    """Convolve length PMFs while carrying E[variant_score product | length]."""

    prob: dict[int, float] = defaultdict(float)
    weighted_score: dict[int, float] = defaultdict(float)
    for l_len, (l_prob, l_score) in left.items():
        for r_len, (r_prob, r_score) in right.items():
            p = l_prob * r_prob
            if p <= prune:
                continue
            length = l_len + r_len
            prob[length] += p
            weighted_score[length] += p * l_score * r_score
    return {
        length: (p, weighted_score[length] / p)
        for length, p in prob.items()
        if p > prune
    }


def span_distributions(
    length_pmf: dict[int, float],
    variant_scores: dict[int, float],
    arity_cap: int,
    prune: float = 1e-14,
) -> dict[int, list[SpanBucket]]:
    """Return exact a-fold independent span distributions for arity 1..A."""

    current = {
        length: (prob, max(1.0, variant_scores.get(length, 1.0)))
        for length, prob in length_pmf.items()
        if prob > prune
    }
    out: dict[int, list[SpanBucket]] = {}
    layer = current
    for arity in range(1, arity_cap + 1):
        out[arity] = [
            SpanBucket(length, prob, score)
            for length, (prob, score) in sorted(layer.items())
            if prob > prune
        ]
        if arity < arity_cap:
            layer = _convolve(layer, current, prune)
    return out


def validate_span_histogram() -> dict[str, float | int]:
    """Explicit multiset enumeration must match the histogram convolution."""

    lengths = [7, 7, 10, 12]
    scores = {7: 1.25, 10: 1.5, 12: 1.0}
    pmf = {7: 0.5, 10: 0.25, 12: 0.25}
    dist = span_distributions(pmf, scores, 3)

    explicit: dict[int, tuple[float, float]] = {}
    total = len(lengths) ** 3
    for a in lengths:
        for b in lengths:
            for c in lengths:
                length = a + b + c
                score = scores[a] * scores[b] * scores[c]
                prob, weighted = explicit.get(length, (0.0, 0.0))
                explicit[length] = (prob + 1 / total, weighted + score / total)

    for bucket in dist[3]:
        prob, weighted = explicit[bucket.span_bits]
        explicit_score = weighted / prob
        if abs(bucket.probability - prob) > 1e-12:
            raise AssertionError((bucket.span_bits, bucket.probability, prob))
        if abs(bucket.opportunity_multiplier - explicit_score) > 1e-12:
            raise AssertionError((bucket.span_bits, bucket.opportunity_multiplier, explicit_score))
    return {"arity": 3, "explicit_tuples": total, "span_buckets": len(dist[3])}


if __name__ == "__main__":
    print(validate_span_histogram())
