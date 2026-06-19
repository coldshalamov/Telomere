#!/usr/bin/env python3
"""H194 - finite-state language transform ledger.

H193 left the next target: force all inputs into a public self-delimiting /
finite-state syntax, pay the reversible transform tax, then ask whether exact
Telomere witnesses over that syntax maintain useful supply.

This kernel enumerates small binary languages exactly.  For an N-bit input, a
public transform maps rank 0..2^N-1 into the first 2^N accepted m-bit syntax
words.  This is reversible and stateless, but it changes the target surface:

* apparent syntax gain compares paid length against m syntax bits;
* real gain compares paid length against the original N input bits.

Two witness-accounting modes are reported:

* all_syntax: every seed record up to Wmax consumes Kraft mass, even if its
  expansion is outside the selected syntax set.
* semantic_reclaim: generous lower bound that reclaims rejected seed holes and
  charges only witness mass landing in the selected syntax set.

If a public transform really breaks the arbitrary-uniform barrier, realGain
must be positive after the transform/rank bill.  The assertions require it not
to cross on these uniform finite rows.
"""

from __future__ import annotations

import argparse
import hashlib
import math
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


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def bits_of(value: int, width: int) -> str:
    return format(value, f"0{width}b")


def max_run(bits: str) -> int:
    if not bits:
        return 0
    best = 1
    run = 1
    for prev, cur in zip(bits, bits[1:]):
        if cur == prev:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def accepts(name: str, value: int, width: int) -> bool:
    bits = bits_of(value, width)
    if name == "all":
        return True
    if name == "suffix0":
        return bits.endswith("0")
    if name == "even_parity":
        return bits.count("1") % 2 == 0
    if name == "no00":
        return "00" not in bits
    if name == "no000":
        return "000" not in bits
    if name == "maxrun2":
        return max_run(bits) <= 2
    if name == "marker4":
        # Public lane: every fourth bit is a marker 1.
        return all(bits[index] == "1" for index in range(3, width, 4))
    if name == "sync11":
        # One terminal synchronizer; no internal 11.
        return bits.endswith("11") and "11" not in bits[:-2]
    if name in {"dyck4", "primdyck4"}:
        height = 0
        returned_early = False
        for index, bit in enumerate(bits):
            height += 1 if bit == "1" else -1
            if height < 0 or height > 4:
                return False
            if height == 0 and index != width - 1:
                returned_early = True
        if height != 0:
            return False
        return not returned_early if name == "primdyck4" else True
    raise ValueError(name)


def accepted_words(name: str, width: int, limit: int | None = None) -> list[int]:
    out: list[int] = []
    for value in range(1 << width):
        if accepts(name, value, width):
            out.append(value)
            if limit is not None and len(out) >= limit:
                break
    return out


def count_language(name: str, width: int) -> int:
    return len(accepted_words(name, width))


def minimal_width(name: str, input_bits: int, max_overhead: int) -> tuple[int, int] | None:
    needed = 1 << input_bits
    for width in range(input_bits, input_bits + max_overhead + 1):
        count = count_language(name, width)
        if count >= needed:
            return width, count
    return None


def hash_to_word(label: bytes, payload_width: int, rank: int, width: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(label)
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(width.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << width) - 1)


@dataclass(frozen=True)
class Row:
    language: str
    input_bits: int
    syntax_bits: int
    lang_count: int
    selected_count: int
    transform_tax: int
    payload_width: int
    mode: str
    selected_support: int
    syntax_hit_mass: float
    charged_mass: float
    mean_paid: float
    real_gain: float
    apparent_syntax_gain: float
    closure_survival: float
    roundtrip_ok: bool
    verdict: str


