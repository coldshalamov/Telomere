#!/usr/bin/env python3
"""
TELOMERE EXACT TOY MODEL — explicit recursive state machine, no mean-field shortcuts.

Built to the correction report's Layer-1 spec ("the grounding wire"):
  * b = 6-bit blocks (default), arity 1-5, canonical Kraft arity codes
  * J3D1 seed records (3-bit jumpstarter + length field + payload)
  * literal marker '111' charged ONCE at initialization
  * recursive entries: "a block is a block is a block" — a replacement becomes ONE
    atomic entry; later-pass targets are concatenations of CURRENT ENTRY BITS
  * strict replacement (record < current main span bits), optional tolerated bloat
  * EXPLICIT superposition: a noncompressive exact match within prune-delta D is
    retained as an alternate FORM of the entry (state, not a search shortcut);
    later windows enumerate main/alt combinations; conversions are counted
  * deterministic shuffles: none | pairswap | rotate | affine | prp  (zero file bits)
  * exact enumeration to a stated depth bound (this is a finite toy universe —
    a sanity/grounding artifact, NOT a Telomere-scale theoretical claim)
  * pass-by-pass ledger -> CSV; entry-length distribution; candidate stats;
    superposition stats; adjacency refresh rates; full decode verification

Output language: ledger facts only. No verdicts.
"""
import argparse, csv, hashlib, math, os, sys, time
import numpy as np

# ---------- canonical costs ----------
ACODE = {1: ('00', 2), 2: ('01', 2), 3: ('100', 3), 4: ('101', 3), 5: ('110', 3)}
LIT = ('111', 3)

def j3d1_fields(idx):
    p = max(1, int(idx).bit_length())
    w = max(1, p.bit_length())
    assert w <= 7, "payload-length field exceeds 3-bit jumpstarter range"
    return ((w, 3), (p, w), (int(idx), p))     # (value, width) triples

def record_build(a, idx):
    """Full record (arity codeword + J3D1 seed index) -> (bit_len, bit_value)."""
    code, cl = ACODE[a]
    v, L = int(code, 2), cl
    for val, wd in j3d1_fields(idx):
        v = (v << wd) | val; L += wd
    return L, v

# ---------- seed universe (exact enumeration, stated depth bound) ----------
def load_expansions(kbits, cache="/tmp/tlmr_exp.npy"):
    K = 1 << kbits
    if os.path.exists(cache):
        e = np.load(cache)
        if len(e) >= K: return e[:K]
    out = np.empty(K, dtype=np.uint64)
    for i in range(K):
        out[i] = int.from_bytes(hashlib.blake2b(i.to_bytes(8, 'little'),
                                                digest_size=8).digest(), 'big')
    np.save(cache, out)
    return out

EXP = None
_PC = {}
def prefix_table(L):
    t = _PC.get(L)
    if t is None:
        pref = (EXP >> np.uint64(64 - L))
        order = np.argsort(pref, kind='stable')      # stable => first hit = min index
        _PC[L] = t = (pref[order], order)
    return t

def best_seeds(L, targets):
    """Min seed index whose L-bit expansion prefix equals each target; -1 if none."""
    sp, order = prefix_table(L)
    pos = np.searchsorted(sp, targets)
    res = np.full(len(targets), -1, dtype=np.int64)
    ok = pos < len(sp)
    okk = ok.copy()
    okk[ok] = sp[pos[ok]] == targets[ok]
    res[okk] = order[pos[okk]]
    return res

def expansion_bits(idx, L):
    return int(EXP[idx]) >> (64 - L)

# ---------- entries ----------
class Entry:
    __slots__ = ('L', 'v', 'alt', 'id', 'kind', 'meta')
    _next = [0]
    def __init__(s, L, v, kind, meta=None):
        s.L, s.v, s.kind, s.meta = L, v, kind, meta
        s.alt = None                      # (altL, altv, idx, tgtL, tgtv) retained candidate
        s.id = Entry._next[0]; Entry._next[0] += 1
    def form(s, use_alt):
        return (s.alt[0], s.alt[1]) if (use_alt and s.alt) else (s.L, s.v)

def concat(forms):
    L, v = 0, 0
    for fl, fv in forms:
        L += fl; v = (v << fl) | fv
    return L, v

# ---------- shuffles (deterministic, zero file bits) ----------
def shuffle(es, rule, p):
    n = len(es)
    if rule == 'none' or n < 2: return es
    if rule == 'pairswap':
        o = list(es)
        for i in range(0, n - 1, 2): o[i], o[i+1] = o[i+1], o[i]
        return o
    if rule == 'rotate':
        s = (7919 * p) % n
        return es[s:] + es[:s]
    if rule == 'affine':
        a = 5
        while math.gcd(a, n) != 1: a += 2
        b = (31 * p) % n
        return [es[(a * i + b) % n] for i in range(n)]
    if rule == 'prp':                      # deterministic random-mixing upper bound
        return [es[j] for j in np.random.default_rng(1000 + p).permutation(n)]
    raise ValueError(rule)

