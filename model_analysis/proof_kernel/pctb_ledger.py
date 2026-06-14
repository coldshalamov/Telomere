#!/usr/bin/env python3
"""
PCTB (Position-Coded Telomere Board) — independent test, on its own terms.

This is NOT analysed by analogy to any existing Table-of-Record row. It is the
construction from the proposal, implemented directly:

  - board state S_t : occupied board-position -> egg (lit | seed)
  - instructions over board size Q_t:  C(p)=carry from p ; M_k(p)=open arity-k at p
  - injective instruction codes:  code(C(p))=p ; code(M_k(p))=Q_t+sum_{j<k}(Q_t-j+1)+p
  - reversible per-pass shuffle: visible_position = PRP_t(code)  (real Feistel + cycle-walk)
  - salt: SHA256(domain || t || code || k || span_len || seed)   (fresh per pass & slot)
  - the file stores ONLY: pass_count, Q_0, and the FINAL occupied positions + payloads.

Two independent questions, answered separately and labelled:

  (A) MECHANICS  — does PCTB round-trip? (real PRP, real SHA-256, real match-opens)
  (B) LEDGER     — what does the final-position list actually cost, and is the
                   "raw + epsilon" worst-case bound preserved? (exact occupancy
                   entropy log2 C(Q_P, N_P) via lgamma, no shortcuts)

Run:  python pctb_ledger.py
"""

import hashlib
from math import lgamma, log2, ceil

DOMAIN = b"TELOMERE-PCTB-v1"

