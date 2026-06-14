#!/usr/bin/env python3
"""
P2 — KEYSTONE ATTACK: biased/structured hash couples birth-pass to the STORED
SEED field. Is the seed-class partition supply-OPTIMAL, or does seed-set
NON-UNIFORMITY (low-index / Lotus-cost bias, E[win|hit]~2 bits) permit a
coupling that conveys a birth-bit while losing STRICTLY LESS than 1 bit of
match supply (sub-1x, beating the 1:1 partition)?

This is PURE COUNTING / EXACT ENUMERATION over a PLANTED Kraft cost
distribution. No hashing, no luck (BRIEF rule 2/3: SHA searches prove nothing
here; the question is information-theoretic).

================================================================================
HYPOTHESIS (written BEFORE running — protocol rule 1)
================================================================================

From the mechanics I expect:

H-A (partition baseline = conservation anchor). For seed->pass to be FREE-
  decodable, the per-pass eligible seed sets S_t must be DISJOINT (a seed must
  determine its pass with no extra stored bits). Under the uniform hash law
  every eligible seed contributes the SAME 2^-W hit-prob to a window, so supply
  per pass is proportional to |S_t| (a COUNT), and disjointness forces
  sum_t |S_t| <= |S_all|. Total supply over T passes <= ONE unrestricted pass,
  vs T unrestricted passes => factor-T supply loss = log2(T) birth bits paid
  EXACTLY in match-supply. 2x per bit. I expect this to be VALUE-INDEPENDENT:
  it falls out of count additivity; the value (W-c) distribution never enters.

H-B (the live question: count-vs-value CO-LOCATION). Sub-1x is possible ONLY if
  a class-decodable partition can preferentially KEEP high-value matches while
  SHEDDING low-value ones. Kraft law: #seeds of cost c ∝ 2^c, win = W-c.
  - COUNT density over c: ∝ 2^c  (rises toward c=W: numerous near-threshold)
  - VALUE density over c: ∝ 2^c·(W-c) (value-weighted supply)
  I expect BOTH to be dominated by the SAME region (near c=W, the numerous
  cheap-win seeds), and rare jackpots (small c, big win) to contribute
  negligibly to BOTH. If count and value are CO-LOCATED, no class-decodable
  partition can sort value from count => NO sub-1x. I expect co-location.

H-C (entropy lever kills asymmetric exploit). Bits actually conveyed by a
  partition = H(birth distribution it induces) <= log2(T), maximized ONLY at
  EQUAL-supply classes. Exploiting non-uniformity needs an ASYMMETRIC partition,
  but that concentrates births on few passes, dropping H(birth) FASTER than it
  saves supply. So the optimum is the UNIFORM partition at exactly 2x/bit;
  asymmetry is strictly worse (supply-loss per conveyed bit > 1). I expect the
  optimum to be the uniform corner.

H-D (soft-coupling converse — close the escape). A BIASED probabilistic
  (non-disjoint) hash is the obvious objection: smear seed->pass so classes
  overlap. I expect a rate-distortion converse: I(seed;pass) <= supply-entropy-
  loss at >= 1:1 across the WHOLE family (not just hard partitions). Smoothing
  cannot beat the corner: any mutual information the decoder reads about pass
  from seed is paid by an equal reduction in the usable (unambiguous) supply.

Master counting gate (applied to THIS candidate): the biased hash is content-
  blind (bias on seed VALUE, not on compressed content). So apparent sub-1x AND
  unbounded => pigeonhole violation. Leaks to watch: (a) explosion-check's
  separate 2.5-bit subsidy bleeding in (keep separate; coupling must be 1:1 on
  ITS OWN bits); (b) "value preserved" living in rare jackpots whose total
  supply contribution is negligible (<1 real bit conveyed).

Distinction from Lane E: period-P was VACUOUS (reverse-walk index gives t mod P
  free). Seed-coupling is NOT vacuous: seed bits are ALREADY stored, so
  seed->pass is genuine DOUBLE-DUTY reuse; the cost is REAL supply loss, not
  vacuity. The seed field is the only FREE ON-WIRE correlate of birth pass.
"""

import math
from itertools import product

