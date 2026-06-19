#!/usr/bin/env python3
"""H212 - bounded-slack witness lookahead.

Equal-cost or near-equal witness choice is not a separate selector if the
selected seed is itself stored.  The decoder reads the seed and derives any
digest-tail state from it.  This kernel measures the option value of that legal
choice in the smallest random-oracle model:

* each target block has exact witnesses up to Wmax;
* greedy picks the shortest witness;
* lookahead may pick a witness within `slack` extra bits if its digest tail is
  in a public future-fertile class;
* the selected seed pays its actual record cost, so slack is charged.

The future credit is deliberately explicit.  Without a real public fertility
law behind that credit, the result is only an option-value ledger, not a
compression proof.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import sys
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


def hash_bits(label: bytes, bits: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << bits) - 1)


def payload_width_count_exact(width: int) -> int:
    return costs.payload_width_count_exact(width)


def width_base_index(width: int) -> int:
    if width == 1:
        return 0
    return costs.payload_width_count_le(width - 1)


@dataclass(frozen=True)
class Candidate:
    seed_index: int
    width: int
    cost: int
    tail_state: int


@dataclass(frozen=True)
class Row:
    block_bits: int
    arity: int
    w_max: int
    slack: int
    states: int
    future_credit: float
    trials: int
    covered: int
    mean_candidates: float
    greedy_tail_rate: float
    lookahead_tail_rate: float
    mean_greedy_cost: float
    mean_lookahead_cost: float
    mean_slack_paid: float
    mean_future_credit_gain: float
    two_pass_gain: float
    needed_credit_per_new_tail: float
    poisson_success: float
    miss_tax: float


def candidates_for_trial(
    *,
    trial: int,
    block_bits: int,
    arity: int,
    w_max: int,
    states: int,
    seed: int,
) -> list[Candidate]:
    target_bits = block_bits * arity
    target = hash_bits(b"H212-target\0" + seed.to_bytes(8, "big") + trial.to_bytes(8, "big"), target_bits)
    out: list[Candidate] = []
    for width in range(1, w_max + 1):
        base = width_base_index(width)
        count = payload_width_count_exact(width)
        cost = costs.record_cost_for_payload_width(arity, width)
        for offset in range(count):
            seed_index = base + offset
            label = (
                b"H212-seed\0"
                + seed.to_bytes(8, "big")
                + trial.to_bytes(8, "big")
                + arity.to_bytes(2, "big")
                + width.to_bytes(2, "big")
                + seed_index.to_bytes(8, "big")
            )
            if hash_bits(label + b"prefix", target_bits) != target:
                continue
            tail_state = hash_bits(label + b"tail", max(1, math.ceil(math.log2(states)))) % states
            out.append(Candidate(seed_index=seed_index, width=width, cost=cost, tail_state=tail_state))
    return out


def choose_greedy(candidates: list[Candidate]) -> Candidate:
    return min(candidates, key=lambda item: (item.cost, item.width, item.seed_index))


def choose_lookahead(
    candidates: list[Candidate],
    *,
    greedy_cost: int,
    slack: int,
    future_credit: float,
) -> Candidate:
    eligible = [item for item in candidates if item.cost <= greedy_cost + slack]
    return min(
        eligible,
        key=lambda item: (
            item.cost - (future_credit if item.tail_state == 0 else 0.0),
            item.cost,
            item.width,
            item.seed_index,
        ),
    )


def run_row(
    *,
    block_bits: int,
    arity: int,
    w_max: int,
    slack: int,
    states: int,
    future_credit: float,
    trials: int,
    seed: int,
) -> Row:
    covered = 0
    total_candidates = 0
    greedy_tail = 0
    look_tail = 0
    greedy_cost_sum = 0.0
    look_cost_sum = 0.0
    slack_sum = 0.0
    future_gain_sum = 0.0
    two_pass_gain_sum = 0.0
    new_tail = 0

    for trial in range(trials):
        candidates = candidates_for_trial(
            trial=trial,
            block_bits=block_bits,
            arity=arity,
            w_max=w_max,
            states=states,
            seed=seed,
        )
        if not candidates:
            continue
        covered += 1
        total_candidates += len(candidates)
        greedy = choose_greedy(candidates)
        look = choose_lookahead(
            candidates,
            greedy_cost=greedy.cost,
            slack=slack,
            future_credit=future_credit,
        )
        g_tail = greedy.tail_state == 0
        l_tail = look.tail_state == 0
        greedy_tail += int(g_tail)
        look_tail += int(l_tail)
        greedy_cost_sum += greedy.cost
        look_cost_sum += look.cost
        slack_paid = look.cost - greedy.cost
        slack_sum += slack_paid
        future_gain = (future_credit if l_tail else 0.0) - (future_credit if g_tail else 0.0)
        future_gain_sum += future_gain
        two_pass_gain_sum += (greedy.cost - look.cost) + future_gain
        if l_tail and not g_tail:
            new_tail += 1

    if covered == 0:
        return Row(
            block_bits,
            arity,
            w_max,
            slack,
            states,
            future_credit,
            trials,
            covered,
            0.0,
            0.0,
            0.0,
            math.inf,
            math.inf,
            math.inf,
            0.0,
            -math.inf,
            math.inf,
            0.0,
            math.inf,
        )

    mean_candidates = total_candidates / covered
    poisson_success = 1.0 - math.exp(-mean_candidates / states)
    miss_tax = -math.log2(poisson_success) if poisson_success > 0.0 else math.inf
    needed = (slack_sum / new_tail) if new_tail else math.inf
    return Row(
        block_bits=block_bits,
        arity=arity,
        w_max=w_max,
        slack=slack,
        states=states,
        future_credit=future_credit,
        trials=trials,
        covered=covered,
        mean_candidates=mean_candidates,
        greedy_tail_rate=greedy_tail / covered,
        lookahead_tail_rate=look_tail / covered,
        mean_greedy_cost=greedy_cost_sum / covered,
        mean_lookahead_cost=look_cost_sum / covered,
        mean_slack_paid=slack_sum / covered,
        mean_future_credit_gain=future_gain_sum / covered,
        two_pass_gain=two_pass_gain_sum / covered,
        needed_credit_per_new_tail=needed,
        poisson_success=poisson_success,
        miss_tax=miss_tax,
    )


def parse_int_list(text: str) -> list[int]:
    return [int(part) for part in text.split(",") if part]


def parse_float_list(text: str) -> list[float]:
    return [float(part) for part in text.split(",") if part]


def print_rows(args: argparse.Namespace) -> None:
    slacks = parse_int_list(args.slack)
    states_list = parse_int_list(args.states)
    credits = parse_float_list(args.future_credit)
    rows = [
        run_row(
            block_bits=args.block_bits,
            arity=args.arity,
            w_max=args.w_max,
            slack=slack,
            states=states,
            future_credit=credit,
            trials=args.trials,
            seed=args.seed,
        )
        for slack in slacks
        for states in states_list
        for credit in credits
    ]
    print("== H212 bounded-slack witness lookahead ==")
    print("Stored seed carries tail state; future credit is explicit and not free.")
    print(
        f"{'B':>3} {'A':>2} {'W':>3} {'slack':>5} {'S':>4} {'credit':>7} "
        f"{'cov':>6} {'cand':>7} {'gTail':>7} {'lTail':>7} "
        f"{'slackPd':>8} {'fGain':>8} {'2pGain':>8} {'needC':>8} {'missTax':>8}"
    )
    for row in rows:
        print(
            f"{row.block_bits:3d} {row.arity:2d} {row.w_max:3d} {row.slack:5d} "
            f"{row.states:4d} {fmt(row.future_credit):>7} {row.covered:6d} "
            f"{fmt(row.mean_candidates):>7} {fmt(row.greedy_tail_rate):>7} "
            f"{fmt(row.lookahead_tail_rate):>7} {fmt(row.mean_slack_paid):>8} "
            f"{fmt(row.mean_future_credit_gain):>8} {fmt(row.two_pass_gain):>8} "
            f"{fmt(row.needed_credit_per_new_tail):>8} {fmt(row.miss_tax):>8}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Equal-cost choice is free only because the chosen seed is the record.")
    print("Near-equal choice pays its extra record bits.  A requested digest-tail")
    print("state appears with multiplicity probability; forcing it thins supply or")
    print("pays slack.  Therefore lookahead can harvest a real public future value,")
    print("but it does not create that value under a uniform hash law.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", type=int, default=8)
    parser.add_argument("--arity", type=int, default=1)
    parser.add_argument("--w-max", type=int, default=8)
    parser.add_argument("--slack", default="0,1,2,4")
    parser.add_argument("--states", default="2,4,16")
    parser.add_argument("--future-credit", default="0,0.5,1,2")
    parser.add_argument("--trials", type=int, default=512)
    parser.add_argument("--seed", type=int, default=212)
    args = parser.parse_args()

    random.seed(args.seed)
    print_rows(args)
    print_theorem()


if __name__ == "__main__":
    main()
