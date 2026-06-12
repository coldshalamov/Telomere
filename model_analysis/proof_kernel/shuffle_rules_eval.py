"""Shuffle-rule bake-off for the V1 spec.

Maintainer's criteria, measured (not argued):
  A. decodes: rule is an exact permutation (bijective) and invertible by
     replaying the same static rule — for EVERY block count N, including
     counts that change between passes;
  B. no early returns: passes until any block revisits a previous position
     (min cycle length), and until the WHOLE configuration repeats (period);
  C. variability: fraction of adjacent PAIRS ever repeated over T passes
     (new neighbors every pass = fresh windows);
  D. robust to changing N: same statistics when N shrinks mid-run (merges);
  E. static: zero parameters that depend on pass or file content.

Rules under test (all static; modulus = current count, decoder-known):
  rotation      i -> (i + floor(0.618 N)) mod N
  bit_reversal  reverse binary digits (next pow2 domain, cycle-walk)
  faro          i -> 2 i mod M, M = N - 1 + (N odd)  (cycle-walk)
  mult_prime    i -> a i mod P, P = least prime >= N, a fixed, cycle-walk
  feistel       4-round Feistel on next-pow2 domain, fixed key, cycle-walk

Run: python shuffle_rules_eval.py
"""

from __future__ import annotations

import hashlib
import json


def is_prime(n: int) -> bool:
    if n < 4:
        return n >= 2
    if n % 2 == 0:
        return False
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


def next_prime(n: int) -> int:
    while not is_prime(n):
        n += 1
    return n


def make_rotation(N: int):
    k = int(0.6180339887 * N) or 1
    return lambda i: (i + k) % N


def make_bit_reversal(N: int):
    bits = max(1, (N - 1).bit_length())

    def f(i: int) -> int:
        j = int(format(i, f"0{bits}b")[::-1], 2)
        while j >= N:  # cycle-walk
            j = int(format(j, f"0{bits}b")[::-1], 2)
        return j
    return f


def make_faro(N: int):
    if N <= 2:
        return lambda i: i
    M = N if N % 2 == 1 else N - 1  # 2 must be invertible mod M (M odd)
    M = M if M % 2 == 1 else M + 1

    def f(i: int) -> int:
        j = (2 * i) % M if i < M else i
        while j >= N:
            j = (2 * j) % M if j < M else j
        return j
    return f


A_FIXED = 5  # protocol constant multiplier


def make_mult_prime(N: int):
    P = next_prime(N)
    a = A_FIXED
    while P % a == 0:  # ensure invertible (P prime => any a < P works; guard tiny N)
        a += 1

    def f(i: int) -> int:
        j = (a * i) % P
        while j >= N:  # cycle-walk within the prime field
            j = (a * j) % P
        return j
    return f


def make_feistel(N: int):
    bits = max(2, (N - 1).bit_length())
    half = bits // 2
    lo_mask = (1 << half) - 1

    def round_fn(r: int, x: int) -> int:
        d = hashlib.sha256(bytes([r]) + x.to_bytes(8, "big")).digest()
        return int.from_bytes(d[:4], "big")

    def perm_once(i: int) -> int:
        L, R = i >> half, i & lo_mask
        for r in range(4):
            L, R = R, L ^ (round_fn(r, R) & ((1 << (bits - half)) - 1))
        return (L << half) | R if (L << half) | R < (1 << bits) else 0

    def f(i: int) -> int:
        j = perm_once(i)
        while j >= N:
            j = perm_once(j)
        return j
    return f


RULES = {
    "rotation": make_rotation,
    "bit_reversal": make_bit_reversal,
    "faro": make_faro,
    "mult_prime": make_mult_prime,
    "feistel": make_feistel,
}


def evaluate(name: str, N: int, T: int = 500) -> dict:
    g = RULES[name](N)
    table = [g(i) for i in range(N)]  # static rule: precompute once
    f = table.__getitem__
    # A: bijectivity
    img = sorted(f(i) for i in range(N))
    bijective = img == list(range(N))
    # B: cycle structure (positions)
    seen = [False] * N
    cycles = []
    for s in range(N):
        if seen[s]:
            continue
        c = 0
        j = s
        while not seen[j]:
            seen[j] = True
            j = f(j)
            c += 1
        cycles.append(c)
    min_cycle = min(cycles)
    n_fixed = sum(1 for c in cycles if c == 1)
    # C: adjacency-pair novelty over T passes — track items, not positions.
    # perm[i] = position of item i after one application; iterate.
    pos = list(range(N))            # pos[item] = current position
    inv = list(range(N))            # inv[position] = item
    pairs_seen = set()
    repeats = 0
    total = 0
    for t in range(T):
        # apply: item at position p moves to f(p)
        new_inv = [0] * N
        for p in range(N):
            new_inv[f(p)] = inv[p]
        inv = new_inv
        for p in range(N - 1):
            pair = (inv[p], inv[p + 1])
            total += 1
            if pair in pairs_seen:
                repeats += 1
            else:
                pairs_seen.add(pair)
    # D: shrink robustness — re-instantiate at 0.61 N, recheck bijectivity
    N2 = int(N * 0.61)
    f2 = RULES[name](N2)
    bij2 = sorted(f2(i) for i in range(N2)) == list(range(N2))
    return {
        "rule": name,
        "bijective": bijective,
        "bijective_after_shrink": bij2,
        "min_cycle_passes_before_position_revisit": min_cycle,
        "max_cycle": max(cycles),
        "n_cycles": len(cycles),
        "fixed_points": n_fixed,
        "pair_repeat_fraction": round(repeats / max(total, 1), 6),
    }


def main() -> None:
    N = 1009  # prime-ish mid-size for exact cycle analysis
    out = [evaluate(name, N) for name in RULES]
    print(json.dumps(out, indent=1))
    # decisive secondary check at non-prime N with shrink sequence
    print("\nshrinking-N sanity (N=1200 -> 730 -> 444), mult_prime vs faro min cycles:")
    for name in ("mult_prime", "faro", "feistel"):
        row = []
        for n in (1200, 730, 444):
            e = evaluate(name, n, T=200)
            row.append((n, e["min_cycle_passes_before_position_revisit"], e["fixed_points"], e["pair_repeat_fraction"]))
        print(name, row)


if __name__ == "__main__":
    main()
