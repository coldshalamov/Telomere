#!/usr/bin/env python3
"""H189 - non-prefix uniquely-decodable grammar Kraft check.

This kernel tests whether abandoning prefix decoding can increase the available
record/witness row mass while remaining stateless and uniquely decodable.

Kraft-McMillan says every binary uniquely-decodable code has Kraft sum <= 1,
even if it is not prefix-free.  Prefix-free is sufficient, not necessary.  The
tempting escape is that a self-synchronizing or delayed-decode grammar might
use non-prefix words with total mass > 1.  Sardinas-Patterson catches that.
"""

from __future__ import annotations

import argparse
import itertools
import math
from dataclasses import dataclass


def binary_words(max_len: int) -> list[str]:
    return [
        "".join(bits)
        for length in range(1, max_len + 1)
        for bits in itertools.product("01", repeat=length)
    ]


def kraft(code: tuple[str, ...]) -> float:
    return sum(2.0 ** (-len(word)) for word in code)


def is_prefix_free(code: tuple[str, ...]) -> bool:
    for a, b in itertools.permutations(code, 2):
        if b.startswith(a):
            return False
    return True


def suffix_if_prefix(prefix: str, word: str) -> str | None:
    if word.startswith(prefix):
        return word[len(prefix) :]
    return None


def sardinas_patterson_ud(code: tuple[str, ...]) -> bool:
    cset = set(code)
    current: set[str] = set()
    for x, y in itertools.permutations(code, 2):
        suffix = suffix_if_prefix(x, y)
        if suffix is not None:
            if suffix == "":
                return False
            current.add(suffix)

    seen: set[frozenset[str]] = set()
    while current:
        frozen = frozenset(current)
        if frozen in seen:
            return True
        seen.add(frozen)
        nxt: set[str] = set()

        # C^-1 S_n
        for c in cset:
            for s in current:
                suffix = suffix_if_prefix(c, s)
                if suffix is not None:
                    if suffix == "":
                        return False
                    nxt.add(suffix)

        # S_n^-1 C
        for s in current:
            for c in cset:
                suffix = suffix_if_prefix(s, c)
                if suffix is not None:
                    if suffix == "":
                        return False
                    nxt.add(suffix)
        current = nxt
    return True


@dataclass(frozen=True)
class ScanRow:
    max_len: int
    code_size: int
    scanned: int
    ud_count: int
    nonprefix_ud_count: int
    max_ud_kraft: float
    max_nonprefix_ud_kraft: float
    max_nonud_kraft: float
    best_ud: tuple[str, ...]
    best_nonprefix_ud: tuple[str, ...]
    best_nonud: tuple[str, ...]


def fmt(value: float) -> str:
    if value == 0.0:
        return "0"
    return f"{value:.6f}"


def scan(max_len: int, code_size: int, cap: int | None) -> ScanRow:
    words = binary_words(max_len)
    scanned = 0
    ud_count = 0
    nonprefix_ud_count = 0
    max_ud = -1.0
    max_nonprefix_ud = -1.0
    max_nonud = -1.0
    best_ud: tuple[str, ...] = ()
    best_nonprefix_ud: tuple[str, ...] = ()
    best_nonud: tuple[str, ...] = ()
    for code in itertools.combinations(words, code_size):
        scanned += 1
        if cap is not None and scanned > cap:
            break
        k = kraft(code)
        ud = sardinas_patterson_ud(code)
        prefix = is_prefix_free(code)
        if ud:
            ud_count += 1
            if k > max_ud:
                max_ud = k
                best_ud = code
            if not prefix:
                nonprefix_ud_count += 1
                if k > max_nonprefix_ud:
                    max_nonprefix_ud = k
                    best_nonprefix_ud = code
        else:
            if k > max_nonud:
                max_nonud = k
                best_nonud = code
    return ScanRow(
        max_len=max_len,
        code_size=code_size,
        scanned=scanned if cap is None else min(scanned, cap),
        ud_count=ud_count,
        nonprefix_ud_count=nonprefix_ud_count,
        max_ud_kraft=max_ud if max_ud >= 0 else 0.0,
        max_nonprefix_ud_kraft=max_nonprefix_ud if max_nonprefix_ud >= 0 else 0.0,
        max_nonud_kraft=max_nonud if max_nonud >= 0 else 0.0,
        best_ud=best_ud,
        best_nonprefix_ud=best_nonprefix_ud,
        best_nonud=best_nonud,
    )


def print_table(args: argparse.Namespace) -> None:
    print("== H189 non-prefix uniquely-decodable Kraft check ==")
    print(
        "UD is checked with Sardinas-Patterson. Non-UD rows can exceed Kraft 1; UD rows cannot."
    )
    print(
        f"{'L':>3} {'size':>4} {'scanned':>8} {'UD':>7} {'nonpreUD':>8} "
        f"{'maxUD':>8} {'maxNonpre':>10} {'maxNonUD':>9} {'best nonprefix UD'}"
    )
    for size in args.code_size:
        row = scan(args.max_len, size, args.cap)
        print(
            f"{row.max_len:3d} {row.code_size:4d} {row.scanned:8d} "
            f"{row.ud_count:7d} {row.nonprefix_ud_count:8d} "
            f"{fmt(row.max_ud_kraft):>8} {fmt(row.max_nonprefix_ud_kraft):>10} "
            f"{fmt(row.max_nonud_kraft):>9} {','.join(row.best_nonprefix_ud)}"
        )
        if row.max_nonprefix_ud_kraft > 1.0 + 1e-12:
            raise AssertionError("found impossible UD Kraft > 1")


def print_examples() -> None:
    examples = [
        ("prefix critical", ("0", "10", "110", "111")),
        ("nonprefix UD", ("01", "10", "011")),
        ("non-UD overfull", ("0", "1", "00")),
    ]
    print()
    print("== examples ==")
    print(f"{'name':<18} {'code':<24} {'kraft':>8} {'prefix':>7} {'UD':>5}")
    for name, code in examples:
        print(
            f"{name:<18} {','.join(code):<24} {fmt(kraft(code)):>8} "
            f"{str(is_prefix_free(code)):>7} {str(sardinas_patterson_ud(code)):>5}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Non-prefix is not overfull capacity. Any stateless uniquely-decodable")
    print("binary record grammar still obeys Kraft sum <= 1. Codebooks with")
    print("Kraft > 1 are either non-UD, need a referee/length side channel,")
    print("or are generated/source-shaped restrictions.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-len", type=int, default=4)
    parser.add_argument("--code-size", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--cap", type=int, default=None)
    args = parser.parse_args()

    print_table(args)
    print_examples()
    print_theorem()


if __name__ == "__main__":
    main()
