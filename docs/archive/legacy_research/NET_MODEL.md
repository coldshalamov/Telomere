# Telomere Net-Compression Model — Proof, Spec, and Exact Equations

This document models **only the real Telomere wire format** and asks one
honest question: *does total emitted size shrink?* It does not invent layer
descriptors, literal-gap records, profile metadata, padding taxes, hidden
selector maps, or per-file helper tables. Where a future format change is
discussed it is explicitly labelled **[future / optional]**.

Every number here is anchored to code via `src/bin/v2_cost_probe.rs`
(reproduce with `cargo run --bin v2_cost_probe`) and the cost functions in
`src/tlmr_v2.rs`, `src/header.rs`, and the `lotus` crate. The closed-form
Lotus model below was checked equal to the real `lotus_encoded_bit_len` on
every sampled value.

---

## 0. Two formats exist; name them before modelling

| | **V1** (legacy default CLI) | **V2** (active research path) |
|---|---|---|
| Emit path | `compress_multi_pass_with_config` → `src/compress.rs` | `compress_streaming_v2*` / `compress_indexed_v2*` |
| Decode path | `decompress_with_limit` v1 branch (`src/lib.rs`) | `decompress_v2_with_limit` (`src/tlmr_v2.rs`) |
| Literal unit | **one 3-bit marker per analysis block** + byte-pad + block bytes | **one `LiteralRun` record per maximal literal run** (len + raw bytes) |
| Seed record | `[arity codeword][Lotus seed_index (J3D1)]` | `[Lotus tag][Lotus(span−1)][Lotus seed_index]` |

The user's described "current/wanted shape" (short header, literal
marker + raw bytes, seed/arity marker + seed index, ordered records decoded
sequentially) is exactly **V2**. We model V2 as *current*, and treat V1 only
as the baseline the marker question is really about.

---

## 1. The marker question (proven)

### 1.1 Does the current format require a literal marker per analysis block?

**V1: yes.** `src/compress.rs:251-260` emits, for every literal *block*:

```
encode_v1_record_into_writer(0xFF, 0)   // 3-bit "111" literal escape
pad to byte boundary                    // 0..7 zero bits
dump block_size raw bytes
```

`src/lib.rs:242-271` mirrors this on decode: it reads one 3-bit escape, pads,
then copies **exactly `block_size`** (or `last_block_size`) bytes. There is no
length field and no coalescing — *k* consecutive literal blocks cost *k*
markers. Because the raw bytes must land byte-aligned, the 3-bit escape always
rounds up to a **full byte** of overhead per block.

> **V1 incompressible-data tax = 1 byte / block = `1/B` of the file.**
> B=2 → 50% bloat, B=8 → 12.5%, B=16 → 6.25%. This is the per-block marker the
> question worries about, and it is real in V1.

**V2: no.** `src/indexed.rs:852-911` (`encode_layer_records_with_fixed_span`)
walks the data and, wherever no seed record is selected, **coalesces the whole
contiguous literal run** and emits it as one or more `LiteralRun` records
(`v2_literal_record_into_writer`, split only at the 65535-byte field cap):

```
[Lotus tag=1][Lotus(len−1)][pad to byte][len raw bytes]
```

So the "future `LiteralRun(length, raw_bytes)`" already exists and is the
active V2 literal record. **The marker question is already answered in the
shipped V2 code**, not a future task.

### 1.2 Is `LiteralRun` unambiguously decodable? (decoder, plainly)

Yes. Decode is driven by output length, not by any per-block grid. From
`decode_v2_payload_with_bit_len` (`src/tlmr_v2.rs:703-868`), in plain steps:

```
decode_layer(payload, descriptor):
    out = []
    reader = bitreader(payload)
    while len(out) < descriptor.decoded_len:        # stop on OUTPUT length
        tag = lotus_decode(reader)                   # self-delimiting
        if tag == 0:                                 # seed-span record
            span = fixed_span or (lotus_decode(reader) + 1)
            seed_index = lotus_decode(reader)
            seed = index_to_seed(seed_index, max_seed_len)
            out += expand(seed)[0 .. span]
        elif tag == 1:                               # LiteralRun record
            len = lotus_decode(reader) + 1
            skip bits until reader is byte-aligned   # all skipped bits must be 0
            out += read len raw bytes
        else: error
    verify trailing bits are zero pad
    return out
```

