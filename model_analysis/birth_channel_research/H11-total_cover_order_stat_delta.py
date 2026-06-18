#!/usr/bin/env python3
"""Public selected-order-statistic delta law for Total-Cover.

H7's raw first-hit law was the best paid delta model so far. H11 tests one
final low-dimensional idea before this lane becomes table-shaped: model the
selected witness width as the minimum of ``m_eff`` public raw first-hit draws.

For a raw first-hit width random variable W:

    P_sel(W=w | min(W_1..W_m) <= D, context)
        = (S_raw(w-1)^m - S_raw(w)^m) / (1 - S_raw(D)^m)

where ``S_raw(w)=P_raw(W>w)`` and ``m=m_eff(context)`` is a frozen public
function of decoder-visible state such as remaining atoms and arity.

This is stateless only if the law/profile is frozen. Choosing the best law per
file or using the encoder's actual unchosen alternatives would be metadata.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402
from total_cover_public_model_kernel import Cover, selected_rank_bits  # noqa: E402


H7_PATH = Path(__file__).with_name("H7-total_cover_parametric_delta.py")


def load_h7() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h7_total_cover_parametric_delta", H7_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H7 kernel from {H7_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H7 = load_h7()
LN2 = math.log(2.0)


@dataclass(frozen=True)
class EffLaw:
    name: str
    kind: str
    value: float = 1.0

    def m_eff(self, remaining: int, arity: int, max_arity: int) -> float:
        if self.kind == "constant":
            return max(1.0, self.value)
        if self.kind == "legal":
            return max(1.0, float(min(max_arity, remaining)))
        if self.kind == "sqrt_legal":
            return max(1.0, math.sqrt(float(min(max_arity, remaining))))
        if self.kind == "arity":
            return max(1.0, float(arity))
        if self.kind == "sqrt_arity":
            return max(1.0, math.sqrt(float(arity)))
        if self.kind == "tiles":
            return max(1.0, math.ceil(remaining / max(1, arity)))
        if self.kind == "sqrt_tiles":
            return max(1.0, math.sqrt(math.ceil(remaining / max(1, arity))))
        raise ValueError(self.kind)


@dataclass(frozen=True)
class ArityModel:
    counts: dict[int, Counter[int]]
    max_arity: int
    alpha: float


@dataclass(frozen=True)
class LawRow:
    law: EffLaw
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    rank_bits_per_record: float
    arity_bits_per_record: float
    delta_bits_per_record: float


def logaddexp(a: float, b: float) -> float:
    if a == float("-inf"):
        return b
    if b == float("-inf"):
        return a
    if b > a:
        a, b = b, a
    return a + math.log1p(math.exp(b - a))


@lru_cache(maxsize=None)
def raw_survival_logprobs(target_bits: int, frontier: int) -> tuple[float, ...]:
    """Return unconditioned logs of S(w)=P_raw(W>w) for w=0..frontier."""

    log_one_minus_q = math.log1p(-math.ldexp(1.0, -target_bits))
    return tuple(
        H7.payload_width_count_le(width) * log_one_minus_q
        for width in range(frontier + 1)
    )


def selected_width_logprob(target_bits: int, width: int, frontier: int, m_eff: float) -> float:
    if width < 1 or width > frontier:
        return float("-inf")
    survival = raw_survival_logprobs(target_bits, frontier)
    log_prev = survival[width - 1]
    log_next = survival[width]
    a = m_eff * log_prev if log_prev != float("-inf") else float("-inf")
    b = m_eff * log_next if log_next != float("-inf") else float("-inf")
    log_mass = H7.logsubexp(a, b)
    log_legal = H7.logsubexp(0.0, m_eff * survival[frontier])
    if log_legal == float("-inf"):
        return float("-inf")
    return log_mass - log_legal


def delta_bits_for(law: EffLaw, remaining: int, arity: int, max_arity: int, target_bits: int, width: int, frontier: int) -> float:
    m_eff = law.m_eff(remaining, arity, max_arity)
    return -selected_width_logprob(target_bits, width, frontier, m_eff) / LN2


def arity_cost(model: ArityModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def code_cost(
    edge: EdgeSample,
    arity: int,
    remaining: int,
    model: ArityModel,
    law: EffLaw,
    max_arity: int,
    frontier: int,
    rank_code: str,
) -> float:
    record = SelectedRecord(
        arity=arity,
        rank=edge.rank,
        target_bits=edge.target_bits,
        lotus_payload_width=edge.lotus_payload_width,
        local_payload_bits=edge.local_payload_bits,
        cost_bits=0.0,
    )
    return (
        selected_rank_bits(record, rank_code)
        + arity_cost(model, remaining, arity)
        + delta_bits_for(law, remaining, arity, max_arity, edge.target_bits, edge.lotus_payload_width, frontier)
    )


def cover_with_law(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
    model: ArityModel,
    law: EffLaw,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity or edge.lotus_payload_width > frontier:
                continue
            cost = code_cost(edge, arity, remaining, model, law, max_arity, frontier, rank_code)
            if cost == float("inf"):
                continue
            candidate = base + cost
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, cost)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())
    cursor = atoms
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, cost = entry
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=cost,
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms] + flush_bits, tuple(records))


def fit_arity_model(covers: list[Cover], max_arity: int, alpha: float) -> ArityModel:
    counts: dict[int, Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            counts.setdefault(remaining, Counter())[record.arity] += 1
            consumed += record.arity
    return ArityModel(counts, max_arity, alpha)


def train_model(
    train_samples: list[list[list[EdgeSample]]],
    max_arity: int,
    frontier: int,
    law: EffLaw,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> tuple[ArityModel, list[Cover]]:
    model = ArityModel({}, max_arity, alpha)
    covers: list[Cover] = []
    for _ in range(iterations):
        covers = [
            cover_with_law(trial, max_arity, frontier, model, law, flush_bits, rank_code)
            for trial in train_samples
        ]
        model = fit_arity_model(covers, max_arity, alpha)
    return model, covers


def gain(covers: list[Cover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    law: EffLaw,
    model: ArityModel,
    train_covers: list[Cover],
    eval_covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rank_code: str,
    atoms: int,
) -> LawRow:
    covered = [cover for cover in eval_covers if cover.covered]
    if not covered:
        return LawRow(law, gain(train_covers, block_bits, atoms), float("-inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    eval_gain = gain(covered, block_bits, atoms)
    records_per_atom = mean(len(cover.records) / atoms for cover in covered)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    all_records = [record for cover in covered for record in cover.records]
    rank_bits = [selected_rank_bits(record, rank_code) for record in all_records]
    arity_bits = []
    delta_bits = []
    for cover in covered:
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_bits.append(arity_cost(model, remaining, record.arity))
            delta_bits.append(
                delta_bits_for(
                    law,
                    remaining,
                    record.arity,
                    max_arity,
                    record.target_bits,
                    record.lotus_payload_width,
                    frontier,
                )
            )
            consumed += record.arity
    return LawRow(
        law=law,
        train_gain_per_atom=gain(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in all_records),
        avg_width=mean(record.lotus_payload_width for record in all_records),
        rank_bits_per_record=mean(rank_bits),
        arity_bits_per_record=mean(arity_bits),
        delta_bits_per_record=mean(delta_bits),
    )


def default_laws(constants: list[float], include_context_laws: bool) -> list[EffLaw]:
    laws = [EffLaw(f"m{value:g}", "constant", value) for value in constants]
    if not include_context_laws:
        return laws
    laws.extend(
        [
            EffLaw("legal", "legal"),
            EffLaw("sqrt_legal", "sqrt_legal"),
            EffLaw("arity", "arity"),
            EffLaw("sqrt_arity", "sqrt_arity"),
            EffLaw("tiles", "tiles"),
            EffLaw("sqrt_tiles", "sqrt_tiles"),
        ]
    )
    return laws


def render(rows: list[LawRow], selected: LawRow, block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Selected-Order-Statistic Delta Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Delta law treats the selected width as the minimum of `m_eff` public raw",
        "first-hit draws, conditioned on that minimum fitting `D`. Train-selected",
        "row is the honest public-profile result;",
        "best held-out row is diagnostic only.",
        "",
        "| law | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | rank bits/rec | arity bits/rec | delta bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        marker = "*" if row.law == selected.law else ""
        lines.append(
            f"| {row.law.name}{marker} | {row.train_gain_per_atom:.6f} | "
            f"{row.eval_gain_per_atom:.6f} | {row.missing_bits_per_record:.3f} | "
            f"{row.records_per_atom:.6f} | {row.avg_arity:.2f} | {row.avg_width:.2f} | "
            f"{row.rank_bits_per_record:.3f} | {row.arity_bits_per_record:.3f} | "
            f"{row.delta_bits_per_record:.3f} |"
        )
    best_eval = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Train-selected law: `{selected.law.name}` with held-out gain "
            f"`{selected.eval_gain_per_atom:.6f}` bits/input atom.",
            f"Best held-out diagnostic law: `{best_eval.law.name}` with "
            f"`{best_eval.eval_gain_per_atom:.6f}` bits/input atom.",
            "Only the train-selected law is a valid public-profile result.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=24)
    parser.add_argument("--eval-trials", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument("--constant-m", type=float, nargs="+", default=[1.0, 2.0, 4.0, 8.0, 16.0])
    parser.add_argument("--include-context-laws", action="store_true")
    parser.add_argument("--seed", type=int, default=2003)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.seed + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.eval_trials,
        args.seed + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
    )
    rows: list[LawRow] = []
    for law in default_laws(args.constant_m, args.include_context_laws):
        model, train_covers = train_model(
            train_samples,
            args.max_arity,
            args.frontier,
            law,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        eval_covers = [
            cover_with_law(trial, args.max_arity, args.frontier, model, law, args.flush_bits, args.rank_code)
            for trial in eval_samples
        ]
        rows.append(
            summarize(
                law,
                model,
                train_covers,
                eval_covers,
                args.block_bits,
                args.max_arity,
                args.frontier,
                args.rank_code,
                args.atoms,
            )
        )
    selected = max(rows, key=lambda row: row.train_gain_per_atom)
    print(render(rows, selected, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
