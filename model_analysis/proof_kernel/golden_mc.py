#!/usr/bin/env python3
"""Constant-N coverage Monte Carlo for the Golden Config sweep.
Real Bernoulli draws at EXACT per-window probabilities from
golden_format_arithmetic.json; sampled integer record costs; exact wire
accounting; greedy largest-arity-first; fragmentation + shuffle
re-pairing; slot-keyed singles as one lifetime trial. Resumable."""
import json, pickle, os, sys
import numpy as np

ART = json.load(open(os.path.join(os.path.dirname(__file__), "golden_format_arithmetic.json")))
HEADER_BITS = 120
CHECKPOINTS = [250, 500, 1000, 2000, 4000, 8000]

def least_prime_geq(n):
    def isp(m):
        f = 2
        while f * f <= m:
            if m % f == 0: return False
            f += 1
        return m > 1
    while not isp(n): n += 1
    return n

def shuffle_perm(N):
    P = least_prime_geq(max(N, 7))
    j = (5 * np.arange(N)) % P
    while True:
        bad = j >= N
        if not bad.any(): break
        j[bad] = (5 * j[bad]) % P
    return j

class CostSampler:
    def __init__(self, entry):
        self.costs = np.array([int(c) for c in entry["by_cost"]])
        counts = np.array(list(entry["by_cost"].values()), dtype=float)
        self.p = counts / counts.sum()
    def __call__(self, rng, n):
        return rng.choice(self.costs, size=n, p=self.p) if n else np.array([], int)

def new_state(N):
    return dict(claimed=np.zeros(N, bool), t=0, rec_bits=0, rec_count=0,
                pos=np.arange(N), results={}, rng_state=None, single_done=False)

def run_config(cfg, passes_target, state):
    B, profile, arities, N, seed = cfg["B"], cfg["profile"], cfg["arities"], cfg["N"], cfg["seed"]
    lit = {"payback": 2, "canonical": 3}[profile]
    ents = {a: ART[f"B{B}|{profile}|a{a}|full"] for a in arities if a > 1}
    samplers = {a: CostSampler(ents[a]) for a in ents}
    rng = np.random.default_rng(seed)
    if state["rng_state"] is not None:
        rng.bit_generator.state = state["rng_state"]
    perm = shuffle_perm(N)
    claimed, pos = state["claimed"], state["pos"]
    if not state["single_done"] and 1 in arities:
        e1 = ART[f"B{B}|{profile}|a1|full"]
        hits = rng.random(N) < e1["p"]
        n1 = int(hits.sum()); claimed[hits] = True
        state["rec_bits"] += int(CostSampler(e1)(rng, n1).sum())
        state["rec_count"] += n1
        state["single_done"] = True
    while state["t"] < passes_target:
        state["t"] += 1
        arr = np.empty(N, int); arr[pos] = np.arange(N)
        un = ~claimed[arr]
        for a in sorted(ents, reverse=True):
            e = ents[a]
            ok = un[:N - a + 1].copy()
            for j in range(1, a):
                ok &= un[j:N - a + 1 + j]
            cand = np.flatnonzero(ok & (rng.random(N - a + 1) < e["p"]))
            acc = 0; last_end = -1
            for i in cand:
                if i <= last_end or not un[i:i + a].all(): continue
                un[i:i + a] = False
                claimed[arr[i:i + a]] = True
                acc += 1; last_end = i + a - 1
            if acc:
                state["rec_bits"] += int(samplers[a](rng, acc).sum())
                state["rec_count"] += acc
        pos = perm[pos]
        if state["t"] in CHECKPOINTS:
            unclaimed = int((~claimed).sum())
            arr2 = np.empty(N, int); arr2[pos] = np.arange(N)
            tail = 0
            for x in arr2[::-1]:
                if claimed[x]: break
                tail += 1
            wire = state["rec_bits"] + unclaimed * (lit + B) + HEADER_BITS
            if tail > 1: wire -= tail * lit - 3
            state["results"][state["t"]] = dict(
                coverage=round(1 - unclaimed / N, 4), wire_bits=int(wire),
                ratio=round(wire / (N * B), 5), records=state["rec_count"])
    state["claimed"], state["pos"] = claimed, pos
    state["rng_state"] = rng.bit_generator.state
    return state

CONFIGS = {
 "G1_B8_canon_a12":  dict(B=8,  profile="canonical", arities=[1,2],     N=16384, seed=11),
 "G2_B8_canon_a123": dict(B=8,  profile="canonical", arities=[1,2,3],   N=16384, seed=12),
 "G3_B8_payb_a123":  dict(B=8,  profile="payback",   arities=[1,2,3],   N=16384, seed=13),
 "G4_B4_canon_a34":  dict(B=4,  profile="canonical", arities=[3,4],     N=16384, seed=14),
 "G5_B16_canon_a12": dict(B=16, profile="canonical", arities=[1,2],     N=16384, seed=15),
 "G6_B8_canon_a2":   dict(B=8,  profile="canonical", arities=[2],       N=16384, seed=16),
}

def main():
    name = sys.argv[1]; target = int(sys.argv[2])
    cfg = CONFIGS[name]
    pkl = f"_golden_{name}.pkl"
    state = pickle.load(open(pkl, "rb")) if os.path.exists(pkl) else new_state(cfg["N"])
    state = run_config(cfg, target, state)
    pickle.dump(state, open(pkl, "wb"))
    print(name, "t =", state["t"])
    for T, r in sorted(state["results"].items()):
        print(f"  T={T:5d} coverage={r['coverage']:.3f} ratio={r['ratio']:.4f} records={r['records']}")

if __name__ == "__main__":
    main()
