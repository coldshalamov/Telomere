#!/usr/bin/env python3
"""
v1_roundtrip_proof.py — proof BY CONSTRUCTION that V1 multi-pass decode
requires ZERO stored metadata beyond the file header.

State model: constant-N block-state (STATE_MODEL_COMPARISON.md, Design B).
  - N blocks of B bits each; N never changes.
  - Shuffle sigma: i -> 5*i mod P (P = least prime >= N), cycle-walked.
    Exactly invertible: i -> inv(5)*i mod P, walked.
  - Pass t = search -> replace(annotate) -> shuffle.
  - Bundles (arity >= 2) expand with key H(seed, pass)   <- per-pass salt
  - Singles  (arity 1)  expand with key H(seed, original_slot)  <- k-free
  - Wire: walk the FINAL arrangement; emit each record once at its first
    final slot; emit literals; skip slots filled by record expansion.
  - Header: N, B, sha256(original). NO pass count, NO birth tags,
    NO per-record epochs, NO literal length fields.

Decoder derives EVERYTHING:
  - T (pass count): trial values, accepted by header-hash match.
  - bundle birth pass k and child placement: the T-candidate index-
    arithmetic test (wrong k must land every child on a coincidentally
    consistent slot; survivors forked and settled by the header hash).
  - single placement and salt: original slot x = sigma^-T(final slot),
    no k anywhere.

Acceptance is RELAXED (any exact match accepted, even when the record is
not smaller): this is a DECODE proof, not a compression claim. Real
SHA-256 throughout; no planted expansions; no oracle anywhere in decode.
"""
import hashlib, random, sys


def least_prime_geq(n):
    def is_prime(m):
        if m < 2: return False
        if m % 2 == 0: return m == 2
        f = 3
        while f * f <= m:
            if m % f == 0: return False
            f += 2
        return True
    while not is_prime(n): n += 1
    return n

def make_shuffle(N):
    P = least_prime_geq(max(N, 3))
    inv5 = pow(5, -1, P)
    def fwd(i):
        j = (5 * i) % P
        while j >= N: j = (5 * j) % P
        return j
    def bwd(i):
        j = (inv5 * i) % P
        while j >= N: j = (inv5 * j) % P
        return j
    return fwd, bwd

def sig_pow(f, i, t):
    for _ in range(t): i = f(i)
    return i

def H_bits(key: str, nbits: int) -> str:
    out = ""
    ctr = 0
    while len(out) < nbits:
        d = hashlib.sha256(f"{key}#{ctr}".encode()).digest()
        out += "".join(f"{b:08b}" for b in d)
        ctr += 1
    return out[:nbits]

# ---------------- encoder ----------------
# alphabet (toy, prefix-free): 00=literal, 01=arity1, 10=arity2, 11=arity3
SEED_BITS = 14   # toy fixed-width seed field (Lotus wire-proven separately)

def encode(blocks, B, T, max_seed=9000, accepts_per_pass=2, rng=None):
    N = len(blocks)
    fwd, bwd = make_shuffle(N)
    arr = list(range(N))            # original indices in current order
    cov = {}                        # original idx -> record
    records = []
    for t in range(1, T + 1):
        accepts = 0
        for a in (3, 2):            # greedy largest arity first
            i = 0
            while i + a <= N and accepts < accepts_per_pass:
                idxs = arr[i:i + a]
                if any(x in cov for x in idxs):
                    i += 1; continue
                target = "".join(blocks[x] for x in idxs)
                hit = None
                for s in range(max_seed):
                    if H_bits(f"{s}|p{t}", a * B) == target:
                        hit = s; break
                if hit is not None:
                    rec = dict(k=t, q=i, a=a, seed=hit, children=idxs[:])
                    records.append(rec)
                    for x in idxs: cov[x] = rec
                    accepts += 1
                    i += a
                else:
                    i += 1
        # singles: key by ORIGINAL slot (k-free), one per pass
        sing = 0
        for i in range(N):
            if sing >= 1: break
            x = arr[i]
            if x in cov: continue
            for s in range(max_seed):
                if H_bits(f"{s}|s{x}", B) == blocks[x]:
                    rec = dict(k=t, q=i, a=1, seed=s, children=[x])
                    records.append(rec); cov[x] = rec; sing += 1
                    break
        arr = apply_shuffle(arr, fwd)
    # serialize from final arrangement
    fpos = {x: p for p, x in enumerate(arr)}
    first = {}
    skip = set()
    for r in records:
        slots = sorted(fpos[x] for x in r["children"])
        first[slots[0]] = r
        skip.update(slots[1:])
    bits = ""
    for p in range(N):
        if p in skip: continue
        if p in first:
            r = first[p]
            cw = {1: "01", 2: "10", 3: "11"}[r["a"]]
            bits += cw + format(r["seed"], f"0{SEED_BITS}b")
        else:
            bits += "00" + blocks[arr[p]]
    return bits, len(records), sum(1 for r in records if r["a"] >= 2)