# ----------------------------------------------------------------------------
# The planted Kraft cost distribution (J3D1-Lotus-like, exact, no hashing).
# A seed whose record costs c bits: there are ~2^c such seeds (Kraft: each
# extra bit of allowed cost ~doubles the eligible seed count). A window of W
# bits nets win = W - c when such a seed matches. Compressive seeds: c < W.
# Per-(seed,key) hit prob is the SAME 2^-W for every eligible seed (uniform
# hash law) — so "supply" contributed by cost-class c is proportional to the
# COUNT n_c = 2^c (number of distinct seeds at that cost), each a fresh lottery
# ticket. This is the exact structure of MATH_MODEL §2.
# ----------------------------------------------------------------------------

def cost_classes(W, c_min=1):
    """Return list of (c, n_c=count∝2^c, win=W-c) for compressive c in [c_min, W-1]."""
    out = []
    for c in range(c_min, W):
        n_c = 2 ** c          # count of seeds at cost c (Kraft)
        win = W - c           # bits netted per match at this cost
        out.append((c, n_c, win))
    return out


def expected_win_given_hit(W, c_min=1):
    """E[win|hit] over the compressive seed set = sum n_c*win / sum n_c.
    MATH_MODEL §2 predicts ~2 bits, independent of W and scale."""
    cc = cost_classes(W, c_min)
    num = sum(n_c * win for (_, n_c, win) in cc)
    den = sum(n_c for (_, n_c, _) in cc)
    return num / den, den


# ============================================================================
# STEP 1 (H-A): the hard-partition baseline = conservation anchor.
# Partition the compressive seed set into T disjoint classes (one per pass).
# Supply of pass t ∝ |S_t| (count). Free seed->pass decode REQUIRES disjoint
# classes. Total usable supply = sum |S_t| = |S_all| (one pass), regardless of
# HOW you split. So vs T unrestricted passes (each with |S_all| supply): loss
# factor = T. The VALUE distribution does not enter the supply-count identity.
# ============================================================================

def step1_partition_anchor(W, T, c_min=1):
    cc = cost_classes(W, c_min)
    S_all = sum(n_c for (_, n_c, _) in cc)
    # T unrestricted passes: each pass sees the FULL set -> total supply T*S_all
    unrestricted_total = T * S_all
    # T disjoint classes: total supply = S_all (partition is exhaustive)
    partition_total = S_all
    loss_factor = unrestricted_total / partition_total  # = T, exactly
    bits_conveyed_max = math.log2(T)                     # log2(T) birth bits
    supply_loss_bits = math.log2(loss_factor)            # = log2(T)
    return {
        "S_all": S_all,
        "unrestricted_total_supply": unrestricted_total,
        "partition_total_supply": partition_total,
        "loss_factor": loss_factor,
        "supply_loss_bits": supply_loss_bits,
        "bits_conveyed_max": bits_conveyed_max,
        "bits_per_bit": supply_loss_bits / bits_conveyed_max,
    }


# ============================================================================
# STEP 2 (H-B): COUNT-vs-VALUE co-location — the load-bearing check.
# If count density (∝2^c) and value density (∝2^c*(W-c)) peak in the SAME
# region, no class-decodable partition can preferentially keep value while
# shedding count -> no sub-1x. Compute both, report where each is concentrated,
# and the correlation. Also: the "value-preserving" partition that keeps only
# the highest-win (lowest-c) classes — show its supply collapses (jackpot trap).
# ============================================================================

def step2_colocation(W, c_min=1):
    cc = cost_classes(W, c_min)
    total_count = sum(n_c for (_, n_c, _) in cc)
    total_value = sum(n_c * win for (_, n_c, win) in cc)
    rows = []
    for (c, n_c, win) in cc:
        count_share = n_c / total_count
        value_share = (n_c * win) / total_value
        rows.append((c, win, n_c, count_share, value_share))
    # Where is each density concentrated? Mean cost under count-measure vs
    # under value-measure. If they coincide, co-located.
    mean_c_count = sum(c * n_c for (c, _, n_c, _, _) in
                       [(c, win, n_c, cs, vs) for (c, win, n_c, cs, vs) in rows]) / total_count
    mean_c_value = sum(c * (n_c * (W - c)) for (c, win, n_c, _, _) in rows) / total_value
    # Top-value-share partition: take classes in DESCENDING win (ascending c),
    # accumulate until we've "kept the value" — see how much COUNT (supply) that
    # costs. The jackpot trap: keeping the top-half of VALUE costs almost ALL
    # the count? or almost none? If value lives where count lives, keeping value
    # keeps count (no sorting possible).
    return rows, total_count, total_value, mean_c_count, mean_c_value


