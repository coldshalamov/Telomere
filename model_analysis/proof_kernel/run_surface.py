"""proof_kernel.run_surface — compute the drift surface with brackets.

Emits, per profile point (b, A, D, T):
    lower-bound final/raw   (conservative disjoint-window selection)
    upper-bound final/raw   (oracle interval-scheduling selection)
    concentration ε at α=1e-9 for the requested N

Output is a CSV + stdout table. NO verdict strings anywhere: the surface is
the deliverable; reading it is the maintainer's job (PROOF_TARGET.md).

Usage:
    python run_surface.py                 # default small grid, N=1e6
    python run_surface.py --N 1000000000  # tighter concentration radius
"""
import argparse
import csv

from state_recurrence import pass1_bracket, pass_update
from concentration import eps_for_confidence


def surface_point(N: int, b: int, A: int, D: int, T: int):
    Hlo, Hup = pass1_bracket(N, b, A, D)
    raw = N * b
    out = []
    for H, bound in ((Hlo, "lower"), (Hup, "upper")):
        bits = sum(L * c for L, c in H.items())
        for _t in range(2, T + 1):
            H, row = pass_update(H, A, D, bound)
            if row.get("bits_after") is None:
                break
            nxt = row["bits_after"]
            if abs(nxt - bits) < 1e-9 * max(bits, 1.0):
                bits = nxt
                break
            bits = nxt
        out.append(bits / raw)
    return out[0], out[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=1_000_000)
    ap.add_argument("--T", type=int, default=8)
    ap.add_argument("--csv", default="surface.csv")
    args = ap.parse_args()

    grid_b = (16, 24, 32)
    grid_A = (1, 3, 5)
    grid_D = (16, 64, 128, 1024, 24000)

    rows = []
    print(f"{'b':>4} {'A':>3} {'D':>7} | {'lower %':>10} {'upper %':>10} | {'ε(1e-9) ±%':>11}")
    for b in grid_b:
        for A in grid_A:
            eps = 100 * eps_for_confidence(args.N, b, A)
            for D in grid_D:
                lo, up = surface_point(args.N, b, A, D, args.T)
                print(f"{b:>4} {A:>3} {D:>7} | {100*lo:>10.4f} {100*up:>10.4f} | {eps:>11.5f}")
                rows.append([b, A, D, args.T, args.N,
                             f"{100*lo:.4f}", f"{100*up:.4f}", f"{eps:.6f}"])
    with open(args.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["b_bits", "arity_cap", "depth_bits", "passes", "N_blocks",
                    "lower_pct", "upper_pct", "eps_pct_at_1e-9"])
        w.writerows(rows)
    print(f"surface -> {args.csv}  ({len(rows)} points)")


if __name__ == "__main__":
    main()
