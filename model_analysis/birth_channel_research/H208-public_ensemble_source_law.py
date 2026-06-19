#!/usr/bin/env python3
"""H208 - public ensemble / source-law bridge for packed populations.

H207 says one packed visible-population family can tie only before mode/fallback.
This kernel tests the natural source-law mutation: use many public generated
families/modes, or assume the source has high probability mass on the generated
ensemble.

The ledger separates:

* paid mode: support gain log2(E) is paid by the mode rank;
* hidden mode: apparent gain is exactly the unpaid mode selector;
* root-derived mode: no mode bill, but no extra support rank;
* all-data fallback: leftover Kraft expands uniform data;
* source-shaped use: a real gain only if the source mass on generated support
  exceeds a computed break-even probability.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def logadd2(a: float, b: float) -> float:
    if math.isinf(a) and a < 0.0:
        return b
    if math.isinf(b) and b < 0.0:
        return a
    m = max(a, b)
    return m + math.log2((2.0 ** (a - m)) + (2.0 ** (b - m)))


def entropy_mixture(out_bits: int, support_bits: float, alpha: float) -> tuple[float, float, float]:
    """Entropy of alpha*Uniform(reachable) + (1-alpha)*Uniform(all N-bit)."""

    if alpha <= 0.0:
        return float(out_bits), 0.0, 1.0
    if alpha >= 1.0:
        return float(support_bits), 1.0, 0.0
    rho = 0.0 if support_bits - out_bits < -1070 else 2.0 ** (support_bits - out_bits)
    mass_in = alpha + (1.0 - alpha) * rho
    mass_out = (1.0 - alpha) * (1.0 - rho)
    lp_in = logadd2(math.log2(alpha) - support_bits, math.log2(1.0 - alpha) - out_bits)
    lp_out = math.log2(1.0 - alpha) - out_bits
    return -mass_in * lp_in - mass_out * lp_out, mass_in, mass_out


def log2_one_minus(q: float) -> float:
    if q >= 1.0:
        return -math.inf
    return math.log1p(-q) / math.log(2.0)


@dataclass(frozen=True)
class Row:
    ensemble: int
    mode_bits: float
    extra_mode_bits: int
    population_size: int
    root_bits: int
    arity: int
    passes: int
    atom_bits: int
    out_bits: int
    root_rank: int
    ensemble_support_bits: float
    paid_mode_bits: float
    paid_mode_net: float
    hidden_mode_net: float
    root_derived_net: float
    fallback_delta: float
    source_break_even: float


@dataclass(frozen=True)
class PriorRow:
    name: str
    population_size: int
    arity: int
    root_bits: int
    atom_bits: int
    passes: int
    out_bits: int
    support_bits: int
    native_paid_bits: int
    delta: int
    q: float
    raw_overhead: float
    threshold_alpha: float


@dataclass(frozen=True)
class AlphaRow:
    name: str
    alpha: float
    cross_entropy: float
    apparent_gain: float
    source_tax: float
    paid_net_after_tax: float


def source_break_even(
    *,
    out_bits: int,
    generated_len: float,
    fallback_delta: float,
) -> float:
    gain_if_generated = out_bits - generated_len
    if gain_if_generated <= 0.0:
        return math.inf
    return fallback_delta / (gain_if_generated + fallback_delta)


def row(
    *,
    ensemble: int,
    population_size: int,
    root_bits: int,
    arity: int,
    passes: int,
    atom_bits: int,
    extra_mode_bits: int,
) -> Row:
    if ensemble < 1:
        raise ValueError("ensemble must be positive")
    mode_rank = math.log2(ensemble)
    mode_bits = mode_rank + extra_mode_bits
    out_bits = population_size * (arity**passes) * atom_bits
    root_rank = population_size * root_bits
    support_bits = root_rank + mode_rank
    paid_len = root_rank + mode_bits
    paid_mode_net = support_bits - paid_len
    hidden_mode_net = support_bits - root_rank
    root_derived_net = 0.0
    q = 2.0 ** (-extra_mode_bits) if extra_mode_bits > 0 else 1.0
    fallback_delta = math.inf if q >= 1.0 else -math.log2(1.0 - q)
    p_star = source_break_even(out_bits=out_bits, generated_len=paid_len, fallback_delta=fallback_delta)
    return Row(
        ensemble=ensemble,
        mode_bits=mode_bits,
        extra_mode_bits=extra_mode_bits,
        population_size=population_size,
        root_bits=root_bits,
        arity=arity,
        passes=passes,
        atom_bits=atom_bits,
        out_bits=out_bits,
        root_rank=root_rank,
        ensemble_support_bits=support_bits,
        paid_mode_bits=paid_len,
        paid_mode_net=paid_mode_net,
        hidden_mode_net=hidden_mode_net,
        root_derived_net=root_derived_net,
        fallback_delta=fallback_delta,
        source_break_even=p_star,
    )


def prior_row(
    *,
    name: str,
    population_size: int,
    arity: int,
    root_bits: int,
    atom_bits: int,
    passes: int,
) -> PriorRow:
    record_bits = costs.record_cost_for_payload_width(arity, root_bits)
    support_bits = population_size * root_bits
    native_paid = 1 + population_size * record_bits
    out_bits = population_size * (arity**passes) * atom_bits
    delta = native_paid - support_bits
    q = 2.0 ** (-delta)
    raw_overhead = -log2_one_minus(q)
    threshold = raw_overhead / (out_bits - native_paid + raw_overhead)
    return PriorRow(
        name=name,
        population_size=population_size,
        arity=arity,
        root_bits=root_bits,
        atom_bits=atom_bits,
        passes=passes,
        out_bits=out_bits,
        support_bits=support_bits,
        native_paid_bits=native_paid,
        delta=delta,
        q=q,
        raw_overhead=raw_overhead,
        threshold_alpha=threshold,
    )


def alpha_row(prior: PriorRow, alpha: float) -> AlphaRow:
    left = log2_one_minus(prior.q)
    entropy, mass_in, mass_out = entropy_mixture(prior.out_bits, prior.support_bits, alpha)
    lq_in = logadd2(-prior.native_paid_bits, left - prior.out_bits)
    lq_out = left - prior.out_bits
    cross_entropy = -mass_in * lq_in - mass_out * lq_out
    return AlphaRow(
        name=prior.name,
        alpha=alpha,
        cross_entropy=cross_entropy,
        apparent_gain=prior.out_bits - cross_entropy,
        source_tax=prior.out_bits - entropy,
        paid_net_after_tax=entropy - cross_entropy,
    )


def print_rows(args: argparse.Namespace) -> None:
    ensembles = parse_int_list(args.ensemble, [1, 2, 16, 256, 65536])
    extras = parse_int_list(args.extra_mode_bits, [0, 1, 2, 4, 8])
    print("== H208 public ensemble / source-law bridge ==")
    print("paid mode cancels ensemble support; hidden mode is an unpaid selector.")
    print(
        f"{'E':>7} {'extra':>5} {'M':>3} {'G':>3} {'N':>9} {'R':>5} "
        f"{'supp':>10} {'paid':>10} {'paidNet':>8} {'hidden':>8} "
        f"{'fbDelta':>9} {'p*source':>10}"
    )
    rows = [
        row(
            ensemble=e,
            population_size=args.population_size,
            root_bits=args.root_bits,
            arity=args.arity,
            passes=args.passes,
            atom_bits=args.atom_bits,
            extra_mode_bits=extra,
        )
        for e in ensembles
        for extra in extras
    ]
    rows.sort(key=lambda item: (item.extra_mode_bits, item.ensemble))
    for item in rows[: args.limit]:
        print(
            f"{item.ensemble:7d} {int(item.mode_bits - math.log2(item.ensemble)):5d} "
            f"{item.population_size:3d} {item.root_bits:3d} {item.out_bits:9d} "
            f"{item.root_rank:5d} {fmt(item.ensemble_support_bits):>10} "
            f"{fmt(item.paid_mode_bits):>10} {fmt(item.paid_mode_net):>8} "
            f"{fmt(item.hidden_mode_net):>8} {fmt(item.fallback_delta):>9} "
            f"{fmt(item.source_break_even):>10}"
        )


def print_prior(args: argparse.Namespace) -> None:
    alphas = [float(value) for value in args.alpha.split(",")]
    priors = [
        prior_row(
            name="H205-single-high-growth",
            population_size=1,
            arity=5,
            root_bits=16,
            atom_bits=32,
            passes=6,
        ),
        prior_row(
            name="H206-best-finite-miss",
            population_size=1,
            arity=2,
            root_bits=1,
            atom_bits=32,
            passes=6,
        ),
        prior_row(
            name="H205-visible-population",
            population_size=32,
            arity=5,
            root_bits=16,
            atom_bits=32,
            passes=6,
        ),
    ]
    print()
    print("== normalized visible-population Kraft prior ==")
    print("Q gives reachable outputs their witness mass and spends leftover Kraft on raw fallback.")
    print(
        f"{'name':<28} {'N':>9} {'s':>5} {'c':>6} {'delta':>6} "
        f"{'q':>10} {'rawOH':>10} {'alpha*':>10}"
    )
    for prior in priors:
        print(
            f"{prior.name:<28} {prior.out_bits:9d} {prior.support_bits:5d} "
            f"{prior.native_paid_bits:6d} {prior.delta:6d} "
            f"{fmt(prior.q):>10} {fmt(prior.raw_overhead):>10} "
            f"{fmt(prior.threshold_alpha):>10}"
        )
    print()
    print(f"{'name':<28} {'alpha':>10} {'CE':>13} {'gain':>12} {'srcTax':>12} {'paidNet':>12}")
    for prior in priors:
        for alpha in alphas:
            item = alpha_row(prior, alpha)
            print(
                f"{item.name:<28} {fmt(item.alpha):>10} {fmt(item.cross_entropy):>13} "
                f"{fmt(item.apparent_gain):>12} {fmt(item.source_tax):>12} "
                f"{fmt(item.paid_net_after_tax):>12}"
            )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A public ensemble adds at most log2(E) support bits.  If the decoder")
    print("must know the selected family, those bits are paid as mode rank.  If")
    print("the root bits derive the family, each root string still names only one")
    print("family and support rank does not increase.  If the family is hidden,")
    print("the apparent gain is exactly the hidden selector.  Source-shaped gains")
    print("are valid only when the generated-ensemble source mass exceeds p*.")
    print("After charging the source law, paid net is H(P)-CE(P,Q) = -D(P||Q) <= 0.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ensemble", action="append", default=[])
    parser.add_argument("--extra-mode-bits", action="append", default=[])
    parser.add_argument("--population-size", type=int, default=32)
    parser.add_argument("--root-bits", type=int, default=16)
    parser.add_argument("--arity", type=int, default=5)
    parser.add_argument("--passes", type=int, default=6)
    parser.add_argument("--atom-bits", type=int, default=32)
    parser.add_argument("--alpha", default="0,1e-12,1e-9,1e-6,1e-3,1")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    print_rows(args)
    print_prior(args)
    print_theorem()


if __name__ == "__main__":
    main()