# ============================================================================
# STEP 3 (H-C): entropy lever. For an arbitrary disjoint partition into T
# classes with supply fractions f_t (sum=1), the decoder reads pass from the
# seed's class; bits CONVEYED = H(f) (entropy of the induced birth distribution
# the partition can certify), and the usable supply is still S_all total but
# the REFRESH benefit only accrues to passes that actually have supply.
#
# The right "supply efficiency" of a partition: a uniform unrestricted run gets
# T*S_all "ticket-passes"; a partition gets S_all split as f_t per pass. The
# value of fresh dice is that EACH pass is a fresh lottery; what you buy with
# the partition is the ability to RUN T passes while paying for one pass of
# supply. The bits you convey is H(f) (you certify which of the f_t-weighted
# classes); supply loss vs T fresh unrestricted passes is log2(T) FIXED (you
# always collapse T*S_all -> S_all). So:
#   supply_loss_bits = log2(T)   (independent of f — you lost a factor T no
#                                  matter how you split)
#   bits_conveyed    = H(f) <= log2(T)  (maximized at uniform f_t = 1/T)
# => bits_per_conveyed_bit = log2(T) / H(f) >= 1, EQUALITY ONLY AT UNIFORM.
# Asymmetric f makes it STRICTLY WORSE. This is the proof asymmetry can't win.
# ============================================================================

def entropy(fs):
    return -sum(f * math.log2(f) for f in fs if f > 0)

def step3_entropy_lever(W, T, c_min=1):
    cc = cost_classes(W, c_min)
    S_all = sum(n_c for (_, n_c, _) in cc)
    log2T = math.log2(T)
    results = []
    # (a) uniform partition: f_t = 1/T
    f_uniform = [1.0 / T] * T
    H_u = entropy(f_uniform)
    results.append(("uniform", H_u, log2T / H_u))
    # (b) a strongly asymmetric partition: one big class + (T-1) tiny.
    #     f_0 = 0.9, rest split the remaining 0.1 equally.
    if T > 1:
        f_skew = [0.9] + [0.1 / (T - 1)] * (T - 1)
        H_s = entropy(f_skew)
        results.append(("skew(0.9)", H_s, log2T / H_s))
    # (c) value-greedy: try to give the high-value (low-c) classes their own
    #     pass and dump everything else in one class. The high-value classes
    #     are TINY in count (n_c=2^c small at low c), so f for them is tiny ->
    #     H(f) tiny -> ratio huge. This is the jackpot trap made quantitative.
    cc_sorted = sorted(cc, key=lambda r: r[2], reverse=True)  # by win desc (low c first)
    # assign the T-1 highest-win cost classes each its own pass, rest -> last
    fs = []
    used = 0
    for i in range(min(T - 1, len(cc_sorted))):
        c, n_c, win = cc_sorted[i]
        fs.append(n_c / S_all)
        used += n_c
    fs.append((S_all - used) / S_all)  # the dumping-ground class (huge count)
    # pad if fewer classes than T
    while len(fs) < T:
        fs.append(0.0)
    H_v = entropy([f for f in fs])
    results.append(("value-greedy", H_v, (log2T / H_v) if H_v > 0 else float('inf')))
    return results, log2T


# ============================================================================
# STEP 4 (H-D): close the SOFT / biased (non-disjoint) escape.
#
# Two parts, kept rigorously separate (an earlier version conflated them and
# printed a spurious sub-1x — see §3 of the findings):
#
#   4a. EXACT 1:1 backbone — hard partition into k <= T EQUAL groups.
#       conveyed = supply_loss = log2(k) exactly; residual (stored) = log2(T/k);
#       total = log2(T). Proven-by-construction for every k. This is the clean
#       1:1 result the lead's partition argument refers to.
#
#   4b. SOFT escape closed by the COUNTING GATE (the rate-distortion converse),
#       NOT by any posited supply formula. The information identity
#           I(L;t) + H(t|L) = log2(T)            (chain rule, EXACT)
#       holds for every coupling. The supply floor is FORCED by pigeonhole:
#       cost < I, the encoder would get MORE effective fresh-pass supply than a
#       full unrestricted run for free => random data net-compresses => the
#       master gate is violated. Equivalently (cleanest form): decodability
#       forces stored >= H(t|L) and the gate forces total >= log2(T), so
#       supply >= log2(T) - H(t|L) = I, with NO dependence on functional form.
#       Hence supply_cost(I) >= I for EVERY coupling; equality is ACHIEVED at the
#       hard partition (4a). Uniqueness of equality is NOT claimed (min-supply
#       distributions for a given mutual information are generically non-unique).
#
# NOTE on what we deliberately do NOT ship: a specific interior "supply vs beta"
# equality curve. The first attempt (S_all/2^I) is not derived from the geometry;
# any posited form that dips below I would itself violate the gate. The airtight
# objects are the hard-partition exact 1:1 (4a) + the gate floor supply >= I (4b).
# ============================================================================

