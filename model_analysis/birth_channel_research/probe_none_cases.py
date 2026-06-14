#!/usr/bin/env python3
"""Discriminate the None-decode cases (N=16 T=6,7; N=20 T=4,6,7) into:
  (1) budget-killed  -> succeeds at fork_budget=1e6 with T_found==T
  (2) benign exhaust -> succeeds at low T_found, out==orig (wire==lower-T wire)
  (3) structural fail -> still None even at fork_budget=1e6 (correctness bug)

Re-runs each case across several files at a huge fork budget and reports the
fork count AT THE CORRECT EPOCH (so we can fit Lane B's survivor growth).
Uses the SAME rng seed/order as forensics_scale_probe Phase A so we hit the
same files; but to be robust we sweep multiple files per (N,T) and report
the distribution of outcomes.
"""
import sys, os, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "proof_kernel"))
import v1_roundtrip_proof as P
from forensics_scale_probe import instrumented_decode, c_mean

BIG = 10**6

def classify(N, T, blocks):
    orig = "".join(blocks)
    want = hashlib.sha256(orig.encode()).hexdigest()
    bits, nrec, nbund = P.encode(blocks, P_B, T, rng=random.Random(1))
    out, T_found, forks = instrumented_decode(bits, N, P_B, want,
                                              T_max=T + 3, fork_budget=BIG)
    if out is None:
        return ("STRUCTURAL_FAIL", None, None, nbund, bits)
    if out != orig:
        return ("WRONG_BYTES", T_found, forks, nbund, bits)
    if T_found == T:
        return ("BUDGET_KILLED(recovered)", T_found, forks, nbund, bits)
    # out==orig but T_found<T: benign effective-pass exhaustion?
    # confirm wire identity at the lower effective T_found
    bits_lo, _, _ = P.encode(blocks, P_B, T_found, rng=random.Random(1))
    tag = "BENIGN_EXHAUST" if bits_lo == bits else "AMBIGUOUS_SHORTER"
    return (tag, T_found, forks, nbund, bits)

P_B = 4

def main():
    rng = random.Random(20260613)
    cases = [(16, 6), (16, 7), (20, 4), (20, 6), (20, 7),
             (16, 8), (20, 8), (24, 6), (24, 8)]
    print(f"{'N':>3} {'T':>2} | per-file outcome  (fork_budget={BIG})")
    for (N, T) in cases:
        tally = {}
        forks_at_T = []
        for f in range(6):
            blocks = ["".join(rng.choice("01") for _ in range(P_B))
                      for _ in range(N)]
            tag, Tf, forks, nbund, _ = classify(N, T, blocks)
            tally[tag] = tally.get(tag, 0) + 1
            if tag.startswith("BUDGET_KILLED") and forks is not None:
                forks_at_T.append(forks)
        fa = (f"forks@correctT={min(forks_at_T)}..{max(forks_at_T)}"
              if forks_at_T else "")
        print(f"{N:>3} {T:>2} | {tally}  {fa}  Ncmean={nbund*c_mean(T):.2f}")

if __name__ == "__main__":
    main()
