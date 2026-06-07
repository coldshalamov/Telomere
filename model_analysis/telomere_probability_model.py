#!/usr/bin/env python3
"""
Telomere — Comprehensive First-Principles Probability Model

This script builds an exact probability model for generative seed-search
compression, properly accounting for:
  1. Exact Lotus J3D2/J1D1 bit costs (not approximations)
  2. Aggregate probability across all arity levels (independent trials)
  3. Per-seed-index compressive match probability
  4. Expected savings vs literal overhead (net compression accounting)
  5. Extended arity analysis (beyond the current cap of 5)
  6. The "gap" structure and whether any parameter regime closes it

No corpus search is performed. This is pure math.
"""

import math
import json
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Lotus Encoding (exact port from telomere_power_model.py) ───

LOTUS_J_BITS = 3
LOTUS_TIERS = 2
LOTUS_ARITY_J_BITS = 1
LOTUS_ARITY_TIERS = 1

def lotus_width_for_value(value: int) -> int:
    """Width of the Lotus payload for a given integer value."""
    if value < 0:
        raise ValueError("Lotus value must be non-negative")
    width = 1
    while True:
        start = (1 << width) - 2
        end = (1 << (width + 1)) - 3
        if start <= value <= end:
            return width
        width += 1

def lotus_encoded_bit_len(value: int, j_bits: int = LOTUS_J_BITS, tiers: int = LOTUS_TIERS) -> int:
    """Exact bit length of a Lotus-encoded integer."""
    if not 1 <= j_bits <= 8 or tiers <= 0:
        raise ValueError("invalid Lotus config")
    if value < 0:
        raise ValueError("Lotus value must be non-negative")
    payload_value = value + 1
    payload_width = lotus_width_for_value(payload_value)
    total_tier_width = 0
    current_width = payload_width
    for _ in range(tiers):
        tier_width = lotus_width_for_value(current_width)
        total_tier_width += tier_width
        current_width = tier_width
    return j_bits + total_tier_width + payload_width

def j1d1_bits(value: int) -> int:
    """Bit cost of a J1D1-encoded value (arity encoding)."""
    return lotus_encoded_bit_len(value, j_bits=1, tiers=1)

def j3d2_bits(value: int) -> int:
    """Bit cost of a J3D2-encoded value (seed index encoding)."""
    return lotus_encoded_bit_len(value, j_bits=3, tiers=2)

# ─── Arity mapping ───

def arity_to_lotus_value(arity: int) -> int:
    """Map arity (1-based) to Lotus J1D1 value. Literal is value 5."""
    if arity < 1:
        raise ValueError("arity must be >= 1")
    return arity - 1  # arity 1 -> value 0, arity 2 -> value 1, etc.

def arity_header_bits(arity: int) -> int:
    """Total header bits for a given arity in V1 format."""
    return j1d1_bits(arity_to_lotus_value(arity))

LITERAL_HEADER_BITS = j1d1_bits(5)  # literal marker = value 5 = 6 bits

# ─── Seed counting ───

def seed_count(max_seed_len: int) -> int:
    """Total seeds up to max_seed_len bytes."""
    return sum(256**k for k in range(1, max_seed_len + 1))

def max_compressive_seed_index(arity: int, block_size: int) -> int:
    """Largest seed index whose V1 record is strictly shorter than the span.
    
    Returns -1 if no seed index produces a compressive record.
    """
    span_bits = 8 * arity * block_size
    h = arity_header_bits(arity)
    budget = span_bits - h  # max bits available for J3D2(seed_index)
    if budget <= 0:
        return -1
    if j3d2_bits(0) >= budget:
        return -1
    # Analytical: find max payload_width where 3 + tw(pw) + pw < budget
    best_pw = 0
    for pw in range(1, 500):
        tw = 0
        cw = pw
        for _ in range(LOTUS_TIERS):
            tier_w = lotus_width_for_value(cw)
            tw += tier_w
            cw = tier_w
        if LOTUS_J_BITS + tw + pw < budget:
            best_pw = pw
        else:
            break
    if best_pw == 0:
        return 0  # only value 0 fits
    # Max value: top of payload_width range, then subtract 1 for value = payload_value - 1
    max_payload_value = (1 << (best_pw + 1)) - 3
    return max_payload_value - 1  # value = payload_value - 1

