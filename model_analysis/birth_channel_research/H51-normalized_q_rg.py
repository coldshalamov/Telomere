#!/usr/bin/env python3
"""H51 - normalized collective-cover reproduction diagnostics.

H44 proved the public normalized-cover accounting:

    Q_raw(x) = sum_{covers c -> x} 2^-L(c)
    Q(x)     = Q_raw(x) / Z
    E_U[-log2 Q(X)] = n + KL(U || Q) >= n

H51 adds the repeated-pass diagnostics used by H49/H50: expected bits, log-rho,
below-raw fraction, and the exact source lift required. This catches the trap
where a variable-length distribution can look interesting in log space while
still having nonnegative expected excess under uniform data.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H29_PATH = ROOT / "model_analysis" / "birth_channel_research" / "H29-cover_equivalence_dp.py"


def load_h29():
    spec = importlib.util.spec_from_file_location("h29_cover_equivalence_dp", H29_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {H29_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H29 = load_h29()


@dataclass(frozen=True)
class Case:
    atoms: int
    block_bits: int
    max_arity: int
    payload_depth: int


DEFAULT_CASES = (
    Case(10, 1, 4, 8),
    Case(12, 1, 4, 8),
    Case(10, 1, 4, 10),
    Case(8, 2, 4, 8),
)


@dataclass(frozen=True)
class QRow:
    case: Case
    raw_bits: int
    coverage: float
    z_mass: float
    avg_bits: float
    excess_bits: float
    avg_log2_rho: float
    geometric_rho: float
    below_raw_fraction: float
    min_bits: float
    max_bits: float
    best_escape_alpha: float
    best_escape_avg_bits: float


def run_case(case: Case) -> QRow:
    raw_bits = case.atoms * case.block_bits
    tables = H29.build_edge_tables(case.block_bits, case.max_arity, case.payload_depth)
    results = [
        H29.score_layer(bits, tables, case.block_bits, case.max_arity)
        for bits in H29.all_bitstrings(raw_bits)
    ]
    summary = H29.summarize(results, raw_bits)
    if summary["coverage"] < 1.0:
        return QRow(
            case,
            raw_bits,
            summary["coverage"],
            summary["total_q_mass"],
            float("inf"),
            float("inf"),
            float("inf"),
            float("inf"),
            0.0,
            float("inf"),
            float("inf"),
            0.0,
            float("inf"),
        )

    z_mass = summary["total_q_mass"]
    bits = [-math.log2(result.q_mass / z_mass) for result in results]
    avg_bits = mean(bits)
    log_rhos = [math.log2(value / raw_bits) for value in bits]
    alpha, mix_avg = H29.best_escape_mixture(results, raw_bits)
    return QRow(
        case=case,
        raw_bits=raw_bits,
        coverage=summary["coverage"],
        z_mass=z_mass,
        avg_bits=avg_bits,
        excess_bits=avg_bits - raw_bits,
        avg_log2_rho=mean(log_rhos),
        geometric_rho=2.0 ** mean(log_rhos),
        below_raw_fraction=sum(1 for value in bits if value < raw_bits) / len(bits),
        min_bits=min(bits),
        max_bits=max(bits),
        best_escape_alpha=alpha,
        best_escape_avg_bits=mix_avg,
    )


def render(rows: list[QRow]) -> str:
    lines = [
        "# Normalized Collective-Cover Reproduction Diagnostics",
        "",
        "Rows enumerate every tiny layer exactly. `avg bits` is the honest",
        "uniform criterion. `avg log2 rho` is shown only as a reproduction",
        "diagnostic; it cannot override expected-length/Kraft accounting.",
        "",
        "| atoms | B | K | D | raw | coverage | Z | avg bits | excess | avg log2 rho | geom rho | below raw | min bits | max bits | escape alpha | escape avg |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        c = row.case
        lines.append(
            f"| {c.atoms} | {c.block_bits} | {c.max_arity} | {c.payload_depth} | "
            f"{row.raw_bits} | {row.coverage:.6f} | {row.z_mass:.8f} | "
            f"{row.avg_bits:.6f} | {row.excess_bits:.6f} | "
            f"{row.avg_log2_rho:.6f} | {row.geometric_rho:.6f} | "
            f"{row.below_raw_fraction:.6f} | {row.min_bits:.6f} | "
            f"{row.max_bits:.6f} | {row.best_escape_alpha:.2f} | "
            f"{row.best_escape_avg_bits:.6f} |"
        )

    best = min(rows, key=lambda row: row.excess_bits)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Smallest uniform excess in these rows: `N={best.case.atoms},B={best.case.block_bits},"
            f"K={best.case.max_arity},D={best.case.payload_depth}` with "
            f"`excess={best.excess_bits:.6f}` bits.",
            "A source drawn from Q can recover that excess and more; uniform data",
            "cannot. If a raw escape mixture chooses `alpha=0`, the public Q prior",
            "is not useful for roughly-all uniform layers at that scale.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atoms", type=int, default=None)
    parser.add_argument("--block-bits", type=int, default=1)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--payload-depth", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = (
        DEFAULT_CASES
        if args.atoms is None
        else (Case(args.atoms, args.block_bits, args.max_arity, args.payload_depth),)
    )
    print(render([run_case(case) for case in cases]))


if __name__ == "__main__":
    main()
