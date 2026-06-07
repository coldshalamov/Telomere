#!/usr/bin/env python3
"""
END-TO-END SIMULATION OF THE FULL TELOMERE MACHINE — maintainer's spec, every fix included.

Implemented format (from the maintainer's specification, June 2026):
  PASS 1: seeds matched against RAW block spans (arity 1-5, no markers — this is how
          planted/natural structure is visible). Replace span with record iff
          record < a*(BLOCK+3) bits (i.e., smaller than what wrapping would cost).
          Unmatched blocks are then wrapped ONCE: '111' + raw bits. Never re-wrapped.
  PASS 2+: ENTRY SEMANTICS ("a block is a block is a block"): targets are concatenated
          ENTRY BYTES (headers included), so recursion self-describes, no layer tags.
          Replace window of entries iff record STRICTLY smaller.
  Records: Kraft-complete arity alphabet 1:'00' 2:'01' 3:'100' 4:'101' 5:'110';
          seed index in J3D1 (3-bit jumpstarter = width of length field; length; payload).
  Shuffle between passes: deterministic, pass-indexed, decoder-known, 0 file bits.
  Every pass: full enumeration of seeds 0..K-1 (expansions fixed, computed once).
  Windows capped at 64 bits (wins beyond need P < 2^-44 at this K; noted, immaterial).

GENEROUS-TO-THESIS toy: 8-bit blocks (wrapper = +37.5% of harvestable slack; raw arity-3
spans = 24 bits, fully searchable by K=2^19 — depth saturates the useful tiers).
FAIRNESS CONTROL: planted file (built from cheap seeds) through the IDENTICAL machine.
"""
import hashlib, numpy as np, sys, time

BLOCK   = 8
N       = 12000
K       = 1 << 19
PASSES  = 12
MAX_W   = 64
ACODE   = {1:('00',2),2:('01',2),3:('100',3),4:('101',3),5:('110',3)}
RAW     = N*BLOCK

def expansions(k):
    out = np.empty(k, dtype=np.uint64)
    for i in range(k):
        out[i] = int.from_bytes(hashlib.blake2b(i.to_bytes(8,'little'),digest_size=8).digest(),'big')
    return out

EXP = expansions(K)
_pc = {}
def prefix_table(L):
    t = _pc.get(L)
    if t is None:
        pref = (EXP >> np.uint64(64-L)).astype(np.uint64)
        order = np.argsort(pref, kind='stable')      # ties keep ascending seed index
        _pc[L] = t = (pref[order], order)
    return t

def best_seeds(L, targets):
    """For each target (uint64 array), the MINIMUM seed index whose L-bit prefix equals it, or -1."""
    sp, order = prefix_table(L)
    pos = np.searchsorted(sp, targets)
    ok = pos < len(sp)
    res = np.full(len(targets), -1, dtype=np.int64)
    okk = ok.copy()
    okk[ok] = sp[pos[ok]] == targets[ok]
    res[okk] = order[pos[okk]]
    return res

def j3d1(i):
    p  = max(1, int(i).bit_length()); w4 = max(1, p.bit_length())
    return 3+w4+p, ((w4,3),(p,w4),(int(i),p))

def record(arity, i):
    code, cl = ACODE[arity]
    cost, fl = j3d1(i)
    v, L = int(code,2), cl
    for val,w in fl: v=(v<<w)|val; L+=w
    return L, v

class E:
    __slots__=('L','v')
    def __init__(s,L,v): s.L=L; s.v=v

def shuffle(es, rule, p):
    n=len(es)
    if rule=='none': return es
    if rule=='pairswap':
        o=list(es)
        for i in range(0,n-1,2): o[i],o[i+1]=o[i+1],o[i]
        return o
    if rule=='rotate':
        s=(7919*p)%n; return es[s:]+es[:s]
    if rule=='prng':
        return [es[j] for j in np.random.default_rng(1000+p).permutation(n)]

