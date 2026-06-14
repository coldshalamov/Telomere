#!/usr/bin/env python3
"""
Fast birth-channel ledgers for RESULTS.md.

This is a small deterministic companion to the heavier lane toys. It does not
run compression searches. It prices the hidden channels that matter:

* final-board/egg-carton arrangement entropy,
* singles birth ambiguity,
* length-pinned bundle survivor ambiguity,
* biased seed/pass coupling,
* recursive layer carriage.
"""

from math import log2


def log2_choose(n: int, k: int) -> float:
    k = min(k, n - k)
    if k <= 0:
        return 0.0
    return sum(log2(n - i) - log2(i + 1) for i in range(k))


def final_board_table() -> None:
    print("== final board / egg-carton lower bound ==")
    print("R survivors, P candidate birth passes, Q coordinate cells.")
    print("birth maps need R*log2(P) bits. Shrinking R lowers total cost")
    print("and total wins together; the per-survivor price is still log2(P).")
    print()
    print(f"{'R':>7} {'P':>5} {'Q':>10} {'log2C(Q,R)/R':>16} "
          f"{'birth/R':>9} {'2-b win/R':>10} {'verdict':>12}")
    cases = [
        (1000, 64, 1000),
        (1000, 64, 4096),
        (1000, 64, 64000),
        (100, 64, 6400),
        (10, 64, 640),
        (1000, 3, 3000),
    ]
    for r, p, q in cases:
        pos_per = log2_choose(q, r) / r
        birth_per = log2(p)
        verdict = "under-cap" if pos_per < birth_per else "paid"
        if birth_per < 2.0:
            verdict = "finite-ok"
        print(f"{r:7d} {p:5d} {q:10d} {pos_per:16.3f} "
              f"{birth_per:9.3f} {2.0:10.3f} {verdict:>12}")
    print()
    print("Reading: if log2C(Q,R) is below R*log2(P), the final board")
    print("does not have enough distinguishable arrangements to encode all")
    print("birth maps. If it is above, the coordinate note is already at")
    print("least the birth bill. R shrinkage does not change the per-match")
    print("condition log2(P) < 2.")
    print()


def pctb_growth_table(q0: int = 1000, r: int = 1000, branching: int = 6) -> None:
    print("== growing PCTB board cost ==")
    print("Carry-only data keeps R fixed while the instruction board grows.")
    print(f"{'P':>4} {'Q_P':>18} {'pos bits/R':>12} {'total/raw':>10}")
    raw = r * 8
    for passes in [0, 1, 2, 4, 8, 16, 32, 64]:
        q = q0 * (branching ** passes)
        pos = log2_choose(q, r)
        total = 64 + raw + pos
        print(f"{passes:4d} {q:18d} {pos / r:12.3f} {total / raw:10.3f}")
    print()
    print("Reading: storing final positions on a growing board preserves")
    print("mechanics but breaks the raw+epsilon safety bound.")
    print()


def singles_table() -> None:
    print("== arity-1 singles ambiguity ==")
    print("A single is 1->1, so every wrong salt still parses as one item.")
    print("Surviving readings before checksum: S = P^R; cost/R = log2(P).")
    print(f"{'P':>5} {'cost/R':>9} {'net after 2-bit win':>22}")
    for p in [2, 3, 4, 16, 64, 100]:
        cost = log2(p)
        print(f"{p:5d} {cost:9.3f} {2.0 - cost:22.3f}")
    print()


def bundle_table() -> None:
    print("== length-pinned bundle ambiguity ==")
    print("Wrong-salt bundle opens survive with q=2^-E, so")
    print("cost/R = log2(1 + (P-1)*q). E changes the intercept, not the slope.")
    e_by_arity = {
        2: 9.36,
        3: 12.59,
        4: 14.97,
        5: 18.20,
    }
    print(f"{'arity':>6} {'E bits':>8} {'K_free=2^E':>14} "
          f"{'K_cost<2':>12} {'cost@64':>9} {'cost@1e6':>10}")
    for arity, e_bits in e_by_arity.items():
        q = 2 ** (-e_bits)
        k_free = 2 ** e_bits
        k_net = 1 + 3 * k_free
        cost64 = log2(1 + 63 * q)
        cost1m = log2(1 + (1_000_000 - 1) * q)
        print(f"{arity:6d} {e_bits:8.2f} {k_free:14.0f} "
              f"{k_net:12.0f} {cost64:9.3f} {cost1m:10.3f}")
    print()
    print("Reading: bundles have a real finite structural subsidy. They do")
    print("not have an unbounded free birth channel.")
    print()


def biased_seed_table() -> None:
    print("== biased seed/pass coupling ==")
    print("If a seed class conveys I birth bits, the eligible seed supply")
    print("shrinks by at least 2^I. The residual is stored bits.")
    p = 64
    print(f"{'I conveyed':>11} {'supply cost':>12} {'stored residual':>16} "
          f"{'total':>8}")
    for conveyed in [0, 1, 2, 3, 4, 5, 6]:
        total = log2(p)
        residual = total - conveyed
        print(f"{conveyed:11.1f} {conveyed:12.1f} {residual:16.1f} "
              f"{total:8.1f}")
    print()


def recursion_table() -> None:
    print("== recursion / layer carriage ==")
    print("At the content-blind base rate, even a free birth channel inside")
    print("a short layer loses to literal carriage on unclaimed windows.")
    rows = [
        ("~K=5.66 draws/layer", 0.04460, 0.00605, 0.35828),
        ("~1 draw/layer", 0.00772, 0.00105, 0.37210),
    ]
    print(f"{'supply':>22} {'coverage':>9} {'earn/bit':>10} "
          f"{'carriage/bit':>13} {'net/bit':>9}")
    for name, coverage, earn, carriage in rows:
        print(f"{name:>22} {coverage:9.5f} {earn:10.5f} "
              f"{carriage:13.5f} {earn - carriage:9.5f}")
    print()


def main() -> None:
    final_board_table()
    pctb_growth_table()
    singles_table()
    bundle_table()
    biased_seed_table()
    recursion_table()


if __name__ == "__main__":
    main()
