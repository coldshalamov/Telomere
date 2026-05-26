"""
Telomere Parameter Economics Model

This doesn't touch the Rust code. It's pure math.
For each (block_size, depth, arity) triple, it computes:
  - Lotus record size (exact, from the encoding spec)
  - Profit per hit (span - record)
  - Hit probability per block
  - Expected hits for various file sizes
  - Expected savings
  - Break-even file size (where E[savings] > 0 after format overhead)
  - Recursion convergence estimate (passes needed for N% compression)
  - Amortized economics (cost per user for popular content)

This is the model that should have been built before any code.
"""

import math
import json
from dataclasses import dataclass

LOTUS_J_BITS = 3
LOTUS_TIERS = 2


def lotus_width_for_value(value: int) -> int:
    """Find the smallest width w such that 2^w - 2 <= value <= 2^(w+1) - 3.

    Mirrors `lotus_width_for_value` in C:/Users/93rob/Documents/GitHub/lotus/src/lib.rs.
    """
    width = 1
    while True:
        start = (1 << width) - 2
        end = (1 << (width + 1)) - 3
        if start <= value <= end:
            return width
        width += 1


def lotus_j3d2_bits(value: int) -> int:
    """Total bit length of lotus_encode_u64(value, j_bits=3, tiers=2).

    Faithful reproduction of the Lotus tiered encoding for the J3D2 preset
    (j_bits=3, tiers=2) used by Telomere for seed-index encoding. See
    C:/Users/93rob/Documents/GitHub/lotus/src/lib.rs::lotus_encode_u64_framed.
    """
    if value < 0:
        raise ValueError("Lotus only encodes unsigned integers")
    payload_value = value + 1
    payload_width = lotus_width_for_value(payload_value)
    tier1_width = lotus_width_for_value(payload_width)
    tier2_width = lotus_width_for_value(tier1_width)
    # jump_val = tier2_width - 1 must fit in 3 bits, i.e. tier2_width in 1..=8.
    if tier2_width < 1 or tier2_width > 8:
        raise ValueError(f"value {value} exceeds J3D2 range")
    return 3 + tier2_width + tier1_width + payload_width


def arity_bits(arity: int) -> int:
    """Bits for arity encoding: 00=1, 01=2, 100=3, 101=4, 110=5."""
    if arity <= 2:
        return 2  # mode(1) + value(1)
    return 3  # mode(1) + value(2)


def telomere_record_bits(seed_index: int, arity: int) -> int:
    """Total bits for a Telomere record encoding seed_index at given arity.

    Layout: [mode bit (1)] [arity value bits (1 or 2)] [Lotus J3D2 seed_index].
    """
    return arity_bits(arity) + lotus_j3d2_bits(seed_index)


def telomere_record_bytes_average(seed_depth: int, arity: int) -> float:
    """Average Telomere record size in bytes across all seeds at given depth.

    Enumerates all seed indices when the seed space is small enough, otherwise
    samples 100_000 indices uniformly at random.
    """
    total_seeds = seeds_at_depth(seed_depth)
    if total_seeds <= 100_000:
        total_bits = sum(telomere_record_bits(i, arity) for i in range(total_seeds))
        return total_bits / total_seeds / 8.0
    import random
    samples = [
        telomere_record_bits(random.randint(0, total_seeds - 1), arity)
        for _ in range(100_000)
    ]
    return sum(samples) / len(samples) / 8.0


def seeds_at_depth(depth: int) -> int:
    """Total seeds enumerable at max_seed_len = depth."""
    total = 0
    for d in range(1, depth + 1):
        total += 256 ** d
    return total


@dataclass
class ParamResult:
    block_size: int
    depth: int
    arity: int
    span_bytes: int
    record_bytes: float
    profit_per_hit: float
    seeds: int
    p_hit: float
    # For various file sizes
    hits_1mb: float
    hits_1gb: float
    hits_4gb: float
    savings_1mb: float
    savings_1gb: float
    savings_4gb: float
    # Recursion
    passes_for_1pct_4gb: float
    # Economics
    compute_hours_depth: float  # rough estimate
    amortized_cost_10m_users: float


