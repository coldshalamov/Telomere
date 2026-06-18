# H60 - recursive shrink converse

Date: 2026-06-17

## Question

Can the "roughly all data" target be rescued by EOF/non-prefix one-to-one
coding, final length, or kept-if-shrinks logic?

This matters because a one-shot non-prefix code can do something surprising:
if the old length `n` is known externally, there are `2^n - 1` binary strings
shorter than `n`, so almost every `n`-bit input can be mapped to a shorter
string. That is real, but it is not automatically recursive Telomere
compression.

## Kernel

Runnable artifact:

```text
model_analysis/birth_channel_research/H60-recursive_shrink_converse.py
```

H60 separates three bounds:

```text
prefix/public-Q fraction saving >= S <= 2^-S
EOF one-shot fraction saving >= S ~= 2^(1-S)
exact output length n-S fraction = 2^-S
```

For recursion, if total saving is `S` over `P` positive-saving passes and only
root length, final length, and pass count are known, the number of possible
intermediate length paths is:

```text
C(S-1, P-1)
```

So the length-path ledger is:

```text
log2 C(S-1, P-1)
```

It also reports:

```text
exact tiny selector counts for n=4,P=2,s=1
required source lift and binary-KL entropy deficit for roughly-all claims
```

## Results

One-shot bounds:

```text
saving 1 bit:
  prefix bound = 0.5
  EOF one-shot bound ~= 1.0
  exact-length output bound = 0.5

saving 2 bits:
  prefix bound = 0.25
  EOF one-shot bound = 0.5
```

Recursive path examples:

```text
P=16, S=32:
  length-path bits = 28.162983
  net S-path = 3.837017
  exact 1-bit/pass fraction = 2^-16

P=64, S=128:
  length-path bits = 123.171434
  net S-path = 4.828566
  exact 1-bit/pass fraction = 2^-64

P=64, S=256:
  length-path bits = 201.566936
  net S-path = 54.433064
```

Exact tiny selector ledger, `n=4,P=2,s=1`, so `S=2` over `16` inputs:

```text
prefix slots:                    4/16
EOF one-to-one slots:            7/16
prefix raw fallback, r=3:        3/16
best-of 4 profiles, selector free: 16/16 apparent
best-of 4 profiles, selector paid: 4/16
checksum C_eff=1 over 4 profiles: 8/16 apparent, 1 bit still owed
```

Required source lift:

```text
S=8,   c=0.90: lift=230.4,    KL deficit=6.731569 bits
S=128, c=0.90: lift=3.06e38,  KL deficit=114.731004 bits
S=128, c=0.99: lift=3.37e38,  KL deficit=126.639207 bits
```

## Reading

EOF/non-prefix one-to-one coding is a valid one-shot length side effect. It can
make a fixed-length block look compressible for almost every input if the
previous length is free.

The recursive blocker is the length path. If pass savings vary, the decoder
cannot invert the last layer without knowing the previous layer length, then
the one before that, and so on. Final length plus root length gives only total
saving; it does not give the path.

If the code forces exactly one bit of saving per pass so the path is derivable,
the eligible exact-length-output fraction is only:

```text
2^-P
```

That is not "roughly all data" over arbitrary passes.

The exact tiny ledger shows the hidden-channel mechanics in miniature. A
best-of-profile system can appear to cover all inputs if the profile identity
is free. Once the selector is paid, it returns to the prefix count. A checksum
can widen the apparent count only up to its finite effective bits; the
remaining profile bits are still owed.

The prior-lift rows quantify the only honest way to make a tiny uniform winning
set become "roughly all" under a different source: the source must concentrate
on that set by the listed lift and entropy deficit. That is source-shaped
compression, not uniform roughly-all-data compression.

## Accounting

Derived:

- one-shot old length, if stored once in a root header;
- final length from EOF;
- fixed exact saving per pass, if truly invariant.

Paid:

- intermediate length path when savings vary;
- pass/profile selector for kept-if-shrinks or best-of-P;
- checksum/referee bits for trial-decoded length paths.

Hidden if omitted:

- treating old length as known at every recursive layer;
- using final length to recover a whole variable length path;
- using non-prefix one-shot counts as if they were prefix/streamable records.

## Verdict

The EOF/non-prefix loophole is real but finite. It explains why a one-shot
"almost all strings shrink by one bit" argument can be true without violating
counting. It does not solve stateless arbitrary-pass recursion.

For maintained recursive compression over roughly all data, a successful
mechanism still needs one of:

- a public invariant that fixes the intermediate length path without reducing
  the eligible fraction to `2^-P`;
- a paid length/path ledger whose cost is beaten elsewhere;
- or a genuine non-uniform source/value law.

No such invariant is identified by H60.