def step4a_hard_partition_k(T):
    """Exact 1:1 backbone: hard partition into k equal groups, k | T."""
    rows = []
    k = 1
    while k <= T:
        conveyed = math.log2(k)
        supply_loss = math.log2(k)          # exact 1:1 (count additivity, Step 1)
        residual_stored = math.log2(T / k)  # unpaid birth bill -> stored bits
        total = conveyed + residual_stored  # == log2(T)
        rows.append({
            "k": k, "conveyed": conveyed, "supply_loss": supply_loss,
            "residual_stored": residual_stored, "total": total,
            "loss_per_conveyed": (supply_loss / conveyed) if conveyed > 0 else float('nan'),
        })
        k *= 2
    return rows


def step4b_soft_gate_bound(T, n_levels=11):
    """
    For the symmetric biased channel P(t|L)=(1-beta)/T + beta*1[t==L], report the
    EXACT conveyed bits I(L;t) and the residual H(t|L) (chain-rule identity), and
    the GATE-FORCED supply floor supply_cost >= I. We do NOT posit an interior
    supply equality; we report the floor and the residual stored bits.
    """
    results = []
    for i in range(n_levels):
        beta = i / (n_levels - 1)
        p_match = (1 - beta) / T + beta
        p_other = (1 - beta) / T
        row = [p_match] + [p_other] * (T - 1)
        s = sum(row); row = [r / s for r in row]
        H_tgivenL = entropy(row)
        I = math.log2(T) - H_tgivenL          # conveyed bits (exact)
        # Gate-forced floor: supply_cost >= I (pigeonhole; see docstring).
        supply_floor = I
        residual_stored = H_tgivenL           # = log2(T) - I, the unpaid bill
        total_floor = supply_floor + residual_stored  # >= log2(T); == at hard part.
        results.append({
            "beta": round(beta, 3),
            "I_conveyed": I,
            "H_t_given_L": H_tgivenL,
            "supply_floor": supply_floor,
            "residual_stored": residual_stored,
            "total_at_floor": total_floor,
        })
    return results


