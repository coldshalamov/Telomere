#!/usr/bin/env python3
"""H176 - finite-state width grammar + mixed-radix payload packing.

H175 made salt decoder-derived:

    z = H(q_i, arity_i, seed_i) -> x_i || q_{i+1}

but exact V1/J3D1 still paid a per-record self-delimiting seed-width bill and
the emitted record surface stopped being recursively coverable.

H176 asks the next narrow question: if witness payload width is a fixed public
function of decoder-known state, can we remove the Lotus width delimiter and
keep enough exact-witness supply for total-cover recursion?

This is a random-oracle sampled trellis, not a corpus compressor. Width laws are
frozen public schedules such as:

    fixed:8             w = 8
    cycle:6,8,10        w = cycle[position mod 3]
    state:6,8,10,12     w = table[q mod len(table)]
    span_margin:2       w = max(1, arity*B - arity_bits - 2)
    arity_margin:2      w = max(1, target_bits - arity_bits - 2)
    abs_margin:6        w = max(1, target_bits - 6)
    periodic_margin:1,3 w = max(1, target_bits - arity_bits - table[pos mod 2])
    union_arity_margin:1,4
    arity:4:3           w = 4 + 3*(arity-1)

The decoder knows the schedule before reading payload. A whole layer may pack
payload ranks as one mixed-radix integer, charged as

    sum arity_bits + ceil(sum log2(M_i))

where M_i is the public witness inventory for record i. Recursive rows use the
inline-equivalent item lengths for the next layer; the packed column is the
best same-path layer bit bill, not a hidden selector.
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
    arity_cost,
    payload_width_count_le,
)


INF = 10**30
LN2 = math.log(2.0)


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


def parse_int_list(raw: str) -> list[int]:
    return [int(part) for part in raw.split(",") if part]


def parse_repeatable(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(parse_int_list(value))
    return out


def state_count(state_bits: int) -> int:
    return 1 << max(0, state_bits)


def arity_bits_for(arity: int, *, max_arity: int, arity_code: str) -> int:
    if arity_code == "v1":
        if arity > 5:
            raise ValueError("v1 arity code only supports K<=5")
        return arity_cost(arity)
    if arity_code == "fixed":
        if not 1 <= arity <= max_arity:
            raise ValueError("arity out of fixed-code range")
        return ceil_log2(max_arity)
    raise ValueError(arity_code)


def widths_from_schedule(
    schedule: str,
    *,
    q_state: int,
    position: int,
    arity: int,
    max_arity: int,
    arity_code: str,
    block_bits: int,
    depth_bits: int,
    target_bits: int,
) -> int:
    a_bits = arity_bits_for(arity, max_arity=max_arity, arity_code=arity_code)
    if schedule.startswith("fixed:"):
        widths = [int(schedule.split(":", 1)[1])]
    elif schedule.startswith("cycle:"):
        values = parse_int_list(schedule.split(":", 1)[1])
        widths = [values[position % len(values)]]
    elif schedule.startswith("state:"):
        values = parse_int_list(schedule.split(":", 1)[1])
        widths = [values[q_state % len(values)]]
    elif schedule.startswith("span_margin:"):
        margin = int(schedule.split(":", 1)[1])
        widths = [arity * block_bits - a_bits - margin]
    elif schedule.startswith("arity_margin:"):
        slack = int(schedule.split(":", 1)[1])
        widths = [target_bits - a_bits - slack]
    elif schedule.startswith("abs_margin:"):
        margin = int(schedule.split(":", 1)[1])
        widths = [target_bits - margin]
    elif schedule.startswith("periodic_margin:"):
        values = parse_int_list(schedule.split(":", 1)[1])
        margin = values[position % len(values)]
        widths = [target_bits - a_bits - margin]
    elif schedule.startswith("union_arity_margin:"):
        slacks = parse_int_list(schedule.split(":", 1)[1])
        widths = [target_bits - a_bits - slack for slack in slacks]
    elif schedule.startswith("arity:"):
        _, base, step = schedule.split(":")
        widths = [int(base) + int(step) * (arity - 1)]
    else:
        raise ValueError(f"unknown schedule {schedule!r}")
    return tuple(sorted({max(1, min(width, depth_bits)) for width in widths}))


def depth_clamped_exact_width_count(width: int, depth_bits: int) -> int:
    """Reachable exact-width seed count inside the first 2**D seed indices."""

    depth_count = 1 << depth_bits
    upper = min(payload_width_count_le(width), depth_count)
    lower = min(payload_width_count_le(width - 1), depth_count)
    return max(0, upper - lower)


def inventory_for_widths(widths: tuple[int, ...], depth_bits: int, mode: str) -> tuple[int, float, int]:
    """Return (M, payload_log_bits, inline_payload_bits).

    M is the number of candidate witnesses made available by the public width
    or width set.
    payload_log_bits is what a mixed-radix layer pays for this rank.
    inline_payload_bits is the record-local payload length used for recursive
    surface lengths.
    """

    depth_count = 1 << depth_bits
    if mode == "power":
        m = sum(1 << min(width, depth_bits) for width in widths)
        bits = ceil_log2(m)
        return m, float(bits), bits
    if mode == "lotus_bucket":
        m = sum(depth_clamped_exact_width_count(width, depth_bits) for width in widths)
        bits = ceil_log2(m)
        return m, math.log2(m) if m else 0.0, bits
    if mode == "lotus_prefix":
        width = max(widths)
        m = min(payload_width_count_le(width), depth_count)
        return m, math.log2(m), ceil_log2(m)
    raise ValueError(mode)


def hit_probability_for_target(candidates: int, target_bits: int) -> float:
    if candidates <= 0:
        return 0.0
    if target_bits <= 0:
        return 1.0
    if target_bits < 900:
        p = 2.0 ** (-target_bits)
        log_miss = candidates * math.log1p(-p)
        if log_miss < -745.0:
            return 1.0
        return -math.expm1(log_miss)

    # For very long spans p underflows as a float. The Poisson limit is the
    # numerically stable random-oracle law here because p is astronomically
    # small and the reachable witness count is large.
    log_lambda = math.log(candidates) - target_bits * LN2
    if log_lambda > 50.0:
        return 1.0
    if log_lambda < -50.0:
        return math.exp(log_lambda)
    return -math.expm1(-math.exp(log_lambda))


def draw_q_values(
    rng: random.Random,
    candidates: int,
    target_bits: int,
    state_bits: int,
    hit_cap: int,
) -> list[int]:
    if candidates <= 0:
        return []
    if state_bits <= 0:
        return [0] if rng.random() < hit_probability_for_target(candidates, target_bits) else []
    states = state_count(state_bits)
    base = candidates // states
    rem = candidates % states
    out: list[int] = []
    for q_state in range(states):
        q_candidates = base + (1 if q_state < rem else 0)
        if rng.random() < hit_probability_for_target(q_candidates, target_bits):
            out.append(q_state)
            if hit_cap > 0 and len(out) >= hit_cap:
                break
    return out


@dataclass(frozen=True)
class Candidate:
    q_next: int
    objective_bits: float
    inline_bits: int
    arity_bits: int
    payload_log_bits: float
    arity: int


@dataclass(frozen=True)
class PathState:
    objective_bits: float
    inline_bits: int
    arity_bits: int
    payload_log_bits: float
    records: int
    arity_sum: int
    output_lengths: tuple[int, ...]

    @property
    def packed_bits(self) -> int:
        return self.arity_bits + math.ceil(self.payload_log_bits)


@dataclass(frozen=True)
class CoverResult:
    supported: bool
    input_bits: int
    objective_bits: float
    inline_bits: int
    packed_bits: int
    records: int
    arity_sum: int
    output_lengths: tuple[int, ...]
    sampled_edges: int
    hit_edges: int
    choices: int
    max_states: int
    pruned_states: int
    truncated_hits: int

    @property
    def avg_arity(self) -> float:
        return self.arity_sum / self.records if self.records else 0.0


@dataclass(frozen=True)
class TrialResult:
    first: CoverResult
    completed: bool
    pass_logs_inline: tuple[float, ...]
    pass_logs_packed: tuple[float, ...]
    final_inline_bits: int | None
    final_packed_bits: int | None


@dataclass(frozen=True)
class Row:
    block_bits: int
    max_arity: int
    arity_code: str
    depth_bits: int
    state_bits: int
    schedule: str
    inventory: str
    objective: str
    items: int
    passes: int
    trials: int
    support1: float
    support_p: float
    edge_hit: float
    choices_per_hit_edge: float
    input_bits: float
    inline_bits: float
    packed_bits: float
    inline_gain_per_atom: float
    packed_gain_per_atom: float
    records_per_atom: float
    avg_arity: float
    mean_log_inline: float
    mean_log_packed: float
    p95_log_inline: float
    max_states: int
    pruned_states: int
    truncated_hits: int


def maybe_prune(frontier: dict[int, PathState], state_cap: int) -> tuple[dict[int, PathState], int]:
    if state_cap <= 0 or len(frontier) <= state_cap:
        return frontier, 0
    kept = sorted(
        frontier.items(),
        key=lambda item: (item[1].objective_bits, item[1].inline_bits, item[0]),
    )[:state_cap]
    return dict(kept), len(frontier) - state_cap


def cover_lengths(
    lengths: list[int],
    *,
    block_bits: int,
    max_arity: int,
    arity_code: str,
    depth_bits: int,
    state_bits: int,
    schedule: str,
    inventory: str,
    objective: str,
    trial_index: int,
    pass_index: int,
    seed: int,
    state_cap: int,
    hit_cap: int,
) -> CoverResult:
    item_count = len(lengths)
    prefix = [0]
    for length in lengths:
        prefix.append(prefix[-1] + length)

    frontiers: list[dict[int, PathState]] = [dict() for _ in range(item_count + 1)]
    frontiers[0][0] = PathState(
        objective_bits=0.0,
        inline_bits=0,
        arity_bits=0,
        payload_log_bits=0.0,
        records=0,
        arity_sum=0,
        output_lengths=(),
    )

    sampled_edges = 0
    hit_edges = 0
    choices = 0
    max_states = 1
    pruned_states = 0
    truncated_hits = 0

    for start in range(item_count):
        for q_state, path in sorted(
            frontiers[start].items(),
            key=lambda item: (item[1].objective_bits, item[1].inline_bits, item[0]),
        ):
            for arity in range(1, min(max_arity, item_count - start) + 1):
                target_bits = prefix[start + arity] - prefix[start]
                widths = widths_from_schedule(
                    schedule,
                    q_state=q_state,
                    position=start,
                    arity=arity,
                    max_arity=max_arity,
                    arity_code=arity_code,
                    block_bits=block_bits,
                    depth_bits=depth_bits,
                    target_bits=target_bits,
                )
                m, payload_log_bits, inline_payload_bits = inventory_for_widths(
                    widths, depth_bits, inventory
                )
                sampled_edges += 1
                if m <= 0:
                    continue
                edge_seed = stable_seed(
                    "H176",
                    seed,
                    trial_index,
                    pass_index,
                    start,
                    q_state,
                    arity,
                    target_bits,
                    widths,
                    schedule,
                    inventory,
                    objective,
                )
                rng = random.Random(edge_seed)
                q_values = draw_q_values(rng, m, target_bits, state_bits, hit_cap)
                if not q_values:
                    continue
                hit_edges += 1
                choices += len(q_values)
                if hit_cap > 0:
                    truncated_hits += max(0, state_count(state_bits) - hit_cap)

                a_bits = arity_bits_for(arity, max_arity=max_arity, arity_code=arity_code)
                inline_edge_bits = a_bits + inline_payload_bits
                packed_edge_bits = a_bits + payload_log_bits
                objective_bits = inline_edge_bits if objective == "inline" else packed_edge_bits

                for q_next in q_values:
                    old = frontiers[start + arity].get(q_next)
                    new = PathState(
                        objective_bits=path.objective_bits + objective_bits,
                        inline_bits=path.inline_bits + inline_edge_bits,
                        arity_bits=path.arity_bits + a_bits,
                        payload_log_bits=path.payload_log_bits + payload_log_bits,
                        records=path.records + 1,
                        arity_sum=path.arity_sum + arity,
                        output_lengths=path.output_lengths + (inline_edge_bits,),
                    )
                    if old is not None and (
                        old.objective_bits,
                        old.inline_bits,
                        old.records,
                    ) <= (new.objective_bits, new.inline_bits, new.records):
                        continue
                    frontiers[start + arity][q_next] = new
                pruned_frontier, pruned = maybe_prune(frontiers[start + arity], state_cap)
                if pruned:
                    frontiers[start + arity] = pruned_frontier
                    pruned_states += pruned
                max_states = max(max_states, len(frontiers[start + arity]))

    final = frontiers[item_count]
    if not final:
        return CoverResult(
            supported=False,
            input_bits=prefix[-1],
            objective_bits=0.0,
            inline_bits=0,
            packed_bits=0,
            records=0,
            arity_sum=0,
            output_lengths=(),
            sampled_edges=sampled_edges,
            hit_edges=hit_edges,
            choices=choices,
            max_states=max_states,
            pruned_states=pruned_states,
            truncated_hits=truncated_hits,
        )

    best = min(final.values(), key=lambda state: (state.objective_bits, state.inline_bits, state.records))
    return CoverResult(
        supported=True,
        input_bits=prefix[-1],
        objective_bits=best.objective_bits,
        inline_bits=best.inline_bits,
        packed_bits=best.packed_bits,
        records=best.records,
        arity_sum=best.arity_sum,
        output_lengths=best.output_lengths,
        sampled_edges=sampled_edges,
        hit_edges=hit_edges,
        choices=choices,
        max_states=max_states,
        pruned_states=pruned_states,
        truncated_hits=truncated_hits,
    )


def run_trial(
    *,
    block_bits: int,
    max_arity: int,
    arity_code: str,
    depth_bits: int,
    state_bits: int,
    schedule: str,
    inventory: str,
    objective: str,
    items: int,
    passes: int,
    trial_index: int,
    seed: int,
    state_cap: int,
    hit_cap: int,
) -> TrialResult:
    lengths = [block_bits] * items
    first: CoverResult | None = None
    logs_inline: list[float] = []
    logs_packed: list[float] = []
    final_inline = None
    final_packed = None

    for pass_index in range(passes):
        result = cover_lengths(
            lengths,
            block_bits=block_bits,
            max_arity=max_arity,
            arity_code=arity_code,
            depth_bits=depth_bits,
            state_bits=state_bits,
            schedule=schedule,
            inventory=inventory,
            objective=objective,
            trial_index=trial_index,
            pass_index=pass_index,
            seed=seed,
            state_cap=state_cap,
            hit_cap=hit_cap,
        )
        if pass_index == 0:
            first = result
        if not result.supported:
            return TrialResult(
                first=first or result,
                completed=False,
                pass_logs_inline=tuple(logs_inline),
                pass_logs_packed=tuple(logs_packed),
                final_inline_bits=None,
                final_packed_bits=None,
            )
        logs_inline.append(math.log2(result.inline_bits / result.input_bits))
        logs_packed.append(math.log2(result.packed_bits / result.input_bits))
        final_inline = result.inline_bits
        final_packed = result.packed_bits
        lengths = list(result.output_lengths)

    assert first is not None
    return TrialResult(
        first=first,
        completed=True,
        pass_logs_inline=tuple(logs_inline),
        pass_logs_packed=tuple(logs_packed),
        final_inline_bits=final_inline,
        final_packed_bits=final_packed,
    )


def finite_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct) - 1))
    return ordered[idx]


def run_row(args: argparse.Namespace, schedule: str, objective: str, state_bits: int) -> Row:
    trials = [
        run_trial(
            block_bits=args.block_bits,
            max_arity=args.max_arity,
            arity_code=args.arity_code,
            depth_bits=args.depth_bits,
            state_bits=state_bits,
            schedule=schedule,
            inventory=args.inventory,
            objective=objective,
            items=args.items,
            passes=args.passes,
            trial_index=i,
            seed=args.seed,
            state_cap=args.state_cap,
            hit_cap=args.hit_cap,
        )
        for i in range(args.trials)
    ]
    pass1 = [trial.first for trial in trials if trial.first.supported]
    completed = [trial for trial in trials if trial.completed]
    sampled = sum(trial.first.sampled_edges for trial in trials)
    hit_edges = sum(trial.first.hit_edges for trial in trials)
    choices = sum(trial.first.choices for trial in trials)
    records = sum(result.records for result in pass1)
    arities = sum(result.arity_sum for result in pass1)
    logs_inline = [value for trial in trials for value in trial.pass_logs_inline]
    logs_packed = [value for trial in trials for value in trial.pass_logs_packed]

    avg_input = finite_mean([float(result.input_bits) for result in pass1])
    avg_inline = finite_mean([float(result.inline_bits) for result in pass1])
    avg_packed = finite_mean([float(result.packed_bits) for result in pass1])
    return Row(
        block_bits=args.block_bits,
        max_arity=args.max_arity,
        arity_code=args.arity_code,
        depth_bits=args.depth_bits,
        state_bits=state_bits,
        schedule=schedule,
        inventory=args.inventory,
        objective=objective,
        items=args.items,
        passes=args.passes,
        trials=args.trials,
        support1=len(pass1) / args.trials if args.trials else 0.0,
        support_p=len(completed) / args.trials if args.trials else 0.0,
        edge_hit=hit_edges / sampled if sampled else 0.0,
        choices_per_hit_edge=choices / hit_edges if hit_edges else 0.0,
        input_bits=avg_input,
        inline_bits=avg_inline,
        packed_bits=avg_packed,
        inline_gain_per_atom=(avg_input - avg_inline) / args.items if pass1 else 0.0,
        packed_gain_per_atom=(avg_input - avg_packed) / args.items if pass1 else 0.0,
        records_per_atom=records / (len(pass1) * args.items) if pass1 else 0.0,
        avg_arity=arities / records if records else 0.0,
        mean_log_inline=finite_mean(logs_inline),
        mean_log_packed=finite_mean(logs_packed),
        p95_log_inline=percentile(logs_inline, 0.95),
        max_states=max((trial.first.max_states for trial in trials), default=0),
        pruned_states=sum(trial.first.pruned_states for trial in trials),
        truncated_hits=sum(trial.first.truncated_hits for trial in trials),
    )


def fmt(value: float) -> str:
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print("== H176 finite-state width grammar / mixed-radix rows ==")
    print(
        "Widths are public schedules. Inline bits are the recursive surface; "
        "packed bits are same-path layer arithmetic packing."
    )
    print(
        f"{'sched':<18} {'inv':<12} {'obj':<7} {'acode':<5} {'B':>2} {'K':>3} {'D':>3} "
        f"{'r':>3} {'N':>4} {'P':>2} {'supp1':>7} {'suppP':>7} "
        f"{'edge':>7} {'choice':>7} {'in':>8} {'inline':>8} {'packed':>8} "
        f"{'gainI/a':>9} {'gainP/a':>9} {'rec/a':>7} {'avgA':>6} "
        f"{'logI':>8} {'logP':>8} {'p95I':>8} {'states':>6} {'prune':>6} {'trunc':>6}"
    )
    for row in rows:
        print(
            f"{row.schedule:<18} {row.inventory:<12} {row.objective:<7} "
            f"{row.arity_code:<5} {row.block_bits:2d} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.state_bits:3d} {row.items:4d} {row.passes:2d} "
            f"{fmt(row.support1):>7} {fmt(row.support_p):>7} "
            f"{fmt(row.edge_hit):>7} {fmt(row.choices_per_hit_edge):>7} "
            f"{fmt(row.input_bits):>8} {fmt(row.inline_bits):>8} "
            f"{fmt(row.packed_bits):>8} {fmt(row.inline_gain_per_atom):>9} "
            f"{fmt(row.packed_gain_per_atom):>9} {fmt(row.records_per_atom):>7} "
            f"{fmt(row.avg_arity):>6} {fmt(row.mean_log_inline):>8} "
            f"{fmt(row.mean_log_packed):>8} {fmt(row.p95_log_inline):>8} "
            f"{row.max_states:6d} {row.pruned_states:6d} {row.truncated_hits:6d}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    if any(row.pruned_states or row.truncated_hits for row in rows):
        print("Some rows were capped; do not promote capped rows as exact evidence.")
    if not rows:
        return
    supported_rows = [row for row in rows if row.support1 > 0.0]
    if not supported_rows:
        print("No first-pass supported rows in this sweep.")
        return
    best_inline = max(supported_rows, key=lambda row: (row.support_p, row.inline_gain_per_atom))
    best_packed = max(supported_rows, key=lambda row: (row.support_p, row.packed_gain_per_atom))
    print(
        f"Best recursive inline row: {best_inline.schedule}, r={best_inline.state_bits}, "
        f"supportP={best_inline.support_p:.6f}, gainI/a={best_inline.inline_gain_per_atom:.6f}."
    )
    print(
        f"Best same-path packed row: {best_packed.schedule}, r={best_packed.state_bits}, "
        f"supportP={best_packed.support_p:.6f}, gainP/a={best_packed.packed_gain_per_atom:.6f}."
    )
    print(
        "A positive packed row is only a layer-packing target unless its inline or "
        "parser-equivalent surface also stays recursively coverable."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--arity-code", choices=["v1", "fixed"], default="v1")
    parser.add_argument("--depth-bits", type=int, default=12)
    parser.add_argument("--state-bits", action="append", default=[])
    parser.add_argument("--schedule", action="append", default=[])
    parser.add_argument("--inventory", choices=["power", "lotus_bucket", "lotus_prefix"], default="power")
    parser.add_argument("--objective", choices=["inline", "packed", "both"], default="both")
    parser.add_argument("--items", type=int, default=16)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--state-cap", type=int, default=0)
    parser.add_argument("--hit-cap", type=int, default=0)
    parser.add_argument("--seed", type=int, default=176176)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.arity_code == "v1" and args.max_arity > 5:
        raise ValueError("v1 arity code supports K<=5; use --arity-code fixed for larger K")
    state_values = parse_repeatable(args.state_bits, [0, 4])
    schedules = args.schedule or [
        "fixed:8",
        "arity_margin:0",
        "arity_margin:1",
        "arity_margin:2",
        "arity_margin:4",
        "abs_margin:4",
        "abs_margin:6",
        "periodic_margin:1,3",
        "union_arity_margin:1,4",
    ]
    objectives = ["inline", "packed"] if args.objective == "both" else [args.objective]
    rows = [
        run_row(args, schedule=schedule, objective=objective, state_bits=state_bits)
        for schedule in schedules
        for objective in objectives
        for state_bits in state_values
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
