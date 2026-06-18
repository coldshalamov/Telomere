#!/usr/bin/env python3
"""Cover-layout entropy ledger for sparse bundle records.

This is an optimistic lower-bound charge for the H3 finite-K bundle branch.
Instead of charging a visible literal marker on every uncovered atom, it charges
only the information needed to place non-overlapping bundle records among raw
literal atoms.

For a fixed arity ``a`` and ``m`` selected bundle intervals in ``N`` atoms, the
number of layouts is:

    C(N - (a - 1) * m, m)

because the packed token stream contains ``m`` bundle tokens and
``N - a*m`` literal atom tokens. Any parseable sparse codec must convey at
least this much layout information unless the layout is decoder-derived by a
public invariant.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H3_PATH = Path(__file__).with_name("H3-bundle_finite_k_ledger.py")


def load_h3() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h3_bundle_finite_k_ledger", H3_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H3 kernel from {H3_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H3 = load_h3()
LedgerRow = H3.LedgerRow
default_passes = H3.default_passes
evaluate = H3.evaluate


@dataclass(frozen=True)
class CoverRow:
    base: LedgerRow
    cover_entropy_per_atom: float
    layout_only_gain_per_atom: float
    exact_atoms: int
    exact_selected_records: int


def binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def asymptotic_cover_entropy_per_atom(records_per_atom: float, arity: int) -> float:
    if records_per_atom <= 0.0:
        return 0.0
    cap = 1.0 / arity
    if records_per_atom >= cap:
        return 0.0
    token_rate = 1.0 - (arity - 1) * records_per_atom
    bundle_token_fraction = records_per_atom / token_rate
    return token_rate * binary_entropy(bundle_token_fraction)


def exact_cover_entropy_per_atom(records_per_atom: float, arity: int, atoms: int) -> tuple[float, int]:
    selected = min(atoms // arity, max(0, round(records_per_atom * atoms)))
    token_count = atoms - (arity - 1) * selected
    if selected <= 0 or selected >= token_count:
        return 0.0, selected
    return math.log2(math.comb(token_count, selected)) / atoms, selected


def evaluate_cover(
    block_bits: int,
    literal_marker_bits: int,
    arity: int,
    passes: int,
    min_raw_savings: float,
    atoms: int,
) -> CoverRow:
    base = evaluate(block_bits, literal_marker_bits, arity, passes, min_raw_savings)
    exact_entropy, exact_selected = exact_cover_entropy_per_atom(
        base.selected_records_per_atom,
        arity,
        atoms,
    )
    asymptotic_entropy = asymptotic_cover_entropy_per_atom(base.selected_records_per_atom, arity)
    # Use the larger of rounded finite-N and asymptotic entropy so the table is
    # not accidentally optimistic due to rounding tiny selected counts to zero.
    cover_entropy = max(exact_entropy, asymptotic_entropy)
    return CoverRow(
        base=base,
        cover_entropy_per_atom=cover_entropy,
        layout_only_gain_per_atom=base.optimistic_gain_per_atom - cover_entropy,
        exact_atoms=atoms,
        exact_selected_records=exact_selected,
    )


def render(rows: list[CoverRow], block_bits: int, literal_marker_bits: int, min_raw_savings: float) -> str:
    lines = [
        "# Cover-Layout Entropy Ledger",
        "",
        f"`B={block_bits}`, structural literal marker bits in matched targets = "
        f"`{literal_marker_bits}`, minimum raw savings per seed record = `{min_raw_savings}`.",
        "",
        "This table keeps H3's optimistic bundle hit model and replaces the",
        "per-uncovered-literal marker charge with the minimum cover-layout",
        "entropy `log2 C(N-(a-1)m,m)`. It is therefore an upper bound on what a",
        "real sparse mixed codec could do; finite-file headers, exact arithmetic",
        "coding overhead, literal token syntax, and any extra salt/open costs are",
        "not charged.",
        "",
        "| arity | passes | hit p/window | selected rec/atom | coverage | optimistic gain/atom | cover entropy/atom | layout-only gain/atom | H3 charged gain/atom |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        base = row.base
        lines.append(
            f"| {base.arity} | {base.passes} | {base.hit_probability:.6g} | "
            f"{base.selected_records_per_atom:.6g} | {base.coverage:.6g} | "
            f"{base.optimistic_gain_per_atom:.6g} | "
            f"{row.cover_entropy_per_atom:.6g} | "
            f"{row.layout_only_gain_per_atom:.6g} | "
            f"{base.charged_gain_per_atom:.6g} |"
        )
    best = max(rows, key=lambda row: row.layout_only_gain_per_atom)
    base = best.base
    lines.extend(
        [
            "",
            "## Best Layout-Only Row",
            "",
            f"`arity={base.arity}, passes={base.passes}` gives "
            f"`{best.layout_only_gain_per_atom:.6g}` bits/input atom after the",
            "minimum cover-layout charge. Since this is still an optimistic",
            "lower-bound charge for sparse placement, a negative value rules out",
            "rescuing H3 by merely replacing literal markers with a better cover",
            "grammar.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=8)
    parser.add_argument("--literal-marker-bits", type=int, default=3)
    parser.add_argument("--min-raw-savings", type=float, default=2.0)
    parser.add_argument("--arities", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--passes", type=int, nargs="+", default=default_passes())
    parser.add_argument("--atoms", type=int, default=4096)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        evaluate_cover(
            args.block_bits,
            args.literal_marker_bits,
            arity,
            passes,
            args.min_raw_savings,
            args.atoms,
        )
        for arity in args.arities
        for passes in args.passes
    ]
    rows.sort(key=lambda row: (row.base.arity, row.base.passes))
    print(render(rows, args.block_bits, args.literal_marker_bits, args.min_raw_savings))


if __name__ == "__main__":
    main()
