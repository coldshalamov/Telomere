#!/usr/bin/env python3
"""H77 - self-induced fertility / codec-output source kernel.

This tests the last constructive-looking loophole:

    "Maybe Telomere's own public record/literal language creates the source
    structure needed for the next pass, so the recursion is self-fertile
    rather than externally structure-dependent."

The kernel is deliberately abstract. A public high-fertility class F has
uniform mass f and per-state Q lift a. A source must visit F with probability
c >= c* to beat a target gap. Recursion additionally needs:

    c_{t+1} = c_t p_FF + (1-c_t) p_OF >= c*

If codec outputs are whitened / unrestricted code bits, then p_FF is just f.
Forcing outputs into F is a public lane restriction and costs:

    lane_loss = -log2(1 - (1-f)^d)

with d-choice routing. This is the same supply-loss currency as public lanes.
"""

from __future__ import annotations

import math
import sys
import importlib.util
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)
build_edge_weights = _h74.build_edge_weights
dp_mass_for_word = _h74.dp_mass_for_word


def source_threshold(target_bits: float, f_mass: float, q_lift: float) -> float:
    if not 0.0 < f_mass < 1.0:
        raise ValueError("f_mass must be in (0,1)")
    if not 0.0 < q_lift < 1.0 / f_mass:
        raise ValueError("q_lift must leave positive complement mass")
    complement_lift = (1.0 - f_mass * q_lift) / (1.0 - f_mass)
    score_f = math.log2(q_lift)
    score_o = math.log2(complement_lift)
    return (target_bits - score_o) / (score_f - score_o)


def expected_uniform_score(f_mass: float, q_lift: float) -> float:
    complement_lift = (1.0 - f_mass * q_lift) / (1.0 - f_mass)
    return f_mass * math.log2(q_lift) + (1.0 - f_mass) * math.log2(complement_lift)


def min_p_ff(c_star: float, p_of: float) -> float:
    if c_star <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


def lane_hit_fraction(f_mass: float, choices: int) -> float:
    return 1.0 - (1.0 - f_mass) ** choices


def lane_loss(f_mass: float, choices: int) -> float:
    hit = lane_hit_fraction(f_mass, choices)
    return -math.log2(hit)


@dataclass(frozen=True)
class Target:
    name: str
    target_bits_per_atom: float


@dataclass(frozen=True)
class FertilityRow:
    target: str
    f_mass: float
    q_lift: float
    c_star: float
    uniform_c0: float
    uniform_score: float
    random_p_ff: float
    min_p_ff_with_background: float
    min_p_ff_closed: float
    natural_next_c_at_threshold: float
    single_lane_loss: float
    d16_lane_loss: float
    d64_lane_loss: float
    verdict: str


@dataclass(frozen=True)
class ExactQRow:
    target: str
    block_bits: int
    atoms: int
    max_arity: int
    depth_bits: int
    f_mass: float
    mu_f: float
    mu_o: float
    c_star: float
    uniform_c0: float
    random_p_ff: float
    min_p_ff_with_background: float
    identity_p_ff: float
    d16_lane_loss: float
    verdict: str


TARGETS = [
    Target("H59 atom miss", 0.053411 / 384.0),
    Target("H58 atom miss", 0.229195 / 384.0),
    Target("H7 atom miss", 0.011929),
]


