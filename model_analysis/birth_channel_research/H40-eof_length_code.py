#!/usr/bin/env python3
"""
H40 - EOF / whole-file length-code ledger.

Idea:

    A whole-file decoder sees EOF/file length. For a fixed n-bit virtual board,
    we can use non-prefix one-to-one codes: public permutation, then trim leading
    zeros; or map ranks to the first 2^n binary strings ordered by length.

This is a real distinction from record-prefix Telomere streams. The question is
whether EOF length can refresh/compound recursive compression without a hidden
length ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, log2


def expected_lz_trim_savings(n_bits: int) -> float:
    """E[leading zeros] for a uniform n-bit string."""

    # P(Z >= k) = 2^-k for 1 <= k <= n.
    return sum(2.0 ** (-k) for k in range(1, n_bits + 1))


def expected_optimal_one_to_one_savings(n_bits: int) -> float:
    """Expected saving for the shortest 2^n non-prefix codewords.

    The codebook uses every string of length 0..n-1 plus one n-bit string.
    Sum_{l=0}^{n-1} l 2^l = (n-2)2^n + 2 for n>=1.
    """

    total_length = ((n_bits - 2) * (1 << n_bits)) + 2 + n_bits
    average_length = total_length / (1 << n_bits)
    return n_bits - average_length


def lz_distribution(n_bits: int) -> list[float]:
    probs = [0.0] * (n_bits + 1)
    for z in range(n_bits):
        probs[z] = 2.0 ** (-(z + 1))
    probs[n_bits] = 2.0 ** (-n_bits)
    return probs


def entropy(probs: list[float]) -> float:
    return -sum(p * log2(p) for p in probs if p > 0.0)


@dataclass(frozen=True)
class FixedBoardRow:
    n_bits: int
    trim_expected_savings: float
    optimal_expected_savings: float
    length_entropy_bits: float
    final_only_comment: str


def fixed_board_rows() -> list[FixedBoardRow]:
    return [
        FixedBoardRow(
            n_bits=n,
            trim_expected_savings=expected_lz_trim_savings(n),
            optimal_expected_savings=expected_optimal_one_to_one_savings(n),
            length_entropy_bits=entropy(lz_distribution(n)),
            final_only_comment="does not accumulate; each pass reuses the same n-bit board",
        )
        for n in (8, 16, 32, 64, 128)
    ]


@dataclass(frozen=True)
class BestOfPRow:
    n_bits: int
    phases: int
    expected_best_lz: float
    selector_bits: float
    net_after_selector: float


def expected_best_lz(n_bits: int, phases: int) -> float:
    # E[max Z] = sum_{k>=1} P(max Z >= k).
    total = 0.0
    for k in range(1, n_bits + 1):
        p_single_lt_k = 1.0 - (2.0 ** (-k))
        total += 1.0 - (p_single_lt_k**phases)
    return total


def best_of_p_rows() -> list[BestOfPRow]:
    rows: list[BestOfPRow] = []
    for n_bits in (64, 128):
        for phases in (1, 2, 4, 16, 256, 65536):
            best = expected_best_lz(n_bits, phases)
            selector = log2(phases)
            rows.append(
                BestOfPRow(
                    n_bits=n_bits,
                    phases=phases,
                    expected_best_lz=best,
                    selector_bits=selector,
                    net_after_selector=best - selector,
                )
            )
    return rows


@dataclass(frozen=True)
class ShrinkingBoardRow:
    passes: int
    expected_saved_bits: float
    entropy_ledger_bits: float
    final_sum_only_bits: float
    net_with_entropy_ledger: float
    ambiguity_if_only_sum_bits: float


def shrinking_board_rows() -> list[ShrinkingBoardRow]:
    rows: list[ShrinkingBoardRow] = []
    h_lz = entropy(lz_distribution(128))
    mean_lz = expected_lz_trim_savings(128)
    for passes in (1, 2, 4, 16, 64, 256):
        expected_saved = passes * mean_lz
        entropy_ledger = passes * h_lz
        # If only original and final lengths are stored, only S=sum z_i is known.
        # The reverse decoder still needs the ordered reductions. Typical
        # ambiguity for sum S over P passes is C(S+P-1, P-1). Use rounded mean.
        s = round(expected_saved)
        ambiguity = log2(comb(s + passes - 1, passes - 1)) if passes > 1 else 0.0
        rows.append(
            ShrinkingBoardRow(
                passes=passes,
                expected_saved_bits=expected_saved,
                entropy_ledger_bits=entropy_ledger,
                final_sum_only_bits=log2(passes * 128 + 1),
                net_with_entropy_ledger=expected_saved - entropy_ledger,
                ambiguity_if_only_sum_bits=ambiguity,
            )
        )
    return rows


@dataclass(frozen=True)
class BytePaddingRow:
    n_bits: int
    bit_expected_savings: float
    expected_byte_savings: float
    byte_padding_loss: float


def byte_padding_rows() -> list[BytePaddingRow]:
    rows: list[BytePaddingRow] = []
    for n_bits in (64, 128, 1024):
        probs = lz_distribution(n_bits)
        expected_bits = expected_lz_trim_savings(n_bits)
        expected_bytes_saved = 0.0
        for z, p in enumerate(probs):
            expected_bytes_saved += p * (z // 8)
        rows.append(
            BytePaddingRow(
                n_bits=n_bits,
                bit_expected_savings=expected_bits,
                expected_byte_savings=8.0 * expected_bytes_saved,
                byte_padding_loss=expected_bits - (8.0 * expected_bytes_saved),
            )
        )
    return rows


@dataclass(frozen=True)
class PaidFormatRow:
    n_bits: int
    ideal_bit_exact_gain: float
    original_length_cost_bits: float
    pad_count_cost_bits: float
    byte_surface_gain_bits: float
    net_with_length_and_pad: float


def paid_format_rows() -> list[PaidFormatRow]:
    rows: list[PaidFormatRow] = []
    for n_bits in (64, 128, 1024, 1_000_000):
        ideal = expected_optimal_one_to_one_savings(n_bits)
        original_length_cost = log2(n_bits + 1)
        # If a byte container needs the final valid bit count modulo 8, this is
        # the minimal fixed-width pad-count field. Real Lotus/self-delimiting
        # integers are not cheaper for small constants.
        pad_count_cost = 3.0
        # Byte-string shortlex is the byte-surface analog: expected byte saving
        # tends to about 2 bytes for fixed byte length, but original byte length
        # still has to be known. Include the simple trim byte-row separately.
        byte_surface_gain = next(
            row.expected_byte_savings
            for row in byte_padding_rows()
            if row.n_bits == n_bits or (n_bits == 1_000_000 and row.n_bits == 1024)
        )
        rows.append(
            PaidFormatRow(
                n_bits=n_bits,
                ideal_bit_exact_gain=ideal,
                original_length_cost_bits=original_length_cost,
                pad_count_cost_bits=pad_count_cost,
                byte_surface_gain_bits=byte_surface_gain,
                net_with_length_and_pad=ideal
                - original_length_cost
                - pad_count_cost,
            )
        )
    return rows


def print_fixed_board_table() -> None:
    print("== fixed virtual board whole-file code ==")
    print(
        "EOF length makes non-prefix one-to-one whole-file codes possible, but "
        "with a fixed n-bit virtual board the saving is final-only, not recursive."
    )
    print(
        f"{'n':>6} {'trim E save':>12} {'optimal 1-1 save':>16} "
        f"{'H(length)':>10} {'comment':>28}"
    )
    for row in fixed_board_rows():
        print(
            f"{row.n_bits:6d} {row.trim_expected_savings:12.6f} "
            f"{row.optimal_expected_savings:16.6f} "
            f"{row.length_entropy_bits:10.6f} {row.final_only_comment:>28}"
        )
    print()


def print_best_of_p_table() -> None:
    print("== best of P public phases ==")
    print(
        "Trying many public permutations gives a larger leading-zero run, but "
        "the chosen phase is a selector unless it is fixed publicly."
    )
    print(
        f"{'n':>6} {'P':>8} {'E best LZ':>11} {'selector':>10} {'net':>9}"
    )
    for row in best_of_p_rows():
        print(
            f"{row.n_bits:6d} {row.phases:8d} {row.expected_best_lz:11.6f} "
            f"{row.selector_bits:10.3f} {row.net_after_selector:9.3f}"
        )
    print()


def print_shrinking_board_table() -> None:
    print("== shrinking board / compounding requires length ledger ==")
    print(
        "If the semantic board shrinks each pass, reverse decode needs the "
        "ordered length reductions. Their entropy exceeds the expected trim save."
    )
    print(
        f"{'passes':>8} {'E saved':>10} {'ledger H':>10} "
        f"{'net ledger':>11} {'sum bits':>9} {'seq ambiguity':>13}"
    )
    for row in shrinking_board_rows():
        print(
            f"{row.passes:8d} {row.expected_saved_bits:10.3f} "
            f"{row.entropy_ledger_bits:10.3f} {row.net_with_entropy_ledger:11.3f} "
            f"{row.final_sum_only_bits:9.3f} {row.ambiguity_if_only_sum_bits:13.3f}"
        )
    print()


def print_byte_padding_table() -> None:
    print("== byte padding reality check ==")
    print(
        "If the outer file stores whole bytes, leading-zero bit savings usually "
        "do not reach the byte surface without additional bitstream packing."
    )
    print(f"{'n':>6} {'bit save':>10} {'byte-surface save':>17} {'padding loss':>13}")
    for row in byte_padding_rows():
        print(
            f"{row.n_bits:6d} {row.bit_expected_savings:10.6f} "
            f"{row.expected_byte_savings:17.6f} {row.byte_padding_loss:13.6f}"
        )
    print()


def print_paid_format_table() -> None:
    print("== paid outer-format sanity check ==")
    print(
        "The ~2 bit EOF code assumes fixed n and exact bit EOF. If n or valid "
        "pad bits must be in the file, that constant is immediately spent."
    )
    print(
        f"{'n':>9} {'ideal gain':>11} {'len cost':>10} {'pad cost':>9} "
        f"{'net':>9}"
    )
    for row in paid_format_rows():
        print(
            f"{row.n_bits:9d} {row.ideal_bit_exact_gain:11.6f} "
            f"{row.original_length_cost_bits:10.3f} "
            f"{row.pad_count_cost_bits:9.3f} "
            f"{row.net_with_length_and_pad:9.3f}"
        )
    print()


def main() -> None:
    print_fixed_board_table()
    print_best_of_p_table()
    print_shrinking_board_table()
    print_byte_padding_table()
    print_paid_format_table()
    print("CONCLUSION:")
    print(
        "EOF/non-prefix whole-file coding is real, and it can save O(1) bits on "
        "a fixed virtual board. It does not solve recursive maintained "
        "compression: fixed boards do not compound; best-of-P needs a phase "
        "selector; shrinking boards need an ordered length ledger whose entropy "
        "is larger than the trim savings. This is useful as a side-channel "
        "sanity check, not a Telomere breakthrough."
    )


if __name__ == "__main__":
    main()
