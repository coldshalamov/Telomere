"""Run the maintainer's decode-by-exact-reversal on a real tiny file.

Encode: wrap 4 blocks -> pass A: shuffle, replace one arity-2 match ->
pass B: shuffle, replace one arity-2 match -> emit. Real SHA-256 matches
(raw blocks planted so matches exist; the matches themselves are genuine
hash prefix equalities). Fixed shuffle rule from the spec family
(multiply mod prime, cycle-walk). No salts (content-keyed dice).

Decode: take every action in reverse: un-replace, un-shuffle, repeat.
The script tries EVERY way of executing that reversal and reports which
succeed structurally (all parses valid) and what raw they produce.
"""

import hashlib

B = 4  # 4-bit blocks for compactness
LIT = "00"      # literal: [00][4 raw bits] -> 6 bits
A2 = "100"      # arity-2 record: [100][lotus-ish seed field]


def expand(seed: int, nbits: int) -> str:
    d = hashlib.sha256(seed.to_bytes(4, "big")).digest()
    return "".join(f"{b:08b}" for b in d)[:nbits]


def seed_field(seed: int) -> str:
    # fixed 14-bit seed field for the demo (structure demo; costs not at issue)
    return format(seed, "014b")


def shuffle(items, inverse=False):
    n = len(items)
    p = n
    while any(p % k == 0 for k in range(2, p)):  # next prime >= n
        p += 1
    a = 2
    def fwd(i):
        j = (a * i) % p
        while j >= n:
            j = (a * j) % p
        return j
    perm = [fwd(i) for i in range(n)]
    out = [None] * n
    if not inverse:
        for i, it in enumerate(items):
            out[perm[i]] = it
    else:
        for i, it in enumerate(items):
            out[perm.index(i)] = it
    return out


# ---- plant raw blocks so two real arity-2 matches exist -----------------
def find_seed_with_shape():
    """Find seeds whose 12-bit expansion looks like [00 xxxx 00 yyyy]."""
    found = []
    for s in range(2, 32):
        e = expand(s, 12)
        if e[0:2] == "00" and e[6:8] == "00":
            found.append((s, e[2:6], e[8:12]))
    return found

cands = find_seed_with_shape()
assert len(cands) >= 2, cands
(s1, r4, r2), (s2, r3, r1) = cands[0], cands[1]

raw = [r1, r2, r3, r4]
print(f"raw blocks: {raw}")
print(f"planted: seed {s1} expands to L4||L2 wire bits; seed {s2} to L3||L1\n")

# ---- ENCODE, action by action -------------------------------------------
S = [LIT + r for r in raw]                       # S0: wrap
print("S0 (wrapped):", S)

S = shuffle(S)                                    # pass A: shuffle
print("pass A shuffle:", S)
# search: find the planted pair if adjacent; else report
def try_replace(S, seed):
    target = expand(seed, 12)
    for i in range(len(S) - 1):
        if S[i] + S[i+1] == target:
            return S[:i] + [A2 + seed_field(seed)] + S[i+2:], i
    return S, None

for sd in (s1, s2):
    S2, pos = try_replace(S, sd)
    if pos is not None:
        S = S2
        print(f"pass A replace: seed {sd} covers positions {pos},{pos+1} ->", S)
        first_seed = sd
        break
else:
    raise SystemExit("planted pair not adjacent after shuffle A — rerun with different perm")

S = shuffle(S)                                    # pass B: shuffle
print("pass B shuffle:", S)
# search ALL seeds for a REAL match on any adjacent literal pair
second_seed = None
for i in range(len(S) - 1):
    if S[i].startswith(LIT) and S[i+1].startswith(LIT):
        target = S[i] + S[i+1]
        for sd in range(2, 16384):
            if expand(sd, 12) == target:
                S = S[:i] + [A2 + seed_field(sd)] + S[i+2:]
                print(f"pass B replace: seed {sd} covers positions {i},{i+1} ->", S)
                second_seed = sd
                break
        if second_seed is not None:
            break
if second_seed is None:
    raise SystemExit("no real second match found in 16k seeds — widen search")

wire = S
print("\nEMITTED WIRE:", wire, "\n")

# ---- DECODE: take every action in reverse --------------------------------
def parse_ok(bits):
    return bits.startswith(LIT) and len(bits) == 6 or bits.startswith(A2)

def is_record(item):
    return item.startswith(A2)

def expand_record(item):
    seed = int(item[3:17], 2)
    e = expand(seed, 12)
    return [e[0:6], e[6:12]], seed

def reverse_decode(wire, choice_order):
    """Reverse: un-replace (expand ONE record per pass-reversal), un-shuffle.
    choice_order says which record to treat as 'the most recent' at each
    reverse step when more than one is present."""
    S = list(wire)
    log = []
    for step, pick in enumerate(choice_order):
        recs = [i for i, it in enumerate(S) if is_record(it)]
        if not recs:
            break
        idx = recs[pick] if pick < len(recs) else recs[-1]
        children, seed = expand_record(S[idx])
        if not all(parse_ok(c) for c in children):
            return None, log + [f"step {step}: expansion of seed {seed} does not parse — REJECT"]
        S = S[:idx] + children + S[idx+1:]
        log.append(f"step {step}: expanded seed {seed} at item {idx} -> {S}")
        S = shuffle(S, inverse=True)
        log.append(f"step {step}: un-shuffled -> {S}")
    return S, log

print("=" * 70)
print("REVERSAL, choice 1: expand the records in one order")
out1, log1 = reverse_decode(wire, [0, 0])
for l in log1: print(" ", l)
print("=" * 70)
print("REVERSAL, choice 2: expand the records in the other order")
out2, log2 = reverse_decode(wire, [1, 0])
for l in log2: print(" ", l)
print("=" * 70)

def to_raw(S):
    if S is None: return None
    if not all(it.startswith(LIT) and len(it) == 6 for it in S): return None
    return [it[2:] for it in S]

print(f"\ntrue raw:              {raw}")
print(f"reversal choice 1 ->   {to_raw(out1)}")
print(f"reversal choice 2 ->   {to_raw(out2)}")
print(f"\nchoice 1 parses fully: {to_raw(out1) is not None}")
print(f"choice 2 parses fully: {to_raw(out2) is not None}")
print(f"choice 1 correct: {to_raw(out1) == raw}")
print(f"choice 2 correct: {to_raw(out2) == raw}")
