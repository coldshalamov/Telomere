# H104 - SPEC_V1 Decode Scaling Audit

Date: 2026-06-18

## Question

The current spec says position salt is self-presenting and keep-what-decodes is
the stateless decoder. The proof artifacts show small round trips. Does that
prove arbitrary-pass, arbitrary-size decode has no birth/open bill?

Runnable artifact:

```text
model_analysis/birth_channel_research/H104-spec_decode_scaling_audit.py
```

## Reconciliation

Both facts can be true:

```text
small keep-what-decodes round trips succeed
fixed checksum/trial decode is still a finite referee budget
```

One caveat matters: `v1_roundtrip_proof.py` is useful supplementary evidence
for trial decode, but it is not the exact current position-salt architecture.
It uses pass salts for bundles and original-slot salts for singles, while
`SPEC_V1.md` says position salts. The direct current-architecture artifact for
opening rules is `robins_opening_rules.py`; the scaling counterweight is the
single-record survivor count.

Position salt is self-presenting for a record opened on the reverse step that
returns the stream to its birth/match state. If the record is carried through
later states, opening it on the wrong reverse step can still produce a
syntactically valid stream. In the arity-1 worst case, every opening time is
structurally valid and only the final checksum distinguishes the bytes.

## Result

For `R` independent carried records across `T` possible reverse walks:

```text
S = T^R readings before checksum
referee bits = log2(S) = R * log2(T)
```

Fixed 64-bit checksum capacity:

```text
T passes   Rmax C64   Rmax with 32 safety bits   net@2b/record
2          64.000     32.000                     +1.000
4          32.000     16.000                      0.000
16         16.000      8.000                     -2.000
64         10.667      5.333                     -4.000
256         8.000      4.000                     -6.000
4096        5.333      2.667                    -10.000
```

Scale examples:

```text
T=64, R=10:   log2 S=60    fixed 64-bit checksum barely covers it
T=64, R=100:  log2 S=600   fixed 64-bit checksum is short by 536 bits
T=64, R=1000: log2 S=6000  fixed 64-bit checksum is short by 5936 bits
```

Near-total exception pricing is still finite but not free:

```text
T=64, eps=0.001: H(eps)+eps*log2(T-1) = 0.017385 bits/atom
T=256,eps=0.001: H(eps)+eps*log2(T-1) = 0.019402 bits/atom
```

## Verdict

The keep-what-decodes rule is a valid finite decoder. It is not an unbounded
free birth channel unless a separate invariant bounds the number of surviving
readings independently of record count and pass count.

For arbitrary-pass stateless recursion, one of these still has to be true:

```text
1. total-cover/all-open: no carried records inside the pass layer;
2. public two-epoch lanes: carried records live at most one pass;
3. near-total exception ledger: exceptions are tiny and explicitly priced;
4. new invariant: survivor count is provably subexponential without checksum bits.
```

So H102/H103 remain the best stateless-readiness shape, and the remaining
compression target remains a positive paid forced-rewrite witness margin.