def count_compressive_seeds(arity: int, block_size: int) -> int:
    """Number of seeds whose record is compressive for given arity/block_size."""
    idx = max_compressive_seed_index(arity, block_size)
    return idx + 1 if idx >= 0 else 0

# ─── Core probability model ───

@dataclass
class ArityAnalysis:
    arity: int
    block_size: int
    span_bytes: int
    span_bits: int
    header_bits: int
    j3d2_budget: int
    max_comp_seed_index: int
    n_compressive_seeds: int
    log2_n_comp: float
    log2_universe: float  # 2^span_bits
    gap_bits: float  # log2_universe - log2_n_comp
    p_comp_per_span: float  # probability of compressive match for one random span
    # Expected savings analysis
    avg_savings_bits: float  # average bits saved per compressive match
    expected_savings_per_span_bits: float  # p_comp * avg_savings

def analyze_arity(arity: int, block_size: int, max_seed_len: Optional[int] = None) -> ArityAnalysis:
    """Full analysis for a single arity level."""
    span_bytes = arity * block_size
    span_bits = 8 * span_bytes
    h = arity_header_bits(arity)
    budget = span_bits - h
    
    max_idx = max_compressive_seed_index(arity, block_size)
    n_comp = max_idx + 1 if max_idx >= 0 else 0
    
    log2_n_comp = math.log2(n_comp) if n_comp > 0 else float('-inf')
    log2_universe = span_bits
    gap = log2_universe - log2_n_comp if n_comp > 0 else float('inf')
    
    # If max_seed_len is specified, cap the compressive seeds to what's searchable
    if max_seed_len is not None:
        searchable = seed_count(max_seed_len)
        effective_n_comp = min(n_comp, searchable)
    else:
        effective_n_comp = n_comp
    
    # P(compressive match for one random span) = 1 - (1 - 2^-S)^N_comp
    # For small probabilities: ≈ N_comp * 2^-S
    if effective_n_comp > 0 and span_bits < 1024:
        log2_p = math.log2(effective_n_comp) - span_bits
        p_comp = 2**log2_p if log2_p > -1074 else 0.0
    else:
        p_comp = 0.0
    
    # Average savings per compressive match (analytical, by payload width)
    if n_comp > 0:
        total_savings = 0
        total_count = 0
        for pw in range(1, 500):
            tw = 0
            cw = pw
            for _ in range(LOTUS_TIERS):
                tier_w = lotus_width_for_value(cw)
                tw += tier_w
                cw = tier_w
            seed_cost = LOTUS_J_BITS + tw + pw
            if seed_cost >= budget:
                break
            # Count of values with this payload width
            if pw == 1:
                count = 1  # only value 0 (payload_value=1)
            else:
                count = 1 << pw  # 2^pw values in this range
            saving = budget - seed_cost
            total_savings += count * saving
            total_count += count
        avg_savings = total_savings / total_count if total_count > 0 else 0.0
    else:
        avg_savings = 0.0
    
    return ArityAnalysis(
        arity=arity,
        block_size=block_size,
        span_bytes=span_bytes,
        span_bits=span_bits,
        header_bits=h,
        j3d2_budget=budget,
        max_comp_seed_index=max_idx,
        n_compressive_seeds=n_comp,
        log2_n_comp=log2_n_comp,
        log2_universe=log2_universe,
        gap_bits=gap,
        p_comp_per_span=p_comp,
        avg_savings_bits=avg_savings,
        expected_savings_per_span_bits=p_comp * avg_savings,
    )

@dataclass
class AggregateResult:
    block_size: int
    max_arity: int
    max_seed_len: Optional[int]
    arity_analyses: list  # list of ArityAnalysis
    aggregate_p_comp: float  # combined probability across all arities
    aggregate_expected_savings_bits: float
    literal_overhead_bits_per_block: float
    net_expected_bits_per_block: float  # positive = compression, negative = expansion
    break_even_p_comp: float  # probability needed to break even

