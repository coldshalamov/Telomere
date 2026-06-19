#!/usr/bin/env python3
"""H175 - state-carrying total-cover transducer.

This tests the attached "salt is digest tail, not metadata" idea.

Generator:

    z = H(domain || q_in || arity || seed)
    x = z[:arity * B]
    q_out = z[arity * B : arity * B + r]

The record stores only [arity][seed witness]. The decoder knows q_in before
the record, reconstructs x, reads q_out from the unconstrained digest tail, and
uses q_out as the next record salt/state.

The accounting distinction is the whole point:

    observing q_out after an x match costs 0 supply bits;
    requiring q_out to equal a chosen value costs r supply bits.

This is a tiny random-oracle kernel with exact current V1/J3D1 record costs for
arities 1..5. It is not a large compression test.
"""

from __future__ import annotations

import argparse
import hashlib
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
    j3d1_cost_for_seed_index,
    lotus_width_for_value,
    payload_width_for_seed_index,
    record_cost,
)


ARITY_CODE = {
    1: "00",
    2: "01",
    3: "100",
    4: "101",
    5: "110",
}


def random_bits(rng: random.Random, nbits: int) -> str:
    return "".join("1" if rng.getrandbits(1) else "0" for _ in range(nbits))


def bytes_to_bits(data: bytes, nbits: int) -> str:
    return "".join(f"{byte:08b}" for byte in data)[:nbits]


def xof_bits(parts: tuple[bytes, ...], nbits: int) -> str:
    out = bytearray()
    counter = 0
    need_bytes = (nbits + 7) // 8
    while len(out) < need_bytes:
        h = hashlib.sha256()
        for part in parts:
            h.update(len(part).to_bytes(4, "big"))
            h.update(part)
        h.update(counter.to_bytes(4, "big"))
        out.extend(h.digest())
        counter += 1
    return bytes_to_bits(bytes(out), nbits)


