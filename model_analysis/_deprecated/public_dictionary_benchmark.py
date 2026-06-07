#!/usr/bin/env python3
"""
Decisive experiment for Telomere's live lane: a frozen, PUBLIC, cross-file
dictionary on file-family-redundant data.

It answers two load-bearing questions with real bytes on held-out files:
  (1) Does a shared public dictionary beat per-file compression? (the project's
      real reframed thesis: cross-file redundancy a single-file coder can't see)
  (2) Does the SEED indirection earn its keep vs. a plain dictionary index?
      (Telomere stores a Lotus seed-index record; the honest alternative is a
       direct varint index into the same public table.)

Controls: a paired SHADOW corpus (same structure, swapped vocabulary) must NOT
compress under the dictionary — that proves the win is real structure capture,
not an artifact. zstd --train is the real-world incumbent for shared dictionaries.
"""
import io, os, json, random, re, struct
import zstandard as zstd

random.seed(20260605)
OUT = []
def log(s): OUT.append(s); print(s)

# ---------- 1. a controlled cross-file-redundant corpus ----------
# Shared schema + enums (cross-file redundancy). Random ids/names/numbers (per-file entropy).
COUNTRIES = ["US","GB","DE","FR","JP","BR","IN","CA","AU","NL","SE","ES"]
STATUSES  = ["active","pending","suspended","closed","trial"]
ROLES     = ["admin","editor","viewer","owner","billing","support"]
FIRST     = ["alex","sam","jordan","taylor","morgan","casey","riley","jamie","robin","drew"]
LAST      = ["nguyen","patel","smith","garcia","kim","muller","rossi","silva","khan","jones"]

def make_record(rng):
    fn, ln = rng.choice(FIRST), rng.choice(LAST)
    return {
        "user_id": rng.randint(10**7, 10**8),
        "first_name": fn, "last_name": ln,
        "email": f"{fn}.{ln}{rng.randint(1,999)}@example.com",
        "country_code": rng.choice(COUNTRIES),
        "status": rng.choice(STATUSES),
        "role": rng.choice(ROLES),
        "active": rng.choice([True, False]),
        "login_count": rng.randint(0, 5000),
        "score": round(rng.uniform(0, 100), 2),
        "created_at": f"2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:00Z",
        "tags": rng.sample(["beta","vip","legacy","new","flagged","verified"], k=rng.randint(0,3)),
    }

def make_file(seed, vocab=None):
    rng = random.Random(seed)
    recs = [make_record(rng) for _ in range(20)]
    text = json.dumps({"records": recs}, indent=2)
    if vocab:  # shadow: swap every schema word for a same-length nonsense token
        for k, v in vocab.items():
            text = text.replace(k, v)
    return text.encode()

N_TRAIN, N_TEST = 60, 25
train = [make_file(1000+i) for i in range(N_TRAIN)]
test  = [make_file(9000+i) for i in range(N_TEST)]

# shadow vocab: same-length replacements for the shared schema words (kills real redundancy)
SHADOW = {w: "".join(chr((ord(c)-97+7)%26+97) if c.isalpha() else c for c in w)
          for w in ["user_id","first_name","last_name","email","country_code","status",
                    "role","active","login_count","score","created_at","tags","records","example"]}
test_shadow = [make_file(9000+i, vocab=SHADOW) for i in range(N_TEST)]

raw_test = sum(len(f) for f in test)
log(f"Corpus: {N_TRAIN} train + {N_TEST} held-out files. Held-out raw bytes: {raw_test}")

# ---------- 2. baselines: zstd per-file, and zstd with a TRAINED shared dict ----------
def zstd_size(data, level=19, cdict=None):
    c = zstd.ZstdCompressor(level=level, dict_data=cdict) if cdict else zstd.ZstdCompressor(level=level)
    return len(c.compress(data))

A = sum(zstd_size(f) for f in test)                      # per-file, no sharing
dict_data = zstd.train_dictionary(64*1024, train)        # shared, trained on train only
B = sum(zstd_size(f, cdict=dict_data) for f in test)     # per-file WITH shared dict

# ---------- 3. frozen PUBLIC token dictionary (built from TRAIN only) ----------
tok_re = re.compile(rb'[A-Za-z_]+|\s+|[^A-Za-z_\s]+')
from collections import Counter
cnt = Counter()
for f in train:
    for t in tok_re.findall(f):
        if 2 <= len(t) <= 40: cnt[t] += 1
# value = bytes a reference would save; keep the best ~255 (1-byte index space)
cand = sorted(cnt.items(), key=lambda kv: kv[1]*len(kv[0]), reverse=True)[:255]
DICT = [t for t,_ in cand]
index = {t:i for i,t in enumerate(DICT)}
maxtok = max(len(t) for t in DICT)