def exact_q_scores(
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> list[float]:
    domain = 1 << (block_bits * atoms)
    edge_weights, edge_maxes = build_edge_weights(block_bits, max_arity, depth_bits, seed)
    q_raw = [
        dp_mass_for_word(word, atoms, block_bits, max_arity, edge_weights, edge_maxes)[0]
        for word in range(domain)
    ]
    z_mass = sum(q_raw)
    if z_mass <= 0.0:
        raise RuntimeError("zero Q mass")
    uniform_probability = 1.0 / domain
    scores: list[float] = []
    for value in q_raw:
        if value <= 0.0:
            scores.append(float("-inf"))
        else:
            q_value = value / z_mass
            scores.append(math.log2(q_value / uniform_probability))
    return scores


def exact_q_rows(
    block_bits: int = 1,
    atoms: int = 12,
    max_arity: int = 6,
    depth_bits: int = 8,
    seed: int = 75,
    top_fraction: float = 0.10,
) -> list[ExactQRow]:
    scores = exact_q_scores(block_bits, atoms, max_arity, depth_bits, seed)
    domain = len(scores)
    f_count = max(1, round(top_fraction * domain))
    order = sorted(range(domain), key=lambda index: scores[index], reverse=True)
    f_set = set(order[:f_count])
    f_mass = f_count / domain
    mu_f = sum(scores[index] for index in f_set) / f_count
    o_count = domain - f_count
    mu_o = sum(scores[index] for index in range(domain) if index not in f_set) / o_count
    result: list[ExactQRow] = []
    for target in TARGETS:
        c_star = (target.target_bits_per_atom - mu_o) / (mu_f - mu_o)
        required = min_p_ff(c_star, f_mass)
        random_p = f_mass
        identity_p = 1.0
        if f_mass >= c_star:
            verdict = "uniform starts at threshold"
        elif random_p >= required:
            verdict = "whitened output self-renews"
        else:
            verdict = "needs forced retention or source"
        result.append(
            ExactQRow(
                target=target.name,
                block_bits=block_bits,
                atoms=atoms,
                max_arity=max_arity,
                depth_bits=depth_bits,
                f_mass=f_mass,
                mu_f=mu_f,
                mu_o=mu_o,
                c_star=c_star,
                uniform_c0=f_mass,
                random_p_ff=random_p,
                min_p_ff_with_background=required,
                identity_p_ff=identity_p,
                d16_lane_loss=lane_loss(f_mass, 16),
                verdict=verdict,
            )
        )
    return result


def row_for(target: Target, f_mass: float, q_lift: float) -> FertilityRow:
    c_star = source_threshold(target.target_bits_per_atom, f_mass, q_lift)
    p_of = f_mass
    random_p = f_mass
    required = min_p_ff(c_star, p_of)
    natural_next = c_star * random_p + (1.0 - c_star) * p_of
    if f_mass >= c_star:
        verdict = "uniform starts at threshold"
    elif random_p >= required:
        verdict = "random codec output self-renews"
    else:
        verdict = "needs forced lane/source retention"
    return FertilityRow(
        target=target.name,
        f_mass=f_mass,
        q_lift=q_lift,
        c_star=c_star,
        uniform_c0=f_mass,
        uniform_score=expected_uniform_score(f_mass, q_lift),
        random_p_ff=random_p,
        min_p_ff_with_background=required,
        min_p_ff_closed=min_p_ff(c_star, 0.0),
        natural_next_c_at_threshold=natural_next,
        single_lane_loss=lane_loss(f_mass, 1),
        d16_lane_loss=lane_loss(f_mass, 16),
        d64_lane_loss=lane_loss(f_mass, 64),
        verdict=verdict,
    )


def rows() -> list[FertilityRow]:
    result: list[FertilityRow] = []
    for target in TARGETS:
        for f_mass, q_lift in ((0.10, 2.0), (0.10, 4.0), (0.01, 8.0)):
            result.append(row_for(target, f_mass, q_lift))
    return result


def print_rows() -> None:
    print("== self-induced fertility rows ==")
    print("Uniform c0=f is the no-external-structure starting point.")
    print(
        f"{'target':<15} {'f':>6} {'a':>5} {'c*':>8} {'c0':>6} "
        f"{'pFF rand':>9} {'pFF need':>9} {'next c':>8} "
        f"{'lane d1':>8} {'lane d16':>9} {'verdict':<34}"
    )
    for row in rows():
        if (row.f_mass, row.q_lift) in ((0.10, 2.0), (0.01, 8.0)):
            print(
                f"{row.target:<15} {row.f_mass:6.2f} {row.q_lift:5.1f} "
                f"{row.c_star:8.4f} {row.uniform_c0:6.3f} "
                f"{row.random_p_ff:9.4f} {row.min_p_ff_with_background:9.4f} "
                f"{row.natural_next_c_at_threshold:8.4f} "
                f"{row.single_lane_loss:8.3f} {row.d16_lane_loss:9.3f} "
                f"{row.verdict:<34}"
            )
    print()


def print_uniform_scores() -> None:
    print("== uniform negative controls ==")
    print("Uniform score is <=0 by KL conservation; c0=f is below c* in rows that need gain.")
    print(f"{'f':>6} {'a':>5} {'E_U score':>12}")
    for f_mass, q_lift in ((0.10, 2.0), (0.10, 4.0), (0.01, 8.0)):
        print(f"{f_mass:6.2f} {q_lift:5.1f} {expected_uniform_score(f_mass, q_lift):12.6f}")
    print()


def print_exact_q_rows() -> None:
    print("== exact H74 high-Q class rows ==")
    print("F is the top 10% by exact latent-Q score in B=1,N=12,K=6,D=8.")
    print(
        f"{'target':<15} {'f':>6} {'mu_F':>9} {'mu_O':>9} {'c*':>8} "
        f"{'pFF rand':>9} {'pFF need':>9} {'lane d16':>9} {'verdict':<34}"
    )
    for row in exact_q_rows():
        print(
            f"{row.target:<15} {row.f_mass:6.3f} {row.mu_f:9.3f} "
            f"{row.mu_o:9.3f} {row.c_star:8.4f} {row.random_p_ff:9.4f} "
            f"{row.min_p_ff_with_background:9.4f} {row.d16_lane_loss:9.3f} "
            f"{row.verdict:<34}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("A self-induced source law would need two things:")
    print("  1. uniform/all-data inputs must enter the fertile class often enough;")
    print("  2. encoded outputs must stay fertile often enough over arbitrary passes.")
    print()
    print("In the public high-Q model, uniform starts at c0=f. The target thresholds")
    print("above f are source-shaped; they are not reached by arbitrary uniform data.")
    print("Unrestricted compressed bits behave like a whitened code stream, so p_FF")
    print("is only f. Forcing p_FF higher means restricting output placement to F,")
    print("which pays lane/supply loss. That may be useful for source-shaped tests,")
    print("but it is not a structure-free all-data escape.")


def main() -> None:
    print_rows()
    print_uniform_scores()
    print_exact_q_rows()
    print_reading()


if __name__ == "__main__":
    main()
