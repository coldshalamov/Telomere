#!/usr/bin/env python3
"""
B-ambiguity-bound_survivor_count.py

LANE B: is the count of self-consistent trial-decodings bounded as a function
of (N records, P passes)?  ANSWER (this toy): for SINGLES, no -- it is exactly
S = T^R, exponential in R, by construction.

WHY SINGLES ARE THE CRUX (the wall, THE_OPEN_QUESTION)
------------------------------------------------------
An arity-1 record is length-preserving (1 item -> 1 item) and ALWAYS expands to
a structurally valid literal at ANY position-salt. So:
  * the explosion check (the ~2.5-bit free structural filter the BRIEF cites)
    does NOT touch a single -- a wrong-salt open is just as structurally valid
    as the right one, it merely yields DIFFERENT BYTES (this is exactly the
    robins_exact_spec.py dispute: same seed 6523, wrong position 0 vs right
    position 4, both "decode successfully", different bytes);
  * the length constraint does NOT bite -- 1->1 preserves item count;
  * therefore the ONLY decode freedom is WHICH reverse walk the single is
    opened on, and every choice is self-consistent until the checksum.

A single placed on the wire is present at all T reverse walks. Opening it on
walk j salts with its position-at-walk-j -> a DISTINCT, structurally valid
reading. R independent singles -> S = T^R self-consistent readings.

This file PROVES that by construction (real SHA-256, the maintainer's exact
in-place / position-salt / +1-shuffle architecture, open/carry DFS counting all
structurally+length valid readings BEFORE the checksum), at T in {20,50,100}.

COUNTING GATE (closed, in the findings .md): to pick the true reading out of
T^R, a referee needs log2(T^R) = R*log2(T) bits. The header checksum IS that
referee. Fixed at 64 bits -> deterministic decode only while R*log2 T < 64.
To scale to N singles the checksum must grow to ~N*log2(T) bits = the birth
bill, log2(passes)/record. Currency: stored-bits (checksum width) == compute
(search T^R). No free unbounded channel.
"""
import hashlib, random, math

SEED_BITS = 14
LIT_BITS = 8
LIT_LEN = 1 + LIT_BITS          # '0' + 8b literal  = 9
A1_LEN = 1 + SEED_BITS          # '0'... wait: we need distinct prefixes.

# Alphabet chosen so SINGLES are the only record kind and literals/records are
# distinguishable on the wire by their FIRST BIT, matching robins_exact_spec's
# spirit but kept minimal:
#   literal block : '0' + 8 raw bits                       (9 bits)
#   arity-1 record: '1' + 14-bit seed                      (15 bits)
REC1_LEN = 1 + SEED_BITS        # 15


def H(key, n):
    out = ""; c = 0
    while len(out) < n:
        out += "".join(f"{b:08b}" for b in hashlib.sha256(f"{key}#{c}".encode()).digest())
        c += 1
    return out[:n]


def is_rec(b):
    return b[0] == '1'


def lit(bits):
    return '0' + bits


def rec1(s):
    return '1' + format(s, f'0{SEED_BITS}b')


# ---- exact +1 shuffle (maintainer's), bijective ----------------------------
def prime_geq(n):
    def isp(m):
        f = 2
        while f * f <= m:
            if m % f == 0:
                return False
            f += 1
        return m > 1
    while not isp(n):
        n += 1
    return n


def shuf(items, inv=False):
    M = len(items); P = prime_geq(max(M, 7)); out = [None] * M
    for i, it in enumerate(items):
        if not inv:
            j = (5 * i) % P
            while j >= M:
                j = (5 * j) % P
            out[(j + 1) % M] = it
        else:
            k = (i - 1) % M; v = pow(5, -1, P); j = (v * k) % P
            while j >= M:
                j = (v * j) % P
            out[j] = it
    return out


def open_single_at(b, pos):
    """Open an arity-1 record at position-salt `pos`. ALWAYS returns one literal
    item (8 raw bits) -- a single can never explode. Returns the literal wire."""
    s = int(b[1:], 2)
    dig = H(f"{s}|{pos}", LIT_BITS)       # expand to exactly one B-bit block
    return '0' + dig                       # always a valid literal


