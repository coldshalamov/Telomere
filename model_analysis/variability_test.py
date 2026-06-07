import hashlib, numpy as np
# Tests Robin's claim: "larger bundle => larger gap between smallest matching seed
# and the target" (bigger bundles give bigger compressions). NO AVERAGING of the
# answer -- we keep every win and show the whole distribution + the single biggest.
# FAIR: equal relative search depth (C x the target space) at each bundle size.
BLOCK = 6; C = 4
print("Searching every seed at equal depth per bundle size. Full distribution, raw.\n")
hdr = {}
for a in (1,2,3):
    s = a*BLOCK; K = C*(1<<s)
    cost = np.maximum(1, np.frombuffer(bytes(min(63, i.bit_length()) for i in range(K)), dtype=np.uint8).astype(np.int16))
    pref = np.empty(K, dtype=np.int64)
    for i in range(K):
        pref[i] = int.from_bytes(hashlib.blake2b(i.to_bytes(6,'little'), digest_size=4).digest(),'big') & ((1<<s)-1)
    minc = np.full(1<<s, 99, dtype=np.int16)
    np.minimum.at(minc, pref, cost)
    hit = minc < 99
    h = np.clip(s - minc[hit], 0, None).astype(np.int64)
    hdr[a] = h
    print(f"arity {a}: span {s:2d} bits, {hit.sum():6d} distinct targets searched | "
          f"BIGGEST single headroom found = {int(h.max()):2d} bits | targets with headroom>=6: {(h>=6).sum()}")

print("\nP(headroom >= d) -- your claim predicts the arity-3 column should TOWER over arity-1:")
print(f"{'d (bits saved)':>14} | {'arity1':>8} {'arity2':>8} {'arity3':>8}")
print("-"*46)
for d in range(0,12):
    print(f"{d:>14} | " + " ".join(f"{(hdr[a]>=d).mean():8.4f}" for a in (1,2,3)))
print("\nBiggest headroom seen at each bundle size:",
      {a:int(hdr[a].max()) for a in (1,2,3)})
