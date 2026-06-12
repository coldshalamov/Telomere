#!/usr/bin/env python3
"""Maintainer's architecture, three opening rules raced.
Encode pass: search -> replace IN PLACE -> shuffle(+1 shift).
Decode: mirror (unshuffle, then open). Rules:
  A: open every record after each unshuffle
  B: carry all records to the end, open them there
  C: maintainer's rule -- try openings, keep what decodes (checksum referee)
Real SHA-256, position salts (current position at match time), relaxed
acceptance (decode proof). Items: '0'+8b literal | '10'+seed a1 | '11'+seed a2.
"""
import hashlib, random, sys
SEED_BITS = 14
def H(key, n):
    out=""; c=0
    while len(out)<n:
        out+="".join(f"{b:08b}" for b in hashlib.sha256(f"{key}#{c}".encode()).digest()); c+=1
    return out[:n]
def prime_geq(n):
    def isp(m):
        f=2
        while f*f<=m:
            if m%f==0: return False
            f+=1
        return m>1
    while not isp(n): n+=1
    return n
def perm(i,M,P,inv=False):
    if not inv:
        j=(5*i)%P
        while j>=M: j=(5*j)%P
        return (j+1)%M
    i=(i-1)%M; v=pow(5,-1,P)
    j=(v*i)%P
    while j>=M: j=(v*j)%P
    return j
def shuffle(items,inv=False):
    M=len(items); P=prime_geq(max(M,7)); out=[None]*M
    for i,x in enumerate(items):
        out[perm(i,M,P) if not inv else perm(i,M,P,True)]=x
    return out
def wire(it): return it[0] if it[0][0]=='0' else it[0]
def lit(bits): return ("0"+bits,)
def rec(a,seed): return (("10" if a==1 else "11")+format(seed,f"0{SEED_BITS}b"),)
def encode(blocks,T,budget=4000,rng=None):
    items=[lit(b) for b in blocks]
    for t in range(1,T+1):
        # arity 2 first
        i=0; n_acc=0
        while i+1 < len(items) and n_acc<2:
            tgt=wire(items[i])+wire(items[i+1])
            hit=next((s for s in range(budget) if H(f"{s}|{i}",len(tgt))==tgt),None)
            if hit is not None:
                items[i:i+2]=[rec(2,hit)]; n_acc+=1; i+=1
            else: i+=1
        # one single per pass
        for i in range(len(items)):
            tgt=wire(items[i])
            hit=next((s for s in range(budget) if H(f"{s}|{i}",len(tgt))==tgt),None)
            if hit is not None:
                items[i]=rec(1,hit); break
        items=shuffle(items)
    return items
def parse(bits):
    items=[];c=0
    while c<len(bits):
        if bits[c]=='0':
            items.append(("0"+bits[c+1:c+9],)); c+=9
        else:
            items.append((bits[c:c+2]+bits[c+2:c+2+SEED_BITS],)); c+=2+SEED_BITS
    return items
def is_rec(it): return it[0][0]=='1'
def open_rec(it,pos):
    a=1 if it[0][:2]=="10" else 2
    seed=int(it[0][2:],2)
    # expand: length unknown a priori -> generate long, parse a items (relaxed: items are 9 or 16 bits)
    dig=H(f"{seed}|{pos}",2*(2+SEED_BITS)+32)
    out=[];c=0
    for _ in range(a):
        if dig[c]=='0': out.append(("0"+dig[c+1:c+9],)); c+=9
        else: out.append((dig[c:c+2+SEED_BITS],)); c+=2+SEED_BITS
    return out
def rule_A(items,T):
    for _ in range(T):
        items=shuffle(items,inv=True)
        out=[]
        for p,it in enumerate(items):
            out.extend(open_rec(it,p) if is_rec(it) else [it])
        items=out
    return items
def rule_B(items,T):
    for _ in range(T): items=shuffle(items,inv=True)
    changed=True
    while changed:
        changed=False; out=[]
        for p,it in enumerate(items):
            if is_rec(it): out.extend(open_rec(it,p)); changed=True
            else: out.append(it)
        items=out
    return items
def rule_C(items,T,target_hash,budget=500000):
    # DFS over which records to open after each unshuffle (maintainer's
    # multiple decodings); checksum referees complete candidates.
    cnt=[0]
    def step(items,t):
        if cnt[0]>budget: return None
        if t==0:
            if any(is_rec(it) for it in items): return None
            blocks="".join(it[0][1:] for it in items)
            if hashlib.sha256(blocks.encode()).hexdigest()==target_hash: return items
            return None
        cur=shuffle(items,inv=True)
        recs=[p for p,it in enumerate(cur) if is_rec(it)]
        # choose subset to open (records made in pass t); try largest-first heuristic then all subsets
        from itertools import combinations
        order=[]
        for k in range(len(recs),-1,-1):
            order.extend(combinations(recs,k))
        for subset in order:
            cnt[0]+=1
            if cnt[0]>budget: return None
            out=[]
            for p,it in enumerate(cur):
                if p in subset: out.extend(open_rec(it,p))
                else: out.append(it)
            r=step(out,t-1)
            if r is not None: return r
        return None
    return step(items,T)
def main():
    rng=random.Random(7)
    res={"A":0,"B":0,"C":0}; trials=0
    for N in (6,8):
        for T in (2,3):
            for rep in range(3):
                blocks=["".join(rng.choice("01") for _ in range(8)) for _ in range(N)]
                want=hashlib.sha256("".join(blocks).encode()).hexdigest()
                enc=encode(blocks,T)
                bits="".join(it[0] for it in enc)
                items=parse(bits)
                trials+=1
                for name,fn in (("A",rule_A),("B",rule_B)):
                    try:
                        out=fn([tuple(i) for i in items],T)
                        got="".join(it[0][1:] for it in out if not is_rec(it))
                        ok=(not any(is_rec(it) for it in out)) and hashlib.sha256(got.encode()).hexdigest()==want
                    except Exception: ok=False
                    res[name]+=ok
                okC=rule_C([tuple(i) for i in items],T,want) is not None
                res["C"]+=okC
                print(f"N={N} T={T} rep={rep}  A={'ok' if res else ''}",
                      f"A_pass_cum={res['A']} B_cum={res['B']} C_cum={res['C']}")
    print(f"\nFINAL: open-everything {res['A']}/{trials} | carry-to-end {res['B']}/{trials} | "
          f"maintainer's keep-what-decodes {res['C']}/{trials}")
if __name__=="__main__": main()
