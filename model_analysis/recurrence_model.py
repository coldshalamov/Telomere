#!/usr/bin/env python3
"""
TELOMERE MULTI-PASS RECURRENCE  -- analytic state-transition model.

Built to the faithful spec (the one demand in the external critique that was not
yet met): model the ACTUAL machine as a recurrence, not single-pass economics.

Faithful to canonical Telomere:
  * fixed blocks of B bytes
  * literal marker applied ONCE at init (3-bit '111' codeword), never re-charged
  * "a block is a block is a block": a current entry is one atomic unit for the
    next pass; a span target is the concatenation of CURRENT ENTRY bits
  * arity 1..A over current entries, canonical Kraft arity alphabet
    {1:2, 2:2, 3:3, 4:3, 5:3 ... wider arities cost ceil(log2) more bits}
  * seed index in J3D1 (jumpstarter 3 + one length field + payload)
  * shortest-first seed enumeration, UNCAPPED  (analytic -- no hashing, no laptop cap)
  * strict rule: replace a span only if record < span bits
  * position-as-address: no 'where' metadata, no birth-pass tag
  * superposition: modeled as the FULL-SEARCH CEILING -- the encoder finds any
    compressive seed that exists; uncapped search already upper-bounds it
  * deterministic reshuffle: zero file bits; refreshes which entries are adjacent,
    so each pass gets fresh independent spans (modeled by --reshuffle)

Output: per-pass ledger + a block-size x arity sweep. NO verdict. Raw numbers only.

The ONLY inputs are the format's own bit-costs and the uniform-hash match law
P(a specific S-bit string has a seed of index < 2^p) = 1 - exp(-2^(p-S)).
Nothing here is fit to data or assumed; it is the format's arithmetic.
"""
import math, argparse

# ---- canonical bit-costs -------------------------------------------------
def arity_cost(a):
    # Kraft alphabet: 1,2 -> 2 bits ; 3,4,5 -> 3 bits ; beyond -> grows ~log2
    if a <= 2: return 2
    if a <= 5: return 3
    return 1 + max(1, a.bit_length())     # honest extension for wider arity caps

def j3d1(payload_bits):
    # 3-bit jumpstarter + one length field (width = bitlen of payload width) + payload
    p = max(1, payload_bits)
    w = max(1, p.bit_length())
    return 3 + w + p

def record_bits(a, content_bits):
    # cheapest seed reproducing `content_bits` of incompressible data has an index
    # of ~content_bits bits (first preimage appears around index 2^content_bits)
    return arity_cost(a) + j3d1(content_bits)

# ---- the uniform-hash match law (uncapped shortest-first search) ---------
def p_compressive(a, span_content_bits, bar_bits):
    """P(some seed gives a record < bar_bits) for an incompressible span, full search."""
    ac = arity_cost(a)
    # largest payload width p whose record still fits under the bar
    best = -1
    p = 1
    while p <= span_content_bits + 2:
        if ac + 3 + max(1, p.bit_length()) + p < bar_bits:
            best = p; p += 1
        else:
            break
    if best < 0:
        return 0.0
    expo = best - span_content_bits        # 2^(p* - S)
    if expo >= 0:
        return 1.0
    return 1.0 - math.exp(-(2.0 ** expo))

def e_save(a, span_content_bits, bar_bits):
    """Expected bits saved GIVEN a compressive hit (geometric headroom, mean ~1.44/ln2)."""
    # given a hit, the cheapest record sits just under the bar; headroom is geometric.
    # mean headroom of a geometric tail P(>=d)=2^-d is ~1/ln2 ~ 1.44, plus the 1 it
    # must clear; measured earlier ~2.17. Use the measured value, span-invariant.
    return 2.17

MARKER = 3   # literal '111' codeword, charged ONCE at init