def main():
    print("=" * 78)
    print("P2 — BIASED-HASH KEYSTONE ATTACK: is the seed-class partition")
    print("     supply-optimal, or does non-uniformity permit sub-1x coupling?")
    print("=" * 78)

    # Sanity: E[win|hit] ~ 2 bits (MATH_MODEL §2), our planted dist is faithful.
    print("\n[SANITY] E[win|hit] over the planted Kraft cost set (expect ~2 bits):")
    for W in (10, 13, 16, 20):
        ewh, nseeds = expected_win_given_hit(W)
        print(f"   W={W:2d}: E[win|hit] = {ewh:.4f} bits   (#compressive seeds = {nseeds})")

    # STEP 1: partition anchor (conservation).
    print("\n" + "-" * 78)
    print("STEP 1 (H-A): hard-partition baseline = the conservation anchor")
    print("-" * 78)
    print(f"{'W':>3} {'T':>4} {'unrestr.supply':>16} {'partition.supply':>16} "
          f"{'lossX':>7} {'lossbits':>9} {'bits/bit':>9}")
    for W in (13, 16):
        for T in (2, 4, 8, 16, 64):
            r = step1_partition_anchor(W, T)
            print(f"{W:>3} {T:>4} {r['unrestricted_total_supply']:>16} "
                  f"{r['partition_total_supply']:>16} {r['loss_factor']:>7.1f} "
                  f"{r['supply_loss_bits']:>9.4f} {r['bits_per_bit']:>9.4f}")
    print("  => loss_factor = T EXACTLY; supply_loss_bits = log2(T) = bits_conveyed_max")
    print("  => EXACTLY 1.0 supply-bit per conveyed bit (2x/bit). VALUE-INDEPENDENT.")

    # STEP 2: co-location.
    print("\n" + "-" * 78)
    print("STEP 2 (H-B): COUNT vs VALUE co-location (the load-bearing check)")
    print("-" * 78)
    for W in (13,):
        rows, tc, tv, mcc, mcv = step2_colocation(W)
        print(f"  W={W}: total count={tc}, total value={tv}")
        print(f"  {'c':>3} {'win':>4} {'n_c=2^c':>9} {'count_share':>12} {'value_share':>12}")
        for (c, win, n_c, cs, vs) in rows:
            print(f"  {c:>3} {win:>4} {n_c:>9} {cs:>12.5f} {vs:>12.5f}")
        print(f"  mean cost under COUNT measure: {mcc:.4f}")
        print(f"  mean cost under VALUE measure: {mcv:.4f}")
        print(f"  separation (count - value mean cost): {mcc - mcv:.4f} bits")
        # jackpot trap: fraction of total VALUE in the lowest-count (jackpot) classes
        # vs the fraction of total COUNT (=supply) they carry.
        print("  --- jackpot trap: keep the K highest-win classes, measure value kept vs supply kept ---")
        cc = cost_classes(W)
        by_win = sorted(cc, key=lambda r: r[2], reverse=True)  # high win first
        cum_count = 0; cum_value = 0
        for K in range(1, len(by_win) + 1):
            c, n_c, win = by_win[K - 1]
            cum_count += n_c; cum_value += n_c * win
            if K <= 5 or K == len(by_win):
                print(f"   keep top-{K:2d} win classes: value_kept={cum_value/tv:.4f}  "
                      f"supply(count)_kept={cum_count/tc:.4f}")

    # STEP 3: entropy lever.
    print("\n" + "-" * 78)
    print("STEP 3 (H-C): entropy lever — uniform partition is the optimum")
    print("-" * 78)
    for W in (13,):
        for T in (4, 8, 16):
            res, log2T = step3_entropy_lever(W, T)
            print(f"  W={W} T={T} (log2T={log2T:.3f}):")
            for (name, H, ratio) in res:
                print(f"     {name:>14}: H(f)={H:.4f} bits conveyed, "
                      f"supply-loss/conveyed = {ratio:.4f}")
    print("  => uniform gives ratio = 1.0 (optimum); every asymmetric split > 1.0")

    # STEP 4: close the soft / biased escape.
    print("\n" + "-" * 78)
    print("STEP 4 (H-D): close the SOFT / biased (non-disjoint) escape")
    print("-" * 78)
    print("  4a. EXACT 1:1 backbone — hard partition into k equal groups (T=8):")
    print(f"  {'k':>3} {'conveyed':>9} {'supply_loss':>12} {'residual_stored':>16} "
          f"{'total':>7} {'loss/conv':>10}")
    for r in step4a_hard_partition_k(8):
        lc = f"{r['loss_per_conveyed']:.4f}" if r['loss_per_conveyed'] == r['loss_per_conveyed'] else "n/a"
        print(f"  {r['k']:>3} {r['conveyed']:>9.4f} {r['supply_loss']:>12.4f} "
              f"{r['residual_stored']:>16.4f} {r['total']:>7.4f} {lc:>10}")
    print("     => conveyed == supply_loss == log2(k) EXACTLY (proven-by-construction);")
    print("        residual log2(T/k) -> stored bits; total = log2(T). This is the 1:1.")
    print()
    print("  4b. SOFT escape closed by the COUNTING GATE (the converse floor, not a")
    print("      posited supply formula). Identity I + H(t|L) = log2(T) is EXACT;")
    print("      gate forces supply_cost >= I (sub-I would net-compress random data).")
    print(f"  {'beta':>6} {'I_conveyed':>11} {'H(t|L)':>8} {'supply_floor(>=I)':>18} "
          f"{'stored_resid':>13} {'total>=':>9}")
    for r in step4b_soft_gate_bound(8):
        print(f"  {r['beta']:>6} {r['I_conveyed']:>11.4f} {r['H_t_given_L']:>8.4f} "
              f"{r['supply_floor']:>18.4f} {r['residual_stored']:>13.4f} "
              f"{r['total_at_floor']:>9.4f}")
    print("     => supply_cost >= I at EVERY bias (gate-forced). Equality is ACHIEVED")
    print("        at the hard partition (4a); uniqueness of equality is NOT claimed.")
    print("     => total cost >= log2(T) for EVERY coupling. NO sub-1x. CONSERVED.")

    print("\n" + "=" * 78)
    print("DONE - see findings/P2-biased-hash.md for the writeup and the gate.")
    print("=" * 78)


if __name__ == "__main__":
    main()