It is unambiguous because: (a) every record begins with a self-delimiting
Lotus tag that names its type; (b) `span−1` and `len−1` are self-delimiting
Lotus codes, so each record's length is known before its payload; (c) literal
raw bytes are byte-aligned, so they cannot be confused with Lotus codes; and
(d) the loop terminates on `decoded_len`, so no end-marker is needed. A
`LiteralRun` therefore needs **no per-block marker** to stay decodable — the
length field plus the output-length stop replace the grid entirely.

**[future / optional] single-header shape.** The user's minimal "short header,
ordered records" shape can drop the per-layer descriptor's `decoded_len`
entirely: a one-layer file terminates decode on the header's `original_len`.
Per-layer `decoded_len`/`decoded_hash` are only needed for *stacked* layers
(multi-pass). For a single pass they are removable overhead, so we label them
optional and exclude per-pass descriptor stacking from the "wanted" minimal
accounting (it is charged explicitly in the multi-pass section).

---

## 2. Exact cost equations (V2, code-anchored)

### 2.1 Lotus codeword cost (verified exact)

Lotus width of a value: `W(x) = ⌊log₂(x + 2)⌋`  (smallest `w≥1` with
`x ∈ [2ʷ−2, 2ʷ⁺¹−3]`). Total bits for `Lotus(v)` under `(J=3, tiers=2)`:

```
L(v) = J + W(v+1) + t₁ + t₂ ,   t₁ = W(W(v+1)),   t₂ = W(t₁)
```

Verified equal to `lotus_encoded_bit_len(v,3,2)` for all sampled `v`
(`v2_cost_probe`). Reference values:

| v | 0 | 1 | 3 | 7 | 15 | 31 | 63 | 127 | 255 | 65534 |
|---|---|---|---|---|----|----|----|-----|-----|-------|
| L(v) bits | 6 | 9 | 9 | 10 | 11 | 12 | 14 | 15 | 16 | 25 |

Record tags: `tag=0` (seed-span) = `L(0)` = **6 bits**; `tag=1` (literal) =
`L(1)` = **9 bits**. *(The source comment in `tlmr_v2.rs:27` claiming both tags
are 6 bits is wrong; the literal tag is 9 — measured, not assumed.)*

Let `ceil8(x) = 8·⌈x/8⌉`.

### 2.2 Header (one-time)

```
H_bits = 40                                   # raw "TLMR" + version (5 bytes)
       + Σ L(field)  over 7 header fields     # preset,hasher,seed_order,
                                              #   layer_count,hash_bits,
                                              #   original_len,payload_bit_len
       + hash_bits                            # raw truncated output hash
       + D_bits·(#layers)                     # per-layer descriptor, §2.5
       + pad to byte boundary
```

Measured single-layer container (`hash_bits=13`, tiny payload): **24 bytes**;
for a 1 MB file ≈ **24–31 bytes** (matches `POWER_MODEL.md` line 349). `H` is
O(1) in file size — negligible per byte for any non-trivial input.

### 2.3 LiteralRun record (per maximal literal run of `m ≤ 65535` bytes)

```
Lit(m)   = ceil8( 9 + L(m−1) ) + 8m          # tag(9) + Lotus(m−1) + bytealign + raw
O_lit(m) = Lit(m) − 8m = ceil8( 9 + L(m−1) ) # the run's overhead (no raw bytes)
```

| m bytes | 1 | 4 | 8 | 64 | 256 | 1024 | 16384 | 65535 |
|---|---|---|---|---|---|---|---|---|
| O_lit (bits) | 16 | 24 | 24 | 24 | 32 | 32 | 32 | 40 |
| O_lit / byte | 16 | 6 | 3 | 0.375 | 0.125 | 0.031 | 0.002 | 0.0006 |

**O_lit is one small constant per run** (3–5 bytes), amortizing to ~0 over a
long run. Runs over 65535 bytes split into `⌈m/65535⌉` records.

