# H191 - Kraft-Reserved Raw Fallback

## Conjecture

```text
The H190 one-bit raw-vs-witness mode is too pessimistic. A prefix/arithmetic
mixture can let witness codewords consume Kraft mass q and encode raw fallback
inside the remaining interval at cost N - log2(1-q), perhaps crossing positive.
```

## Kernel

`H191-kraft_reserved_raw_fallback.py`

The kernel enumerates every small `N`-bit output and every exact V1/J3D1 witness
up to `Wmax`. It then prices the optimal implicit raw fallback:

```text
rawFrac = N - log2(1 - q)
```

where `q` is the Kraft mass reserved by the witness language.

Two modes are tested:

```text
all_syntax: every public witness codeword up to Wmax consumes Kraft mass
canonical:  generous lower bound keeping only the shortest witness per output
```

The canonical row is not automatically a wire format; it assumes alias mass can
be publicly reclaimed without a backtracking/referee channel.

## Result

Representative rows from the default exact sweep:

```text
N=8, Wmax=16, canonical:  q=0.007812, rawFrac=8.011315,
                           gainFrac=-0.007365
N=12,Wmax=16, canonical:  q=0.038818, rawFrac=12.057119,
                           gainFrac=-0.044319
N=16,Wmax=16, canonical:  q=0.050766, rawFrac=16.075164,
                           gainFrac=-0.066205
N=16,Wmax=16, all_syntax: q=0.076172, rawFrac=16.114304,
                           gainFrac=-0.105041
```

The nearest nontrivial default miss is:

```text
N=8,Wmax=4,canonical: -0.007365 bits/layer
```

## Bill

The missing raw-vs-witness bit can be reduced to a fractional Kraft-reservation
bill, but it does not disappear:

```text
short witness mass q raises the fallback length for the rest of the alphabet
```

Under uniform targets, the expected length is the source entropy plus a
nonnegative divergence term. A positive row would indicate invalid-code
reclamation, non-unique decoding, or source restriction.

## Mutation

The next attack is not "mode bit too large"; that was tested. The next target is
a public invariant that makes raw/witness partitioning source-shaped or
decoder-derived without thinning supply, consuming checksum/referee bits, or
turning into a generated/reachable class.