# ---------- one pass over current entries ----------
def entry_pass(es, A, supo, prune_D, tol, max_w, tried, stats):
    n = len(es)
    by_L = {}
    # window candidate generation (explicit combos when alts exist)
    for a in range(1, A + 1):
        new_w = rep_w = 0
        for i in range(n - a + 1):
            win = es[i:i + a]
            key = (a,) + tuple(e.id for e in win)
            if key in tried: rep_w += 1
            else: new_w += 1; tried.add(key)
            bar = sum(e.L for e in win) + tol          # strict bar (+ tolerated bloat)
            has_alt = any(e.alt for e in win)
            combos = range(1 << a) if (supo and has_alt) else (0,)
            for m in combos:
                forms = [win[k].form(bool(m >> k & 1)) for k in range(a)]
                Lc, vc = concat(forms)
                if Lc > max_w: continue
                by_L.setdefault(Lc, []).append((vc, i, a, bar, m))
        stats['new_w'][a] = stats['new_w'].get(a, 0) + new_w
        stats['rep_w'][a] = stats['rep_w'].get(a, 0) + rep_w

    # exact lookups per span length
    cands = []
    for Lc, lst in by_L.items():
        t = np.array([x[0] for x in lst], dtype=np.uint64)
        bs = best_seeds(Lc, t)
        for k in np.nonzero(bs >= 0)[0]:
            vc, i, a, bar, m = lst[k]
            rl, rv = record_build(a, int(bs[k]))
            stats['cand'][a] = stats['cand'].get(a, 0) + 1
            if rl < bar:
                cands.append((bar - tol - rl, i, a, rl, rv, int(bs[k]), Lc, vc, m))
            elif supo and a == 1 and m == 0 and rl - (bar - tol) <= prune_D:
                e = es[i]                              # retain noncompressive candidate
                if e.alt is None or rl < e.alt[0]:
                    e.alt = (rl, rv, int(bs[k]), Lc, vc)
                    stats['retained'] += 1
            elif supo and a == 1 and m == 0:
                stats['pruned'] += 1

    # greedy largest-gain non-overlapping selection
    cands.sort(key=lambda c: -c[0])
    used = np.zeros(n, bool)
    out_repl = {}
    for sv, i, a, rl, rv, idx, Lc, vc, m in cands:
        if used[i:i + a].any(): continue
        used[i:i + a] = True
        out_repl[i] = (a, rl, rv, idx, Lc, vc, m)
        stats['acc'][a] = stats['acc'].get(a, 0) + 1
        stats['saved'] += sv
        if m:
            stats['conv'] += bin(m).count('1')
            stats['conv_saved'] += sv

    out = []
    i = 0
    while i < n:
        if i in out_repl:
            a, rl, rv, idx, Lc, vc, m = out_repl[i]
            ne = Entry(rl, rv, 'seed', (a, idx, Lc, vc, m, es[i:i + a]))
            out.append(ne); i += a
        else:
            out.append(es[i]); i += 1
    return out

# ---------- pass 1 (raw spans; wrap-once leftover) ----------
def pass1(blocks, B, A, max_w):
    N = len(blocks)
    cands = []
    for a in range(1, A + 1):
        L = a * B
        if L > max_w: break
        t = np.zeros(N - a + 1, dtype=np.uint64)
        for j in range(a):
            t = (t << np.uint64(B)) | blocks[j:N - a + 1 + j].astype(np.uint64)
        bs = best_seeds(L, t)
        for i in np.nonzero(bs >= 0)[0]:
            rl, rv = record_build(a, int(bs[i]))
            bar = a * (B + LIT[1])
            if rl < bar:
                cands.append((bar - rl, int(i), a, rl, rv, int(bs[i]), L, int(t[i])))
    cands.sort(key=lambda c: -c[0])
    used = np.zeros(N, bool); repl = {}
    for sv, i, a, rl, rv, idx, L, tv in cands:
        if used[i:i + a].any(): continue
        used[i:i + a] = True
        repl[i] = (a, rl, rv, idx, L, tv)
    es = []
    i = 0
    w1 = {a: 0 for a in range(1, A + 1)}
    while i < N:
        if i in repl:
            a, rl, rv, idx, L, tv = repl[i]
            es.append(Entry(rl, rv, 'seed', (a, idx, L, tv, 0, None)))
            w1[a] += 1; i += a
        else:
            es.append(Entry(B + LIT[1], (int(LIT[0], 2) << B) | int(blocks[i]), 'lit',
                            int(blocks[i])))
            i += 1
    return es, w1

# ---------- decode verification (recompute hashes; recurse to raw blocks) ----------
def verify(es, blocks, B):
    out = []
    def expand(e):
        if e.kind == 'lit':
            out.append(e.meta); return
        a, idx, L, tv, m, children = e.meta
        if expansion_bits(idx, L) != tv: raise AssertionError("expansion mismatch")
        if children is None:                      # pass-1 record: raw content
            for j in range(a - 1, -1, -1):
                out.append((tv >> (j * B)) & ((1 << B) - 1))
        else:                                     # recursive record: entry bits
            forms = [children[k].form(bool(m >> k & 1)) for k in range(a)]
            Lc, vc = concat(forms)
            if (Lc, vc) != (L, tv): raise AssertionError("children/target mismatch")
            for k, ch in enumerate(children):
                if m >> k & 1:                    # alt form: verify alt seed too
                    al, av, aidx, atL, atv = ch.alt
                    if expansion_bits(aidx, atL) != atv: raise AssertionError("alt mismatch")
                expand(ch)
    for e in es: expand(e)
    return out == [int(b) for b in blocks]