### 2.4 Seed-span record (per selected hit)

```
S_var(span, s) = 6 + L(span−1) + L(s)        # variable span (carries span len)
S_fix(s)       = 6 + L(s)                     # fixed-span layer (span in descriptor)
```
**[future / optional]** minimal record (1-bit flag + flat fixed-width index):
```
S_min(s)       = 1 + b ,   b = ⌈log₂ K⌉       # b = 8 for K=256 (max_seed_len=1)
```
Seed-index facts (`max_seed_len=1`, K=256, uniform): Lotus index averages
**13.85 bits** (min 6, max 16); a flat 8-bit index is **−5.85 bits/record**.
A bounded seed universe is the one case where Lotus *over*-charges.

### 2.5 Layer descriptor (charged only for multi-pass, §4)

```
D_bits = L(decoded_len) + hash_bits
       + L(max_seed_len) + L(max_span_len) + L(block_size)
       + L(tier_policy)  + L(span_step)
```
Measured ≈ **9 bytes / layer** (`v2_cost_probe`: container 24→33→…→102 for
1→10 layers). This is the real recurring cost of each extra pass.

### 2.6 Total emitted size and net (single pass)

For input `N` bytes, with selected seed spans covering `C` bytes total and the
remaining `N−C` literal bytes packed into `R` runs of lengths `mⱼ`:

```
Emitted_bits = 8H + 8(N − C) + Σⱼ O_lit(mⱼ) + Σ_hits S(·)

NetSave_bits = 8N − Emitted_bits
             = 8C  −  8H  −  Σⱼ O_lit(mⱼ)  −  Σ_hits S(·)
```

Net compression (total emitted shrinks) **iff**:

```
8C  >  8H + Σⱼ O_lit(mⱼ) + Σ_hits S(·)
```

Gross seed opportunity (how many spans *could* match a cheap seed) is **not**
on the left side of this inequality and is **not** a compression rate. Only
realized `8C` minus *all* overhead counts.

---

## 3. The core result: clustered break-even `k*` (not single-hit)

A single hit is the wrong atomic unit. `encode_layer_records_with_fixed_span`
coalesces literals; dropping **one isolated** seed record into the interior of
a literal run **splits that run in two**, adding **one** `O_lit` header. So:

```
Δ(1 isolated interior hit) = S + O_lit − 8B          # often POSITIVE = bloat
Δ(cluster of k adjacent hits, interior) = k·S + O_lit − 8kB
```

A cluster is net-profitable iff `k·(8B − S) > O_lit`, giving the **real
V2-native break-even**:

```
            ⌈   O_lit    ⌉
   k*(B) =  | ----------- |        valid only when 8B > S   (else: never)
            |  8B − S     |
```

Measured (`O_lit = 24`, `S_v2_best = 12` at seed 0, `S_min = 9`):

| B (bytes) | 8B bits | k\* (V2 fixed-span, best seed) | k\* (minimal record) |
|---|---|---|---|
| 1 | 8 | never (8B<S) | never |
| 2 | 16 | **6** | **4** |
| 3 | 24 | 2 | 2 |
| 4 | 32 | 2 | 2 |
| 5 | 40 | 1 | 1 |
| ≥5 | ≥40 | 1 | 1 |

> At average seed cost (`S = 6+13.85 ≈ 20`), B=2 is **never** profitable in the
> current format — only the few cheapest seeds clear `8B`. The minimal record
> lowers `k*` but does not remove it.

### 3.1 The fragmentation-vs-rarity vise

Effective probability of a *profitable cluster* (structure-blind,
`h = K/2^{8B}` per-block hit prob): `≈ h^{k*}`. Because `k*·8B ≈ k*·S + O_lit`
at the margin, `h^{k*}` stays pinned near **2⁻³²** for every feasible B at
K=256:

| B | h = K/2^{8B} | k\* | h^{k\*} (profitable-cluster prob) |
|---|---|---|---|
| 2 | 2⁻⁸ | 4 | ≈ 2⁻³² |
| 3 | 2⁻¹⁶ | 2 | ≈ 2⁻³² |
| 5 | 2⁻³² | 1 | ≈ 2⁻³² |