def varint_len(n):
    n+=1; b=1
    while n>=128: n>>=7; b+=1
    return b

def encode(files, ref_bytes_fn):
    """Greedy longest-match dictionary substitution. Returns (encoded_streams, total_bytes)."""
    total=0; streams=[]
    for f in files:
        buf=bytearray(); i=0; lit=bytearray()
        def flush():
            nonlocal total
            if lit:
                buf.append(0);
                n=len(lit);
                while True:
                    x=n&0x7f; n>>=7
                    buf.append(x|(0x80 if n else 0))
                    if not n: break
                buf.extend(lit); lit.clear()
        while i<len(f):
            m=None
            for L in range(min(maxtok,len(f)-i),1,-1):
                sub=bytes(f[i:i+L])
                if sub in index: m=(sub,L); break
            if m:
                flush()
                ref=index[m[0]]
                buf.extend(ref_bytes_fn(ref))   # the reference encoding under test
                i+=m[1]
            else:
                lit.append(f[i]); i+=1
        flush()
        streams.append(bytes(buf)); total+=len(buf)
    return streams, total

# C: DIRECT varint index into the public dict (the honest "dictionary is the compressor")
def ref_direct(idx):
    out=bytearray(); n=idx+1
    while True:
        x=n&0x7f; n>>=7; out.append((x|0x80) if n else x|0x00);
        if not n: break
    # mark as a ref (high bit on first byte set means ref; literals use op byte 0)
    out[0]|=0x80
    return bytes([0x81])+bytes(out)  # 1 op-marker + varint; ~2 bytes for 255 entries... keep simple:
# (simplify: a ref costs a 1-byte op tag + 1-byte index for <=255 entries)
def ref_direct(idx):  # ~ 1 byte (index) since op/flag amortized; charge 1 byte for <=255 dict
    return bytes([idx & 0xff])
# D: Telomere SEED record: Lotus(tag=0)+Lotus(seed_index). For idx 0..255 under J3D2 ~13-15 bits.
def ref_seed(idx):
    return b"\x00\x00"  # ~2 bytes (tag + seed-index), matching POWER_MODEL fixed-span record

_, C = encode(test, ref_direct)
_, D = encode(test, ref_seed)
C_streams, _ = encode(test, ref_direct)
C_plus_zstd = sum(zstd_size(s) for s in C_streams)   # fair: dict-substitution THEN entropy code

# ---------- 4. SHADOW control: same machine, vocabulary swapped (should NOT compress) ----------
raw_shadow = sum(len(f) for f in test_shadow)
_, C_shadow = encode(test_shadow, ref_direct)

# ---------- 5. report ----------
log("")
log("HELD-OUT TOTAL BYTES (lower = better). Public dict + zstd dict are shared, not charged per file:")
log(f"  raw (uncompressed)                         {raw_test:8d}   1.000x")
log(f"  A. zstd -19, per file (no sharing)         {A:8d}   {A/raw_test:.3f}x")
log(f"  B. zstd -19 + TRAINED shared dict          {B:8d}   {B/raw_test:.3f}x   <- real incumbent for shared dicts")
log(f"  C. public dict, DIRECT 1-byte index        {C:8d}   {C/raw_test:.3f}x")
log(f"  D. public dict, SEED record (~2B/ref)      {D:8d}   {D/raw_test:.3f}x   <- Telomere's actual encoding")
log(f"  C+zstd (dict-substitute, then entropy)     {C_plus_zstd:8d}   {C_plus_zstd/raw_test:.3f}x")
log("")
log(f"  seed-step overhead (D - C)                 {D-C:8d} bytes  ({100*(D-C)/C:.1f}% worse than a direct index)")
log("")
log("SHADOW CONTROL (vocabulary swapped; dictionary should stop matching):")
log(f"  C on shadow corpus                         {C_shadow:8d}   {C_shadow/raw_shadow:.3f}x   (want ~1.0 = null)")
log("")
log("READS:")
log(f"  - public dict beats per-file zstd?   C<A : {C<A}   ({A-C:+d} bytes)")
log(f"  - public dict beats zstd-trained?    C<B : {C<B}   ({B-C:+d} bytes)")
log(f"  - C+zstd beats zstd-trained?  C+zstd<B    : {C_plus_zstd<B}   ({B-C_plus_zstd:+d} bytes)")
log(f"  - seed record costs more than direct idx? D>C: {D>C}")
log(f"  - shadow stayed ~null (control clean)? {C_shadow/raw_shadow>0.92}")

with open("public_dictionary_benchmark_results.txt","w") as fh:
    fh.write("\n".join(OUT)+"\n")