# ---- encoder: plant R singles, spread one per early pass so each rides -------
def encode(blocks, T, R):
    """Plant R arity-1 singles. Plant one on each of passes 1..R, at the lowest
    available literal slot, by OVERWRITING that slot's block to the seed's
    expansion (the standard plant trick: a genuine match the decoder accepts).
    Track ground-truth birth pass for the report."""
    items = [lit(b) for b in blocks]
    birth = {}                              # ground-truth: slot-id -> birth pass
    ids = list(range(len(items)))           # identity tags travel with items
    for t in range(1, T + 1):
        if t <= R:
            # plant one single at the first literal slot
            for i in range(len(items)):
                if not is_rec(items[i]):
                    s = (t * 131 + i) % (1 << SEED_BITS)
                    items[i] = rec1(s)
                    birth[ids[i]] = t
                    break
        # shuffle items and the identity tags together
        paired = list(zip(items, ids))
        paired = shuf(paired)
        items = [p[0] for p in paired]
        ids = [p[1] for p in paired]
    return items, birth


# ---- survivor-count DFS: branch open/carry on every record every walk -------
def count_survivors(items, T, node_budget=50_000_000):
    nodes = [0]; leaves = [0]; capped = [False]

    def step(cur_items, t):
        nodes[0] += 1
        if nodes[0] > node_budget:
            capped[0] = True
            return
        if t == 0:
            if all(not is_rec(b) for b in cur_items):
                leaves[0] += 1
            return
        cur = shuf(cur_items, inv=True)
        rec_pos = [p for p, b in enumerate(cur) if is_rec(b)]
        # branch over every subset of records to OPEN at this reverse walk
        for mask in range(1 << len(rec_pos)):
            if capped[0]:
                return
            out = list(cur)
            opened = [rec_pos[j] for j in range(len(rec_pos)) if mask & (1 << j)]
            for p in opened:
                out[p] = open_single_at(cur[p], p)   # always valid
            step(out, t - 1)

    step(items, T)
    return leaves[0], nodes[0], capped[0]


def main():
    print("=" * 72)
    print("LANE B -- survivor-count S(R,T) for SINGLES, exact architecture")
    print("  literal='0'+8b ; arity-1 record='1'+14b ; +1 shuffle ; pos salts")
    print("  open/carry DFS counts ALL structurally+length-valid readings")
    print("  BEFORE the checksum.  Prediction (by construction): S = T^R.")
    print("=" * 72)
    rng = random.Random(2026)
    all_rows = []
    for T in (20, 50, 100):
        print(f"\n--- T = {T} passes (well past the wall; BRIEF says >tens) ---")
        print(f"  {'R':>2} {'N':>3} {'S (survivors)':>14} {'T^R (predicted)':>18}"
              f" {'match':>6} {'nodes':>10}")
        for R in (1, 2, 3):
            N = 5 + R                       # enough slots, small for tractable DFS
            blocks = ["".join(rng.choice("01") for _ in range(LIT_BITS))
                      for _ in range(N)]
            items, birth = encode(list(blocks), T, R)
            n_recs = sum(1 for it in items if is_rec(it))
            S, nodes, capped = count_survivors(items, T)
            pred = T ** R if n_recs == R else None
            match = "" if pred is None else ("YES" if S == pred else "NO")
            preds = str(pred) if pred is not None else f"(recs={n_recs}!=R)"
            cap = " CAPPED" if capped else ""
            print(f"  {R:>2} {N:>3} {S:>14} {preds:>18} {match:>6} {nodes:>10}{cap}")
            all_rows.append((T, R, n_recs, S, pred, capped))

    print()
    print("=" * 72)
    print("COUNTING GATE")
    print("=" * 72)
    print("  To select the true reading from S=T^R, a referee needs")
    print("  log2 S = R*log2 T bits. The header checksum is that referee.")
    print(f"  {'T':>4} {'log2 T':>8} {'R for 64-bit collision':>24} "
          f"{'net/single=2-log2 T':>20}")
    for T in (4, 20, 50, 100):
        l2 = math.log2(T)
        Rcrit = 64 / l2
        net = 2 - l2
        print(f"  {T:>4} {l2:>8.3f} {Rcrit:>24.2f} {net:>20.3f}")
    print()
    print("  => net/single = 2 - log2 T <= 0 for T >= 4: free singles-grinding")
    print("     reach K ~= 4 passes (consistent with 'arity-1 is one-shot').")
    print("     Deterministic decode at fixed 64-bit checksum holds only while")
    print("     R*log2 T < 64; to scale to N singles the checksum must grow to")
    print("     ~N*log2 T bits == the birth bill (log2(passes)/record).")


if __name__ == "__main__":
    main()
