#!/usr/bin/env python3
"""Robin's decode spec, implemented verbatim from his message:
- ENCODE pass: search seeds (salt = item's CURRENT position, pre-shuffle);
  replace matches in place; then shuffle x5 +1.
- DECODE: -1, /5 unshuffle; walk the string decoding EVERY record at its
  CURRENT position as salt, skipping 111 literals; repeat; when a walk
  finds only 111s, unwrap per header.
Variant B is identical except records created in pass k are opened only
on the walk that reverses pass k (they ride until then).
Real SHA-256. Alphabet: '111'+8 = literal block; '0'+14b seed = arity-1
record; '10'+14b seed = arity-2 record. Relaxed acceptance (decode test).
"""
import hashlib, random
SEED=14
def H(key,n):
    out="";c=0
    while len(out)<n:
        out+="".join(f"{b:08b}" for b in hashlib.sha256(f"{key}#{c}".encode()).digest());c+=1
    return out[:n]
def prime_geq(n):
    def isp(m):
        f=2
        while f*f<=m:
            if m%f==0:return False
            f+=1
        return m>1
    while not isp(n):n+=1
    return n
def shuf(items,inv=False):
    M=len(items);P=prime_geq(max(M,7));out=[None]*M
    for i,it in enumerate(items):
        if not inv:
            j=(5*i)%P
            while j>=M:j=(5*j)%P
            out[(j+1)%M]=it
        else:
            k=(i-1)%M;v=pow(5,-1,P);j=(v*k)%P
            while j>=M:j=(v*j)%P
            out[j]=it
    return out
def wire(it):return it["bits"]
def parse_digest(d,arity):
    items=[];c=0
    for _ in range(arity):
        if d[c:c+3]=="111":items.append({"bits":"111"+d[c+3:c+11]});c+=11
        elif d[c]=="0":items.append({"bits":d[c:c+1+SEED]});c+=1+SEED
        else:items.append({"bits":d[c:c+2+SEED]});c+=2+SEED
    return items
def is_rec(it):return not it["bits"].startswith("111")
def encode(blocks,T,budget=9000,log=None):
    items=[{"bits":"111"+b} for b in blocks]
    for t in range(1,T+1):
        i=0
        while i<len(items):
            # arity-2 first
            done=False
            if i+1<len(items):
                tgt=wire(items[i])+wire(items[i+1])
                for s in range(budget):
                    if H(f"{s}|{i}",len(tgt))==tgt:
                        items[i:i+2]=[{"bits":"10"+format(s,f"0{SEED}b"),"born":t,
                                       "kids_born":[items[i].get("born"),items[i+1].get("born")]}]
                        log is not None and log.append(("ENC",t,i,s,2)); done=True; break
            if not done:
                tgt=wire(items[i])
                for s in range(budget):
                    if H(f"{s}|{i}",len(tgt))==tgt:
                        items[i]={"bits":"0"+format(s,f"0{SEED}b"),"born":t,
                                  "kids_born":[items[i].get("born")]}
                        log is not None and log.append(("ENC",t,i,s,1)); break
            i+=1
        items=shuf(items)
    return items
def decode(items,T,defer=False,log=None):
    items=[dict(it) for it in items]
    for walk in range(1,T+1):
        items=shuf(items,inv=True)
        out=[]
        for p,it in enumerate(items):
            if is_rec(it) and (not defer or it.get("born")==T-walk+1):
                b=it["bits"];a=1 if b[0]=="0" else 2
                s=int(b[1:1+SEED] if a==1 else b[2:2+SEED],2)
                exp=H(f"{s}|{p}",260)
                kids=parse_digest(exp,2 if a==2 else 1)
                kb=it.get("kids_born",[None]*len(kids))
                for kid,b in zip(kids,kb):
                    if b is not None: kid["born"]=b
                log is not None and log.append(("DEC",walk,p,s,a))
                out.extend(kids)
            else:out.append(it)
        items=out
    ok_struct=all(not is_rec(it) for it in items)
    blocks=[it["bits"][3:] for it in items if not is_rec(it)]
    return blocks,ok_struct
def main():
    rng=random.Random(99)
    nA=nB=trials=0
    for trial in range(10):
        blocks=["".join(rng.choice("01") for _ in range(8)) for _ in range(7)]
        elog=[]
        enc=encode(blocks,2,log=elog)
        survivors=[it for it in enc if is_rec(it) and it.get("born")==1]
        if not any(e[1]==1 for e in elog) or not any(e[1]==2 for e in elog) or not survivors:
            continue  # need pass-1 record surviving + a pass-2 record, per the dispute
        trials+=1
        dA,_=decode(enc,2,defer=False)
        dB,_=decode(enc,2,defer=True)
        okA="".join(dA)=="".join(blocks); okB="".join(dB)=="".join(blocks)
        nA+=okA;nB+=okB
        if trials==1:
            print("TRIAL 1 FULL TRACE  (original 7 blocks, 2 passes)")
            for e in elog: print(f"  pass {e[1]}: position {e[2]} matched seed {e[3]} (arity {e[4]}) -> salt = {e[2]}")
            print("  --- decode, Robin's rule (open everything each walk) ---")
            dlog=[];decode(enc,2,defer=False,log=dlog)
            for d in dlog: print(f"  walk {d[1]}: opened record at position {d[2]} with salt {d[2]} (seed {d[3]})")
            print(f"  original : {' '.join(blocks)}")
            print(f"  rule A out: {' '.join(dA) if dA else '(structure broken)'}  -> {'EXACT' if okA else 'DIFFERENT BYTES'}")
            print(f"  rule B out: {' '.join(dB)}  -> {'EXACT' if okB else 'DIFFERENT'}   (B = identical, but pass-1 records ride until walk 2)")
    print(f"\nacross {trials} files containing a surviving pass-1 record:")
    print(f"  open-everything-each-walk : {nA}/{trials} exact round trips")
    print(f"  survivors-ride-one-walk   : {nB}/{trials} exact round trips")
if __name__=="__main__":main()