def analyze(block_size: int, depth: int, arity: int) -> ParamResult:
    span_bytes = block_size * arity
    record_bytes = telomere_record_bytes_average(depth, arity)
    profit = span_bytes - record_bytes
    seeds = seeds_at_depth(depth)
    p_hit = seeds / (2 ** (8 * span_bytes))

    blocks_1mb = (1024 * 1024) // span_bytes
    blocks_1gb = (1024 ** 3) // span_bytes
    blocks_4gb = (4 * 1024 ** 3) // span_bytes

    hits_1mb = blocks_1mb * p_hit
    hits_1gb = blocks_1gb * p_hit
    hits_4gb = blocks_4gb * p_hit

    savings_1mb = hits_1mb * profit
    savings_1gb = hits_1gb * profit
    savings_4gb = hits_4gb * profit

    # Recursion estimate: each pass gives ~hits_4gb hits (roughly stable
    # until file shrinks significantly). Passes for 1% compression:
    target_savings = 0.01 * 4 * 1024 ** 3
    if savings_4gb > 0:
        passes_for_1pct = target_savings / savings_4gb
    else:
        passes_for_1pct = float('inf')

    # Compute estimate: seeds * blocks comparisons per pass
    # Assume 1 billion comparisons/sec on modern hardware (conservative for rayon)
    comparisons_per_pass = seeds * blocks_4gb
    seconds_per_pass = comparisons_per_pass / 1e9
    total_seconds = seconds_per_pass * min(passes_for_1pct, 1e9)
    compute_hours = total_seconds / 3600

    # Amortized: if 10M users download, bandwidth savings vs compute cost
    # Assume $0.01/GB bandwidth, $3/GPU-hour
    bandwidth_saved_bytes = savings_4gb * min(passes_for_1pct, 100000)
    bandwidth_saved_gb = bandwidth_saved_bytes / (1024 ** 3)
    bandwidth_cost_saved = bandwidth_saved_gb * 0.01 * 10_000_000
    compute_cost = compute_hours * 3
    if compute_cost > 0:
        amortized = compute_cost / 10_000_000
    else:
        amortized = 0

    return ParamResult(
        block_size=block_size,
        depth=depth,
        arity=arity,
        span_bytes=span_bytes,
        record_bytes=record_bytes,
        profit_per_hit=profit,
        seeds=seeds,
        p_hit=p_hit,
        hits_1mb=hits_1mb,
        hits_1gb=hits_1gb,
        hits_4gb=hits_4gb,
        savings_1mb=savings_1mb,
        savings_1gb=savings_1gb,
        savings_4gb=savings_4gb,
        passes_for_1pct_4gb=passes_for_1pct,
        compute_hours_depth=compute_hours,
        amortized_cost_10m_users=amortized,
    )