- **Small B:** hits common, but `k*` large → need many *adjacent* hits →
  clusters essentially never form.
- **Large B:** `k*=1` (no clustering needed) → but single hits vanishingly
  rare.

There is no block size that is simultaneously common-hit and cluster-free.
Expected profitable clusters in 1 MB at K=256 ≈ `(N/B)·h^{k*} ≈ 2⁻¹³` → **≈ 0
net savings**, for *all* B. Deeper search raises K but also raises `S` (longer
seed index) and forces larger B to stay profitable, reproducing the same vise
(see `POWER_MODEL.md`). **This, not the literal tax, is the binding wall in
V2.**

---

## 4. Multi-pass and the persistent-match-rate audit

Per-pass recurrence (a later pass compresses the previous pass's payload):

```
payload₀ = N
payloadₖ = payloadₖ₋₁ − Σ NetSaveₖ                  # bytes actually saved in pass k
fileₖ    = payloadₖ + H + D_bits·k / 8              # +9 bytes container per pass
```

**Why is each pass fresh — or not?** Audited honestly:

| pass | what it searches | fresh opportunity? | verdict |
|---|---|---|---|
| 1 | the original bytes | yes — first trial | **real** |
| k≥2, **fixed grid** | payloadₖ₋₁ = the *same* literal bytes that already failed + tiny high-entropy record bytes | no — identical bytes, identical seeds, identical block grid → 0 new hits | **repeated-search optimism** |
| k≥2, **rechunk** (change B or span_step) | same bytes, *different* windows/boundaries | yes — genuinely new trials over the same bytes | real but **bounded** |

The only legitimate fresh-trial source on unchanged data is **rechunk /
changed boundaries**. Its total lift saturates at the aggregate-arity
constant (~**1.2×**, `CLAUDE.md`) — a one-time constant factor, **not** a
per-pass compounding gain. Meanwhile every extra layer costs **+9 bytes**
(§2.5), and `src/streaming.rs:361` already **stops** the moment a pass is
non-compressive (`payload.len() >= current.len()`).

> **Conclusion: effective passes ≈ 1 (≤ ~2 with rechunk).** `net(passes)` rises
> by at most the ~1.2× rechunk constant, then declines monotonically under the
> 9-byte/pass descriptor tax. 50/100/200 passes only bloat. The `+0.3%/pass ×
> 10` framing assumes independent fresh trials that the format does not
> provide; restate the target as **"+X% in ~1 effective pass."**

**Measured.** Running the real encoder with `passes=10` on 1 MB of
incompressible data keeps exactly **1 layer** and halts with
`stop_reason = non_compressive_layer` (0 selected hits, −0.011% net). The
behavioral claim "passes do not stack" is observed, not just inferred from the
stop condition — see `model_analysis/NET_COMPRESSION_REPORT.md` §3.

---

## 5. What this means for the optimisation target

To reach even +0.3% *true net* on a 1 MB file you must satisfy
`8C > 8H + ΣO_lit + ΣS` by a 3000-byte margin — i.e. realize ≈ **1500+
profitable cluster-bytes** that raw search delivers with probability ≈ 2⁻³².
No pure-format change moves a 2⁻³² probability to order 1. Format changes
(minimal record, flat index, fixed-span, fragmentation-aware selection) lower
`H`, `O_lit`, `S`, and `k*` — they push the **bloat floor toward 0** and bank
every real cluster, but they **cannot manufacture clustered hit density**.

The single lever that moves `C` is a **mechanism that raises profitable
*clustered* exact-hit density** while keeping decode cheap: frozen public
presets, reversible transforms, dictionaries, or schema-native tables —
charged honestly in the bitstream. That is the open question in `CLAUDE.md`,
and the schema-native dictionary probe (`VIABILITY.md` level 45) is the
lane that has flickered positive.

See `model_analysis/NET_COMPRESSION_REPORT.md` for the experiment table, the
10-pass ledger, projections at 1/10/50/100/200 passes, and the best current
candidate.
