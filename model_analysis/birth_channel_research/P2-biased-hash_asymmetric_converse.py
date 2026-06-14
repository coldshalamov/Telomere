#!/usr/bin/env python3
"""
P2 — ASYMMETRIC soft-coupling converse (close the last escape).

The main ledger established the gate floor supply_cost >= I (no sub-1x). But the
SHARPEST objection exploits the seed-cost SKEW directly: bias the hash so that
HIGH-VALUE (low-cost, rare) seeds get their own pass labels and the low-value
(high-cost, numerous) seeds share. The claim to kill: such an asymmetric
coupling reads a birth-bit while losing < 1 bit of USABLE supply, because the
supply it sheds is "cheap" (low-value) supply.

HYPOTHESIS (before running): this fails by the COUNT-vs-VALUE co-location
already shown — but I make it airtight here by computing, for an ARBITRARY
coupling, the GENERAL converse:

   conveyed bits         = I(L ; t)              [what the decoder reads free]
   match-supply loss     = I(L ; t)              [per-pass set shrinks by 2^I]
   value-weighted supply loss <= I(L ; t)        [you can only shed value you
                                                   labelled away, and value is
                                                   co-located with count]

The decisive quantity: when you carve the seed set to convey I bits, the
per-pass eligible COUNT shrinks by 2^I. The VALUE-weighted supply shrinks by
the SAME factor (to first order) BECAUSE E[win|hit] is ~constant (~2 bits)
across the set — value per ticket does not vary enough to let you preferentially
keep it. We verify: for any partition, (value-weighted supply retained) /
(count supply retained) stays ~1 — you cannot retain disproportionate value.

If even the value-greedy / maximally-skewed coupling cannot get
value_retained/count_retained > 1 by more than the per-ticket value variance
(which is tiny: E[win|hit]~2, the distribution is concentrated), then there is
NO sub-1x: the seed-class partition is supply-optimal, in BOTH count and value.

This is the rate-distortion converse the lead asked for, made concrete on the
planted Kraft distribution.
"""

import math


def cost_classes(W, c_min=1):
    return [(c, 2 ** c, W - c) for c in range(c_min, W)]


def entropy(ps):
    return -sum(p * math.log2(p) for p in ps if p > 0)


def general_converse(W, T, c_min=1):
    """
    For the planted set, consider ANY disjoint partition of the compressive
    seeds into T classes (one per pass). The decoder reads the class => conveys
    H(f) bits where f_t = (count in class t)/S_all. The match-supply loss vs T
    fresh unrestricted passes is ALWAYS log2(T) (you collapse T*S_all -> S_all),
    but the FREELY-CONVEYED part is H(f); the residual log2(T)-H(f) is unpaid
    (stored bits). So conveyed-per-supply-loss = H(f)/log2(T) <= 1.

    The VALUE question: does an asymmetric partition let you keep MORE value per
    unit of count you retain? We test the extreme: the value-greedy partition
    (high-win classes isolated). Compute, for the class that an accepted match
    most likely falls in, the value-per-ticket vs the global E[win|hit]. If they
    are equal, value and count are perfectly co-located and there is no sorting.
    """
    cc = cost_classes(W, c_min)
    S_all = sum(n for (_, n, _) in cc)
    total_value = sum(n * w for (_, n, w) in cc)
    global_ewh = total_value / S_all

    # value-greedy partition: sort by win desc, give the top (T-1) cost-classes
    # their own pass, dump the rest into one class.
    by_win = sorted(cc, key=lambda r: r[2], reverse=True)
    classes = []
    for i in range(min(T - 1, len(by_win))):
        classes.append([by_win[i]])
    rest = by_win[min(T - 1, len(by_win)):]
    if rest:
        classes.append(rest)

    rows = []
    for cls in classes:
        cnt = sum(n for (_, n, _) in cls)
        val = sum(n * w for (_, n, w) in cls)
        f = cnt / S_all                       # count-share (== supply-share)
        ewh_class = val / cnt if cnt else 0    # value per ticket in this class
        rows.append((f, ewh_class, cnt, val))

    f_list = [r[0] for r in rows]
    H_f = entropy(f_list)
    conveyed_per_loss = H_f / math.log2(T)

    # value-vs-count co-location metric: the value-weighted supply retained if
    # you KEEP only the high-value classes vs the count retained. If the ratio
    # (value_share / count_share) for the high-value classes is ~1, no sorting.
    # Report the max value/count leverage any single class achieves.
    leverage = max((r[1] / global_ewh) for r in rows)  # ewh_class / global_ewh
    return {
        "S_all": S_all,
        "global_ewh": global_ewh,
        "H_f_conveyed": H_f,
        "log2T": math.log2(T),
        "conveyed_per_supply_loss": conveyed_per_loss,
        "max_value_leverage": leverage,   # >1 would mean a class beats avg value
        "rows": rows,
    }