def aggregate_analysis(block_size: int, max_arity: int = 5, 
                       max_seed_len: Optional[int] = None) -> AggregateResult:
    """Aggregate analysis across all arity levels."""
    analyses = []
    for a in range(1, max_arity + 1):
        analyses.append(analyze_arity(a, block_size, max_seed_len))
    
    # Aggregate: P(any arity compresses) = 1 - prod(1 - P_comp(a))
    prod_no_comp = 1.0
    for an in analyses:
        prod_no_comp *= (1.0 - an.p_comp_per_span)
    agg_p = 1.0 - prod_no_comp
    
    # Aggregate expected savings: sum of independent expected values
    # (slight overcount due to overlapping spans, but correct for independent events)
    agg_savings = sum(a.expected_savings_per_span_bits for a in analyses)
    
    # Literal overhead per block (V1 format: just the literal marker)
    lit_overhead = LITERAL_HEADER_BITS  # 6 bits per literal block
    
    # Net: expected savings minus literal overhead on non-matched blocks
    # E[net per block] = P_agg * E[savings] - (1-P_agg) * literal_overhead
    # But this isn't quite right because different arities cover different numbers of blocks
    # For simplicity, use arity-1 as the per-block baseline
    net = agg_savings - (1.0 - agg_p) * lit_overhead
    
    # Break-even: P * savings = (1-P) * overhead ≈ overhead for small P
    break_even = lit_overhead / (analyses[0].avg_savings_bits + lit_overhead) if analyses[0].avg_savings_bits > 0 else 1.0
    
    return AggregateResult(
        block_size=block_size,
        max_arity=max_arity,
        max_seed_len=max_seed_len,
        arity_analyses=analyses,
        aggregate_p_comp=agg_p,
        aggregate_expected_savings_bits=agg_savings,
        literal_overhead_bits_per_block=lit_overhead,
        net_expected_bits_per_block=net,
        break_even_p_comp=break_even,
    )


# ─── V2 Record analysis ───

def v2_record_bits(span_len: int, seed_index: int) -> int:
    """V2 seed-span record: Lotus(tag=0) + Lotus(span_len-1) + Lotus(seed_index)"""
    return j3d2_bits(0) + j3d2_bits(span_len - 1) + j3d2_bits(seed_index)

def v2_max_compressive_seed_index(span_len: int) -> int:
    """Largest seed index where V2 record < span bits."""
    span_bits = 8 * span_len
    tag_bits = j3d2_bits(0)  # 6
    len_bits = j3d2_bits(span_len - 1)
    budget = span_bits - tag_bits - len_bits
    if budget <= 0:
        return -1
    lo, hi = 0, 2**64
    if j3d2_bits(0) >= budget:
        return -1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            if j3d2_bits(mid) < budget:
                lo = mid
            else:
                hi = mid - 1
        except (ValueError, OverflowError):
            hi = mid - 1
    return lo

# ─── Main analysis ───