# ---------- driver ----------
def run(mode, B, N, kbits, passes, A, supo, prune_D, tol, rule, csvw, seed=42):
    global EXP
    rng = np.random.default_rng(seed)
    blocks = rng.integers(0, 1 << B, N, dtype=np.uint64)
    raw = N * B
    es, w1 = pass1(blocks, B, A, max_w=48)
    bits = sum(e.L for e in es)
    tried = set()
    print(f"\n--- mode {mode}: supo={supo}(D={prune_D}) shuffle={rule} tol={tol} "
          f"depth=2^{kbits} seeds, N={N}x{B}b, raw={raw}b ---")
    print(f"  pass  1: {bits:7d}b = {100*bits/raw:8.3f}% raw | entries={len(es):5d} | "
          f"p1 wins {dict((a,c) for a,c in w1.items() if c)}")
    csvw.writerow([mode, 1, raw, bits, f"{100*bits/raw:.3f}", len(es),
                   ';'.join(f"a{a}:{c}" for a, c in w1.items() if c), 0, 0, 0, '', ''])
    for t in range(2, passes + 1):
        if mode == 'A': break                      # one-pass only
        es = shuffle(es, rule, t)
        st = {'cand': {}, 'acc': {}, 'new_w': {}, 'rep_w': {}, 'saved': 0,
              'retained': 0, 'pruned': 0, 'conv': 0, 'conv_saved': 0}
        before = bits
        es = entry_pass(es, A, supo, prune_D, tol, max_w=48, tried=tried, stats=st)
        bits = sum(e.L for e in es)
        Ls = np.array([e.L for e in es])
        refresh = {a: (st['new_w'].get(a, 0),
                       st['new_w'].get(a, 0) + st['rep_w'].get(a, 0)) for a in range(2, A+1)}
        rstr = ' '.join(f"a{a}:{x}/{y}" for a, (x, y) in refresh.items() if y)
        print(f"  pass {t:2d}: {bits:7d}b = {100*bits/raw:8.3f}% raw | "
              f"acc={sum(st['acc'].values()):3d} {dict(st['acc'])} | saved={st['saved']:4d}b | "
              f"supo ret={st['retained']:4d} prn={st['pruned']:3d} conv={st['conv']:2d} | "
              f"len p50/p90/max={int(np.median(Ls))}/{int(np.percentile(Ls,90))}/{Ls.max()}")
        csvw.writerow([mode, t, before, bits, f"{100*bits/raw:.3f}", len(es),
                       ';'.join(f"a{a}:{c}" for a, c in st['acc'].items()),
                       st['retained'], st['pruned'], st['conv'], rstr,
                       f"{int(np.median(Ls))}/{int(np.percentile(Ls,90))}/{Ls.max()}"])
    ok = verify(es, blocks, B)
    print(f"  decode verification: {'PASS' if ok else 'FAIL'}   final {100*bits/raw:.3f}% of raw")
    return bits / raw, ok

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="B")
    ap.add_argument("--B", type=int, default=6)
    ap.add_argument("--N", type=int, default=3000)
    ap.add_argument("--kbits", type=int, default=19)
    ap.add_argument("--passes", type=int, default=10)
    ap.add_argument("--A", type=int, default=5)
    ap.add_argument("--prune", type=int, default=16)
    ap.add_argument("--tol", type=int, default=0)
    ap.add_argument("--csv", default="telomere_model_results.csv")
    args = ap.parse_args()

    EXP = load_expansions(args.kbits)
    new = not os.path.exists(args.csv)
    with open(args.csv, 'a', newline='') as f:
        cw = csv.writer(f)
        if new:
            cw.writerow(["mode", "pass", "bits_before", "bits_after", "pct_of_raw",
                         "entries", "accepted_by_arity", "retained_supo", "pruned_supo",
                         "converted_supo", "refresh_new/total", "len_p50/p90/max"])
        CFG = {  # mode -> (supo, rule, tol)
            'A': (0, 'none', 0), 'B': (0, 'none', 0), 'C': (1, 'none', 0),
            'D': (0, 'affine', 0), 'E': (1, 'affine', 0),
            'F1': (1, 'affine', 1), 'F4': (1, 'affine', 4),
        }
        t0 = time.time()
        for m in args.modes.split(','):
            supo, rule, tol = CFG[m]
            run(m, args.B, args.N, args.kbits, args.passes, args.A,
                supo, args.prune, tol if args.tol == 0 else args.tol, rule, cw)
        print(f"\n[{time.time()-t0:.1f}s] CSV -> {args.csv}")
