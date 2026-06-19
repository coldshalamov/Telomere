#!/usr/bin/env python3
"""H214 - measured tail fertility with shuffle controls.

H212 showed that stored-seed tail steering is syntactically legal.  H214 asks
whether the tail state itself predicts actual next-pass fertility under the
uniform hash law.

For each first-pass exact witness candidate:

    target <- H1(seed)                 (matches current block)
    token  <- public record bits       (the emitted next-layer surface)
    q_tail <- digest tail state        (decoder-visible after reading seed)
    F_next <- actual best second-pass saving for token

Then the kernel compares:

* greedy current-cost choice;
* q-policy: choose q_tail == 0 within slack;
* measured lookahead: choose the candidate with best current_cost - F_next;
* shuffled-tail controls, including same-width/cost shuffles.

If q_tail has no real public fertility signal, q-policy gain should match the
shuffle controls.  Measured lookahead may still help, but then the useful state
is the searched future token itself, not the digest-tail class.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import sys
from collections import Counter, defaultdict
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


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def hash_bits(label: bytes, bits: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << bits) - 1)


def width_base_index(width: int) -> int:
    if width == 1:
        return 0
    return costs.payload_width_count_le(width - 1)


def seed_indices(max_width: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for width in range(1, max_width + 1):
        base = width_base_index(width)
        for offset in range(costs.payload_width_count_exact(width)):
            out.append((base + offset, width))
    return out


@dataclass(frozen=True)
class Candidate:
    seed_index: int
    width: int
    cost: int
    tail_state: int
    future_saving: int


@dataclass(frozen=True)
class Row:
    block_bits: int
    arity: int
    w1: int
    w2: int
    states: int
    slack: int
    trials: int
    covered: int
    mean_candidates: float
    token_classes: int
    class_bits: int
    mean_future_saving: float
    tail0_future: float
    tail_other_future: float
    tail_lift: float
    same_width_tail_lift: float
    q_tail_rate: float
    measured_tail_rate: float
    q_slack_paid: float
    measured_slack_paid: float
    q_actual_net: float
    measured_actual_net: float
    q_shuffle_net: float
    width_shuffle_net: float
    verdict: str


def possible_cost_classes(arity: int, w1: int) -> set[int]:
    return {costs.record_cost_for_payload_width(arity, width) for _idx, width in seed_indices(w1)}


def target_for_trial(seed: int, trial: int, bits: int) -> int:
    return hash_bits(b"H214-target\0" + seed.to_bytes(8, "big") + trial.to_bytes(8, "big"), bits)


def token_value_for_candidate(seed: int, trial: int, seed_index: int, token_len: int) -> int:
    return hash_bits(
        b"H214-token\0"
        + seed.to_bytes(8, "big")
        + trial.to_bytes(8, "big")
        + seed_index.to_bytes(8, "big"),
        token_len,
    )


def future_saving(
    *,
    token_len: int,
    token_value: int,
    arity: int,
    w2: int,
    class_bits: int,
    raw_mode_bits: int,
) -> int:
    raw_cost = token_len + raw_mode_bits
    best = raw_cost
    for seed_index, width in seed_indices(w2):
        value = hash_bits(
            b"H214-pass2\0" + token_len.to_bytes(2, "big") + seed_index.to_bytes(8, "big"),
            token_len,
        )
        if value != token_value:
            continue
        best = min(best, costs.record_cost_for_payload_width(arity, width) + class_bits)
    return raw_cost - best


def candidates_by_trial(
    *,
    block_bits: int,
    arity: int,
    w1: int,
    w2: int,
    states: int,
    trials: int,
    seed: int,
    raw_mode_bits: int,
) -> tuple[list[list[Candidate]], int]:
    target_bits = block_bits * arity
    class_bits = ceil_log2(len(possible_cost_classes(arity, w1)))
    out: list[list[Candidate]] = []
    state_bits = max(1, ceil_log2(states))
    first_seeds = seed_indices(w1)
    for trial in range(trials):
        target = target_for_trial(seed, trial, target_bits)
        row: list[Candidate] = []
        for seed_index, width in first_seeds:
            cost = costs.record_cost_for_payload_width(arity, width)
            label = (
                b"H214-pass1\0"
                + seed.to_bytes(8, "big")
                + trial.to_bytes(8, "big")
                + seed_index.to_bytes(8, "big")
            )
            if hash_bits(label + b"prefix", target_bits) != target:
                continue
            token_value = token_value_for_candidate(seed, trial, seed_index, cost)
            saving = future_saving(
                token_len=cost,
                token_value=token_value,
                arity=arity,
                w2=w2,
                class_bits=class_bits,
                raw_mode_bits=raw_mode_bits,
            )
            tail_state = hash_bits(label + b"tail", state_bits) % states
            row.append(
                Candidate(
                    seed_index=seed_index,
                    width=width,
                    cost=cost,
                    tail_state=tail_state,
                    future_saving=saving,
                )
            )
        out.append(row)
    return out, class_bits


def choose_greedy(candidates: list[Candidate]) -> Candidate:
    return min(candidates, key=lambda item: (item.cost, item.width, item.seed_index))


def choose_q_policy(candidates: list[Candidate], greedy: Candidate, slack: int) -> Candidate:
    eligible = [item for item in candidates if item.cost <= greedy.cost + slack]
    tail0 = [item for item in eligible if item.tail_state == 0]
    if not tail0:
        return greedy
    return min(tail0, key=lambda item: (item.cost, item.width, item.seed_index))


def choose_measured(candidates: list[Candidate], greedy: Candidate, slack: int) -> Candidate:
    eligible = [item for item in candidates if item.cost <= greedy.cost + slack]
    return min(
        eligible,
        key=lambda item: (
            item.cost - item.future_saving,
            item.cost,
            item.width,
            item.seed_index,
        ),
    )


def policy_net(greedy: Candidate, chosen: Candidate) -> int:
    return (greedy.cost - chosen.cost) + (chosen.future_saving - greedy.future_saving)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def tail_stats(all_candidates: list[Candidate]) -> tuple[float, float, float, float]:
    tail0 = [item.future_saving for item in all_candidates if item.tail_state == 0]
    other = [item.future_saving for item in all_candidates if item.tail_state != 0]
    lift = mean(tail0) - mean(other)
    buckets: dict[tuple[int, int], list[Candidate]] = defaultdict(list)
    for item in all_candidates:
        buckets[(item.width, item.cost)].append(item)
    weighted_lifts: list[float] = []
    for bucket in buckets.values():
        b0 = [item.future_saving for item in bucket if item.tail_state == 0]
        bo = [item.future_saving for item in bucket if item.tail_state != 0]
        if b0 and bo:
            weighted_lifts.append(mean(b0) - mean(bo))
    return mean(tail0), mean(other), lift, mean(weighted_lifts)


def shuffled_q_net(
    by_trial: list[list[Candidate]],
    *,
    slack: int,
    rng: random.Random,
    same_width: bool,
) -> float:
    flat = [item for row in by_trial for item in row]
    if same_width:
        grouped: dict[tuple[int, int], list[int]] = defaultdict(list)
        for item in flat:
            grouped[(item.width, item.cost)].append(item.tail_state)
        for values in grouped.values():
            rng.shuffle(values)
        offsets: Counter[tuple[int, int]] = Counter()
        shuffled: dict[tuple[int, int], int] = {}
        for item in flat:
            key = (item.width, item.cost)
            shuffled[(item.seed_index, item.cost)] = grouped[key][offsets[key]]
            offsets[key] += 1
    else:
        tails = [item.tail_state for item in flat]
        rng.shuffle(tails)
        shuffled = {
            (item.seed_index, item.cost): tail for item, tail in zip(flat, tails, strict=False)
        }

    nets: list[float] = []
    for row in by_trial:
        if not row:
            continue
        remapped = [
            Candidate(
                seed_index=item.seed_index,
                width=item.width,
                cost=item.cost,
                tail_state=shuffled[(item.seed_index, item.cost)],
                future_saving=item.future_saving,
            )
            for item in row
        ]
        greedy = choose_greedy(row)
        chosen = choose_q_policy(remapped, greedy, slack)
        original = next(
            item for item in row if item.seed_index == chosen.seed_index and item.cost == chosen.cost
        )
        nets.append(policy_net(greedy, original))
    return mean(nets)


def run_row(
    *,
    block_bits: int,
    arity: int,
    w1: int,
    w2: int,
    states: int,
    slack: int,
    trials: int,
    seed: int,
    raw_mode_bits: int,
    shuffles: int,
) -> Row:
    by_trial, class_bits = candidates_by_trial(
        block_bits=block_bits,
        arity=arity,
        w1=w1,
        w2=w2,
        states=states,
        trials=trials,
        seed=seed,
        raw_mode_bits=raw_mode_bits,
    )
    covered_rows = [row for row in by_trial if row]
    all_candidates = [item for row in covered_rows for item in row]
    q_nets: list[float] = []
    measured_nets: list[float] = []
    q_slacks: list[float] = []
    measured_slacks: list[float] = []
    q_tail = 0
    measured_tail = 0
    for row_items in covered_rows:
        greedy = choose_greedy(row_items)
        q_choice = choose_q_policy(row_items, greedy, slack)
        measured_choice = choose_measured(row_items, greedy, slack)
        q_nets.append(policy_net(greedy, q_choice))
        measured_nets.append(policy_net(greedy, measured_choice))
        q_slacks.append(q_choice.cost - greedy.cost)
        measured_slacks.append(measured_choice.cost - greedy.cost)
        q_tail += int(q_choice.tail_state == 0)
        measured_tail += int(measured_choice.tail_state == 0)

    rng = random.Random(seed + 214)
    q_shuffle = mean(
        [
            shuffled_q_net(covered_rows, slack=slack, rng=rng, same_width=False)
            for _ in range(shuffles)
        ]
    )
    width_shuffle = mean(
        [
            shuffled_q_net(covered_rows, slack=slack, rng=rng, same_width=True)
            for _ in range(shuffles)
        ]
    )
    tail0, tail_other, lift, width_lift = tail_stats(all_candidates)
    token_classes = len(possible_cost_classes(arity, w1))
    q_actual = mean(q_nets)
    measured_actual = mean(measured_nets)
    verdict = "tail_signal" if q_actual > max(q_shuffle, width_shuffle) + 0.05 else "no_tail_signal"
    if measured_actual > q_actual + 0.05:
        verdict += "+measured_lookahead"
    return Row(
        block_bits=block_bits,
        arity=arity,
        w1=w1,
        w2=w2,
        states=states,
        slack=slack,
        trials=trials,
        covered=len(covered_rows),
        mean_candidates=len(all_candidates) / len(covered_rows) if covered_rows else 0.0,
        token_classes=token_classes,
        class_bits=class_bits,
        mean_future_saving=mean([item.future_saving for item in all_candidates]),
        tail0_future=tail0,
        tail_other_future=tail_other,
        tail_lift=lift,
        same_width_tail_lift=width_lift,
        q_tail_rate=q_tail / len(covered_rows) if covered_rows else 0.0,
        measured_tail_rate=measured_tail / len(covered_rows) if covered_rows else 0.0,
        q_slack_paid=mean(q_slacks),
        measured_slack_paid=mean(measured_slacks),
        q_actual_net=q_actual,
        measured_actual_net=measured_actual,
        q_shuffle_net=q_shuffle,
        width_shuffle_net=width_shuffle,
        verdict=verdict,
    )


def parse_int_list(text: str) -> list[int]:
    return [int(part) for part in text.split(",") if part]


def print_rows(args: argparse.Namespace) -> None:
    rows = [
        run_row(
            block_bits=args.block_bits,
            arity=args.arity,
            w1=args.w1,
            w2=args.w2,
            states=states,
            slack=slack,
            trials=args.trials,
            seed=args.seed,
            raw_mode_bits=args.raw_mode_bits,
            shuffles=args.shuffles,
        )
        for states in parse_int_list(args.states)
        for slack in parse_int_list(args.slack)
    ]
    print("== H214 measured tail fertility ==")
    print("q-policy is compared with shuffled-tail controls; measured lookahead uses actual F_next.")
    print(
        f"{'S':>4} {'slack':>5} {'cov':>5} {'cand':>7} {'cls':>3} {'cB':>3} "
        f"{'meanF':>7} {'tailLift':>9} {'wLift':>9} {'qTail':>7} {'mTail':>7} "
        f"{'qSlack':>8} {'mSlack':>8} {'qNet':>8} {'mNet':>8} "
        f"{'qShuf':>8} {'wShuf':>8} {'verdict':>24}"
    )
    for row in rows:
        print(
            f"{row.states:4d} {row.slack:5d} {row.covered:5d} "
            f"{fmt(row.mean_candidates):>7} {row.token_classes:3d} {row.class_bits:3d} "
            f"{fmt(row.mean_future_saving):>7} {fmt(row.tail_lift):>9} "
            f"{fmt(row.same_width_tail_lift):>9} {fmt(row.q_tail_rate):>7} "
            f"{fmt(row.measured_tail_rate):>7} {fmt(row.q_slack_paid):>8} "
            f"{fmt(row.measured_slack_paid):>8} {fmt(row.q_actual_net):>8} "
            f"{fmt(row.measured_actual_net):>8} {fmt(row.q_shuffle_net):>8} "
            f"{fmt(row.width_shuffle_net):>8} {row.verdict:>24}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Under an independent uniform hash law, digest-tail state is an observed")
    print("label, not a fertility source.  If q-policy lift does not beat shuffled")
    print("tail controls, H212's future_credit is not native.  Exact measured")
    print("lookahead can still improve subset cases by searching future tokens,")
    print("but then the useful information is the future token match itself and")
    print("must pass the recursive support/raw-fallback ledger.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", type=int, default=8)
    parser.add_argument("--arity", type=int, default=1)
    parser.add_argument("--w1", type=int, default=8)
    parser.add_argument("--w2", type=int, default=8)
    parser.add_argument("--states", default="2,4,16")
    parser.add_argument("--slack", default="0,1,2")
    parser.add_argument("--trials", type=int, default=512)
    parser.add_argument("--seed", type=int, default=214)
    parser.add_argument("--raw-mode-bits", type=int, default=1)
    parser.add_argument("--shuffles", type=int, default=32)
    args = parser.parse_args()
    print_rows(args)
    print_theorem()


if __name__ == "__main__":
    main()