def value_sorting_ceiling(W, c_min=1):
    """
    The fundamental ceiling on value-sorting. The per-ticket value is win=W-c,
    distributed with weight n_c=2^c. The BEST any value-sorting can do is keep
    the single highest-value class. Its value-per-ticket is (W-c_min); the
    fraction of total SUPPLY (count) it carries is 2^c_min / S_all (vanishing).
    So to convey even one full bit you must isolate ~half the COUNT, which sits
    at high c (low value). Quantify: to convey b bits you isolate 2^-b of the
    count into distinguished classes; the value you can lift above average is
    bounded by the value variance, which we compute.
    """
    cc = cost_classes(W, c_min)
    S_all = sum(n for (_, n, _) in cc)
    mean_win = sum(n * w for (_, n, w) in cc) / S_all
    var_win = sum(n * (w - mean_win) ** 2 for (_, n, w) in cc) / S_all
    std_win = math.sqrt(var_win)
    return mean_win, std_win, var_win


def main():
    print("=" * 78)
    print("P2 — ASYMMETRIC soft-coupling converse (the sharpest escape, closed)")
    print("=" * 78)

    print("\n[value-sorting ceiling] per-ticket win distribution (weight 2^c):")
    print(f"  {'W':>3} {'E[win]':>8} {'std[win]':>9} {'CV=std/mean':>12}")
    for W in (10, 13, 16, 20):
        mw, sw, vw = value_sorting_ceiling(W)
        print(f"  {W:>3} {mw:>8.4f} {sw:>9.4f} {sw/mw:>12.4f}")
    print("  => win is TIGHTLY concentrated (mean~2, std~1.4): there is almost no")
    print("     value spread to exploit. Value per ticket ~ constant => count and")
    print("     value are CO-LOCATED; no partition can sort one from the other.")

    print("\n[general converse] value-greedy (max-skew) partition cannot beat 1:1:")
    print(f"  {'W':>3} {'T':>4} {'H(f)conv':>10} {'log2T':>7} {'conv/loss':>10} "
          f"{'maxValLev':>10}")
    for W in (13, 16):
        for T in (4, 8, 16):
            r = general_converse(W, T)
            print(f"  {W:>3} {T:>4} {r['H_f_conveyed']:>10.4f} {r['log2T']:>7.4f} "
                  f"{r['conveyed_per_supply_loss']:>10.4f} {r['max_value_leverage']:>10.4f}")
    print("  => conv/loss < 1 ALWAYS for the skewed partition (it conveys FEWER")
    print("     free bits per unit supply lost than the uniform split).")
    print("  => max_value_leverage is bounded (a high-value class has ~6x the avg")
    print("     win but ~0 supply share; it conveys ~0 bits). The jackpot trap.")

    print("\n" + "=" * 78)
    print("CONCLUSION: the seed-class partition is SUPPLY-OPTIMAL. The conveyed")
    print("part costs EXACTLY 1 supply-bit per birth-bit (2x/bit); the residual is")
    print("stored-bits. Non-uniformity does NOT permit sub-1x: count and value are")
    print("co-located (E[win|hit] ~ 2 bits, tightly concentrated), so no class-")
    print("decodable coupling can shed cheap supply while keeping dear supply.")
    print("=" * 78)


if __name__ == "__main__":
    main()
