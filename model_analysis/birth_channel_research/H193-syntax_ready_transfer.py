#!/usr/bin/env python3
"""H193 - syntax-derived ready-set transfer and closed partitions.

H190-H192 close the local raw/witness mode channel.  This kernel moves the
object upward: can the already-decoded syntax determine whether the next slot is
raw-ready or witness-ready, keeping future witness supply alive without a mode
bit?

Two exact bounded probes are included:

1. Public ready-state DFA.
   A state q is derived from previous decoded items.  At state q the codec uses
   a public distribution P_q over N-bit outputs: raw, leftover-Kraft witness
   mixture, canonical shortest-witness mixture, or a canonical partition.  The
   next state is a public predicate of the decoded output.  For arbitrary uniform
   next items, state does not predict the next item, so the mean paid length is
   still N + a KL bill.

2. Closed canonical partition.
   A public set C_t is witness-ready only if its canonical witness child remains
   in C_{t-1}.  The complement is encoded by optimal public complement-rank mass.
   Closure thinning is then measured directly.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


INF = 10**9


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


def hash_to_output(label: bytes, payload_width: int, rank: int, target_bits: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(label)
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << target_bits) - 1)


@dataclass(frozen=True)
class Inventory:
    target_bits: int
    max_payload_width: int
    masses: list[float]
    best_len: list[int]
    best_mass: list[float]
    best_child: list[int]
    descriptions: int
    total_mass: float


@dataclass(frozen=True)
class Dist:
    name: str
    p: list[float]
    support: int
    mass: float
    active: frozenset[int]


@dataclass(frozen=True)
class DistStats:
    mean_uniform_len: float
    uniform_gain: float
    entropy: float
    inside_gain: float
    source_tax: float
    max_len: float


@dataclass(frozen=True)
class ReadyRow:
    target_bits: int
    max_payload_width: int
    rule: str
    state0: str
    state1: str
    pi0_uniform: float
    pi1_uniform: float
    mean_uniform_len: float
    uniform_gain: float
    entropy_rate: float
    inside_gain: float
    source_tax: float
    rho: float
    verdict: str


@dataclass(frozen=True)
class ClosureRow:
    target_bits: int
    max_payload_width: int
    pass_index: int
    support: int
    fraction: float
    witness_mass: float
    raw_frac_len: float
    mean_uniform_len: float
    uniform_gain: float
    closed_survival: float
    verdict: str


def build_inventory(target_bits: int, max_payload_width: int) -> Inventory:
    output_count = 1 << target_bits
    masses = [0.0] * output_count
    best_len = [INF] * output_count
    best_mass = [0.0] * output_count
    best_child = [-1] * output_count
    descriptions = 0
    total_mass = 0.0
    for payload_width in range(1, max_payload_width + 1):
        count = costs.payload_width_count_exact(payload_width)
        record_bits = costs.record_cost_for_payload_width(1, payload_width)
        mass = 2.0 ** (-record_bits)
        descriptions += count
        total_mass += count * mass
        for rank in range(count):
            out = hash_to_output(b"H193-layer\0", payload_width, rank, target_bits)
            masses[out] += mass
            if record_bits < best_len[out]:
                best_len[out] = record_bits
                best_mass[out] = mass
                best_child[out] = hash_to_output(
                    b"H193-child\0", payload_width, rank, target_bits
                )
    return Inventory(
        target_bits=target_bits,
        max_payload_width=max_payload_width,
        masses=masses,
        best_len=best_len,
        best_mass=best_mass,
        best_child=best_child,
        descriptions=descriptions,
        total_mass=total_mass,
    )


def uniform_dist(inv: Inventory) -> Dist:
    output_count = 1 << inv.target_bits
    return Dist("raw", [1.0 / output_count] * output_count, output_count, 1.0, frozenset())


def leftover_all_dist(inv: Inventory) -> Dist:
    output_count = 1 << inv.target_bits
    q = inv.total_mass
    if not 0.0 <= q < 1.0:
        raise ValueError("invalid total witness mass")
    p = [(1.0 - q) / output_count + mass for mass in inv.masses]
    return Dist(
        "allmix",
        p,
        sum(1 for mass in inv.masses if mass > 0.0),
        q,
        frozenset(i for i, mass in enumerate(inv.masses) if mass > 0.0),
    )


def leftover_best_dist(inv: Inventory) -> Dist:
    output_count = 1 << inv.target_bits
    q = sum(inv.best_mass)
    if not 0.0 <= q < 1.0:
        raise ValueError("invalid canonical witness mass")
    p = [(1.0 - q) / output_count + mass for mass in inv.best_mass]
    return Dist(
        "bestmix",
        p,
        sum(1 for mass in inv.best_mass if mass > 0.0),
        q,
        frozenset(i for i, mass in enumerate(inv.best_mass) if mass > 0.0),
    )


def canonical_partition_dist(inv: Inventory) -> Dist:
    output_count = 1 << inv.target_bits
    active = {i for i, length in enumerate(inv.best_len) if length < INF}
    while active:
        q = sum(inv.best_mass[i] for i in active)
        comp = output_count - len(active)
        raw_len = math.inf if comp == 0 else math.log2(comp / (1.0 - q))
        next_active = {i for i in active if inv.best_len[i] < raw_len}
        if next_active == active:
            break
        active = next_active
    q = sum(inv.best_mass[i] for i in active)
    comp = output_count - len(active)
    p = [0.0] * output_count
    if comp == 0:
        # Full witness coverage still cannot reclaim unused Kraft slack for
        # free.  Keep the same leftover raw mass model as H191/H192.
        p = [(1.0 - q) / output_count + inv.best_mass[i] for i in range(output_count)]
    else:
        raw_p = (1.0 - q) / comp
        for i in range(output_count):
            p[i] = inv.best_mass[i] if i in active else raw_p
    return Dist("canonpart", p, len(active), q, frozenset(active))


def dist_stats(target_bits: int, p: list[float]) -> DistStats:
    output_count = 1 << target_bits
    lengths = [(-math.log2(prob) if prob > 0.0 else math.inf) for prob in p]
    mean_uniform = sum(lengths) / output_count
    entropy = -sum(prob * math.log2(prob) for prob in p if prob > 0.0)
    inside_gain = target_bits - entropy
    source_tax = inside_gain
    return DistStats(
        mean_uniform_len=mean_uniform,
        uniform_gain=target_bits - mean_uniform,
        entropy=entropy,
        inside_gain=inside_gain,
        source_tax=source_tax,
        max_len=max(lengths),
    )


def next_state(rule: str, inv: Inventory, state: int, output: int) -> int:
    if rule == "parity":
        return output & 1
    if rule == "covered":
        return 1 if inv.masses[output] > 0.0 else 0
    if rule == "short":
        return 1 if inv.best_len[output] < inv.target_bits else 0
    if rule == "toggle_covered":
        return state ^ (1 if inv.masses[output] > 0.0 else 0)
    raise ValueError(rule)


def transition(inv: Inventory, rule: str, p: list[float], state: int) -> list[float]:
    row = [0.0, 0.0]
    for output, prob in enumerate(p):
        row[next_state(rule, inv, state, output)] += prob
    return row


def stationary(matrix: list[list[float]]) -> list[float]:
    pi = [0.5, 0.5]
    for _ in range(512):
        nxt = [
            pi[0] * matrix[0][0] + pi[1] * matrix[1][0],
            pi[0] * matrix[0][1] + pi[1] * matrix[1][1],
        ]
        total = sum(nxt)
        if total <= 0.0:
            return [0.5, 0.5]
        nxt = [value / total for value in nxt]
        if max(abs(nxt[i] - pi[i]) for i in range(2)) < 1e-14:
            return nxt
        pi = nxt
    return pi


def spectral_radius_2x2(matrix: list[list[float]]) -> float:
    a, b = matrix[0]
    c, d = matrix[1]
    trace = a + d
    det = a * d - b * c
    disc = max(0.0, trace * trace - 4.0 * det)
    return max(abs((trace + math.sqrt(disc)) / 2.0), abs((trace - math.sqrt(disc)) / 2.0))


def ready_row(inv: Inventory, rule: str, d0: Dist, d1: Dist) -> ReadyRow:
    output_count = 1 << inv.target_bits
    uniform_p = [1.0 / output_count] * output_count
    uniform_matrix = [
        transition(inv, rule, uniform_p, 0),
        transition(inv, rule, uniform_p, 1),
    ]
    pi_u = stationary(uniform_matrix)
    s0 = dist_stats(inv.target_bits, d0.p)
    s1 = dist_stats(inv.target_bits, d1.p)
    mean_u = pi_u[0] * s0.mean_uniform_len + pi_u[1] * s1.mean_uniform_len

    code_matrix = [
        transition(inv, rule, d0.p, 0),
        transition(inv, rule, d1.p, 1),
    ]
    pi_p = stationary(code_matrix)
    entropy_rate = pi_p[0] * s0.entropy + pi_p[1] * s1.entropy
    inside_gain = inv.target_bits - entropy_rate
    source_tax = inside_gain
    rho = spectral_radius_2x2(code_matrix)
    verdict = (
        "BUG: public ready state beats uniform"
        if inv.target_bits - mean_u > 1e-12
        else "uniform bill nonnegative; inside gain is source-shaped"
    )
    return ReadyRow(
        target_bits=inv.target_bits,
        max_payload_width=inv.max_payload_width,
        rule=rule,
        state0=d0.name,
        state1=d1.name,
        pi0_uniform=pi_u[0],
        pi1_uniform=pi_u[1],
        mean_uniform_len=mean_u,
        uniform_gain=inv.target_bits - mean_u,
        entropy_rate=entropy_rate,
        inside_gain=inside_gain,
        source_tax=source_tax,
        rho=rho,
        verdict=verdict,
    )


def closure_rows(inv: Inventory, passes: int) -> list[ClosureRow]:
    output_count = 1 << inv.target_bits
    active = {i for i, length in enumerate(inv.best_len) if length < INF}
    start_count = max(1, len(active))
    rows: list[ClosureRow] = []
    for pass_index in range(passes + 1):
        q = sum(inv.best_mass[i] for i in active)
        comp = output_count - len(active)
        if comp == 0:
            raw_len = math.inf
            mean_len = sum(inv.best_len[i] for i in active) / output_count
        else:
            raw_len = math.log2(comp / (1.0 - q))
            mean_len = (
                sum(inv.best_len[i] for i in active) + comp * raw_len
            ) / output_count
        gain = inv.target_bits - mean_len
        verdict = (
            "BUG: closed partition beats uniform"
            if gain > 1e-12
            else "closure/complement bill nonnegative"
        )
        rows.append(
            ClosureRow(
                target_bits=inv.target_bits,
                max_payload_width=inv.max_payload_width,
                pass_index=pass_index,
                support=len(active),
                fraction=len(active) / output_count,
                witness_mass=q,
                raw_frac_len=raw_len,
                mean_uniform_len=mean_len,
                uniform_gain=gain,
                closed_survival=len(active) / start_count,
                verdict=verdict,
            )
        )
        active = {i for i in active if inv.best_child[i] in active}
    return rows


def print_ready_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 12, 16])
    max_width_values = parse_int_list(args.max_payload_width, [4, 8, 16])
    rules = args.rule or ["parity", "covered", "short", "toggle_covered"]
    print("== H193 syntax-derived ready-state transfer ==")
    print(
        "State is public from decoded syntax. uniformGain>0 would be an arbitrary-data crossing."
    )
    print(
        f"{'N':>4} {'Wmax':>5} {'rule':<14} {'q0':<10} {'q1':<10} "
        f"{'pi1U':>7} {'meanU':>9} {'gainU':>9} {'Hrate':>9} "
        f"{'inGain':>9} {'tax':>9} {'rho':>7} {'verdict'}"
    )
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            inv = build_inventory(target_bits, max_width)
            dists = {
                "raw": uniform_dist(inv),
                "allmix": leftover_all_dist(inv),
                "bestmix": leftover_best_dist(inv),
                "canonpart": canonical_partition_dist(inv),
            }
            pairs = [
                ("raw", "allmix"),
                ("raw", "bestmix"),
                ("raw", "canonpart"),
                ("canonpart", "canonpart"),
            ]
            for rule in rules:
                for a, b in pairs:
                    row = ready_row(inv, rule, dists[a], dists[b])
                    if row.uniform_gain > 1e-9:
                        raise AssertionError("public ready-state row beat uniform")
                    print(
                        f"{row.target_bits:4d} {row.max_payload_width:5d} "
                        f"{row.rule:<14} {row.state0:<10} {row.state1:<10} "
                        f"{fmt(row.pi1_uniform):>7} {fmt(row.mean_uniform_len):>9} "
                        f"{fmt(row.uniform_gain):>9} {fmt(row.entropy_rate):>9} "
                        f"{fmt(row.inside_gain):>9} {fmt(row.source_tax):>9} "
                        f"{fmt(row.rho):>7} {row.verdict}"
                    )


def print_closure_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 12, 16])
    max_width_values = parse_int_list(args.max_payload_width, [4, 8, 16])
    print()
    print("== H193 closed canonical partition ==")
    print(
        "C_{t+1} keeps outputs whose canonical witness child remains in C_t; complement is rank-coded."
    )
    print(
        f"{'N':>4} {'Wmax':>5} {'t':>3} {'support':>8} {'frac':>9} "
        f"{'q':>9} {'rawF':>9} {'meanU':>9} {'gainU':>9} "
        f"{'survive':>9} {'verdict'}"
    )
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            inv = build_inventory(target_bits, max_width)
            for row in closure_rows(inv, args.passes):
                if row.uniform_gain > 1e-9:
                    raise AssertionError("closed partition row beat uniform")
                print(
                    f"{row.target_bits:4d} {row.max_payload_width:5d} "
                    f"{row.pass_index:3d} {row.support:8d} {fmt(row.fraction):>9} "
                    f"{fmt(row.witness_mass):>9} {fmt(row.raw_frac_len):>9} "
                    f"{fmt(row.mean_uniform_len):>9} {fmt(row.uniform_gain):>9} "
                    f"{fmt(row.closed_survival):>9} {row.verdict}"
                )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A public ready state is geometry unless it predicts the next target.")
    print("For arbitrary uniform next items, every state distribution P_q pays")
    print("E_U[-log P_q]=N+D(U||P_q). Syntax-derived recurrence can create")
    print("inside-class gain only by creating a non-uniform source law; the")
    print("source tax is the same KL term. Closed partitions thin witness support")
    print("and charge the complement rank/fallback mass. A positive rho requires")
    print("overfull row mass or an explicit generated/reachable source.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--rule", action="append", default=[])
    parser.add_argument("--passes", type=int, default=4)
    args = parser.parse_args()

    print_ready_table(args)
    print_closure_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
