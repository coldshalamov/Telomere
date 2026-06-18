#!/usr/bin/env python3
"""H109 - non-prefix / trial-decode referee capacity.

After H108, a natural remaining loophole is to leave the prefix record stream:
let the decoder try many parses/openings and keep the checksum winner. This is
exactly the keep-what-decodes shape, so the bill is the number of surviving
readings.

For an ambiguous length language with codeword lengths L, the number of parses
of an m-bit stream obeys:

    A_0 = 1
    A_m = sum_{l in L, l<=m} A_{m-l}

The omitted delimiter/selector information is log2 A_m. A fixed C-bit checksum
can referee only log2 A_m <= C (minus safety). For arbitrary file length, the
ambiguity grows exponentially at rate log2(lambda), where lambda is the largest
root of sum_l lambda^-l = 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    name: str
    lengths: tuple[int, ...]


LANGUAGES = [
    Language("fixed8", (8,)),
    Language("fib_1_2", (1, 2)),
    Language("byte_or_marker", (8, 9)),
    Language("record_7_16", (7, 16)),
    Language("lotus_toy", (7, 8, 9, 10, 11, 12, 13, 14, 15, 16)),
]


def ambiguity_count(lengths: tuple[int, ...], bits: int) -> int:
    dp = [0] * (bits + 1)
    dp[0] = 1
    for total in range(1, bits + 1):
        dp[total] = sum(dp[total - length] for length in lengths if length <= total)
    return dp[bits]


def ambiguity_log2(lengths: tuple[int, ...], bits: int) -> float:
    """Return log2(A_bits) without constructing enormous integers."""

    return ambiguity_log2_table(lengths, bits)[bits]


def ambiguity_log2_table(lengths: tuple[int, ...], bits: int) -> list[float]:
    """Return log2(A_m) for all m<=bits."""

    log_dp = [float("-inf")] * (bits + 1)
    log_dp[0] = 0.0
    for total in range(1, bits + 1):
        terms = [
            log_dp[total - length]
            for length in lengths
            if length <= total and math.isfinite(log_dp[total - length])
        ]
        if not terms:
            continue
        peak = max(terms)
        log_dp[total] = peak + math.log2(sum(2.0 ** (term - peak) for term in terms))
    return log_dp


def prefix_max_ambiguity_log2(lengths: tuple[int, ...], bits: int) -> float:
    """Return max_m<=bits log2(A_m), the monotone referee liability."""

    return max(ambiguity_log2_table(lengths, bits))


def ambiguity_rate(lengths: tuple[int, ...]) -> float:
    """Return log2(lambda), where sum(lambda^-l)=1."""

    if len(lengths) == 1:
        return 0.0

    def f(lam: float) -> float:
        return sum(lam ** (-length) for length in lengths) - 1.0

    lo = 1.0
    hi = 2.0
    while f(hi) > 0.0:
        hi *= 2.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return math.log2((lo + hi) / 2.0)


def max_bits_for_referee(lengths: tuple[int, ...], checksum_bits: int, safety_bits: int = 0) -> int | None:
    if len(lengths) == 1:
        return None

    limit = max(0, checksum_bits - safety_bits)
    lo = 0
    hi = 1
    while prefix_max_ambiguity_log2(lengths, hi) <= limit:
        lo = hi
        hi *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if prefix_max_ambiguity_log2(lengths, mid) <= limit:
            lo = mid
        else:
            hi = mid
    return lo


def fmt_referee_frontier(bits: int | None) -> str:
    return "unbounded" if bits is None else str(bits)


def print_language_table() -> None:
    print("== non-prefix ambiguity rate ==")
    print("A fixed checksum can select one reading only while log2(A_m) is below its budget.")
    print(
        f"{'language':<14} {'lengths':<24} {'rate bits/bit':>14} "
        f"{'m@64':>8} {'m@64-32safe':>14}"
    )
    for language in LANGUAGES:
        rate = ambiguity_rate(language.lengths)
        m64 = max_bits_for_referee(language.lengths, 64, 0)
        m32 = max_bits_for_referee(language.lengths, 64, 32)
        print(
            f"{language.name:<14} {str(language.lengths):<24} "
            f"{rate:14.6f} {fmt_referee_frontier(m64):>10} "
            f"{fmt_referee_frontier(m32):>14}"
        )
    print()


def print_exact_examples() -> None:
    print("== exact examples ==")
    print(f"{'language':<14} {'m':>6} {'log2 A_m':>12} {'false@C64 log2':>16}")
    for language in LANGUAGES:
        for bits in (64, 256, 1024):
            count = ambiguity_count(language.lengths, bits)
            log_count = math.log2(count) if count > 0 else float("-inf")
            print(
                f"{language.name:<14} {bits:6d} {log_count:12.6f} "
                f"{log_count - 64:16.6f}"
            )
        print()


def print_open_carry_connection() -> None:
    print("== open/carry connection ==")
    print("A carried record with T possible opening walks is the same ledger:")
    print("A = T^R, log2 A = R*log2(T).")
    print(f"{'T':>6} {'R':>8} {'log2 A':>12} {'64-bit enough?':>15}")
    for passes, records in ((64, 10), (64, 100), (256, 8), (256, 100)):
        bits = records * math.log2(passes)
        print(f"{passes:6d} {records:8d} {bits:12.3f} {str(bits <= 64):>15}")
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Non-prefix/trial-decode syntax can be a finite engineering tool, but "
        "the ambiguity it removes from the stream reappears as checksum/referee "
        "bits or exponential decode work. A fixed 64-bit checksum only buys a "
        "finite amount of missing delimiter/open-state information."
    )
    print(
        "Therefore non-prefix syntax does not provide arbitrary-pass, roughly-all "
        "content-blind compression unless a separate public invariant bounds the "
        "surviving reading count independently of file size and pass count."
    )


def main() -> None:
    print_language_table()
    print_exact_examples()
    print_open_carry_connection()
    print_reading()


if __name__ == "__main__":
    main()