# ----------------------------------------------------------------------------
# real hashing
# ----------------------------------------------------------------------------
def _h(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        if isinstance(p, int):
            p = p.to_bytes((p.bit_length() + 7) // 8 or 1, "big")
        elif isinstance(p, str):
            p = p.encode()
        h.update(len(p).to_bytes(4, "big"))
        h.update(p)
    return h.digest()

def expand_bits(seed: int, code: int, t: int, k: int, span_len: int) -> str:
    """PCTB salted expansion: first span_len bits of SHA stream keyed by
    (domain, pass t, instruction code, arity k, seed)."""
    out = []
    c = 0
    while sum(len(x) for x in out) < span_len:
        d = _h(DOMAIN, t, code, k, span_len, seed, c)
        out.append("".join(f"{b:08b}" for b in d))
        c += 1
    return "".join(out)[:span_len]

# ----------------------------------------------------------------------------
# reversible PRP over [0, Q):  4-round Feistel on a power-of-two pad, cycle-walked
# ----------------------------------------------------------------------------
def _feistel(x: int, hb: int, key, rounds=4) -> int:
    mask = (1 << hb) - 1
    L = (x >> hb) & mask
    R = x & mask
    for r in range(rounds):
        f = int.from_bytes(_h(b"F", key, r, R), "big") & mask
        L, R = R, (L ^ f)
    return (L << hb) | R

def _feistel_inv(y: int, hb: int, key, rounds=4) -> int:
    mask = (1 << hb) - 1
    L = (y >> hb) & mask
    R = y & mask
    for r in reversed(range(rounds)):
        f = int.from_bytes(_h(b"F", key, r, L), "big") & mask
        R, L = L, (R ^ f)
    return (L << hb) | R

def _half_bits(Q: int) -> int:
    n = max(2, (Q - 1).bit_length())
    if n % 2:
        n += 1
    return n // 2

def prp(code: int, Q: int, t: int) -> int:
    """bijection [0,Q) -> [0,Q), keyed by pass t. cycle-walk over the pad."""
    hb = _half_bits(Q)
    key = f"PRP{t}"
    y = code
    for _ in range(64):  # cycle-walk; terminates fast (pad < 2*Q)
        y = _feistel(y, hb, key)
        if y < Q:
            return y
    raise RuntimeError("cycle-walk failed")

def prp_inv(vis: int, Q: int, t: int) -> int:
    hb = _half_bits(Q)
    key = f"PRP{t}"
    y = vis
    for _ in range(64):
        y = _feistel_inv(y, hb, key)
        if y < Q:
            return y
    raise RuntimeError("cycle-walk inverse failed")

# ----------------------------------------------------------------------------
# instruction coding (carry + arity 1..MAXK), board-size growth
# ----------------------------------------------------------------------------
def lane_offsets(Q: int, maxk: int):
    """returns (carry_lane_size, [(k, start, count)...]) and next board size."""
    off = Q                       # carry lane occupies [0, Q)
    lanes = []
    for k in range(1, maxk + 1):
        count = Q - k + 1         # anchors 0..Q-k
        lanes.append((k, off, count))
        off += count
    return lanes, off             # off == Q_{t+1}

def code_carry(p, Q, maxk):  # p in [0,Q)
    return p

def code_match(p, k, Q, maxk):
    lanes, _ = lane_offsets(Q, maxk)
    for (kk, start, count) in lanes:
        if kk == k:
            assert 0 <= p <= Q - k
            return start + p
    raise ValueError

def parse_code(code, Q, maxk):
    """visible-position-inverse -> ('carry',p) or ('match',k,p)."""
    if code < Q:
        return ("carry", code, None)
    lanes, total = lane_offsets(Q, maxk)
    for (k, start, count) in lanes:
        if start <= code < start + count:
            return ("match", k, code - start)
    raise ValueError(f"code {code} out of range for Q={Q}")

# ----------------------------------------------------------------------------
# encoder / decoder.  egg = ('lit', bits) | ('seed', seed, k)
# ----------------------------------------------------------------------------
def encode(blocks, passes, maxk=2, seed_budget=1 << 16, planted=None):
    """Returns (final_board {vis:egg}, Q_schedule). Greedy carry/match tiling.

    `planted`: optional dict {pass_t: {anchor_p: (seed,k)}} to force specific
    matches so the round-trip exercises real match-opens deterministically
    (brute search at honest settings finds ~nothing, which is the point of B)."""
    B = len(blocks[0])
    # S_0: dense board, position == index, all literals
    S = {i: ("lit", blocks[i]) for i in range(len(blocks))}
    Q = len(blocks)
    Qsched = [Q]
    for t in range(1, passes + 1):
        lanes, Qn = lane_offsets(Q, maxk)
        occ = sorted(S.keys())
        occ_set = set(occ)
        used = set()
        nextS = {}
        plant_t = (planted or {}).get(t, {})
        i = 0
        # tile in board order; greedy largest arity first among contiguous occupied
        for p in occ:
            if p in used:
                continue
            placed = False
            # try planted match at this anchor
            if p in plant_t:
                seed, k = plant_t[p]
                span = [p + j for j in range(k)]
                if all((q in occ_set and q not in used) for q in span) and p <= Q - k:
                    # verify the seed really regenerates the raw span (real SHA)
                    tgt = "".join(S[q][1] for q in span)
                    assert all(S[q][0] == "lit" for q in span), "toy plants on literals"
                    code = code_match(p, k, Q, maxk)
                    if expand_bits(seed, code, t, k, len(tgt)) == tgt:
                        vis = prp(code, Qn, t)
                        nextS[vis] = ("seed", seed, k)
                        for q in span:
                            used.add(q)
                        placed = True
            if not placed:
                # carry
                code = code_carry(p, Q, maxk)
                vis = prp(code, Qn, t)
                nextS[vis] = S[p]
                used.add(p)
        S = nextS
        Q = Qn
        Qsched.append(Q)
    return S, Qsched

def decode(final_board, Qsched, passes, B, maxk=2):
    """Reverse the passes. Returns reconstructed dense block list."""
    S = dict(final_board)
    for t in range(passes, 0, -1):
        Q_prev = Qsched[t - 1]      # board size BEFORE pass t
        Qn = Qsched[t]              # board size AFTER pass t (== current S domain)
        nextS = {}
        for vis, egg in S.items():
            code = prp_inv(vis, Qn, t)
            kind = parse_code(code, Q_prev, maxk)
            if kind[0] == "carry":
                p = kind[1]
                nextS[p] = egg
            else:
                _, k, p = kind
                assert egg[0] == "seed" and egg[2] == k
                seed = egg[1]
                bits = expand_bits(seed, code, t, k, k * B)
                for j in range(k):
                    nextS[p + j] = ("lit", bits[j * B:(j + 1) * B])
        S = nextS
    # S now over board Q_0; positions are 0..M-1 dense
    M = Qsched[0]
    out = []
    for i in range(M):
        assert i in S and S[i][0] == "lit", f"slot {i} not a literal after full reversal"
        out.append(S[i][1])
    return out

# ----------------------------------------------------------------------------
# exact occupancy cost
# ----------------------------------------------------------------------------
def log2_choose(n: int, k: int) -> float:
    """Exact log2 C(n,k), cancellation-free and overflow-safe for huge n.
    log2 C(n,k) = sum_{i=0}^{k-1} [log2(n-i) - log2(i+1)].
    math.log2 accepts arbitrary-precision ints, so n far beyond float range is fine."""
    n = int(n)
    k = int(k)
    k = min(k, n - k)
    if k <= 0:
        return 0.0
    s = 0.0
    for i in range(k):
        s += log2(n - i) - log2(i + 1)
    return s

# ----------------------------------------------------------------------------
# (A) MECHANICS: round-trip with real opens
# ----------------------------------------------------------------------------
def mechanics_demo():
    import random
    rng = random.Random(12345)
    B = 8
    M = 24
    blocks = [f"{rng.getrandbits(B):0{B}b}" for _ in range(M)]
    maxk = 2

    # Plant two arity-2 matches in pass 1 (anchors 0 and 4): choose a seed,
    # compute its real PCTB expansion for that (pass,code,arity), and SET the
    # target blocks to it -- a genuine match the encoder will accept & open.
    Q0 = M
    planted = {1: {}}
    for anchor, seed in [(0, 7), (4, 13)]:
        code = code_match(anchor, 2, Q0, maxk)
        span_bits = expand_bits(seed, code, 1, 2, 2 * B)
        blocks[anchor] = span_bits[:B]
        blocks[anchor + 1] = span_bits[B:2 * B]
        planted[1][anchor] = (seed, 2)

    original = list(blocks)
    passes = 3
    final, Qsched = encode(blocks, passes, maxk=maxk, planted=planted)
    recon = decode(final, Qsched, passes, B, maxk=maxk)
    ok = (recon == original)
    n_seed = sum(1 for e in final.values() if e[0] == "seed")
    print("== (A) MECHANICS ==")
    print(f"  M={M} blocks, B={B}, passes={passes}, maxk={maxk}")
    print(f"  Q schedule: {Qsched}")
    print(f"  final eggs: {len(final)}  (seed-eggs opened on reverse: {n_seed})")
    print(f"  ROUND-TRIP EXACT: {ok}")
    assert ok, "PCTB failed to round-trip"
    print("  -> the board mechanics + salted opens are reversible. (report's claim: confirmed)\n")

# ----------------------------------------------------------------------------
# (B) LEDGER: honest stored-bit accounting + the bounded-loss test
# ----------------------------------------------------------------------------
def stored_bits(Q_P, N_P, payload_bits, header_bits=64):
    pos = log2_choose(Q_P, N_P)          # exact bits to name which cells occupied
    return header_bits + pos + payload_bits, pos

def ledger_incompressible(M=1000, B=8, maxk=5):
    """The case that defines Telomere's safety: incompressible data, no matches
    ever (every egg carries). PCTB must still keep raw+epsilon. Does it?"""
    raw = M * B
    print("== (B1) BOUNDED-LOSS on incompressible data (carry-only, maxk=%d) ==" % maxk)
    print(f"  raw = {raw} bits ;  V1 guarantee = raw + 3 + header (bounded, pass-count free)")
    print(f"  {'P':>3} {'Q_P':>16} {'pos bits':>12} {'payload':>9} {'total':>9} {'total/raw':>10}")
    prev = None
    for P in [0, 1, 2, 3, 5, 8, 12, 16, 32, 64]:
        Q = M
        for _ in range(P):
            _, Q = lane_offsets(Q, maxk)
        N = M  # no matches -> all M originals survive as carries
        total, pos = stored_bits(Q, N, M * B)
        flag = ""
        if prev is not None and total < prev:
            flag = "  (decreasing?!)"
        prev = total
        print(f"  {P:>3} {Q:>16} {pos:>12.0f} {M*B:>9} {total:>9.0f} {total/raw:>10.3f}{flag}")
    print("  per-pass position tax per surviving egg = log2(branching) = "
          f"log2({1+maxk}) = {log2(1+maxk):.3f} bits/egg/pass\n")

def ledger_breakeven(M=4096, B=8, maxk=5, win_bits=2.0):
    """The dense lane: each pass collapses the survivor count by factor (1-rho)
    via arity-2 matches (rho = fraction of eggs consumed per pass). A match
    saves ~win_bits. What survivor-collapse rate makes PCTB net-compress, and
    how does its position bill compare to a flat per-pass match-map (tags)?"""
    raw = M * B
    print("== (B2) BREAK-EVEN in the dense lane (maxk=%d, win=%.1f bits/match) ==" % (maxk, win_bits))
    print("  model: rho = per-pass fraction of eggs consumed into arity-2 matches")
    print(f"  {'rho':>6} {'P':>3} {'N_P':>7} {'pos bits':>10} {'tag bits':>9} {'wins':>9} {'net vs raw':>11}")
    for rho in [0.02, 0.05, 0.10, 0.19, 0.30, 0.50]:
        for P in [16, 64]:
            N = M
            tag = 0.0          # flat diary: 1 bit/pass per *current* egg (carry/match)
            matches = 0
            Ncurve = []
            for _ in range(P):
                tag += N * log2(1 + maxk)   # bits to say carry-or-which-arity, per egg, this pass
                consumed = N * rho
                # arity-2 match: 2 eggs -> 1, so #matches this pass = consumed/2, eggs drop by consumed/2
                m = consumed / 2.0
                matches += m
                N = max(1.0, N - m)
                Ncurve.append(N)
            Q = M
            for _ in range(P):
                _, Q = lane_offsets(Q, maxk)
            pos = log2_choose(int(Q), max(1, int(round(N))))
            payload = N * B            # surviving eggs still carry ~B bits each (toy)
            wins = matches * win_bits
            total = 64 + pos + payload
            net = raw - total
            print(f"  {rho:>6.2f} {P:>3} {int(N):>7} {pos:>10.0f} {tag:>9.0f} {wins:>9.0f} {net:>11.0f}")
    print("  pos = PCTB final-position list (exact log2 C(Q_P,N_P));"
          " tag = flat per-pass diary (Sum_t N_t*log2 branching)")
    print("  net>0 would mean PCTB compresses; net<0 means it bloats.\n")

if __name__ == "__main__":
    mechanics_demo()
    ledger_incompressible(maxk=5)
    ledger_breakeven(maxk=5)
