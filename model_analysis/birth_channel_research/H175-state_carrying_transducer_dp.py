#!/usr/bin/env python3
"""H175 - state-carrying total-cover transducer DP.

This is the first kernel for the pasted state-transducer proposal:

    G(q_i, a_i, s_i) = (x_i, q_{i+1})

Only [arity][seed witness] is stored. The decoder starts from public q0=0,
opens records in order, and derives q_{i+1} from digest tail bits. Under the
uniform hash law, matching the data prefix costs 2^-L. Observing the tail bits
that become q_{i+1} is free; conditioning those bits to a requested value is
modeled explicitly by --condition-tail-bits and reduces witness supply.

The encoder is a trellis over (position, q). For each reachable state and
interval, it samples matching witnesses from the exact J3D1 payload-width
buckets and then keeps either:

* shortest: one shortest witness only;
* equal: all witnesses with the shortest record cost;
* slack:N: all witnesses within N bits of the shortest record cost.

The DP is exact for the sampled edge set unless --state-cap or --hit-cap prunes
states/candidates; both are reported. K>5 rows require an explicitly labeled
hypothetical arity grammar because current V1 exact arity codewords stop at 5.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    arity_cost,
    j3d1_cost_for_payload_width,
    payload_width_count_le,
)


INF = 10**18


@dataclass(frozen=True)
class Candidate:
    cost: int
    arity: int
    q_next: int


@dataclass(frozen=True)
class PathState:
    cost: int
    records: int
    arity_sum: int
    output_lengths: tuple[int, ...]


@dataclass(frozen=True)
class CoverResult:
    supported: bool
    input_bits: int
    output_bits: int | None
    output_lengths: tuple[int, ...]
    records: int
    arity_sum: int
    sampled_edges: int
    hit_edges: int
    candidate_choices: int
    truncated_hits: int
    pruned_states: int
    max_frontier_states: int

    @property
    def avg_arity(self) -> float:
        return self.arity_sum / self.records if self.records else 0.0


@dataclass(frozen=True)
class TrialResult:
    pass1: CoverResult
    completed: bool
    final_bits: int | None
    pass_log2rho: tuple[float, ...]


@dataclass(frozen=True)
class Row:
    block_bits: int
    max_arity: int
    depth_bits: int
    state_bits: int
    policy: str
    slack: int
    arity_code: str
    condition_tail_bits: int
    item_count: int
    passes: int
    trials: int
    pass1_support: float
    complete_support: float
    edge_hit_rate: float
    choices_per_hit: float
    avg_input_bits: float
    avg_output_bits: float
    gain_per_atom: float
    records_per_atom: float
    avg_arity: float
    mean_pass_log2rho: float
    p95_pass_log2rho: float
    mean_final_log2rho: float
    max_frontier_states: int
    pruned_states: int
    truncated_hits: int


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode("ascii"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest(), "big")


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    result: list[int] = []
    for raw in values:
        result.extend(int(part) for part in raw.split(",") if part)
    return result


def parse_policy(raw: str) -> tuple[str, int]:
    if raw == "shortest":
        return "shortest", 0
    if raw == "equal":
        return "equal", 0
    if raw.startswith("slack:"):
        slack = int(raw.split(":", 1)[1])
        if slack < 0:
            raise ValueError("slack must be non-negative")
        return "slack", slack
    raise ValueError(f"unknown policy {raw!r}")


def policy_label(policy: str, slack: int) -> str:
    if policy == "slack":
        return f"slack:{slack}"
    return policy


def record_arity_cost(arity: int, max_arity: int, arity_code: str) -> int:
    if arity_code == "exact":
        return arity_cost(arity)
    if arity_code == "fixed":
        return ceil_log2(max_arity)
    if arity_code == "escape5":
        if arity <= 5:
            return arity_cost(arity)
        return 3 + ceil_log2(max_arity - 5)
    raise ValueError(arity_code)


def exact_payload_counts_for_depth(depth_bits: int) -> Counter[int]:
    seed_count = 1 << depth_bits
    result: Counter[int] = Counter()
    prev = 0
    for width in range(1, MAX_PAYLOAD_WIDTH_BITS + 1):
        cur = min(payload_width_count_le(width), seed_count)
        count = cur - prev
        if count > 0:
            result[width] = count
        prev = cur
        if prev >= seed_count:
            break
    return result


def source_costs_by_arity(
    max_arity: int, depth_bits: int, arity_code: str
) -> dict[int, Counter[int]]:
    if arity_code == "exact" and max_arity > 5:
        raise ValueError("exact V1/J3D1 arity coding only supports K<=5")
    payload_counts = exact_payload_counts_for_depth(depth_bits)
    result: dict[int, Counter[int]] = {}
    for arity in range(1, max_arity + 1):
        costs: Counter[int] = Counter()
        arity_bits = record_arity_cost(arity, max_arity, arity_code)
        for width, count in payload_counts.items():
            costs[arity_bits + j3d1_cost_for_payload_width(width)] += count
        result[arity] = costs
    return result


def match_probability(target_bits: int, condition_tail_bits: int) -> float:
    total = target_bits + condition_tail_bits
    if total >= 1074:
        return 0.0
    return 2.0 ** (-total)


def draw_q_next(rng: random.Random, state_bits: int, condition_tail_bits: int) -> int:
    if state_bits <= 0:
        return 0
    free_bits = max(0, state_bits - min(state_bits, condition_tail_bits))
    if free_bits == 0:
        return 0
    suffix = rng.getrandbits(free_bits)
    return suffix


def draw_candidates(
    rng: random.Random,
    source_costs: Counter[int],
    target_bits: int,
    arity: int,
    state_bits: int,
    policy: str,
    slack: int,
    condition_tail_bits: int,
    hit_cap: int,
) -> tuple[list[Candidate], int, int]:
    p = match_probability(target_bits, condition_tail_bits)
    if p <= 0.0:
        return [], 0, 0

    best_cost: int | None = None
    by_q: dict[int, Candidate] = {}
    raw_hits = 0
    truncated_hits = 0

    for cost in sorted(source_costs):
        if best_cost is not None:
            if policy == "shortest":
                break
            if cost > best_cost + slack:
                break

        hits = rng.binomialvariate(source_costs[cost], p)
        if hits <= 0:
            continue
        raw_hits += hits

        if best_cost is None:
            best_cost = cost

        if policy == "shortest":
            q_next = draw_q_next(rng, state_bits, condition_tail_bits)
            return [Candidate(cost=cost, arity=arity, q_next=q_next)], raw_hits, 0

        remaining = max(0, hit_cap - len(by_q)) if hit_cap > 0 else hits
        kept = min(hits, remaining)
        truncated_hits += hits - kept
        for _ in range(kept):
            q_next = draw_q_next(rng, state_bits, condition_tail_bits)
            old = by_q.get(q_next)
            if old is None or cost < old.cost:
                by_q[q_next] = Candidate(cost=cost, arity=arity, q_next=q_next)
        if hit_cap > 0 and len(by_q) >= hit_cap:
            break

    return list(by_q.values()), raw_hits, truncated_hits


def maybe_prune(
    frontier: dict[int, PathState], state_cap: int
) -> tuple[dict[int, PathState], int]:
    if state_cap <= 0 or len(frontier) <= state_cap:
        return frontier, 0
    kept_items = sorted(
        frontier.items(),
        key=lambda item: (item[1].cost, item[1].records, item[0]),
    )[:state_cap]
    return dict(kept_items), len(frontier) - state_cap


def cover_lengths(
    lengths: list[int],
    *,
    source_by_arity: dict[int, Counter[int]],
    max_arity: int,
    state_bits: int,
    policy: str,
    slack: int,
    arity_code: str,
    condition_tail_bits: int,
    seed: int,
    trial_index: int,
    pass_index: int,
    state_cap: int,
    hit_cap: int,
) -> CoverResult:
    item_count = len(lengths)
    prefix = [0]
    for length in lengths:
        prefix.append(prefix[-1] + length)

    frontiers: list[dict[int, PathState]] = [dict() for _ in range(item_count + 1)]
    frontiers[0][0] = PathState(cost=0, records=0, arity_sum=0, output_lengths=())

    sampled_edges = 0
    hit_edges = 0
    candidate_choices = 0
    truncated_hits = 0
    pruned_states = 0
    max_frontier_states = 1

    for start in range(item_count):
        states = sorted(
            frontiers[start].items(),
            key=lambda item: (item[1].cost, item[1].records, item[0]),
        )
        for q_state, path in states:
            for arity in range(1, max_arity + 1):
                end = start + arity
                if end > item_count:
                    break
                target_bits = prefix[end] - prefix[start]
                edge_seed = stable_seed(
                    "H175",
                    seed,
                    trial_index,
                    pass_index,
                    start,
                    q_state,
                    arity,
                    target_bits,
                    policy,
                    slack,
                    arity_code,
                    state_bits,
                    condition_tail_bits,
                )
                candidates, raw_hits, truncated = draw_candidates(
                    random.Random(edge_seed),
                    source_by_arity[arity],
                    target_bits,
                    arity,
                    state_bits,
                    policy,
                    slack,
                    condition_tail_bits,
                    hit_cap,
                )
                sampled_edges += 1
                truncated_hits += truncated
                if raw_hits:
                    hit_edges += 1
                candidate_choices += len(candidates)

                for candidate in candidates:
                    new_cost = path.cost + candidate.cost
                    old = frontiers[end].get(candidate.q_next)
                    if old is not None and (old.cost, old.records) <= (
                        new_cost,
                        path.records + 1,
                    ):
                        continue
                    frontiers[end][candidate.q_next] = PathState(
                        cost=new_cost,
                        records=path.records + 1,
                        arity_sum=path.arity_sum + arity,
                        output_lengths=path.output_lengths + (candidate.cost,),
                    )
                pruned_frontier, pruned = maybe_prune(frontiers[end], state_cap)
                if pruned:
                    frontiers[end] = pruned_frontier
                    pruned_states += pruned
                max_frontier_states = max(max_frontier_states, len(frontiers[end]))

    final_frontier = frontiers[item_count]
    if not final_frontier:
        return CoverResult(
            supported=False,
            input_bits=prefix[-1],
            output_bits=None,
            output_lengths=(),
            records=0,
            arity_sum=0,
            sampled_edges=sampled_edges,
            hit_edges=hit_edges,
            candidate_choices=candidate_choices,
            truncated_hits=truncated_hits,
            pruned_states=pruned_states,
            max_frontier_states=max_frontier_states,
        )

    best = min(final_frontier.values(), key=lambda state: (state.cost, state.records))
    return CoverResult(
        supported=True,
        input_bits=prefix[-1],
        output_bits=best.cost,
        output_lengths=best.output_lengths,
        records=best.records,
        arity_sum=best.arity_sum,
        sampled_edges=sampled_edges,
        hit_edges=hit_edges,
        candidate_choices=candidate_choices,
        truncated_hits=truncated_hits,
        pruned_states=pruned_states,
        max_frontier_states=max_frontier_states,
    )


def run_trial(
    *,
    block_bits: int,
    item_count: int,
    passes: int,
    source_by_arity: dict[int, Counter[int]],
    max_arity: int,
    state_bits: int,
    policy: str,
    slack: int,
    arity_code: str,
    condition_tail_bits: int,
    seed: int,
    trial_index: int,
    state_cap: int,
    hit_cap: int,
) -> TrialResult:
    lengths = [block_bits] * item_count
    pass_log2rho: list[float] = []
    first: CoverResult | None = None

    for pass_index in range(passes):
        result = cover_lengths(
            lengths,
            source_by_arity=source_by_arity,
            max_arity=max_arity,
            state_bits=state_bits,
            policy=policy,
            slack=slack,
            arity_code=arity_code,
            condition_tail_bits=condition_tail_bits,
            seed=seed,
            trial_index=trial_index,
            pass_index=pass_index,
            state_cap=state_cap,
            hit_cap=hit_cap,
        )
        if pass_index == 0:
            first = result
        if not result.supported or result.output_bits is None:
            return TrialResult(
                pass1=first or result,
                completed=False,
                final_bits=None,
                pass_log2rho=tuple(pass_log2rho),
            )
        pass_log2rho.append(math.log2(result.output_bits / result.input_bits))
        lengths = list(result.output_lengths)

    if first is None:
        raise RuntimeError("passes must be >= 1")
    return TrialResult(
        pass1=first,
        completed=True,
        final_bits=sum(lengths),
        pass_log2rho=tuple(pass_log2rho),
    )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(pct * len(ordered)) - 1))
    return ordered[index]


def finite_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def run_row(
    *,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    state_bits: int,
    policy: str,
    slack: int,
    arity_code: str,
    condition_tail_bits: int,
    item_count: int,
    passes: int,
    trials: int,
    seed: int,
    state_cap: int,
    hit_cap: int,
) -> Row:
    source_by_arity = source_costs_by_arity(max_arity, depth_bits, arity_code)
    trial_results = [
        run_trial(
            block_bits=block_bits,
            item_count=item_count,
            passes=passes,
            source_by_arity=source_by_arity,
            max_arity=max_arity,
            state_bits=state_bits,
            policy=policy,
            slack=slack,
            arity_code=arity_code,
            condition_tail_bits=condition_tail_bits,
            seed=seed,
            trial_index=trial,
            state_cap=state_cap,
            hit_cap=hit_cap,
        )
        for trial in range(trials)
    ]
    pass1_success = [trial.pass1 for trial in trial_results if trial.pass1.supported]
    completed = [trial for trial in trial_results if trial.completed and trial.final_bits is not None]
    sampled_edges = sum(trial.pass1.sampled_edges for trial in trial_results)
    hit_edges = sum(trial.pass1.hit_edges for trial in trial_results)
    candidate_choices = sum(trial.pass1.candidate_choices for trial in trial_results)
    records = sum(result.records for result in pass1_success)
    arity_sum = sum(result.arity_sum for result in pass1_success)
    pass_logs = [value for trial in trial_results for value in trial.pass_log2rho]
    final_logs = [
        math.log2(trial.final_bits / (block_bits * item_count))
        for trial in completed
        if trial.final_bits is not None
    ]

    avg_input = finite_mean([float(result.input_bits) for result in pass1_success])
    avg_output = finite_mean(
        [float(result.output_bits) for result in pass1_success if result.output_bits is not None]
    )
    return Row(
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        state_bits=state_bits,
        policy=policy_label(policy, slack),
        slack=slack,
        arity_code=arity_code,
        condition_tail_bits=condition_tail_bits,
        item_count=item_count,
        passes=passes,
        trials=trials,
        pass1_support=len(pass1_success) / trials if trials else 0.0,
        complete_support=len(completed) / trials if trials else 0.0,
        edge_hit_rate=hit_edges / sampled_edges if sampled_edges else 0.0,
        choices_per_hit=candidate_choices / hit_edges if hit_edges else 0.0,
        avg_input_bits=avg_input,
        avg_output_bits=avg_output,
        gain_per_atom=((avg_input - avg_output) / item_count if pass1_success else 0.0),
        records_per_atom=(records / (len(pass1_success) * item_count) if pass1_success else 0.0),
        avg_arity=(arity_sum / records if records else 0.0),
        mean_pass_log2rho=finite_mean(pass_logs),
        p95_pass_log2rho=percentile(pass_logs, 0.95),
        mean_final_log2rho=finite_mean(final_logs),
        max_frontier_states=max(
            (trial.pass1.max_frontier_states for trial in trial_results),
            default=0,
        ),
        pruned_states=sum(trial.pass1.pruned_states for trial in trial_results),
        truncated_hits=sum(trial.pass1.truncated_hits for trial in trial_results),
    )


def fmt(value: float) -> str:
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print("== state-carrying total-cover transducer ==")
    print(
        "q_next is observed digest tail state. Only --condition-tail-bits reduces "
        "match supply; state/checkpoint bits are not stored in these sequential rows."
    )
    print(
        f"{'B':>2} {'K':>3} {'D':>3} {'r':>3} {'policy':<9} {'N':>4} "
        f"{'P':>2} {'trials':>6} {'code':<7} {'cond':>4} "
        f"{'supp1':>7} {'suppP':>7} {'edgeHit':>8} {'choice/h':>8} "
        f"{'in':>8} {'out':>8} {'gain/a':>9} {'rec/a':>8} {'avgA':>6} "
        f"{'meanLog':>8} {'p95Log':>8} {'finalLog':>8} {'states':>7} "
        f"{'pruned':>8} {'trunc':>8}"
    )
    for row in rows:
        print(
            f"{row.block_bits:2d} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.state_bits:3d} {row.policy:<9} {row.item_count:4d} "
            f"{row.passes:2d} {row.trials:6d} {row.arity_code:<7} "
            f"{row.condition_tail_bits:4d} "
            f"{fmt(row.pass1_support):>7} {fmt(row.complete_support):>7} "
            f"{fmt(row.edge_hit_rate):>8} {fmt(row.choices_per_hit):>8} "
            f"{fmt(row.avg_input_bits):>8} {fmt(row.avg_output_bits):>8} "
            f"{fmt(row.gain_per_atom):>9} {fmt(row.records_per_atom):>8} "
            f"{fmt(row.avg_arity):>6} {fmt(row.mean_pass_log2rho):>8} "
            f"{fmt(row.p95_pass_log2rho):>8} {fmt(row.mean_final_log2rho):>8} "
            f"{row.max_frontier_states:7d} {row.pruned_states:8d} "
            f"{row.truncated_hits:8d}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    uncapped = [row for row in rows if row.pruned_states == 0 and row.truncated_hits == 0]
    if len(uncapped) != len(rows):
        print(
            "At least one row hit a cap; treat those rows as beam/capped telemetry, "
            "not exact sampled-DP evidence."
        )
    if not rows:
        return
    best_support = max(rows, key=lambda row: (row.complete_support, row.gain_per_atom))
    best_gain = max(rows, key=lambda row: (row.gain_per_atom, row.complete_support))
    print(
        f"Best complete-support row: B={best_support.block_bits},K={best_support.max_arity},"
        f"D={best_support.depth_bits},r={best_support.state_bits},"
        f"policy={best_support.policy}; support={best_support.complete_support:.6f}, "
        f"gain/atom={best_support.gain_per_atom:.6f}."
    )
    print(
        f"Best one-pass gain row: B={best_gain.block_bits},K={best_gain.max_arity},"
        f"D={best_gain.depth_bits},r={best_gain.state_bits},policy={best_gain.policy}; "
        f"support={best_gain.pass1_support:.6f}, gain/atom={best_gain.gain_per_atom:.6f}."
    )
    if any(row.condition_tail_bits for row in rows):
        print(
            "Rows with conditioned tail bits are supply-loss controls: they ask for "
            "specific control bits and therefore pay in hit probability."
        )
    print(
        "A state-tail lift is useful only if it improves paid full-cover support or "
        "log drift after exact record costs, without hidden anchors or selectors."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", action="append", default=[])
    parser.add_argument("--max-arity", action="append", default=[])
    parser.add_argument("--depth", action="append", default=[])
    parser.add_argument("--state-bits", action="append", default=[])
    parser.add_argument(
        "--policy",
        action="append",
        default=[],
        help="shortest, equal, or slack:N. Repeatable.",
    )
    parser.add_argument("--arity-code", choices=["exact", "fixed", "escape5"], default="exact")
    parser.add_argument("--condition-tail-bits", type=int, default=0)
    parser.add_argument("--items", type=int, default=32)
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=175175)
    parser.add_argument(
        "--state-cap",
        type=int,
        default=0,
        help="0 means no cap. Positive values beam-prune cheapest states per position.",
    )
    parser.add_argument(
        "--hit-cap",
        type=int,
        default=0,
        help="0 means no cap. Positive values cap retained q_next choices per edge.",
    )
    args = parser.parse_args()

    if args.passes < 1:
        raise ValueError("--passes must be >= 1")
    if args.condition_tail_bits < 0:
        raise ValueError("--condition-tail-bits must be non-negative")

    block_values = parse_int_list(args.block_bits, [8])
    arity_values = parse_int_list(args.max_arity, [5])
    depth_values = parse_int_list(args.depth, [80])
    state_values = parse_int_list(args.state_bits, [0, 8, 16])
    policies = [parse_policy(raw) for raw in (args.policy or ["shortest", "equal", "slack:2", "slack:4"])]

    rows: list[Row] = []
    for block_bits in block_values:
        for max_arity in arity_values:
            for depth_bits in depth_values:
                for state_bits in state_values:
                    for policy, slack in policies:
                        rows.append(
                            run_row(
                                block_bits=block_bits,
                                max_arity=max_arity,
                                depth_bits=depth_bits,
                                state_bits=state_bits,
                                policy=policy,
                                slack=slack,
                                arity_code=args.arity_code,
                                condition_tail_bits=args.condition_tail_bits,
                                item_count=args.items,
                                passes=args.passes,
                                trials=args.trials,
                                seed=args.seed,
                                state_cap=args.state_cap,
                                hit_cap=args.hit_cap,
                            )
                        )
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