def run_full_analysis():
    results = {}
    
    # ════════════════════════════════════════════════════════════
    # 1. Lotus overhead characterization
    # ════════════════════════════════════════════════════════════
    print("=" * 72)
    print("SECTION 1: Lotus J3D2 Overhead Characterization")
    print("=" * 72)
    
    overhead_data = []
    for exp in range(0, 65):
        v = max(0, (1 << exp) - 1)
        bits = j3d2_bits(v)
        info = math.log2(v + 1) if v > 0 else 0
        overhead = bits - info
        overhead_data.append((v, bits, info, overhead))
    
    print(f"{'Value':>18s}  {'Lotus bits':>10s}  {'log2(v+1)':>10s}  {'Overhead':>10s}")
    for v, b, i, o in overhead_data[:25]:
        print(f"{v:>18d}  {b:>10d}  {i:>10.2f}  {o:>10.2f}")
    print("  ...")
    
    # Key finding: overhead oscillates 6-9 bits
    overheads = [o for _, _, _, o in overhead_data if _ > 0]
    print(f"\nOverhead range: {min(overheads):.2f} to {max(overheads):.2f} bits")
    print(f"Mean overhead: {sum(overheads)/len(overheads):.2f} bits")
    
    # ════════════════════════════════════════════════════════════
    # 2. Per-arity compressive seed analysis
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 2: Per-Arity Compressive Seed Space (V1 format)")
    print("=" * 72)
    
    for bs in [4, 8, 16, 32]:
        print(f"\n--- Block size = {bs} bytes ---")
        print(f"{'Arity':>6s}  {'Span':>6s}  {'Header':>7s}  {'Budget':>7s}  {'MaxIdx':>18s}  {'N_comp':>18s}  {'log2(N)':>8s}  {'Gap':>8s}")
        for a in range(1, 11):
            try:
                an = analyze_arity(a, bs)
                max_idx_str = f"{an.max_comp_seed_index:>18d}" if an.max_comp_seed_index >= 0 else "           NONE"
                n_comp_str = f"{an.n_compressive_seeds:>18d}" if an.n_compressive_seeds > 0 else "              0"
                print(f"{a:>6d}  {an.span_bytes:>5d}B  {an.header_bits:>6d}b  {an.j3d2_budget:>6d}b  {max_idx_str}  {n_comp_str}  {an.log2_n_comp:>8.2f}  {an.gap_bits:>8.2f}")
            except Exception as e:
                print(f"{a:>6d}  {a*bs:>5d}B  error: {e}")
    
    # ════════════════════════════════════════════════════════════
    # 3. Aggregate arity analysis — Robin's core argument
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 3: Aggregate Arity Analysis (Independent Trials)")
    print("=" * 72)
    print("Each arity level is an independent chance at a compressive match.")
    print("The aggregate probability = 1 - prod(1 - P_comp(a)).")
    
    for bs in [8, 16, 32]:
        for max_a in [5, 10, 20]:
            agg = aggregate_analysis(bs, max_a)
            print(f"\n--- Block size={bs}, max arity={max_a} ---")
            print(f"  Aggregate P_comp = {agg.aggregate_p_comp:.6e}")
            print(f"  Individual P_comp by arity:")
            for an in agg.arity_analyses[:min(10, max_a)]:
                print(f"    arity {an.arity:2d}: P={an.p_comp_per_span:.4e}  gap={an.gap_bits:.1f}  avg_savings={an.avg_savings_bits:.1f}b")
            if max_a > 10:
                remaining = sum(a.p_comp_per_span for a in agg.arity_analyses[10:])
                print(f"    arity 11-{max_a}: sum(P) = {remaining:.4e}")
            print(f"  Literal overhead per block: {agg.literal_overhead_bits_per_block:.0f} bits")
            print(f"  Break-even P_comp: {agg.break_even_p_comp:.4e}")
            print(f"  Net expected bits/block: {agg.net_expected_bits_per_block:.6f}")
    
    # ════════════════════════════════════════════════════════════
    # 4. Gap invariance test — the central contested claim
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 4: Gap Invariance Test")
    print("=" * 72)
    print("Does the gap close with deeper search? Test across seed depths 1-8.")
    
    for bs in [8]:
        print(f"\n--- Block size = {bs} ---")
        print(f"{'Depth':>6s}  {'Seeds':>18s}  {'log2':>8s}  ", end="")
        for a in range(1, 6):
            print(f"{'A'+str(a)+' gap':>8s}  ", end="")
        print(f"{'Agg gap':>8s}")
        
        for depth in range(1, 9):
            seeds = seed_count(depth)
            log2_s = math.log2(seeds)
            gaps = []
            for a in range(1, 6):
                an = analyze_arity(a, bs, max_seed_len=depth)
                # The "effective gap" for this depth
                span_bits = 8 * a * bs
                effective_n = min(an.n_compressive_seeds, seeds)
                if effective_n > 0:
                    eff_gap = span_bits - math.log2(effective_n)
                else:
                    eff_gap = float('inf')
                gaps.append(eff_gap)
            
            # Aggregate gap: log2(2^S / sum_a(N_comp_a))
            # This is the effective gap considering ALL arities
            total_comp = 0
            min_span = 8 * bs  # arity 1 span
            for a in range(1, 6):
                an = analyze_arity(a, bs, max_seed_len=depth)
                effective_n = min(an.n_compressive_seeds, seeds)
                # Weight by span: larger spans cover more bytes but target fewer positions
                total_comp += effective_n  # simplified
            agg_gap = min_span * 8 - math.log2(total_comp) if total_comp > 0 else float('inf')
            
            print(f"{depth:>6d}  {seeds:>18d}  {log2_s:>8.2f}  ", end="")
            for g in gaps:
                if g < 1000:
                    print(f"{g:>8.2f}  ", end="")
                else:
                    print(f"     inf  ", end="")
            print(f"{agg_gap:>8.2f}")
    
    # ════════════════════════════════════════════════════════════
    # 5. What would it take? — Break-even analysis
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 5: Break-Even Analysis")
    print("=" * 72)
    print("What hit-rate multiplier (from transforms/presets/dictionaries)")
    print("would be needed for net compression on 1MB input?")
    
    input_bytes = 1_000_000
    for bs in [2, 4, 8]:
        print(f"\n--- Block size={bs} (uncapped N_comp) ---")

        # For arity 1 — no max_seed_len cap, so we get the theoretical break-even
        an = analyze_arity(1, bs)
        spans = input_bytes // bs

        # Expected matches at base rate
        base_matches = spans * an.p_comp_per_span

        # Savings per match
        if an.avg_savings_bits > 0:
            savings_per_match_bytes = an.avg_savings_bits / 8
        else:
            savings_per_match_bytes = 0

        # Per-span literal overhead (V1 format): J1D1(5) = 6 bits per literal span
        lit_marker_bits = LITERAL_HEADER_BITS  # 6 bits

        # Break-even condition (per-span):
        #   P * (avg_savings + lit_marker) > lit_marker
        #   P > lit_marker / (avg_savings + lit_marker)
        p_needed = lit_marker_bits / (an.avg_savings_bits + lit_marker_bits) if an.avg_savings_bits > 0 else 1.0
        if an.p_comp_per_span > 0:
            multiplier = p_needed / an.p_comp_per_span
        else:
            multiplier = float('inf')

        # Also compute total literal overhead for context
        total_lit_overhead_bits = spans * lit_marker_bits
        total_savings_bits = base_matches * an.avg_savings_bits

        print(f"  Base P_comp (arity 1): {an.p_comp_per_span:.4e}")
        print(f"  Avg savings/match: {an.avg_savings_bits:.2f} bits")
        print(f"  P needed for break-even: {p_needed:.4f} ({p_needed*100:.1f}%)")
        print(f"  Spans in 1MB: {spans:,}")
        print(f"  Expected base matches: {base_matches:.4f}")
        print(f"  Total literal overhead: {total_lit_overhead_bits/8:,.0f} bytes ({lit_marker_bits}b × {spans:,} spans)")
        print(f"  Total expected savings: {total_savings_bits/8:.4f} bytes")
        if multiplier < float('inf'):
            print(f"  Break-even multiplier: {multiplier:,.0f}x")
        else:
            print(f"  Break-even multiplier: infinite (no base matches)")
    
    # ════════════════════════════════════════════════════════════
    # 6. Extended arity — is there a sweet spot?
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 6: Extended Arity with Custom Header Encoding")
    print("=" * 72)
    print("What if we use a more efficient header for high arity?")
    print("Optimal prefix code for N arities uses ceil(log2(N+1)) bits for arity,")
    print("plus the literal marker.")
    
    for bs in [8, 32]:
        print(f"\n--- Block size = {bs} ---")
        # With custom encoding: arity field uses ceil(log2(max_arity+1)) bits
        # Plus 1 bit for literal/seed flag
        for max_a in [5, 10, 50, 100, 256]:
            arity_field_bits = math.ceil(math.log2(max_a + 2))  # +1 for literal, +1 for the count
            flag_bit = 1  # seed vs literal
            custom_header = arity_field_bits + flag_bit
            
            total_p = 0
            total_e_savings = 0
            for a in range(1, max_a + 1):
                span_bits = 8 * a * bs
                budget = span_bits - custom_header
                if budget <= 6:  # minimum J3D2 is 6 bits
                    continue
                # Count compressive seeds with this custom header
                lo, hi = 0, 2**62
                if j3d2_bits(0) >= budget:
                    continue
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    try:
                        if j3d2_bits(mid) < budget:
                            lo = mid
                        else:
                            hi = mid - 1
                    except:
                        hi = mid - 1
                n_comp = lo + 1
                log2_p = math.log2(n_comp) - span_bits
                p = 2**log2_p if log2_p > -1074 else 0.0
                total_p += p
                # Approximate savings
                avg_sav = max(0, budget - j3d2_bits(n_comp // 2))
                total_e_savings += p * avg_sav
            
            print(f"  max_arity={max_a:>4d}: header={custom_header}b  agg_P={total_p:.4e}  E[savings/pos]={total_e_savings:.6f} bits")
    
    # ════════════════════════════════════════════════════════════
    # 7. The critical insight: overhead structure
    # ════════════════════════════════════════════════════════════
    print("\n" + "=" * 72)
    print("SECTION 7: Why the Gap Exists — Structural Analysis")
    print("=" * 72)
    
    print("""
For a span of S bits and a seed record of h + J3D2(i) bits:
  - Record is compressive when h + J3D2(i) < S
  - J3D2(i) ≈ log2(i) + overhead, where overhead ∈ [6, 9]
  - So compressive seeds: i < 2^(S - h - overhead)
  - P(compressive match) = 2^(S - h - overhead) / 2^S = 2^(-h - overhead)
  
This probability depends ONLY on h (header bits) and the Lotus overhead,
NOT on the span size S or the search depth.

The gap = S - log2(N_comp) = h + overhead ≈ header + 7.5 bits

For V1 with Lotus J1D1 arity encoding:
  - Arity 1: h=3, gap ≈ 3 + 7.5 = 10.5
  - Arity 2-5: h=5, gap ≈ 5 + 7.5 = 12.5

For V2 with variable span lengths:
  - tag=0 costs 6 bits, span_len costs ~6-9 bits
  - Total fixed overhead: ~12-15 bits + Lotus overhead on seed index
  - Effective gap: ~20-24 bits (matches the POWER_MODEL's 24-32 range)
""")

    # Verify: compute actual gap for V2 format
    # Gap = span_bits - log2(N_comp_v2), NOT span_bits - log2(total_seeds)
    print("V2 format gap verification (gap = span_bits - log2(N_comp)):")
    for span_len in [3, 4, 8, 16, 32, 64]:
        max_idx = v2_max_compressive_seed_index(span_len)
        if max_idx >= 0:
            n_comp = max_idx + 1
            gap = span_len * 8 - math.log2(n_comp)
            record_at_max = v2_record_bits(span_len, max_idx)
            print(f"  span={span_len}B ({span_len*8}b): N_comp={n_comp}, gap={gap:.2f}, record@max={record_at_max}b")
        else:
            print(f"  span={span_len}B: no compressive seeds")
    
    print("\n" + "=" * 72)
    print("SECTION 8: Summary of Key Results")
    print("=" * 72)
    print("""
KEY RESULTS:

1. LOTUS OVERHEAD: The J3D2 encoding costs log2(v) + 6 to 8 bits.
   This overhead is structural — it's the price of self-delimiting encoding.
   It determines the gap.

2. GAP STRUCTURE: For V1 arity 1, the gap ranges 10-13 bits (by block size:
   10 at bs=2, 12 at bs=4, 13 at bs=8). V2 gap is ~32 bits.

   This gap is:
   - INDEPENDENT of search depth (confirmed by POWER_MODEL)
   - WEAKLY dependent on block size (through Lotus tier boundaries)

3. AGGREGATE ARITY: Multiple arity levels give independent chances, but
   arity 1 dominates. Aggregate improvement: ~1.12x at bs=4.

4. BREAK-EVEN: ~75% of spans must find compressive matches for net
   compression (each match saves ~2 bits, each literal costs 6 bits).
   Break-even multipliers: 824x at bs=2, 3066x at bs=4, 6144x at bs=8.

5. THREE LEVERS: Literal overhead (6 bits in V1 — format design can
   reduce this), average savings per match (~2 bits — biasing toward
   low-index seeds helps), and base hit probability (density mechanisms
   raise this). These multiply independently.

6. WHERE VIABLE COMPRESSION LIVES: A mechanism that raises effective
   hit probability via transforms, dictionaries, presets, or source-family
   structure. See FINDINGS.md for the full analysis.
""")

if __name__ == "__main__":
    run_full_analysis()

