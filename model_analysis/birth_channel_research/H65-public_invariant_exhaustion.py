#!/usr/bin/env python3
"""H65 - public invariant exhaustion ledger.

This kernel reduces fixed boards, public permutations, CRT clocks, affine
orbits, canonical normal forms, EOF trimming, and profile schedules to the only
quantity that matters for stateless decode:

    how many final visible states can the decoder distinguish?

If a proposed public invariant claims more winning inputs than visible final
states, the excess is hidden path/profile/phase information. If the invariant
is truly public, it reduces eligible fraction or match supply instead.

The kernel is finite and exact at the counting level; it intentionally does not
enumerate individual codebooks because every codebook with the same visible
state count obeys the same pigeonhole bound.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


NEG_INF = float("-inf")


def log2_add(lhs: float, rhs: float) -> float:
    if lhs == NEG_INF:
        return rhs
    if rhs == NEG_INF:
        return lhs
    if rhs > lhs:
        lhs, rhs = rhs, lhs
    return lhs + math.log2(1.0 + 2.0 ** (rhs - lhs))


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return NEG_INF
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2.0)


def log2_eof_slots(n_bits: int, saving: int) -> float:
    if saving <= 0:
        return float(n_bits)
    max_len = n_bits - saving
    if max_len < 0:
        return NEG_INF
    # log2(2^(max_len+1)-1), stably.
    return (max_len + 1) + math.log2(1.0 - 2.0 ** (-(max_len + 1)))


def log2_path_apparent_slots(n_bits: int, passes: int, min_step: int) -> float:
    minimum = passes * min_step
    total = NEG_INF
    for saving in range(minimum, n_bits + 1):
        residual = saving - minimum
        path_log = log2_comb(residual + passes - 1, passes - 1)
        exact_final_log = n_bits - saving
        total = log2_add(total, path_log + exact_final_log)
    return total


@dataclass(frozen=True)
class Row:
    candidate: str
    n_bits: int
    passes: int
    min_step: int
    visible_log2_slots: float
    apparent_log2_slots: float
    public_loss_bits: float
    paid_selector_bits: float
    referee_bits: float

    @property
    def hidden_bits(self) -> float:
        return max(0.0, self.apparent_log2_slots - self.visible_log2_slots)

    @property
    def charged_log2_slots(self) -> float:
        unpaid = max(0.0, self.hidden_bits - self.paid_selector_bits - self.referee_bits)
        return self.apparent_log2_slots - self.paid_selector_bits - unpaid - self.public_loss_bits

    @property
    def visible_fraction(self) -> float:
        return 2.0 ** min(0.0, self.visible_log2_slots - self.n_bits)

    @property
    def apparent_fraction(self) -> float:
        return 2.0 ** min(0.0, self.apparent_log2_slots - self.n_bits)

    @property
    def charged_fraction(self) -> float:
        return 2.0 ** min(0.0, self.charged_log2_slots - self.n_bits)


def rows(
    n_bits: int,
    passes: int,
    min_step: int,
    profile_choices: int,
    lane_fraction: float,
    checksum_bits: float,
    safety_bits: float,
) -> list[Row]:
    saving = passes * min_step
    exact_visible = n_bits - saving
    eof_visible = log2_eof_slots(n_bits, saving)
    path_apparent = log2_path_apparent_slots(n_bits, passes, min_step)
    selector_bits = passes * math.log2(profile_choices) if profile_choices > 1 else 0.0
    referee = max(0.0, checksum_bits - safety_bits)
    lane_loss = -math.log2(lane_fraction) if lane_fraction > 0.0 else float("inf")

    return [
        Row(
            "fixed exact public path",
            n_bits,
            passes,
            min_step,
            exact_visible,
            exact_visible,
            0.0,
            0.0,
            0.0,
        ),
        Row(
            "EOF visible final states",
            n_bits,
            passes,
            min_step,
            eof_visible,
            eof_visible,
            0.0,
            0.0,
            0.0,
        ),
        Row(
            "variable path hidden",
            n_bits,
            passes,
            min_step,
            eof_visible,
            path_apparent,
            0.0,
            0.0,
            0.0,
        ),
        Row(
            "variable path with checksum referee",
            n_bits,
            passes,
            min_step,
            eof_visible,
            path_apparent,
            0.0,
            0.0,
            referee,
        ),
        Row(
            "best-of profile path paid",
            n_bits,
            passes,
            min_step,
            eof_visible,
            eof_visible + selector_bits,
            0.0,
            selector_bits,
            0.0,
        ),
        Row(
            "public lane mask",
            n_bits,
            passes,
            min_step,
            eof_visible,
            eof_visible,
            lane_loss,
            0.0,
            0.0,
        ),
    ]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def render(rows_: list[Row]) -> str:
    lines = [
        "# H65 - Public Invariant Exhaustion",
        "",
        "| candidate | n | P | s | visible fraction | apparent fraction | hidden bits | paid selector | referee | public loss | charged fraction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows_:
        lines.append(
            f"| {row.candidate} | {row.n_bits} | {row.passes} | {row.min_step} | "
            f"{fmt_prob(row.visible_fraction)} | {fmt_prob(row.apparent_fraction)} | "
            f"{fmt(row.hidden_bits)} | {fmt(row.paid_selector_bits)} | "
            f"{fmt(row.referee_bits)} | {fmt(row.public_loss_bits)} | "
            f"{fmt_prob(row.charged_fraction)} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A row is a possible public-invariant escape only if `charged fraction`",
            "exceeds the visible-state bound without hidden bits. In these rows,",
            "extra apparent coverage comes only from hidden path/profile choices or",
            "finite checksum budget. Public lanes reduce eligible fraction instead.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-bits", type=int, default=16)
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--min-step", type=int, default=1)
    parser.add_argument("--profile-choices", type=int, default=3)
    parser.add_argument("--lane-fraction", type=float, default=0.1)
    parser.add_argument("--checksum-bits", type=float, default=16.0)
    parser.add_argument("--safety-bits", type=float, default=4.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        render(
            rows(
                args.n_bits,
                args.passes,
                args.min_step,
                args.profile_choices,
                args.lane_fraction,
                args.checksum_bits,
                args.safety_bits,
            )
        )
    )


if __name__ == "__main__":
    main()
