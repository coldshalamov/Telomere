#!/usr/bin/env python3
"""Fast discrimination of the None cases. Budget=20000 (large vs the ~128
native), few files, prints each file immediately so a timeout still yields
data. Reports forks at the correct epoch where recovered."""
import sys, os, random, hashlib, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "proof_kernel"))
import v1_roundtrip_proof as P
from forensics_scale_probe import instrumented_decode, c_mean

BIG = 20000
P_B = 4

def main():
    rng = random.Random(20260613)
    cases = [(16, 6), (20, 4), (16, 7), (20, 6)]
    for (N, T) in cases:
        for f in range(3):
            blocks = ["".join(rng.choice("01") for _ in range(P_B))
                      for _ in range(N)]
            orig = "".join(blocks)
            want = hashlib.sha256(orig.encode()).hexdigest()
            bits, nrec, nbund = P.encode(blocks, P_B, T, rng=random.Random(1))
            t0 = time.time()
            out, T_found, forks = instrumented_decode(
                bits, N, P_B, want, T_max=T + 2, fork_budget=BIG)
            dt = time.time() - t0
            if out is None:
                tag = "STRUCTURAL_FAIL_or_budget>20k"
            elif out != orig:
                tag = "WRONG_BYTES"
            elif T_found == T:
                tag = f"RECOVERED@T={T} forks={forks}"
            else:
                bits_lo, _, _ = P.encode(blocks, P_B, T_found, rng=random.Random(1))
                tag = ("BENIGN_EXHAUST(wire==T%d)" % T_found
                       if bits_lo == bits else "AMBIGUOUS_SHORTER@T=%d" % T_found)
            print(f"N={N} T={T} f={f} nbund={nbund} -> {tag}  "
                  f"({dt:.1f}s)  Ncmean={nbund*c_mean(T):.2f}", flush=True)

if __name__ == "__main__":
    main()
