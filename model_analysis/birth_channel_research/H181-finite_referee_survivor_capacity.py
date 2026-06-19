#!/usr/bin/env python3
"""H181 - finite referee / survivor capacity accounting.

This kernel tests whether a stateless checksum, trial-decode referee, or
non-prefix survivor filter can hide many parse/witness choices cheaply.

The favorable model is:

* the correct reading is guaranteed to pass the stored/root referee;
* each wrong reading survives independently with probability 2^-c;
* the decoder is stateless except for public/root/end data;
* every hidden branch bit is treated as a real candidate reading unless it is
  made public by the record itself.

If there are M possible readings, the expected false survivors are

    lambda_false = (M - 1) * 2^-c ~= 2^(log2(M) - c)

and unique decode has probability exp(-lambda_false).  To make ambiguity rare,
the referee needs c ~= log2(M) + safety bits.  That is the whole hidden branch
entropy plus a reliability margin; a fixed small referee only works for bounded
M and fails as records or passes grow.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from dataclasses import dataclass


LN2 = math.log(2.0)


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode("ascii"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest(), "big")


def parse_float_list(values: list[str], default: list[float]) -> list[float]:
    if not values:
        return default
    out: list[float] = []
    for value in values:
        out.extend(float(part) for part in value.split(",") if part)
    return out


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def log2_false_survivors(log2_m: float, referee_bits: int) -> float:
    return log2_m - float(referee_bits)


def expected_false_survivors(log2_false: float) -> float:
    if log2_false > 1023.0:
        return math.inf
    if log2_false < -1074.0:
        return 0.0
    return 2.0**log2_false


def p_unique_from_log2_false(log2_false: float) -> float:
    """Probability that no wrong candidate survives, Poisson approximation.

    The approximation is exact enough for the intended accounting rows.  It is
    conservative in the direction that matters here: once log2_false is large,
    uniqueness is effectively zero.
    """

    lam = expected_false_survivors(log2_false)
    if lam == 0.0:
        return 1.0
    if math.isinf(lam) or lam > 745.0:
        return 0.0
    return math.exp(-lam)


def required_referee_bits(log2_m: float, target_unique: float) -> int:
    if not 0.0 < target_unique < 1.0:
        raise ValueError("target_unique must be in (0, 1)")
    # exp(-2^(log2_m-c)) >= target_unique
    # c >= log2_m - log2(-ln(target_unique))
    safety = -math.log2(-math.log(target_unique))
    return math.ceil(log2_m + safety)


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    if value == 0.0:
        return "0"
    abs_value = abs(value)
    if abs_value >= 1_000_000.0 or abs_value < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


@dataclass(frozen=True)
class Row:
    branch_factor: float
    records: int
    passes: int
    referee_bits: int
    log2_m: float
    log2_false: float
    false_survivors: float
    p_unique: float
    hidden_bits_per_step: float
    paid_bits_per_step: float
    unpriced_ambiguity_bits: float
    verdict: str


def classify(row: Row, target_unique: float) -> str:
    if row.p_unique >= target_unique:
        if row.paid_bits_per_step + 1e-12 >= row.hidden_bits_per_step:
            return "unique but paid branch entropy"
        return "bounded tiny row only"
    if row.unpriced_ambiguity_bits > 0.0:
        return "ambiguous; underpriced hidden channel"
    return "ambiguous tail"


def make_row(
    *,
    branch_factor: float,
    records: int,
    passes: int,
    referee_bits: int,
    target_unique: float,
) -> Row:
    steps = records * passes
    hidden_bits_per_step = math.log2(branch_factor)
    log2_m = steps * hidden_bits_per_step
    log2_false = log2_false_survivors(log2_m, referee_bits)
    paid_bits_per_step = referee_bits / steps
    row = Row(
        branch_factor=branch_factor,
        records=records,
        passes=passes,
        referee_bits=referee_bits,
        log2_m=log2_m,
        log2_false=log2_false,
        false_survivors=expected_false_survivors(log2_false),
        p_unique=p_unique_from_log2_false(log2_false),
        hidden_bits_per_step=hidden_bits_per_step,
        paid_bits_per_step=paid_bits_per_step,
        unpriced_ambiguity_bits=max(0.0, log2_false),
        verdict="",
    )
    return Row(**{**row.__dict__, "verdict": classify(row, target_unique)})


@dataclass(frozen=True)
class RequiredRow:
    branch_factor: float
    records: int
    passes: int
    target_unique: float
    log2_m: float
    required_bits: int
    hidden_bits_per_step: float
    paid_bits_per_step: float
    excess_bits_per_step: float


def make_required_row(
    *,
    branch_factor: float,
    records: int,
    passes: int,
    target_unique: float,
) -> RequiredRow:
    steps = records * passes
    hidden_bits_per_step = math.log2(branch_factor)
    log2_m = steps * hidden_bits_per_step
    required_bits = required_referee_bits(log2_m, target_unique)
    paid_bits_per_step = required_bits / steps
    return RequiredRow(
        branch_factor=branch_factor,
        records=records,
        passes=passes,
        target_unique=target_unique,
        log2_m=log2_m,
        required_bits=required_bits,
        hidden_bits_per_step=hidden_bits_per_step,
        paid_bits_per_step=paid_bits_per_step,
        excess_bits_per_step=paid_bits_per_step - hidden_bits_per_step,
    )


def exact_trial_unique_probability(
    *,
    candidates: int,
    referee_bits: int,
    trials: int,
    seed: int,
) -> float:
    """Exact tiny simulation for the favorable one-true-candidate model."""

    if candidates < 1:
        raise ValueError("candidates must be >= 1")
    if referee_bits < 0:
        raise ValueError("referee_bits must be >= 0")
    rng = random.Random(stable_seed("H181", candidates, referee_bits, trials, seed))
    modulus = 1 << referee_bits
    unique = 0
    for _ in range(trials):
        target = rng.randrange(modulus)
        false_hit = False
        for _ in range(candidates - 1):
            if rng.randrange(modulus) == target:
                false_hit = True
                break
        if not false_hit:
            unique += 1
    return unique / trials if trials else 0.0


def print_referee_table(args: argparse.Namespace) -> None:
    branch_factors = parse_float_list(args.branch_factor, [2.0, 4.0, 8.0])
    records_values = parse_int_list(args.records, [8, 32, 128])
    pass_values = parse_int_list(args.passes, [1, 2, 4, 8, 16])
    referee_values = parse_int_list(args.referee_bits, [8, 16, 32, 64, 128])

    print("== H181 finite referee / survivor capacity ==")
    print(
        "Favorable model: one true parse always passes; false parses survive "
        "with probability 2^-c."
    )
    print(
        f"{'b':>5} {'R':>5} {'P':>4} {'c':>5} {'log2M':>10} "
        f"{'Efalse':>12} {'p_unique':>10} {'hid/step':>10} "
        f"{'paid/step':>10} {'ambig_bits':>11} {'verdict':<34}"
    )
    for branch_factor in branch_factors:
        for records in records_values:
            for passes in pass_values:
                for referee_bits in referee_values:
                    row = make_row(
                        branch_factor=branch_factor,
                        records=records,
                        passes=passes,
                        referee_bits=referee_bits,
                        target_unique=args.target_unique,
                    )
                    print(
                        f"{row.branch_factor:5.1f} {row.records:5d} {row.passes:4d} "
                        f"{row.referee_bits:5d} {fmt(row.log2_m):>10} "
                        f"{fmt(row.false_survivors):>12} {fmt(row.p_unique):>10} "
                        f"{fmt(row.hidden_bits_per_step):>10} "
                        f"{fmt(row.paid_bits_per_step):>10} "
                        f"{fmt(row.unpriced_ambiguity_bits):>11} {row.verdict:<34}"
                    )


def print_required_table(args: argparse.Namespace) -> None:
    branch_factors = parse_float_list(args.branch_factor, [2.0, 4.0, 8.0])
    records_values = parse_int_list(args.records, [8, 32, 128])
    pass_values = parse_int_list(args.passes, [1, 2, 4, 8, 16])

    print()
    print("== required referee bits for reliable stateless decode ==")
    print(
        "Required c is the branch entropy log2(M) plus the safety margin needed "
        "to make false survivors rare."
    )
    print(
        f"{'b':>5} {'R':>5} {'P':>4} {'target':>8} {'log2M':>10} "
        f"{'c_req':>7} {'hid/step':>10} {'paid/step':>10} "
        f"{'excess/step':>12}"
    )
    for branch_factor in branch_factors:
        for records in records_values:
            for passes in pass_values:
                row = make_required_row(
                    branch_factor=branch_factor,
                    records=records,
                    passes=passes,
                    target_unique=args.target_unique,
                )
                print(
                    f"{row.branch_factor:5.1f} {row.records:5d} {row.passes:4d} "
                    f"{fmt(row.target_unique):>8} {fmt(row.log2_m):>10} "
                    f"{row.required_bits:7d} {fmt(row.hidden_bits_per_step):>10} "
                    f"{fmt(row.paid_bits_per_step):>10} {fmt(row.excess_bits_per_step):>12}"
                )


def structural_effective_options(opening_choices: int, structural_filter_bits: float) -> float:
    if opening_choices < 1:
        raise ValueError("opening_choices must be >= 1")
    return 1.0 + (opening_choices - 1.0) * (2.0 ** (-structural_filter_bits))


def print_structural_filter_table(args: argparse.Namespace) -> None:
    opening_choices_values = parse_int_list(args.opening_choices, [64, 655, 65536])
    filter_values = parse_float_list(args.structural_filter_bits, [0.0, 4.0, 9.36])
    records_values = parse_int_list(args.records, [8, 32, 128])

    print()
    print("== structural pruning knee ==")
    print(
        "If each wrong opening survives E public structural bits, effective local "
        "ambiguity is M_eff=1+(T-1)2^-E."
    )
    print(
        f"{'T':>8} {'E':>8} {'Meff':>12} {'bill/rec':>10} "
        f"{'R':>5} {'log2S':>10} {'c_req99':>8} {'reading':<36}"
    )
    for opening_choices in opening_choices_values:
        for structural_filter_bits in filter_values:
            m_eff = structural_effective_options(opening_choices, structural_filter_bits)
            bill_per_record = math.log2(m_eff)
            for records in records_values:
                log2_s = records * bill_per_record
                c_req = required_referee_bits(log2_s, args.target_unique)
                if opening_choices <= 2.0**structural_filter_bits:
                    reading = "finite knee; near-bounded"
                else:
                    reading = "slope returns after filter"
                print(
                    f"{opening_choices:8d} {fmt(structural_filter_bits):>8} "
                    f"{fmt(m_eff):>12} {fmt(bill_per_record):>10} "
                    f"{records:5d} {fmt(log2_s):>10} {c_req:8d} {reading:<36}"
                )


def print_exact_check(args: argparse.Namespace) -> None:
    if args.exact_candidates <= 0:
        return
    measured = exact_trial_unique_probability(
        candidates=args.exact_candidates,
        referee_bits=args.exact_referee_bits,
        trials=args.exact_trials,
        seed=args.seed,
    )
    log2_m = math.log2(args.exact_candidates)
    predicted = p_unique_from_log2_false(log2_m - args.exact_referee_bits)
    print()
    print("== exact tiny referee check ==")
    print(
        f"candidates={args.exact_candidates} c={args.exact_referee_bits} "
        f"trials={args.exact_trials} measured={fmt(measured)} "
        f"poisson_pred={fmt(predicted)}"
    )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A finite referee is not a free stateless birth/open channel.")
    print("For M hidden readings and c referee bits, expected false survivors are about M/2^c.")
    print("Reliable unique decode needs c = log2(M) + safety bits.")
    print("A structural filter of E bits only changes M to 1+(T-1)2^-E.")
    print("Therefore any hidden branch savings are cancelled by the referee bill,")
    print("unless the branch choices are already public in the emitted records or")
    print("the source is restricted to a bounded/generated class whose membership tax is paid.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-factor", action="append", default=[])
    parser.add_argument("--records", action="append", default=[])
    parser.add_argument("--passes", action="append", default=[])
    parser.add_argument("--referee-bits", action="append", default=[])
    parser.add_argument("--opening-choices", action="append", default=[])
    parser.add_argument("--structural-filter-bits", action="append", default=[])
    parser.add_argument("--target-unique", type=float, default=0.99)
    parser.add_argument("--exact-candidates", type=int, default=4096)
    parser.add_argument("--exact-referee-bits", type=int, default=20)
    parser.add_argument("--exact-trials", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=181181)
    args = parser.parse_args()

    print_referee_table(args)
    print_required_table(args)
    print_structural_filter_table(args)
    print_exact_check(args)
    print_theorem()


if __name__ == "__main__":
    main()
