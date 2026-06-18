#!/usr/bin/env python3
"""H55 - exact unique-survivor audit for headerless slack profiles.

H53 priced a global slack/profile selector. The tempting escape is:

    do not store the selector;
    let the decoder try every slack/profile;
    keep the one that parses / covers / checks out.

This is free only if the emitted stream language is disjoint across slacks, or
if all surviving parses reconstruct the same previous layer. H55 builds tiny
exact prefix languages and counts the overlap. It does not model natural data
or run Telomere searches; it audits the parsing/referee channel.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Codeword:
    value: int
    bits: int
    width: int


@dataclass(frozen=True)
class Config:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int
    slacks: tuple[int, ...]


@dataclass(frozen=True)
class AuditRow:
    config: Config
    arity_code: str
    total_descriptions: int
    union_streams: int
    ambiguous_streams: int
    max_survivors: int
    expected_missing_bits_per_description: float
    overlap_dividend_bits: float
    unique_description_fraction: float
    canonical_first_loss_bits: float


def prefix_arity_codes(max_arity: int) -> dict[int, Codeword]:
    """Small canonical prefix code for exact toy audits.

    Arity 1 is cheap (`0`). Larger arities are unary-ish (`10`, `110`, ...,
    final all-ones word). This is not the production Lotus alphabet; it is a
    prefix grammar whose only job is to test whether slack-dependent payload
    lengths create disjoint languages.
    """

    if max_arity < 1:
        raise ValueError("max_arity must be positive")
    codes: dict[int, Codeword] = {}
    for arity in range(1, max_arity + 1):
        if arity == 1:
            bits = 0b0
            width = 1
        elif arity == max_arity:
            bits = (1 << arity) - 1
            width = arity
        else:
            width = arity
            bits = ((1 << (arity - 1)) - 1) << 1
        codes[arity] = Codeword(bits=bits, width=width, value=arity)
    return codes


def fixed_arity_codes(max_arity: int) -> dict[int, Codeword]:
    width = max(1, math.ceil(math.log2(max_arity + 1)))
    return {
        arity: Codeword(value=arity, bits=arity, width=width)
        for arity in range(1, max_arity + 1)
    }


def gamma_arity_codes(max_arity: int) -> dict[int, Codeword]:
    codes: dict[int, Codeword] = {}
    for arity in range(1, max_arity + 1):
        payload_width = arity.bit_length()
        zeros = payload_width - 1
        width = zeros + payload_width
        bits = arity
        codes[arity] = Codeword(value=arity, bits=bits, width=width)
    return codes


def fibonacci_arity_codes(max_arity: int) -> dict[int, Codeword]:
    fibs = [1, 2]
    while fibs[-1] < max_arity:
        fibs.append(fibs[-1] + fibs[-2])

    codes: dict[int, Codeword] = {}
    for arity in range(1, max_arity + 1):
        remaining = arity
        used = [0] * len(fibs)
        for index in range(len(fibs) - 1, -1, -1):
            if fibs[index] <= remaining:
                used[index] = 1
                remaining -= fibs[index]
        while used and used[-1] == 0:
            used.pop()
        # Standard Fibonacci coding appends a terminal 1. The representation
        # itself has no adjacent ones; the terminator creates the only `11`.
        bits_list = used + [1]
        bits = 0
        for bit in bits_list:
            bits = (bits << 1) | bit
        codes[arity] = Codeword(value=arity, bits=bits, width=len(bits_list))
    return codes


def arity_codes(max_arity: int, mode: str) -> dict[int, Codeword]:
    if mode == "prefix":
        return prefix_arity_codes(max_arity)
    if mode == "fixed":
        return fixed_arity_codes(max_arity)
    if mode == "gamma":
        return gamma_arity_codes(max_arity)
    if mode == "fibonacci":
        return fibonacci_arity_codes(max_arity)
    raise ValueError(mode)


def width_bits_for(block_bits: int, frontier: int, arity: int, slack: int) -> int | None:
    width = min(frontier, arity * block_bits - slack)
    if width < 1:
        return None
    return width


def append_bits(prefix: tuple[int, int], bits: int, width: int) -> tuple[int, int]:
    value, length = prefix
    return (value << width) | bits, length + width


def generate_streams(
    config: Config,
    slack: int,
    codes: dict[int, Codeword],
    max_streams: int,
) -> set[tuple[int, int]]:
    streams: set[tuple[int, int]] = set()

    def rec(remaining: int, prefix: tuple[int, int]) -> None:
        if len(streams) > max_streams:
            raise RuntimeError(f"stream cap exceeded ({max_streams})")
        if remaining == 0:
            streams.add(prefix)
            return
        legal_max = min(config.max_arity, remaining)
        for arity in range(1, legal_max + 1):
            width = width_bits_for(config.block_bits, config.frontier, arity, slack)
            if width is None:
                continue
            code = codes[arity]
            with_arity = append_bits(prefix, code.bits, code.width)
            for payload in range(1 << width):
                rec(remaining - arity, append_bits(with_arity, payload, width))

    rec(config.atoms, (0, 0))
    return streams


def audit_config(config: Config, code_mode: str, max_streams: int) -> AuditRow:
    codes = arity_codes(config.max_arity, code_mode)
    membership: dict[tuple[int, int], set[int]] = defaultdict(set)
    per_slack_sizes: dict[int, int] = {}
    for slack in config.slacks:
        streams = generate_streams(config, slack, codes, max_streams)
        per_slack_sizes[slack] = len(streams)
        for stream in streams:
            membership[stream].add(slack)

    total_descriptions = sum(per_slack_sizes.values())
    union_streams = len(membership)
    ambiguous_streams = sum(1 for slacks in membership.values() if len(slacks) > 1)
    max_survivors = max((len(slacks) for slacks in membership.values()), default=0)

    missing_weight = 0.0
    unique_descriptions = 0
    canonical_counts: Counter[int] = Counter()
    for stream, slacks in membership.items():
        survivors = len(slacks)
        missing_weight += survivors * math.log2(survivors)
        if survivors == 1:
            unique_descriptions += 1
        canonical_counts[min(slacks)] += 1

    expected_missing = missing_weight / total_descriptions if total_descriptions else 0.0
    overlap_dividend = (
        math.log2(total_descriptions / union_streams)
        if total_descriptions and union_streams
        else 0.0
    )

    # If a public canonical rule assigns every overlapping stream to the first
    # valid slack, later slacks lose their overlapping options. This is a supply
    # loss, not a free adaptive choice.
    best_canonical = max(canonical_counts.values(), default=0)
    canonical_loss = (
        math.log2(total_descriptions / best_canonical)
        if total_descriptions and best_canonical
        else 0.0
    )

    return AuditRow(
        config=config,
        arity_code=code_mode,
        total_descriptions=total_descriptions,
        union_streams=union_streams,
        ambiguous_streams=ambiguous_streams,
        max_survivors=max_survivors,
        expected_missing_bits_per_description=expected_missing,
        overlap_dividend_bits=overlap_dividend,
        unique_description_fraction=unique_descriptions / total_descriptions
        if total_descriptions
        else 0.0,
        canonical_first_loss_bits=canonical_loss,
    )


def parse_config(text: str) -> Config:
    parts = text.split(",")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError("config must be B,K,D,N,slacks")
    block_bits = int(parts[0])
    max_arity = int(parts[1])
    frontier = int(parts[2])
    atoms = int(parts[3])
    slacks = tuple(int(item) for item in parts[4].split(":"))
    return Config(block_bits, max_arity, frontier, atoms, slacks)


def render(rows: list[AuditRow]) -> str:
    lines = [
        "# H55 - Unique Slack Survivor Audit",
        "",
        "Exact tiny languages for headerless slack/profile decoding. A stream is",
        "ambiguous when it is a valid full-cover parse under more than one slack.",
        "",
        "| B | K | D | atoms | slacks | arity code | descriptions | union streams | ambiguous streams | max survivors | missing bits/description | overlap dividend | unique description fraction | canonical-first loss |",
        "| ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        cfg = row.config
        lines.append(
            f"| {cfg.block_bits} | {cfg.max_arity} | {cfg.frontier} | "
            f"{cfg.atoms} | {':'.join(str(s) for s in cfg.slacks)} | "
            f"{row.arity_code} | {row.total_descriptions} | "
            f"{row.union_streams} | {row.ambiguous_streams} | "
            f"{row.max_survivors} | "
            f"{row.expected_missing_bits_per_description:.6f} | "
            f"{row.overlap_dividend_bits:.6f} | "
            f"{row.unique_description_fraction:.6f} | "
            f"{row.canonical_first_loss_bits:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "`missing bits/description` is the expected `log2(|valid slacks|)` bill",
            "when descriptions are selected uniformly from the slack-tagged",
            "languages. `overlap dividend` is the apparent saving from merging",
            "tagged languages into one headerless union. Those are the same hidden",
            "channel seen from opposite sides.",
            "",
            "If `ambiguous streams > 0`, trial parsing alone has not derived a unique",
            "profile. A checksum can referee the ambiguity only up to the finite H54",
            "budget. A canonical-first rule is public and stateless, but it gives up",
            "the adaptive choices counted in the later slack languages.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        dest="configs",
        type=parse_config,
        action="append",
        default=None,
        help="B,K,D,N,slacks where slacks use ':' separators, e.g. 2,3,6,4,0:1:2",
    )
    parser.add_argument(
        "--arity-code",
        choices=["prefix", "fixed", "gamma", "fibonacci"],
        nargs="+",
        default=["prefix", "fixed", "gamma", "fibonacci"],
    )
    parser.add_argument("--max-streams", type=int, default=2_000_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs or [
        Config(2, 3, 6, 4, (0, 1, 2)),
        Config(2, 3, 6, 5, (0, 1, 2)),
        Config(3, 3, 9, 4, (0, 1, 2)),
    ]
    rows = [
        audit_config(config, code_mode, args.max_streams)
        for config in configs
        for code_mode in args.arity_code
    ]
    print(render(rows))


if __name__ == "__main__":
    main()
