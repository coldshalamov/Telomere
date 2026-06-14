#!/usr/bin/env python3
"""Investigate the N=10,T=8 FAIL where T_derived=4 but encode used T=8.
Two possibilities:
  (a) the encoder did fewer EFFECTIVE passes than T (no matches in later
      passes, so the wire is identical to a smaller-T encode) -> benign:
      T_derived is the true effective pass count, header hash still matched,
      'out==orig' should be TRUE and only T_found==T fails (cosmetic).
  (b) a genuinely DIFFERENT pass count reproduces the EXACT original bytes
      and hash -> a real decode ambiguity the 256-bit referee did NOT catch
      -> the headline 'decode PROVEN' is wrong at this T.
Distinguish them: print out==orig separately from T_found==T.
"""
import sys, os, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "proof_kernel"))
import v1_roundtrip_proof as P

rng = random.Random(20260613)
B = 4
# Reproduce the exact draw sequence used in the probe for N=10 up to T=8.
# The probe iterates N in [10,16,24], T in [2,3,4,5,6,8,10,12], reps=2,
# drawing N blocks each rep. To land on the same N=10,T=8 file we must
# replay the same rng draws. Simpler: just sweep fresh and look for the
# phenomenon directly.
for trial in range(40):
    N = 10
    for T in (6, 8, 10, 12):
        blocks = ["".join(rng.choice("01") for _ in range(B)) for _ in range(N)]
        orig = "".join(blocks)
        want = hashlib.sha256(orig.encode()).hexdigest()
        bits, nrec, nbund = P.encode(blocks, B, T, rng=rng)
        out, T_found, forks = P.decode(bits, N, B, want, T_max=T + 2)
        if out is None:
            print(f"trial{trial} N={N} T={T}: DECODE RETURNED NONE "
                  f"(no solution found, forks budget likely exhausted)")
            continue
        same_bytes = (out == orig)
        if T_found != T or not same_bytes:
            print(f"trial{trial} N={N} T={T}: T_found={T_found} "
                  f"out==orig={same_bytes} forks={forks} "
                  f"nrec={nrec} nbund={nbund}")
            # Re-encode at T_found to check effective-pass-count hypothesis
            bits2, nrec2, nbund2 = P.encode(blocks, B, T_found, rng=random.Random(0))
            print(f"          re-encode at T={T_found}: "
                  f"wire_equal={bits2==bits} nrec2={nrec2} nbund2={nbund2}")
