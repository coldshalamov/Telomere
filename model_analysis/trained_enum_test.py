import numpy as np, glob, os
# EXPERIMENT 2: trained seed-enumeration (mother seed table / footpaths) at block=2 bytes.
# Table = 16-bit blocks ranked by frequency in TRAINING files (decoder-public preset,
# trained without the held-out file). Seed index i -> i-th most frequent training block.
# Record cost (Robin's format): arity '00' (2b) + J3D1(i) = 2+3+w4+p. Literal = 16+3 = 19b.
SRC = sorted(glob.glob('/sessions/quirky-relaxed-cray/mnt/Telomere/src/*.rs'))
held = '/sessions/quirky-relaxed-cray/mnt/Telomere/src/streaming.rs'
train_files = [f for f in SRC if f != held]
def blocks(path_or_bytes):
    b = open(path_or_bytes,'rb').read() if isinstance(path_or_bytes,str) else path_or_bytes
    b = b[:len(b)//2*2]
    return np.frombuffer(b, dtype='>u2')
train = np.concatenate([blocks(f) for f in train_files])
vals, counts = np.unique(train, return_counts=True)
order = np.argsort(-counts)
rank = {int(vals[i]): r for r, i in enumerate(order)}        # block value -> seed index
def j3d1_cost(i):
    p = max(1, int(i).bit_length()); w4 = max(1, p.bit_length())
    return 2 + 3 + w4 + p                                     # arity '00' + jumpstarter + len + payload
def run(name, blks):
    LIT = 16 + 3
    total = 0; wins = 0; saved = 0
    for b in blks:
        r = rank.get(int(b))
        c = j3d1_cost(r) if r is not None else 999
        if c < LIT: total += c; wins += 1; saved += LIT - c
        else: total += LIT
    raw = 16 * len(blks)
    print(f"{name:22s}: {len(blks):6d} blocks | win rate {100*wins/len(blks):6.2f}% | "
          f"net {100*total/raw:7.2f}% of raw {'<- NET COMPRESSION' if total<raw else ''}")
    return wins/len(blks)
print(f"table trained on {len(train_files)} real source files ({len(train)} blocks); held-out file untouched by training\n")
wr_real = run("REAL held-out file", blocks(held))
rng = np.random.default_rng(7)
wr_rand = run("RANDOM data (control)", rng.integers(0,1<<16,12000,dtype=np.uint16).astype('>u2'))
# raw-search baseline win rate at bs=2 for reference (uniform hash, same cost ledger):
# a win needs a seed index < ~2^11 matching a 16-bit target: P ~ 2^11/2^16
print(f"\nraw uniform-search baseline win rate ~ {100*(2**11)/(2**16):.2f}%  (any file, structured or random)")
print(f"density multiplier delivered by training: {wr_real/max(wr_rand,1e-9):,.0f}x over random-through-table; "
      f"{wr_real/((2**11)/(2**16)):.0f}x over raw search")
