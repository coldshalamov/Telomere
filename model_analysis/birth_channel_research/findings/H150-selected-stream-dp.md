# H150 - Selected-Stream Min-Plus DP

Date: 2026-06-18

## Question

Can H148's two-pass selected-stream check be made exact without brute-forcing
every possible second-pass record stream?

Runnable artifact:

```text
model_analysis/birth_channel_research/H150-selected_stream_dp.py
```

## Model

The kernel keeps the first-pass search over visible candidate records, but
replaces second-pass enumeration with an online min-plus parser state:

```text
state = (t, hlen, tail, f[0..K])
```

`f[d]` is the cheapest selected second-pass final length that covers the
generated intermediate prefix except for the last `d` bits. Feeding one
intermediate bit updates the suffix parser and computes whether a second-pass
record can close the suffix.

The final file length is `f[0]`. The intermediate `c1` is not stored; it is
free only because the selected final stream decodes to it. There is no
collective future score.

## Results

Default H148 reproduction:

```text
N=4,K=4,D=7

slack=8:
  pass1 coverage = 0.937500
  pass2 selected coverage = 0.000000

slack=12:
  pass1 coverage = 1.000000
  pass2 selected coverage = 0.000000
```

Looser support can be bought, but it bloats badly:

```text
N=4,K=4,D=7,slack=16:
  pass2 coverage = 0.062500
  mean final length = 23.000000 bits
  mean gain = -19.000000 bits/word

N=4,K=4,D=7,slack=20:
  pass2 coverage = 0.625000
  mean final length = 29.100000 bits
  mean gain = -25.100000 bits/word
```

Stretch row:

```text
N=5,K=4,D=7,slack=20:
  pass1 coverage = 1.000000
  pass2 selected coverage = 0.000000
  mean terminal states = 141.406250
```

## Reading

H150 confirms H148 without brute force. The collective H146 future score is
too generous for a real recursive codec. When the next pass has to be an actual
selected stream, support appears only after large slack, and the selected final
stream is far longer than the original.

## Verdict

The missing piece is recurrent fertility/closure of the visible record
language. Candidate count alone is not enough. A positive route must make
intermediate visible strings cheaply re-encodable by the same public grammar
while paying any support restriction or shaping cost.