def price_row(
    *,
    language: str,
    input_bits: int,
    syntax_bits: int,
    lang_count: int,
    selected: list[int],
    payload_width: int,
    mode: str,
) -> Row:
    selected_count = 1 << input_bits
    selected_index = {word: idx for idx, word in enumerate(selected)}
    masses = [0.0] * selected_count
    total_syntax_mass = 0.0
    charged_mass = 0.0
    all_syntax_mass = 0.0
    for width in range(1, payload_width + 1):
        count = costs.payload_width_count_exact(width)
        record_bits = costs.record_cost_for_payload_width(1, width)
        mass = 2.0 ** (-record_bits)
        all_syntax_mass += count * mass
        for rank in range(count):
            word = hash_to_word(b"H194-word\0", width, rank, syntax_bits)
            if word in selected_index:
                masses[selected_index[word]] += mass
                total_syntax_mass += mass
            elif accepts(language, word, syntax_bits):
                total_syntax_mass += mass
    charged_mass = all_syntax_mass if mode == "all_syntax" else sum(masses)
    if charged_mass >= 1.0:
        raw_len = math.inf
    else:
        raw_len = input_bits - math.log2(1.0 - charged_mass)
    lengths = []
    for mass in masses:
        if mode == "all_syntax":
            p = (1.0 - charged_mass) / selected_count + mass
        else:
            p = (1.0 - charged_mass) / selected_count + mass
        lengths.append(-math.log2(p) if p > 0.0 else math.inf)
    mean_paid = sum(lengths) / selected_count
    real_gain = input_bits - mean_paid
    apparent_gain = syntax_bits - mean_paid

    # Closure proxy: selected transformed words whose witness output also lands
    # in the selected syntax set.  This measures whether the language keeps a
    # next-pass selected surface alive.
    support_words = {selected[i] for i, mass in enumerate(masses) if mass > 0.0}
    closure_hits = sum(1 for word in support_words if word in selected_index)
    closure_survival = closure_hits / len(support_words) if support_words else 0.0

    samples = [0, selected_count // 3, selected_count - 1]
    roundtrip_ok = all(selected_index[selected[sample]] == sample for sample in samples)
    verdict = (
        "BUG: transform crosses arbitrary uniform"
        if real_gain > 1e-12
        else "transform/syntax bill nonnegative"
    )
    return Row(
        language=language,
        input_bits=input_bits,
        syntax_bits=syntax_bits,
        lang_count=lang_count,
        selected_count=selected_count,
        transform_tax=syntax_bits - input_bits,
        payload_width=payload_width,
        mode=mode,
        selected_support=sum(1 for mass in masses if mass > 0.0),
        syntax_hit_mass=total_syntax_mass,
        charged_mass=charged_mass,
        mean_paid=mean_paid,
        real_gain=real_gain,
        apparent_syntax_gain=apparent_gain,
        closure_survival=closure_survival,
        roundtrip_ok=roundtrip_ok,
        verdict=verdict,
    )


def print_table(args: argparse.Namespace) -> None:
    input_bits_values = parse_int_list(args.input_bits, [8, 12, 16])
    payload_width_values = parse_int_list(args.max_payload_width, [4, 8, 16])
    languages = args.language or [
        "all",
        "suffix0",
        "even_parity",
        "no000",
        "maxrun2",
        "marker4",
        "sync11",
        "dyck4",
        "primdyck4",
    ]
    print("== H194 finite-state language transform ledger ==")
    print(
        "realGain compares paid length to original N bits; appGain compares to expanded syntax length m."
    )
    print(
        f"{'lang':<11} {'N':>4} {'m':>4} {'|L_m|':>8} {'tax':>4} "
        f"{'W':>4} {'mode':<16} {'sup':>7} {'q_hit':>9} {'q_chg':>9} "
        f"{'mean':>9} {'realG':>9} {'appG':>9} {'rt':>4} {'verdict'}"
    )
    best: Row | None = None
    for language in languages:
        for input_bits in input_bits_values:
            found = minimal_width(language, input_bits, args.max_overhead)
            if found is None:
                continue
            syntax_bits, lang_count = found
            selected = accepted_words(language, syntax_bits, 1 << input_bits)
            if len(selected) < (1 << input_bits):
                raise AssertionError("selected set too small")
            for payload_width in payload_width_values:
                for mode in ("all_syntax", "semantic_reclaim"):
                    row = price_row(
                        language=language,
                        input_bits=input_bits,
                        syntax_bits=syntax_bits,
                        lang_count=lang_count,
                        selected=selected,
                        payload_width=payload_width,
                        mode=mode,
                    )
                    if row.real_gain > 1e-9:
                        raise AssertionError("finite-state transform beat uniform input")
                    if row.selected_support > 0 and (
                        best is None or row.real_gain > best.real_gain
                    ):
                        best = row
                    print(
                        f"{row.language:<11} {row.input_bits:4d} {row.syntax_bits:4d} "
                        f"{row.lang_count:8d} {row.transform_tax:4d} "
                        f"{row.payload_width:4d} {row.mode:<16} "
                        f"{row.selected_support:7d} {fmt(row.syntax_hit_mass):>9} "
                        f"{fmt(row.charged_mass):>9} {fmt(row.mean_paid):>9} "
                        f"{fmt(row.real_gain):>9} {fmt(row.apparent_syntax_gain):>9} "
                        f"{str(row.roundtrip_ok):>4} {row.verdict}"
                    )
    if best is not None:
        print()
        print(
            "nearest nonzero-support real gain: "
            f"{fmt(best.real_gain)} at {best.language},N={best.input_bits},"
            f"m={best.syntax_bits},W={best.payload_width},{best.mode}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A reversible public language transform maps N raw bits into a")
    print("selected set of 2^N syntax words. That may make parse geometry")
    print("clean and can show large apparent gain versus the expanded m-bit")
    print("syntax, but the real source has only N bits. Witness mass landing")
    print("inside the selected language either consumes Kraft globally or is")
    print("a generous semantic-hole lower bound. For arbitrary uniform ranks,")
    print("the paid mean remains N + D(U||Q). Any positive row would require")
    print("overfull syntax, hidden semantic rejection, or a source/reachable")
    print("restriction rather than a free recursive refresh mechanism.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument("--max-overhead", type=int, default=4)
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
