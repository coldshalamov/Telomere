#!/usr/bin/env python3
"""H81 - output whitening versus visible fertility.

H80 found a real source-shaped public-Q target. H81 asks whether a normal
stateless code output preserves that target.

The tradeoff is:

* Entropy coding a Q source gets the Q saving but emits near-uniform code bits.
* Keeping the next visible layer Q-shaped preserves fertility but spends the
  same redundancy as distribution-shaping slack, or stores a raw-length word.
* Public reversible permutations can preserve F, but they do not compress.

This is an exact finite-domain ledger over the H80 public-Q distribution.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H80_PATH = Path(__file__).resolve().with_name("H80-public_q_fertility_lane.py")
_h80_spec = importlib.util.spec_from_file_location("h80_public_q_fertility_lane", H80_PATH)
if _h80_spec is None or _h80_spec.loader is None:
    raise RuntimeError("could not load H80 public-Q fertility lane kernel")
_h80 = importlib.util.module_from_spec(_h80_spec)
sys.modules[_h80_spec.name] = _h80
_h80_spec.loader.exec_module(_h80)


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def min_p_ff(c_star: float, p_of: float) -> float:
    if c_star <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


@dataclass(frozen=True)
class ClassProfile:
    name: str
    fraction: float
    q_mass: float
    mu_f: float
    mu_o: float
    c_star_h7: float
    min_pff_uniform_bg: float


@dataclass(frozen=True)
class RegimeRow:
    cls: str
    regime: str
    visible_next_c: float
    p_ff: float
    p_of: float
    source_gain_bits: float
    visible_shape_cost_bits: float
    net_before_record_costs: float
    maintains_h7: bool
    reading: str


def h7_target_word(domain) -> float:
    return 0.011929 * domain.atoms


def profile_for_indices(domain, name: str, indices: list[int]) -> ClassProfile:
    row = _h80.row_for_indices(domain, indices)
    target_word = h7_target_word(domain)
    c_star = (target_word - row.mu_o) / (row.mu_f - row.mu_o)
    return ClassProfile(
        name=name,
        fraction=row.fraction,
        q_mass=row.q_mass,
        mu_f=row.mu_f,
        mu_o=row.mu_o,
        c_star_h7=c_star,
        min_pff_uniform_bg=min_p_ff(c_star, row.fraction),
    )


def class_profiles(domain) -> list[ClassProfile]:
    return [
        profile_for_indices(domain, "top10", _h80.top_class_indices(domain.scores, 0.10)),
        profile_for_indices(domain, "top25", _h80.top_class_indices(domain.scores, 0.25)),
        profile_for_indices(domain, "F_positive", _h80.positive_class_indices(domain.scores)),
    ]


def regime_rows(domain, profile: ClassProfile) -> list[RegimeRow]:
    raw_bits = domain.raw_bits
    h_q = entropy(domain.q)
    d_q_u = raw_bits - h_q
    # Normalized Q has uniform expected excess D(U||Q), but the Q source itself
    # has D(Q||U) bits of redundancy available.
    source_gain = d_q_u
    f = profile.fraction
    qf = profile.q_mass
    rows: list[RegimeRow] = []

    rows.append(
        RegimeRow(
            cls=profile.name,
            regime="entropy-coded Q",
            visible_next_c=f,
            p_ff=f,
            p_of=f,
            source_gain_bits=source_gain,
            visible_shape_cost_bits=0.0,
            net_before_record_costs=source_gain,
            maintains_h7=f >= profile.c_star_h7,
            reading="compact stream; fertility whitened to uniform class rate",
        )
    )
    rows.append(
        RegimeRow(
            cls=profile.name,
            regime="visible Q-shaped",
            visible_next_c=qf,
            p_ff=qf,
            p_of=qf,
            source_gain_bits=source_gain,
            visible_shape_cost_bits=d_q_u,
            net_before_record_costs=source_gain - d_q_u,
            maintains_h7=qf >= profile.c_star_h7,
            reading="fertility preserved as source law; shaping slack spends source gain",
        )
    )
    rows.append(
        RegimeRow(
            cls=profile.name,
            regime="raw/permutation",
            visible_next_c=qf,
            p_ff=1.0,
            p_of=0.0,
            source_gain_bits=0.0,
            visible_shape_cost_bits=0.0,
            net_before_record_costs=0.0,
            maintains_h7=qf >= profile.c_star_h7,
            reading="reversible visible layer can preserve F, but does not compress",
        )
    )
    return rows


def print_domain(domain) -> None:
    raw_bits = domain.raw_bits
    h_q = entropy(domain.q)
    d_q_u = raw_bits - h_q
    d_u_q = -domain.uniform_mean_score
    print("== output law ledger on exact H80 domain ==")
    print(
        f"B={domain.block_bits}, N={domain.atoms}, K={domain.max_arity}, "
        f"D={domain.depth_bits}, domain={len(domain.q)}"
    )
    print(f"raw visible word bits:          {raw_bits:.6f}")
    print(f"H(Q):                           {h_q:.6f}")
    print(f"D(Q||U) source redundancy:      {d_q_u:.6f}")
    print(f"D(U||Q) uniform Q-code excess:  {d_u_q:.6f}")
    print()


def print_profiles(profiles: list[ClassProfile]) -> None:
    print("== class profiles ==")
    print(
        f"{'class':<12} {'f=U(F)':>9} {'Q(F)':>9} {'mu_F':>9} "
        f"{'mu_O':>9} {'c*_H7':>9} {'pFF need':>9}"
    )
    for profile in profiles:
        print(
            f"{profile.name:<12} {profile.fraction:9.4f} {profile.q_mass:9.4f} "
            f"{profile.mu_f:9.3f} {profile.mu_o:9.3f} "
            f"{profile.c_star_h7:9.4f} {profile.min_pff_uniform_bg:9.4f}"
        )
    print()


def print_regimes(domain, profiles: list[ClassProfile]) -> None:
    print("== recurrence under output regimes ==")
    print(
        f"{'class':<12} {'regime':<17} {'next c':>8} {'pFF':>8} {'pOF':>8} "
        f"{'gain':>8} {'shape':>8} {'net':>8} {'H7?':>5} {'reading'}"
    )
    for profile in profiles:
        for row in regime_rows(domain, profile):
            print(
                f"{row.cls:<12} {row.regime:<17} {row.visible_next_c:8.4f} "
                f"{row.p_ff:8.4f} {row.p_of:8.4f} {row.source_gain_bits:8.3f} "
                f"{row.visible_shape_cost_bits:8.3f} {row.net_before_record_costs:8.3f} "
                f"{'yes' if row.maintains_h7 else 'no':>5} {row.reading}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "H80's public-Q class is a real source-shaped target, but a compact "
        "Q-code does not visibly carry that law forward; it spends the source "
        "redundancy and leaves a near-uniform code stream. Making the next "
        "visible layer Q-shaped again costs D(Q||U), which cancels the finite "
        "source saving before Telomere record costs. Reversible public "
        "permutations can preserve F, but they do not shrink the layer. The "
        "remaining breakthrough target is therefore narrower: find a Telomere "
        "record language whose *native compact syntax* is itself high-Q/fertile, "
        "rather than entropy-coding then reshaping."
    )


def main() -> None:
    domain = _h80.exact_domain()
    profiles = class_profiles(domain)
    print_domain(domain)
    print_profiles(profiles)
    print_regimes(domain, profiles)
    print_reading()


if __name__ == "__main__":
    main()
