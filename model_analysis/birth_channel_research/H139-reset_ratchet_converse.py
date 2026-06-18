#!/usr/bin/env python3
"""H139 - reset/ratchet converse harness.

H138 models reset suffix dynamics. H139 is a stricter acceptance test for any
reset/stop/ratchet claim:

* How many total saving bits S are claimed?
* What fraction of uniform inputs can have outputs that short?
* How small must the bad/reset probability be for survival?
* How many bits are owed for variable length/reset paths?
* Do hidden best-of choices cancel after selector payment?

This is not a compression search. It is a counting ledger for proposed reset
mechanisms.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RatchetAuditRow:
    label: str
    n_bits: int
    passes: int
    saving_per_pass: float
    coverage_claim: float
    visible_state_bits: float
    hidden_choices: float
    total_saving: float
    prefix_bound: float
    eof_bound: float
    eps_max_for_survival: float
    loser_expansion_needed: float
    length_path_bits: float
    charged_saving: float
    charged_prefix_bound: float
    apparent_hidden_bound: float
    paid_hidden_bound: float


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("inf")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def prefix_bound(saving_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    return 2.0 ** (-saving_bits)


def eof_bound(n_bits: int, saving_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    return max(0.0, min(1.0, (2.0 ** (1.0 - saving_bits)) - (2.0 ** (-n_bits))))


def audit(
    label: str,
    n_bits: int,
    passes: int,
    saving_per_pass: float,
    coverage_claim: float,
    visible_state_bits: float = 0.0,
    hidden_choices: float = 1.0,
) -> RatchetAuditRow:
    total_saving = passes * saving_per_pass
    eps_max = 1.0 - (coverage_claim ** (1.0 / passes)) if passes > 0 else 0.0
    loser_expansion = (
        coverage_claim * total_saving / (1.0 - coverage_claim)
        if coverage_claim < 1.0
        else float("inf")
    )
    # If each pass can save a variable number of units, a path of P positive
    # parts summing to S has C(S-1,P-1) possibilities. For non-integer S, this
    # rounds up to the next claimed bit inventory.
    total_units = math.ceil(total_saving)
    path_bits = log2_comb(total_units - 1, passes - 1) if total_units >= passes and passes > 0 else 0.0
    charged_saving = total_saving - visible_state_bits - path_bits
    charged_prefix = prefix_bound(charged_saving)
    raw_prefix = prefix_bound(total_saving)
    apparent_hidden = min(1.0, hidden_choices * raw_prefix)
    paid_hidden = raw_prefix
    return RatchetAuditRow(
        label=label,
        n_bits=n_bits,
        passes=passes,
        saving_per_pass=saving_per_pass,
        coverage_claim=coverage_claim,
        visible_state_bits=visible_state_bits,
        hidden_choices=hidden_choices,
        total_saving=total_saving,
        prefix_bound=raw_prefix,
        eof_bound=eof_bound(n_bits, total_saving),
        eps_max_for_survival=eps_max,
        loser_expansion_needed=loser_expansion,
        length_path_bits=path_bits,
        charged_saving=charged_saving,
        charged_prefix_bound=charged_prefix,
        apparent_hidden_bound=apparent_hidden,
        paid_hidden_bound=paid_hidden,
    )


def rows() -> list[RatchetAuditRow]:
    return [
        audit("P64_s1_c90", 1024, 64, 1.0, 0.90),
        audit("P64_s1_c90_state64", 1024, 64, 1.0, 0.90, visible_state_bits=64.0),
        audit("P64_s1_c90_hidden2^32", 1024, 64, 1.0, 0.90, hidden_choices=2.0**32),
        audit("P128_s1_c90", 1024, 128, 1.0, 0.90),
        audit("P256_s0.25_c90", 1024, 256, 0.25, 0.90),
        audit("P4096_s0.01_c90", 1024, 4096, 0.01, 0.90),
        audit("P4096_s0.1_c90", 4096, 4096, 0.10, 0.90),
        audit("P4096_s1_c90", 8192, 4096, 1.0, 0.90),
    ]


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def print_rows(result: list[RatchetAuditRow]) -> None:
    print("== reset/ratchet converse audit ==")
    print(
        f"{'label':<22} {'S':>8} {'prefix c':>11} {'EOF c':>11} "
        f"{'eps max':>10} {'loser E':>10} {'path bits':>10} "
        f"{'charged S':>10} {'charged c':>11} {'hidden free':>11} {'hidden paid':>11}"
    )
    for item in result:
        print(
            f"{item.label:<22} {item.total_saving:8.3f} "
            f"{fmt_prob(item.prefix_bound):>11} {fmt_prob(item.eof_bound):>11} "
            f"{item.eps_max_for_survival:10.6g} {item.loser_expansion_needed:10.3f} "
            f"{item.length_path_bits:10.3f} {item.charged_saving:10.3f} "
            f"{fmt_prob(item.charged_prefix_bound):>11} "
            f"{fmt_prob(item.apparent_hidden_bound):>11} {fmt_prob(item.paid_hidden_bound):>11}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Reset/ratchet schemes can change the engineering surface, but after "
        "counting short-output inventory, length/reset paths, visible final "
        "state, and hidden-choice selectors, high roughly-all coverage with "
        "positive total saving is not available under the uniform law."
    )
    print(
        "A finite hidden best-of multiplier can make apparent coverage larger, "
        "but the paid selector returns to the raw prefix bound. Visible state "
        "or variable reset paths subtract from the claimed saving before the "
        "coverage bound is applied."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading()


if __name__ == "__main__":
    main()