def pass1(blocks):
    """Raw-span matching, then wrap leftovers. Returns entry list."""
    cands=[]
    for a in range(1,6):
        L=a*BLOCK
        if L>MAX_W: break
        t=np.zeros(N-a+1,dtype=np.uint64)
        for j in range(a): t=(t<<np.uint64(BLOCK))|blocks[j:N-a+1+j].astype(np.uint64)
        bs=best_seeds(L,t)
        for i in np.nonzero(bs>=0)[0]:
            rl,rv=record(a,int(bs[i]))
            bar=a*(BLOCK+3)
            if rl<bar: cands.append((bar-rl,int(i),a,rl,rv))
    cands.sort(key=lambda c:-c[0])
    used=np.zeros(N,bool); repl={}
    for sv,i,a,rl,rv in cands:
        if used[i:i+a].any(): continue
        used[i:i+a]=True; repl[i]=(a,rl,rv)
    es=[]; i=0
    while i<N:
        if i in repl:
            a,rl,rv=repl[i]; es.append(E(rl,rv)); i+=a
        else:
            es.append(E(BLOCK+3,(0b111<<BLOCK)|int(blocks[i]))); i+=1
    return es, len(repl)

def entry_pass(es):
    n=len(es); pref=[0]*(n+1)
    for i,e in enumerate(es): pref[i+1]=pref[i]+e.L
    byL={}
    for a in range(1,6):
        for i in range(n-a+1):
            L=pref[i+a]-pref[i]
            if L>MAX_W: continue
            v=0
            for e in es[i:i+a]: v=(v<<e.L)|e.v
            byL.setdefault(L,[]).append((v,i,a))
    cands=[]
    for L,lst in byL.items():
        t=np.array([x[0] for x in lst],dtype=np.uint64)
        bs=best_seeds(L,t)
        for k in np.nonzero(bs>=0)[0]:
            v,i,a=lst[k]; rl,rv=record(a,int(bs[k]))
            if rl<L: cands.append((L-rl,i,a,rl,rv))
    cands.sort(key=lambda c:-c[0])
    used=np.zeros(n,bool); repl={}; saved=0
    for sv,i,a,rl,rv in cands:
        if used[i:i+a].any(): continue
        used[i:i+a]=True; repl[i]=(a,rl,rv); saved+=sv
    out=[]; i=0
    while i<n:
        if i in repl:
            a,rl,rv=repl[i]; out.append(E(rl,rv)); i+=a
        else:
            out.append(es[i]); i+=1
    return out,len(repl),saved

def run(blocks,rule,passes=PASSES):
    es,w1=pass1(blocks)
    sz=sum(e.L for e in es)
    print(f"  pass  1 (raw matching + wrap-once): {sz:7d} bits ({100*sz/RAW:6.2f}% of raw)  raw-span wins: {w1}")
    for p in range(2,passes+1):
        es=shuffle(es,rule,p)
        es,w,s=entry_pass(es)
        sz=sum(e.L for e in es)
        print(f"  pass {p:2d} [{rule:8s}]: {sz:7d} bits ({100*sz/RAW:6.2f}%)  wins: {w:4d}  saved: {s} bits")
    return sz

t0=time.time()
rng=np.random.default_rng(42)
print(f"=== RANDOM DATA: {N} x {BLOCK}-bit blocks = {RAW} raw bits ===")
blocks=rng.integers(0,1<<BLOCK,N,dtype=np.uint64)
finals={}
for rule in ('none','pairswap','rotate'):
    print(f"\n--- shuffle: {rule} ---")
    finals[rule]=run(blocks,rule)
print("\n=== PLANTED CONTROL (identical machine): blocks built from cheap seeds ===")
pb=[]
while len(pb)<N:
    i=int(rng.integers(0,1<<10))
    e=int(EXP[i])>>40
    pb+=[(e>>16)&0xFF,(e>>8)&0xFF,e&0xFF]
pl=run(np.array(pb[:N],dtype=np.uint64),'rotate',passes=4)
print(f"\nSUMMARY  (raw = 100%):")
for r,s in finals.items(): print(f"  random + {r:9s}: final {100*s/RAW:6.2f}%")
print(f"  PLANTED control : final {100*pl/RAW:6.2f}%  {'<-- NET COMPRESSION, same code' if pl<RAW else ''}")
print(f"[{time.time()-t0:.1f}s]")
