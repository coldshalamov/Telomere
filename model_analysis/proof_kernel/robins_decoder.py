"""The maintainer's decoder, implemented exactly as specified:

  "it'd have to know 'this is a seed, decode it' and 'this is a literal,
   leave it' ... then unshuffle ... at every step, the state of the string
   of blocks is identical to what it was at a step of the inverse process"

Encode loop (his): search, replace, shuffle ... emit.
Decode loop (his): per reverse step: every seed -> decode it (one level,
seeds expand to the blocks they covered); every literal -> leave it; then
unshuffle. Literal unwrapping only at the very end, per header length.

Acceptance check (his criterion): after each decode step, the state must
EQUAL the encoder's state at the mirrored moment. We record every encoder
state and diff directly.
"""

import hashlib

LIT = "00"
A2 = "100"

def expand(seed, nbits):
    d = hashlib.sha256(seed.to_bytes(4, "big")).digest()
    return "".join(f"{b:08b}" for b in d)[:nbits]

def sf(seed):  # 14-bit demo seed field
    return format(seed, "014b")

def shuffle(items, inverse=False):
    n = len(items)
    if n < 2:
        return list(items)
    p = max(n, 3)
    while p == 2 or any(p % k == 0 for k in range(2, p)):
        p += 1
    def fwd(i):
        j = (2 * i) % p
        while j >= n:
            j = (2 * j) % p
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

def find_match(S):
    """Real seed search: any adjacent literal pair, seeds < 2^15."""
    for i in range(len(S) - 1):
        if S[i].startswith(LIT) and S[i+1].startswith(LIT) and len(S[i]) == 6 and len(S[i+1]) == 6:
            t = S[i] + S[i+1]
            for sd in range(2, 32768):
                if expand(sd, 12) == t:
                    return i, sd
    return None, None

def is_seed(it):
    return it.startswith(A2)

def decode_seed(it):
    sd = int(it[3:17], 2)
    e = expand(sd, 12)
    return [e[0:6], e[6:12]]

def run(passes):
    print(f"\n{'='*72}\n  {passes}-PASS ROUND TRIP, decoder exactly as specified\n{'='*72}")
    # choose raw blocks so matches exist (planted shapes, real SHA equalities)
    cands = []
    for s in range(2, 32768):
        e = expand(s, 12)
        if e[0:2] == "00" and e[6:8] == "00":
            cands.append(s)
        if len(cands) >= 4:
            break
    e0 = expand(cands[0], 12)
    raw = [e0[2:6], e0[8:12], expand(cands[1], 12)[2:6], expand(cands[1], 12)[8:12]]
    S = [LIT + r for r in raw]
    encoder_states = [list(S)]           # state BEFORE each pass's shuffle
    print(f"raw blocks: {raw}")
    print(f"S0: {S}")
    for t in range(1, passes + 1):
        i, sd = find_match(S)
        if sd is not None:
            S = S[:i] + [A2 + sf(sd)] + S[i+2:]
            print(f"pass {t} replace: seed {sd} at {i} -> {S}")
        else:
            print(f"pass {t}: no match found")
        S = shuffle(S)
        print(f"pass {t} shuffle -> {S}")
        encoder_states.append(list(S))
    wire = list(S)
    print(f"WIRE: {wire}")

    # ---- THE DECODER, as specified ----
    D = list(wire)
    ok = True
    for step in range(passes, 0, -1):
        D = shuffle(D, inverse=True)          # reverse of the last action (shuffle)
        out = []
        for it in D:                          # "seed -> decode it; literal -> leave it"
            out.extend(decode_seed(it) if is_seed(it) else [it])
        D = out
        mirror = encoder_states[step - 1]     # encoder state before pass `step`
        match = (D == mirror)
        ok = ok and match
        print(f"decode step (reversing pass {step}): unshuffle+decode-seeds -> {D}")
        print(f"  encoder state at mirrored moment:                    {mirror}")
        print(f"  IDENTICAL: {match}")
    final_raw = [it[2:] for it in D if it.startswith(LIT) and len(it) == 6]
    print(f"final unwrap -> {final_raw}   correct: {final_raw == raw}")
    return ok and final_raw == raw

one = run(1)
two = run(2)
print(f"\n{'='*72}\n1-pass round trip: {'SUCCESS' if one else 'FAIL'}")
print(f"2-pass round trip: {'SUCCESS' if two else 'FAIL'}")