@lru_cache(maxsize=None)
def transduce(q_in: int, arity: int, seed: int, block_bits: int, state_bits: int) -> tuple[str, int]:
    data_bits = arity * block_bits
    total_bits = data_bits + state_bits
    z = xof_bits(
        (
            b"Telomere-H175-State-v1",
            q_in.to_bytes(max(1, (state_bits + 7) // 8), "big"),
            arity.to_bytes(2, "big"),
            seed.to_bytes(8, "big"),
        ),
        total_bits,
    )
    x = z[:data_bits]
    q_out = int(z[data_bits:total_bits] or "0", 2)
    return x, q_out


def j3d1_encode(seed_index: int) -> str:
    value = seed_index + 1
    payload_width = payload_width_for_seed_index(seed_index)
    tier_width = lotus_width_for_value(payload_width)
    bits = format(tier_width - 1, "03b")
    bits += format(payload_width - ((1 << tier_width) - 2), f"0{tier_width}b")
    bits += format(value - ((1 << payload_width) - 2), f"0{payload_width}b")
    assert len(bits) == j3d1_cost_for_seed_index(seed_index)
    return bits


def record_wire_bits(arity: int, seed: int) -> str:
    return ARITY_CODE[arity] + j3d1_encode(seed)


@dataclass(frozen=True)
class Edge:
    start: int
    end: int
    q_in: int
    q_out: int
    arity: int
    seed: int
    cost: int
    wire: str


@dataclass(frozen=True)
class PathState:
    cost: int
    q: int
    bits: str
    records: int
    arity_sum: int


@dataclass
class PolicySummary:
    label: str
    trials: int = 0
    successes: int = 0
    input_bits: int = 0
    output_bits: int = 0
    records: int = 0
    arity_sum: int = 0
    pass2_successes: int = 0
    pass2_total_bits: int = 0
    greedy_two_pass_bits: int = 0
    lookahead_two_pass_bits: int = 0
    lookahead_wins: int = 0

    def add_one_pass(self, input_len: int, path: PathState) -> None:
        self.trials += 1
        self.successes += 1
        self.input_bits += input_len
        self.output_bits += path.cost
        self.records += path.records
        self.arity_sum += path.arity_sum

    @property
    def support(self) -> float:
        return self.successes / self.trials if self.trials else 0.0

    @property
    def gain_per_atom(self) -> float:
        if not self.successes:
            return 0.0
        return (self.input_bits - self.output_bits) / self.successes

    @property
    def records_per_atom(self) -> float:
        if not self.successes:
            return 0.0
        atoms = self.input_bits / self.successes
        return self.records / self.successes / atoms

    @property
    def avg_arity(self) -> float:
        return self.arity_sum / self.records if self.records else 0.0


def edge_matches(
    target: str,
    start_atom: int,
    q_in: int,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    state_bits: int,
    edge_slack: int,
    keep_equal: bool,
) -> list[Edge]:
    seed_count = 1 << depth_bits
    n_atoms = len(target) // block_bits
    all_hits: list[Edge] = []
    for arity in range(1, min(max_arity, n_atoms - start_atom) + 1):
        start_bit = start_atom * block_bits
        end_bit = start_bit + arity * block_bits
        wanted = target[start_bit:end_bit]
        hits: list[Edge] = []
        for seed in range(seed_count):
            x, q_out = transduce(q_in, arity, seed, block_bits, state_bits)
            if x != wanted:
                continue
            wire = record_wire_bits(arity, seed)
            cost = record_cost(arity, seed)
            assert cost == len(wire)
            hits.append(
                Edge(
                    start=start_atom,
                    end=start_atom + arity,
                    q_in=q_in,
                    q_out=q_out,
                    arity=arity,
                    seed=seed,
                    cost=cost,
                    wire=wire,
                )
            )
        if not hits:
            continue
        best = min(edge.cost for edge in hits)
        if keep_equal:
            kept = [edge for edge in hits if edge.cost == best]
        else:
            kept = [min(hits, key=lambda edge: (edge.cost, edge.seed))]
        if edge_slack > 0:
            kept = [edge for edge in hits if edge.cost <= best + edge_slack]
        all_hits.extend(kept)
    return all_hits


def trim_beam(paths: list[PathState], beam: int) -> list[PathState]:
    paths.sort(key=lambda path: (path.cost, len(path.bits), path.q))
    seen: set[tuple[int, int, str]] = set()
    out: list[PathState] = []
    for path in paths:
        key = (path.cost, path.q, path.bits)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
        if len(out) >= beam:
            break
    return out


def cover_paths(
    target: str,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    state_bits: int,
    edge_slack: int,
    keep_equal: bool,
    beam: int,
) -> list[PathState]:
    if len(target) % block_bits:
        raise ValueError("target length must be atom-aligned")
    n_atoms = len(target) // block_bits
    layers: list[dict[int, list[PathState]]] = [dict() for _ in range(n_atoms + 1)]
    layers[0][0] = [PathState(cost=0, q=0, bits="", records=0, arity_sum=0)]
    edge_cache: dict[tuple[int, int], list[Edge]] = {}

    for pos in range(n_atoms):
        if not layers[pos]:
            continue
        for q_in, paths in list(layers[pos].items()):
            cache_key = (pos, q_in)
            if cache_key not in edge_cache:
                edge_cache[cache_key] = edge_matches(
                    target,
                    pos,
                    q_in,
                    block_bits,
                    max_arity,
                    depth_bits,
                    state_bits,
                    edge_slack,
                    keep_equal,
                )
            for path in paths:
                for edge in edge_cache[cache_key]:
                    nxt = PathState(
                        cost=path.cost + edge.cost,
                        q=edge.q_out,
                        bits=path.bits + edge.wire,
                        records=path.records + 1,
                        arity_sum=path.arity_sum + edge.arity,
                    )
                    bucket = layers[edge.end].setdefault(edge.q_out, [])
                    bucket.append(nxt)
                    if len(bucket) > beam * 4:
                        layers[edge.end][edge.q_out] = trim_beam(bucket, beam)

    finals: list[PathState] = []
    for paths in layers[n_atoms].values():
        finals.extend(paths)
    return trim_beam(finals, beam)


def pad_to_atom(bits: str, block_bits: int) -> str:
    pad = (-len(bits)) % block_bits
    return bits + ("0" * pad)


def tail_sanity(rng: random.Random, block_bits: int, depth_bits: int, state_bits: int, trials: int) -> None:
    unconstrained = 0
    conditioned = 0
    for _ in range(trials):
        q = rng.randrange(1 << state_bits)
        target = random_bits(rng, block_bits)
        for seed in range(1 << depth_bits):
            x, q_out = transduce(q, 1, seed, block_bits, state_bits)
            if x == target:
                unconstrained += 1
                if q_out == 0:
                    conditioned += 1
    expected_ratio = 2.0 ** (-state_bits)
    observed_ratio = conditioned / unconstrained if unconstrained else 0.0
    print("== digest-tail observe vs condition sanity ==")
    print(
        f"B={block_bits} D={depth_bits} r={state_bits} trials={trials} "
        f"unconstrained_matches={unconstrained} q_out_zero={conditioned}"
    )
    print(
        f"observed conditioned/unconstrained={observed_ratio:.6f}; "
        f"expected about 2^-r={expected_ratio:.6f}"
    )
    print()


def policy_sweep(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    policies = [
        ("shortest", 0, False, 1),
        ("equal-cost", 0, True, args.beam),
        ("slack+1", 1, True, args.beam),
        ("slack+2", 2, True, args.beam),
        ("slack+4", 4, True, args.beam),
        ("slack+8", 8, True, args.beam),
    ]
    summaries = {label: PolicySummary(label=label) for label, _, _, _ in policies}
    two_pass_trials = 0

    for _ in range(args.trials):
        target = random_bits(rng, args.atoms * args.block_bits)
        greedy_two = None
        if args.two_pass:
            greedy_paths = cover_paths(
                target,
                args.block_bits,
                args.max_arity,
                args.depth_bits,
                args.state_bits,
                edge_slack=0,
                keep_equal=False,
                beam=1,
            )
        else:
            greedy_paths = []
        if args.two_pass and greedy_paths:
            next_target = pad_to_atom(greedy_paths[0].bits, args.block_bits)
            next_paths = cover_paths(
                next_target,
                args.block_bits,
                args.max_arity,
                args.depth_bits,
                args.state_bits,
                edge_slack=0,
                keep_equal=False,
                beam=1,
            )
            if next_paths:
                greedy_two = greedy_paths[0].cost + next_paths[0].cost

        for label, slack, keep_equal, beam in policies:
            paths = cover_paths(
                target,
                args.block_bits,
                args.max_arity,
                args.depth_bits,
                args.state_bits,
                edge_slack=slack,
                keep_equal=keep_equal,
                beam=beam,
            )
            summary = summaries[label]
            summary.trials += 1
            if not paths:
                continue
            best = paths[0]
            summary.successes += 1
            summary.input_bits += len(target)
            summary.output_bits += best.cost
            summary.records += best.records
            summary.arity_sum += best.arity_sum

            if not args.two_pass or greedy_two is None or label == "shortest":
                continue
            best_two = None
            for path in paths[: args.lookahead_paths]:
                next_target = pad_to_atom(path.bits, args.block_bits)
                next_paths = cover_paths(
                    next_target,
                    args.block_bits,
                    args.max_arity,
                    args.depth_bits,
                    args.state_bits,
                    edge_slack=0,
                    keep_equal=False,
                    beam=1,
                )
                if not next_paths:
                    continue
                total = path.cost + next_paths[0].cost
                best_two = total if best_two is None else min(best_two, total)
            if best_two is not None:
                summary.pass2_successes += 1
                summary.greedy_two_pass_bits += greedy_two
                summary.lookahead_two_pass_bits += best_two
                if best_two < greedy_two:
                    summary.lookahead_wins += 1
        two_pass_trials += 1

    print("== state-carrying cover policy sweep ==")
    print(
        f"B={args.block_bits} atoms={args.atoms} K={args.max_arity} "
        f"D={args.depth_bits} r={args.state_bits} trials={args.trials}"
    )
    print(
        f"{'policy':<12} {'support':>8} {'gain/trial':>11} {'out/in':>8} "
        f"{'records':>8} {'avg a':>7} {'2p wins':>8} {'2p delta':>10}"
    )
    for label, _, _, _ in policies:
        s = summaries[label]
        if s.successes:
            out_in = s.output_bits / s.input_bits
            gain = (s.input_bits - s.output_bits) / s.successes
            records = s.records / s.successes
            avg_a = s.avg_arity
        else:
            out_in = 0.0
            gain = 0.0
            records = 0.0
            avg_a = 0.0
        if s.pass2_successes:
            delta = (s.greedy_two_pass_bits - s.lookahead_two_pass_bits) / s.pass2_successes
        else:
            delta = 0.0
        print(
            f"{label:<12} {s.support:8.3f} {gain:11.3f} {out_in:8.3f} "
            f"{records:8.3f} {avg_a:7.3f} {s.lookahead_wins:8d} {delta:10.3f}"
        )
    print()
    print("2p delta is greedy_two_pass_bits - lookahead_two_pass_bits when --two-pass")
    print("is enabled; positive means bounded-slack surface choice improved exact")
    print("two-pass cost without a selector.")
    print()


def analytic_grid() -> None:
    print("== analytic edge supply grid ==")
    print("Expected matches per interval = 2^D / 2^(aB). Conditioning r tail bits")
    print("would divide these by 2^r; merely observing q_out does not.")
    print(f"{'B':>4} {'K':>4} {'D':>4} {'arity':>5} {'lambda':>12} {'min rec':>8} {'span':>6}")
    for block_bits in (4, 6, 8, 12):
        for max_arity in (2, 5):
            depth_bits = min(12, max_arity * block_bits)
            for arity in range(1, min(max_arity, 5) + 1):
                lam = 2.0 ** (depth_bits - arity * block_bits)
                print(
                    f"{block_bits:4d} {max_arity:4d} {depth_bits:4d} "
                    f"{arity:5d} {lam:12.6g} {record_cost(arity, 0):8d} "
                    f"{arity * block_bits:6d}"
                )
            print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=16)
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--depth-bits", type=int, default=8)
    parser.add_argument("--state-bits", type=int, default=4)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--tail-trials", type=int, default=200)
    parser.add_argument("--beam", type=int, default=6)
    parser.add_argument("--lookahead-paths", type=int, default=4)
    parser.add_argument("--two-pass", action="store_true")
    parser.add_argument("--seed", type=int, default=20260618)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_arity > 5:
        raise ValueError("H175 exact V1/J3D1 mode supports K<=5")
    rng = random.Random(args.seed)
    tail_sanity(rng, args.block_bits, args.depth_bits, args.state_bits, args.tail_trials)
    analytic_grid()
    policy_sweep(args)


if __name__ == "__main__":
    main()