def main():
    print("=" * 100)
    print("TELOMERE PARAMETER ECONOMICS")
    print("=" * 100)
    print()
    print(f"{'BS':>3} {'D':>2} {'A':>2} | {'Span':>4} {'Rec':>5} {'Prof':>6} | "
          f"{'Seeds':>12} {'P(hit)':>12} | "
          f"{'Hits/4GB':>12} {'Save/4GB':>12} | "
          f"{'Passes 1%':>10} {'Hours':>10}")
    print("-" * 100)

    results = []
    for block_size in [2, 3, 4, 5, 6, 8]:
        for depth in [1, 2, 3, 4, 5]:
            for arity in [1, 2, 3, 4, 5]:
                r = analyze(block_size, depth, arity)
                results.append(r)

                # Only print interesting ones (positive profit, non-zero hits)
                if r.profit_per_hit > 0 and r.hits_4gb > 0.001:
                    print(f"{r.block_size:>3} {r.depth:>2} {r.arity:>2} | "
                          f"{r.span_bytes:>4} {r.record_bytes:>5.2f} {r.profit_per_hit:>6.2f} | "
                          f"{r.seeds:>12,} {r.p_hit:>12.2e} | "
                          f"{r.hits_4gb:>12,.1f} {r.savings_4gb:>12,.0f} | "
                          f"{r.passes_for_1pct_4gb:>10,.0f} {r.compute_hours_depth:>10,.1f}")

    print()
    print("=" * 100)
    print("TOP 10 BY EXPECTED SAVINGS ON 4GB (single pass)")
    print("=" * 100)
    profitable = [r for r in results if r.profit_per_hit > 0 and r.savings_4gb > 0]
    profitable.sort(key=lambda r: r.savings_4gb, reverse=True)
    for r in profitable[:10]:
        print(f"  BS={r.block_size} D={r.depth} A={r.arity}: "
              f"span={r.span_bytes}B, record={r.record_bytes:.2f}B, "
              f"profit={r.profit_per_hit:.2f}B/hit, "
              f"E[hits]={r.hits_4gb:,.0f}, E[savings]={r.savings_4gb:,.0f} bytes, "
              f"passes_for_1%={r.passes_for_1pct_4gb:,.0f}")

    print()
    print("=" * 100)
    print("TOP 10 BY AMORTIZED ECONOMICS (compute cost / 10M users)")
    print("=" * 100)
    economical = [r for r in results if r.profit_per_hit > 0 and r.savings_4gb > 0
                  and r.passes_for_1pct_4gb < 1e8]
    economical.sort(key=lambda r: r.savings_4gb / max(r.compute_hours_depth, 0.001), reverse=True)
    for r in economical[:10]:
        savings_per_hour = r.savings_4gb / max(r.compute_hours_depth / r.passes_for_1pct_4gb, 0.001)
        print(f"  BS={r.block_size} D={r.depth} A={r.arity}: "
              f"{r.savings_4gb:,.0f} bytes/pass, "
              f"savings_rate={savings_per_hour:,.0f} bytes/compute-hour, "
              f"amortized=${r.amortized_cost_10m_users:.6f}/user")

    print()
    print("=" * 100)
    print("RECURSION CONVERGENCE MODEL")
    print("=" * 100)
    print()
    # Take the best single-pass config and model recursion
    if profitable:
        best = profitable[0]
        print(f"Best config: BS={best.block_size} D={best.depth} A={best.arity}")
        print(f"Single-pass: {best.hits_4gb:,.0f} hits, {best.savings_4gb:,.0f} bytes saved")
        print()
        file_size = 4 * 1024 ** 3
        cumulative = 0
        for pass_n in range(1, 51):
            current_blocks = file_size // best.span_bytes
            hits = current_blocks * best.p_hit
            saved = hits * best.profit_per_hit
            cumulative += saved
            file_size -= saved
            pct = cumulative / (4 * 1024**3) * 100
            if pass_n <= 10 or pass_n % 10 == 0:
                print(f"  Pass {pass_n:>3}: {hits:>12,.0f} hits, "
                      f"{saved:>10,.0f} bytes this pass, "
                      f"{cumulative:>12,.0f} total ({pct:.4f}%)")

    # Output as JSON for further analysis
    output = []
    for r in profitable[:20]:
        output.append({
            'block_size': r.block_size,
            'depth': r.depth,
            'arity': r.arity,
            'span_bytes': r.span_bytes,
            'record_bytes': r.record_bytes,
            'profit_per_hit': r.profit_per_hit,
            'seeds': r.seeds,
            'p_hit': r.p_hit,
            'hits_4gb': r.hits_4gb,
            'savings_4gb': r.savings_4gb,
            'passes_for_1pct': r.passes_for_1pct_4gb,
        })
    with open('scripts/parameter_economics.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote top-20 results to scripts/parameter_economics.json")


if __name__ == '__main__':
    main()