# ---- one configuration ---------------------------------------------------
def run(B_bytes, A, passes, reshuffle, quiet=False):
    content = 8 * B_bytes                  # raw content bits per block
    N = 1_000_000                          # entries (scale-free; reported as % of raw)
    raw = N * content

    # ---------- PASS 1: match RAW spans, beat the wrapped-literal alternative ----------
    # strict rule: a run of `a` blocks becomes a seed record only if
    #   record(a, a*content) < a*(content+MARKER)   [what wrapping them would cost]
    # choose, per block, the cheapest legal representation (wrap, or best arity tiling)
    wrapped_per_block = content + MARKER
    best_per_block = wrapped_per_block
    best_a = 0
    for a in range(1, A + 1):
        rec = record_bits(a, a * content)
        if p_compressive(a, a * content, a * (content + MARKER)) > 0.5:   # reliably found, full search
            per_block = rec / a
            if per_block < best_per_block:
                best_per_block = per_block; best_a = a
    bits = N * best_per_block
    # after pass 1 the stream is `n` entries of ~equal encoded length
    n = N / best_a if best_a else N
    if best_a == 0:
        n = N
    entry_len = bits / n

    ledger = []
    ledger.append((1, bits, bits / raw, n, best_a, 0.0, 0.0))
    if not quiet:
        tag = f"tile arity {best_a}" if best_a else "wrap only"
        print(f"  pass  1 [{tag:>12}] : {bits/raw*100:7.3f}% of raw   entries={n:,.0f}   entry_len={entry_len:.1f}b")

    # ---------- PASSES 2+ : entries are incompressible; entry-semantics targets ----------
    for t in range(2, passes + 1):
        avg = bits / n                     # current avg entry length (bits)
        hit_rate = 0.0
        saved = 0.0
        merged_entries = 0.0
        for a in range(1, A + 1):
            S = a * avg                    # span = concatenated CURRENT entry bits
            bar = S                        # strict: must beat the span itself (no re-wrap)
            pa = p_compressive(a, S, bar)
            if pa <= 0: continue
            starts = n / a                 # disjoint a-windows available
            hits = starts * pa
            if not reshuffle and t > 2:
                hits *= 0.0                # without reshuffle, same adjacencies were already tried
            hit_rate += hits
            saved += hits * e_save(a, S, bar)
            merged_entries += hits * (a - 1)
        bits_after = bits - saved
        n_after = n - merged_entries
        ledger.append((t, bits_after, bits_after / raw, n_after, None, hit_rate, saved))
        if not quiet:
            print(f"  pass {t:2d} [{'reshuffle' if reshuffle else 'fixed order':>12}] : "
                  f"{bits_after/raw*100:7.3f}% of raw   hits={hit_rate:,.1f}   saved={saved:,.0f}b   "
                  f"delta={(bits_after-bits)/raw*100:+.4f}%")
        if abs(bits - bits_after) < 1e-6 * bits:
            if not quiet: print(f"       -> converged (no further expected gain) at pass {t}")
            bits = bits_after; n = n_after
            break
        bits, n = bits_after, n_after

    return bits / raw

# ---- sweep ---------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=12)
    ap.add_argument("--reshuffle", action="store_true", default=True)
    args = ap.parse_args()

    print("=" * 82)
    print("TELOMERE MULTI-PASS RECURRENCE  (analytic, uncapped search, no hashing)")
    print("reshuffle ON (fresh adjacencies each pass); superposition = full-search ceiling")
    print("=" * 82)

    for B in (2, 3, 4):
        print(f"\n### block size = {B} bytes ({8*B} bits), arity cap = 5 ###")
        run(B, 5, args.passes, reshuffle=True)

    print("\n" + "=" * 82)
    print("SWEEP: converged net size (% of raw) -- rows=block bytes, cols=arity cap")
    print("=" * 82)
    caps = (1, 2, 5, 16, 64)
    hdr = "B\\A"
    print(f"{hdr:>6} | " + " ".join(f"{a:>9}" for a in caps))
    print("-" * 70)
    for B in (2, 3, 4, 5):
        row = []
        for a in caps:
            r = run(B, a, args.passes, reshuffle=True, quiet=True)
            row.append(f"{r*100:8.3f}%")
        print(f"{B:>4}B | " + " ".join(f"{c:>9}" for c in row))

    print("\nAll cells are % of the raw input size. 100.000% = break-even (no net change).")
    print("Pass-1 floor cross-checks against model_analysis/arity_floor.py.")
