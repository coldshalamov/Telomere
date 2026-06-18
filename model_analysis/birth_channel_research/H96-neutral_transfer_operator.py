#!/usr/bin/env python3
"""H96 - neutral transfer operator over visible record strings.

This is the smallest native version of the biology analogy:

    phenotype: current raw word x
    genotype: a concrete paid Telomere record string c that decodes to x
    fertility: how compressible the visible record string c is on the next pass

The encoder is allowed to choose among neutral/synonymous descriptions, but the
chosen record bits are the output, so the choice is paid by the visible current
record length. No neutral-rank selector, profile, pass tag, or birth ledger is
stored.

The kernel exactly enumerates all descriptions in a tiny B=1 domain, computes
their current cost, then computes the all-description next-pass mass of each
visible record string. It asks whether best neutral transfer can make the
two-pass cycle positive under a fixed public record family.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    arity_cost,
    j3d1_cost_for_payload_width,
    record_cost_for_payload_width,
)
from total_cover_lotus_crossover import lotus_payload_width_from_rank  # noqa: E402


H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)


ARITY_BITS = {
    1: "00",
    2: "01",
    3: "100",
    4: "101",
    5: "110",
}


@dataclass(frozen=True)
class Record:
    arity: int
    rank: int
    value: int
    cost: int
    weight: float
    bits: str


@dataclass(frozen=True)
class Description:
    weight: float
    cost: int
    bits: str


@dataclass(frozen=True)
class WordRow:
    word: int
    description_count: int
    z_current: float
    collective_current_saving: float
    best_current_saving: float
    posterior_future_saving: float
    best_transfer_cycle: float
    best_transfer_current: float
    best_transfer_future: float
    random_same_length_future: float
    best_transfer_len: int


def stable_bits(label: str, count: int) -> str:
    out = ""
    counter = 0
    while len(out) < count:
        digest = hashlib.sha256(f"{label}:{counter}".encode("ascii")).digest()
        out += "".join(f"{byte:08b}" for byte in digest)
        counter += 1
    return out[:count]


def record_bits(arity: int, rank: int, cost: int) -> str:
    prefix = ARITY_BITS[arity]
    remaining = cost - len(prefix)
    if remaining < 1:
        raise ValueError("record cost shorter than arity prefix")
    return prefix + stable_bits(f"a{arity}:r{rank}", remaining)


def span_value(word: int, start_atom: int, arity: int, atoms: int) -> int:
    shift_atoms = atoms - (start_atom + arity)
    mask = (1 << arity) - 1
    return (word >> shift_atoms) & mask


def word_from_bits(bits: str) -> int:
    return int(bits, 2) if bits else 0


def build_record_family(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[list[list[Record]]], list[list[float]], list[list[float]]]:
    if block_bits != 1:
        raise ValueError("H96 currently uses B=1 so visible record strings can be reblocked exactly")
    rng = random.Random(seed)
    by_value: list[list[list[Record]]] = [[]]
    edge_weights: list[list[float]] = [[]]
    edge_maxes: list[list[float]] = [[]]
    for arity in range(1, max_arity + 1):
        value_count = 1 << arity
        records = [[] for _ in range(value_count)]
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for rank in range(1, (1 << depth_bits) + 1):
            value = rng.randrange(value_count)
            payload_width = lotus_payload_width_from_rank(rank)
            cost = record_cost_for_payload_width(arity, payload_width)
            bits = record_bits(arity, rank, cost)
            if len(bits) != cost:
                raise AssertionError("bad record bit length")
            weight = 2.0 ** (-cost)
            record = Record(
                arity=arity,
                rank=rank,
                value=value,
                cost=cost,
                weight=weight,
                bits=bits,
            )
            records[value].append(record)
            weights[value] += weight
            maxes[value] = max(maxes[value], weight)
        by_value.append(records)
        edge_weights.append(weights)
        edge_maxes.append(maxes)
    return by_value, edge_weights, edge_maxes


def enumerate_descriptions(
    word: int,
    atoms: int,
    max_arity: int,
    by_value: list[list[list[Record]]],
) -> list[Description]:
    descriptions: list[Description] = []

    def rec(pos: int, weight: float, cost: int, bits: str) -> None:
        if pos == atoms:
            descriptions.append(Description(weight=weight, cost=cost, bits=bits))
            return
        for arity in range(1, min(max_arity, atoms - pos) + 1):
            value = span_value(word, pos, arity, atoms)
            for record in by_value[arity][value]:
                rec(
                    pos + arity,
                    weight * record.weight,
                    cost + record.cost,
                    bits + record.bits,
                )

    rec(0, 1.0, 0, "")
    return descriptions


def all_description_mass_for_bits(
    bits: str,
    max_arity: int,
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
) -> tuple[float, float]:
    atoms = len(bits)
    return _h74.dp_mass_for_word(
        word_from_bits(bits),
        atoms,
        1,
        max_arity,
        edge_weights,
        edge_maxes,
    )


def run_kernel(
    atoms: int = 5,
    max_arity: int = 3,
    depth_bits: int = 3,
    seed: int = 96000,
) -> list[WordRow]:
    by_value, edge_weights, edge_maxes = build_record_family(
        block_bits=1,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=seed,
    )
    rng = random.Random(seed + 1)

    @lru_cache(maxsize=None)
    def future_collective_saving(bits: str) -> float:
        total, _ = all_description_mass_for_bits(bits, max_arity, edge_weights, edge_maxes)
        if total <= 0.0:
            return float("-inf")
        return len(bits) + math.log2(total)

    rows: list[WordRow] = []
    for word in range(1 << atoms):
        descriptions = enumerate_descriptions(word, atoms, max_arity, by_value)
        if not descriptions:
            rows.append(
                WordRow(
                    word=word,
                    description_count=0,
                    z_current=0.0,
                    collective_current_saving=float("-inf"),
                    best_current_saving=float("-inf"),
                    posterior_future_saving=float("-inf"),
                    best_transfer_cycle=float("-inf"),
                    best_transfer_current=float("-inf"),
                    best_transfer_future=float("-inf"),
                    random_same_length_future=float("-inf"),
                    best_transfer_len=0,
                )
            )
            continue
        z_current = sum(description.weight for description in descriptions)
        collective_current_saving = atoms + math.log2(z_current)
        best_current_saving = max(atoms - description.cost for description in descriptions)
        posterior_future = sum(
            (description.weight / z_current) * future_collective_saving(description.bits)
            for description in descriptions
        )
        best_description = max(
            descriptions,
            key=lambda description: (
                atoms - description.cost + future_collective_saving(description.bits),
                atoms - description.cost,
            ),
        )
        best_future = future_collective_saving(best_description.bits)
        best_current = atoms - best_description.cost
        random_bits = "".join("1" if rng.randrange(2) else "0" for _ in range(len(best_description.bits)))
        random_future = future_collective_saving(random_bits)
        rows.append(
            WordRow(
                word=word,
                description_count=len(descriptions),
                z_current=z_current,
                collective_current_saving=collective_current_saving,
                best_current_saving=best_current_saving,
                posterior_future_saving=posterior_future,
                best_transfer_cycle=best_current + best_future,
                best_transfer_current=best_current,
                best_transfer_future=best_future,
                random_same_length_future=random_future,
                best_transfer_len=len(best_description.bits),
            )
        )
    return rows


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else float("-inf")


def print_rows(rows: list[WordRow], atoms: int, max_arity: int, depth_bits: int) -> None:
    print("== neutral transfer operator ==")
    print(f"B=1,N={atoms},K={max_arity},D={depth_bits}; exact description enumeration.")
    print(
        f"{'metric':<34} {'value':>12}"
    )
    print(f"{'reachable words':<34} {sum(1 for row in rows if row.description_count):12d}/{len(rows)}")
    print(f"{'avg descriptions/word':<34} {finite_mean([row.description_count for row in rows]):12.3f}")
    print(f"{'E_U collective current saving':<34} {finite_mean([row.collective_current_saving for row in rows]):12.6f}")
    print(f"{'E_U best selected current saving':<34} {finite_mean([row.best_current_saving for row in rows]):12.6f}")
    print(f"{'E_posterior future saving':<34} {finite_mean([row.posterior_future_saving for row in rows]):12.6f}")
    print(f"{'E_U best transfer cycle':<34} {finite_mean([row.best_transfer_cycle for row in rows]):12.6f}")
    print(f"{'E current of transfer choice':<34} {finite_mean([row.best_transfer_current for row in rows]):12.6f}")
    print(f"{'E future of transfer choice':<34} {finite_mean([row.best_transfer_future for row in rows]):12.6f}")
    print(f"{'E random same-length future':<34} {finite_mean([row.random_same_length_future for row in rows]):12.6f}")
    print(f"{'E neutral future lift':<34} {finite_mean([row.best_transfer_future - row.random_same_length_future for row in rows]):12.6f}")
    print(f"{'E future lift vs posterior':<34} {finite_mean([row.best_transfer_future - row.posterior_future_saving for row in rows]):12.6f}")
    print(f"{'Pr cycle positive':<34} {sum(1 for row in rows if row.best_transfer_cycle > 0.0) / len(rows):12.6f}")
    print(f"{'Pr current selected positive':<34} {sum(1 for row in rows if row.best_current_saving > 0.0) / len(rows):12.6f}")
    print()
    print("== top transfer rows ==")
    print(
        f"{'word':>5} {'descs':>8} {'coll now':>10} {'best now':>10} "
        f"{'cycle':>10} {'chosen now':>11} {'chosen fut':>11} {'len':>5}"
    )
    for row in sorted(rows, key=lambda item: item.best_transfer_cycle, reverse=True)[:8]:
        print(
            f"{row.word:5d} {row.description_count:8d} "
            f"{row.collective_current_saving:10.4f} {row.best_current_saving:10.4f} "
            f"{row.best_transfer_cycle:10.4f} {row.best_transfer_current:11.4f} "
            f"{row.best_transfer_future:11.4f} {row.best_transfer_len:5d}"
        )
    print()


def print_reading(rows: list[WordRow]) -> None:
    avg_cycle = finite_mean([row.best_transfer_cycle for row in rows])
    positive = sum(1 for row in rows if row.best_transfer_cycle > 0.0) / len(rows)
    print("== reading ==")
    print(
        "This is an intentionally favorable neutral-transfer test: the encoder "
        "can choose the visible record string that maximizes current+next "
        "all-description savings, and that choice needs no side selector because "
        "the chosen bits are the output."
    )
    print(
        f"In this exact toy, average best two-pass cycle is {avg_cycle:.6f} "
        f"bits/word and the positive-cycle fraction is {positive:.6f}."
    )
    print(
        "A positive minority is allowed and expected; the all-data question is "
        "the uniform average after paying the current record bits. If this row "
        "stays negative, neutral genotype choice is a source/fertility tool, "
        "not a roughly-all-data escape."
    )


def main() -> None:
    atoms = 5
    max_arity = 3
    depth_bits = 3
    rows = run_kernel(atoms=atoms, max_arity=max_arity, depth_bits=depth_bits)
    print_rows(rows, atoms, max_arity, depth_bits)
    print_reading(rows)


if __name__ == "__main__":
    main()
