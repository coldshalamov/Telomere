#!/usr/bin/env python3
"""
forensics_scale_probe.py -- push v1_roundtrip_proof past its toy regime and
measure the bundle birth-epoch decode mechanism's real cost:

  (1) forks-per-bundle as a function of (N, T)  [Lane B survivor count for bundles]
  (2) whether fork_budget=128 silently drops the correct decoding at high T
  (3) the largest T at which decode still round-trips = bundle max-free-reach K
  (4) N*c_mean(T) for the bundles, to confirm whether the proof lives in
      Lane E's free region.

We import the proof module verbatim and re-run encode/decode at larger (N,T),
plus an instrumented decode that reports whether the correct solution was
pruned by the fork budget.
"""
import sys, os, math, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "proof_kernel"))
import v1_roundtrip_proof as P


def c_mean(T, q=2**-2.5):
    """Lane E residual surviving-readings per bundle record: log2(1+(T-1)q).
    q = free explosion-check pass-distinguishing prob ~ 2^-2.5 per the brief."""
    return math.log2(1 + (T - 1) * q)


def instrumented_decode(bits, N, B, want_hash, T_max, fork_budget):
    """Like P.decode but lets us vary fork_budget and report per-T_try forks
    and whether a solution was found."""
    for T_try in range(1, T_max + 1):
        sols, forks = try_decode_fb(bits, N, B, T_try, fork_budget)
        for s in sols:
            out = "".join(s[x] for x in range(N))
            if hashlib.sha256(out.encode()).hexdigest() == want_hash:
                return out, T_try, forks
    return None, None, None


def try_decode_fb(bits, N, B, T_try, fork_budget):
    """Copy of P.try_decode with parametric fork_budget."""
    fwd, bwd = P.make_shuffle(N)
    forks = 0
    sols = []
    SEED_BITS = P.SEED_BITS

    def rec(slot, cur, filled, blocks):
        nonlocal forks
        while slot < N and slot in filled:
            slot += 1
        if slot == N:
            if cur == len(bits) and len(blocks) == N:
                sols.append(dict(blocks))
            return
        if cur + 2 > len(bits):
            return
        cw = bits[cur:cur + 2]; cur += 2
        if cw == "00":
            if cur + B > len(bits):
                return
            content = bits[cur:cur + B]; cur += B
            x = P.sig_pow(bwd, slot, T_try)
            nb = dict(blocks); nb[x] = content
            nf = dict(filled); nf[slot] = True
            rec(slot + 1, cur, nf, nb); return
        a = {"01": 1, "10": 2, "11": 3}[cw]
        if cur + SEED_BITS > len(bits):
            return
        seed = int(bits[cur:cur + SEED_BITS], 2); cur += SEED_BITS
        if a == 1:
            x = P.sig_pow(bwd, slot, T_try)
            content = P.H_bits(f"{seed}|s{x}", B)
            nb = dict(blocks); nb[x] = content
            nf = dict(filled); nf[slot] = True
            rec(slot + 1, cur, nf, nb); return
        cands = []
        for k in range(1, T_try + 1):
            shifts = T_try - k + 1
            p0 = P.sig_pow(bwd, slot, shifts)
            for j0 in range(a):
                q = p0 - j0
                if q < 0 or q + a > N:
                    continue
                F = [P.sig_pow(fwd, q + j, shifts) for j in range(a)]
                if min(F) != slot:
                    continue
                if any((f != slot) and (f in filled) for f in F):
                    continue
                if any(f < slot and f != slot for f in F):
                    continue
                cands.append((k, q, F))
        if len(cands) > 1:
            forks += len(cands) - 1
        if forks > fork_budget:
            return
        for (k, q, F) in cands:
            exp = P.H_bits(f"{seed}|p{k}", a * B)
            nb = dict(blocks); nf = dict(filled)
            ok = True
            for j in range(a):
                x = P.sig_pow(bwd, q + j, k - 1)
                if x in nb:
                    ok = False; break
                nb[x] = exp[j * B:(j + 1) * B]
                nf[F[j]] = True
            if ok:
                rec(slot + 1, cur, nf, nb)

    rec(0, 0, {}, {})
    return sols, forks


def run(Ns, Ts, reps, fork_budget, T_max_pad=2, seed=20260613):
    rng = random.Random(seed)
    B = 4
    print(f"=== fork_budget={fork_budget} ===")
    print(f"{'N':>3} {'T':>2} {'rec':>3} {'bund':>4} {'fpb':>6} {'forks':>6} "
          f"{'Tder':>4} {'Ncmean':>7} {'budget_hit':>10} {'OK':>4}")
    summary = {}
    for N in Ns:
        for T in Ts:
            okc = 0; budget_hits = 0; fpb_max = 0
            f_acc = 0; b_acc = 0
            for rep in range(reps):
                blocks = ["".join(rng.choice("01") for _ in range(B))
                          for _ in range(N)]
                orig = "".join(blocks)
                want = hashlib.sha256(orig.encode()).hexdigest()
                bits, nrec, nbund = P.encode(blocks, B, T, rng=rng)
                out, T_found, forks = instrumented_decode(
                    bits, N, B, want, T_max=T + T_max_pad,
                    fork_budget=fork_budget)
                good = (out == orig) and (T_found == T)
                okc += good
                budget_hits += (1 if (forks or 0) >= fork_budget else 0)
                fpb = ((forks or 0) / nbund) if nbund else 0
                fpb_max = max(fpb_max, fpb)
                f_acc += forks or 0
                b_acc += nbund
                ncm = nbund * c_mean(T)
                if rep == 0:
                    print(f"{N:>3} {T:>2} {nrec:>3} {nbund:>4} {fpb:>6.1f} "
                          f"{forks if forks is not None else -1:>6} "
                          f"{str(T_found):>4} {ncm:>7.3f} "
                          f"{'YES' if (forks or 0) >= fork_budget else 'no':>10} "
                          f"{'OK' if good else 'FAIL':>4}")
            summary[(N, T)] = dict(ok=okc, reps=reps, budget_hits=budget_hits,
                                   fpb_max=fpb_max,
                                   avg_forks=f_acc / reps,
                                   avg_bund=b_acc / reps)
    return summary


if __name__ == "__main__":
    # Phase A: replicate-and-extend with the proof's own fork_budget=128
    print("PHASE A: extend T and N at the proof's native fork_budget=128\n")
    Ns = [10, 16, 20]
    Ts = [2, 3, 4, 5, 6, 7]
    s128 = run(Ns, Ts, reps=2, fork_budget=128)

    print("\nPHASE B: SAME runs with fork_budget=10 (does the budget gate the "
          "answer? if OK drops, the checksum/budget is load-bearing)\n")
    s10 = run([16], [2, 3, 4, 5, 6, 8], reps=2, fork_budget=10)

    print("\nPHASE C: SAME runs with fork_budget=2 (near-fingerprint test)\n")
    s2 = run([16], [2, 3, 4, 5, 6, 8], reps=2, fork_budget=2)

    print("\n=== SUMMARY: OK rate by (N,T) at fork_budget=128 ===")
    for (N, T), d in sorted(s128.items()):
        print(f"N={N:3d} T={T:2d}  OK={d['ok']}/{d['reps']}  "
              f"avg_forks={d['avg_forks']:7.1f}  avg_bundles={d['avg_bund']:.1f}  "
              f"fpb_max={d['fpb_max']:.1f}  budget_hits={d['budget_hits']}")
