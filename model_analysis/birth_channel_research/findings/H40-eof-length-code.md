# H40 - EOF / whole-file length-code ledger

Date: 2026-06-17

## Question

Can whole-file EOF length act as a free stateless channel?

Mechanism:

```text
fixed n-bit virtual board
public permutation/dither
encode whole state with a non-prefix one-to-one code
decoder uses EOF/file length plus n to recover the virtual state
```

The simplest version is:

```text
y = public_permutation(x)
output = y with leading zeros stripped
decode = left-pad output to n bits, then invert permutation
```

This is a real distinction from record-prefix streams: a whole-file decoder can
use EOF, so the code does not need to be prefix-free across concatenated
records.

## Fixed virtual board

For a uniform `n`-bit state:

```text
E[leading_zero_savings] ~= 1 bit
H(output length) ~= 2 bits
```

The optimal one-to-one non-prefix code for a fixed `n` maps the `2^n` source
states to the first `2^n` binary strings ordered by length. It saves:

```text
~2 bits on average
```

H40 rows:

```text
n=64:  trim save=1.000000, optimal one-to-one save=2.000000, H(length)=2.000000
n=128: trim save=1.000000, optimal one-to-one save=2.000000, H(length)=2.000000
```

The exact optimum is:

```text
E[L]_min = n - 2 + (n + 2) / 2^n
```

because the codebook uses all bitstrings of length `< n` plus one `n`-bit
string. So even the best EOF-delimited fixed-`n` trick has less than two
expected bits of boundary credit.

This is real, but it is a final-state whole-file trick. If every recursive pass
uses the same fixed `n`-bit virtual board, the saved length from previous passes
does not become the next semantic board size. Each pass re-randomizes an `n`-bit
state and the final file still saves only `O(1)` bits.

## Best of P phases

Trying many public permutations and choosing the one with the most leading
zeros looks better, but the chosen phase is a selector:

```text
selector = log2(P)
```

H40 rows:

```text
P=16:    E best LZ=4.377,  selector=4,  net=0.377
P=256:   E best LZ=8.336,  selector=8,  net=0.336
P=65536: E best LZ=16.333, selector=16, net=0.333
```

So best-of-P can add a small constant whole-file gain in this non-prefix model,
but it does not create a per-pass accumulating channel. If the phase is not
stored, decode has `P` possible predecessors. If phase choice is fixed publicly,
there is no best-of-P gain.

## Shrinking board

To make savings compound, the semantic board would need to shrink each pass:

```text
n_{t+1} = n_t - z_t
```

But reverse decode then needs the ordered reduction sequence `z_t`, not merely
the final length. For geometric leading-zero savings:

```text
E[z] ~= 1 bit/pass
H(z) ~= 2 bits/pass
```

H40 rows:

```text
passes=16:  E saved=16,  length-ledger entropy=32,  net=-16
passes=64:  E saved=64,  length-ledger entropy=128, net=-64
passes=256: E saved=256, length-ledger entropy=512, net=-256
```

If only original and final lengths are stored, the decoder knows only
`sum(z_t)`. It still lacks the ordered sequence. Typical sequence ambiguity
grows quickly:

```text
passes=64:  ambiguity ~= 123.171 bits
passes=256: ambiguity ~= 506.174 bits
```

That is the hidden length ledger.

## Byte padding

At the outer file byte surface, bit-level leading-zero savings mostly vanish
unless the format already packs arbitrary bit lengths:

```text
n=128: expected bit save=1.000000
       expected byte-surface save=0.031373 bits
       padding loss=0.968627 bits
```

Telomere's internal bitstream can talk about bit savings, but an on-disk byte
format must still account for final padding.

## Paid outer format

The `~2` bit optimum assumes:

- original `n` is already known;
- exact bit EOF is available;
- no pad-count field is needed.

If those are not public invariants, the constant is spent immediately:

```text
n=64:      ideal gain=2.000, len cost=6.022,  pad count=3, net=-7.022
n=128:     ideal gain=2.000, len cost=7.011,  pad count=3, net=-8.011
n=1,000,000: ideal gain=2.000, len cost=19.932, pad count=3, net=-20.932
```

That does not mean EOF is forbidden. It means the boundary credit is only
available when the container/spec already supplies those invariants.

## Verdict

EOF/non-prefix whole-file coding is real and worth knowing about. It is not the
missing recursive Telomere mechanism:

- fixed virtual boards give only `O(1)` final-file savings;
- best-of-P phases require a selector and still give only a small constant;
- shrinking boards require an ordered length ledger whose entropy exceeds the
  savings;
- byte padding eats most simple leading-zero bit wins unless already packed.
- storing original length or exact valid-bit count spends more than the ideal
  fixed-`n` constant unless those values are already public invariants.

This is a useful side-channel sanity check. It explains why “final length” can
carry a little information, but it does not maintain compression over arbitrary
recursive passes.

## Artifact

`model_analysis/birth_channel_research/H40-eof_length_code.py`