def apply_shuffle(arr, fwd):
    out = [None] * len(arr)
    for i, x in enumerate(arr): out[fwd(i)] = x
    return out

# ---------------- decoder (no encoder state; header = N, B, hash) ----------
def try_decode(bits, N, B, T_try, fork_budget=128):
    fwd, bwd = make_shuffle(N)
    # stack of (cursor, filled{slot: original_content_assignment}, blocks{x: bits})
    init = (0, {}, {})
    stack = [(0, init)]   # (slot, state)
    forks = 0
    sols = []
    def rec(slot, cur, filled, blocks):
        nonlocal forks
        while slot < N and slot in filled: slot += 1
        if slot == N:
            if cur == len(bits) and len(blocks) == N:
                sols.append(dict(blocks))
            return
        if cur + 2 > len(bits): return
        cw = bits[cur:cur + 2]; cur += 2
        if cw == "00":
            if cur + B > len(bits): return
            content = bits[cur:cur + B]; cur += B
            x = sig_pow(bwd, slot, T_try)
            nb = dict(blocks); nb[x] = content
            nf = dict(filled); nf[slot] = True
            rec(slot + 1, cur, nf, nb); return
        a = {"01": 1, "10": 2, "11": 3}[cw]
        if cur + SEED_BITS > len(bits): return
        seed = int(bits[cur:cur + SEED_BITS], 2); cur += SEED_BITS
        if a == 1:
            x = sig_pow(bwd, slot, T_try)            # k-free
            content = H_bits(f"{seed}|s{x}", B)
            nb = dict(blocks); nb[x] = content
            nf = dict(filled); nf[slot] = True
            rec(slot + 1, cur, nf, nb); return
        # bundle: infer (k, j0) by the T-candidate index-arithmetic test
        cands = []
        for k in range(1, T_try + 1):
            shifts = T_try - k + 1
            p0 = sig_pow(bwd, slot, shifts)
            for j0 in range(a):
                q = p0 - j0
                if q < 0 or q + a > N: continue
                F = [sig_pow(fwd, q + j, shifts) for j in range(a)]
                if min(F) != slot: continue
                if any((f != slot) and (f in filled) for f in F): continue
                if any(f < slot and f != slot for f in F): continue
                cands.append((k, q, F))
        if len(cands) > 1: forks += len(cands) - 1
        if forks > fork_budget: return
        for (k, q, F) in cands:
            exp = H_bits(f"{seed}|p{k}", a * B)
            nb = dict(blocks); nf = dict(filled)
            ok = True
            for j in range(a):
                x = sig_pow(bwd, q + j, k - 1)
                if x in nb: ok = False; break
                nb[x] = exp[j * B:(j + 1) * B]
                nf[F[j]] = True
            if ok: rec(slot + 1, cur, nf, nb)
    rec(0, 0, {}, {})
    return sols, forks

def decode(bits, N, B, want_hash, T_max=10):
    for T_try in range(1, T_max + 1):
        sols, forks = try_decode(bits, N, B, T_try)
        for s in sols:
            out = "".join(s[x] for x in range(N))
            if hashlib.sha256(out.encode()).hexdigest() == want_hash:
                return out, T_try, forks
    return None, None, None

# ---------------- harness ----------------
def main():
    rng = random.Random(20260611)
    B = 4
    trials = ok = 0
    tot_forks = 0
    tot_bundles = 0
    for N in (10, 13, 16):
        for T in (2, 3, 4, 5):
            for rep in range(3):
                blocks = ["".join(rng.choice("01") for _ in range(B))
                          for _ in range(N)]
                orig = "".join(blocks)
                want = hashlib.sha256(orig.encode()).hexdigest()
                bits, nrec, nbund = encode(blocks, B, T, rng=rng)
                out, T_found, forks = decode(bits, N, B, want)
                trials += 1
                tot_bundles += nbund
                good = (out == orig) and (T_found == T)
                ok += good
                tot_forks += forks or 0
                print(f"N={N:2d} T={T} rep={rep} rec={nrec:2d} "
                      f"bundles={nbund} T_derived={T_found} forks={forks} "
                      f"{'OK' if good else 'FAIL'}")
    print(f"\n{ok}/{trials} exact round trips "
          f"(bundles total={tot_bundles}, ambiguity forks total={tot_forks})")
    print("decoder inputs: wire bits + N + B + sha256(original). "
          "No pass count, no birth tags, no epochs, no length fields.")
    return 0 if ok == trials else 1

if __name__ == "__main__":
    sys.exit(main())
