"""His exact decode procedure (expand every seed, leave literals, unshuffle,
repeat; unwrap at the end), across randomized multi-pass cases.
Control: oracle-staged decoder (expands only the right pass's seeds, using
encoder birth records) — must always succeed if the harness is sound."""

import hashlib, random
from robins_decoder import expand, sf, shuffle, LIT, A2, is_seed, decode_seed

def find_match(S, banned):
    for i in range(len(S) - 1):
        if S[i].startswith(LIT) and S[i+1].startswith(LIT) and len(S[i]) == 6 == len(S[i+1]):
            t = S[i] + S[i+1]
            if t in banned:
                continue
            for sd in range(2, 65536):
                if expand(sd, 12) == t:
                    return i, sd
    return None, None

def trial(seed_rng, n_blocks, passes):
    rng = random.Random(seed_rng)
    # plant: derive blocks from real expansions so matches exist
    plant = []
    s = 2
    while len(plant) < n_blocks // 2:
        e = expand(s, 12)
        if e[0:2] == "00" and e[6:8] == "00":
            plant.append((e[2:6], e[8:12]))
        s += 1
    raw = [b for pair in plant for b in pair][:n_blocks]
    rng.shuffle(raw)
    S = [LIT + r for r in raw]
    states = [list(S)]
    births = []  # (pass, seed) for control decoder
    for t in range(1, passes + 1):
        i, sd = find_match(S, set())
        if sd is not None:
            S = S[:i] + [A2 + sf(sd)] + S[i+2:]
            births.append(sd)
        else:
            births.append(None)
        S = shuffle(S)
        states.append(list(S))
    wire = list(S)

    # --- his procedure: expand ALL seeds each step ---
    D = list(wire)
    for step in range(passes, 0, -1):
        D = shuffle(D, inverse=True)
        out = []
        for it in D:
            out.extend(decode_seed(it) if is_seed(it) else [it])
        D = out
    his = [it[2:] for it in D if it.startswith(LIT) and len(it) == 6]
    his_ok = (his == raw) and len(D) == len(raw)

    # --- control: staged decoder with oracle birth info ---
    D = list(wire)
    for step in range(passes, 0, -1):
        D = shuffle(D, inverse=True)
        sd_born = births[step - 1]
        out = []
        for it in D:
            if is_seed(it) and int(it[3:17], 2) == sd_born:
                out.extend(decode_seed(it))
            else:
                out.append(it)
        D = out
    ctl = [it[2:] for it in D if it.startswith(LIT) and len(it) == 6]
    ctl_ok = (ctl == raw) and len(D) == len(raw)
    n_seeds = sum(1 for b in births if b is not None)
    return his_ok, ctl_ok, n_seeds

results = {}
for n_blocks in (6, 8, 10):
    for passes in (2, 3, 4):
        his_wins = ctl_wins = total = 0
        multi = 0
        for r in range(12):
            h, c, ns = trial(1000 * n_blocks + 10 * passes + r, n_blocks, passes)
            total += 1
            his_wins += h
            ctl_wins += c
            if ns >= 2:
                multi += 1
        results[(n_blocks, passes)] = (his_wins, ctl_wins, total, multi)
        print(f"N={n_blocks} passes={passes}: HIS procedure {his_wins}/{total} correct | "
              f"oracle-staged control {ctl_wins}/{total} | trials with >=2 seeds: {multi}")
